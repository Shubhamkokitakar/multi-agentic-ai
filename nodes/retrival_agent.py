from sqlalchemy import text

from db import engine

from langchain_ollama import OllamaEmbeddings


class PolicyRetrievalAgent:

    def __init__(self):

        self.embedding_model = OllamaEmbeddings(
            model="nomic-embed-text"
        )


    def retrieve(
        self,
        query,
        top_k=3
    ):

        query_embedding = self.embedding_model.embed_query(query)

        sql = text(
            """
            SELECT
                policy_name,
                chunk_text,
                embedding <=> :query_embedding AS distance
            FROM youtube_policy_embeddings
            ORDER BY distance
            LIMIT :top_k
            """
        )

        with engine.connect() as conn:

            rows = conn.execute(
                sql,
                {
                    "query_embedding": query_embedding,
                    "top_k": top_k
                }
            ).fetchall()

        return rows