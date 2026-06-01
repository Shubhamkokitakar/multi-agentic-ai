from agents.live_agent import live_agent
from graph.state import GraphState

async def live_node(state: GraphState):

    result = await live_agent(

        state["question"],
        conversation_history=state.get("history", "")

    )

    state["response"] = result
    state["show_followup"] = (
        result != "I could not find the answer in the knowledge base."
    )

    return state

