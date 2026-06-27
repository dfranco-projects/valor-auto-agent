from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.deps import get_settings
from backend.schemas import ConfigOut, ModelPatch
from backend.services import sessions
from valor_auto_agent.config import Settings

MODELS = [
    "claude-opus-4-8",
    "claude-sonnet-4-6",
    "claude-haiku-4-5-20251001",
    "gemini-3.5-flash",
    "gemini-3.1-pro",
    "gemini-3.1-flash-lite",
    "gemini-2.5-pro",
    "gemini-2.5-flash",
]

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("", response_model=ConfigOut)
def get_config(settings: Settings = Depends(get_settings)):
    pref = sessions.load_pref()
    return ConfigOut(
        models=MODELS,
        default_model=pref["rater_model"] or settings.rater_model,
        anthropic_key=bool(settings.anthropic_api_key),
        gemini_key=bool(settings.gemini_api_key) or settings.google_genai_use_vertexai,
    )


@router.patch("", response_model=ConfigOut)
def patch_config(body: ModelPatch, settings: Settings = Depends(get_settings)):
    sessions.save_pref(rater_model=body.rater_model)
    return get_config(settings)
