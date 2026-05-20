# ----------------------------
# REWRITE NODE
# ----------------------------
from agents.query_refiner import refine_query
from graph.state import GraphState

async def rewrite_node(state: GraphState):
    print("REWRITE_NODE: rewriting question using history")
    standalone_q = await refine_query(
        state.get("history", []),
        state["question"]
    )
    state["standalone_question"] = standalone_q
    print(f"REWRITE_NODE: original={state['question']}, rewritten={standalone_q}")
    return state