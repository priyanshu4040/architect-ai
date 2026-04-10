"""
Code Analysis Agent (Brownfield)
Takes existing code and returns issue detection with refactoring recommendations.
"""

from langchain_community.chat_models import ChatOllama
from agents.state import AgentState
import json
import re
import os
from dotenv import load_dotenv

load_dotenv()

# Instantly switch to Groq Cloud API if the key exists, otherwise use local Ollama
groq_api_key = os.getenv("GROQ_API_KEY")
if groq_api_key:
    from langchain_groq import ChatGroq
    llm = ChatGroq(model="llama-3.3-70b-versatile", groq_api_key=groq_api_key)
    print("[Brownfield] Using Groq Cloud API for Llama-3...")
else:
    from langchain_community.chat_models import ChatOllama
    llm = ChatOllama(model="llama3")
    print("[Brownfield] Using local Ollama for Llama-3...")

def code_agent(state: AgentState) -> AgentState:
    """
    Brownfield Agent — takes existing code or a code description
    and returns issue detection with refactoring recommendations.
    """
    print("\n[Code Analysis Agent] Reviewing existing code...")

    # Truncate sections to stay within Groq's free-tier token limit (~10k tokens max)
    ast_summary = (state.get('ast_summary') or '')[:4000]
    readme      = (state.get('readme_content') or '')[:1500]
    past_memory = (state.get('past_memory') or '')[:1500]

    prompt = f"""
You are a principal software architecture reviewer for brownfield modernization.

Analyze the following system:

--- PROJECT TOPIC / IDEA (README) ---
{readme or 'No README provided.'}

--- PAST ARCHITECTURAL KNOWLEDGE (Company Standard / RAG) ---
{past_memory or 'No past memory found.'}

--- AST STRUCTURAL GRAPH (Dependencies & Classes) ---
{ast_summary or 'No structural graph available.'}

NOTE: The raw source code is intentionally omitted to stay within token limits.
Rely on the AST graph above for structural analysis.

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


def generate_brownfield_component_details(
    *,
    ast_summary: str,
    analysis_report: str,
    node_labels: list[str],
    readme_content: str = "",
    past_memory: str = "",
) -> list[dict]:
    """
    Generate component functionality details for brownfield mode from AST + analysis.
    Returns a list shaped like:
      [{component, functionality, inputs, outputs, dependencies}, ...]
    """
    labels = [str(x).strip() for x in (node_labels or []) if str(x).strip()][:40]
    if not labels:
        return []

    label_block = "\n".join([f"- {x}" for x in labels])
    prompt = f"""
You are a principal software architect.
Generate precise component functionality details for an EXISTING brownfield codebase.

--- README / project context ---
{(readme_content or "No README provided.")[:1800]}

--- Existing architecture/code analysis ---
{(analysis_report or "No analysis report provided.")[:6000]}

--- AST structural summary ---
{(ast_summary or "No AST summary provided.")[:6000]}

--- Target components to describe ---
{label_block}

--- Past architectural standards ---
{(past_memory or "No past memory found.")[:1500]}

Output STRICT JSON only (no markdown fences, no extra text):
{{
  "component_details": [
    {{
      "component": "string (must match one of target component names)",
      "functionality": "2-4 sentence concrete behavior/responsibility for the EXISTING system",
      "inputs": ["string"],
      "outputs": ["string"],
      "dependencies": ["string"]
    }}
  ]
}}

Rules:
- Cover as many target components as possible.
- Be concrete; do not use generic filler.
- If unsure, infer from naming + AST relations and state likely behavior.
"""
    response = llm.invoke(prompt)
    raw = (response.content or "").strip()
    try:
        obj = json.loads(raw)
    except Exception:
        m = re.search(r"\{[\s\S]*\}", raw)
        if not m:
            return []
        try:
            obj = json.loads(m.group(0))
        except Exception:
            return []

    details = obj.get("component_details") if isinstance(obj, dict) else None
    if not isinstance(details, list):
        return []

    out: list[dict] = []
    allowed = {x.lower() for x in labels}
    for item in details:
        if not isinstance(item, dict):
            continue
        name = str(item.get("component") or "").strip()
        if not name:
            continue
        if name.lower() not in allowed:
            continue
        functionality = str(item.get("functionality") or "").strip()
        inputs = [str(x).strip() for x in (item.get("inputs") or []) if str(x).strip()]
        outputs = [str(x).strip() for x in (item.get("outputs") or []) if str(x).strip()]
        dependencies = [str(x).strip() for x in (item.get("dependencies") or []) if str(x).strip()]
        out.append(
            {
                "component": name,
                "functionality": functionality,
                "inputs": inputs[:8],
                "outputs": outputs[:8],
                "dependencies": dependencies[:8],
            }
        )
    return out
