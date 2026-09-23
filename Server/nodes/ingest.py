from nodes.chunking import Chunker
from nodes.embeddings import Embedder

from datasets import load_dataset
from langchain_core.documents import Document
from database.vector_store import VectorStore


# --------------------------------------------------
# 1. LOAD DATASET
# --------------------------------------------------

dataset = load_dataset(
    "catyung/cricket-qa-dataset",
    split="train"
)

print("Columns:", dataset.column_names)
print("First row:", dataset[0])


# --------------------------------------------------
# 2. CREATE DOCUMENTS
# --------------------------------------------------

documents = []

for row in dataset:

    text = f"""
Question:
{row['Question']}

Answer:
{row['Answer']}
"""

    documents.append(
        Document(
            page_content=text,
            metadata={
                "source": "cricket-qa-dataset"
            }
        )
    )

print("\nDocuments created:", len(documents))


# --------------------------------------------------
# 3. CHUNKING
# --------------------------------------------------

chunker = Chunker()

chunks = chunker.split_documents(documents)

print("\nTotal chunks:", len(chunks))


# --------------------------------------------------
# 4. PRINT CHUNKS
# --------------------------------------------------

print("\n========== CHUNKS ==========")

for i, chunk in enumerate(chunks[:10]):

    print(f"\n--- Chunk {i} ---")
    print(chunk.page_content)

    print("Metadata:")
    print(chunk.metadata)


# --------------------------------------------------
# 5. CREATE EMBEDDINGS
# --------------------------------------------------

embedder = Embedder()

embeddings = embedder.embed_documents(chunks)


# --------------------------------------------------
# 6. PRINT EMBEDDINGS
# --------------------------------------------------

print("\n========== EMBEDDINGS ==========")

for i, embedding in enumerate(embeddings[:10]):

    print(f"\n--- Embedding {i} ---")

    print("Dimensions:", len(embedding))

    # Print only first 10 values
    print("First 10 values:", embedding[:10])


# --------------------------------------------------
# 7. STORE IN CHROMA
# --------------------------------------------------

vector_store = VectorStore()


ids = [
    str(i)
    for i in range(len(chunks))
]

vector_store.add_documents(
    documents=[
        chunk.page_content
        for chunk in chunks
    ],
    embeddings=embeddings,
    ids=ids
)

print("\nINGESTION COMPLETE")