from __future__ import annotations

import uuid

from valor_auto_agent.db.models import UiPref
from valor_auto_agent.db.session import session


def load_pref() -> dict:
    with session() as s:
        p = s.get(UiPref, 1)
        if p is None:
            return {"active_thread_id": None, "rater_model": None}
        return {"active_thread_id": p.active_thread_id, "rater_model": p.rater_model}


def save_pref(active_thread_id: str | None = None, rater_model: str | None = None) -> None:
    with session() as s:
        p = s.get(UiPref, 1)
        if p is None:
            p = UiPref(id=1)
            s.add(p)
        if active_thread_id is not None:
            p.active_thread_id = active_thread_id
        if rater_model is not None:
            p.rater_model = rater_model


def new_thread() -> str:
    thread_id = str(uuid.uuid4())
    save_pref(active_thread_id=thread_id)
    return thread_id
