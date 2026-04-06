from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from app.workspace.models import SubsystemInfo

DEFAULT_APP_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class WorkspaceManifest:
    app_root: Path
    total_python_files: int
    top_level_modules: tuple[SubsystemInfo, ...]

    def to_markdown(self) -> str:
        lines = [
            f"Application root: `{self.app_root}`",
            f"Total Python files under app: **{self.total_python_files}**",
            "",
            "Top-level packages:",
        ]
        for module in self.top_level_modules:
            lines.append(f"- `{module.name}` ({module.file_count} files) — {module.notes}")
        return "\n".join(lines)


def build_workspace_manifest(app_root: Path | None = None) -> WorkspaceManifest:
    root = (app_root or DEFAULT_APP_ROOT).resolve()
    files = [p for p in root.rglob("*.py") if p.is_file() and "__pycache__" not in p.parts]
    counter: Counter[str] = Counter()
    for path in files:
        rel = path.relative_to(root)
        top = rel.parts[0] if len(rel.parts) > 1 else rel.name
        counter[top] += 1

    notes: dict[str, str] = {
        "main.py": "ASGI entrypoint",
        "config.py": "settings",
        "workspace": "orchestration and workspace introspection",
    }
    modules = tuple(
        SubsystemInfo(
            name=name,
            path=f"app/{name}" if not name.endswith(".py") else f"app/{name}",
            file_count=count,
            notes=notes.get(name, "application module"),
        )
        for name, count in counter.most_common()
    )
    return WorkspaceManifest(app_root=root, total_python_files=len(files), top_level_modules=modules)
