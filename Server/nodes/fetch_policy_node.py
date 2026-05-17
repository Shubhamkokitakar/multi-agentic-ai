import requests

from bs4 import BeautifulSoup
from unstructured.partition.html import partition_html

from langchain_text_splitters import RecursiveCharacterTextSplitter


POLICY_REGISTRY = {
    "advertiser_friendly":
        "https://support.google.com/youtube/answer/6162278",

    "misrepresentation":
        "https://support.google.com/adspolicy/answer/6020955",

    "healthcare":
        "https://support.google.com/adspolicy/answer/176031"
}


class PolicyFetchNode:

    def fetch_html(self, url: str):

        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        response = requests.get(
            url,
            headers=headers,
            timeout=30
        )

        response.raise_for_status()

        return response.text


    def clean_html(self, html: str):

        soup = BeautifulSoup(html, "html.parser")

        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        return soup.prettify()


    def parse_html(self, html: str):

        with open("temp_policy.html", "w", encoding="utf-8") as f:
            f.write(html)

        elements = partition_html(filename="temp_policy.html")

        junk_words = [
            "Privacy Policy",
            "Terms of Service",
            "Help Center",
            "Sign in",
            "Submit feedback",
            "Skip to main content"
        ]

        all_text = []

        for el in elements:

            if not hasattr(el, "text"):
                continue

            text = el.text.strip()

            if len(text) < 40:
                continue

            if any(j in text for j in junk_words):
                continue

            all_text.append(text)

        combined_text = "\n\n".join(all_text)

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=100,
            separators=["\n\n", "\n", ". ", " ", ""]
        )

        chunks = splitter.split_text(combined_text)

        return chunks


# =========================
# RUN ALL POLICIES
# =========================
def get_all_chunks():
    node = PolicyFetchNode()

    all_data = []

    for name, url in POLICY_REGISTRY.items():

        html = node.fetch_html(url)
        cleaned = node.clean_html(html)
        chunks = node.parse_html(cleaned)

        for chunk in chunks:
            all_data.append({
                "policy_name": name,
                "chunk": chunk
            })
    print(all_data)

    return all_data