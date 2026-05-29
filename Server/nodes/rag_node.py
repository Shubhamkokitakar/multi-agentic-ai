from agents.rag_agent import rag_agent
from database.vector_store import search_documents
from graph.state import GraphState

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
