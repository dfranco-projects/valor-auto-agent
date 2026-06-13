from __future__ import annotations

from fastapi import APIRouter, Query

from backend.schemas import DecisionIn, EvaluationOut
from backend.services import evaluations

router = APIRouter(prefix="/api", tags=["evaluations"])


@router.get("/evaluations", response_model=list[EvaluationOut])
def get_evaluations(
    search: str | None = None,
    sources: list[str] | None = Query(default=None),
    min_score: float | None = None,
    statuses: list[str] | None = Query(default=None),
):
    return evaluations.list_evaluations(
        search=search, sources=sources, min_score=min_score, statuses=statuses
    )


@router.patch("/evaluations")
def patch_decision(body: DecisionIn):
    evaluations.set_decision(body.source, body.external_id, body.status, body.notes)
    return {"ok": True}
