from __future__ import annotations

from valor_auto_agent import pipeline
from valor_auto_agent.pipeline import _model_match
from valor_auto_agent.tools.crawler.schemas import Filters, Listing


def test_model_number_token_match():
    # "320d" keeps 3-series 320 variants, drops other models
    assert _model_match("BMW 320 ver d Pack M", "320d")
    assert _model_match("BMW 320d Touring", "320d")
    assert not _model_match("BMW 116 i Confort", "320d")
    assert not _model_match("BMW 318 d LifeStyle", "320d")
    assert not _model_match("BMW i3 60 Ah", "320d")


def test_model_word_match_when_no_number():
    assert _model_match("VW Golf 1.6 TDI", "golf")
    assert not _model_match("VW Polo 1.0", "golf")


def _li(ext: str, title: str, km: int | None) -> Listing:
    return Listing(source="olx", external_id=ext, title=title, km=km, url=f"https://x/{ext}")


async def test_crawl_applies_model_and_km_filters(monkeypatch):
    sample = [
        _li("1", "BMW 320d", 100000),
        _li("2", "BMW 116d", 90000),
        _li("3", "BMW 320d high km", 300000),
        _li("4", "BMW 320d unknown km", None),
    ]

    async def fake_olx(_f):
        return sample

    async def fake_sv(_f):
        return []

    monkeypatch.setattr(pipeline.olx, "search", fake_olx)
    monkeypatch.setattr(pipeline.standvirtual, "search", fake_sv)

    out = await pipeline.crawl(Filters(model="320d", km_max=250000))
    # "2" dropped by model, "3" dropped by km_max, "4" kept (km unknown)
    assert sorted(li.external_id for li in out) == ["1", "4"]
