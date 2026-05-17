from vector_store import search_documents
from openai import OpenAI
import os

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


async def rag_agent(question: str):

    print(question, 'question in rag agent')

    # -------------------------
    # RETRIEVE CONTEXT
    # -------------------------
    documents = search_documents(question)

    context = "\n\n".join(documents)

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
    response = client.chat.completions.create(

        model="gpt-4.1-mini",

        messages=[

            {
                "role": "user",
                "content": prompt
            }

        ]
    )

    return response.choices[0].message.content