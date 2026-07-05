from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from valor_auto_agent.config import load
from valor_auto_agent.db.models import Listing, Search


def snapshot_search(search_id: int, sess: Session) -> Path:
    settings = load()
    search = sess.get(Search, search_id)
    if search is None:
        raise ValueError(f"search {search_id} not found")

    listings = sess.scalars(
        select(Listing).where(Listing.search_id == search_id).order_by(Listing.source, Listing.id)
    ).all()

    date = (search.created_at or datetime.now(UTC)).strftime("%Y-%m-%d")
    out = settings.snapshots_dir / f"{search_id:04d}-{date}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(_render(search, listings), encoding="utf-8")
    return out


def _render(search: Search, listings: Sequence[Listing]) -> str:
    lines: list[str] = []
    lines.append(f"# search {search.id}")
    lines.append("")
    lines.append(f"- created_at: {search.created_at}")
    lines.append(f"- status: {search.status}")
    lines.append(f"- sources: {search.sources}")
    lines.append(f"- scrape_started_at: {search.scrape_started_at}")
    lines.append(f"- scrape_ended_at: {search.scrape_ended_at}")
    lines.append("")
    lines.append("## filters")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(search.filters_json, indent=2, ensure_ascii=False))
    lines.append("```")
    lines.append("")
    lines.append(f"## listings ({len(listings)})")
    lines.append("")
    lines.append("| source | title | year | km | price € | rating | location | url |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for li in listings:
        score = f"{li.rating.score:.1f}" if li.rating else ""
        title = (li.title or "").replace("|", "/")[:80]
        lines.append(
            f"| {li.source} | {title} | {li.year or ''} | {li.km or ''} | "
            f"{li.price_eur or ''} | {score} | {li.location or ''} | {li.url} |"
        )
    lines.append("")

    rated = [(li, li.rating) for li in listings if li.rating is not None]
    if rated:
        rated.sort(key=lambda p: p[1].score, reverse=True)
        lines.append("## rationale (top 10)")
        lines.append("")
        for li, rating in rated[:10]:
            lines.append(f"### {li.title} — {rating.score:.1f}")
            lines.append("")
            lines.append(rating.rationale)
            lines.append("")
            lines.append(f"<{li.url}>")
            lines.append("")
    return "\n".join(lines)
