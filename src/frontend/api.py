from __future__ import annotations

import os

import httpx

BASE = os.getenv("VALOR_API_BASE", "http://localhost:8000")


def _client() -> httpx.Client:
    # scrape+rate runs synchronously, so keep a roomy timeout
    return httpx.Client(base_url=BASE, timeout=180)


def get_config() -> dict:
    with _client() as c:
        return c.get("/api/config").json()


def patch_config(rater_model: str) -> dict:
    with _client() as c:
        return c.patch("/api/config", json={"rater_model": rater_model}).json()


def get_active_session() -> dict:
    with _client() as c:
        return c.get("/api/sessions/active").json()


def new_session() -> dict:
    with _client() as c:
        return c.post("/api/sessions/new").json()


def post_search(thread_id: str, message: str, rater_model: str | None) -> dict:
    with _client() as c:
        return c.post(
            "/api/search",
            json={"thread_id": thread_id, "message": message, "rater_model": rater_model},
        ).json()


def post_resume(thread_id: str, filters: dict) -> dict:
    with _client() as c:
        return c.post(
            "/api/search/resume", json={"thread_id": thread_id, "filters": filters}
        ).json()


def get_evaluations(
    *,
    search: str | None = None,
    sources: list[str] | None = None,
    min_score: float | None = None,
    statuses: list[str] | None = None,
) -> list[dict]:
    params: dict = {}
    if search:
        params["search"] = search
    if sources:
        params["sources"] = sources
    if min_score is not None:
        params["min_score"] = min_score
    if statuses:
        params["statuses"] = statuses
    with _client() as c:
        return c.get("/api/evaluations", params=params).json()


def patch_decision(source: str, external_id: str, status: str | None, notes: str) -> dict:
    with _client() as c:
        return c.patch(
            "/api/evaluations",
            json={"source": source, "external_id": external_id, "status": status, "notes": notes},
        ).json()
