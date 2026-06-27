from __future__ import annotations

import os
import time

import httpx

BASE = os.getenv("VALOR_API_BASE", "http://localhost:8000")


class ApiError(Exception):
    pass


def _call(method: str, path: str, *, retries: int = 20, **kwargs):
    # the backend may still be starting (or restarting); retry connection refusals
    last: Exception | None = None
    for _ in range(retries):
        try:
            with httpx.Client(base_url=BASE, timeout=180) as c:
                r = c.request(method, path, **kwargs)
                if r.status_code >= 400:
                    detail = r.text[:300] or r.reason_phrase
                    raise ApiError(f"backend error {r.status_code}: {detail}")
                return r.json()
        except httpx.ConnectError as e:
            last = e
            time.sleep(0.5)
    raise last  # type: ignore[misc]


def get_config() -> dict:
    return _call("GET", "/api/config")


def patch_config(rater_model: str) -> dict:
    return _call("PATCH", "/api/config", json={"rater_model": rater_model})


def get_active_session() -> dict:
    return _call("GET", "/api/sessions/active")


def get_sessions() -> list[dict]:
    return _call("GET", "/api/sessions")


def get_session(thread_id: str) -> dict:
    return _call("GET", f"/api/sessions/{thread_id}")


def new_session() -> dict:
    return _call("POST", "/api/sessions/new")


def post_search(thread_id: str, message: str, rater_model: str | None) -> dict:
    return _call(
        "POST",
        "/api/search",
        json={"thread_id": thread_id, "message": message, "rater_model": rater_model},
    )


def post_resume(thread_id: str, filters: dict) -> dict:
    return _call("POST", "/api/search/resume", json={"thread_id": thread_id, "filters": filters})


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
    return _call("GET", "/api/evaluations", params=params)


def patch_decision(source: str, external_id: str, status: str | None, notes: str) -> dict:
    return _call(
        "PATCH",
        "/api/evaluations",
        json={"source": source, "external_id": external_id, "status": status, "notes": notes},
    )
