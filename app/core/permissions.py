from __future__ import annotations

import fnmatch
from typing import Any

from app.models.config import PermissionRule


_rules: list[PermissionRule] = []


def set_rules(rules: list[PermissionRule]) -> None:
    global _rules
    _rules = list(rules)


def check_permission(tool_name: str, tool_input: dict[str, Any] | None = None) -> bool:
    """Return True if the tool call is allowed by the current permission rules.

    Rules are evaluated in order; the first match wins. If no rule matches, allow.
    """
    for rule in _rules:
        if not fnmatch.fnmatch(tool_name, rule.tool):
            continue

        if rule.path_pattern and tool_input:
            path_value = tool_input.get("file_path") or tool_input.get("path") or ""
            if not fnmatch.fnmatch(str(path_value), rule.path_pattern):
                continue

        return rule.action == "allow"

    return True
