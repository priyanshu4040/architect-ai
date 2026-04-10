"""
Router logic for LangGraph.
Decides which agent to route to based on the mode.
"""

from agents.state import AgentState

def router(state: AgentState) -> str:
    """
    Routes to 'architecture' (Greenfield) or 'code' (Brownfield)
    based on the 'mode' field in AgentState.
    """
    if state["mode"] == "greenfield":
        print("\n[Router] -> Architecture Agent (Greenfield)")
        return "architecture"
    else:
        print("\n[Router] -> Code Analysis Agent (Brownfield)")
        return "code"
