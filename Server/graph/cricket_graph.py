from typing import TypedDict

from langgraph.graph import StateGraph, END

from agents.live_agent import live_agent
from agents.rag_agent import rag_agent


class GraphState(TypedDict):

    question: str

    route: str

    response: str


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

    question = state["question"].lower()

    is_live = any(

        keyword in question

        for keyword in LIVE_KEYWORDS
    )

    if is_live:

        state["route"] = "live"

    else:

        state["route"] = "rag"

    return state


# ----------------------------
# LIVE NODE
# ----------------------------
async def live_node(state: GraphState):

    result = await live_agent(

        state["question"]
    )

    state["response"] = result

    return state


# ----------------------------
# RAG NODE
# ----------------------------
async def rag_node(state: GraphState):

    result = await rag_agent(

        state["question"]
    )

    state["response"] = result

    return state


# ----------------------------
# BUILD GRAPH
# ----------------------------
workflow = StateGraph(GraphState)

workflow.add_node(

    "router",
    router_node
)

workflow.add_node(

    "live",
    live_node
)

workflow.add_node(

    "rag",
    rag_node
)


workflow.set_entry_point("router")


def route_decision(state: GraphState):

    return state["route"]


workflow.add_conditional_edges(

    "router",

    route_decision,

    {

        "live": "live",

        "rag": "rag"
    }
)

workflow.add_edge("live", END)

workflow.add_edge("rag", END)

graph = workflow.compile()