# embedder.py

import os

from openai import OpenAI


client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


class Embedder:


    def __init__(

        self,
        model="text-embedding-3-small"

    ):

        self.model = model


    def embed_batch(self, texts: list[str]):


        response = client.embeddings.create(

            model=self.model,

            input=texts

        )


        return [

            item.embedding

            for item in response.data

        ]