from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient


async def _make_client():
    """Create a test client with DB and tools initialized."""
    from app.services.store import set_db_path, init_db
    set_db_path(":memory:")
    await init_db()

    from app.core.tool_registry import registry
    # Full suite: another test module may have imported only coder.py and registered Coder alone.
    if len(registry) == 0 or registry.get("Bash") is None:
        registry.discover()

    from app.agent.graph import compile_agent_graph
    from app.agent.runtime import set_compiled_graph

    set_compiled_graph(compile_agent_graph(registry))

    from app.main import create_app
    app = create_app()
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.anyio
async def test_health():
    async with await _make_client() as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "default_models" in data
        assert "api_keys_configured" in data


@pytest.mark.anyio
async def test_tools_list():
    async with await _make_client() as client:
        resp = await client.get("/api/tools")
        assert resp.status_code == 200
        data = resp.json()
        assert "tools" in data
        tool_names = [t["name"] for t in data["tools"]]
        assert "Bash" in tool_names
        assert "Read" in tool_names
        assert "Write" in tool_names
        assert "Edit" in tool_names
        assert "Glob" in tool_names
        assert "Grep" in tool_names
        assert "Coder" in tool_names


@pytest.mark.anyio
async def test_conversations_crud():
    async with await _make_client() as client:
        # Create
        resp = await client.post("/api/conversations?title=Test+Conv")
        assert resp.status_code == 200
        conv = resp.json()
        assert conv["title"] == "Test Conv"
        conv_id = conv["id"]

        # List
        resp = await client.get("/api/conversations")
        assert resp.status_code == 200
        convs = resp.json()
        assert any(c["id"] == conv_id for c in convs)

        # Get
        resp = await client.get(f"/api/conversations/{conv_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == conv_id

        # Delete
        resp = await client.delete(f"/api/conversations/{conv_id}")
        assert resp.status_code == 200

        # Verify deleted
        resp = await client.get(f"/api/conversations/{conv_id}")
        assert resp.status_code == 404


@pytest.mark.anyio
async def test_sessions_crud():
    async with await _make_client() as client:
        resp = await client.post("/api/sessions", json={})
        assert resp.status_code == 200
        session = resp.json()
        session_id = session["id"]

        resp = await client.get("/api/sessions")
        assert resp.status_code == 200

        resp = await client.delete(f"/api/sessions/{session_id}")
        assert resp.status_code == 200


@pytest.mark.anyio
async def test_chat_requires_api_key(monkeypatch):
    from app.config import settings
    orig_anthropic = settings.anthropic_api_key
    orig_openai = settings.openai_api_key
    monkeypatch.setattr(settings, "anthropic_api_key", "")
    monkeypatch.setattr(settings, "openai_api_key", "")
    try:
        async with await _make_client() as client:
            resp = await client.post("/api/chat", json={
                "messages": [{"role": "user", "content": "hello"}],
            })
            assert resp.status_code == 200
            text = resp.text
            assert (
                "ANTHROPIC_API_KEY" in text
                or "OPENAI_API_KEY" in text
                or "error" in text.lower()
            )
    finally:
        settings.anthropic_api_key = orig_anthropic
        settings.openai_api_key = orig_openai
