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
GENERIC_KEYWORDS = [
    "hi",
    "hello",
    "hey",
    "thanks",
    "thank you",
    "good morning",
    "good evening",
    "how are you"
]
# ----------------------------
# ROUTER NODE
# ----------------------------
async def router_node(state: GraphState):

    question = state.get("standalone_question", state["question"]).lower()

     # GENERIC ROUTE
    if question in GENERIC_KEYWORDS:

        state["route"] = "generic"

    # LIVE ROUTE
    elif any(keyword in question for keyword in LIVE_KEYWORDS):

        state["route"] = "live"

    # DEFAULT RAG ROUTE
    else:

        state["route"] = "rag"

    return state