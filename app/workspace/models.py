from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SubsystemInfo:
    name: str
    path: str
    file_count: int
    notes: str


@dataclass(frozen=True)
class RoutedMatch:
    kind: str
    name: str
    source_hint: str
    score: int


@dataclass(frozen=True)
class PermissionDenial:
    tool_name: str
    reason: str


@dataclass
class UsageSummary:
    input_tokens: int = 0
    output_tokens: int = 0

    def add_turn(self, prompt: str, output: str) -> UsageSummary:
        return UsageSummary(
            input_tokens=self.input_tokens + max(1, len(prompt.split())),
            output_tokens=self.output_tokens + max(1, len(output.split())),
        )


@dataclass(frozen=True)
class ApiRouteDef:
    method: str
    path: str
    description: str


@dataclass(frozen=True)
class ToolSurfaceEntry:
    name: str
    description: str
    category: str


@dataclass
class TurnResult:
    prompt: str
    output: str
    matched_commands: tuple[str, ...]
    matched_tools: tuple[str, ...]
    permission_denials: tuple[PermissionDenial, ...]
    usage: UsageSummary
    stop_reason: str


@dataclass
class DiagnosticsConfig:
    max_turns: int = 8
    max_budget_tokens: int = 2000
    compact_after_turns: int = 12
    structured_output: bool = False
    structured_retry_limit: int = 2
