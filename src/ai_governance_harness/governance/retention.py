"""Typed, metadata-only retention eligibility and staff referral contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

EligibilityStatus = Literal[
    "routine_permitted", "duplicate_open", "specialist_required",
    "account_exited", "review_required", "unknown",
]
SpecialistTeam = Literal[
    "complaints", "hardship", "bereavement", "member_support",
]


class RetentionCase(BaseModel):
    """One synthetic internal case, with explicit closed-case clearance."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str = Field(pattern=r"^CASE-\d{3}$")
    kind: Literal["routine_retention", "specialist"]
    status: Literal["open", "closed"]
    closure_outcome: Literal["routine_cleared", "review_required", "unknown"] = "unknown"
    specialist_team: SpecialistTeam | None = None


class RetentionRecord(BaseModel):
    """Trusted eligibility facts; omitted facts are unknown, never permissive."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    member_id: str = Field(pattern=r"^MEM-\d{3}$")
    account_status: Literal["active", "closed", "exit_completed", "unknown"] = "unknown"
    new_signals_status: Literal["satisfied", "not_satisfied", "unknown"] = "unknown"
    contact_policy_status: Literal["satisfied", "restricted", "unknown"] = "unknown"
    cooling_off_status: Literal["satisfied", "restricted", "unknown"] = "unknown"
    cases: tuple[RetentionCase, ...]

    def review(self) -> RetentionReview:
        """Derive a bounded outcome without disclosing member case narratives."""
        if self.account_status in {"closed", "exit_completed"}:
            return RetentionReview(status="account_exited")
        for case in self.cases:
            if case.kind == "specialist" and (
                case.status == "open" or case.closure_outcome != "routine_cleared"
            ):
                return RetentionReview(
                    status="specialist_required",
                    existing_case_id=case.case_id,
                    specialist_team=case.specialist_team or "member_support",
                )
        for case in self.cases:
            if case.kind == "routine_retention" and case.status == "open":
                return RetentionReview(
                    status="duplicate_open", existing_case_id=case.case_id,
                )
        if self.account_status == "unknown" or "unknown" in {
            self.new_signals_status, self.contact_policy_status, self.cooling_off_status,
        }:
            return RetentionReview(status="unknown")
        if (
            self.new_signals_status != "satisfied"
            or self.contact_policy_status != "satisfied"
            or self.cooling_off_status != "satisfied"
            or any(case.closure_outcome != "routine_cleared" for case in self.cases)
        ):
            return RetentionReview(status="review_required")
        return RetentionReview(status="routine_permitted")


class RetentionReview(BaseModel):
    """Safe staff-facing outcome, not an executed referral or a new case."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: EligibilityStatus
    existing_case_id: str | None = Field(default=None, pattern=r"^CASE-\d{3}$")
    specialist_team: SpecialistTeam | None = None

    def policy_data(self) -> dict[str, str]:
        """Expose only the decision status to policy evaluation."""
        return {"retention_handling_status": self.status}

    def staff_message(self) -> str:
        """Describe the next staff action using fixed, non-sensitive wording."""
        if self.status == "specialist_required":
            return (
                "Routine retention outreach is blocked. "
                f"Refer to the {self.specialist_team or 'member_support'} team"
                f" and review existing case {self.existing_case_id or 'in the internal system'}. "
                "Staff must complete the referral through the internal process. "
                "No specialist case was created and no contact occurred."
            )
        if self.status == "duplicate_open":
            return (
                "A routine retention case is already open. "
                f"Continue existing case {self.existing_case_id or 'in the internal system'}; "
                "no duplicate case was prepared."
            )
        if self.status == "account_exited":
            return (
                "Routine retention outreach is blocked because the account is closed "
                "or the exit is completed. Follow a separately approved post-exit process."
            )
        if self.status in {"review_required", "unknown"}:
            return (
                "Routine retention outreach eligibility is not confirmed. "
                "Staff must verify closure clearance, new signals, contact restrictions "
                "and cooling-off eligibility before preparing a case."
            )
        return "Routine retention preparation is eligible, subject to human approval."
