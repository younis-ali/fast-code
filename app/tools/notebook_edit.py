from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.tool_registry import registry
from app.models.tools import ToolResult
from app.tools.base import BaseTool


class NotebookEditTool(BaseTool):
    name = "NotebookEdit"
    description = (
        "Edit a Jupyter notebook cell. Can edit existing cells or create new ones. "
        "For existing cells set is_new_cell=false and provide old_string+new_string. "
        "For new cells set is_new_cell=true and provide new_string."
    )
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "notebook_path": {
                "type": "string",
                "description": "Path to the .ipynb notebook file.",
            },
            "cell_idx": {
                "type": "integer",
                "description": "0-based index of the cell to edit or insert at.",
            },
            "is_new_cell": {
                "type": "boolean",
                "description": "If true, create a new cell at cell_idx.",
            },
            "cell_language": {
                "type": "string",
                "description": "Language of the cell: python, markdown, etc.",
            },
            "old_string": {
                "type": "string",
                "description": "Text to replace in existing cell (required if is_new_cell=false).",
            },
            "new_string": {
                "type": "string",
                "description": "Replacement or new cell content.",
            },
        },
        "required": ["notebook_path", "cell_idx", "is_new_cell", "new_string"],
    }

    async def call(self, tool_input: dict[str, Any], *, tool_use_id: str = "") -> ToolResult:
        nb_path = Path(tool_input["notebook_path"]).resolve()
        cell_idx: int = tool_input["cell_idx"]
        is_new_cell: bool = tool_input["is_new_cell"]
        new_string: str = tool_input["new_string"]
        old_string: str = tool_input.get("old_string", "")
        cell_language: str = tool_input.get("cell_language", "python")

        if not nb_path.exists():
            if is_new_cell and cell_idx == 0:
                # Create new notebook
                nb = {
                    "nbformat": 4,
                    "nbformat_minor": 5,
                    "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}},
                    "cells": [],
                }
            else:
                return ToolResult(tool_use_id=tool_use_id, content=f"Notebook not found: {nb_path}", is_error=True)
        else:
            try:
                nb = json.loads(nb_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                return ToolResult(tool_use_id=tool_use_id, content=f"Cannot read notebook: {exc}", is_error=True)

        cells = nb.get("cells", [])

        if is_new_cell:
            cell_type = "code" if cell_language in ("python", "javascript", "r", "sql", "shell") else "markdown"
            new_cell = {
                "cell_type": cell_type,
                "metadata": {},
                "source": new_string.splitlines(keepends=True),
                "outputs": [] if cell_type == "code" else None,
            }
            if cell_type == "code":
                new_cell["execution_count"] = None
            else:
                new_cell.pop("outputs", None)
            cells.insert(cell_idx, new_cell)
        else:
            if cell_idx < 0 or cell_idx >= len(cells):
                return ToolResult(
                    tool_use_id=tool_use_id,
                    content=f"Cell index {cell_idx} out of range (notebook has {len(cells)} cells).",
                    is_error=True,
                )

            cell = cells[cell_idx]
            source = "".join(cell.get("source", []))

            if old_string and old_string not in source:
                return ToolResult(
                    tool_use_id=tool_use_id,
                    content=f"old_string not found in cell {cell_idx}.",
                    is_error=True,
                )

            if old_string:
                new_source = source.replace(old_string, new_string, 1)
            else:
                new_source = new_string

            cell["source"] = new_source.splitlines(keepends=True)

        nb["cells"] = cells

        try:
            nb_path.parent.mkdir(parents=True, exist_ok=True)
            nb_path.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        except OSError as exc:
            return ToolResult(tool_use_id=tool_use_id, content=str(exc), is_error=True)

        action = "Created new cell" if is_new_cell else "Edited cell"
        return ToolResult(tool_use_id=tool_use_id, content=f"{action} {cell_idx} in {nb_path}")


registry.register(NotebookEditTool())
