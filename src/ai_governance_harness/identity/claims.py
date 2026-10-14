"""Pure normalization of previously validated agent claims."""

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
from typing import TYPE_CHECKING, Literal, cast

from ai_governance_harness.governance import Actor, StaffRole, TokenType
from ai_governance_harness.identity.constants import STAFF_ROLES

if TYPE_CHECKING:
    from ai_governance_harness.mcp_server.config import ServerSettings


@dataclass(frozen=True)
class Rejection:
    """Closed, privacy-safe authentication rejection."""

    reason: Literal[
        "invalid_token",
        "unknown_agent",
        "invalid_token_shape",
        "missing_scope",
        "invalid_tenant",
        "invalid_audience",
        "invalid_platform_principal",
    ]


@dataclass(frozen=True)
class NormalizedIdentity:
    """Only bounded identity labels and a one-way principal reference."""

    actor: Actor
    token_type: TokenType
    staff_role: StaffRole
    principal_hash: str


def _strings(value: object) -> list[str] | None:
    if isinstance(value, str):
        return value.split()
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
    return None


def normalize_claims(
    claims: Mapping[str, object], *, settings: "ServerSettings"
) -> NormalizedIdentity | Rejection:
    """Derive governance enums without returning raw claims."""
    azp = claims.get("azp")
    if not isinstance(azp, str) or azp not in {
        settings.interactive_agent_id,
        settings.reporting_agent_id,
    }:
        return Rejection("unknown_agent")
    actor: Actor = (
        "interactive" if azp == settings.interactive_agent_id else "reporting"
    )
    oid = claims.get("oid")
    if not isinstance(oid, str) or not oid.strip() or len(oid) > 128:
        return Rejection("invalid_token_shape")
    act = _strings(claims.get("xms_act_fct", []))
    sub = _strings(claims.get("xms_sub_fct", []))
    roles = claims.get("roles", [])
    if (
        act is None
        or sub is None
        or "13" in sub
        or not isinstance(roles, list)
        or not all(isinstance(role, str) for role in roles)
    ):
        return Rejection("invalid_token_shape")
    principal_hash = hashlib.sha256(oid.encode("utf-8")).hexdigest()
    if claims.get("idtyp") == "user":
        if actor != "interactive" or "11" not in act:
            return Rejection("invalid_token_shape")
        scope = claims.get("scp")
        if (
            settings.auth_required_scope is not None
            and (
                not isinstance(scope, str)
                or settings.auth_required_scope not in scope.split()
            )
        ):
            return Rejection("missing_scope")
        staff = [role for role in roles if role.startswith("Staff.")]
        role: StaffRole = "none"
        if len(staff) == 1 and staff[0] in STAFF_ROLES:
            role = cast(StaffRole, STAFF_ROLES[staff[0]])
        return NormalizedIdentity(actor, "user", role, principal_hash)
    if claims.get("idtyp") == "app":
        if (
            actor != "reporting"
            or "11" not in sub
            or "Reports.Aggregate.Read" not in roles
        ):
            return Rejection("invalid_token_shape")
        return NormalizedIdentity(actor, "app", "none", principal_hash)
    return Rejection("invalid_token_shape")
