async def generic_agent(state):

    question = state["question"].lower()

    responses = {

        "hi": "Hi! How can I help you with cricket today?",

        "hello": "Hello! Ask me anything about cricket.",

        "thanks": "You're welcome!"
    }

    response = responses.get(

        question,

        "Hello! How can I help you?"
    )

    state["response"] = response

    return state