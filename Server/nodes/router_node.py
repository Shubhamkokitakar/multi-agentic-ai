import re
from langchain_core.callbacks.manager import adispatch_custom_event
from graph.state import GraphState


# ----------------------------
# LIVE INTENT PATTERNS
# ----------------------------
LIVE_PATTERNS = [
    r"\blive\s+(cricket\s+)?match(es)?\b",
    r"\bcurrent\s+(cricket\s+)?match(es)?\b",
    r"\blive\s+score(s)?\b",
    r"\bcurrent\s+score(s)?\b",
    r"\blatest\s+score(s)?\b",
    r"\blatest\s+(cricket\s+)?match(es)?\b",
    r"\btoday'?s\s+(cricket\s+)?match(es)?\b",
    r"\btoday\s+(cricket\s+)?match(es)?\b",
    r"\bmatch(es)?\s+today\b",
    r"\bmatch(es)?\s+currently\s+playing\b",
    r"\bcurrently\s+playing\b",
    r"\bbeing\s+played\s+now\b",
]


# ----------------------------
# GENERIC / GREETING PATTERNS
# ----------------------------
GREETING_REGEX = (
    r"^(hi|hello|hey|thanks|thank you|good morning|"
    r"good evening|how are you)(\s+\w+){0,3}$"
)


def is_generic_message(question: str) -> bool:
    """
    Returns True when the user's message is primarily
    a greeting or simple social interaction.
    """

    question = question.lower().strip()

    # Remove punctuation
    normalized = re.sub(r"[^\w\s]", "", question)

    return bool(re.match(GREETING_REGEX, normalized))


# ----------------------------
# ROUTER NODE
# ----------------------------
async def router_node(state: GraphState):

    await adispatch_custom_event(
        "stage",
        {
            "type": "stage",
            "stage": "intent_detection",
            "message": "Analyzing question..."
        },
    )



    question = state.get(
        "standalone_question",
        state["question"]
    ).lower().strip()

    # ----------------------------
    # GENERIC ROUTE
    # ----------------------------
    if is_generic_message(question):

        state["route"] = "generic"
        state["stage"] = "greeting_detected"

        return state

    # ----------------------------
    # LIVE ROUTE
    # ----------------------------
    if any(
        re.search(pattern, question)
        for pattern in LIVE_PATTERNS
    ):

        state["route"] = "live"

        return state

    # ----------------------------
    # RAG ROUTE
    # ----------------------------
    state["route"] = "rag"

    return state