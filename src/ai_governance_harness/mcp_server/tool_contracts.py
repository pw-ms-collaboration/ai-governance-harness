"""Structured MCP tool metadata shared by server and browser chat."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

TOOL_META_NAMESPACE = "ai_governance_harness"


def build_tool_metadata(
    *,
    intent: str,
    browser_chat_enabled: bool,
    requires_approval: bool = False,
) -> dict[str, Any]:
    """Build the repository-owned metadata contract for an MCP tool."""
    return {
        TOOL_META_NAMESPACE: {
            "intent": intent,
            "browser_chat": {"enabled": browser_chat_enabled},
            "requires_approval": requires_approval,
        }
    }


def browser_chat_enabled(meta: object) -> bool:
    """Return whether valid tool metadata explicitly enables browser chat."""
    if not isinstance(meta, Mapping):
        return False
    harness_meta = meta.get(TOOL_META_NAMESPACE)
    if not isinstance(harness_meta, Mapping):
        return False
    intent = harness_meta.get("intent")
    browser_chat = harness_meta.get("browser_chat")
    return (
        isinstance(intent, str)
        and bool(intent.strip())
        and isinstance(browser_chat, Mapping)
        and browser_chat.get("enabled") is True
    )
