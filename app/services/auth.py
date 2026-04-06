from __future__ import annotations

from app.config import settings


def is_auth_enabled() -> bool:
    return bool(settings.auth_token)


def validate_token(token: str) -> bool:
    if not settings.auth_token:
        return True
    return token == settings.auth_token
