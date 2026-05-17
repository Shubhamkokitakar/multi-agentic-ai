async def rag_node(state: GraphState):

    result = await rag_agent(

        state["question"]
    )

    state["response"] = result

    return state