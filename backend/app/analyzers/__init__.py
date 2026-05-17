"""Deterministic codebase analyzers (no LLM)."""

from .compact_context import build_brownfield_llm_context
from .tech_stack_scanner import scan_tech_stack, validate_source_project

__all__ = [
    "scan_tech_stack",
    "validate_source_project",
    "build_brownfield_llm_context",
]
