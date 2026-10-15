"""Advice Boundary and Disclosure Guardrails (ASIC RG 244 & Corporations Act 2001).

Restricts agent outputs to Factual Information and General Advice, strictly prohibiting
personalized financial product recommendations, and deterministically attaching
mandatory statutory disclaimers and in-fund data scope notices.
"""

import re
from collections.abc import Iterator
from typing import List, Optional, Tuple

from ai_governance_harness.governance.models import LifecyclePoint
from ai_governance_harness.governance.telemetry import guardrail_span

GENERAL_ADVICE_WARNING = (
    "--- GENERAL ADVICE WARNING (ASIC RG 244) ---\n"
    "This information is general in nature and has been prepared without taking into account "
    "your individual objectives, financial situation, or needs. Before acting on any information, "
    "you should consider its appropriateness having regard to your objectives, financial situation, "
    "and needs, and consider obtaining personal financial advice. Please read the relevant "
    "Product Disclosure Statement (PDS) and Target Market Determination (TMD) before making any financial decision."
)

IN_FUND_PROVENANCE_NOTICE = (
    "--- IN-FUND DATA SCOPE & PROVENANCE NOTICE ---\n"
    "All member observations, balance summaries, and interaction histories are derived solely "
    "from internal superannuation fund records. External financial assets, third-party superannuation "
    "balances, and external liabilities are not tracked or verified. Any insights reflect internal fund data only."
)

# Prohibited directive personal advice patterns (ASIC RG 244 Section C)
PROHIBITED_ADVICE_PATTERNS = [
    re.compile(r"\b(you\s+(should|ought\s+to|must|need\s+to)\s+(switch|rollover|roll\s+over|transfer|consolidate|move|invest|choose))\b", re.IGNORECASE),
    re.compile(r"\b(we\s+recommend\s+(that\s+you\s+)?(switching|rolling\s+over|transferring|consolidating|investing|choosing))\b", re.IGNORECASE),
    re.compile(r"\b(i\s+recommend\s+(that\s+you\s+)?(switch|rollover|roll\s+over|transfer|consolidate|invest|choose))\b", re.IGNORECASE),
    re.compile(r"\b(the\s+best\s+option\s+for\s+you\s+is)\b", re.IGNORECASE),
    re.compile(r"\b(you\s+should\s+allocate\s+your\s+super)\b", re.IGNORECASE),
    re.compile(r"\b(you\s+should\s+close\s+your\s+account)\b", re.IGNORECASE),
    re.compile(r"\b(you\s+would\s+be\s+better\s+off\s+(switching|moving|transferring))\b", re.IGNORECASE),
    re.compile(r"\b(this\s+is\s+the\s+right\s+investment\s+for\s+your\s+situation)\b", re.IGNORECASE),
]

# Patterns asserting complete whole-of-wealth across external institutions
WHOLE_OF_WEALTH_EXAGGERATION_PATTERNS = [
    re.compile(r"\b(complete\s+wealth\s+picture|total\s+net\s+worth|all\s+your\s+external\s+assets|complete\s+financial\s+situation)\b", re.IGNORECASE),
]


class PersonalAdviceViolationError(ValueError):
    """Raised when generated output contains directive personal financial advice."""
    pass


class AdviceClassificationGuardrail:
    """Detects and mitigates personal financial advice violations in agent outputs."""

    def __init__(self, prohibited_patterns: Optional[List[re.Pattern]] = None):
        self.prohibited_patterns = prohibited_patterns or PROHIBITED_ADVICE_PATTERNS

    def scan_for_personal_advice(self, text: str) -> List[str]:
        """Scan text and return any detected prohibited personal advice phrases."""
        violations = []
        for pattern in self.prohibited_patterns:
            matches = pattern.findall(text)
            if matches:
                # Format matched text
                for m in pattern.finditer(text):
                    violations.append(m.group(0))
        return violations

    def enforce_advice_boundaries(
        self,
        output_text: str,
        allow_fallback: bool = True,
        fallback_summary: Optional[str] = None,
    ) -> Tuple[str, bool]:
        """Verify that output_text is free from personal advice.

        If violations are found:
        - If allow_fallback is True, replaces text with sanitized factual summary.
        - Otherwise, raises PersonalAdviceViolationError.

        Returns (sanitized_text, violation_detected).
        """
        violations = self.scan_for_personal_advice(output_text)
        if not violations:
            return output_text, False

        if not allow_fallback:
            raise PersonalAdviceViolationError(
                f"ASIC RG 244 Violation: Detected personal financial product advice: {violations}"
            )

        # Apply deterministic factual fallback
        safe_body = fallback_summary or (
            "[SYSTEM NOTICE: The generated response contained personalized advice phrasing "
            "prohibited by ASIC RG 244 and has been converted to factual information only.]\n\n"
            "Summary of Record: The member's account and transaction history remain available for factual review. "
            "No recommendation is made regarding switching, rolling over, or altering investment options. "
            "Frontline consultants should provide factual product information or refer the member to a licensed financial adviser."
        )

        return safe_body, True


class WholeOfWealthInvariantGuardrail:
    """Enforces that the agent does not falsely claim whole-of-wealth visibility across external institutions."""

    def sanitize_scope_claims(self, text: str) -> str:
        """Replace false claims of total net worth with internal in-fund qualifiers."""
        sanitized = text
        for pattern in WHOLE_OF_WEALTH_EXAGGERATION_PATTERNS:
            sanitized = pattern.sub("internal in-fund superannuation holdings", sanitized)
        return sanitized


class DisclosureAttacher:
    """Ensures statutory General Advice Warning and In-Fund Data Scope notices are present."""

    @staticmethod
    def attach_disclosures(text: str) -> str:
        """Attach General Advice and In-Fund provenance disclaimers to text."""
        result = text.rstrip()

        if "GENERAL ADVICE WARNING" not in result:
            result = f"{result}\n\n{GENERAL_ADVICE_WARNING}"

        if "IN-FUND DATA SCOPE" not in result:
            result = f"{result}\n\n{IN_FUND_PROVENANCE_NOTICE}"

        return result


def _response_text(payload: object) -> Iterator[str]:
    if isinstance(payload, str):
        yield payload
    elif isinstance(payload, dict):
        for key, value in payload.items():
            yield from _response_text(key)
            yield from _response_text(value)
    elif isinstance(payload, (list, tuple)):
        for value in payload:
            yield from _response_text(value)
    elif payload is not None and not isinstance(payload, (bool, int, float)):
        raise TypeError("Tool advice scanning requires a JSON-compatible response.")


def tool_response_policy_data(payload: object) -> dict[str, str]:
    """Scan response text in memory and expose only bounded policy metadata.

    A passed scan means no prohibited pattern was detected, not that the
    response has been legally classified as factual information or general advice.
    """
    guardrail = AdviceClassificationGuardrail()
    with guardrail_span("personal_advice_scan", LifecyclePoint.POST_TOOL) as check:
        detected = any(
            guardrail.scan_for_personal_advice(text)
            for text in _response_text(payload)
        )
        if detected:
            check.triggered("personal_advice_detected")
    return {
        "result_type": type(payload).__name__,
        "advice_scan_status": "personal_advice_detected" if detected else "passed",
    }
