"""Bounded bearer parsing shared across the mock and application boundaries."""

import re
from collections.abc import Sequence

MAX_TOKEN_LENGTH = 16_384
_BEARER = re.compile(
    r"Bearer ([A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)", re.IGNORECASE
)


class InvalidIdentityToken(ValueError):
    """A token was rejected without exposing the supplied credential."""


def bearer_token(headers: Sequence[str]) -> str:
    """Require a single, bounded bearer JWT header."""
    if len(headers) != 1 or len(headers[0]) > MAX_TOKEN_LENGTH + 7:
        raise InvalidIdentityToken("invalid_token")
    match = _BEARER.fullmatch(headers[0])
    if match is None:
        raise InvalidIdentityToken("invalid_token")
    return match[1]
