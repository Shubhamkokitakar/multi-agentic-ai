async def live_node(state: GraphState):

    result = await live_agent(

        state["question"]
    )

    state["response"] = result

    return state