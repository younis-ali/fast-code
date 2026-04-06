from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DeferredInitResult:
    """Steps normally run during application startup (after settings load)."""

    database_ready: bool
    tools_discovered: bool
    static_files_mounted: bool
    web_templates_present: bool

    def as_lines(self) -> tuple[str, ...]:
        return (
            f"- database_ready={self.database_ready}",
            f"- tools_discovered={self.tools_discovered}",
            f"- static_files_mounted={self.static_files_mounted}",
            f"- web_templates_present={self.web_templates_present}",
        )


def describe_deferred_init(app_root: Path | None = None) -> DeferredInitResult:
    """Describe what the Fast Code server expects to have completed at startup."""
    root = app_root or Path(__file__).resolve().parent.parent
    project_root = root.parent
    web_static = project_root / "web" / "static"
    web_templates = project_root / "web" / "templates"
    return DeferredInitResult(
        database_ready=True,
        tools_discovered=True,
        static_files_mounted=web_static.is_dir(),
        web_templates_present=web_templates.is_dir(),
    )
