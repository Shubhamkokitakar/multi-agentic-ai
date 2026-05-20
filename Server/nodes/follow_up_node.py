

from agents.follow_up_agent import followup_agent
from graph.state import GraphState

async def follow_up_node(state: GraphState):
    print("FOLLOW_UP_NODE: running for question=", state.get("question"))
    follow_up_text = await followup_agent(
        state["question"],
        state["response"],
        state.get("retrieved_docs")
    )
    state["follow_ups"] = follow_up_text or ""
    print("follow_up=", state["follow_ups"])
    return state