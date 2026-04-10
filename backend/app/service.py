import os
import sys
import json
import re
from pathlib import Path
from typing import Any, Dict, Tuple


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


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
    from agents.brownfield import code_agent
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


def _normalize_layer(value: Any) -> str | None:
    v = str(value or "").strip().lower()
    if not v:
        return None
    aliases = {
        "presentation": "presentation",
        "ui": "presentation",
        "api": "presentation",
        "business": "business",
        "business_logic": "business",
        "logic": "business",
        "domain": "business",
        "service": "business",
        "data": "data",
        "data_access": "data",
        "repository": "data",
        "persistence": "data",
        "infrastructure": "infrastructure",
        "infra": "infrastructure",
        "platform": "infrastructure",
    }
    return aliases.get(v)


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
        layer = _normalize_layer(item.get("layer"))
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


def _apply_component_details(graph_data: Dict[str, Any], results: Dict[str, Any] | None) -> Dict[str, Any]:
    if not graph_data or not isinstance(graph_data, dict):
        return graph_data

    details_by_component: Dict[str, str] = {}
    if isinstance(results, dict):
        component_details = results.get("component_details") or []
        if isinstance(component_details, list):
            for item in component_details:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("component") or "").strip().lower()
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
        key_label = label.lower()
        key_id = str(node.get("id") or "").strip().lower()
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


def run_analysis(mode: str, user_input: str) -> Dict[str, Any]:
    mode = mode.lower().strip()
    if mode not in {"greenfield", "brownfield"}:
        raise ValueError("mode must be 'greenfield' or 'brownfield'")

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
        }
    )

    architecture_plan = result.get("architecture_plan", "") or ""
    analysis_report = result.get("analysis_report", "") or ""
    structured_results = _extract_results_json(architecture_plan) or _extract_results_json(analysis_report)
    if (not analysis_report.strip()) and structured_results:
        analysis_report = _results_to_analysis_report(structured_results)
    if architecture_plan:
        # Prefer AST-derived graph in brownfield when we have it; otherwise, try to
        # derive a usable graph from the architecture plan Mermaid/text so the
        # frontend visualization never falls back to dummy data.
        should_parse_plan = mode == "greenfield" or not (graph_data.get("nodes") or [])
        if should_parse_plan:
            graph_data = mods["parse_mermaid_to_graph"](architecture_plan)
            if not (graph_data.get("nodes") or []):
                try:
                    from agents.graph_builder import parse_text_to_graph

                    graph_data = parse_text_to_graph(architecture_plan)
                except Exception as exc:
                    warning = (warning + " | " if warning else "") + f"Graph fallback failed: {exc}"

    graph_data = _apply_layer_assignments(graph_data, structured_results)
    graph_data = _apply_component_details(graph_data, structured_results)

    return {
        "mode": mode,
        "analysis_report": analysis_report,
        "architecture_plan": architecture_plan,
        "ast_summary": ast_summary_text,
        "graph": graph_data,
        "memory_used": memory_used,
        "warning": warning,
        "results": structured_results,
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

