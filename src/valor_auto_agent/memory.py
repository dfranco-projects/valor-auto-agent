from __future__ import annotations

from valor_auto_agent.db.models import UserMemory
from valor_auto_agent.db.session import session

DEFAULT_USER = "default"

# stable preferences worth remembering to pre-fill future searches. `model` is intentionally
# excluded — it's too query-specific (e.g. "320d") to carry into an unrelated next search.
_REMEMBERED = (
    "brand",
    "year_min",
    "year_max",
    "price_min",
    "price_max",
    "km_max",
    "fuel",
    "transmission",
    "location",
)


def recall_defaults(user_id: str = DEFAULT_USER) -> dict:
    with session() as s:
        row = s.get(UserMemory, user_id)
        return dict(row.prefs_json) if row and row.prefs_json else {}


def remember(filters: dict, user_id: str = DEFAULT_USER) -> None:
    sticky = {
        k: v for k, v in (filters or {}).items() if k in _REMEMBERED and v not in (None, "")
    }
    if not sticky:
        return
    with session() as s:
        row = s.get(UserMemory, user_id)
        if row is None:
            row = UserMemory(user_id=user_id, prefs_json={})
            s.add(row)
        row.prefs_json = {**(row.prefs_json or {}), **sticky}
