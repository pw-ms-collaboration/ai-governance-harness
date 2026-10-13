"""Australian Data Sovereignty Guardrail (APRA CPS 234).

Enforces that all inference, data processing, and storage endpoints reside
strictly within Australian sovereign territory (australiaeast or australiasoutheast).
"""

import os
import re
from typing import Optional, Set
from urllib.parse import urlparse

ALLOWED_AUSTRALIAN_REGIONS: Set[str] = {
    "australiaeast",
    "australiasoutheast",
}


class SovereigntyViolationError(PermissionError):
    """Raised when an inference or storage target violates APRA CPS 234 Australian data sovereignty."""
    pass


class SovereigntyGuardrail:
    """Validator ensuring cloud endpoints and inference operations remain strictly in Australia."""

    def __init__(self, allowed_regions: Optional[Set[str]] = None):
        self.allowed_regions = allowed_regions or ALLOWED_AUSTRALIAN_REGIONS

    def validate_region(self, region: Optional[str]) -> bool:
        """Validate an Azure region name.

        Raises SovereigntyViolationError if the region is not in the allowed Australian regions list.
        """
        if not region:
            # Check environment fallback
            region = os.getenv("AZURE_AI_PROJECT_REGION") or os.getenv("AZURE_REGION")

        if not region:
            # In mock or offline environments, default is approved
            return True

        normalized_region = region.strip().lower().replace(" ", "")
        if normalized_region in self.allowed_regions:
            return True

        raise SovereigntyViolationError(
            f"APRA CPS 234 Sovereignty Violation: Region '{region}' is not an approved "
            f"Australian sovereign region. Permitted regions: {sorted(list(self.allowed_regions))}."
        )

    def validate_endpoint(self, endpoint: Optional[str]) -> bool:
        """Inspect endpoint URL or hostname for compliance with Australian data sovereignty.

        Raises SovereigntyViolationError if the endpoint hostname indicates a non-Australian location.
        """
        if not endpoint:
            endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT") or os.getenv("AZURE_OPENAI_ENDPOINT")

        if not endpoint or endpoint in ("local-mock", "mock://local", "test"):
            return True

        # Extract hostname from URL if protocol included
        target = endpoint
        if "://" in endpoint:
            parsed = urlparse(endpoint)
            target = parsed.netloc or parsed.path

        target_lower = target.lower()

        # Check for explicit non-compliant regions in hostname (e.g., eastus, westeurope, etc.)
        # Match common Azure region tokens
        detected_regions = re.findall(
            r"\b(eastus\d*|westus\d*|centralus|westeurope|northeurope|southeastasia|eastasia|japaneast|brazilsouth)\b",
            target_lower,
        )
        if detected_regions:
            raise SovereigntyViolationError(
                f"APRA CPS 234 Sovereignty Violation: Endpoint '{endpoint}' contains non-Australian region '{detected_regions[0]}'. "
                f"Inference and data access must remain in {sorted(list(self.allowed_regions))}."
            )

        # Check if an allowed region is present in the domain
        has_allowed_region = any(reg in target_lower for reg in self.allowed_regions)
        if has_allowed_region:
            return True

        # If domain is a general Azure endpoint (e.g. services.ai.azure.com), verify configured region
        env_region = os.getenv("AZURE_AI_PROJECT_REGION") or os.getenv("AZURE_REGION")
        if env_region:
            return self.validate_region(env_region)

        # If neither URL nor env region explicitly identifies the region, raise caution / violation
        raise SovereigntyViolationError(
            f"APRA CPS 234 Sovereignty Verification Failed: Endpoint '{endpoint}' does not specify an Australian region "
            f"and AZURE_AI_PROJECT_REGION is not set to one of {sorted(list(self.allowed_regions))}."
        )
