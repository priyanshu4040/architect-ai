"""
Router logic for LangGraph.
"""

from agents.state import AgentState


def router(state: AgentState) -> str:
    """
    Greenfield and brownfield both start at analysis (token-saving: skip code_agent pass).
    """
    if state["mode"] == "greenfield":
        print("\n[Router] -> Analysis Agent (Greenfield)")
    else:
        print("\n[Router] -> Analysis Agent (Brownfield, compact summary)")
    return "analysis"
