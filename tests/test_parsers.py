from __future__ import annotations

import json
from pathlib import Path

from valor_auto_agent.tools.crawler import olx, standvirtual
from valor_auto_agent.tools.crawler.base import extract_apollo_images
from valor_auto_agent.tools.crawler.standvirtual import _parse_advert

FIXTURES = Path(__file__).parent / "fixtures"

_A = "https://ireland.apollo.olxcdn.com/v1/files"


def test_extract_apollo_images_dedupes_size_variants():
    html = (
        f'"{_A}/aaa-PT/image;s=320x240" x "{_A}/aaa-PT/image;s=1020x765" '
        f'"{_A}/bbb-PT/image;s=320x240"'
    )
    imgs = extract_apollo_images(html, limit=4)
    assert len(imgs) == 2  # the two sizes of photo "aaa" collapse to one


def test_sv_parse_advert_extracts_specs_desc_equipment_photos():
    advert = {
        "description": "<p>BMW 320d<br>1 dono</p>",
        "details": [
            {"key": "power", "label": "Potência", "value": "177 cv"},
            {"key": "color", "label": "Cor", "value": "Preto"},
        ],
        "equipment": [
            {"key": "audio", "label": "Áudio", "values": [{"key": "radio", "label": "Rádio"}]}
        ],
        "images": {"photos": [{"id": "https://img/1.jpg"}, {"id": "https://img/2.jpg"}]},
    }
    html = (
        '<html><body><script id="__NEXT_DATA__">'
        + json.dumps({"props": {"pageProps": {"advert": advert}}})
        + "</script></body></html>"
    )
    d = _parse_advert(html)
    assert d.specs["Potência"] == "177 cv"
    assert d.specs["Cor"] == "Preto"
    assert "BMW 320d" in d.description and "<" not in d.description
    assert "Rádio" in d.equipment
    assert d.images == ["https://img/1.jpg", "https://img/2.jpg"]


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
    assert c.image_url == "https://img.olx.pt/bmw-320d.jpg"
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
