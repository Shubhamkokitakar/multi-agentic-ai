
from typing import TypedDict


class GraphState(TypedDict, total=False):

    question: str
    route: str
    response: str
    follow_ups: str
    history: list[dict[str, str]]
    standalone_question: str
    retrieved_docs: list[str]  # NEW