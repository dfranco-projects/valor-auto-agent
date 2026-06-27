from __future__ import annotations

import asyncio
import json
import logging
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


def render_user_message(listings: list[Listing]) -> str:
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
            "url": li.url,
        }
        for li in listings
    ]
    return (
        "market batch (use as comparison context):\n\n"
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
        ),
    )
    finish = getattr((resp.candidates or [None])[0], "finish_reason", None)
    log.info("gemini finish_reason=%s text_len=%d", finish, len(resp.text or ""))
    return resp.text or ""


# rate in small concurrent chunks: one giant call is slow, risks output-token truncation,
# and (with no provider-side timeout) can hang the whole request.
_CHUNK = 25
_TIMEOUT_S = 90


async def _rate_chunk(settings: Settings, model: str, chunk: list[Listing]) -> list[dict]:
    user_msg = render_user_message(chunk)
    try:
        if model.startswith("gemini"):
            text = await asyncio.wait_for(_rate_gemini(settings, model, user_msg), _TIMEOUT_S)
        else:
            text = await asyncio.wait_for(_rate_anthropic(settings, model, user_msg), _TIMEOUT_S)
        return _parse(text)
    except Exception:
        log.exception("rate chunk failed (%d listings) — skipping", len(chunk))
        return []


async def rate_batch(listings: list[Listing], model: str | None = None) -> list[dict]:
    if not listings:
        return []
    settings = load()
    model = model or settings.rater_model
    chunks = [listings[i : i + _CHUNK] for i in range(0, len(listings), _CHUNK)]
    log.info("rate_batch start: %d listings via %s in %d chunks", len(listings), model, len(chunks))
    results = await asyncio.gather(*(_rate_chunk(settings, model, c) for c in chunks))
    rated = [r for chunk in results for r in chunk]
    log.info("rate_batch done: parsed %d ratings", len(rated))
    return rated
