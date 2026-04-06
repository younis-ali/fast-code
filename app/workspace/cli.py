from __future__ import annotations

import argparse
import sys

from app.core.tool_registry import registry
from app.workspace.audit import run_structure_audit
from app.workspace.command_graph import build_command_graph
from app.workspace.execution_registry import build_execution_registry
from app.workspace.query_summary import WorkspaceQuerySummary
from app.workspace.runtime import WorkspaceRuntime
from app.workspace.tool_pool import assemble_tool_pool


def _ensure_tools() -> None:
    registry.discover()


def cmd_summary() -> int:
    _ensure_tools()
    text = WorkspaceQuerySummary.from_app(registry).render_summary()
    print(text)
    return 0


def cmd_audit() -> int:
    result = run_structure_audit()
    print(result.to_markdown())
    return 0 if not result.missing else 1


def cmd_route(args: argparse.Namespace) -> int:
    _ensure_tools()
    rt = WorkspaceRuntime(registry)
    matches = rt.route_prompt(args.prompt, limit=args.limit)
    for m in matches:
        print(f"[{m.kind}] {m.name} score={m.score} — {m.source_hint}")
    return 0


def cmd_bootstrap(args: argparse.Namespace) -> int:
    _ensure_tools()
    rt = WorkspaceRuntime(registry)
    session = rt.bootstrap_session(args.prompt, limit=args.limit)
    print(session.as_markdown())
    return 0


def cmd_tool_pool(args: argparse.Namespace) -> int:
    _ensure_tools()
    pool = assemble_tool_pool(registry, simple_mode=args.simple, include_delegated=not args.simple)
    print(pool.as_markdown())
    return 0


def cmd_command_graph() -> int:
    _ensure_tools()
    print(build_command_graph(registry).as_markdown())
    return 0


def cmd_registry() -> int:
    _ensure_tools()
    ex = build_execution_registry(registry)
    print("# Execution registry\n")
    print("## Tools\n")
    for t in ex.tools:
        print(f"- {t.name}: {t.description[:120]}")
    print("\n## HTTP surface\n")
    for c in ex.api_commands[:30]:
        print(f"- {c.method} {c.path}")
    return 0


def cmd_turn_loop(args: argparse.Namespace) -> int:
    _ensure_tools()
    rt = WorkspaceRuntime(registry)
    results = rt.run_turn_loop(
        args.prompt,
        limit=args.limit,
        max_turns=args.max_turns,
        structured_output=args.structured,
    )
    for i, tr in enumerate(results, start=1):
        print(f"## Turn {i}")
        print(f"stop_reason={tr.stop_reason}")
        print(tr.output)
        print()
    return 0


def cmd_bootstrap_graph() -> int:
    _ensure_tools()
    from app.workspace.deferred_init import describe_deferred_init

    graph = build_command_graph(registry)
    d = describe_deferred_init()
    print("# Bootstrap graph\n")
    print(graph.as_markdown())
    print("\n## Deferred startup\n")
    print("\n".join(d.as_lines()))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.workspace.cli", description="Fast Code workspace tools")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("summary", help="Print workspace markdown summary")
    sub.add_parser("audit", help="Verify expected project files exist")
    p_route = sub.add_parser("route", help="Route a prompt to tools / HTTP surface")
    p_route.add_argument("prompt", nargs="+")
    p_route.add_argument("--limit", type=int, default=5)

    p_boot = sub.add_parser("bootstrap", help="Run a full diagnostic bootstrap session")
    p_boot.add_argument("prompt", nargs="+")
    p_boot.add_argument("--limit", type=int, default=5)

    p_pool = sub.add_parser("tool-pool", help="List pooled tools")
    p_pool.add_argument("--simple", action="store_true", help="Exclude delegated tools")

    sub.add_parser("command-graph", help="Print tool graph (core / network / delegated)")
    sub.add_parser("registry", help="List execution registry entries")
    sub.add_parser("bootstrap-graph", help="Tool graph plus startup flags")

    p_loop = sub.add_parser("turn-loop", help="Run diagnostics multi-turn loop")
    p_loop.add_argument("prompt", nargs="+")
    p_loop.add_argument("--limit", type=int, default=5)
    p_loop.add_argument("--max-turns", type=int, default=2)
    p_loop.add_argument("--structured", action="store_true")

    args = parser.parse_args(argv)
    prompt = " ".join(args.prompt) if hasattr(args, "prompt") and args.prompt else ""

    if args.command == "summary":
        return cmd_summary()
    if args.command == "audit":
        return cmd_audit()
    if args.command == "route":
        args.prompt = prompt
        return cmd_route(args)
    if args.command == "bootstrap":
        args.prompt = prompt
        return cmd_bootstrap(args)
    if args.command == "tool-pool":
        return cmd_tool_pool(args)
    if args.command == "command-graph":
        return cmd_command_graph()
    if args.command == "registry":
        return cmd_registry()
    if args.command == "bootstrap-graph":
        return cmd_bootstrap_graph()
    if args.command == "turn-loop":
        args.prompt = prompt
        return cmd_turn_loop(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
