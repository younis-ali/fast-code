from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Expected layout for a healthy Fast Code tree (relative to project root).
EXPECTED_FILES: tuple[str, ...] = (
    "app/main.py",
    "app/config.py",
    "app/core/query_engine.py",
    "app/core/tool_registry.py",
    "app/workspace/manifest.py",
    "app/workspace/query_summary.py",
    "web/templates/index.html",
    "pyproject.toml",
)


@dataclass(frozen=True)
class StructureAuditResult:
    project_root: Path
    present: tuple[str, ...]
    missing: tuple[str, ...]

    @property
    def coverage(self) -> tuple[int, int]:
        n = len(EXPECTED_FILES)
        ok = len(self.present)
        return (ok, n)

    def to_markdown(self) -> str:
        cov = self.coverage
        lines = [
            "# Structure audit",
            "",
            f"Coverage: **{cov[0]}/{cov[1]}** expected paths",
            f"Project root: `{self.project_root}`",
            "",
            "Present:",
            *(f"- `{p}`" for p in self.present),
        ]
        if self.missing:
            lines.extend(["", "Missing:", *(f"- `{m}`" for m in self.missing)])
        return "\n".join(lines)

    def to_dict(self) -> dict[str, object]:
        return {
            "project_root": str(self.project_root),
            "coverage": {"ok": self.coverage[0], "total": self.coverage[1]},
            "present": list(self.present),
            "missing": list(self.missing),
        }


def run_structure_audit(root: Path | None = None) -> StructureAuditResult:
    base = (root or PROJECT_ROOT).resolve()
    present: list[str] = []
    missing: list[str] = []
    for rel in EXPECTED_FILES:
        if (base / rel).is_file():
            present.append(rel)
        else:
            missing.append(rel)
    return StructureAuditResult(
        project_root=base,
        present=tuple(present),
        missing=tuple(missing),
    )
