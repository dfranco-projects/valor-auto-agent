from __future__ import annotations

from valor_auto_agent.tools.crawler import olx, standvirtual
from valor_auto_agent.tools.crawler.schemas import Filters


def test_olx_url_contains_filters():
    url = olx.build_url(
        Filters(brand="bmw", price_min=5000, price_max=15000, year_min=2015, km_max=150000), page=2
    )
    assert url.startswith("https://www.olx.pt/d/carros-motos-e-barcos/carros/bmw")
    assert "filter_float_price%3Afrom%5D=5000" in url
    assert "filter_float_price%3Ato%5D=15000" in url
    assert "filter_float_year%3Afrom%5D=2015" in url
    assert "filter_float_mileage%3Ato%5D=150000" in url
    assert "page=2" in url


def test_standvirtual_url_contains_filters():
    url = standvirtual.build_url(
        Filters(brand="audi", model="a4", price_max=25000, year_min=2018, fuel="gasolina")
    )
    assert url.startswith("https://www.standvirtual.com/carros/audi/a4")
    assert "filter_float_price%3Ato%5D=25000" in url
    assert "filter_float_first_registration_year%3Afrom%5D=2018" in url
    # standvirtual uses english fuel slugs, so our "gasolina" maps to "petrol"
    assert "filter_enum_fuel_type%5D%5B0%5D=petrol" in url
