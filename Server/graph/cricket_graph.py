from langgraph.graph import StateGraph, END

from nodes.live_node import live_node
from nodes.rag_node import rag_node
from nodes.rewrite_node import rewrite_node
from nodes.router_node import router_node
from nodes.follow_up_node import follow_up_node

from graph.state import GraphState
from agents.generic_agent import generic_agent

# ----------------------------
# BUILD GRAPH
# ----------------------------
workflow = StateGraph(GraphState)

# ----------------------------
# NODES
# ----------------------------
workflow.add_node("router", router_node)
workflow.add_node("rewrite", rewrite_node)
workflow.add_node("live", live_node)
workflow.add_node("rag", rag_node)
workflow.add_node("follow_up", follow_up_node)
workflow.add_node("generic_agent", generic_agent)

# ----------------------------
# ROUTER FUNCTION
# ----------------------------
def route_decision(state: GraphState):
    return state["route"]

workflow.set_entry_point("router")

# ----------------------------
# ROUTER EDGES
# ----------------------------
workflow.add_conditional_edges(
    "router",
    route_decision,
    {
        "generic": "generic_agent",
        "live": "rewrite",
        "rag": "rewrite",
    }
)

# ----------------------------
# REWRITE ROUTING
# ----------------------------
workflow.add_conditional_edges(
    "rewrite",
    route_decision,
    {
        "live": "live",
        "rag": "rag",
    }
)

workflow.add_edge("generic_agent", END)

workflow.add_edge("live", "follow_up")
workflow.add_edge("rag", "follow_up")

workflow.add_edge("follow_up", END)

# ----------------------------
# COMPILE GRAPH
# ----------------------------
graph = workflow.compile()