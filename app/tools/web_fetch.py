from __future__ import annotations

import re
from typing import Any

import httpx

from app.core.tool_registry import registry
from app.models.tools import ToolResult
from app.tools.base import BaseTool

MAX_RESPONSE_SIZE = 500_000
TIMEOUT = 30


class WebFetchTool(BaseTool):
    name = "WebFetch"
    description = (
        "Fetch content from a URL and return it as readable text. Strips HTML tags for "
        "web pages. Returns raw text for non-HTML content."
    )
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL to fetch.",
            },
        },
        "required": ["url"],
    }
    is_read_only = True

    async def call(self, tool_input: dict[str, Any], *, tool_use_id: str = "") -> ToolResult:
        url = tool_input["url"]

        if not url.startswith(("http://", "https://")):
            return ToolResult(
                tool_use_id=tool_use_id,
                content="URL must start with http:// or https://",
                is_error=True,
            )

        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=TIMEOUT,
                headers={"User-Agent": "FastCode/1.0"},
            ) as client:
                resp = await client.get(url)
                resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            return ToolResult(
                tool_use_id=tool_use_id,
                content=f"HTTP {exc.response.status_code}: {exc.response.reason_phrase}",
                is_error=True,
            )
        except httpx.RequestError as exc:
            return ToolResult(
                tool_use_id=tool_use_id,
                content=f"Request failed: {exc}",
                is_error=True,
            )

        content_type = resp.headers.get("content-type", "")
        text = resp.text

        if "html" in content_type:
            text = _strip_html(text)

        if len(text) > MAX_RESPONSE_SIZE:
            text = text[:MAX_RESPONSE_SIZE] + "\n... [truncated]"

        return ToolResult(tool_use_id=tool_use_id, content=text)


def _strip_html(html: str) -> str:
    """Rough HTML-to-text conversion."""
    # Remove script and style blocks
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
    # Convert common block elements to newlines
    html = re.sub(r"<(br|hr|p|div|h[1-6]|li|tr)[^>]*>", "\n", html, flags=re.IGNORECASE)
    # Strip remaining tags
    html = re.sub(r"<[^>]+>", "", html)
    # Collapse whitespace
    html = re.sub(r"\n{3,}", "\n\n", html)
    html = re.sub(r"[ \t]+", " ", html)
    # Decode common entities
    for entity, char in [("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&nbsp;", " "), ("&quot;", '"')]:
        html = html.replace(entity, char)
    return html.strip()


registry.register(WebFetchTool())
