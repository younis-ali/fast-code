from __future__ import annotations

import json
from typing import Any


def sse_event(data: Any, event: str | None = None) -> str:
    """Format a single SSE frame."""
    parts: list[str] = []
    if event:
        parts.append(f"event: {event}")
    payload = json.dumps(data) if not isinstance(data, str) else data
    parts.append(f"data: {payload}")
    parts.append("")
    parts.append("")
    return "\n".join(parts)


def sse_done() -> str:
    return "data: [DONE]\n\n"
