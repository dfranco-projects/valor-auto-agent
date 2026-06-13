from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.deps import get_graph
from backend.schemas import SessionOut
from backend.services import agent, sessions

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("/active", response_model=SessionOut)
def active(graph=Depends(get_graph)):
    pref = sessions.load_pref()
    thread_id = pref["active_thread_id"] or sessions.new_thread()
    history, top = agent.get_history(graph, thread_id)
    return SessionOut(
        thread_id=thread_id, history=history, top=top, rater_model=pref["rater_model"]
    )


@router.post("/new", response_model=SessionOut)
def new():
    thread_id = sessions.new_thread()
    return SessionOut(thread_id=thread_id, rater_model=sessions.load_pref()["rater_model"])
