from langchain_core.callbacks.manager import adispatch_custom_event
from agents.live_agent import live_agent
from graph.state import GraphState


async def live_node(state: GraphState):
    print("LIVE_NODE: fetching live match data for question")
    # -------------------------
    # STAGE 1: FETCHING
    # -------------------------
    await adispatch_custom_event(
        "stage",
        {"type": "stage", "stage": "fetch", "message": "Fetching live match data..."}
    )

    # -------------------------
    # STAGE 2: GENERATION
    # -------------------------
    await adispatch_custom_event(
        "stage",
        {"type": "stage", "stage": "generation", "message": "Generating answer..."}
    )

    print(f"LIVE_NODE: calling live_agent with question={state['question']}")
    result = await live_agent(
        state["question"],
    )

    state["response"] = result
    state["show_followup"] = (
        result != "I could not find the answer in the knowledge base."
    )

    return state