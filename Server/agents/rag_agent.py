from vector_store import search_documents
from openai import OpenAI
import os

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


async def rag_agent(question: str):
    print(question,'question in rag agent')

    context = search_documents(question)

    prompt = f"""

    Answer using provided context.

    Context:
    {context}

    Question:
    {question}

    """

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