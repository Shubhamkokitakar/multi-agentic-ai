from database.vector_store import search_documents
import os
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4.1-mini")


async def rag_agent(question: str):

    print(question, 'question in rag agent')

    # -------------------------
    # RETRIEVE CONTEXT
    # -------------------------
    documents = search_documents(question)
    print(documents, 'documents retrieved in rag agent')

    context = "\n\n".join(documents)
    print(context, 'context in rag agent')

    # -------------------------
    # GROUNDED PROMPT
    # -------------------------
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

    # -------------------------
    # LLM CALL
    # -------------------------
    response = await llm.ainvoke(prompt)
    print(response.content.strip(), 'response in rag agent')
    return response.content.strip()