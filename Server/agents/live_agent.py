
import os
import requests

from typing import List, Dict, Any
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

llm = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0
)


class LiveCricketAgent:

    def __init__(self):

        self.api_key = os.getenv("CRICAPI_KEY")

        if not self.api_key:
            raise Exception("CRICAPI_KEY not found in .env")

        self.base_url = "https://api.cricapi.com/v1"

    # ---------------------------------
    # FETCH LIVE MATCHES
    # ---------------------------------
    def fetch_live_matches(self):

        url = f"{self.base_url}/currentMatches"

        params = {
            "apikey": self.api_key,
            "offset": 0
        }

        response = requests.get(
            url,
            params=params,
            timeout=15
        )

        if response.status_code != 200:
            raise Exception(
                f"API Error: {response.status_code} - {response.text}"
            )

        return response.json()

    # ---------------------------------
    # EXTRACT MATCHES
    # ---------------------------------
    def extract_matches(
        self,
        data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:

        return data.get("data", [])

    # ---------------------------------
    # FORMAT MATCH
    # ---------------------------------
    def format_match(
        self,
        match: Dict[str, Any]
    ) -> str:

        return f"""
Match: {match.get('name')}

Status:
{match.get('status')}

Venue:
{match.get('venue')}

Match Type:
{match.get('matchType')}

Score:
{match.get('score')}
"""

    # ---------------------------------
    # MAIN EXECUTION
    # ---------------------------------
    def run(self):

        data = self.fetch_live_matches()

        matches = self.extract_matches(data)

        if not matches:
            return "No live matches found."

        output = []

        for match in matches[:5]:
            output.append(
                self.format_match(match)
            )

        return "\n\n------------------\n\n".join(output)


# =====================================
# AGENT FUNCTION
# =====================================

async def live_agent(
    question: str,
    conversation_history: str = ""
):

    agent = LiveCricketAgent()

    live_data = agent.run()

    prompt = f"""
You are a cricket assistant.

User Question:
{question}

Live Match Data:
{live_data}

Return the answer in the following format:

🏏 Match Name

• Status:
• Score:
• Venue:

------------------

🏏 Match Name

• Status:
• Score:
• Venue:

Keep the response concise and highly readable.
"""

    response = llm.invoke(prompt)

    return response.content

