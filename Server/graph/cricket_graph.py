from typing import TypedDict

from langgraph.graph import StateGraph, END

from agents.live_agent import live_agent
from agents.rag_agent import rag_agent
from agents.follow_up_agent import followup_agent
from agents.query_refiner import refine_query
from vector_store import search_documents

class GraphState(TypedDict, total=False):

    question: str

    route: str

    response: str

    follow_ups: str
    history: list[dict[str, str]]
    standalone_question: str
    retrieved_docs: list[str]  # NEW


LIVE_KEYWORDS = [

    "live",
    "score",
    "today",
    "current",
    "latest",
    "ipl"

]


# ----------------------------
# REWRITE NODE
# ----------------------------
async def rewrite_node(state: GraphState):
    print("REWRITE_NODE: rewriting question using history")
    standalone_q = await refine_query(
        state.get("history", []),
        state["question"]
    )
    state["standalone_question"] = standalone_q
    print(f"REWRITE_NODE: original={state['question']}, rewritten={standalone_q}")
    return state


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

    search_q = state.get("standalone_question", state["question"])
      # Get documents
    documents = search_documents(search_q)
    state["retrieved_docs"] = documents  # Store them

    result = await rag_agent(search_q)

    state["response"] = result

    return state



# ...

async def follow_up_node(state: GraphState):
    print("FOLLOW_UP_NODE: running for question=", state.get("question"))
    follow_up_text = await followup_agent(
        state["question"],
        state["response"],
        state.get("retrieved_docs")
    )
    state["follow_ups"] = follow_up_text or ""
    print("FOLLOW_UP_NODE: follow_ups=", state["follow_ups"])
    return state


# ----------------------------
# BUILD GRAPH
# ----------------------------
workflow = StateGraph(GraphState)

workflow.add_node(

    "rewrite",
    rewrite_node
)

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
workflow.add_node("follow_up", follow_up_node)



workflow.set_entry_point("rewrite")


def route_decision(state: GraphState):

    return state["route"]


workflow.add_edge("rewrite", "router")

workflow.add_conditional_edges(

    "router",

    route_decision,

    {

        "live": "live",

        "rag": "rag"
    }
)

workflow.add_edge("live", "follow_up")
workflow.add_edge("rag", "follow_up")
workflow.add_edge("follow_up", END)

graph = workflow.compile()