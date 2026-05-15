from typing import TypedDict
from langgraph.graph import END, StateGraph

from nodes.fetch_policy_node import PolicyFetchNode
from nodes.embedding_node import EmbeddingNode
from nodes.retrival_agent import PolicyRetrievalAgent

class GraphState(TypedDict):
    policy_chunks: list


policy_Fetch_node = PolicyFetchNode()
embedding_node = EmbeddingNode()
policy_retrieval_agent = PolicyRetrievalAgent()


workflow = StateGraph(GraphState)


workflow.add_node(
    "fetch_policies",
    policy_Fetch_node.run
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

    results = policy_retrieval_agent.retrieve(query)


    print("Retrieved Context:\n")

    for row in results:

        print("Policy:", row[0])
        print("Text:", row[1][:500])
        print("Distance:", row[2])
        print("=" * 80)