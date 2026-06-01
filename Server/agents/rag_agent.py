from database.vector_store import search_documents
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="gpt-4.1-mini"
)


async def rag_agent(
    question: str,
    token_callback=None
):

    documents = search_documents(question)

    context = "\n\n".join(documents)

    prompt = f"""
You are a cricket assistant.

Answer ONLY using the provided context.

If the answer is not found in the context,
reply exactly with:

"I could not find the answer in the knowledge base."

CONTEXT:
{context}

QUESTION:
{question}
"""

    full_response = ""

    async for chunk in llm.astream(prompt):

        token = chunk.content

        if not token:
            continue

        full_response += token

        if token_callback:
            await token_callback(token)

    return full_response.strip()