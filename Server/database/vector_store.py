import chromadb
from nodes.embedding_node import Embedder

client = chromadb.PersistentClient(path="./vector_db")

collection = client.get_or_create_collection(
    name="cricket_data"
)
print(collection,'collection')

embedder = Embedder()


def insert_documents(documents):

    embeddings = embedder.embed_batch(documents)

    ids = [

        f"id_{i}"

        for i in range(len(documents))
    ]

    collection.add(

        documents=documents,
        embeddings=embeddings,
        ids=ids
    )
    print(collection, 'collection of documents after embedding')


def search_documents(query):

    query_embedding = embedder.embed_batch([query])[0]

    results = collection.query(

        query_embeddings=[query_embedding],
        n_results=3
    )
    print(results,'resullts of embedding')

    return results["documents"][0]