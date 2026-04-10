"""
Code Analysis Agent (Brownfield)
Takes existing code and returns issue detection with refactoring recommendations.
"""

from langchain_community.chat_models import ChatOllama
from agents.state import AgentState
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
You are a software architecture reviewer.

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

Keep answer structured and actionable.
"""

    response = llm.invoke(prompt)
    print("\n[Code Analysis Agent] Analysis complete.")
    return {"analysis_report": response.content}
