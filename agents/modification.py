"""
Modification Agent — applies user change requests to an existing architecture output.
"""

from typing import Any, Dict

from agents.api_errors import ApiKeyError, classify_llm_error
from agents.llm_utils import get_llm, structured_invoke
from agents.output_schemas import ModifyArchitectureOutput


def modify_architecture(
    mode: str,
    current_architecture: Dict[str, Any],
    user_change_request: str,
) -> Dict[str, Any]:
    """
    Update architecture based on natural-language change request.
    Preserves unaffected sections where possible.
    """
    prompt = (
        "You are a principal software architect applying a targeted change to an existing architecture.\n\n"
        f"MODE: {mode}\n\n"
        f"CURRENT ARCHITECTURE (JSON):\n{current_architecture}\n\n"
        f"USER CHANGE REQUEST:\n{user_change_request}\n\n"
        "Rules:\n"
        "1. Update ONLY parts affected by the request; preserve other decisions.\n"
        "2. List each change in changes_applied (concise bullets).\n"
        "3. Explain reasoning per major change in reasoning.\n"
        "4. Fill impact_analysis for frontend, backend, database, security, deployment.\n"
        "5. updated_architecture must be the FULL updated JSON (merge greenfield structured_output "
        "or brownfield structured_output shape as appropriate).\n"
        "6. Be specific — no generic 'use best practices' without tying to the request.\n"
    )

    try:
        llm = get_llm()
        obj = structured_invoke(llm, ModifyArchitectureOutput, prompt)
        out = obj.model_dump() if hasattr(obj, "model_dump") else obj.dict()
    except ApiKeyError:
        raise
    except Exception as exc:
        classified = classify_llm_error(exc)
        if classified:
            raise classified from exc
        out = _fallback_modify(current_architecture, user_change_request, str(exc))
    return out


def _fallback_modify(
    current: Dict[str, Any],
    request: str,
    error: str,
) -> Dict[str, Any]:
    """Minimal deterministic fallback when LLM fails."""
    updated = dict(current)
    note = f"Applied note (LLM unavailable: {error}): {request}"
    changes = [f"Recorded change request: {request}"]
    if "structured_output" in current:
        so = dict(current.get("structured_output") or {})
        so["final_summary"] = (so.get("final_summary") or "") + " " + note
        updated["structured_output"] = so
    updated["is_fallback"] = True
    updated["warning"] = (
        (current.get("warning") or "")
        + " Modification used fallback — LLM update unavailable."
    ).strip()
    return {
        "updated_architecture": updated,
        "changes_applied": changes,
        "reasoning": ["LLM modification unavailable; merge manually or retry."],
        "impact_analysis": {
            "frontend_impact": "Review UI modules if stack changed.",
            "backend_impact": "Review API and service modules.",
            "database_impact": "Review schema and migrations if database changed.",
            "security_impact": "Re-evaluate auth model if authentication changed.",
            "deployment_impact": "Update CI/CD and infra if deployment changed.",
        },
        "final_summary": note[:500],
    }
