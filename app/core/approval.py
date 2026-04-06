from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

READ_ONLY_TOOLS = frozenset({
    "Read", "Glob", "Grep", "WebFetch", "WebSearch", "TodoWrite",
})


@dataclass
class PendingApproval:
    request_id: str
    tool_calls: list[dict[str, Any]]
    event: asyncio.Event = field(default_factory=asyncio.Event)
    approved: bool = False
    approved_ids: set[str] = field(default_factory=set)
    denied_ids: set[str] = field(default_factory=set)


_pending: dict[str, PendingApproval] = {}


def needs_approval(tool_calls: list[dict[str, Any]]) -> bool:
    """Return True if any tool in the list requires user approval."""
    return any(tc.get("name") not in READ_ONLY_TOOLS for tc in tool_calls)


def create_approval_request(tool_calls: list[dict[str, Any]]) -> PendingApproval:
    """Register a new pending approval and return it."""
    req_id = uuid.uuid4().hex[:12]
    pa = PendingApproval(request_id=req_id, tool_calls=tool_calls)
    _pending[req_id] = pa
    return pa


def resolve_approval(request_id: str, *, approve_all: bool = False,
                     approved_ids: list[str] | None = None,
                     denied_ids: list[str] | None = None) -> bool:
    """Resolve a pending approval.  Returns False if not found."""
    pa = _pending.get(request_id)
    if pa is None:
        return False

    if approve_all:
        pa.approved = True
        pa.approved_ids = {tc["id"] for tc in pa.tool_calls}
    else:
        pa.approved_ids = set(approved_ids or [])
        pa.denied_ids = set(denied_ids or [])
        pa.approved = len(pa.approved_ids) > 0

    pa.event.set()
    return True


def cleanup_approval(request_id: str) -> None:
    _pending.pop(request_id, None)
