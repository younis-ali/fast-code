from __future__ import annotations

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

_bearer_scheme = HTTPBearer(auto_error=False)


async def verify_auth(
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer_scheme),
) -> str | None:
    """If AUTH_TOKEN is set, require a matching Bearer token. Otherwise pass-through."""
    if not settings.auth_token:
        return None
    if credentials is None or credentials.credentials != settings.auth_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing authentication token",
        )
    return credentials.credentials


def require_api_key() -> str:
    """Raise if no LLM API key is configured (Anthropic and/or OpenAI)."""
    if not settings.anthropic_api_key and not settings.openai_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Configure ANTHROPIC_API_KEY and/or OPENAI_API_KEY",
        )
    return settings.anthropic_api_key or settings.openai_api_key
