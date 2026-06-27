from __future__ import annotations

from valor_auto_agent.tools.crawler.schemas import Listing
from valor_auto_agent.tools.dedupe import also_on, group_duplicates


def _li(source, ext, title, price, year, km):
    return Listing(
        source=source,  # type: ignore[arg-type]
        external_id=ext,
        title=title,
        price_eur=price,
        year=year,
        km=km,
        url=f"https://{source}.pt/{ext}",
    )


def test_groups_cross_source_duplicate():
    listings = [
        _li("olx", "1", "BMW 320d Pack M Auto", 9500, 2016, 150000),
        _li("standvirtual", "2", "BMW 320d Pack M automatic", 9800, 2016, 152000),
        _li("olx", "3", "Audi A4 2.0 TDI", 12000, 2018, 90000),
    ]
    groups = group_duplicates(listings)
    assert len(groups) == 1
    assert sorted(groups[0]) == [0, 1]  # the two BMWs, audi excluded


def test_no_match_when_year_differs():
    listings = [
        _li("olx", "1", "BMW 320d Pack M", 9500, 2016, 150000),
        _li("standvirtual", "2", "BMW 320d Pack M", 9500, 2019, 150000),
    ]
    assert group_duplicates(listings) == []


def test_same_source_not_grouped():
    listings = [
        _li("olx", "1", "BMW 320d Pack M", 9500, 2016, 150000),
        _li("olx", "2", "BMW 320d Pack M", 9600, 2016, 151000),
    ]
    assert group_duplicates(listings) == []


def test_also_on_maps_other_source():
    listings = [
        _li("olx", "1", "BMW 320d Pack M Auto", 9500, 2016, 150000),
        _li("standvirtual", "2", "BMW 320d Pack M automatic", 9800, 2016, 152000),
    ]
    mapping = also_on(listings)
    assert mapping[0] == [{"source": "standvirtual", "url": "https://standvirtual.pt/2"}]
    assert mapping[1] == [{"source": "olx", "url": "https://olx.pt/1"}]
