from __future__ import annotations

from dataclasses import dataclass

from app.core.tool_registry import ToolRegistry, registry as default_registry
from app.workspace.deferred_init import describe_deferred_init
from app.workspace.execution_registry import build_execution_registry
from app.workspace.history import HistoryLog
from app.workspace.models import PermissionDenial, RoutedMatch, TurnResult
from app.workspace.query_summary import DiagnosticsQueryEngine
from app.workspace.setup_context import build_setup_context


@dataclass(frozen=True)
class WorkspaceRuntimeSession:
    prompt: str
    setup_markdown: str
    deferred_lines: tuple[str, ...]
    history: HistoryLog
    routed_matches: list[RoutedMatch]
    command_messages: tuple[str, ...]
    tool_messages: tuple[str, ...]
    stream_events: tuple[dict[str, object], ...]
    diagnostics_output: str
    persisted_session_path: str

    def as_markdown(self) -> str:
        lines = [
            "# Runtime session",
            "",
            f"Prompt: {self.prompt}",
            "",
            "## Environment",
            self.setup_markdown,
            "",
            "## Startup",
            *(f"- {line}" for line in self.deferred_lines),
            "",
            "## Routed matches",
        ]
        if self.routed_matches:
            lines.extend(
                f"- [{m.kind}] {m.name} (score {m.score}) — {m.source_hint}"
                for m in self.routed_matches
            )
        else:
            lines.append("- none")
        lines.extend([
            "",
            "## HTTP surface checks",
            *(self.command_messages or ("none",)),
            "",
            "## Tool registry checks",
            *(self.tool_messages or ("none",)),
            "",
            "## Stream events",
            *(f"- {e.get('type', '?')}" for e in self.stream_events),
            "",
            "## Diagnostics turn",
            self.diagnostics_output,
            "",
            f"Persisted session: `{self.persisted_session_path}`",
            "",
            self.history.as_markdown(),
        ])
        return "\n".join(lines)


class WorkspaceRuntime:
    def __init__(self, tool_registry: ToolRegistry | None = None) -> None:
        self._registry = tool_registry or default_registry

    def route_prompt(self, prompt: str, limit: int = 5) -> list[RoutedMatch]:
        tokens = {t.lower() for t in prompt.replace("/", " ").replace("-", " ").split() if t}
        ex = build_execution_registry(self._registry)
        tool_matches: list[RoutedMatch] = []
        for t in ex.tools:
            score = _score_tokens(tokens, t.name.replace("_", " ").split())
            if score > 0:
                tool_matches.append(
                    RoutedMatch(kind="tool", name=t.name, source_hint="registered tool", score=score)
                )
        api_matches: list[RoutedMatch] = []
        for cmd in ex.api_commands:
            parts = [p for p in cmd.path.strip("/").split("/") if p]
            score = _score_tokens(tokens, parts + [cmd.method.lower()])
            if score > 0:
                api_matches.append(
                    RoutedMatch(
                        kind="http",
                        name=f"{cmd.method} {cmd.path}",
                        source_hint=cmd.description[:80],
                        score=score,
                    )
                )

        tool_matches.sort(key=lambda m: (-m.score, m.name))
        api_matches.sort(key=lambda m: (-m.score, m.name))
        merged: list[RoutedMatch] = []
        if tool_matches:
            merged.append(tool_matches[0])
        if api_matches:
            merged.append(api_matches[0])
        rest = sorted(
            tool_matches[1:] + api_matches[1:],
            key=lambda m: (-m.score, m.kind, m.name),
        )
        merged.extend(rest[: max(0, limit - len(merged))])
        return merged[:limit]

    def bootstrap_session(self, prompt: str, limit: int = 5) -> WorkspaceRuntimeSession:
        setup_md = build_setup_context()
        deferred = describe_deferred_init()
        history = HistoryLog()
        history.add("context", f"tools_registered={len(self._registry)}")
        matches = self.route_prompt(prompt, limit=limit)
        ex = build_execution_registry(self._registry)
        cmd_msgs: list[str] = []
        for m in matches:
            if m.kind == "http":
                frag = m.name.split(" ", 1)[-1] if " " in m.name else m.name
                c = ex.api_command(frag.replace("/api", "").strip("/"))
                if c:
                    cmd_msgs.append(c.execute(prompt))
        tool_msgs: list[str] = []
        for m in matches:
            if m.kind == "tool":
                th = ex.tool(m.name)
                if th:
                    tool_msgs.append(th.execute(prompt))
        denials = tuple(_infer_permission_denials(matches))
        engine = DiagnosticsQueryEngine.from_workspace(self._registry)
        stream_list: list[dict[str, object]] = []
        diagnostics_output = ""
        stop_reason = ""
        for ev in engine.stream_submit_message(
            prompt,
            matched_commands=tuple(x.name for x in matches if x.kind == "http"),
            matched_tools=tuple(x.name for x in matches if x.kind == "tool"),
            denied_tools=denials,
        ):
            stream_list.append(ev)
            if ev.get("type") == "message_delta":
                diagnostics_output = str(ev.get("text", ""))
            if ev.get("type") == "message_stop":
                stop_reason = str(ev.get("stop_reason", ""))
        path = engine.persist_session()
        history.add("routing", f"matches={len(matches)}")
        history.add("turn", f"stop={stop_reason or 'unknown'}")
        return WorkspaceRuntimeSession(
            prompt=prompt,
            setup_markdown=setup_md,
            deferred_lines=deferred.as_lines(),
            history=history,
            routed_matches=matches,
            command_messages=tuple(cmd_msgs),
            tool_messages=tuple(tool_msgs),
            stream_events=tuple(stream_list),
            diagnostics_output=diagnostics_output,
            persisted_session_path=path,
        )

    def run_turn_loop(
        self, prompt: str, limit: int = 5, max_turns: int = 3, structured_output: bool = False
    ) -> list:
        from app.workspace.models import DiagnosticsConfig

        engine = DiagnosticsQueryEngine.from_workspace(self._registry)
        engine.config = DiagnosticsConfig(max_turns=max_turns, structured_output=structured_output)
        matches = self.route_prompt(prompt, limit=limit)
        cmd_names = tuple(m.name for m in matches if m.kind == "http")
        tool_names = tuple(m.name for m in matches if m.kind == "tool")
        results: list[TurnResult] = []
        for turn in range(max_turns):
            turn_prompt = prompt if turn == 0 else f"{prompt} [turn {turn + 1}]"
            results.append(
                engine.submit_message(turn_prompt, cmd_names, tool_names, ())
            )
            if results[-1].stop_reason != "completed":
                break
        return results


def _score_tokens(tokens: set[str], parts: list[str]) -> int:
    score = 0
    for p in parts:
        pl = p.lower().strip("{}")
        if pl and pl in tokens:
            score += 2
        for tok in tokens:
            if len(tok) > 2 and tok in pl:
                score += 1
    return score


def _infer_permission_denials(matches: list[RoutedMatch]) -> list[PermissionDenial]:
    out: list[PermissionDenial] = []
    for m in matches:
        if m.kind == "tool" and m.name.lower() == "bash":
            out.append(
                PermissionDenial(
                    tool_name=m.name,
                    reason="Shell execution requires explicit approval in the agent loop",
                )
            )
    return out
