from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

import httpx
from google.genai import types

from valor_auto_agent.config import load
from valor_auto_agent.subagents.rater import _gemini_client
from valor_auto_agent.tools.crawler import olx, standvirtual
from valor_auto_agent.tools.crawler.base import with_browser
from valor_auto_agent.tools.crawler.schemas import Listing

log = logging.getLogger(__name__)
_PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "inspector.md"
_MAX_IMAGES = 4
_CONCURRENCY = 2
_TIMEOUT_S = 120


def _context(li: Listing, desc: str) -> str:
    specs = {
        "title": li.title,
        "price_eur": li.price_eur,
        "year": li.year,
        "km": li.km,
        "fuel": li.fuel,
        "transmission": li.transmission,
        "location": li.location,
    }
    return (
        f"listing specs: {json.dumps(specs, ensure_ascii=False)}\n\n"
        f"seller description:\n{desc[:2000] or '(none provided)'}\n\n"
        "the attached images are this listing's photos. inspect them and rate the listing."
    )


async def _fetch_details(targets: list[Listing]) -> dict[tuple[str, str], tuple[str, list[str]]]:
    out: dict[tuple[str, str], tuple[str, list[str]]] = {}
    async with with_browser() as ctx:
        for li in targets:
            fetcher = olx.fetch_detail if li.source == "olx" else standvirtual.fetch_detail
            try:
                out[(li.source, li.external_id)] = await fetcher(ctx, li.url)
            except Exception as e:
                log.warning("detail fetch failed %s: %s", li.url, e)
                out[(li.source, li.external_id)] = ("", [])
    return out


async def _download(http: httpx.AsyncClient, urls: list[str]) -> list[bytes]:
    images: list[bytes] = []
    for u in urls[:_MAX_IMAGES]:
        try:
            r = await http.get(u)
            if r.status_code == 200 and r.content:
                images.append(r.content)
        except Exception:
            continue
    return images


async def _inspect_one(
    li: Listing,
    detail: tuple[str, list[str]],
    model: str,
    sem: asyncio.Semaphore,
    http: httpx.AsyncClient,
) -> dict | None:
    desc, image_urls = detail
    async with sem:
        images = await _download(http, image_urls)
        if not images:
            return None  # nothing to look at — leave the first-pass text rating untouched
        prompt = _PROMPT_PATH.read_text(encoding="utf-8") + "\n\n" + _context(li, desc)
        parts: list[types.Part] = [types.Part.from_text(text=prompt)]
        parts += [types.Part.from_bytes(data=b, mime_type="image/jpeg") for b in images]
        client = _gemini_client(load())
        try:
            resp = await asyncio.wait_for(
                client.aio.models.generate_content(
                    model=model,
                    contents=parts,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json", temperature=0.0
                    ),
                ),
                _TIMEOUT_S,
            )
            data = json.loads(resp.text or "{}")
            return {
                "source": li.source,
                "external_id": li.external_id,
                "score": float(data["score"]),
                "rationale": str(data.get("rationale", "")),
                "photos": len(images),
            }
        except Exception as e:
            log.warning("inspect failed %s: %s", li.external_id, e)
            return None


async def inspect_listings(targets: list[Listing], model: str) -> list[dict]:
    """deep multimodal pass: fetch each ad's gallery + description and re-score from the photos."""
    if not targets:
        return []
    details = await _fetch_details(targets)
    sem = asyncio.Semaphore(_CONCURRENCY)
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as http:
        results = await asyncio.gather(
            *(
                _inspect_one(li, details[(li.source, li.external_id)], model, sem, http)
                for li in targets
            )
        )
    return [r for r in results if r]
