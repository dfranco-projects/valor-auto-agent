from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Command

from valor_auto_agent.tools.crawler.schemas import Filters


def _cfg(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


async def _result(graph, thread_id: str) -> dict:
    state = await graph.aget_state(_cfg(thread_id))
    if state.next and "collect_filters" in state.next:
        return {
            "status": "need_filters",
            "reply": state.values.get("prefill_note")
            or "filters needed — confirm to start the scrape",
            "top": [],
            "filter_schema": Filters.model_json_schema(),
            "prefill": state.values.get("filters_prefill") or {},
        }
    values = state.values
    return {
        "status": "done",
        "reply": values.get("reply") or "(no reply)",
        "top": values.get("top") or [],
        "filter_schema": None,
    }


async def run_message(graph, thread_id: str, text: str, model: str | None) -> dict:
    await graph.ainvoke(
        {"messages": [HumanMessage(content=text)], "rater_model": model}, _cfg(thread_id)
    )
    return await _result(graph, thread_id)


async def resume(graph, thread_id: str, filters: dict) -> dict:
    await graph.ainvoke(Command(resume=filters), _cfg(thread_id))
    return await _result(graph, thread_id)


async def get_history(graph, thread_id: str) -> tuple[list[tuple[str, str]], list[dict]]:
    state = await graph.aget_state(_cfg(thread_id))
    history: list[tuple[str, str]] = []
    for m in state.values.get("messages", []) or []:
        if isinstance(m, HumanMessage):
            history.append(("user", str(m.content)))
        elif isinstance(m, AIMessage):
            history.append(("assistant", str(m.content)))
    return history, state.values.get("top") or []
