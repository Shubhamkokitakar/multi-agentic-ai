async def generic_agent(state):

    question = state["question"].lower().strip()

    responses = {
        "hi": "Hi! How can I help you with cricket today?",
        "hello": "Hello! Ask me anything about cricket.",
        "hey": "Hey! How can I help you with cricket?",
        "thanks": "You're welcome!",
        "thank you": "You're welcome!",
        "good morning": "Good morning! How can I help you with cricket?",
        "good evening": "Good evening! How can I help you with cricket?",
        "how are you": "I'm doing well! How can I help you with cricket?"
    }

    if question in responses:
        response = responses[question]
    else:
        response = "I'm here to help with cricket-related questions."

    state["response"] = response

    return state