# store_policy_chunks.py

import hashlib

from sqlalchemy import text

from db import SessionLocal
from embedding_node import Embedder
from nodes.fetch_policy_node import get_all_chunks


# ==========================================
# EMBEDDER
# ==========================================

embedder = Embedder()


# ==========================================
# HASH FUNCTION
# ==========================================

def generate_hash(text_data: str):

    return hashlib.sha256(
        text_data.encode("utf-8")
    ).hexdigest()


# ==========================================
# STORE CHUNKS
# ==========================================

def store_chunks():

    db = SessionLocal()

    try:

        # ----------------------------------
        # FETCH ALL CHUNKS
        # ----------------------------------

        data = get_all_chunks()

        print(f"\nTotal chunks fetched: {len(data)}")


        # ----------------------------------
        # CREATE EMBEDDINGS IN BATCH
        # ----------------------------------

        texts = [
            item["chunk"]
            for item in data
        ]

        embeddings = embedder.embed_batch(texts)

        print("\nEmbeddings generated successfully")


        # ----------------------------------
        # INSERT INTO DB
        # ----------------------------------

        for index, item in enumerate(data):

            policy_name = item["policy_name"]

            content = item["chunk"]

            embedding = embeddings[index]

            content_hash = generate_hash(content)


            db.execute(

                text("""

                    INSERT INTO policy_chunks (

                        policy_name,
                        content,
                        content_hash,
                        embedding,
                        chunk_index

                    )

                    VALUES (

                        :policy_name,
                        :content,
                        :content_hash,
                        :embedding,
                        :chunk_index

                    )

                    ON CONFLICT (content_hash)
                    DO NOTHING

                """),

                {

                    "policy_name": policy_name,

                    "content": content,

                    "content_hash": content_hash,

                    "embedding": embedding,

                    "chunk_index": index

                }

            )


        # ----------------------------------
        # COMMIT
        # ----------------------------------

        db.commit()

        print("\n✅ All chunks stored successfully")


    except Exception as e:

        db.rollback()

        print("\n❌ Error while storing chunks:")
        print(e)


    finally:

        db.close()


# ==========================================
# RUN
# ==========================================

if __name__ == "__main__":

    store_chunks()