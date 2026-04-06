from __future__ import annotations

from typing import Any

from app.core.tool_registry import registry
from app.models.tools import ToolResult
from app.tools.base import BaseTool

# In-memory per-session storage (keyed by a pseudo session; single-server only)
_todos: dict[str, dict[str, Any]] = {}


class TodoWriteTool(BaseTool):
    name = "TodoWrite"
    description = (
        "Create and manage a structured task list. Each todo has an id, content, and "
        "status (pending, in_progress, completed, cancelled). Use merge=true to update "
        "existing todos, merge=false to replace all."
    )
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "todos": {
                "type": "array",
                "description": "Array of TODO items with id, content, and status.",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "content": {"type": "string"},
                        "status": {
                            "type": "string",
                            "enum": ["pending", "in_progress", "completed", "cancelled"],
                        },
                    },
                    "required": ["id", "content", "status"],
                },
            },
            "merge": {
                "type": "boolean",
                "description": "If true, merge into existing todos. If false, replace all.",
            },
        },
        "required": ["todos", "merge"],
    }

    async def call(self, tool_input: dict[str, Any], *, tool_use_id: str = "") -> ToolResult:
        todos = tool_input["todos"]
        merge = tool_input["merge"]

        if merge:
            for item in todos:
                _todos[item["id"]] = item
        else:
            _todos.clear()
            for item in todos:
                _todos[item["id"]] = item

        summary_lines = []
        for tid, item in _todos.items():
            status = item.get("status", "pending").upper()
            content = item.get("content", "")
            summary_lines.append(f"- [{status}] {content} (id: {tid})")

        return ToolResult(
            tool_use_id=tool_use_id,
            content="Updated TODO list:\n" + "\n".join(summary_lines) if summary_lines else "TODO list is empty.",
        )


registry.register(TodoWriteTool())
