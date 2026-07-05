"""Offline end-to-end tests of the LangGraph graph.

Compiles the real graph topology with an in-memory checkpointer and monkeypatches every
external effect (LLM calls, crawler, rater, snapshots) so the full search flow — including
the `interrupt()` pause at collect_filters and the `Command(resume=...)` resume — runs
without network, browser, or API keys.
"""

from __future__ import annotations

import importlib
from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from valor_auto_agent.config import Settings
from valor_auto_agent.db import session as session_mod
from valor_auto_agent.graph import nodes
from valor_auto_agent.graph.builder import _stategraph
from valor_auto_agent.tools.crawler.schemas import Filters, Listing

CFG = {"configurable": {"thread_id": "t1"}}


def _li(ext: str, source: str = "olx", price: int = 9000) -> Listing:
    return Listing(
        source=source,  # type: ignore[arg-type]
        external_id=ext,
        title=f"bmw 320d {ext}",
        price_eur=price,
        url=f"https://example.pt/{ext}",
    )


@pytest.fixture
def graph_env(tmp_path, monkeypatch):
    """Isolated db + offline settings + a compiled graph with an in-memory checkpointer."""
    monkeypatch.setenv("VALOR_DB_URL", f"sqlite:///{tmp_path}/t.db")
    monkeypatch.setenv("VALOR_SNAPSHOTS_DIR", str(tmp_path / "snaps"))
    session_mod._engine = None
    session_mod._factory = None
    importlib.reload(session_mod)

    settings = Settings(
        _env_file=None,
        anthropic_api_key="",
        gemini_api_key="",
        db_url=f"sqlite:///{tmp_path}/t.db",
        snapshots_dir=tmp_path / "snaps",
        rater_model="claude-haiku-4-5",  # non-gemini so `inspect` no-ops
    )
    monkeypatch.setattr(nodes, "load", lambda: settings)
    monkeypatch.setattr(nodes, "snapshot_search", lambda *a, **k: None)
    monkeypatch.setattr(nodes, "recall_defaults", lambda *a, **k: {})
    monkeypatch.setattr(nodes, "remember", lambda *a, **k: None)

    crawl_calls: list[Filters] = []
    listings = [_li("1", price=8500), _li("2", source="standvirtual", price=9500)]

    async def fake_crawl(filters):
        crawl_calls.append(filters)
        return listings

    monkeypatch.setattr(nodes.pipeline, "crawl", fake_crawl)

    async def fake_rate_batch(ls, model=None, lang=None):
        return [
            {
                "source": li.source,
                "external_id": li.external_id,
                "score": 9.0 - i,
                "rationale": "ok",
            }
            for i, li in enumerate(ls)
        ]

    monkeypatch.setattr(nodes, "rate_batch", fake_rate_batch)

    async def fake_extract(text, model):
        return {"brand": "bmw", "model": "320d", "price_max": 10000, "lang": "en"}

    monkeypatch.setattr(nodes, "_extract", fake_extract)

    graph = _stategraph().compile(checkpointer=InMemorySaver())
    return SimpleNamespace(graph=graph, settings=settings, crawl_calls=crawl_calls)


async def test_full_search_flow_interrupt_and_resume(graph_env):
    graph = graph_env.graph

    # 1) user message -> decide routes to search -> extract_filters -> interrupt at collect_filters
    result = await graph.ainvoke(
        {"messages": [HumanMessage(content="find me a bmw 320d under 10k")]}, CFG
    )
    interrupts = result.get("__interrupt__")
    assert interrupts, "graph should pause at collect_filters"
    payload = interrupts[0].value
    assert payload["need"] == "filters"
    assert payload["prefill"] == {"brand": "bmw", "model": "320d", "price_max": 10000}
    assert "properties" in payload["schema"]
    assert payload["note"]  # prefill note surfaced for the ui

    state = await graph.aget_state(CFG)
    assert "collect_filters" in state.next
    assert not graph_env.crawl_calls  # nothing scraped before the user confirms

    # 2) resume with confirmed filters -> scrape -> rate -> inspect (no-op) -> present
    filters = {"brand": "bmw", "model": "320d", "price_max": 10000}
    result = await graph.ainvoke(Command(resume=filters), CFG)

    assert "__interrupt__" not in result
    assert [f.model_dump(exclude_none=True) for f in graph_env.crawl_calls] == [filters]
    assert result["filters"] == filters
    assert result["search_id"] is not None

    top = result["top"]
    assert [t["external_id"] for t in top] == ["1", "2"]  # sorted by fake score desc
    assert top[0]["score"] == 9.0
    assert not top[0]["inspected"]  # inspect no-ops for non-gemini models

    assert "found 2 matches" in result["reply"]
    last = result["messages"][-1]
    assert isinstance(last, AIMessage)
    assert last.content == result["reply"]


async def test_chat_route_skips_scrape(graph_env, monkeypatch):
    graph_env.settings.anthropic_api_key = "test-key"

    class FakeMessages:
        async def create(self, **kw):
            text = "chat" if kw.get("system") == nodes.CLASSIFY_SYS else "hey there!"
            return SimpleNamespace(content=[SimpleNamespace(text=text)])

    class FakeAnthropic:
        def __init__(self, api_key=None):
            self.messages = FakeMessages()

    monkeypatch.setattr(nodes, "AsyncAnthropic", FakeAnthropic)

    result = await graph_env.graph.ainvoke(
        {"messages": [HumanMessage(content="hello, how are you?")]}, CFG
    )

    assert "__interrupt__" not in result
    assert result["should_scrape"] is False
    assert result["reply"] == "hey there!"
    assert isinstance(result["messages"][-1], AIMessage)
    assert not graph_env.crawl_calls  # crawler never invoked on the chat branch
    assert "top" not in result
