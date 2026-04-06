from __future__ import annotations

import sys

from mcp_explorer.server import SRC_ROOT, mcp


def main() -> None:
    if not SRC_ROOT.is_dir():
        print(f"ERROR: Source root not found: {SRC_ROOT}", file=sys.stderr)
        print("Set SRC_ROOT to the directory you want to explore.", file=sys.stderr)
        sys.exit(1)

    print(f"MCP Explorer (stdio) – source root: {SRC_ROOT}", file=sys.stderr)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
