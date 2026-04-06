from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def client():
    # Use in-memory DB for tests
    from app.services.store import set_db_path, init_db
    set_db_path(":memory:")
    await init_db()

    # Ensure tools are registered
    from app.core.tool_registry import registry
    if len(registry) == 0:
        registry.discover()

    from app.agent.graph import compile_agent_graph
    from app.agent.runtime import set_compiled_graph

    set_compiled_graph(compile_agent_graph(registry))

    from app.main import create_app
    app = create_app()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # Reset DB for next test
    set_db_path(":memory:")
