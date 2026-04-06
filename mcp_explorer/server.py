from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from mcp.server import FastMCP

SRC_ROOT = Path(os.environ.get("SRC_ROOT", str(Path(__file__).resolve().parent.parent / "app")))

mcp = FastMCP("fast-code-explorer")


def _safe_path(relative: str) -> Path:
    resolved = (SRC_ROOT / relative).resolve()
    if not str(resolved).startswith(str(SRC_ROOT.resolve())):
        raise ValueError(f"Path traversal blocked: {relative}")
    return resolved


def _list_dir(directory: Path) -> list[str]:
    entries: list[str] = []
    try:
        for item in sorted(directory.iterdir()):
            name = item.name
            if name.startswith(".") or name == "node_modules" or name == "__pycache__":
                continue
            entries.append(f"{name}/" if item.is_dir() else name)
    except PermissionError:
        pass
    return entries


def _walk_files(directory: Path) -> list[Path]:
    results: list[Path] = []
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in ("node_modules", "__pycache__", ".git", ".venv")]
        for f in files:
            results.append(Path(root) / f)
    return results


@mcp.tool()
def list_source_files(directory: str = "") -> str:
    """List all source files under a directory (relative to source root)."""
    target = _safe_path(directory) if directory else SRC_ROOT
    if not target.is_dir():
        return f"Not a directory: {directory}"
    files = _walk_files(target)
    rel_paths = sorted(str(f.relative_to(SRC_ROOT)) for f in files)
    if not rel_paths:
        return "No files found."
    return "\n".join(rel_paths[:2000])


@mcp.tool()
def read_source_file(path: str, start_line: int = 0, end_line: int = 0) -> str:
    """Read a source file with optional line range (1-based)."""
    file_path = _safe_path(path)
    if not file_path.is_file():
        return f"File not found: {path}"
    try:
        text = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return str(exc)

    lines = text.splitlines()
    if start_line > 0 or end_line > 0:
        s = max(0, start_line - 1) if start_line > 0 else 0
        e = end_line if end_line > 0 else len(lines)
        lines = lines[s:e]

    numbered = [f"{i+1:6d}|{line}" for i, line in enumerate(lines, start=max(1, start_line))]
    return "\n".join(numbered)


@mcp.tool()
def search_source(pattern: str, file_pattern: str = "", max_results: int = 50) -> str:
    """Search source files for a regex pattern. Optionally filter by file glob."""
    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error as exc:
        return f"Invalid regex: {exc}"

    all_files = _walk_files(SRC_ROOT)
    if file_pattern:
        import fnmatch
        all_files = [f for f in all_files if fnmatch.fnmatch(f.name, file_pattern)]

    matches: list[str] = []
    for fp in all_files:
        try:
            text = fp.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if regex.search(line):
                rel = str(fp.relative_to(SRC_ROOT))
                matches.append(f"{rel}:{i}:{line.rstrip()}")
                if len(matches) >= max_results:
                    return "\n".join(matches) + f"\n... [capped at {max_results}]"
    return "\n".join(matches) if matches else "No matches found."


@mcp.tool()
def list_directory(path: str = "") -> str:
    """List contents of a directory relative to source root."""
    target = _safe_path(path) if path else SRC_ROOT
    if not target.is_dir():
        return f"Not a directory: {path}"
    entries = _list_dir(target)
    return "\n".join(entries) if entries else "(empty)"


@mcp.tool()
def get_file_info(path: str) -> str:
    """Get metadata about a file (size, line count, type)."""
    file_path = _safe_path(path)
    if not file_path.exists():
        return f"Not found: {path}"

    stat = file_path.stat()
    info_lines = [
        f"Path: {path}",
        f"Type: {'directory' if file_path.is_dir() else 'file'}",
        f"Size: {stat.st_size} bytes",
    ]
    if file_path.is_file():
        try:
            line_count = len(file_path.read_text(encoding="utf-8", errors="replace").splitlines())
            info_lines.append(f"Lines: {line_count}")
        except OSError:
            pass
        info_lines.append(f"Extension: {file_path.suffix}")
    return "\n".join(info_lines)


@mcp.tool()
def get_architecture() -> str:
    """Get a high-level architecture overview of the codebase."""
    readme_path = SRC_ROOT.parent / "README.md"
    if readme_path.is_file():
        text = readme_path.read_text(encoding="utf-8", errors="replace")
        if len(text) > 10000:
            text = text[:10000] + "\n... [truncated]"
        return text

    dirs = _list_dir(SRC_ROOT)
    return "Source root directories:\n" + "\n".join(f"  {d}" for d in dirs)


@mcp.tool()
def get_tools_overview() -> str:
    """List available tools in the codebase."""
    tools_dir = SRC_ROOT / "tools"
    if not tools_dir.is_dir():
        return "No tools directory found."
    entries = _list_dir(tools_dir)
    return "\n".join(entries)


@mcp.tool()
def get_commands_overview() -> str:
    """List available commands in the codebase."""
    for candidate in [SRC_ROOT / "commands", SRC_ROOT / "api"]:
        if candidate.is_dir():
            return "\n".join(_list_dir(candidate))
    return "No commands directory found."


@mcp.resource("fast-code://architecture")
def resource_architecture() -> str:
    """Architecture overview of the codebase."""
    return get_architecture()


@mcp.resource("fast-code://tools")
def resource_tools() -> str:
    """List of available tools."""
    return get_tools_overview()


@mcp.resource("fast-code://commands")
def resource_commands() -> str:
    """List of available commands."""
    return get_commands_overview()


@mcp.prompt()
def explore_codebase(area: str = "") -> str:
    """Guide exploration of a specific area of the codebase."""
    if area:
        return (
            f"I want to explore the '{area}' area of the codebase. "
            f"Start by listing the files in that directory, then read the key files "
            f"to understand the architecture and main patterns used."
        )
    return (
        "I want to explore the codebase. Start by getting the architecture "
        "overview, then list the main directories and identify key files to understand."
    )


@mcp.prompt()
def explain_tool(tool_name: str = "") -> str:
    """Explain how a specific tool works."""
    if tool_name:
        return (
            f"Explain how the '{tool_name}' tool works. "
            f"Read its source file, understand its input schema, implementation, "
            f"and how it integrates with the tool system."
        )
    return "List all available tools and briefly explain what each one does."


@mcp.prompt()
def how_does_it_work(feature: str = "") -> str:
    """Explain how a feature or subsystem works."""
    if feature:
        return (
            f"Explain how '{feature}' works. Search for relevant "
            f"files, read the implementation, and explain the data flow."
        )
    return "Give me a high-level overview of how the system works, covering the main subsystems."


@mcp.prompt()
def find_implementation(description: str = "") -> str:
    """Help locate where something is implemented."""
    if description:
        return (
            f"Help me find where '{description}' is implemented in the codebase. "
            f"Search for relevant patterns and read the matching files."
        )
    return "Help me find a specific implementation in the codebase. What are you looking for?"


@mcp.prompt()
def review_code(path: str = "") -> str:
    """Review code in a specific file or directory."""
    if path:
        return (
            f"Review the code in '{path}'. Read the file(s), analyze the "
            f"implementation quality, patterns used, and suggest improvements."
        )
    return "I'd like you to review some code. Which file or directory should I look at?"
