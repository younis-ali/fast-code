from __future__ import annotations

from fastapi import APIRouter

from app.config import settings

router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    return {
        "status": "ok",
        "version": "1.0.0",
        "default_models": {
            "anthropic": settings.anthropic_model,
            "openai": settings.openai_model,
        },
        "api_keys_configured": {
            "anthropic": bool(settings.anthropic_api_key),
            "openai": bool(settings.openai_api_key),
        },
        "auth_enabled": bool(settings.auth_token),
    }
