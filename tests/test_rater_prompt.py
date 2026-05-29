from __future__ import annotations

from valor_auto_agent.subagents.rater import _system_prompt, render_user_message
from valor_auto_agent.tools.crawler.schemas import Listing


def test_system_prompt_has_rubric():
    p = _system_prompt()
    assert "0-10" in p
    assert "km-per-year" in p
    assert "json" in p.lower()


def test_user_message_contains_batch():
    listings = [
        Listing(
            source="olx",
            external_id="1",
            title="bmw 320d",
            price_eur=14500,
            year=2018,
            km=120000,
            url="https://olx.pt/x",
        ),
        Listing(
            source="standvirtual",
            external_id="2",
            title="audi a4",
            price_eur=22900,
            year=2019,
            km=85000,
            url="https://standvirtual.com/y",
        ),
    ]
    msg = render_user_message(listings)
    assert "market batch" in msg
    assert "bmw 320d" in msg
    assert "audi a4" in msg
    assert "14500" in msg
    assert "85000" in msg
