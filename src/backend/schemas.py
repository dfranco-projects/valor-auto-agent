from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class SearchRequest(BaseModel):
    thread_id: str
    message: str
    rater_model: str | None = None


class ResumeRequest(BaseModel):
    thread_id: str
    filters: dict


class SearchResponse(BaseModel):
    status: Literal["need_filters", "done"]
    reply: str | None = None
    top: list[dict] = []
    filter_schema: dict | None = None
    prefill: dict = {}


class EvaluationOut(BaseModel):
    source: str
    external_id: str
    brand: str | None = None
    model: str | None = None
    title: str
    year: int | None = None
    km: int | None = None
    price_eur: int | None = None
    fuel: str | None = None
    transmission: str | None = None
    location: str | None = None
    score: float
    rationale: str
    rated_by: str
    rated_at: str | None = None
    status: str | None = None
    notes: str = ""
    url: str


class DecisionIn(BaseModel):
    source: str
    external_id: str
    status: str | None = None
    notes: str = ""


class SessionOut(BaseModel):
    thread_id: str
    history: list[tuple[str, str]] = []
    top: list[dict] = []
    rater_model: str | None = None


class SessionMeta(BaseModel):
    thread_id: str
    title: str
    updated_at: str | None = None


class ConfigOut(BaseModel):
    models: list[str]
    default_model: str
    anthropic_key: bool
    gemini_key: bool


class ModelPatch(BaseModel):
    rater_model: str
