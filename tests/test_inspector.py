from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace

from valor_auto_agent.subagents import inspector
from valor_auto_agent.subagents.inspector import _fetch_details, _sample
from valor_auto_agent.tools.crawler.schemas import Detail, Listing


def _li(source: str, ext: str) -> Listing:
    return Listing(source=source, external_id=ext, title=ext, url=f"https://x/{ext}")


def test_sample_returns_all_when_small():
    urls = ["a", "b", "c"]
    assert _sample(urls, 6) == urls


def test_sample_spreads_across_gallery():
    urls = [f"u{i}" for i in range(12)]
    out = _sample(urls, 6)
    assert out == ["u0", "u2", "u4", "u6", "u8", "u10"]  # even spread, starts at the first photo
    assert len(_sample([f"u{i}" for i in range(100)], 6)) == 6


@asynccontextmanager
async def _fake_browser():
    yield "ctx"


def _patch_env(monkeypatch, concurrency: int = 3) -> None:
    monkeypatch.setattr(inspector, "with_browser", _fake_browser)
    monkeypatch.setattr(
        inspector, "load", lambda: SimpleNamespace(max_detail_concurrency=concurrency)
    )


async def test_fetch_details_dispatches_by_source(monkeypatch):
    _patch_env(monkeypatch)
    calls: list[tuple[str, str]] = []

    async def fake_olx(ctx, url):
        calls.append(("olx", url))
        return Detail(description="from olx")

    async def fake_sv(ctx, url):
        calls.append(("sv", url))
        return Detail(description="from sv")

    monkeypatch.setattr(inspector.olx, "fetch_detail", fake_olx)
    monkeypatch.setattr(inspector.standvirtual, "fetch_detail", fake_sv)

    targets = [_li("olx", "1"), _li("standvirtual", "2")]
    out = await _fetch_details(targets)
    assert out[("olx", "1")].description == "from olx"
    assert out[("standvirtual", "2")].description == "from sv"
    assert sorted(calls) == [("olx", "https://x/1"), ("sv", "https://x/2")]


async def test_fetch_details_tolerates_per_listing_failures(monkeypatch):
    _patch_env(monkeypatch)

    async def fake_olx(ctx, url):
        if url.endswith("bad"):
            raise RuntimeError("boom")
        return Detail(description="ok")

    monkeypatch.setattr(inspector.olx, "fetch_detail", fake_olx)

    out = await _fetch_details([_li("olx", "good"), _li("olx", "bad")])
    assert out[("olx", "good")].description == "ok"
    assert out[("olx", "bad")] == Detail()  # failure yields an empty detail, not a crash


async def test_fetch_details_respects_max_detail_concurrency(monkeypatch):
    _patch_env(monkeypatch, concurrency=2)
    in_flight = 0
    peak = 0

    async def fake_olx(ctx, url):
        nonlocal in_flight, peak
        in_flight += 1
        peak = max(peak, in_flight)
        await asyncio.sleep(0.01)
        in_flight -= 1
        return Detail()

    monkeypatch.setattr(inspector.olx, "fetch_detail", fake_olx)

    targets = [_li("olx", str(i)) for i in range(6)]
    out = await _fetch_details(targets)
    assert len(out) == 6
    assert peak == 2  # bounded by max_detail_concurrency, but actually parallel
