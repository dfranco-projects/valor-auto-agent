from __future__ import annotations

from pathlib import Path

from valor_auto_agent.tools.crawler import olx, standvirtual

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_olx_card():
    html = (FIXTURES / "olx_card.html").read_text()
    cards = olx.parse_cards(html)
    assert len(cards) == 1
    c = cards[0]
    assert c.source == "olx"
    assert "BMW 320d" in c.title
    assert c.price_eur == 14500
    assert c.year == 2018
    assert c.km == 120000
    assert c.fuel == "diesel"
    assert c.url.endswith("ID12345.html")
    assert c.external_id == "bmw-320d-2018-ID12345.html"


def test_parse_standvirtual_card():
    html = (FIXTURES / "standvirtual_card.html").read_text()
    cards = standvirtual.parse_cards(html)
    assert len(cards) == 1
    c = cards[0]
    assert c.source == "standvirtual"
    assert "Audi A4" in c.title
    assert c.price_eur == 22900
    assert c.year == 2019
    assert c.km == 85000
    assert c.fuel == "gasolina"
    assert c.transmission == "automatica"
    assert c.external_id == "SV-9001"
