from __future__ import annotations

import urllib.parse
from typing import Any

import httpx

from app.core.tool_registry import registry
from app.models.tools import ToolResult
from app.tools.base import BaseTool


class WebSearchTool(BaseTool):
    name = "WebSearch"
    description = (
        "Search the web for information. Returns summarized search results. "
        "Use when you need up-to-date information."
    )
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query.",
            },
        },
        "required": ["query"],
    }
    is_read_only = True

    async def call(self, tool_input: dict[str, Any], *, tool_use_id: str = "") -> ToolResult:
        query = tool_input["query"]

        # Use DuckDuckGo HTML (no API key needed)
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote_plus(query)}"

        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=15,
                headers={"User-Agent": "FastCode/1.0"},
            ) as client:
                resp = await client.get(url)
                resp.raise_for_status()
        except httpx.RequestError as exc:
            return ToolResult(
                tool_use_id=tool_use_id,
                content=f"Search request failed: {exc}",
                is_error=True,
            )

        text = resp.text
        results = _parse_ddg_results(text)

        if not results:
            return ToolResult(
                tool_use_id=tool_use_id,
                content=f"No results found for: {query}",
            )

        return ToolResult(tool_use_id=tool_use_id, content=results)


def _parse_ddg_results(html: str) -> str:
    """Extract search results from DuckDuckGo HTML response."""
    import re

    results: list[str] = []
    # Extract result snippets between result__snippet class tags
    snippets = re.findall(
        r'class="result__snippet"[^>]*>(.*?)</a>',
        html,
        re.DOTALL,
    )
    titles = re.findall(
        r'class="result__a"[^>]*>(.*?)</a>',
        html,
        re.DOTALL,
    )
    urls = re.findall(
        r'class="result__url"[^>]*>(.*?)</a>',
        html,
        re.DOTALL,
    )

    for i in range(min(len(titles), 8)):
        title = re.sub(r"<[^>]+>", "", titles[i]).strip()
        snippet = re.sub(r"<[^>]+>", "", snippets[i]).strip() if i < len(snippets) else ""
        link = re.sub(r"<[^>]+>", "", urls[i]).strip() if i < len(urls) else ""
        results.append(f"{i+1}. {title}\n   {link}\n   {snippet}")

    return "\n\n".join(results) if results else ""


registry.register(WebSearchTool())
