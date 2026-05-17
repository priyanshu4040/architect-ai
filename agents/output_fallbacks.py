"""
Merge agent outputs into frontend structured payloads.

Parser-detected brownfield fields are authoritative — LLM cannot overwrite them.
Synthetic defaults only when force_fallback=True (agent runtime unavailable).
"""

from typing import Any, Dict, List

from agents.output_schemas import (
    BrownfieldStructuredOutput,
    EvolutionPlan,
    GreenfieldStructuredOutput,
    SuggestedArchitecture,
)

_PARSER_AUTHORITATIVE_KEYS = frozenset({
    "detected_modules",
    "detected_apis",
    "detected_stack",
    "detected_tech_stack",
})
_MAX_ISSUES = 15


def _non_empty_list(items) -> list:
    if not isinstance(items, list):
        return []
    return [str(x).strip() for x in items if str(x).strip()]


def _deep_get(d: Dict, *keys, default=None):
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
    return cur if cur is not None else default


def _has_primary_llm_data(primary: Dict[str, Any] | None) -> bool:
    if not primary:
        return False
    for v in primary.values():
        if v not in (None, "", [], {}):
            return True
    return False


def _mark_fallback(out: Dict[str, Any], *, force_fallback: bool, reason: str, fields: List[str]) -> Dict[str, Any]:
    if force_fallback or fields:
        out["is_fallback"] = True
        out["fallback_reason"] = reason
        if fields:
            out["fallback_fields"] = fields
        if force_fallback:
            out["fallback_type"] = out.get("fallback_type") or "agent_unavailable"
    else:
        out["is_fallback"] = False
    return out


def _normalize_detected_modules(items: List) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for item in items or []:
        if isinstance(item, dict) and item.get("name"):
            out.append({
                "name": str(item.get("name", "")),
                "type": str(item.get("type", "unknown")),
                "path": str(item.get("path", item.get("evidence", ""))),
                "evidence": str(item.get("evidence", item.get("path", ""))),
                "confidence": str(item.get("confidence", "high")),
            })
        elif isinstance(item, str) and item.strip():
            out.append({
                "name": item.strip(),
                "type": "unknown",
                "path": "",
                "evidence": "",
                "confidence": "low",
            })
    return out


def merge_greenfield_structured(
    primary: Dict[str, Any] | None,
    analysis: Dict[str, Any] | None,
    architecture_results: Dict[str, Any] | None,
    requirements: str,
    *,
    force_fallback: bool = False,
    architecture_plan: str = "",
) -> Dict[str, Any]:
    out = GreenfieldStructuredOutput().model_dump()
    synthetic_fields: List[str] = []

    if primary:
        for k, v in primary.items():
            if k in ("is_fallback", "fallback_reason", "fallback_fields"):
                continue
            if v not in (None, "", [], {}):
                out[k] = v

    insights = analysis or {}
    arch = architecture_results or {}
    has_llm = _has_primary_llm_data(primary) or bool(insights) or bool(arch) or bool(
        (architecture_plan or "").strip()
    )

    if not out.get("project_summary"):
        out["project_summary"] = (
            insights.get("project_summary")
            or (requirements[:400] + ("..." if len(requirements) > 400 else ""))
        )

    if not out.get("detected_domain") and insights.get("detected_domain"):
        out["detected_domain"] = insights["detected_domain"]
    elif not out.get("detected_domain") and force_fallback:
        out["detected_domain"] = "General web application"
        synthetic_fields.append("detected_domain")

    if not _non_empty_list(out.get("assumptions")):
        out["assumptions"] = _non_empty_list(insights.get("constraints"))[:8]

    if not _non_empty_list(out.get("functional_requirements")):
        out["functional_requirements"] = _non_empty_list(insights.get("functional_requirements"))
    if not _non_empty_list(out.get("non_functional_requirements")):
        out["non_functional_requirements"] = _non_empty_list(
            insights.get("non_functional_requirements")
        )
    if not _non_empty_list(out.get("database_entities")):
        out["database_entities"] = _non_empty_list(insights.get("data_entities"))

    suggested = out.get("suggested_architecture") or {}
    if isinstance(suggested, dict) and not any(suggested.values()):
        decisions = arch.get("key_decisions") or []
        dec_text = " ".join(
            f"{d.get('decision', '')} {d.get('rationale', '')}"
            for d in decisions
            if isinstance(d, dict)
        )
        if dec_text.strip():
            out["suggested_architecture"] = SuggestedArchitecture(
                backend=dec_text[:500],
            ).model_dump()
        elif force_fallback:
            out["suggested_architecture"] = SuggestedArchitecture(
                frontend="See architecture plan.",
                backend="Modular backend aligned to domain boundaries.",
                database="Relational store unless document/event requirements dominate.",
                authentication="Session or JWT based on client type and threat model.",
                deployment="Containerized deploy on managed cloud with CI/CD.",
            ).model_dump()
            synthetic_fields.append("suggested_architecture")

    if not _non_empty_list(out.get("modules")):
        comps = [
            str(c.get("component", ""))
            for c in (arch.get("component_details") or [])
            if isinstance(c, dict) and c.get("component")
        ]
        if comps:
            out["modules"] = comps[:10]
        elif force_fallback:
            synthetic_fields.append("modules")

    if not _non_empty_list(out.get("security_suggestions")):
        mitigations = [
            str(r.get("mitigation", r.get("risk", "")))
            for r in (arch.get("risk_analysis") or [])
            if isinstance(r, dict) and (r.get("mitigation") or r.get("risk"))
        ]
        if mitigations:
            out["security_suggestions"] = mitigations[:6]
        elif force_fallback:
            synthetic_fields.append("security_suggestions")

    if not _non_empty_list(out.get("scalability_suggestions")):
        notes = (arch.get("indicators") or {}).get("notes") or {}
        note = notes.get("scalability") if isinstance(notes, dict) else None
        if note:
            out["scalability_suggestions"] = [note]
        elif force_fallback:
            synthetic_fields.append("scalability_suggestions")

    if not out.get("final_summary"):
        patterns = arch.get("recommended_patterns") or []
        if patterns and isinstance(patterns[0], dict):
            out["final_summary"] = patterns[0].get("why", "")[:600]
        else:
            out["final_summary"] = out.get("project_summary", "")

    reason = (
        "Agent runtime unavailable; showing placeholder structured sections."
        if force_fallback
        else (
            "Some structured fields were filled from partial agent output."
            if synthetic_fields
            else ""
        )
    )
    if force_fallback and not has_llm:
        return _mark_fallback(
            out,
            force_fallback=True,
            reason=reason or "Agent runtime unavailable.",
            fields=synthetic_fields,
        )
    if synthetic_fields:
        return _mark_fallback(out, force_fallback=False, reason=reason, fields=synthetic_fields)
    return _mark_fallback(out, force_fallback=False, reason="", fields=[])


def _coerce_issue_list(items: List) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for item in items or []:
        if isinstance(item, dict):
            out.append({
                "issue": str(item.get("issue", item.get("fault", ""))),
                "severity": str(item.get("severity", "Medium")),
                "reason": str(item.get("reason", item.get("evidence", ""))),
                "suggested_fix": str(item.get("suggested_fix", item.get("mitigation", ""))),
                "affected_area": str(
                    item.get("affected_area", item.get("affected_file_or_folder", ""))
                ),
                "evidence": str(item.get("evidence", "")),
                "affected_file_or_folder": str(
                    item.get("affected_file_or_folder", item.get("affected_area", ""))
                ),
            })
        elif isinstance(item, str) and item.strip():
            out.append({
                "issue": item,
                "severity": "Medium",
                "reason": "",
                "suggested_fix": "",
                "affected_area": "",
                "evidence": "",
                "affected_file_or_folder": "",
            })
    return out


def merge_brownfield_structured(
    primary: Dict[str, Any] | None,
    analysis: Dict[str, Any] | None,
    architecture_results: Dict[str, Any] | None,
    inventory: Dict[str, Any] | None,
    deep_analysis: Dict[str, Any] | None = None,
    *,
    force_fallback: bool = False,
    llm_failed: bool = False,
    structured_llm_incomplete: bool = False,
) -> Dict[str, Any]:
    """Merge parser (authoritative) + optional LLM enrichment."""
    synthetic_fields: List[str] = []
    base = dict(deep_analysis or {})
    base.pop("_parser_stats", None)
    base.pop("_analysis_text", None)
    base.pop("compact_summary", None)
    base.pop("detected_stack_evidence", None)
    base.pop("detected_modules_flat", None)
    has_static = bool(base.get("detected_modules") or base.get("detected_apis"))

    out = BrownfieldStructuredOutput().model_dump()
    parser_modules = _normalize_detected_modules(base.get("detected_modules") or [])
    parser_apis = base.get("detected_apis") or []
    parser_stack = base.get("detected_stack") or {}
    parser_tech_stack = base.get("detected_tech_stack") or {}

    if base:
        for k, v in base.items():
            if k in _PARSER_AUTHORITATIVE_KEYS:
                continue
            if v not in (None, "", [], {}):
                out[k] = v

    out["detected_modules"] = parser_modules
    out["detected_apis"] = parser_apis
    if isinstance(parser_stack, dict) and any(parser_stack.values()):
        out["detected_stack"] = parser_stack
    if isinstance(parser_tech_stack, dict) and parser_tech_stack:
        out["detected_tech_stack"] = {
            "languages": parser_tech_stack.get("languages", []),
            "language_percentages": parser_tech_stack.get("language_percentages", {}),
            "frameworks": parser_tech_stack.get("frameworks", []),
            "libraries": parser_tech_stack.get("libraries", []),
            "databases": parser_tech_stack.get("databases", []),
            "build_tools": parser_tech_stack.get("build_tools", []),
            "deployment": parser_tech_stack.get("deployment", []),
            "package_managers": parser_tech_stack.get("package_managers", []),
            "evidence": parser_tech_stack.get("evidence", {}),
            "confidence": parser_tech_stack.get("confidence", {}),
            "folder_structure": parser_tech_stack.get("folder_structure", []),
            "validation_message": parser_tech_stack.get("validation_message", ""),
        }

    if primary:
        for k, v in primary.items():
            if k in ("is_fallback", "fallback_reason", "fallback_fields"):
                continue
            if k in _PARSER_AUTHORITATIVE_KEYS:
                continue
            if v not in (None, "", [], {}):
                out[k] = v

    insights = analysis or {}
    arch = architecture_results or {}

    if not out.get("project_summary"):
        out["project_summary"] = insights.get("project_summary") or _deep_get(inventory, "summary", default="")

    if not (out.get("suggested_modules") or []) and primary:
        sm = primary.get("suggested_modules")
        if isinstance(sm, list):
            out["suggested_modules"] = [
                x for x in sm if isinstance(x, dict) and x.get("name")
            ][:10]

    if not out.get("folder_analysis"):
        out["folder_analysis"] = base.get("folder_analysis") or []

    if not out.get("architecture_issues"):
        smells = _coerce_issue_list(_non_empty_list(insights.get("architecture_smells")))
        faults = _coerce_issue_list(arch.get("current_codebase_faults") or [])
        combined = base.get("architecture_issues") or smells or faults
        out["architecture_issues"] = combined[:_MAX_ISSUES]

    if not out.get("security_issues"):
        out["security_issues"] = base.get("security_issues") or _coerce_issue_list(
            _non_empty_list(insights.get("security_gaps"))
        )

    if not out.get("scalability_issues"):
        out["scalability_issues"] = base.get("scalability_issues") or _coerce_issue_list(
            _non_empty_list(insights.get("scalability_concerns"))
        )

    if not out.get("maintainability_issues"):
        out["maintainability_issues"] = base.get("maintainability_issues") or []

    evo = out.get("evolution_plan")
    if not isinstance(evo, dict) or not any(evo.values()):
        base_evo = base.get("evolution_plan")
        if isinstance(base_evo, dict) and any(base_evo.values()):
            out["evolution_plan"] = base_evo
        elif force_fallback and not has_static:
            out["evolution_plan"] = EvolutionPlan(
                immediate_fixes=["Re-run analysis with agents enabled."],
            ).model_dump()
            synthetic_fields.append("evolution_plan")

    if not out.get("final_summary"):
        cmp_rows = arch.get("comparison_old_vs_new") or []
        if cmp_rows and isinstance(cmp_rows[0], dict):
            out["final_summary"] = str(cmp_rows[0].get("benefit", ""))[:600]
        else:
            out["final_summary"] = out.get("project_summary", "")

    # True LLM outage: no narrative/plan — parser-only ZIP summary.
    if llm_failed and has_static:
        out["is_fallback"] = True
        out["fallback_type"] = "parser_only"
        out["message"] = "AI analysis unavailable. Showing ZIP parser results only."
        out["final_summary"] = out.get("final_summary") or "AI review unavailable."
        return out

    # Narrative succeeded but structured JSON failed — not an error state.
    if structured_llm_incomplete:
        out["is_fallback"] = False
        out["structured_partial"] = True
        out["fallback_type"] = "structured_partial"
        out["message"] = (
            "Full structured review was not extracted; narrative plan and parser data are shown."
        )

    if force_fallback and not has_static and not _has_primary_llm_data(primary):
        return _mark_fallback(
            out,
            force_fallback=True,
            reason="Agent runtime unavailable; static/partial data only.",
            fields=synthetic_fields,
        )
    if synthetic_fields:
        return _mark_fallback(
            out,
            force_fallback=False,
            reason="Some brownfield fields use placeholder values.",
            fields=synthetic_fields,
        )
    return _mark_fallback(out, force_fallback=False, reason="", fields=[])
