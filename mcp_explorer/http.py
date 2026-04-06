from __future__ import annotations

import os
import sys

from mcp_explorer.server import SRC_ROOT, mcp


def main() -> None:
    if not SRC_ROOT.is_dir():
        print(f"ERROR: Source root not found: {SRC_ROOT}", file=sys.stderr)
        print("Set SRC_ROOT to the directory you want to explore.", file=sys.stderr)
        sys.exit(1)

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "3001"))

    print(f"MCP Explorer (HTTP) – source root: {SRC_ROOT}", file=sys.stderr)
    print(f"Listening on {host}:{port}", file=sys.stderr)
    mcp.run(transport="sse", host=host, port=port)


if __name__ == "__main__":
    main()
