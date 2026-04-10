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
    if state["mode"] == "greenfield":
        print("\n[Architecture Agent] Designing from scratch (Greenfield)...")
        context = f"Requirements:\n{state['input']}"
    else:
        print("\n[Architecture Agent] Designing refactored architecture (Brownfield)...")
        context = f"Existing Codebase Analysis Report:\n{state['analysis_report']}\n\nExisting AST Structure:\n{state.get('ast_summary', '')}"

    prompt = f"""
You are an expert software architect.

Based on the following context, build or refactor the architecture.

{context}

--- PAST ARCHITECTURAL KNOWLEDGE (RAG Memory) ---
{state.get('past_memory', 'No past memory found.')}
-------------------------------------------------

Do the following:
1. Suggest best architecture (Microservices, MVC, Layered, Event-Driven, etc.). Align with PAST ARCHITECTURAL KNOWLEDGE if relevant.
2. Provide a HIGHLY DETAILED modular decomposition grouped strictly by Topic/Business Domain.
3. For each Topic/Module, explicitly list the exact Class Names to be built.
4. Detail exactly how those classes Connect to each other and their relation to one another (Inheritance, Composition, or API calls).
5. Suggest design patterns (Factory, Observer, Strategy, etc.) to use for those class relations.
6. Generate a visual Dependency Graph using Mermaid.js (` ```mermaid graph TD ... ``` `) that plots all the classes and their exact connections to each other.

Keep answer structured, extremely detailed, and concise.
"""

    response = llm.invoke(prompt)
    print("\n[Architecture Agent] Plan generated.")
    return {"architecture_plan": response.content}
