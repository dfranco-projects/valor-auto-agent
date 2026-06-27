from __future__ import annotations

from fastapi import APIRouter

from backend.schemas import AlertOut, SavedSearchIn, SavedSearchOut
from valor_auto_agent import saved

router = APIRouter(prefix="/api", tags=["saved"])


@router.get("/saved-searches", response_model=list[SavedSearchOut])
def index():
    return saved.list_saved()


@router.post("/saved-searches", response_model=SavedSearchOut)
def create(body: SavedSearchIn):
    return saved.create_saved(body.name, body.filters, body.cadence_minutes)


@router.delete("/saved-searches/{saved_id}")
def remove(saved_id: int):
    saved.delete_saved(saved_id)
    return {"ok": True}


@router.post("/saved-searches/{saved_id}/run", response_model=list[AlertOut])
async def run(saved_id: int):
    return await saved.run_saved(saved_id)


@router.get("/alerts", response_model=list[AlertOut])
def alerts(unread_only: bool = False):
    return saved.list_alerts(unread_only=unread_only)


@router.post("/alerts/{alert_id}/read")
def read(alert_id: int):
    saved.mark_alert_read(alert_id)
    return {"ok": True}
