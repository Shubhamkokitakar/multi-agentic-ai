from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def followup_agent(question: str, answer: str, retrieved_docs: list[str] = None):
    docs_text = "\n\n".join(retrieved_docs) if retrieved_docs else ""
    
    prompt = f"""
You are a cricket assistant.

Based on the retrieved documents and the answer, suggest 2-3 follow-up questions.
ONLY suggest questions that can be answered from the retrieved documents.
Do not invent new topics.

RETRIEVED DOCUMENTS:
{docs_text}

ORIGINAL QUESTION:
{question}

ANSWER:
{answer}

FOLLOW-UP QUESTIONS:
"""
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()