from __future__ import annotations

import json
import uuid
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field, create_model

from app.core.tool_registry import ToolRegistry
from app.models.tools import ToolResult
from app.tools.base import BaseTool


def _schema_to_pydantic(name: str, schema: dict[str, Any]) -> type[BaseModel]:
    """Build a loose Pydantic model from JSON Schema (top-level object properties)."""
    props = schema.get("properties") or {}
    required = set(schema.get("required") or [])
    field_defs: dict[str, Any] = {}
    for key, spec in props.items():
        desc = (spec or {}).get("description", "") or ""
        if key in required:
            field_defs[key] = (Any, Field(..., description=desc))
        else:
            field_defs[key] = (Any, Field(default=None, description=desc))
    if not field_defs:
        return create_model(f"{name}Args", __base__=BaseModel)
    return create_model(f"{name}Args", **field_defs)


def base_tool_to_structured_tool(bt: BaseTool) -> StructuredTool:
    """Wrap a Fast Code BaseTool as a LangChain StructuredTool."""

    args_schema = _schema_to_pydantic(bt.name, bt.input_schema if bt.input_schema.get("type") == "object" else {"type": "object", "properties": {}})

    async def _arun(**kwargs: Any) -> str:
        tid = f"toolu_{uuid.uuid4().hex[:24]}"
        cleaned = {k: v for k, v in kwargs.items() if v is not None or k in (bt.input_schema.get("required") or [])}
        res: ToolResult = await bt.call(cleaned, tool_use_id=tid)
        if isinstance(res.content, str):
            return res.content
        return json.dumps(res.content)

    return StructuredTool(
        name=bt.name,
        description=bt.description or "",
        coroutine=_arun,
        args_schema=args_schema,
    )


def registry_tools_to_langchain(
    registry: ToolRegistry,
    allowed_names: frozenset[str] | None = None,
) -> list[StructuredTool]:
    """Registered tools as LangChain StructuredTool instances, optionally filtered by name."""
    tools: list[StructuredTool] = []
    for t in sorted(registry._tools.values(), key=lambda x: x.name):
        if allowed_names is not None and t.name not in allowed_names:
            continue
        tools.append(base_tool_to_structured_tool(t))
    return tools
