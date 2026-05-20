from openai import OpenAI
import os
from langchain_openai import ChatOpenAI 

llm = ChatOpenAI(model="gpt-4.1-mini")

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


Suggest 2-3 follow-up questions that are directly supported by the retrieved documents.
If you cannot, respond with: No follow-up questions.
"""
    response = await llm.ainvoke(prompt)
    return response.content.strip()