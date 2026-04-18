"""
Code Analysis Agent (Brownfield)
Takes existing code and returns issue detection with refactoring recommendations.
"""

import os
from dotenv import load_dotenv

from agents.state import AgentState
from agents.utils import PROMPT_GROUNDING

load_dotenv()

groq_api_key = os.getenv("GROQ_API_KEY1")
if not groq_api_key:
    raise ValueError("GROQ_API_KEY is not set in environment.")

from langchain_groq import ChatGroq
llm = ChatGroq(model="llama-3.3-70b-versatile", groq_api_key=groq_api_key)
print("[Brownfield] Using Groq Cloud API for Llama-3...")

def code_agent(state: AgentState) -> AgentState:
    """
    Brownfield Agent — takes existing code or a code description
    and returns issue detection with refactoring recommendations.
    """
    print("\n[Code Analysis Agent] Reviewing existing code...")

    # Pass full strings, utilizing the 128k context limits of modern instances
    ast_summary = state.get('ast_summary') or ''
    readme      = state.get('readme_content') or ''
    past_memory = state.get('past_memory') or ''

    prompt = f"""
You are a principal software architecture reviewer for brownfield modernization.

{PROMPT_GROUNDING}

Analyze the following system:

--- PROJECT TOPIC / IDEA (README) ---
{readme or 'No README provided.'}

--- PAST ARCHITECTURAL KNOWLEDGE (Company Standard / RAG) ---
{past_memory or 'No past memory found.'}

--- AST STRUCTURAL GRAPH (Dependencies & Classes) ---
{ast_summary or 'No structural graph available.'}

NOTE: The raw source code is intentionally omitted. Rely on the AST graph above for structural analysis.

Do the following:
1. Identify architectural issues from the AST graph (circular dependencies, tight coupling, etc.).
2. Detect poor modularization or separation of concerns.
3. Suggest concrete improvements referencing specific classes or imports from the graph.
4. Recommend a better architecture if needed.
5. Prioritize issues by severity: High / Medium / Low.

Output format (strictly use these sections):
## Current Codebase Snapshot
- 4-8 bullets about observed structure and dependency style.

## Faults in Current Codebase
- List concrete faults as bullets with: fault, evidence from AST/readme, impact.
- Use severity labels: High / Medium / Low.

## Root Cause Analysis
- Explain why the faults exist (module boundaries, layering violations, coupling patterns, etc.)

## Refactoring and Modernization Strategy
- List improvements mapped to affected modules/components.
- Include migration safety considerations and sequencing.

## Expected Improvements (Why this helps)
- Explain measurable gains in maintainability, scalability, performance, security, and delivery speed.

## Old vs New Architecture Comparison
| Area | Current State | Proposed State | Expected Benefit |
|---|---|---|---|

Keep answer highly concrete, technical, and actionable. Avoid generic statements.
"""

    response = llm.invoke(prompt)
    print("\n[Code Analysis Agent] Analysis complete.")
    return {"analysis_report": response.content}


def generate_brownfield_component_details(*args, **kwargs) -> list[dict]:
    # Deprecated: native json structure extraction is handled by structured output in greenfield.py
    return []
