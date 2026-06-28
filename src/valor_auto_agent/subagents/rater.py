from __future__ import annotations

import asyncio
import json
import logging
import re
import statistics
from pathlib import Path

from anthropic import AsyncAnthropic
from google import genai
from google.genai import types

from valor_auto_agent.config import Settings, load
from valor_auto_agent.tools.crawler.schemas import Listing

log = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "rater.md"


def _system_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


def market_context(listings: list[Listing]) -> str:
    # a deterministic price benchmark computed once over the WHOLE search, so scores don't drift
    # with batch composition or chunking — the model is told to use these, not re-estimate them.
    prices = sorted(li.price_eur for li in listings if li.price_eur)
    if not prices:
        return ""

    def pct(p: float) -> int:
        return prices[min(len(prices) - 1, int(p * len(prices)))]

    return (
        f"fixed market reference for this search ({len(prices)} priced listings) — use these as "
        f"the price benchmark, do NOT re-estimate the median from the batch below: "
        f"median {int(statistics.median(prices))}€, p25 {pct(0.25)}€, "
        f"p75 {pct(0.75)}€, min {prices[0]}€, max {prices[-1]}€."
    )


def render_user_message(listings: list[Listing], context: str = "") -> str:
    payload = [
        {
            "source": li.source,
            "external_id": li.external_id,
            "title": li.title,
            "price_eur": li.price_eur,
            "year": li.year,
            "km": li.km,
            "fuel": li.fuel,
            "transmission": li.transmission,
            "location": li.location,
            "has_photo": bool(li.image_url),
            "url": li.url,
        }
        for li in listings
    ]
    head = f"{context}\n\n" if context else ""
    return (
        head
        + "market batch (use as comparison context):\n\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
        + "\n\nrate every listing above. return only the json array, same order"
    )


def _parse(raw: str) -> list[dict]:
    s = raw.strip()
    if s.startswith("```"):
        s = s.strip("`")
        if s.lower().startswith("json"):
            s = s[4:]
    s = s.strip()
    if not s.startswith("["):
        s = "[" + s
    return json.loads(s)


async def _rate_anthropic(settings: Settings, model: str, user_msg: str) -> str:
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    resp = await client.messages.create(
        model=model,
        max_tokens=4096,
        temperature=0.0,
        system=[
            {
                "type": "text",
                "text": _system_prompt(),
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": user_msg,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
            },
            {"role": "assistant", "content": "["},
        ],
    )
    return "".join(b.text for b in resp.content if hasattr(b, "text"))


def _gemini_client(settings: Settings) -> genai.Client:
    if settings.google_genai_use_vertexai:
        return genai.Client(
            vertexai=True,
            project=settings.google_cloud_project or None,
            location=settings.google_cloud_location or None,
        )
    return genai.Client(api_key=settings.gemini_api_key)


async def _rate_gemini(settings: Settings, model: str, user_msg: str) -> str:
    client = _gemini_client(settings)
    resp = await client.aio.models.generate_content(
        model=model,
        contents=user_msg,
        config=types.GenerateContentConfig(
            system_instruction=_system_prompt(),
            response_mime_type="application/json",
            temperature=0.0,
            seed=42,
        ),
    )
    finish = getattr((resp.candidates or [None])[0], "finish_reason", None)
    log.info("gemini finish_reason=%s text_len=%d", finish, len(resp.text or ""))
    return resp.text or ""


# rate in chunks, but cap concurrency and retry on rate-limit/overload: one giant call is slow
# and risks truncation, while firing every chunk at once trips the provider's per-minute quota.
_CHUNK = 40
_TIMEOUT_S = 90
_CONCURRENCY = 3
_MAX_ATTEMPTS = 2
_RETRY_RX = re.compile(r"retry in ([\d.]+)s")


def _retryable(e: Exception) -> bool:
    s = str(e)
    return any(k in s for k in ("429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE"))


def _retry_after(e: Exception, attempt: int) -> float:
    m = _RETRY_RX.search(str(e))
    return min(float(m.group(1)) + 1 if m else 5.0 * (attempt + 1), 30.0)


async def _call_model(settings: Settings, model: str, user_msg: str) -> str:
    if model.startswith("gemini"):
        return await asyncio.wait_for(_rate_gemini(settings, model, user_msg), _TIMEOUT_S)
    return await asyncio.wait_for(_rate_anthropic(settings, model, user_msg), _TIMEOUT_S)


async def _rate_chunk(
    settings: Settings, model: str, chunk: list[Listing], context: str, sem: asyncio.Semaphore
) -> list[dict]:
    user_msg = render_user_message(chunk, context)
    async with sem:
        for attempt in range(_MAX_ATTEMPTS):
            try:
                return _parse(await _call_model(settings, model, user_msg))
            except Exception as e:
                if _retryable(e) and attempt < _MAX_ATTEMPTS - 1:
                    delay = _retry_after(e, attempt)
                    log.warning(
                        "rate chunk (%d listings) %s — retry %d/%d in %.0fs",
                        len(chunk), type(e).__name__, attempt + 1, _MAX_ATTEMPTS - 1, delay,
                    )
                    await asyncio.sleep(delay)
                    continue
                log.warning("rate chunk failed (%d listings) — skipping: %s", len(chunk), e)
                return []
    return []


async def rate_batch(listings: list[Listing], model: str | None = None) -> list[dict]:
    if not listings:
        return []
    settings = load()
    model = model or settings.rater_model
    context = market_context(listings)  # computed over the full batch, shared by every chunk
    chunks = [listings[i : i + _CHUNK] for i in range(0, len(listings), _CHUNK)]
    sem = asyncio.Semaphore(_CONCURRENCY)
    log.info("rate_batch start: %d listings via %s in %d chunks", len(listings), model, len(chunks))
    results = await asyncio.gather(
        *(_rate_chunk(settings, model, c, context, sem) for c in chunks)
    )
    rated = [r for chunk in results for r in chunk]
    log.info("rate_batch done: parsed %d ratings", len(rated))
    return rated
