from __future__ import annotations

from dataclasses import dataclass

from app.core.tool_registry import ToolRegistry
from app.workspace.execution_registry import _tool_category


@dataclass(frozen=True)
class CommandGraph:
    core_tools: tuple[str, ...]
    network_tools: tuple[str, ...]
    delegated_tools: tuple[str, ...]

    def as_markdown(self) -> str:
        lines = [
            "# Tool graph",
            "",
            f"Core file/shell tools: **{len(self.core_tools)}**",
            f"Network tools: **{len(self.network_tools)}**",
            f"Delegated / multi-step tools: **{len(self.delegated_tools)}**",
            "",
            "Core:",
            *(f"- {n}" for n in self.core_tools),
            "",
            "Network:",
            *(f"- {n}" for n in self.network_tools),
            "",
            "Delegated:",
            *(f"- {n}" for n in self.delegated_tools),
        ]
        return "\n".join(lines)


def build_command_graph(registry: ToolRegistry) -> CommandGraph:
    core: list[str] = []
    network: list[str] = []
    delegated: list[str] = []
    for name in sorted(registry._tools.keys()):
        cat = _tool_category(name)
        if cat == "network":
            network.append(name)
        elif cat == "delegated":
            delegated.append(name)
        else:
            core.append(name)
    return CommandGraph(
        core_tools=tuple(core),
        network_tools=tuple(network),
        delegated_tools=tuple(delegated),
    )
