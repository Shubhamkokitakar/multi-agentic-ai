from datasets import load_dataset

from nodes.embedding_node import Embedder

from database.vector_store import collection


embedder = Embedder()

# -------------------------
# LOAD DATASET
# -------------------------
dataset = load_dataset(

    "catyung/cricket-qa-dataset",

    split="train"
)
print(dataset.column_names)

print(dataset[0])

# -------------------------
# CREATE DOCUMENTS
# -------------------------
documents = []

ids = []

for idx, row in enumerate(dataset):

    text = f"""

    Question:
    {row['Question']}

    Answer:
    {row['Answer']}

    """

    documents.append(text)

    ids.append(str(idx))

# -------------------------
# CREATE EMBEDDINGS
# -------------------------
embeddings = embedder.embed_batch(
    documents
)

# -------------------------
# STORE IN CHROMA
# -------------------------
collection.add(

    documents=documents,

    embeddings=embeddings,

    ids=ids
)

print("INGESTION COMPLETE")