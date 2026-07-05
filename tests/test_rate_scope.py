from datetime import UTC, datetime

from valor_auto_agent.graph.nodes import _rating_targets
from valor_auto_agent.tools.crawler.schemas import Listing


def _li(ext: str, price: int | None = None, year: int | None = None) -> Listing:
    return Listing(
        source="olx", external_id=ext, title=ext, price_eur=price, year=year, url=f"https://x/{ext}"
    )


LISTINGS = [_li(f"c{i}", price=1000 * (i + 1), year=2010 + i) for i in range(10)]


def test_all_and_none_scope_keep_everything():
    assert _rating_targets(LISTINGS, None, None) == LISTINGS
    assert _rating_targets(LISTINGS, "all", 50) == LISTINGS


def test_newest_keeps_recent_years():
    cutoff = datetime.now(UTC).year - 3 + 1
    recent = [_li("a", year=cutoff), _li("b", year=cutoff - 1), _li("c", year=None)]
    picked = _rating_targets(recent, "newest", 3)
    assert [li.external_id for li in picked] == ["a"]


def test_newest_empty_falls_back_to_all():
    old = [_li("a", year=2005), _li("b", year=None)]
    assert _rating_targets(old, "newest", 3) == old


def test_cheapest_takes_bottom_percentile():
    picked = _rating_targets(LISTINGS, "cheapest", 30)
    assert [li.external_id for li in picked] == ["c0", "c1", "c2"]


def test_cheapest_puts_unpriced_last():
    mixed = [_li("np"), _li("cheap", price=500), _li("dear", price=9000)]
    picked = _rating_targets(mixed, "cheapest", 33)
    assert [li.external_id for li in picked] == ["cheap"]


def test_sample_spreads_across_price_range():
    picked = _rating_targets(LISTINGS, "sample", 30)
    ids = [li.external_id for li in picked]
    assert len(ids) == 3
    assert ids[0] == "c0"
    assert ids[-1] >= "c6"  # reaches into the expensive end, not just the cheap one


def test_unknown_scope_falls_back_to_all():
    assert _rating_targets(LISTINGS, "bogus", 10) == LISTINGS
