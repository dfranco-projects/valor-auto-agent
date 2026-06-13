from __future__ import annotations

import json
from pathlib import Path

from anthropic import AsyncAnthropic
from google import genai
from google.genai import types

from valor_auto_agent.config import Settings, load
from valor_auto_agent.tools.crawler.schemas import Listing

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


async def _rate_gemini(settings: Settings, model: str, user_msg: str) -> str:
    client = genai.Client(api_key=settings.gemini_api_key)
    resp = await client.aio.models.generate_content(
        model=model,
        contents=user_msg,
        config=types.GenerateContentConfig(
            system_instruction=_system_prompt(),
            response_mime_type="application/json",
        ),
    )
    return resp.text or ""


async def rate_batch(listings: list[Listing], model: str | None = None) -> list[dict]:
    if not listings:
        return []
    settings = load()
    model = model or settings.rater_model
    user_msg = render_user_message(listings)
    if model.startswith("gemini"):
        text = await _rate_gemini(settings, model, user_msg)
    else:
        text = await _rate_anthropic(settings, model, user_msg)
    return _parse(text)
