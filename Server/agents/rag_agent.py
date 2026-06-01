from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4.1-mini")


async def rag_agent(
    question: str,
    documents: list[str],
    token_callback=None
):
    """
    RAG generation with streaming tokens.
    Assumes documents are already retrieved by the graph/node.
    """

    context = "\n\n".join(
        f"[DOC {i+1}]\n{doc}"
        for i, doc in enumerate(documents or [])
    )

    prompt = f"""
You are a cricket assistant.

Answer ONLY using the provided context.

If the answer is not found in the context, reply exactly:
"I could not find the answer in the knowledge base."

CONTEXT:
{context}

QUESTION:
{question}

Answer clearly and concisely.
"""

    full_response = []

    stream = llm.astream(prompt)

    async for chunk in stream:
        token = getattr(chunk, "content", None)

        if not token:
            continue

        full_response.append(token)

        if token_callback:
            await token_callback(token)

    return "".join(full_response).strip()