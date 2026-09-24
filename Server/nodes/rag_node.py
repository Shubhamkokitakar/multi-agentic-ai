from langchain_core.callbacks.manager import adispatch_custom_event
from agents.rag_agent import rag_agent
from database.vector_store import VectorStore
from nodes.embeddings import Embedder

vector_store = VectorStore()
embedder = Embedder()



async def rag_node(state):
    search_q = state.get("standalone_question") or state["question"]

    # -------------------------
    # STAGE 1: RETRIEVAL
    # -------------------------
    await adispatch_custom_event(
        "stage",
        {"type": "stage", "stage": "retrieval", "message": "Searching knowledge base..."},
    )

    query_embedding = embedder.embed_query(search_q)


    results  = vector_store.search_documents(query_embedding, n_results=3)

    documents = results["documents"][0]
    print(f"documents retrieved: {documents}")

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