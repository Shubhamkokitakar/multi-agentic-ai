from langchain_core.callbacks.manager import adispatch_custom_event
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4.1-mini")


async def rag_agent(question: str, documents: list[str]) -> str:
    """
    RAG generation with streaming tokens via custom events.
    Token callbacks are gone — tokens are dispatched as events
    and picked up by whoever is listening (e.g. the WebSocket layer).
    """
    context = "\n\n".join(
        f"[DOC {i+1}]\n{doc}" for i, doc in enumerate(documents or [])
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

    async for chunk in llm.astream(prompt):
        token = getattr(chunk, "content", None)
        if not token:
            continue

        full_response.append(token)

        # Dispatch token as an event — no callback needed
        await adispatch_custom_event("token", {"type": "token", "value": token})

    return "".join(full_response).strip()