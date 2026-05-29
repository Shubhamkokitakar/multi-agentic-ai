from typing import TypedDict

from agents.generic_agent import generic_agent
from langgraph.graph import StateGraph, END

from agents.live_agent import live_agent
from agents.rag_agent import rag_agent
from agents.follow_up_agent import followup_agent
from agents.query_refiner import refine_query
from vector_store import search_documents

from nodes.live_node import live_node
from nodes.rag_node import rag_node
from nodes.rewrite_node import rewrite_node
from nodes.router_node import router_node
from nodes.follow_up_node import follow_up_node
from graph.state import GraphState





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

workflow.add_node(generic_agent, generic_agent)



workflow.set_entry_point("rewrite")


# workflow route

def route_decision(state: GraphState):

    return state["route"]

workflow.add_edge("rewrite", "router")

workflow.add_conditional_edges(

    "router",

    route_decision,

    {
        "generic": "generic_agent",

        "live": "live",

        "rag": "rag"
    }
)

workflow.add_edge("live", "follow_up")
workflow.add_edge("rag", "follow_up")
workflow.add_edge("follow_up", END)

graph = workflow.compile()