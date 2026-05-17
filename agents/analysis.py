"""
Architecture Analysis Agent — compact structured discovery (minimal narrative tokens).
"""

from agents.api_errors import ApiKeyError
from agents.llm_utils import (
    MAX_TOKENS_BROWNFIELD,
    MAX_TOKENS_GREENFIELD,
    MAX_TOKENS_NARRATIVE,
    get_llm,
    invoke_with_fallback,
    structured_invoke,
)
from agents.output_schemas import AnalysisInsightOutput
from agents.state import AgentState
from agents.utils import PROMPT_GROUNDING

BROWNFIELD_ANTI_HALLUCINATION = (
    "Use only technologies, modules, folders, and files found in detected_tech_stack, "
    "dependency_graph summary, folder_structure, key_files, detected_modules, or detected_apis. "
    "Do not mention frameworks, databases, services, or modules unless they appear there. "
    "If something is missing, say 'Not detected in uploaded codebase' instead of assuming."
)


def analysis_agent(state: AgentState) -> AgentState:
    mode = (state.get("mode") or "").strip().lower()
    nfr = (state.get("nfr_context") or "").strip()
    nfr_block = f"\nNFR priorities:\n{nfr}\n" if nfr else ""

    if mode == "brownfield":
        compact = (state.get("deep_brownfield_analysis") or "").strip()
        tech = (state.get("detected_tech_stack") or "").strip()
        readme = (state.get("readme_content") or "").strip()[:600]
        context = (
            "MODE: brownfield (existing codebase review)\n"
            f"README excerpt:\n{readme or 'none'}\n\n"
            f"DETECTED_TECH_STACK (deterministic, source of truth):\n{tech or 'none'}\n\n"
            f"COMPACT CODEBASE CONTEXT:\n{compact or 'none'}\n"
        )
        narrative_prompt = (
            "Brownfield software architecture reviewer. Analyze the EXISTING uploaded codebase only.\n"
            f"{BROWNFIELD_ANTI_HALLUCINATION}\n"
            f"{PROMPT_GROUNDING}\n"
            f"{context}{nfr_block}\n"
            "Focus on: actual stack, real modules, architecture risks, missing layers, refactoring priorities. "
            "Do NOT propose a greenfield stack from scratch. "
            "Write 8-12 evidence-based bullets; each must cite a path or manifest from the context.\n"
        )
        max_narr = MAX_TOKENS_BROWNFIELD
    else:
        req = (state.get("input") or "").strip()
        context = f"MODE: greenfield (new project from requirements)\nREQUIREMENTS:\n{req}\n{nfr_block}\n"
        narrative_prompt = (
            "Greenfield software architect. Design a NEW system from requirements only.\n"
            f"{PROMPT_GROUNDING}\n"
            f"{context}\n"
            "Extract domain, users, core features, data entities, constraints, NFR. "
            "Suggest modules and stack suited to THIS domain (not a generic template). "
            "Max 12 bullets.\n"
        )
        max_narr = MAX_TOKENS_NARRATIVE

    analysis_report = invoke_with_fallback(narrative_prompt, max_tokens=max_narr, label=mode)

    extract_prompt = (
        "Extract structured discovery JSON for THIS project only. Short strings in lists (max 8 each).\n"
        f"{context}\n\nBULLETS:\n{analysis_report[:3000]}\n"
    )
    if mode == "brownfield":
        extract_prompt += f"\n{BROWNFIELD_ANTI_HALLUCINATION}\n"

    insights: dict = {}
    try:
        llm = get_llm(max_tokens=MAX_TOKENS_GREENFIELD if mode == "greenfield" else MAX_TOKENS_BROWNFIELD)
        obj = structured_invoke(llm, AnalysisInsightOutput, extract_prompt, label=f"{mode}-insights")
        insights = obj.model_dump() if hasattr(obj, "model_dump") else obj.dict()
    except ApiKeyError:
        raise
    except Exception as exc:
        print(f"[Analysis Agent] Structured extraction failed: {exc}")

    return {
        "analysis_report": analysis_report,
        "analysis_insights": insights,
    }
