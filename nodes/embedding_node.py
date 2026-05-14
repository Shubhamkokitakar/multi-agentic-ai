from langchain_ollama import OllamaEmbeddings

from sqlalchemy import text

from db import engine


class EmbeddingNode:

    def __init__(self):

        self.embedding_model = OllamaEmbeddings(
            model="nomic-embed-text"
        )


    def run(self, state):

        chunks = state["policy_chunks"]

        with engine.begin() as conn:

            for chunk in chunks:

                embedding = self.embedding_model.embed_query(
                    chunk["text"]
                )

                conn.execute(
                    text(
                        """
                        INSERT INTO youtube_policy_embeddings
                        (
                            policy_name,
                            chunk_text,
                            embedding
        return state