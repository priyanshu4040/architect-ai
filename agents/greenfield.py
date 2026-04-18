"""
Architecture Agent (Greenfield)
Takes requirements for a NEW system and returns an architecture plan.
"""

from agents.state import AgentState
from agents.utils import PROMPT_GROUNDING
from agents.schemas import ArchitectureOutput
import os
from dotenv import load_dotenv

load_dotenv()

groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    raise ValueError("GROQ_API_KEY is not set in environment.")

from langchain_groq import ChatGroq
llm = ChatGroq(model="llama-3.3-70b-versatile", groq_api_key=groq_api_key)
print("[Greenfield] Using Groq Cloud API for Llama-3...")

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
        "Do the following:\n"
        "1. Provide a highly detailed modular decomposition grouped by Topic/Business Domain.\n"
        "2. For each Topic/Module, list the exact class/component names to be built.\n"
        "3. Describe how components connect (API calls, composition, events, inheritance).\n"
        "4. Suggest key design patterns for those relationships.\n"
        "5. Generate a Mermaid dependency graph using a fenced block: ```mermaid\\ngraph TD\\n...\\n```\n"
        "   Use descriptive node labels (e.g. UserController, OrderService, OrderRepository, PostgresDB). "
        "Include at least one clear data/persistence component (Repository, DAO, ORM, or Database client) "
        "connected to the business layer.\n\n"
        "Keep the answer structured, detailed, and concise. Do NOT generate a JSON array."
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
        "- component_details must include every major component from the decomposition and Mermaid graph.\n"
        "- functionality CANNOT be empty or generic. You MUST provide a concrete 2-4 sentence description for each component's behavior/responsibility for both new AND existing components.\n"
        "- component_layer_mapping must include ONE entry per component in component_details.\n"
        "- You may use the standard architectural layers (presentation, business, data, infrastructure) OR create additional contextual layers (e.g., shared, external, worker) if needed to accurately model the refactored architecture.\n"
        "- Keep strings concise and professional.\n"
    )

    try:
        results_obj = structured_llm.invoke(prompt_json)
        results = results_obj.model_dump() if hasattr(results_obj, "model_dump") else results_obj.dict()
    except Exception as e:
        print(f"[Architecture Agent] Warning: Structured extraction failed: {e}")
        results = {}

    return {"architecture_plan": architecture_plan, "results": results}
