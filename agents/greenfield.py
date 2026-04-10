"""
Architecture Agent (Greenfield)
Takes requirements for a NEW system and returns an architecture plan.
"""

from langchain_community.chat_models import ChatOllama
from agents.state import AgentState
from pprint import pprint
import os
from dotenv import load_dotenv

load_dotenv()

# Instantly switch to Groq Cloud API if the key exists, otherwise use local Ollama
groq_api_key = os.getenv("GROQ_API_KEY")
if groq_api_key:
    from langchain_groq import ChatGroq
    llm = ChatGroq(model="llama-3.3-70b-versatile", groq_api_key=groq_api_key)
    print("[Greenfield] Using Groq Cloud API for Llama-3...")
else:
    from langchain_community.chat_models import ChatOllama
    llm = ChatOllama(model="llama3")
    print("[Greenfield] Using local Ollama for Llama-3...")

def architecture_agent(state: AgentState) -> AgentState:
    """
    Architecture Agent — takes requirements (Greenfield) 
    OR an existing code analysis report (Brownfield) 
    and returns a system architecture plan.
    """
    mode = state["mode"]
    if mode == "greenfield":
        print("\n[Architecture Agent] Designing from scratch (Greenfield)...")
        # In orchestrated mode, `analysis_report` is produced first by `analysis_agent`.
        analysis = (state.get("analysis_report") or "").strip()
        if analysis:
            context = f"Requirements:\n{state['input']}\n\nAnalysis Report:\n{analysis}"
        else:
            context = f"Requirements:\n{state['input']}"
    else:
        print("\n[Architecture Agent] Designing refactored architecture (Brownfield)...")
        context = f"Existing Codebase Analysis Report:\n{state['analysis_report']}\n\nExisting AST Structure:\n{state.get('ast_summary', '')}"

    past_memory = state.get("past_memory", "No past memory found.")

    brownfield_extra_keys = (
        "    \"current_codebase_faults\": [\n"
        "      {\n"
        "        \"fault\": \"string\",\n"
        "        \"severity\": \"high|medium|low\",\n"
        "        \"evidence\": \"string\",\n"
        "        \"impact\": \"string\"\n"
        "      }\n"
        "    ],\n"
        "    \"comparison_old_vs_new\": [\n"
        "      {\n"
        "        \"dimension\": \"string\",\n"
        "        \"current_state\": \"string\",\n"
        "        \"proposed_state\": \"string\",\n"
        "        \"benefit\": \"string\"\n"
        "      }\n"
        "    ],\n"
        "    \"expected_improvements\": [\n"
        "      {\n"
        "        \"metric\": \"maintainability|scalability|performance|security|delivery_speed\",\n"
        "        \"current_baseline\": \"string\",\n"
        "        \"target_outcome\": \"string\",\n"
        "        \"why_it_improves\": \"string\"\n"
        "      }\n"
        "    ],\n"
    ) if mode == "brownfield" else ""
    brownfield_rule = (
        "- For brownfield mode, include concrete current_codebase_faults, comparison_old_vs_new, and expected_improvements.\n"
        if mode == "brownfield"
        else ""
    )

    prompt = (
        "You are an expert software architect.\n\n"
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
        "5. Generate a Mermaid dependency graph using a fenced block: ```mermaid\\ngraph TD\\n...\\n```\n\n"
        "Then, at the very end, output a STRICT JSON block in this exact format (no trailing commas, no comments, no additional keys outside \"results\"):\n\n"
        "```json\n"
        "{\n"
        "  \"results\": {\n"
        f"{brownfield_extra_keys}"
        "    \"component_details\": [\n"
        "      {\n"
        "        \"component\": \"string\",\n"
        "        \"functionality\": \"2-4 sentence detailed responsibility and behavior\",\n"
        "        \"inputs\": [\"string\"],\n"
        "        \"outputs\": [\"string\"],\n"
        "        \"dependencies\": [\"string\"]\n"
        "      }\n"
        "    ],\n"
        "    \"component_layer_mapping\": [\n"
        "      {\n"
        "        \"component\": \"string\",\n"
        "        \"layer\": \"presentation|business|data|infrastructure\",\n"
        "        \"reason\": \"string\",\n"
        "        \"confidence\": 0\n"
        "      }\n"
        "    ],\n"
        "    \"recommended_patterns\": [\n"
        "      {\n"
        "        \"pattern\": \"string\",\n"
        "        \"why\": \"string\",\n"
        "        \"confidence\": 0,\n"
        "        \"tags\": [\"string\"]\n"
        "      }\n"
        "    ],\n"
        "    \"key_decisions\": [\n"
        "      {\n"
        "        \"decision\": \"string\",\n"
        "        \"rationale\": \"string\",\n"
        "        \"alternatives\": [\"string\"]\n"
        "      }\n"
        "    ],\n"
        "    \"risk_analysis\": [\n"
        "      {\n"
        "        \"risk\": \"string\",\n"
        "        \"severity\": \"high|medium|low\",\n"
        "        \"impact\": \"string\",\n"
        "        \"likelihood\": \"high|medium|low\",\n"
        "        \"mitigation\": \"string\"\n"
        "      }\n"
        "    ],\n"
        "    \"evolution_roadmap\": [\n"
        "      {\n"
        "        \"phase\": \"string\",\n"
        "        \"timeframe\": \"string\",\n"
        "        \"goals\": [\"string\"],\n"
        "        \"deliverables\": [\"string\"]\n"
        "      }\n"
        "    ],\n"
        "    \"indicators\": {\n"
        "      \"scalability\": 0,\n"
        "      \"performance\": 0,\n"
        "      \"maintainability\": 0,\n"
        "      \"security\": 0,\n"
        "      \"notes\": {\n"
        "        \"scalability\": \"string\",\n"
        "        \"performance\": \"string\",\n"
        "        \"maintainability\": \"string\",\n"
        "        \"security\": \"string\"\n"
        "      }\n"
        "    }\n"
        "  }\n"
        "}\n"
        "```\n\n"
        "Rules for JSON:\n"
        "- Use integers 0-100 for indicators and confidence.\n"
        f"{brownfield_rule}"
        "- component_details must include every major component from the decomposition and Mermaid graph.\n"
        "- functionality must be concrete and specific (avoid generic labels like 'handles logic').\n"
        "- component_layer_mapping must include every major component from the decomposition and Mermaid graph.\n"
        "- layer must be one of: presentation, business, data, infrastructure.\n"
        "- Provide 3-5 items per list where possible.\n"
        "- Keep strings concise and professional.\n\n"
        "Keep the rest of the answer structured, detailed, and concise.\n"
    )

    response = llm.invoke(prompt)
    print("\n[Architecture Agent] Plan generated.")
    return {"architecture_plan": (response.content or "").strip()}
