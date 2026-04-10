"""
Architecture Analysis Agent (Greenfield + Brownfield)

Produces a professional `analysis_report` that the Architecture/Planning agent
can consume. This enables true orchestration:
  greenfield: analysis -> architecture
  brownfield: code -> analysis -> architecture
"""

import os
from dotenv import load_dotenv

from agents.state import AgentState

load_dotenv()

groq_api_key = os.getenv("GROQ_API_KEY")
if groq_api_key:
    from langchain_groq import ChatGroq

    llm = ChatGroq(model="llama-3.3-70b-versatile", groq_api_key=groq_api_key)
    print("[Analysis] Using Groq Cloud API for Llama-3...")
else:
    from langchain_community.chat_models import ChatOllama

    llm = ChatOllama(model="llama3")
    print("[Analysis] Using local Ollama for Llama-3...")


def analysis_agent(state: AgentState) -> AgentState:
    """
    Generate an analysis report.

    - Greenfield: analyze requirements + NFRs + risks + key decisions.
    - Brownfield: refine the code agent output into an executive-quality report,
      incorporating README + AST structure where present.
    """
    mode = (state.get("mode") or "").strip().lower()
    readme = (state.get("readme_content") or "")[:1500]
    ast_summary = (state.get("ast_summary") or "")[:4000]
    past_memory = (state.get("past_memory") or "")[:1500]

    if mode == "brownfield":
        base = (state.get("analysis_report") or "")[:7000]
        context = (
            "MODE: brownfield\n\n"
            "You are refining an initial architecture/code analysis into an executive-quality report.\n\n"
            "--- README (topic) ---\n"
            f"{readme or 'No README provided.'}\n\n"
            "--- AST summary (structure) ---\n"
            f"{ast_summary or 'No AST summary provided.'}\n\n"
            "--- Initial findings (from code agent) ---\n"
            f"{base or 'No initial findings provided.'}\n\n"
            "--- Past architectural knowledge ---\n"
            f"{past_memory or 'No past memory found.'}\n"
        )
    else:
        req = (state.get("input") or "")[:9000]
        context = (
            "MODE: greenfield\n\n"
            "You are analyzing requirements for a new system.\n\n"
            "--- Requirements ---\n"
            f"{req}\n\n"
            "--- Past architectural knowledge ---\n"
            f"{past_memory or 'No past memory found.'}\n"
        )

    if mode == "brownfield":
        prompt = (
            "You are a senior staff software architect specializing in brownfield modernization.\n\n"
            f"{context}\n\n"
            "Write a PROFESSIONAL analysis report in Markdown using exactly these headings:\n"
            "## Executive Summary\n"
            "- 4-8 bullets\n\n"
            "## Current Codebase Faults\n"
            "- For each fault include: Severity, Evidence, Impact\n\n"
            "## Root Causes\n"
            "- Explain structural causes behind top faults\n\n"
            "## Proposed Target Architecture\n"
            "- 1-2 short paragraphs on the improved architecture\n\n"
            "## Old vs New Comparison\n"
            "| Dimension | Current | Proposed | Benefit |\n"
            "|---|---|---|---|\n\n"
            "## Non-Functional Assessment\n"
            "- Scalability: <0-100>/100 — <1 sentence>\n"
            "- Performance: <0-100>/100 — <1 sentence>\n"
            "- Maintainability: <0-100>/100 — <1 sentence>\n"
            "- Security: <0-100>/100 — <1 sentence>\n\n"
            "## Migration Plan\n"
            "- 4-8 bullets with sequencing and risk controls\n\n"
            "## Risk Analysis\n"
            "- High: ...\n"
            "- Medium: ...\n"
            "- Low: ...\n\n"
            "Constraints:\n"
            "- Be concrete and avoid generic filler.\n"
            "- Use the provided AST/README evidence.\n"
            "- Keep it readable and industry-grade.\n"
        )
    else:
        prompt = (
            "You are a senior staff software architect.\n\n"
            f"{context}\n\n"
            "Write a PROFESSIONAL analysis report in Markdown using exactly these headings:\n"
            "## Executive Summary\n"
            "- 3-6 bullets\n\n"
            "## Recommended Architecture\n"
            "- 1 short paragraph\n\n"
            "## Non-Functional Assessment\n"
            "- Scalability: <0-100>/100 — <1 sentence>\n"
            "- Performance: <0-100>/100 — <1 sentence>\n"
            "- Maintainability: <0-100>/100 — <1 sentence>\n"
            "- Security: <0-100>/100 — <1 sentence>\n\n"
            "## Key Decisions\n"
            "- 3-6 bullets, each with 1-line rationale\n\n"
            "## Risk Analysis\n"
            "- High: ...\n"
            "- Medium: ...\n"
            "- Low: ...\n\n"
            "Constraints:\n"
            "- Be concrete and avoid generic filler.\n"
            "- Keep it readable and \"industry style\".\n"
        )

    resp = llm.invoke(prompt)
    return {"analysis_report": (resp.content or "").strip()}

