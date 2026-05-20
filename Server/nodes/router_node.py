from agents.live_agent import live_agent
from agents.rag_agent import rag_agent
from graph.state import GraphState

LIVE_KEYWORDS = [

    "live",
    "score",
    "today",
    "current",
    "latest",
    "ipl"

]

# ----------------------------
# ROUTER NODE
# ----------------------------
async def router_node(state: GraphState):

    question = state.get("standalone_question", state["question"]).lower()

    is_live = any(

        keyword in question

        for keyword in LIVE_KEYWORDS
    )

    if is_live:

        state["route"] = "live"

    else:

        state["route"] = "rag"

    return state