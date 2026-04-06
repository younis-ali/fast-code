from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph

_compiled_graph: CompiledStateGraph | None = None


def set_compiled_graph(graph: CompiledStateGraph) -> None:
    global _compiled_graph
    _compiled_graph = graph


def get_compiled_graph() -> CompiledStateGraph:
    if _compiled_graph is None:
        raise RuntimeError("Agent graph not initialized; check application lifespan")
    return _compiled_graph
