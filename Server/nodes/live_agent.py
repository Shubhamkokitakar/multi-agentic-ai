import os
import requests
from typing import List, Dict, Any
from dotenv import load_dotenv


class LiveCricketAgent:
    """
    Live Cricket Agent using CricAPI
    - Reads API key from .env
    - Fetches live matches
    - Safe parsing + chunking
    """

    def __init__(self):
        load_dotenv()  # load .env file

        self.api_key = os.getenv("CRICAPI_KEY")

        if not self.api_key:
            raise Exception("CRICAPI_KEY not found in .env file")

        self.base_url = "https://api.cricapi.com/v1"

    # -----------------------------
    # FETCH LIVE MATCHES
    # -----------------------------
    def fetch_live_matches(self) -> Dict[str, Any]:
        url = f"{self.base_url}/currentMatches"

        params = {
            "apikey": self.api_key,
            "offset": 0,
            "limit": 50
        }

        try:
            res = requests.get(
                url,
                params=params,
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "Accept": "application/json"
                },
                timeout=15
            )

            print("\n[DEBUG] STATUS:", res.status_code)
            print("[DEBUG] RAW:", res.text[:300])

            if res.status_code != 200:
                raise Exception(f"API Error {res.status_code}: {res.text}")

            return res.json()

        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error: {e}")

    # -----------------------------
    # EXTRACT MATCHES
    # -----------------------------
    def extract_matches(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not isinstance(data, dict):
            return []

        return data.get("data", [])

    # -----------------------------
    # FORMAT MATCH
    # -----------------------------
    def format_match(self, match: Dict[str, Any]) -> str:
        return f"""
MATCH:
Name: {match.get('name', 'Unknown')}
Status: {match.get('status', 'Unknown')}
Type: {match.get('matchType', 'Unknown')}
Venue: {match.get('venue', 'Unknown')}
Score: {match.get('score', 'No score')}
""".strip()

    # -----------------------------
    # CHUNK MATCHES
    # -----------------------------
    def chunk_matches(self, matches: List[Dict[str, Any]], chunk_size: int = 2) -> List[str]:
        if not matches:
            return []

        formatted = [self.format_match(m) for m in matches]

        chunks = []
        for i in range(0, len(formatted), chunk_size):
            chunks.append("\n\n---\n\n".join(formatted[i:i + chunk_size]))

        return chunks

    # -----------------------------
    # RUN PIPELINE
    # -----------------------------
    def run(self):
        data = self.fetch_live_matches()
        matches = self.extract_matches(data)
        chunks = self.chunk_matches(matches)

        print("\n======================")
        print("TOTAL MATCHES:", len(matches))
        print("TOTAL CHUNKS:", len(chunks))
        print("======================\n")

        if chunks:
            print("=== CHUNK 0 ===\n")
            print(chunks[0])
        else:
            print("No live matches currently available.")


# -----------------------------
# MAIN
# -----------------------------
if __name__ == "__main__":
    agent = LiveCricketAgent()
    agent.run()