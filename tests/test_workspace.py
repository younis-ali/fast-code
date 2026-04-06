from __future__ import annotations

import pytest

from app.core.tool_registry import registry
from app.workspace import (
    WorkspaceQuerySummary,
    build_workspace_manifest,
    run_structure_audit,
)
from app.workspace.runtime import WorkspaceRuntime


@pytest.fixture
def discovered_registry():
    registry.discover()
    return registry


def test_manifest_counts_python_files(discovered_registry):
    m = build_workspace_manifest()
    assert m.total_python_files >= 20
    assert m.top_level_modules


def test_query_summary_mentions_workspace(discovered_registry):
    summary = WorkspaceQuerySummary.from_app(registry).render_summary()
    assert "Fast Code workspace summary" in summary
    assert "Tool surface:" in summary
    assert "HTTP surface:" in summary


def test_structure_audit_complete(discovered_registry):
    audit = run_structure_audit()
    assert audit.coverage[0] == audit.coverage[1]
    assert not audit.missing


def test_route_finds_chat_and_tool(discovered_registry):
    rt = WorkspaceRuntime(registry)
    matches = rt.route_prompt("use bash and POST chat api", limit=8)
    kinds = {m.kind for m in matches}
    assert "tool" in kinds or "http" in kinds


def test_bootstrap_session_has_markdown(discovered_registry):
    rt = WorkspaceRuntime(registry)
    session = rt.bootstrap_session("read files and call api chat", limit=5)
    md = session.as_markdown()
    assert "Runtime session" in md
    assert "Persisted session" in md
