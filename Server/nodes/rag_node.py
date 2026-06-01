from agents.rag_agent import rag_agent
from database.vector_store import search_documents


async def rag_node(state):

    search_q = state.get(
        "standalone_question",
        state["question"]
    )

    documents = search_documents(search_q)

    state["retrieved_docs"] = documents

    token_callback = state.get("token_callback")

    result = await rag_agent(
        search_q,
        token_callback=token_callback
    )

    state["response"] = result

    return state