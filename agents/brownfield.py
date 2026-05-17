"""
Code Analysis Agent (Brownfield) — first pass before Analysis Agent.
"""

from agents.llm_utils import invoke_with_fallback
from agents.state import AgentState
from agents.utils import PROMPT_GROUNDING


def code_agent(state: AgentState) -> AgentState:
    print("\n[Code Analysis Agent] Reviewing existing codebase structure...")

    ast_summary = state.get("ast_summary") or ""
    readme = state.get("readme_content") or ""
    inventory = state.get("project_inventory") or ""
    deep = state.get("deep_brownfield_analysis") or ""
    past_memory = state.get("past_memory") or ""
    nfr = (state.get("nfr_context") or "").strip()

    prompt = f"""
You are a principal software architect reviewing an EXISTING codebase for modernization.

{PROMPT_GROUNDING}

--- README (product context) ---
{readme or "No README provided."}

--- PROJECT INVENTORY (manifests, folders, route hints) ---
{inventory or "No inventory available."}

--- DEEP STATIC ANALYSIS (structure, stack, routes, security) ---
{deep or "No deep analysis."}

--- AST STRUCTURAL GRAPH ---
{ast_summary or "No AST available."}

--- USER NFR PRIORITIES ---
{nfr or "Not specified."}

--- PAST ARCHITECTURAL KNOWLEDGE ---
{past_memory or "None."}

Raw source is omitted intentionally; use inventory + AST as evidence.

Deliver a technical findings document with these sections:

## Project Type and Stack
- Infer project type (SPA, API, monolith, microservices, etc.) from inventory/AST.
- List detected technologies with evidence.

## Folder and Module Structure
- Describe how code is organized; call out missing layers (domain, infra, tests).

## APIs and Routes
- List likely API surfaces from route file hints and controller/handler classes in AST.

## Dependencies and Coupling
- Note heavy imports, circular patterns, or god-modules if visible in AST.

## Architecture Issues
- Bullet each issue: severity (High/Medium/Low), evidence, impact.

## Security and Scalability Gaps
- Concrete gaps tied to this codebase (not generic OWASP lists).

## Refactoring Strategy
- Prioritized improvements mapped to modules/classes from AST.

## Old vs New Architecture Comparison
| Area | Current State | Proposed State | Expected Benefit |
|---|---|---|---|

Avoid generic advice. Every bullet must reference inventory or AST evidence.
"""

    analysis_report = invoke_with_fallback(prompt)
    print("\n[Code Analysis Agent] Analysis complete.")
    return {"analysis_report": analysis_report}


def generate_brownfield_component_details(*args, **kwargs) -> list[dict]:
    # Deprecated: structured extraction handled in greenfield.py architecture_agent
    return []
