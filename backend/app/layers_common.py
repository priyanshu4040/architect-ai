"""Shared canonical layer names for architecture outputs (reports, graph, JSON)."""

from __future__ import annotations

import re
from typing import Any

CANONICAL_LAYERS = frozenset({"presentation", "business", "data", "infrastructure"})


def normalize_layer(value: Any) -> str | None:
    v = str(value or "").strip().lower()
    if not v:
        return None
    v = re.sub(r"[\s_-]+", " ", v).strip()
    aliases = {
        "presentation": "presentation",
        "ui": "presentation",
        "api": "presentation",
        "business": "business",
        "business logic": "business",
        "business_logic": "business",
        "logic": "business",
        "domain": "business",
        "service": "business",
        "application": "business",
        "data": "data",
        "data access": "data",
        "data access layer": "data",
        "data layer": "data",
        "datalayer": "data",
        "database": "data",
        "database layer": "data",
        "persistence": "data",
        "persistence layer": "data",
        "repository": "data",
        "repository layer": "data",
        "dal": "data",
        "dao": "data",
        "orm": "data",
        "data_access": "data",
        "infrastructure": "infrastructure",
        "infra": "infrastructure",
        "platform": "infrastructure",
        "integration": "infrastructure",
        "messaging": "infrastructure",
    }
    if v in aliases:
        return aliases[v]
    if any(
        tok in v
        for tok in (
            "data access",
            "data layer",
            "persistence",
            "repository",
            "database",
            "orm",
            " dao",
            "dal",
            "jdbc",
            "sql client",
            "entity framework",
            "prisma",
        )
    ):
        return "data"
    if any(tok in v for tok in ("presentation", "user interface", "frontend", "api gateway", "controller layer")):
        return "presentation"
    if any(tok in v for tok in ("infrastructure", "integration", "messaging", "queue", "observability", "logging")):
        return "infrastructure"
    if any(tok in v for tok in ("business", "domain", "application service", "use case")):
        return "business"
    return None
