from langchain_core.callbacks.manager import adispatch_custom_event
from agents.rag_agent import rag_agent
from database.vector_store import search_documents


async def rag_node(state):
    search_q = state.get("standalone_question") or state["question"]

    # -------------------------
    # STAGE 1: RETRIEVAL
    # -------------------------
    await adispatch_custom_event(
        "stage",
        {"type": "stage", "stage": "retrieval", "message": "Searching knowledge base..."},
    )

    documents = search_documents(search_q)
    state["retrieved_docs"] = documents

    # -------------------------
    # STAGE 2: GENERATION
    # -------------------------
    await adispatch_custom_event(
        "stage",
        {"type": "stage", "stage": "generation", "message": "Generating answer..."},
    )

    state["response"] = await rag_agent(
        question=search_q,
        documents=documents,
    )

    return state