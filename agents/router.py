"""
Router logic for LangGraph.
Decides which agent to route to based on the mode.
"""

from agents.state import AgentState

def router(state: AgentState) -> str:
    """
    Routes to 'analysis' (Greenfield) or 'code' (Brownfield)
    based on the 'mode' field in AgentState.
    """
    if state["mode"] == "greenfield":
        print("\n[Router] -> Analysis Agent (Greenfield)")
        return "analysis"
    else:
        print("\n[Router] -> Code Analysis Agent (Brownfield)")
        return "code"
