from __future__ import annotations

from dataclasses import dataclass

from app.core.tool_registry import ToolRegistry
from app.workspace.execution_registry import _tool_category


@dataclass(frozen=True)
class ToolPool:
    tools: tuple[str, ...]
    simple_mode: bool
    include_delegated: bool

    def as_markdown(self) -> str:
        lines = [
            "# Tool pool",
            "",
            f"Simple mode (hide delegated tools): **{self.simple_mode}**",
            f"Include delegated tools: **{self.include_delegated}**",
            f"Tool count: **{len(self.tools)}**",
            "",
        ]
        lines.extend(f"- {name}" for name in self.tools[:24])
        if len(self.tools) > 24:
            lines.append(f"- … and {len(self.tools) - 24} more")
        return "\n".join(lines)


def assemble_tool_pool(
    registry: ToolRegistry,
    *,
    simple_mode: bool = False,
    include_delegated: bool = True,
) -> ToolPool:
    names: list[str] = []
    skip_delegated = simple_mode or not include_delegated
    for name in sorted(registry._tools.keys()):
        if skip_delegated and _tool_category(name) == "delegated":
            continue
        names.append(name)
    return ToolPool(
        tools=tuple(names),
        simple_mode=simple_mode,
        include_delegated=include_delegated,
    )
