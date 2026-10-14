"""Structured, privacy-safe errors shared by chat and the identity client."""

from typing import Literal

ChatErrorCode = Literal[
    "chat_service_error",
    "governance_denied",
    "invalid_model_response",
    "invalid_request",
    "model_round_limit",
    "unsafe_tool_result",
    "upstream_failure",
    "authentication_required",
    "identity_unavailable",
]


class ChatServiceError(RuntimeError):
    """Raised when a chat turn cannot be completed safely."""

    def __init__(
        self,
        message: str,
        *,
        code: ChatErrorCode = "chat_service_error",
        status_code: int = 502,
        details: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.details = dict(details or {})
