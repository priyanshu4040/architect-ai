"""
Deterministic repair of component_layer_mapping so layers stay consistent with
component names and common four-layer coverage (presentation / business / data / infrastructure).
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any, Dict, List, Tuple

from .layers_common import CANONICAL_LAYERS, normalize_layer

Layer = str


def _name_layer_scores(name: str) -> Dict[Layer, float]:
    """Soft scores from naming — used to nudge or override obviously wrong LLM labels."""
    l = (name or "").strip().lower()
    s: Dict[Layer, float] = {k: 0.0 for k in ("presentation", "business", "data", "infrastructure")}

    pres = (
        "controller",
        "router",
        "handler",
        "viewmodel",
        "view",
        "page",
        "screen",
        "widget",
        "bff",
        "graphql",
        "grpc",
        "endpoint",
        "mvc",
        "restapi",
        "rest api",
        "servlet",
        "filter",  # often HTTP — weak alone
        "middleware",
        "gateway",  # API gateway vs message gateway — boost presentation slightly
    )
    for kw in pres:
        if kw in l:
            s["presentation"] += 3.0 if kw in ("controller", "router", "handler", "viewmodel", "bff") else 1.8
    if l.endswith("controller") or l.endswith("router") or l.endswith("handler"):
        s["presentation"] += 3.5
    if "api" in l and any(x in l for x in ("controller", "router", "handler", "gateway", "bff")):
        s["presentation"] += 2.0

    data_kw = (
        ("repository", 5.0),
        ("repositories", 5.0),
        ("repo", 3.5),
        ("dao", 5.0),
        ("dal", 5.0),
        ("orm", 4.5),
        ("dbcontext", 5.0),
        ("persistence", 4.0),
        ("database", 3.5),
        ("datastore", 4.0),
        ("jdbc", 3.5),
        ("prisma", 4.0),
        ("dapper", 4.0),
        ("entityframework", 4.5),
        ("unitofwork", 4.0),
        ("mongo", 3.5),
        ("postgres", 3.5),
        ("redis", 3.0),
        ("migrations", 3.0),
        ("sqlserver", 3.5),
        ("schema", 2.0),
    )
    for kw, wt in data_kw:
        if kw in l:
            s["data"] += wt
    if "entity" in l and any(x in l for x in ("db", "sql", "persist", "orm", "context")):
        s["data"] += 2.5

    infra_kw = (
        ("kafka", 4.0),
        ("rabbit", 4.0),
        ("sqs", 4.0),
        ("sns", 4.0),
        ("s3", 3.5),
        ("blob", 3.0),
        ("smtp", 3.5),
        ("mailer", 3.5),
        ("sendgrid", 3.5),
        ("messagebus", 3.5),
        ("eventbridge", 3.5),
        ("vault", 3.0),
        ("secrets", 2.5),
        ("telemetry", 3.0),
        ("observability", 3.0),
        ("httpclient", 3.0),
        ("external", 2.0),
        ("adapter", 2.2),  # hexagonal outbound — often infra
        ("consumer", 2.5),
        ("producer", 2.5),
    )
    for kw, wt in infra_kw:
        if kw in l:
            s["infrastructure"] += wt
    if re.search(r"\bclient\b", l) and s["presentation"] < 4 and "controller" not in l:
        s["infrastructure"] += 1.5

    bus_kw = (
        "service",
        "usecase",
        "use case",
        "domain",
        "policy",
        "workflow",
        "saga",
        "aggregate",
        "factory",
        "manager",
        "processor",
        "engine",
        "calculator",
        "validator",
        "orchestrator",
    )
    for kw in bus_kw:
        if kw in l:
            s["business"] += 2.0

    return s


def _resolve_layer(name: str, model_layer: str | None) -> Tuple[Layer, bool]:
    """
    Returns (canonical_layer, was_changed_from_model).
    model_layer must already be normalized to a canonical value or None.
    """
    s = _name_layer_scores(name)
    ranked = sorted(s.keys(), key=lambda k: s[k], reverse=True)
    best = ranked[0]
    second = ranked[1]
    spread = s[best] - s[second]

    norm: Layer = model_layer if model_layer in CANONICAL_LAYERS else "business"

    # Strong name signal wins
    if s[best] >= 6.0:
        return (best, best != norm)
    if s[best] >= 4.0 and spread >= 2.0:
        return (best, best != norm)
    # Common LLM mistake: everything tagged "business"
    if norm == "business" and s[best] >= 2.8 and best != "business":
        return (best, True)

    # Wrong layer vs strong opposite signal
    if norm == "data" and s["presentation"] >= 5.0 and s["data"] < 3.0:
        return ("presentation", True)
    if norm == "presentation" and s["data"] >= 5.5 and s["presentation"] < 2.5:
        return ("data", True)
    if norm == "business" and s["data"] >= 5.0 and s["business"] <= s["data"] - 1.0:
        return ("data", True)
    if norm == "business" and s["presentation"] >= 5.0 and s["business"] <= s["presentation"] - 1.0:
        return ("presentation", True)

    # Keep model when it matches a competitive score
    if s[norm] + 0.25 >= s[best] and norm in CANONICAL_LAYERS:
        return (norm, False)

    return (norm, False)


def _canonical_component_names(
    results: Dict[str, Any],
    graph_data: Dict[str, Any] | None,
) -> List[str]:
    """Stable ordered unique component names (prefer component_details order)."""
    seen: Dict[str, str] = {}

    details = results.get("component_details") or []
    if isinstance(details, list):
        for item in details:
            if not isinstance(item, dict):
                continue
            c = str(item.get("component") or "").strip()
            if not c:
                continue
            seen.setdefault(c.lower(), c)

    mapping = results.get("component_layer_mapping") or []
    if isinstance(mapping, list):
        for item in mapping:
            if not isinstance(item, dict):
                continue
            c = str(item.get("component") or "").strip()
            if not c:
                continue
            seen.setdefault(c.lower(), c)

    nodes = (graph_data or {}).get("nodes") or []
    if isinstance(nodes, list):
        for n in nodes:
            if not isinstance(n, dict):
                continue
            label = str(n.get("label") or "").strip()
            nid = str(n.get("id") or "").strip()
            for c in (label, nid):
                if not c or len(c) < 2:
                    continue
                if len(c) == 1 and c.isalpha():
                    continue
                seen.setdefault(c.lower(), c)

    return list(seen.values())


def reconcile_structured_layers(
    results: Dict[str, Any] | None,
    graph_data: Dict[str, Any] | None,
) -> Dict[str, Any] | None:
    """
    Normalize layers, fix cross-layer mis-tags from naming signals, ensure each
    listed component has a mapping row, and nudge coverage so empty layers are
    filled when there are enough components (>= 5) to justify four layers.
    """
    if not results or not isinstance(results, dict):
        return results

    out = dict(results)
    names = _canonical_component_names(out, graph_data)
    if not names:
        return out  # nothing to reconcile; keep agent mapping as-is

    existing: Dict[str, Dict[str, Any]] = {}
    raw_mapping = out.get("component_layer_mapping")
    if isinstance(raw_mapping, list):
        for item in raw_mapping:
            if not isinstance(item, dict):
                continue
            c = str(item.get("component") or "").strip()
            if not c:
                continue
            existing[c.lower()] = dict(item)

    new_rows: List[Dict[str, Any]] = []
    touched = 0

    for name in names:
        row = existing.get(name.lower(), {})
        model_raw = row.get("layer")
        model_norm = normalize_layer(model_raw)
        resolved, changed = _resolve_layer(name, model_norm)
        if changed:
            touched += 1

        reason = str(row.get("reason") or "").strip()
        if changed:
            extra = "Layer aligned with naming conventions (repository/controller/client patterns)."
            reason = f"{reason.rstrip('.')}. {extra}".strip() if reason else extra

        conf = row.get("confidence")
        try:
            conf_int = int(conf) if conf is not None else (70 if changed else 60)
        except Exception:
            conf_int = 70 if changed else 60

        new_rows.append(
            {
                "component": name,
                "layer": resolved,
                "reason": reason or "Architectural layer assignment.",
                "confidence": min(100, max(0, conf_int)),
            }
        )

    # The UI now allows dynamic layers and does not aggressively force layers to fill 4 columns.
    # We trust the agent's architectural assignment over name-based heuristics.

    out["component_layer_mapping"] = new_rows
    if touched:
        out["_layer_reconcile_note"] = (
            f"Adjusted {touched} layer assignment(s) for naming consistency and four-layer coverage."
        )
    return out
