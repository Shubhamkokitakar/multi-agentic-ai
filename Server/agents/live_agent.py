import os
import requests

from typing import Dict, Any
from dotenv import load_dotenv

from langchain_core.callbacks.manager import adispatch_custom_event
from langchain_openai import ChatOpenAI


load_dotenv()


llm = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0
)


class LiveCricketAgent:

    def __init__(self):

        self.api_key = os.getenv("BBS_API_KEY")

        if not self.api_key:
            raise Exception(
                "BBS_API_KEY not found in .env"
            )

        self.base_url = "https://api.bigballsdata.com/v1"

        self.headers = {
            "Authorization": f"Bearer {self.api_key}"
        }

    # ---------------------------------
    # FETCH MATCHES
    # ---------------------------------
    def fetch_matches(self):

        url = f"{self.base_url}/cricket/matches"

        response = requests.get(
            url,
            headers=self.headers,
            timeout=15
        )

        print(
            f"BIG BALLS API STATUS: {response.status_code}"
        )

        if response.status_code != 200:

            raise Exception(
                f"API Error: "
                f"{response.status_code} - "
                f"{response.text}"
            )

        data = response.json()

        print("BIG BALLS API RESPONSE:")
        print(data)

        return data

    # ---------------------------------
    # CONVERT API RESPONSE TO TEXT
    # ---------------------------------
    def format_api_response(
        self,
        data: Dict[str, Any]
    ) -> str:

        return str(data)

    # ---------------------------------
    # MAIN EXECUTION
    # ---------------------------------
    def run(self):

        data = self.fetch_matches()

        return self.format_api_response(data)


# =====================================
# AGENT FUNCTION
# =====================================

async def live_agent(
    question: str
):

    print(
        f"LIVE_AGENT: question={question}"
    )

    agent = LiveCricketAgent()

    # Get whatever Big Balls returns
    live_data = agent.run()

    print(
        "LIVE_AGENT: API data received"
    )

    prompt = f"""
You are a cricket assistant.

Answer the user's question using ONLY
the cricket data returned by the API.

User Question:
{question}

API Cricket Data:
{live_data}

Instructions:

1. Use only the information available in the API data.

2. Do not invent scores, players, teams, venues, or match information.

3. If live matches are available, show the live matches relevant to the user's question.

4. If no live matches are available in the API data, show the upcoming scheduled matches from the API instead.

5. Clearly indicate that these are upcoming matches and not currently live.

6. If multiple upcoming matches are available, show the most relevant ones.

7. Keep the answer concise and readable.

8. Do not mention API implementation details in the final answer.

Answer the user's question directly.
"""

    full_response = []

    async for chunk in llm.astream(prompt):

        token = getattr(
            chunk,
            "content",
            None
        )
        print(
            f"LIVE_AGENT: token={token}"
        )
        if not token:
            continue

        full_response.append(token)

        await adispatch_custom_event(
            "token",
            {
                "type": "token",
                "value": token
            }
        )

    return "".join(
        full_response
    ).strip()