"""
Planning Agent — greenfield design and brownfield evolution (token-optimized prompts).
"""

from agents.api_errors import ApiKeyError
from agents.llm_utils import (
    MAX_TOKENS_BROWNFIELD,
    MAX_TOKENS_GREENFIELD,
    MAX_TOKENS_NARRATIVE,
    MAX_TOKENS_STRUCTURED,
    get_llm,
    invoke_with_fallback,
    structured_invoke,
)
from agents.output_schemas import (
    BrownfieldLlmEnrichment,
    GreenfieldStructuredOutput,
)
from agents.schemas import ArchitectureOutput
from agents.analysis import BROWNFIELD_ANTI_HALLUCINATION
from agents.state import AgentState
from agents.utils import PROMPT_GROUNDING


def architecture_agent(state: AgentState) -> AgentState:
    mode = state["mode"]
    nfr = (state.get("nfr_context") or "").strip()
    nfr_block = f"\nNFR:\n{nfr}\n" if nfr else ""
    insights = state.get("analysis_insights") or {}
    insights_block = f"\nInsights:\n{insights}\n" if insights else ""

    if mode == "greenfield":
        print("\n[Planning Agent] Greenfield architecture...")
        analysis = (state.get("analysis_report") or "").strip()[:2000]
        context = f"Requirements:\n{state['input'][:4000]}\n{nfr_block}\nAnalysis:\n{analysis}\n{insights_block}"
        narrative_prompt = (
            "Senior web application architect. Architecture for the given requirements only.\n"
            f"{PROMPT_GROUNDING}\n"
            "Every module, API, entity must relate to the project domain. "
            "State assumptions briefly. Include ```mermaid graph with subgraphs "
            "Presentation, Business, Data, Infrastructure (2-4 components each).\n"
            f"{context}\n"
        )
        max_narr = MAX_TOKENS_GREENFIELD
    else:
        print("\n[Planning Agent] Brownfield evolution plan...")
        compact = (state.get("deep_brownfield_analysis") or "").strip()
        tech = (state.get("detected_tech_stack") or "").strip()
        analysis = (state.get("analysis_report") or "").strip()[:1500]
        context = (
            f"DETECTED_TECH_STACK:\n{tech}\n\n"
            f"COMPACT CODEBASE CONTEXT:\n{compact}\n\n"
            f"REVIEW FINDINGS:\n{analysis}\n{nfr_block}{insights_block}"
        )
        narrative_prompt = (
            "Brownfield evolution architect. Improve the EXISTING codebase; do not redesign as greenfield.\n"
            f"{BROWNFIELD_ANTI_HALLUCINATION}\n"
            f"{PROMPT_GROUNDING}\n"
            f"{context}\n"
            "Output: codebase risks, missing layers, refactoring steps, evolution plan. "
            "Mermaid ``` for current→target (mark '(suggested)' if not in ZIP).\n"
        )
        max_narr = MAX_TOKENS_BROWNFIELD

    architecture_plan = invoke_with_fallback(narrative_prompt, max_tokens=max_narr, label=f"{mode}-plan")

    brownfield_rule = (
        "- Issues must cite evidence paths from the compact summary.\n"
        "- detected_modules in JSON must match parser list only; new names -> suggested_modules.\n"
        if mode == "brownfield"
        else ""
    )

    prompt_arch_output = (
        "Extract structured metrics from plan. Concise fields only.\n"
        f"{context[:3500]}\n\nPLAN:\n{architecture_plan[:3500]}\n"
        f"Rules:\n{brownfield_rule}"
        "- component_details: 2 sentences max each.\n"
    )

    results: dict = {}
    try:
        llm = get_llm(max_tokens=MAX_TOKENS_STRUCTURED)
        obj = structured_invoke(llm, ArchitectureOutput, prompt_arch_output, label=f"{mode}-arch")
        results = obj.model_dump() if hasattr(obj, "model_dump") else obj.dict()
    except ApiKeyError:
        raise
    except Exception as e:
        print(f"[Planning Agent] ArchitectureOutput extraction failed: {e}")

    structured_output: dict = {}
    if mode == "greenfield":
        prompt_gf = (
            "Generate greenfield JSON for THIS project only. "
            "modules/api_suggestions/database_entities must match domain (max 8 each). "
            "List assumptions[]. No generic reusable architecture.\n"
            f"{context[:3500]}\n\nPLAN:\n{architecture_plan[:2500]}\n"
        )
        schema = GreenfieldStructuredOutput
        max_struct = MAX_TOKENS_GREENFIELD
    else:
        prompt_gf = (
            "Brownfield evolution JSON. Do NOT include detected_modules, detected_apis, or tech stack "
            "(scanner provides those). Fill: project_summary, suggested_modules, issues, evolution_plan, "
            "final_summary. Max 8 items per list.\n"
            f"{BROWNFIELD_ANTI_HALLUCINATION}\n"
            f"{context[:5000]}\n\nPLAN:\n{architecture_plan[:2000]}\n"
        )
        schema = BrownfieldLlmEnrichment
        max_struct = MAX_TOKENS_BROWNFIELD

    try:
        llm = get_llm(max_tokens=max_struct)
        sobj = structured_invoke(llm, schema, prompt_gf, label=f"{mode}-structured")
        structured_output = (
            sobj.model_dump() if hasattr(sobj, "model_dump") else sobj.dict()
        )
    except ApiKeyError:
        raise
    except Exception as e:
        print(f"[Planning Agent] Mode structured output failed: {e}")

    return {
        "architecture_plan": architecture_plan,
        "results": results,
        "structured_output": structured_output,
    }
