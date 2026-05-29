from __future__ import annotations

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    messages: Annotated[list, add_messages]
    should_scrape: bool
    filters: dict | None
    search_id: int | None
    listings: list[dict]
    ratings: list[dict]
    top: list[dict]
    reply: str | None
