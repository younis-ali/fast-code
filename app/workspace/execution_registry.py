from __future__ import annotations

from dataclasses import dataclass

from app.core.tool_registry import ToolRegistry
from app.workspace.models import ApiRouteDef, ToolSurfaceEntry


# HTTP surface exposed by Fast Code (mirrors router registration in app.main).
API_ROUTE_SURFACE: tuple[ApiRouteDef, ...] = (
    ApiRouteDef("GET", "/health", "Liveness check"),
    ApiRouteDef("GET", "/", "Web UI"),
    ApiRouteDef("POST", "/api/chat", "Streaming chat (SSE)"),
    ApiRouteDef("POST", "/api/tool-approve", "Approve or deny pending tools"),
    ApiRouteDef("GET", "/api/files/list", "List workspace files for UI"),
    ApiRouteDef("GET", "/api/files/read", "Read a file (auth optional)"),
    ApiRouteDef("POST", "/api/files/write", "Write a file (auth optional)"),
    ApiRouteDef("GET", "/api/conversations", "List conversations"),
    ApiRouteDef("POST", "/api/conversations", "Create conversation"),
    ApiRouteDef("GET", "/api/conversations/{id}", "Get conversation"),
    ApiRouteDef("DELETE", "/api/conversations/{id}", "Delete conversation"),
    ApiRouteDef("GET", "/api/sessions", "List sessions"),
    ApiRouteDef("POST", "/api/sessions", "Create session"),
    ApiRouteDef("GET", "/api/sessions/{id}", "Get session"),
    ApiRouteDef("DELETE", "/api/sessions/{id}", "Delete session"),
    ApiRouteDef("GET", "/api/tools", "List tool definitions"),
    ApiRouteDef("GET", "/api/workspace/summary", "Workspace markdown summary"),
    ApiRouteDef("GET", "/api/workspace/audit", "Structure audit JSON"),
    ApiRouteDef("GET", "/mcp/health", "MCP server health"),
    ApiRouteDef("GET", "/mcp/tools", "MCP tool listing"),
)


@dataclass(frozen=True)
class RegisteredToolHandle:
    name: str
    description: str

    def execute(self, payload: str) -> str:
        """Dry-run style message for diagnostics (does not invoke the LLM or shell)."""
        return f"Registered tool {self.name!r} (payload length {len(payload)} chars)"


@dataclass(frozen=True)
class RegisteredApiCommand:
    method: str
    path: str
    description: str

    def execute(self, prompt: str) -> str:
        return f"HTTP {self.method} {self.path} — {self.description} (hint: {prompt[:80]!r})"


@dataclass(frozen=True)
class ExecutionRegistry:
    tools: tuple[RegisteredToolHandle, ...]
    api_commands: tuple[RegisteredApiCommand, ...]

    def tool(self, name: str) -> RegisteredToolHandle | None:
        lowered = name.lower()
        for t in self.tools:
            if t.name.lower() == lowered:
                return t
        return None

    def api_command(self, path_fragment: str) -> RegisteredApiCommand | None:
        frag = path_fragment.strip().lower()
        for c in self.api_commands:
            if frag in c.path.lower():
                return c
        return None


def _tool_category(name: str) -> str:
    if name in ("Agent", "Coder"):
        return "delegated"
    if name in ("WebFetch", "WebSearch"):
        return "network"
    return "core"


def build_execution_registry(registry: ToolRegistry) -> ExecutionRegistry:
    tools: list[RegisteredToolHandle] = []
    for t in sorted(registry._tools.values(), key=lambda x: x.name):
        tools.append(RegisteredToolHandle(name=t.name, description=(t.description or "")[:200]))
    api_cmds = tuple(
        RegisteredApiCommand(method=r.method, path=r.path, description=r.description)
        for r in API_ROUTE_SURFACE
    )
    return ExecutionRegistry(tools=tuple(tools), api_commands=api_cmds)


def tool_surface_entries(registry: ToolRegistry) -> tuple[ToolSurfaceEntry, ...]:
    out: list[ToolSurfaceEntry] = []
    for t in sorted(registry._tools.values(), key=lambda x: x.name):
        out.append(
            ToolSurfaceEntry(
                name=t.name,
                description=(t.description or "")[:240],
                category=_tool_category(t.name),
            )
        )
    return tuple(out)
