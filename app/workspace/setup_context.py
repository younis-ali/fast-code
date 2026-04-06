from __future__ import annotations

import platform
import sys


def build_setup_context() -> str:
    """Short environment description for workspace runtime reports."""
    lines = [
        f"- Python: {sys.version.split()[0]} ({platform.python_implementation()})",
        f"- Platform: {platform.system()} {platform.release()} ({platform.machine()})",
        "- Test command: `pytest`",
    ]
    return "\n".join(lines)
