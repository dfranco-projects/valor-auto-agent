from __future__ import annotations

import uuid

from sqlalchemy import select

from valor_auto_agent.db.models import ChatSession, UiPref
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


def record_session(thread_id: str, first_message: str) -> None:
    # title the session from its first user message; later messages don't rename it
    with session() as s:
        cs = s.get(ChatSession, thread_id)
        if cs is None:
            cs = ChatSession(thread_id=thread_id)
            s.add(cs)
        if not cs.title:
            cs.title = first_message.strip()[:48] or "New chat"


def list_sessions() -> list[dict]:
    with session() as s:
        rows = s.scalars(select(ChatSession).order_by(ChatSession.updated_at.desc())).all()
        return [
            {
                "thread_id": cs.thread_id,
                "title": cs.title or "New chat",
                "updated_at": cs.updated_at.isoformat() if cs.updated_at else None,
            }
            for cs in rows
        ]
