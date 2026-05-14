from agents.state import AgentState
from agents.utils import PROMPT_GROUNDING
from agents.schemas import ArchitectureOutput
import os
from dotenv import load_dotenv

load_dotenv()

from langchain_groq import ChatGroq


def _get_llm() -> ChatGroq:
    """Read key fresh from env at call time so .env changes + key rotation work."""
    keys = [
        os.getenv("GROQ_API_KEY"),
        os.getenv("GROQ_API_KEY1"),
        os.getenv("GROQ_API_KEY2"),
    ]
    key = next((k for k in keys if k), None)
    if not key:
        raise ValueError("No GROQ_API_KEY configured in environment.")
    return ChatGroq(model="llama-3.3-70b-versatile", groq_api_key=key)


def _invoke_with_fallback(prompt: str) -> str:
    """Try each configured Groq key in order; skip on 429 rate-limit."""
    keys = [
        k for k in [
            os.getenv("GROQ_API_KEY"),
            os.getenv("GROQ_API_KEY1"),
            os.getenv("GROQ_API_KEY2"),
        ] if k
    ]
    if not keys:
        raise ValueError("No GROQ_API_KEY configured in environment.")
    last_err = None
    for key in keys:
        try:
            llm = ChatGroq(model="llama-3.3-70b-versatile", groq_api_key=key)
            return (llm.invoke(prompt).content or "").strip()
        except Exception as e:
            if "429" in str(e) or "rate_limit" in str(e).lower():
                last_err = e
                continue
            raise
    raise last_err


def architecture_agent(state: AgentState) -> AgentState:
    """
    Architecture Agent — takes requirements (Greenfield) 
    OR an existing code analysis report (Brownfield) 
    and returns a system architecture plan.
    """
    mode = state["mode"]
    nfr = (state.get("nfr_context") or "").strip()
    nfr_block = (
        f"\n--- Non-functional priorities (user-specified) ---\n{nfr}\n"
        if nfr
        else ""
    )
    if mode == "greenfield":
        print("\n[Architecture Agent] Designing from scratch (Greenfield)...")
        analysis = (state.get("analysis_report") or "").strip()
        if analysis:
            context = (
                f"Requirements:\n{state['input']}\n{nfr_block}\nAnalysis Report:\n{analysis}"
            )
        else:
            context = f"Requirements:\n{state['input']}{nfr_block}"
    else:
        print("\n[Architecture Agent] Designing refactored architecture (Brownfield)...")
        ast = (state.get("ast_summary") or "").strip()
        context = (
            f"Existing Codebase Analysis Report:\n{state.get('analysis_report', '')}\n\n"
            f"Existing AST Structure:\n{ast}\n"
            f"{nfr_block}"
        )

    past_memory = state.get("past_memory", "No past memory found.")

    prompt_narrative = (
        "You are an expert software architect.\n\n"
        f"{PROMPT_GROUNDING}\n"
        "Based on the following context, build or refactor the architecture.\n\n"
        f"{context}\n\n"
        "--- PAST ARCHITECTURAL KNOWLEDGE (RAG Memory) ---\n"
        f"{past_memory}\n"
        "-------------------------------------------------\n\n"
        "STRICT ARCHITECTURE RULES — follow every rule exactly:\n"
        "1. Decompose the architecture into EXACTLY FOUR layers: Presentation, Business, Data, Infrastructure.\n"
        "2. Each layer MUST contain AT LEAST TWO named components/classes. Aim for 3-5 per layer for a realistic architecture.\n"
        "3. Do NOT skip or merge layers. All four MUST appear in the output even if the codebase is minimal.\n"
        "4. Infrastructure layer is MANDATORY and must include cross-cutting concerns such as:\n"
        "   - AppConfig / ConfigLoader (application configuration management)\n"
        "   - LoggingService / Logger (centralised logging)\n"
        "   - ExternalApiClient / HttpClient (outbound HTTP calls to third-party services)\n"
        "   - MessageQueue / EventBus (async messaging) — if relevant\n"
        "   - EmailService / NotificationService — if relevant\n"
        "   Pick the two most relevant ones for this system and name them concretely.\n"
        "5. For brownfield mode: use ONLY real class/module names from the AST. If a layer has fewer than 2 real classes,\n"
        "   add the minimum number of GENERAL placeholder classes needed (e.g. 'AppConfig', 'LoggingService')\n"
        "   and clearly label them as '(placeholder — not in source)'.\n"
        "   DO NOT invent fake classes that appear to come from the actual codebase.\n"
        "6. For each component: state its exact class name, which layer it belongs to, and its key responsibility (1-2 sentences).\n"
        "7. Describe inter-layer connections (API calls, composition, events, inheritance) and suggest design patterns.\n"
        "8. Generate a Mermaid dependency graph using a fenced block: ```mermaid\ngraph TD\n...\n```\n"
        "   IMPORTANT: Group nodes using Mermaid subgraph blocks named exactly after each layer:\n"
        "     subgraph Presentation ... end\n"
        "     subgraph Business ... end\n"
        "     subgraph Data ... end\n"
        "     subgraph Infrastructure ... end\n"
        "   Every component MUST appear inside the correct subgraph. All four subgraphs MUST be present.\n\n"
        "Keep the answer structured and concise. Do NOT output a JSON array."
    )

    response_narrative = llm.invoke(prompt_narrative)
    architecture_plan = (response_narrative.content or "").strip()
    print("\n[Architecture Agent] Plan generated. Extracting structured metrics...")

    structured_llm = llm.with_structured_output(ArchitectureOutput)
    
    brownfield_rule = (
        "- For brownfield mode, include concrete current_codebase_faults, comparison_old_vs_new, and expected_improvements.\n"
        if mode == "brownfield"
        else ""
    )

    prompt_json = (
        "You are a strict data extractor for software architecture. "
        "Based on the architecture plan generated below, extract the components, decisions, and risks into structured data.\n\n"
        f"--- CONTEXT ---\n{context}\n\n"
        f"--- ARCHITECTURE PLAN ---\n{architecture_plan}\n\n"
        "Rules:\n"
        "- Use integers 0-100 for indicators and confidence.\n"
        f"{brownfield_rule}"
        "- component_details must include every component listed in the architecture plan and Mermaid graph.\n"
        "- functionality CANNOT be empty or generic. Provide a concrete 2-4 sentence description of each component's responsibility.\n"
        "- component_layer_mapping must have ONE entry per component in component_details.\n"
        "- Every component MUST be placed in one of: 'Presentation', 'Business', 'Data', 'Infrastructure'. No other layer names allowed.\n"
        "- EVERY layer MUST have AT LEAST TWO components mapped to it. If the plan only produced one component for a layer,\n"
        "  add a second sensible general component (e.g. 'AppConfig' for Infrastructure, 'BaseRepository' for Data)\n"
        "  and mark its functionality as 'General placeholder to satisfy minimum layer coverage'.\n"
        "- Infrastructure layer MUST contain at least two of: AppConfig, LoggingService, HttpClient, MessageQueue, EmailService, CacheManager, or similar cross-cutting concerns.\n"
        "- Keep strings concise and professional.\n"
    )

    try:
        results_obj = structured_llm.invoke(prompt_json)
        results = results_obj.model_dump() if hasattr(results_obj, "model_dump") else results_obj.dict()
    except Exception as e:
        print(f"[Architecture Agent] Warning: Structured extraction failed: {e}")
        results = {}

    return {"architecture_plan": architecture_plan, "results": results}
