"""Synthetic superannuation data models and schemas."""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class MemberRecord(BaseModel):
    """Unified internal superannuation member record."""

    member_id: str = Field(..., description="Unique member identifier, e.g. MEM-001")
    full_name: str = Field(..., description="Synthetic member name")
    age: int = Field(..., ge=18, le=100, description="Member age in years")
    tenure_years: float = Field(..., ge=0.0, description="Tenure with the fund in years")
    risk_profile: str = Field(..., description="Risk profile: Conservative, Balanced, Growth, High Growth")
    communication_pref: str = Field(default="email", description="Preferred communication channel")
    has_closure_inquiry: bool = Field(default=False, description="Flag indicating active or past closure inquiry")


class AccountRecord(BaseModel):
    """Superannuation account holding within the fund."""

    account_id: str = Field(..., description="Unique account identifier, e.g. ACC-001")
    member_id: str = Field(..., description="Associated member identifier")
    balance: float = Field(..., ge=0.0, description="Current account balance in AUD")
    phase: str = Field(default="Accumulation", description="Account phase: Accumulation, Transition to Retirement, Pension")
    option_allocation: Dict[str, float] = Field(
        default_factory=dict,
        description="Investment option allocation percentages summing to 1.0",
    )


class ContributionRecord(BaseModel):
    """Historical contribution record for a superannuation account."""

    contribution_id: str = Field(..., description="Unique contribution transaction ID")
    account_id: str = Field(..., description="Target account identifier")
    member_id: str = Field(..., description="Associated member identifier")
    date: str = Field(..., description="Contribution transaction date (YYYY-MM-DD)")
    amount: float = Field(..., ge=0.0, description="Contribution amount in AUD")
    type: str = Field(..., description="Contribution category: Concessional, SG, Non-Concessional, Salary Sacrifice")
    usual_monthly_baseline: float = Field(..., ge=0.0, description="Expected monthly baseline contribution in AUD")


class InteractionRecord(BaseModel):
    """Frontline and digital interaction logged for a member."""

    interaction_id: str = Field(..., description="Unique interaction identifier")
    member_id: str = Field(..., description="Associated member identifier")
    timestamp: str = Field(..., description="ISO 8601 interaction timestamp")
    channel: str = Field(..., description="Contact channel: phone, email, secure_mail, portal_chat")
    category: str = Field(..., description="Interaction category, e.g. closure_inquiry, general_inquiry, fee_query")
    notes: str = Field(..., description="Summary notes logged by consultant or system")
    closure_inquiry_flag: bool = Field(default=False, description="Explicit flag marking a fund closure or transfer inquiry")


class DigitalActivityRecord(BaseModel):
    """Aggregated monthly portal and mobile app activity metrics."""

    activity_id: str = Field(..., description="Unique activity summary identifier")
    member_id: str = Field(..., description="Associated member identifier")
    month: str = Field(..., description="Activity month in YYYY-MM format")
    login_count: int = Field(..., ge=0, description="Number of portal/mobile logins during month")
    document_downloads: int = Field(default=0, ge=0, description="Count of statements or PDS documents downloaded")
    baseline_logins: int = Field(..., ge=0, description="Historical 6-month average baseline monthly logins")
