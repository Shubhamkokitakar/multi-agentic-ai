import requests

from bs4 import BeautifulSoup
from unstructured.partition.html import partition_html

from policy_registration import POLICY_REGISTRY


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

        for tag in soup([
            "script",
            "style",
            "noscript"
        ]):
            tag.decompose()

        return soup.prettify()


    def parse_html(self, html: str):

        with open(
            "temp_policy.html",
            "w",
            encoding="utf-8"
        ) as f:
            f.write(html)

        elements = partition_html(
            filename="temp_policy.html"
        )

        parsed_text = "\n".join(
            [
                el.text
                for el in elements
                if hasattr(el, "text")
            ]
        )

        return parsed_text


    def chunk_text(
        self,
        text,
        chunk_size=1000,
        overlap=150
    ):

        chunks = []

        start = 0

        while start < len(text):
