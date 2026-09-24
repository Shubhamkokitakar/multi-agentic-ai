import chromadb


class VectorStore:

    def __init__(self, collection_name="cricket_data"):

        self.client = chromadb.PersistentClient(
            path="./vector_db"
        )

        self.collection = self.client.get_or_create_collection(
            name=collection_name
        )

    def add_documents(self, documents, embeddings, ids):

        self.collection.add(
            documents=documents,
            embeddings=embeddings,
            ids=ids
        )

    def search_documents(self, query_embedding, n_results=3):
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )

        return results

    def count(self):

        return self.collection.count()