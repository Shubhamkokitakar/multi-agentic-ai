from openai import OpenAI
import os
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4.1-mini")


async def refine_query(history, question):
    history_text = "\n".join(
        f"{item['role']}: {item['content']}"
        for item in history[-6:]
    )

    prompt = f"""
You are a cricket assistant.
Rewrite the latest question into a standalone question using the chat history.
If the latest question is already self-contained, return it unchanged.

Chat history:
{history_text}

Latest question:
{question}

Standalone question:
"""
    response = await llm.ainvoke(prompt)

    return response.content.strip()