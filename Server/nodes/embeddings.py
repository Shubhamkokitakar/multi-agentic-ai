from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings

load_dotenv()


class Embedder:

    def __init__(self, model="text-embedding-3-small"):
        self.embeddings = OpenAIEmbeddings(model=model)

    def embed_documents(self, documents):
        texts = [document.page_content for document in documents]

        return self.embeddings.embed_documents(texts)

    def embed_query(self, query):
        return self.embeddings.embed_query(query)