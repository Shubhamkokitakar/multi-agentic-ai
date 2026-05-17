from langgraph.graph import StateGraph, END

from nodes.router_node import router_node
from nodes.rag_node import rag_node
from nodes.live_node import live_node


workflow = StateGraph(dict)

workflow.add_node(
    "router",
    router_node
)

workflow.add_node(
    "rag",
    rag_node
)

workflow.add_node(
    "live",
    live_node
)

workflow.set_entry_point(
    "router"
)

workflow.add_conditional_edges(

    "router",

    lambda state: state["route"],

    {
        "rag": "rag",
        "live": "live"
    }
)

workflow.add_edge(
    "rag",
    END
)

workflow.add_edge(
    "live",
    END
)

graph = workflow.compile()