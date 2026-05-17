from openai import OpenAI
import os

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

class Embedder:

    def __init__(
        self,
        model="text-embedding-3-small"
    ):

        self.model = model

    def embed_batch(
        self,
        texts: list[str]
    ):

        response = client.embeddings.create(

            model=self.model,
            input=texts
        )
        print(response,'response')

        return [

            item.embedding

            for item in response.data
        ]