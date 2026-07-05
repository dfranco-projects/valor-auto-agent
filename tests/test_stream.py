from __future__ import annotations

import asyncio
import importlib
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend.services import agent
from valor_auto_agent.db import session as session_mod


class FakeGraph:
    """Stand-in exposing just what agent._stream touches."""

    def __init__(self, node_names: list[str], state_values: dict, state_next: tuple = ()):
        self._nodes = node_names
        self._state = SimpleNamespace(values=state_values, next=state_next)

    async def astream_events(self, payload, cfg):
        for name in self._nodes:
            yield {"event": "on_chain_start", "name": name}
            yield {"event": "on_chain_end", "name": name}

    async def aget_state(self, cfg):
        return self._state


def _collect(gen):
    async def run():
        return [evt async for evt in gen]

    return asyncio.run(run())


def test_stream_message_emits_phases_then_result():
    graph = FakeGraph(
        ["LangGraph", "decide", "scrape", "rate", "present", "ChannelWrite"],
        {"reply": "here you go", "top": [{"title": "bmw"}]},
    )
    events = _collect(agent.stream_message(graph, "t1", "find a bmw", None))

    assert [e["node"] for e in events[:-1] if e["event"] == "phase"] == [
        "decide",
        "scrape",
        "rate",
        "present",
    ]
    final = events[-1]
    assert final["event"] == "result"
    assert final["status"] == "done"
    assert final["top"] == [{"title": "bmw"}]


def test_stream_result_carries_need_filters_interrupt():
    graph = FakeGraph(
        ["decide", "extract_filters", "collect_filters"],
        {"filters_prefill": {"brand": "bmw"}},
        state_next=("collect_filters",),
    )
    events = _collect(agent.stream_resume(graph, "t1", {"brand": "bmw"}))

    final = events[-1]
    assert final["event"] == "result"
    assert final["status"] == "need_filters"
    assert final["prefill"] == {"brand": "bmw"}
    assert final["filter_schema"]


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("VALOR_DB_URL", f"sqlite:///{tmp_path}/t.db")
    monkeypatch.setenv("VALOR_CHECKPOINT_DB", str(tmp_path / "c.db"))
    monkeypatch.setenv("VALOR_SNAPSHOTS_DIR", str(tmp_path / "snaps"))
    session_mod._engine = None
    session_mod._factory = None
    importlib.reload(session_mod)

    from backend.deps import get_graph
    from backend.main import create_app

    app = create_app()
    app.dependency_overrides[get_graph] = lambda: FakeGraph(["decide", "chat"], {"reply": "hello"})
    with TestClient(app) as c:
        yield c


def test_stream_endpoint_returns_sse_frames(client):
    with client.stream(
        "POST",
        "/api/search/stream",
        json={"thread_id": "t-sse", "message": "hi", "rater_model": None},
    ) as res:
        assert res.status_code == 200
        assert res.headers["content-type"].startswith("text/event-stream")
        body = "".join(res.iter_text())

    frames = [json.loads(f[6:]) for f in body.strip().split("\n\n") if f.startswith("data: ")]
    assert [f["event"] for f in frames] == ["phase", "phase", "result"]
    assert frames[-1]["status"] == "done"
    assert frames[-1]["reply"] == "hello"
