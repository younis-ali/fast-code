from __future__ import annotations

from app.core.coder_subtools import CODER_SUBTOOL_NAMES


def test_coder_subtool_allowlist_excludes_nested_agents() -> None:
    assert "Agent" not in CODER_SUBTOOL_NAMES
    assert "Coder" not in CODER_SUBTOOL_NAMES
    assert "Read" in CODER_SUBTOOL_NAMES
    assert "Bash" in CODER_SUBTOOL_NAMES


def test_coder_tool_schema_has_required_fields() -> None:
    from app.tools.coder import CoderTool

    t = CoderTool()
    assert t.name == "Coder"
    assert "prompt" in t.input_schema.get("properties", {})
    assert "description" in t.input_schema.get("properties", {})
    req = t.input_schema.get("required", [])
    assert "prompt" in req and "description" in req


def test_coder_tool_schemas_match_registry() -> None:
    from app.services.store import set_db_path, init_db
    from app.core.tool_registry import registry
    from app.tools.coder import _coder_tool_schemas

    import asyncio

    async def _setup() -> None:
        set_db_path(":memory:")
        await init_db()
        registry.discover()

    asyncio.run(_setup())

    schemas = _coder_tool_schemas()
    names = {s["name"] for s in schemas}
    assert names == CODER_SUBTOOL_NAMES
    assert len(schemas) == len(CODER_SUBTOOL_NAMES)
