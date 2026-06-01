from graph.state import GraphState

LIVE_KEYWORDS = [
    "live",
    "score",
    "today",
    "current",
    "latest",
    "ipl"
]

GENERIC_KEYWORDS = [
    "hi",
    "hello",
    "hey",
    "thanks",
    "thank you",
    "good morning",
    "good evening",
    "how are you"
]


# ----------------------------
# ROUTER NODE
# ----------------------------
async def router_node(state: GraphState):

    stage_callback = state.get("stage_callback")

    # Send stage from node itself
    if stage_callback:
        await stage_callback(
            "Understanding your question..."
        )

    question = state.get(
        "standalone_question",
        state["question"]
    ).lower().strip()

    # ----------------------------
    # GENERIC ROUTE
    # ----------------------------
    if any(k in question for k in GENERIC_KEYWORDS):

        state["route"] = "generic"
        state["stage"] = "greeting_detected"
        state["route_reason"] = "greeting_match"
        state["route_confidence"] = 1.0

    # ----------------------------
    # LIVE ROUTE
    # ----------------------------
    elif any(k in question for k in LIVE_KEYWORDS):

        state["route"] = "live"
        state["stage"] = "live_intent_detected"
        state["route_reason"] = "keyword_live_match"
        state["route_confidence"] = 0.8

    # ----------------------------
    # RAG ROUTE
    # ----------------------------
    else:

        state["route"] = "rag"
        state["stage"] = "knowledge_intent_detected"
        state["route_reason"] = "default_fallback"
        state["route_confidence"] = 0.5

    return state