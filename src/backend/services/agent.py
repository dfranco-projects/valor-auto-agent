from __future__ import annotations

from collections.abc import AsyncIterator

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Command

from valor_auto_agent.tools.crawler.schemas import Filters

# graph nodes worth surfacing as progress phases in the ui
_PHASE_NODES = {
    "decide",
    "extract_filters",
    "collect_filters",
    "scrape",
    "rate",
    "inspect",
    "present",
    "chat",
}


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


async def _stream(graph, thread_id: str, payload) -> AsyncIterator[dict]:
    # emit a phase event when each graph node starts, then the same payload the
    # blocking endpoints return (the stream simply ends early on an interrupt)
    async for event in graph.astream_events(payload, _cfg(thread_id)):
        if event["event"] == "on_chain_start" and event["name"] in _PHASE_NODES:
            yield {"event": "phase", "node": event["name"]}
    yield {"event": "result", **await _result(graph, thread_id)}


def stream_message(graph, thread_id: str, text: str, model: str | None) -> AsyncIterator[dict]:
    return _stream(
        graph, thread_id, {"messages": [HumanMessage(content=text)], "rater_model": model}
    )


def stream_resume(graph, thread_id: str, filters: dict) -> AsyncIterator[dict]:
    return _stream(graph, thread_id, Command(resume=filters))


async def get_history(graph, thread_id: str) -> tuple[list[tuple[str, str]], list[dict]]:
    state = await graph.aget_state(_cfg(thread_id))
    history: list[tuple[str, str]] = []
    for m in state.values.get("messages", []) or []:
        if isinstance(m, HumanMessage):
            history.append(("user", str(m.content)))
        elif isinstance(m, AIMessage):
            history.append(("assistant", str(m.content)))
    return history, state.values.get("top") or []
