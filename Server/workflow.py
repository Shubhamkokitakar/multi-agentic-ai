
from langgraph.graph import StateGraph, END

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

def route_decision(state: GraphState):

    return state["route"]

workflow.set_entry_point("router")

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