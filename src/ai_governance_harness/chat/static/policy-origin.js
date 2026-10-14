export function provenanceLabel(provenance, { includeSource = false, action = null } = {}) {
  if (!provenance) {
    return action === "deny" ? "System policy" : "Not attributed";
  }
  const layers = {
    "business-unit": "Business unit",
    enterprise: "Enterprise",
    identity: "Identity",
    regulation: "Regulation",
  };
  const layer = layers[provenance.layer] || "Unknown origin";
  const label = `${layer}: ${provenance.policy_id} v${provenance.policy_version}`;
  return includeSource ? `${label} (${provenance.source})` : label;
}
