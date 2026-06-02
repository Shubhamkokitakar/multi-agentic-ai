import re

from graph.state import GraphState

LIVE_KEYWORDS = [
    "live",
    "score",
    "today",
    "current",
    "latest",
    "ipl"
]

GENERIC_PATTERNS = [
    r"hi",
    r"hello",
    r"hey",
    r"thanks",
    r"thank you",
    r"good morning",
    r"good evening",
    r"how are you"
]


def is_generic_message(question: str) -> bool:
    """
    Returns True only when the user's message is primarily
    a greeting/social interaction and not an actual question.
    """

    question = question.lower().strip()

    # Remove punctuation
    normalized = re.sub(r"[^\w\s]", "", question)

    # Exact greeting match
    if normalized in GENERIC_PATTERNS:
        return True

    # Allow simple variants such as:
    # "hi there"
    # "hello bot"
    # "hey buddy"
    greeting_regex = (
        r"^(hi|hello|hey|thanks|thank you|good morning|"
        r"good evening|how are you)(\s+\w+){0,3}$"
    )

    return bool(re.match(greeting_regex, normalized))


# ----------------------------
# ROUTER NODE
# ----------------------------
async def router_node(state: GraphState):


    question = state.get(
        "standalone_question",
        state["question"]
    ).lower().strip()

    # ----------------------------
    # GENERIC ROUTE
    # ----------------------------
    if is_generic_message(question):

        state["route"] = "generic"
        return state


    # ----------------------------
    # LIVE ROUTE
    # ----------------------------
    if any(
        re.search(rf"\b{re.escape(k)}\b", question)
        for k in LIVE_KEYWORDS
    ):

        state["route"] = "live"
        return state


    # ----------------------------
    # RAG ROUTE
    # ----------------------------
    else:

        state["route"] = "rag"

    return state