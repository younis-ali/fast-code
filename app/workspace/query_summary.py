from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from app.config import settings
from app.core.tool_registry import ToolRegistry, registry as default_registry
from app.workspace.command_graph import build_command_graph
from app.workspace.deferred_init import describe_deferred_init
from app.workspace.execution_registry import (
    API_ROUTE_SURFACE,
    build_execution_registry,
    tool_surface_entries,
)
from app.workspace.manifest import WorkspaceManifest, build_workspace_manifest
from app.workspace.models import DiagnosticsConfig, PermissionDenial, TurnResult, UsageSummary
from app.workspace.tool_pool import assemble_tool_pool
from app.workspace.transcript import TranscriptStore


@dataclass
class WorkspaceQuerySummary:
    """Read-only workspace report (manifest, HTTP surface, tool surface)."""

    manifest: WorkspaceManifest
    tool_registry: ToolRegistry

    @classmethod
    def from_app(cls, reg: ToolRegistry | None = None) -> WorkspaceQuerySummary:
        return cls(manifest=build_workspace_manifest(), tool_registry=reg or default_registry)

    def render_summary(self) -> str:
        ex = build_execution_registry(self.tool_registry)
        pool = assemble_tool_pool(self.tool_registry)
        graph = build_command_graph(self.tool_registry)
        surface = tool_surface_entries(self.tool_registry)
        deferred = describe_deferred_init()

        sections: list[str] = [
            "# Fast Code workspace summary",
            "",
            self.manifest.to_markdown(),
            "",
            f"HTTP surface: **{len(API_ROUTE_SURFACE)}** routes",
            *(f"- `{r.method}` {r.path} — {r.description}" for r in API_ROUTE_SURFACE[:12]),
            "",
            f"Tool surface: **{len(surface)}** registered tools",
            *(
                (
                    f"- **{e.name}** [{e.category}] — {e.description[:120]}…"
                    if len(e.description) > 120
                    else f"- **{e.name}** [{e.category}] — {e.description}"
                )
                for e in surface[:12]
            ),
            "",
            "Deferred startup:",
            *deferred.as_lines(),
            "",
            graph.as_markdown(),
            "",
            pool.as_markdown(),
            "",
            f"Execution registry: **{len(ex.tools)}** tool handles, **{len(ex.api_commands)}** HTTP entries",
        ]
        return "\n".join(s for s in sections if s is not None)


@dataclass
class DiagnosticsQueryEngine:
    """Lightweight multi-turn transcript for local diagnostics (no LLM calls)."""

    manifest: WorkspaceManifest
    config: DiagnosticsConfig = field(default_factory=DiagnosticsConfig)
    session_id: str = field(default_factory=lambda: uuid4().hex)
    mutable_messages: list[str] = field(default_factory=list)
    permission_denials: list[PermissionDenial] = field(default_factory=list)
    total_usage: UsageSummary = field(default_factory=UsageSummary)
    transcript_store: TranscriptStore = field(default_factory=TranscriptStore)
    tool_registry: ToolRegistry = field(default_factory=lambda: default_registry)

    @classmethod
    def from_workspace(cls, reg: ToolRegistry | None = None) -> DiagnosticsQueryEngine:
        return cls(manifest=build_workspace_manifest(), tool_registry=reg or default_registry)

    def submit_message(
        self,
        prompt: str,
        matched_commands: tuple[str, ...] = (),
        matched_tools: tuple[str, ...] = (),
        denied_tools: tuple[PermissionDenial, ...] = (),
    ) -> TurnResult:
        if len(self.mutable_messages) >= self.config.max_turns:
            output = f"Max turns reached before processing prompt: {prompt}"
            return TurnResult(
                prompt=prompt,
                output=output,
                matched_commands=matched_commands,
                matched_tools=matched_tools,
                permission_denials=tuple(denied_tools),
                usage=self.total_usage,
                stop_reason="max_turns_reached",
            )

        summary_lines = [
            f"Prompt: {prompt}",
            f"Matched HTTP hints: {', '.join(matched_commands) if matched_commands else 'none'}",
            f"Matched tools: {', '.join(matched_tools) if matched_tools else 'none'}",
            f"Permission denials: {len(denied_tools)}",
        ]
        output = self._format_output(summary_lines)
        projected = self.total_usage.add_turn(prompt, output)
        stop_reason = "completed"
        if projected.input_tokens + projected.output_tokens > self.config.max_budget_tokens:
            stop_reason = "max_budget_reached"

        self.mutable_messages.append(prompt)
        self.transcript_store.append(prompt)
        self.permission_denials.extend(denied_tools)
        self.total_usage = projected
        self.compact_messages_if_needed()

        return TurnResult(
            prompt=prompt,
            output=output,
            matched_commands=matched_commands,
            matched_tools=matched_tools,
            permission_denials=tuple(denied_tools),
            usage=self.total_usage,
            stop_reason=stop_reason,
        )

    def stream_submit_message(
        self,
        prompt: str,
        matched_commands: tuple[str, ...] = (),
        matched_tools: tuple[str, ...] = (),
        denied_tools: tuple[PermissionDenial, ...] = (),
    ):
        yield {"type": "message_start", "session_id": self.session_id, "prompt": prompt}
        if matched_commands:
            yield {"type": "http_match", "paths": matched_commands}
        if matched_tools:
            yield {"type": "tool_match", "tools": matched_tools}
        if denied_tools:
            yield {"type": "permission_denial", "denials": [d.tool_name for d in denied_tools]}
        result = self.submit_message(prompt, matched_commands, matched_tools, denied_tools)
        yield {"type": "message_delta", "text": result.output}
        yield {
            "type": "message_stop",
            "usage": {
                "input_tokens": result.usage.input_tokens,
                "output_tokens": result.usage.output_tokens,
            },
            "stop_reason": result.stop_reason,
            "transcript_size": len(self.transcript_store.entries),
        }

    def compact_messages_if_needed(self) -> None:
        if len(self.mutable_messages) > self.config.compact_after_turns:
            self.mutable_messages[:] = self.mutable_messages[-self.config.compact_after_turns :]
        self.transcript_store.compact(self.config.compact_after_turns)

    def flush_transcript(self) -> None:
        self.transcript_store.flush()

    def persist_session(self) -> str:
        self.flush_transcript()
        path = Path(settings.data_dir) / f"workspace_session_{self.session_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "session_id": self.session_id,
            "messages": list(self.mutable_messages),
            "input_tokens": self.total_usage.input_tokens,
            "output_tokens": self.total_usage.output_tokens,
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return str(path)

    def _format_output(self, summary_lines: list[str]) -> str:
        if self.config.structured_output:
            payload = {"summary": summary_lines, "session_id": self.session_id}
            for _ in range(self.config.structured_retry_limit):
                try:
                    return json.dumps(payload, indent=2)
                except (TypeError, ValueError):
                    payload = {"summary": ["structured output retry"], "session_id": self.session_id}
            return json.dumps(payload)
        return "\n".join(summary_lines)
