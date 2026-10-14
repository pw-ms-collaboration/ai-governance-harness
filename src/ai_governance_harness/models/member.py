"""Data contracts and Pydantic models for Australian Superannuation member records.

Aligns with PRD-2026-SUPER-001 (FR-001, DD-002, CON-003) and Security Plan SEC-2026-SUPER-001.
Strictly internal fund data; does not represent external whole-of-wealth or third-party assets.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import List
from pydantic import BaseModel, Field


class ContributionRecord(BaseModel):
    """Historical contribution record for a specific date/period."""
    date: date
    employer_contribution: float = Field(default=0.0, ge=0.0, description="Mandatory SG employer contributions")
    voluntary_contribution: float = Field(default=0.0, ge=0.0, description="Salary sacrifice or personal concessional/non-concessional contributions")

    @property
    def total_contribution(self) -> float:
        return self.employer_contribution + self.voluntary_contribution


class DigitalActivityRecord(BaseModel):
    """Aggregated monthly digital footprint for member engagement tracking."""
    month: str = Field(description="Format YYYY-MM")
    portal_logins: int = Field(default=0, ge=0)
    app_sessions: int = Field(default=0, ge=0)
    document_downloads: int = Field(default=0, ge=0)

    @property
    def total_interactions(self) -> int:
        return self.portal_logins + self.app_sessions + self.document_downloads


class InteractionRecord(BaseModel):
    """Staff contact centre or digital interaction event."""
    timestamp: datetime
    channel: str = Field(description="phone, email, secure_portal_message, face_to_face")
    topic: str = Field(description="Interaction subject: e.g. balance_inquiry, investment_switch, fees, closure_inquiry")
    closure_inquiry: bool = Field(default=False, description="Whether the member inquired about account closure or rollover out")
    notes_summary: str = Field(description="Factual summary of interaction; no sensitive health or personal data")


class MemberProfile(BaseModel):
    """Comprehensive internal superannuation profile for a single member.

    Complies with FR-001 and DD-002: Internal fund data only; no external wealth representation.
    """
    member_id: str
    first_name: str
    last_name: str
    age: int = Field(ge=16, le=120)
    tenure_years: float = Field(ge=0.0)
    current_balance: float = Field(ge=0.0)
    investment_options: List[str] = Field(default_factory=list, description="e.g. ['Growth', 'Balanced', 'Australian Shares']")
    insurance_opt_in: bool = Field(default=True, description="Whether Death/TPD/Income Protection cover is active")
    contributions: List[ContributionRecord] = Field(default_factory=list)
    digital_activity: List[DigitalActivityRecord] = Field(default_factory=list)
    interactions: List[InteractionRecord] = Field(default_factory=list)

    @property
    def recent_closure_inquiry(self) -> bool:
        """Check if any recorded interaction flags a closure inquiry."""
        return any(ix.closure_inquiry for ix in self.interactions)
