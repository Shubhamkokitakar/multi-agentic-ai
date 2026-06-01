from agents.rag_agent import rag_agent
from database.vector_store import search_documents


async def rag_node(state):

    search_q = state.get("standalone_question") or state["question"]

    token_callback = state.get("token_callback")
    stage_callback = state.get("stage_callback")

    # -------------------------
    # STAGE 1: RETRIEVAL
    # -------------------------
    await stage_callback({
        "type": "stage",
        "stage": "retrieval",
        "message": "Searching knowledge base..."
    })

    documents = search_documents(search_q)
    state["retrieved_docs"] = documents

    # -------------------------
    # STAGE 2: GENERATION
    # -------------------------
    await stage_callback({
        "type": "stage",
        "stage": "generation",
        "message": "Generating answer..."
    })

    # STREAM LLM
    state["response"] = await rag_agent(
        question=search_q,
        documents=documents,
        token_callback=token_callback
    )

    return state