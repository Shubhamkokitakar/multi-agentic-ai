from typing import TypedDict

from nodes.fetch_policy_node import PolicyFetchNode
from nodes.embedding_node import EmbeddingNode
from nodes.retrieval_agent import PolicyRetrievalAgent


class GraphState(TypedDict):

    policy_chunks: list


fetch_node = PolicyFetchNode()
embedding_node = EmbeddingNode()
retrieval_agent = PolicyRetrievalAgent()


workflow = StateGraph(GraphState)


workflow.add_node(
    "fetch_policies",
    fetch_node.run
)

workflow.add_node(
    "generate_embeddings",
    embedding_node.run
)


workflow.set_entry_point(
    "fetch_policies"
)

workflow.add_edge(
    "fetch_policies",
    "generate_embeddings"
)

workflow.add_edge(
    "generate_embeddings",
    END
)


app = workflow.compile()


if __name__ == "__main__":

    app.invoke({})

    print("\nPolicy ingestion completed\n")


    query = "guaranteed weight loss claims"

    results = retrieval_agent.retrieve(query)


    print("Retrieved Context:\n")

    for row in results:

        print("Policy:", row[0])
        print("Text:", row[1][:500])
        print("Distance:", row[2])
        print("=" * 80)