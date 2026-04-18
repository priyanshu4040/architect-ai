import os
import sys
import json
import re
from pathlib import Path
from typing import Any, Dict, Tuple

# Load .env from the repo root early so GROQ_API_KEY is available whenever
# this module is imported (e.g. standalone scripts, tests, or direct uvicorn
# invocations that don't go through backend/app/main.py first).
try:
    from dotenv import load_dotenv as _load_dotenv

    _env_path = Path(__file__).resolve().parents[2] / ".env"
    _load_dotenv(_env_path, override=False)
except Exception:
    pass  # python-dotenv not installed — rely on shell environment


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from .layer_reconcile import reconcile_structured_layers
from .layers_common import normalize_layer


def _fallback_greenfield_plan(requirements: str) -> str:
    return (
        "## Proposed Architecture (Fallback)\n\n"
        "- Pattern: Layered + modular monolith (safe default)\n"
        "- Modules: `api`, `application`, `domain`, `infrastructure`\n"
        "- Start with clear boundaries and evolve to microservices only when needed.\n\n"
        "### Inputs\n"
        f"{requirements[:1500]}"
    )


def _fallback_brownfield_report(user_input: str) -> str:
    return (
        "## Brownfield Analysis (Fallback)\n\n"
        "- High: Unknown coupling hotspots (LLM pipeline unavailable).\n"
        "- Medium: Missing architecture conformance checks.\n"
        "- Low: Documentation and ownership boundaries may be unclear.\n\n"
        "Recommendation: enable LangGraph/LangChain runtime and rerun for deep analysis.\n\n"
        "### Input Snapshot\n"
        f"{user_input[:1500]}"
    )


def _imports() -> Dict[str, Any]:
    from langgraph.graph import StateGraph

    from agents.ast_parser import generate_ast_summary
    from agents.analysis import analysis_agent
    from agents.brownfield import code_agent, generate_brownfield_component_details
    from agents.graph_builder import parse_ast_summary_to_graph, parse_mermaid_to_graph
    from agents.greenfield import architecture_agent
    from agents.memory import forget_memory, retrieve_memory, train_memory
    from agents.router import router
    from agents.state import AgentState
    from agents.utils import read_codebase

    return {
        "StateGraph": StateGraph,
        "AgentState": AgentState,
        "architecture_agent": architecture_agent,
        "code_agent": code_agent,
        "generate_brownfield_component_details": generate_brownfield_component_details,
        "analysis_agent": analysis_agent,
        "router": router,
        "read_codebase": read_codebase,
        "generate_ast_summary": generate_ast_summary,
        "parse_ast_summary_to_graph": parse_ast_summary_to_graph,
        "parse_mermaid_to_graph": parse_mermaid_to_graph,
        "train_memory": train_memory,
        "retrieve_memory": retrieve_memory,
        "forget_memory": forget_memory,
    }


def _build_graph(mods: Dict[str, Any]):
    builder = mods["StateGraph"](mods["AgentState"])
    builder.add_node("architecture", mods["architecture_agent"])
    builder.add_node("code", mods["code_agent"])
    builder.add_node("analysis", mods["analysis_agent"])
    builder.set_conditional_entry_point(mods["router"])
    builder.add_edge("code", "analysis")
    builder.add_edge("analysis", "architecture")
    builder.set_finish_point("architecture")
    return builder.compile()


def _extract_results_json(text: str) -> Dict[str, Any] | None:
    """
    Extract a JSON block from agent output.

    Expected shape:
      ```json
      { "results": { ... } }
      ```
    Returns the inner `results` dict when possible.
    """
    if not text:
        return None

    m = re.search(r"```json\s*(\{[\s\S]*?\})\s*```", text, re.IGNORECASE)
    if not m:
        return None

    raw = m.group(1).strip()
    try:
        obj = json.loads(raw)
    except Exception:
        return None

    if isinstance(obj, dict) and isinstance(obj.get("results"), dict):
        return obj["results"]
    return None


# Tokens that alone do not tie a component name to a specific project (whitelist overlap).
_GENERIC_ARCH_TOKENS = frozenset(
    {
        "service",
        "manager",
        "controller",
        "adapter",
        "handler",
        "client",
        "base",
        "helper",
        "util",
        "utils",
        "data",
        "model",
        "dto",
        "api",
        "gateway",
        "worker",
        "provider",
        "factory",
        "impl",
        "interface",
        "component",
        "module",
        "system",
        "app",
        "core",
        "common",
        "shared",
        "server",
        "database",
        "cache",
        "queue",
        "repo",
        "repository",
    }
)


def _tokenizer_words(text: str) -> set[str]:
    return {m.group(0).lower() for m in re.finditer(r"[A-Za-z][A-Za-z0-9]{2,}", text or "")}


def _name_fragments(name: str) -> set[str]:
    raw = (name or "").strip()
    if not raw:
        return set()
    s1 = re.sub(r"([a-z])([A-Z])", r"\1 \2", raw)
    s2 = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", s1)
    parts = {p.lower() for p in re.split(r"[\s_\-/]+", s2) if p}
    alnum = re.sub(r"[^a-zA-Z0-9]", "", raw).lower()
    if alnum:
        parts.add(alnum)
    return parts


def _component_detail_grounded(
    name: str, functionality: str, corpus_lower: str, ast_words: set[str]
) -> bool:
    name = (name or "").strip()
    if not name:
        return False
    nl = name.lower()
    if nl in corpus_lower:
        return True
    frags = _name_fragments(name)
    meaningful = {f for f in frags if len(f) >= 3 and f not in _GENERIC_ARCH_TOKENS}
    if not meaningful:
        return nl in corpus_lower
    for f in meaningful:
        if f in corpus_lower:
            return True
    if meaningful & ast_words:
        return True
    fn_low = (functionality or "").lower()
    for f in meaningful:
        if len(f) >= 4 and f in fn_low and f in corpus_lower:
            return True
    return False


def _prune_ungrounded_component_details(
    results: Dict[str, Any] | None,
    *,
    corpus: str,
    ast_summary: str,
) -> tuple[Dict[str, Any] | None, str]:
    """
    Drop component_details entries with no lexical overlap with README/AST/requirements.
    Returns (possibly mutated results dict, extra warning text).
    """
    if not results or not isinstance(results, dict):
        return results, ""
    details = results.get("component_details")
    if not isinstance(details, list) or not details:
        return results, ""

    corpus_lower = (corpus or "").lower()
    ast_words = _tokenizer_words(ast_summary or "")

    kept: list[dict] = []
    kept_lower: set[str] = set()
    for item in details:
        if not isinstance(item, dict):
            continue
        comp = str(item.get("component") or "").strip()
        if not comp:
            continue
        fn = str(item.get("functionality") or "").strip()
        if _component_detail_grounded(comp, fn, corpus_lower, ast_words):
            kept.append(item)
            kept_lower.add(comp.lower())

    if not kept and details:
        return results, ""

    out = dict(results)
    out["component_details"] = kept

    mapping = out.get("component_layer_mapping")
    if isinstance(mapping, list):
        out["component_layer_mapping"] = [
            m
            for m in mapping
            if isinstance(m, dict)
            and str(m.get("component") or "").strip().lower() in kept_lower
        ]
    extra = ""
    if len(kept) < len(details):
        extra = (
            f"Removed {len(details) - len(kept)} component(s) with no textual overlap "
            "with README, AST summary, or requirements."
        )
    return out, extra


def _results_to_analysis_report(results: Dict[str, Any]) -> str:
    """
    Convert structured `results` into a professional markdown analysis report.
    This makes greenfield runs produce a stable `analysis_report` even if the LLM
    only returns a plan + JSON.
    """
    if not results:
        return ""

    patterns = results.get("recommended_patterns") or []
    decisions = results.get("key_decisions") or []
    risks = results.get("risk_analysis") or []
    roadmap = results.get("evolution_roadmap") or []
    indicators = results.get("indicators") or {}
    notes = (indicators.get("notes") or {}) if isinstance(indicators, dict) else {}

    def fmt_int(x: Any) -> str:
        try:
            return str(int(x))
        except Exception:
            return ""

    lines: list[str] = []
    lines.append("## Executive Summary")
    if patterns:
        for p in patterns[:5]:
            pat = (p.get("pattern") or "").strip()
            why = (p.get("why") or "").strip()
            conf = fmt_int(p.get("confidence"))
            msg = f"- **{pat}**"
            if conf:
                msg += f" ({conf}/100)"
            if why:
                msg += f": {why}"
            lines.append(msg)
    else:
        lines.append("- Architecture recommendation generated from requirements.")

    lines.append("")
    lines.append("## Non-Functional Assessment")
    for key in ("scalability", "performance", "maintainability", "security"):
        val = fmt_int(indicators.get(key)) if isinstance(indicators, dict) else ""
        note = (notes.get(key) or "").strip() if isinstance(notes, dict) else ""
        label = key.capitalize()
        if val:
            lines.append(f"- **{label}**: {val}/100" + (f" — {note}" if note else ""))
        elif note:
            lines.append(f"- **{label}**: {note}")

    if decisions:
        lines.append("")
        lines.append("## Key Decisions")
        for d in decisions[:6]:
            dec = (d.get("decision") or "").strip()
            rat = (d.get("rationale") or "").strip()
            if not dec:
                continue
            lines.append(f"- **{dec}**" + (f": {rat}" if rat else ""))

    if risks:
        lines.append("")
        lines.append("## Risk Analysis")
        for r in risks[:6]:
            risk = (r.get("risk") or "").strip()
            sev = (r.get("severity") or "").strip()
            impact = (r.get("impact") or "").strip()
            like = (r.get("likelihood") or "").strip()
            mit = (r.get("mitigation") or "").strip()
            if not risk:
                continue
            meta_bits = [b for b in [sev and f"Severity: {sev}", like and f"Likelihood: {like}", impact and f"Impact: {impact}"] if b]
            meta = " · ".join(meta_bits)
            lines.append(f"- **{risk}**" + (f" ({meta})" if meta else ""))
            if mit:
                lines.append(f"  - Mitigation: {mit}")

    if roadmap:
        lines.append("")
        lines.append("## Evolution Roadmap (High Level)")
        for ph in roadmap[:4]:
            phase = (ph.get("phase") or "").strip()
            timeframe = (ph.get("timeframe") or "").strip()
            title = phase or "Phase"
            if timeframe:
                title = f"{title} ({timeframe})"
            lines.append(f"- **{title}**")
            goals = ph.get("goals") or []
            deliverables = ph.get("deliverables") or []
            for item in (goals + deliverables)[:6]:
                s = str(item).strip()
                if s:
                    lines.append(f"  - {s}")

    return "\n".join(lines).strip()


def _apply_layer_assignments(graph_data: Dict[str, Any], results: Dict[str, Any] | None) -> Dict[str, Any]:
    if not graph_data or not isinstance(graph_data, dict):
        return graph_data
    if not results or not isinstance(results, dict):
        return graph_data

    mapping = results.get("component_layer_mapping") or []
    if not isinstance(mapping, list) or not mapping:
        return graph_data

    layer_by_component: Dict[str, str] = {}
    for item in mapping:
        if not isinstance(item, dict):
            continue
        name = str(item.get("component") or "").strip().lower()
        layer = normalize_layer(item.get("layer"))
        if name and layer:
            layer_by_component[name] = layer

    if not layer_by_component:
        return graph_data

    for node in graph_data.get("nodes", []):
        if not isinstance(node, dict):
            continue
        label_key = str(node.get("label") or "").strip().lower()
        id_key = str(node.get("id") or "").strip().lower()
        assigned = layer_by_component.get(label_key) or layer_by_component.get(id_key)
        if assigned:
            node["layer"] = assigned

    return graph_data


def _detailed_functionality_fallback(label: str, layer: str | None, ntype: str | None) -> str:
    component = (label or "This component").strip()
    l = (layer or "").strip().lower()
    t = (ntype or "").strip().lower()

    if l == "presentation":
        return (
            f"{component} serves as the interaction boundary for clients and upstream consumers. "
            "It validates incoming requests, translates them into application-level operations, "
            "and returns normalized responses with consistent error handling. "
            "It should avoid core business decisions and delegate domain behavior to business services."
        )
    if l == "business":
        return (
            f"{component} encapsulates core domain behavior and orchestration rules for this capability. "
            "It coordinates use-cases, applies validations and policy checks, and controls transactional flow "
            "across dependent repositories or external adapters. "
            "It should remain framework-light so business rules are testable and reusable."
        )
    if l == "data":
        return (
            f"{component} is responsible for persistence and query access patterns required by the domain. "
            "It abstracts storage-specific details (schema, query optimization, caching, and mapping), "
            "and provides stable read/write contracts to business services. "
            "It should centralize data consistency and reduce leakage of storage concerns into higher layers."
        )
    if l == "infrastructure" or t in {"client", "queue", "storage", "external", "file"}:
        return (
            f"{component} provides technical integration with platform or third-party capabilities. "
            "It handles protocol-level concerns such as retries, timeouts, serialization, observability, and failures, "
            "exposing a clean interface for the business layer. "
            "It should keep vendor-specific logic isolated to simplify replacement and maintenance."
        )
    return (
        f"{component} owns a focused architectural responsibility and collaborates with connected components "
        "through explicit contracts. It should keep a clear boundary, minimize hidden side effects, and expose behavior "
        "that is observable, testable, and aligned with system-level quality goals."
    )


def _apply_component_details(graph_data: Dict[str, Any], results: Dict[str, Any] | None, mode: str | None = None) -> Dict[str, Any]:
    if not graph_data or not isinstance(graph_data, dict):
        return graph_data

    details_by_component: Dict[str, str] = {}
    if isinstance(results, dict):
        component_details = results.get("component_details") or []
        if isinstance(component_details, list):
            for item in component_details:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("component") or "").strip().lower().replace(" ", "").replace("_", "")
                functionality = str(item.get("functionality") or "").strip()
                inputs = [str(x).strip() for x in (item.get("inputs") or []) if str(x).strip()]
                outputs = [str(x).strip() for x in (item.get("outputs") or []) if str(x).strip()]
                deps = [str(x).strip() for x in (item.get("dependencies") or []) if str(x).strip()]
                if not name:
                    continue
                extra = []
                if inputs:
                    extra.append(f"Inputs: {', '.join(inputs[:6])}.")
                if outputs:
                    extra.append(f"Outputs: {', '.join(outputs[:6])}.")
                if deps:
                    extra.append(f"Dependencies: {', '.join(deps[:6])}.")
                merged = " ".join([functionality] + extra).strip()
                if merged:
                    details_by_component[name] = merged

    for node in graph_data.get("nodes", []):
        if not isinstance(node, dict):
            continue
        label = str(node.get("label") or "").strip()
        key_label = label.lower().replace(" ", "").replace("_", "")
        key_id = str(node.get("id") or "").strip().lower().replace(" ", "").replace("_", "")
        chosen = details_by_component.get(key_label) or details_by_component.get(key_id)
        if not chosen:
            existing = str(node.get("functionality") or node.get("description") or "").strip()
            if existing and len(existing) >= 50:
                chosen = existing
            else:
                chosen = _detailed_functionality_fallback(label, node.get("layer"), node.get("type"))
        node["functionality"] = chosen
        # Keep description aligned for clients that still read description.
        node["description"] = chosen

    return graph_data


def _strip_unwanted_blocks(text: str) -> str:
    if not text:
        return ""
    return (
        text
        .replace("\r\n", "\n")
        .replace("\r", "\n")
    )


def _remove_mermaid_and_json_blocks(text: str) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"```mermaid[\s\S]*?```", "", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"```json[\s\S]*?```", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _extract_mermaid_block(text: str) -> str:
    """Return a fenced Mermaid block from architecture plan text, or empty string."""
    if not text:
        return ""
    m = re.search(r"```mermaid\s*([\s\S]*?)```", text, flags=re.IGNORECASE)
    if not m:
        return ""
    inner = (m.group(1) or "").strip()
    if not inner:
        return ""
    return f"```mermaid\n{inner}\n```"


def _bar(score: int) -> str:
    s = max(0, min(100, int(score)))
    filled = int(round(s / 10))
    return "█" * filled + "░" * (10 - filled)


def _build_detailed_report_document(
    *,
    mode: str,
    analysis_report: str,
    architecture_plan: str,
    graph_data: Dict[str, Any],
    results: Dict[str, Any] | None,
    warning: str,
) -> str:
    safe_analysis = _remove_mermaid_and_json_blocks(_strip_unwanted_blocks(analysis_report))
    safe_plan = _remove_mermaid_and_json_blocks(_strip_unwanted_blocks(architecture_plan))

    patterns = (results or {}).get("recommended_patterns") or []
    decisions = (results or {}).get("key_decisions") or []
    risks = (results or {}).get("risk_analysis") or []
    roadmap = (results or {}).get("evolution_roadmap") or []
    indicators = (results or {}).get("indicators") or {}
    layer_map = (results or {}).get("component_layer_mapping") or []
    comp_details = (results or {}).get("component_details") or []
    current_faults = (results or {}).get("current_codebase_faults") or []
    old_new = (results or {}).get("comparison_old_vs_new") or []
    expected_improvements = (results or {}).get("expected_improvements") or []

    nodes = (graph_data or {}).get("nodes") or []
    edges = (graph_data or {}).get("edges") or []

    # Layer counts: prefer agent mapping (one row per component) so "Data" reflects JSON layers;
    # fall back to graph node layers when mapping is missing.
    layer_counts: Dict[str, int] = {"presentation": 0, "business": 0, "data": 0, "infrastructure": 0}
    mapping_counted = False
    if isinstance(layer_map, list) and layer_map:
        for item in layer_map:
            if not isinstance(item, dict):
                continue
            layer = normalize_layer(item.get("layer"))
            if layer in layer_counts:
                layer_counts[layer] += 1
                mapping_counted = True
    if not mapping_counted:
        for n in nodes:
            if not isinstance(n, dict):
                continue
            layer = normalize_layer(n.get("layer")) or str(n.get("layer") or "").strip().lower()
            if layer in layer_counts:
                layer_counts[layer] += 1

    # Relationship counts by edge label
    rel_counts: Dict[str, int] = {}
    for e in edges:
        if not isinstance(e, dict):
            continue
        label = str(e.get("label") or "uses").strip().lower() or "uses"
        rel_counts[label] = rel_counts.get(label, 0) + 1

    # Component details table rows (prefer explicit results, fallback to graph nodes)
    detail_rows: list[tuple[str, str, str]] = []
    if isinstance(comp_details, list) and comp_details:
        for item in comp_details[:30]:
            if not isinstance(item, dict):
                continue
            name = str(item.get("component") or "").strip()
            func = str(item.get("functionality") or "").strip()
            deps = ", ".join([str(d).strip() for d in (item.get("dependencies") or []) if str(d).strip()][:4])
            if name:
                detail_rows.append((name, (func or "N/A").replace("\n", " "), deps or "N/A"))
    else:
        for n in nodes[:30]:
            if not isinstance(n, dict):
                continue
            name = str(n.get("label") or n.get("id") or "").strip()
            func = str(n.get("functionality") or n.get("description") or "").strip()
            if name:
                detail_rows.append((name, (func or "N/A").replace("\n", " "), "N/A"))

    scalability = int(indicators.get("scalability", 0) or 0) if isinstance(indicators, dict) else 0
    performance = int(indicators.get("performance", 0) or 0) if isinstance(indicators, dict) else 0
    maintainability = int(indicators.get("maintainability", 0) or 0) if isinstance(indicators, dict) else 0
    security = int(indicators.get("security", 0) or 0) if isinstance(indicators, dict) else 0

    lines: list[str] = []
    lines.append("# Architecture Analysis Report")
    lines.append("")
    lines.append("## 1. Report Context")
    lines.append(f"- **Analysis mode:** {mode}")
    lines.append(f"- **Components identified:** {len(nodes)}")
    lines.append(f"- **Dependencies identified:** {len(edges)}")
    if warning:
        lines.append(f"- **Warning:** {warning}")
    lines.append("")
    lines.append("## 2. Executive Summary")
    if patterns:
        for p in patterns[:5]:
            lines.append(f"- **{p.get('pattern', 'Recommendation')}**: {p.get('why', 'Rationale not provided.')}")
    else:
        lines.append("- The architecture analysis recommends modular boundaries and explicit dependency contracts.")
        lines.append("- Prioritize high-impact risks first, then execute phased modernization.")
    lines.append("")
    lines.append("## 3. Architecture Overview")
    lines.append("### 3.1 Layer Distribution (Visual Scorecard)")
    lines.append("| Layer | Components |")
    lines.append("|---|---:|")
    lines.append(f"| Presentation | {layer_counts['presentation']} |")
    lines.append(f"| Business | {layer_counts['business']} |")
    lines.append(f"| Data | {layer_counts['data']} |")
    lines.append(f"| Infrastructure | {layer_counts['infrastructure']} |")
    lines.append("")
    lines.append("## 3A. Brownfield Current-State Findings")
    if mode == "brownfield":
        if isinstance(current_faults, list) and current_faults:
            lines.append("| Fault | Severity | Evidence | Impact |")
            lines.append("|---|---|---|---|")
            for f in current_faults[:20]:
                if not isinstance(f, dict):
                    continue
                lines.append(
                    f"| {str(f.get('fault', 'N/A')).replace('|', '/')} | "
                    f"{f.get('severity', 'N/A')} | "
                    f"{str(f.get('evidence', 'N/A')).replace('|', '/')} | "
                    f"{str(f.get('impact', 'N/A')).replace('|', '/')} |"
                )
        else:
            lines.append("- Structured fault list was not returned. See analysis narrative for detected codebase issues.")
    else:
        lines.append("- Not applicable for greenfield mode.")
    lines.append("")
    lines.append("### 3.2 Interaction Profile")
    lines.append("| Relationship | Count |")
    lines.append("|---|---:|")
    if rel_counts:
        for k, v in sorted(rel_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            lines.append(f"| {k} | {v} |")
    else:
        lines.append("| uses | 0 |")
    lines.append("")
    lines.append("## 4. Non-Functional Assessment")
    lines.append("| Attribute | Score | Visual |")
    lines.append("|---|---:|---|")
    lines.append(f"| Scalability | {scalability}/100 | `{_bar(scalability)}` |")
    lines.append(f"| Performance | {performance}/100 | `{_bar(performance)}` |")
    lines.append(f"| Maintainability | {maintainability}/100 | `{_bar(maintainability)}` |")
    lines.append(f"| Security | {security}/100 | `{_bar(security)}` |")
    lines.append("")
    lines.append("## 5. Component Functional Deep Dive")
    lines.append("### 5.1 Layer Assignment Rationale")
    lines.append("| Component | Layer | Why | Confidence |")
    lines.append("|---|---|---|---:|")
    if isinstance(layer_map, list) and layer_map:
        for item in layer_map[:40]:
            if not isinstance(item, dict):
                continue
            raw_layer = item.get("layer", "N/A")
            disp_layer = normalize_layer(raw_layer) or raw_layer
            lines.append(
                f"| {item.get('component', 'N/A')} | {disp_layer} | "
                f"{str(item.get('reason', 'N/A')).replace('|', '/')} | {int(item.get('confidence', 0) or 0)} |"
            )
    else:
        lines.append("| N/A | N/A | Agent did not return explicit layer rationale. | 0 |")
    lines.append("")
    lines.append("### 5.2 Component Responsibilities")
    lines.append("| Component | Detailed Functionality | Key Dependencies |")
    lines.append("|---|---|---|")
    if detail_rows:
        for name, func, deps in detail_rows:
            lines.append(f"| {name} | {func.replace('|', '/')} | {deps.replace('|', '/')} |")
    else:
        lines.append("| N/A | No component details were generated. | N/A |")
    lines.append("")
    lines.append("## 6. Key Decisions and Trade-offs")
    if decisions:
        for idx, d in enumerate(decisions[:8], start=1):
            lines.append(f"### 6.{idx} {d.get('decision', 'Decision')}")
            lines.append(f"- **Rationale:** {d.get('rationale', 'N/A')}")
            alts = d.get("alternatives") or []
            if alts:
                lines.append(f"- **Alternatives considered:** {', '.join([str(a) for a in alts[:5]])}")
            lines.append("")
    else:
        lines.append("- No structured decision log was returned by the agent.")
        lines.append("")
    lines.append("## 7. Risk Register and Mitigation Plan")
    lines.append("| Risk | Severity | Likelihood | Impact | Mitigation |")
    lines.append("|---|---|---|---|---|")
    if risks:
        for r in risks[:15]:
            lines.append(
                f"| {r.get('risk', 'N/A')} | {r.get('severity', 'N/A')} | {r.get('likelihood', 'N/A')} | "
                f"{str(r.get('impact', 'N/A')).replace('|', '/')} | {str(r.get('mitigation', 'N/A')).replace('|', '/')} |"
            )
    else:
        lines.append("| No explicit risks provided | - | - | - | Run a deeper scenario analysis |")
    lines.append("")
    lines.append("## 7A. Old vs New Architecture Comparison")
    lines.append("| Dimension | Current State | Proposed State | Benefit |")
    lines.append("|---|---|---|---|")
    if isinstance(old_new, list) and old_new:
        for c in old_new[:20]:
            if not isinstance(c, dict):
                continue
            lines.append(
                f"| {str(c.get('dimension', 'N/A')).replace('|', '/')} | "
                f"{str(c.get('current_state', 'N/A')).replace('|', '/')} | "
                f"{str(c.get('proposed_state', 'N/A')).replace('|', '/')} | "
                f"{str(c.get('benefit', 'N/A')).replace('|', '/')} |"
            )
    else:
        lines.append("| N/A | Comparison data not returned by agent. | N/A | N/A |")
    lines.append("")
    lines.append("## 7B. Expected Improvement Outcomes (Why it helps)")
    lines.append("| Metric | Current Baseline | Target Outcome | Why Improvement Happens |")
    lines.append("|---|---|---|---|")
    if isinstance(expected_improvements, list) and expected_improvements:
        for item in expected_improvements[:20]:
            if not isinstance(item, dict):
                continue
            lines.append(
                f"| {str(item.get('metric', 'N/A')).replace('|', '/')} | "
                f"{str(item.get('current_baseline', 'N/A')).replace('|', '/')} | "
                f"{str(item.get('target_outcome', 'N/A')).replace('|', '/')} | "
                f"{str(item.get('why_it_improves', 'N/A')).replace('|', '/')} |"
            )
    else:
        lines.append("| N/A | Baseline not provided | Outcome not provided | Explanation not provided |")
    lines.append("")
    lines.append("## 8. Evolution Roadmap")
    if roadmap:
        for idx, ph in enumerate(roadmap[:8], start=1):
            phase = str(ph.get("phase") or f"Phase {idx}")
            timeframe = str(ph.get("timeframe") or "TBD")
            lines.append(f"### 8.{idx} {phase} ({timeframe})")
            goals = [str(g).strip() for g in (ph.get("goals") or []) if str(g).strip()]
            deliverables = [str(d).strip() for d in (ph.get("deliverables") or []) if str(d).strip()]
            if goals:
                lines.append("- **Goals**")
                for g in goals[:8]:
                    lines.append(f"  - {g}")
            if deliverables:
                lines.append("- **Deliverables**")
                for d in deliverables[:8]:
                    lines.append(f"  - {d}")
            lines.append("")
    else:
        lines.append("- No structured roadmap provided. Use 30/60/90-day implementation planning.")
        lines.append("")
    lines.append("## 9. Detailed Narrative")
    lines.append("### 9.1 Analysis Narrative")
    lines.append(safe_analysis or "No analysis narrative available.")
    lines.append("")
    lines.append("### 9.2 Architecture Narrative")
    lines.append(safe_plan or "No architecture narrative available.")
    lines.append("")
    mermaid_block = _extract_mermaid_block(architecture_plan or "")
    lines.append("## 10. Mermaid Dependency Graph")
    if mermaid_block:
        lines.append(
            "The following diagram is copied from the architecture plan (same source as the in-app graph)."
        )
        lines.append("")
        lines.append(mermaid_block)
    else:
        lines.append(
            "_No fenced Mermaid block was found in the architecture plan. "
            "Regenerate the analysis or ensure the plan includes a ```mermaid ...``` section._"
        )
    lines.append("")
    lines.append("## 11. Appendix")
    lines.append("- Raw ```json``` results blocks are omitted from narratives above; structured tables reflect that content.")
    lines.append("- Use the in-app visualization tabs for interactive exploration and filtering.")
    return "\n".join(lines).strip()


def _ensure_brownfield_component_details(
    *,
    mods: Dict[str, Any],
    results: Dict[str, Any] | None,
    graph_data: Dict[str, Any],
    ast_summary_text: str,
    analysis_report: str,
    readme_text: str,
    past_memory: str,
) -> Dict[str, Any]:
    base = dict(results or {})
    existing = base.get("component_details") or []
    if isinstance(existing, list) and existing:
        return base
    labels = [str(n.get("label") or "").strip() for n in (graph_data.get("nodes") or []) if isinstance(n, dict)]
    labels = [x for x in labels if x][:40]
    if not labels:
        return base
    try:
        generated = mods["generate_brownfield_component_details"](
            ast_summary=ast_summary_text,
            analysis_report=analysis_report,
            node_labels=labels,
            readme_content=readme_text,
            past_memory=past_memory,
        )
        if generated:
            base["component_details"] = generated
    except Exception:
        # Keep pipeline resilient; fallback behavior remains in graph detail mapping.
        pass
    return base


def run_analysis(
    mode: str,
    user_input: str,
    *,
    project_name: str | None = None,
    scalability: int | None = None,
    performance: int | None = None,
    maintainability: int | None = None,
    security: int | None = None,
    expected_users: str | None = None,
    growth_rate: str | None = None,
) -> Dict[str, Any]:
    mode = mode.lower().strip()
    if mode not in {"greenfield", "brownfield"}:
        raise ValueError("mode must be 'greenfield' or 'brownfield'")

    # Build a structured NFR context block to inject into agent prompts
    nfr_lines: list[str] = []
    if project_name:
        nfr_lines.append(f"Project Name: {project_name}")
    if scalability is not None:
        nfr_lines.append(f"Scalability priority: {scalability}/100")
    if performance is not None:
        nfr_lines.append(f"Performance priority: {performance}/100")
    if maintainability is not None:
        nfr_lines.append(f"Maintainability priority: {maintainability}/100")
    if security is not None:
        nfr_lines.append(f"Security priority: {security}/100")
    if expected_users:
        nfr_lines.append(f"Expected users: {expected_users}")
    if growth_rate:
        nfr_lines.append(f"Monthly growth rate: {growth_rate}")
    nfr_context = "\n".join(nfr_lines)  # empty string if no NFR data provided

    warning = ""
    ast_summary_text = ""
    readme_text = ""
    input_payload = user_input
    graph_data = {"nodes": [], "edges": []}
    memory_used = "No past architectural memory found."

    try:
        mods = _imports()
        graph = _build_graph(mods)
    except Exception as exc:
        warning = f"Agent runtime unavailable: {exc}"
        if mode == "greenfield":
            return {
                "mode": mode,
                "analysis_report": "",
                "architecture_plan": _fallback_greenfield_plan(user_input),
                "ast_summary": "",
                "graph": graph_data,
                "memory_used": memory_used,
                "warning": warning,
            }
        return {
            "mode": mode,
            "analysis_report": _fallback_brownfield_report(user_input),
            "architecture_plan": _fallback_greenfield_plan("Refactor existing system with bounded contexts."),
            "ast_summary": "",
            "graph": graph_data,
            "memory_used": memory_used,
            "warning": warning,
        }

    if mode == "brownfield" and os.path.exists(user_input):
        readme_path = os.path.join(user_input, "README.md")
        if os.path.exists(readme_path):
            with open(readme_path, "r", encoding="utf-8") as rf:
                readme_text = rf.read()

        ast_summary_text = mods["generate_ast_summary"](user_input)
        input_payload = mods["read_codebase"](user_input) or user_input
        graph_data = mods["parse_ast_summary_to_graph"](ast_summary_text)

    search_query = input_payload if mode == "greenfield" else (ast_summary_text[:4000] or "Software architecture refactoring")
    try:
        memory_used = mods["retrieve_memory"](search_query)
    except Exception as exc:
        warning = f"Memory lookup failed: {exc}"

    result = graph.invoke(
        {
            "input": input_payload,
            "mode": mode,
            "readme_content": readme_text,
            "past_memory": memory_used,
            "ast_summary": ast_summary_text,
            "analysis_report": "",
            "architecture_plan": "",
            "nfr_context": nfr_context,
        }
    )

    architecture_plan = result.get("architecture_plan", "") or ""
    analysis_report = result.get("analysis_report", "") or ""
    structured_results = result.get("results") or {}
    if (not analysis_report.strip()) and structured_results:
        analysis_report = _results_to_analysis_report(structured_results)

    _snippet_src = input_payload if mode == "brownfield" else user_input
    _snippet = (_snippet_src or "").strip()
    if len(_snippet) > 12000:
        _snippet = _snippet[:12000]
    validation_corpus = "\n".join(
        [readme_text, ast_summary_text, nfr_context, _snippet]
    )
    if structured_results:
        structured_results, prune_note = _prune_ungrounded_component_details(
            structured_results,
            corpus=validation_corpus,
            ast_summary=ast_summary_text,
        )
        if prune_note:
            warning = (warning + " | " if warning else "") + prune_note

    if architecture_plan:
        # Always parse the LLM's refactored architecture graph instead of using the raw AST graph.
        # This ensures the visual nodes exactly match the component_details the agent generates!
        should_parse_plan = True
        if should_parse_plan:
            graph_data = mods["parse_mermaid_to_graph"](architecture_plan)
            if not (graph_data.get("nodes") or []):
                try:
                    from agents.graph_builder import parse_text_to_graph

                    graph_data = parse_text_to_graph(architecture_plan)
                except Exception as exc:
                    warning = (warning + " | " if warning else "") + f"Graph fallback failed: {exc}"

    if mode == "brownfield":
        structured_results = _ensure_brownfield_component_details(
            mods=mods,
            results=structured_results,
            graph_data=graph_data,
            ast_summary_text=ast_summary_text,
            analysis_report=analysis_report,
            readme_text=readme_text,
            past_memory=memory_used,
        )

    if structured_results:
        structured_results = reconcile_structured_layers(structured_results, graph_data)
        lr_note = structured_results.pop("_layer_reconcile_note", None)
        if isinstance(lr_note, str) and lr_note.strip():
            warning = (warning + " | " if warning else "") + lr_note.strip()

    graph_data = _apply_layer_assignments(graph_data, structured_results)
    graph_data = _apply_component_details(graph_data, structured_results, mode=mode)
    report_document = _build_detailed_report_document(
        mode=mode,
        analysis_report=analysis_report,
        architecture_plan=architecture_plan,
        graph_data=graph_data,
        results=structured_results,
        warning=warning,
    )

    return {
        "mode": mode,
        "analysis_report": analysis_report,
        "architecture_plan": architecture_plan,
        "ast_summary": ast_summary_text,
        "graph": graph_data,
        "memory_used": memory_used,
        "warning": warning,
        "results": structured_results,
        "report_document": report_document,
    }


def train_memory_from_path(path: str) -> Tuple[bool, str]:
    try:
        mods = _imports()
        mods["train_memory"](path)
        return True, "Training completed."
    except Exception as exc:
        return False, f"Training failed: {exc}"


def forget_memory_by_path(path: str) -> Tuple[bool, str]:
    try:
        mods = _imports()
        mods["forget_memory"](path)
        return True, "Memory deletion completed."
    except Exception as exc:
        return False, f"Memory deletion failed: {exc}"

