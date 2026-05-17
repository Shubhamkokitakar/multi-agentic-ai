# store_policy_chunks.py

import hashlib

from sqlalchemy import text

from db import SessionLocal
from nodes.fetch_policy_node import get_all_chunks
from nodes.embedding_node import Embedder


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
        # FETCH EXISTING HASHES
        # ----------------------------------

        existing_rows = db.execute(

            text("""

                SELECT content_hash
                FROM policy_chunks

            """)

        ).fetchall()


        existing_hashes = {

            row[0]
            for row in existing_rows

        }

        print(f"\nExisting chunks in DB: {len(existing_hashes)}")


        # ----------------------------------
        # REMOVE DUPLICATES
        # ----------------------------------

        new_data = []

        for item in data:

            content = item["chunk"]

            content_hash = generate_hash(content)

            if content_hash in existing_hashes:
                continue

            item["content_hash"] = content_hash

            new_data.append(item)


        print(f"\nNew unique chunks: {len(new_data)}")


        # ----------------------------------
        # STOP IF NOTHING NEW
        # ----------------------------------

        if len(new_data) == 0:

            print("\n✅ No new chunks to insert")

            return


        # ----------------------------------
        # CREATE EMBEDDINGS ONLY FOR NEW DATA
        # ----------------------------------

        texts = [

            item["chunk"]
            for item in new_data

        ]

        embeddings = embedder.embed_batch(texts)

        print("\n✅ Embeddings generated successfully")


        # ----------------------------------
        # INSERT INTO DB
        # ----------------------------------

        for index, item in enumerate(new_data):

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

                    "policy_name": item["policy_name"],

                    "content": item["chunk"],

                    "content_hash": item["content_hash"],

                    "embedding": embeddings[index],

                    "chunk_index": index

                }

            )


        # ----------------------------------
        # COMMIT
        # ----------------------------------

        db.commit()

        print("\n✅ All new chunks stored successfully")


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