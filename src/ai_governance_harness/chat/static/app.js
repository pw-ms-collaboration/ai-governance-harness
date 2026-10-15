"use strict";

const form = document.querySelector("#chat-form");
const input = document.querySelector("#chat-input");
const sendButton = document.querySelector("#send-button");
const messagesElement = document.querySelector("#messages");
const activityStatus = document.querySelector("#activity-status");
const errorMessage = document.querySelector("#error-message");
const characterCount = document.querySelector("#character-count");
const clearButton = document.querySelector("#clear-chat");
const connection = document.querySelector(".connection");
const connectionStatus = document.querySelector("#connection-status");
const governanceOverallStatus = document.querySelector("#governance-overall-status");
const governanceUpdateStatus = document.querySelector("#governance-update-status");
const refreshGovernanceButton = document.querySelector("#refresh-governance");
const pauseGovernanceButton = document.querySelector("#pause-governance");
const allowedCount = document.querySelector("#allowed-count");
const deniedCount = document.querySelector("#denied-count");
const totalCount = document.querySelector("#total-count");
const retainedCount = document.querySelector("#retained-count");
const serviceStatuses = document.querySelector("#service-statuses");
const enforcementMode = document.querySelector("#enforcement-mode");
const sandboxStatus = document.querySelector("#sandbox-status");
const policyDigest = document.querySelector("#policy-digest");
const circuitHealthSummary = document.querySelector("#circuit-health-summary");
const circuitStatuses = document.querySelector("#circuit-statuses");
const decisionEvents = document.querySelector("#decision-events");
const policyRules = document.querySelector("#policy-rules");
const policyFilterControls = [...document.querySelectorAll("[data-policy-filter]")];
const policyFilterStatus = document.querySelector("#policy-filter-status");
const policyCaption = document.querySelector("#policy-caption");
const defaultAction = document.querySelector("#default-action");
const evidenceControls = document.querySelector("#evidence-controls");
const privacyControls = document.querySelector("#privacy-controls");
const personaSelector = document.querySelector("#mock-persona");
const signInButton = document.querySelector("#identity-signin");
const identityStatus = document.querySelector("#identity-status");
const selectedRoleName = document.querySelector("#selected-role-name");
const roleAccessSummary = document.querySelector("#role-access-summary");
const roleAggregate = document.querySelector("#role-aggregate");
const roleMember = document.querySelector("#role-member");
const roleOutreach = document.querySelector("#role-outreach");

let history = [];
let governancePaused = false;
let accessToken = null;
let busy = false;
let governanceBaselineAt = null;
let governanceRetainedLimit = 0;

const circuitPresentation = {
  foundry: {
    label: "AI response service",
    description: "Generates assistant responses after governance allows a request.",
  },
  foundry_advice_classifier: {
    label: "Advice safety classifier",
    description: "Classifies request intent before policy evaluates the chat input.",
  },
  mcp: {
    label: "Governed data tools",
    description: "Retrieves synthetic member and retention workflow data.",
  },
  mcp_observability: {
    label: "Governance monitoring",
    description: "Loads runtime and decision evidence for this panel.",
  },
};

const circuitStatePresentation = {
  closed: {
    label: "Calls allowed",
    badgeClass: "ready",
    explanation: "The failure threshold has not been reached.",
  },
  half_open: {
    label: "Recovery check",
    badgeClass: "partial",
    explanation: "A limited request is testing recovery after recent failures.",
  },
  open: {
    label: "Calls paused",
    badgeClass: "unavailable",
    explanation: "Requests are paused briefly after repeated failures.",
  },
};

const roleAccessPresentation = Object.freeze({
  analyst: {
    name: "Analyst (OBO)",
    summary: "Aggregate insights are available. Member-level tools and outreach are blocked.",
    aggregate: ["Allow", "allowed"],
    member: ["Deny", "denied"],
    outreach: ["Deny", "denied"],
  },
  retention_specialist: {
    name: "Retention Specialist (OBO)",
    summary: "Aggregate and member tools are available. Outreach remains controlled.",
    aggregate: ["Allow", "allowed"],
    member: ["Allow", "allowed"],
    outreach: ["Eligibility + approval", "conditional"],
  },
  compliance_reviewer: {
    name: "Compliance Reviewer (OBO)",
    summary: "Aggregate, member, and outreach tools are blocked for this role.",
    aggregate: ["Deny", "denied"],
    member: ["Deny", "denied"],
    outreach: ["Deny", "denied"],
  },
  administrator: {
    name: "Administrator (OBO)",
    summary: "Aggregate, member, and outreach tools are blocked for this role.",
    aggregate: ["Deny", "denied"],
    member: ["Deny", "denied"],
    outreach: ["Deny", "denied"],
  },
});

// Must match _OUTREACH_APPROVAL_HEADING in chat/service.py.
const APPROVAL_HEADING = "Approval required for ";

function setAccessStatus(element, [label, tone]) {
  element.textContent = label;
  element.className = `access-status ${tone}`;
}

function renderRoleAccessPreview(persona) {
  const presentation = roleAccessPresentation[persona];
  if (!presentation) {
    selectedRoleName.textContent = "Choose a persona to preview access";
    roleAccessSummary.textContent = "Role capabilities will appear here before you sign in.";
    [roleAggregate, roleMember, roleOutreach].forEach((element) => {
      setAccessStatus(element, ["Not selected", "neutral"]);
    });
    return;
  }

  selectedRoleName.textContent = presentation.name;
  roleAccessSummary.textContent = presentation.summary;
  setAccessStatus(roleAggregate, presentation.aggregate);
  setAccessStatus(roleMember, presentation.member);
  setAccessStatus(roleOutreach, presentation.outreach);
}

function setApprovalActionsEnabled(enabled) {
  messagesElement.querySelectorAll(".approval-actions button").forEach((button) => {
    button.disabled = !enabled;
  });
}

function sendApprovalReply(reply, chosen) {
  if (input.disabled) {
    return;
  }
  setApprovalActionsEnabled(false);
  chosen.setAttribute("aria-pressed", "true");
  input.value = reply;
  characterCount.textContent = `${reply.length} / 4000`;
  form.requestSubmit();
}

function approvalActions(content) {
  const memberId = content.slice(APPROVAL_HEADING.length).split(/\s/, 1)[0];
  const group = document.createElement("div");
  group.className = "approval-actions";
  group.setAttribute("role", "group");
  group.setAttribute("aria-label", `Outreach case approval for ${memberId}`);
  for (const [reply, className] of [["Approve", "approve"], ["Decline", "danger-secondary"]]) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = className;
    button.textContent = reply;
    button.setAttribute("aria-pressed", "false");
    button.addEventListener("click", () => sendApprovalReply(reply, button));
    group.append(button);
  }
  const hint = document.createElement("p");
  hint.className = "approval-hint";
  hint.textContent = "Or type Approve or Decline below.";
  group.append(hint);
  return group;
}

function addMessage(role, content, policyNotice = null) {
  // The backend accepts an approval reply only directly after its prompt.
  setApprovalActionsEnabled(false);
  const item = document.createElement("li");
  item.className = `message ${role}`;

  const article = document.createElement("article");
  const heading = document.createElement("h3");
  const body = document.createElement("p");

  heading.textContent = role === "user" ? "You" : "Assistant";
  body.textContent = content;
  article.append(heading, body);
  if (policyNotice) {
    const rule = policyNotice.rule || "unnamed rule";
    const policy = policyNotice.policy_name || "unknown policy";
    const decision = String(policyNotice.decision || "deny").replaceAll("_", " ");
    const notice = document.createElement("p");
    notice.className = "policy-notice";
    notice.textContent = `Policy break: rule ${rule} in ${policy} (${decision}).`;
    article.append(notice);
  }
  if (role === "assistant" && content.startsWith(APPROVAL_HEADING)) {
    article.append(approvalActions(content));
  }
  item.append(article);
  messagesElement.append(item);
  messagesElement.scrollTop = messagesElement.scrollHeight;
}

function setBusy(isBusy) {
  busy = isBusy;
  input.disabled = isBusy;
  sendButton.disabled = isBusy || !accessToken;
  personaSelector.disabled = isBusy;
  signInButton.disabled = isBusy || Boolean(accessToken);
  clearButton.disabled = isBusy;
  activityStatus.textContent = isBusy ? "Thinking and checking governance tools" : "";
  activityStatus.classList.toggle("busy", isBusy);
}

function showError(message) {
  errorMessage.textContent = message;
  errorMessage.hidden = false;
}

function clearError() {
  errorMessage.textContent = "";
  errorMessage.hidden = true;
}

function chatErrorMessage(payload) {
  const error = payload?.error;
  if (typeof error === "string") {
    return error;
  }
  if (!error || typeof error !== "object") {
    return "The chat request failed.";
  }

  const parts = [String(error.message || "The chat request failed.")];
  if (error.details?.matched_rule) {
    parts.push(`Policy rule: ${String(error.details.matched_rule)}.`);
  }
  if (error.details?.finish_reason) {
    parts.push(`Model stop condition: ${String(error.details.finish_reason)}.`);
  }
  if (error.details?.foundry_error_code) {
    parts.push(`Foundry error: ${String(error.details.foundry_error_code)}.`);
  }
  if (error.details?.content_filter_stage) {
    parts.push(`Filtered stage: ${String(error.details.content_filter_stage)}.`);
  }
  if (error.details?.content_filter_category) {
    const severity = error.details.content_filter_severity
      ? ` (${String(error.details.content_filter_severity)})`
      : "";
    parts.push(
      `Foundry content filter: ${String(error.details.content_filter_category)}${severity}.`,
    );
  }
  if (error.details?.required_capability) {
    parts.push(
      `Required client capability: ${String(error.details.required_capability)}.`,
    );
  }
  if (error.details?.tool) {
    parts.push(`Tool: ${String(error.details.tool)}.`);
  }
  if (error.correlation_id) {
    parts.push(`Reference: ${String(error.correlation_id)}.`);
  }
  return parts.join(" ");
}

async function checkHealth() {
  try {
    const response = await fetch("/health/ready", { headers: { Accept: "application/json" } });
    if (!response.ok) {
      throw new Error("not ready");
    }
    connection.classList.add("ready");
    connection.classList.remove("error");
    connectionStatus.textContent = "Chat and governance ready";
  } catch {
    connection.classList.add("error");
    connection.classList.remove("ready");
    connectionStatus.textContent = "Chat service unavailable";
  }
}

function statusClass(value) {
  const normalized = String(value || "neutral").toLowerCase();
  return normalized.replace(/[^a-z_]/g, "_");
}

function makeStatusBadge(value, prefix = "", label = null) {
  const badge = document.createElement("span");
  badge.className = `status-badge ${statusClass(value)}`;
  badge.textContent = label
    ? `${prefix}${label}`
    : `${prefix}${String(value || "unknown").replaceAll("_", " ")}`;
  return badge;
}

function renderServices(services) {
  serviceStatuses.replaceChildren();
  for (const service of Array.isArray(services) ? services : []) {
    const item = document.createElement("li");
    const line = document.createElement("div");
    const name = document.createElement("strong");
    line.className = "status-line";
    name.textContent = String(service.name || "service").toUpperCase();
    line.append(name, makeStatusBadge(service.status));
    item.append(line);
    if (service.detail) {
      const detail = document.createElement("small");
      detail.textContent = String(service.detail);
      item.append(detail);
    }
    serviceStatuses.append(item);
  }
}

function renderCircuits(circuits, services) {
  circuitStatuses.replaceChildren();
  const entries = Object.entries(circuits || {});
  const serviceEntries = Array.isArray(services) ? services : [];
  if (!entries.length) {
    circuitHealthSummary.replaceChildren(
      makeStatusBadge("neutral", "", "Health unavailable"),
      document.createTextNode(" No dependency health information is available."),
    );
    const empty = document.createElement("p");
    empty.textContent = "Dependency health has not been reported yet.";
    circuitStatuses.append(empty);
    return;
  }

  const unavailableServices = serviceEntries.filter((service) => {
    const state = String(service.status || "").toLowerCase();
    return state === "unavailable" || state === "not_ready";
  });
  const partialServices = serviceEntries.filter(
    (service) => String(service.status || "").toLowerCase() === "partial",
  );
  const normalizedStates = entries.map(([, state]) => String(state).toLowerCase());
  let overall = {
    label: "Services ready",
    badgeClass: "ready",
    explanation: "All reported services are available.",
  };
  if (unavailableServices.length) {
    overall = {
      label: "Some services unavailable",
      badgeClass: "unavailable",
      explanation: `${unavailableServices
        .map((service) => String(service.name || "A service").toUpperCase())
        .join(", ")} cannot currently be reached.`,
    };
  } else if (partialServices.length) {
    overall = {
      label: "Partial service health",
      badgeClass: "partial",
      explanation: "At least one service reported partial availability.",
    };
  } else if (normalizedStates.some((state) => state === "open")) {
    overall = {
      label: "Some calls paused",
      badgeClass: "unavailable",
      explanation: "Failure protection is temporarily blocking at least one dependency.",
    };
  } else if (normalizedStates.some((state) => state === "half_open")) {
    overall = {
      label: "Recovery checks active",
      badgeClass: "partial",
      explanation: "Failure protection is testing at least one dependency.",
    };
  } else if (normalizedStates.some((state) => state !== "closed")) {
    overall = {
      label: "Health partly unknown",
      badgeClass: "neutral",
      explanation: "At least one dependency reported an unfamiliar state.",
    };
  }
  circuitHealthSummary.replaceChildren(
    makeStatusBadge(overall.badgeClass, "", overall.label),
    document.createTextNode(` ${overall.explanation}`),
  );

  for (const [name, state] of entries) {
    const item = document.createElement("li");
    const headingRow = document.createElement("div");
    const heading = document.createElement("strong");
    const description = document.createElement("p");
    const technical = document.createElement("small");
    const normalizedState = String(state || "unknown").toLowerCase();
    const component = circuitPresentation[name] || {
      label: name.replaceAll("_", " "),
      description: "Supports governed chat operations.",
    };
    const stateView = circuitStatePresentation[normalizedState] || {
      label: "Unknown",
      badgeClass: "neutral",
      explanation: "No recognized health state was reported.",
    };

    item.className = "health-card";
    headingRow.className = "health-card-heading";
    heading.textContent = component.label;
    headingRow.append(
      heading,
      makeStatusBadge(stateView.badgeClass, "", stateView.label),
    );
    description.textContent = component.description;
    technical.textContent = `${stateView.explanation} Technical circuit state: ${normalizedState.replaceAll("_", " ")}.`;
    item.append(headingRow, description, technical);
    circuitStatuses.append(item);
  }
}

function appendTableCell(row, value, { code = false } = {}) {
  const cell = document.createElement("td");
  if (code) {
    const element = document.createElement("code");
    element.textContent = String(value);
    cell.append(element);
  } else {
    cell.textContent = String(value);
  }
  row.append(cell);
}

function provenanceLabel(provenance, { includeSource = false, action = null } = {}) {
  if (!provenance) {
    return action === "deny" ? "System policy" : "Not attributed";
  }
  const layer = provenance.layer === "business-unit" ? "Business unit" : "Enterprise";
  const label = `${layer}: ${provenance.policy_id} v${provenance.policy_version}`;
  return includeSource ? `${label} (${provenance.source})` : label;
}

function renderEvents(events) {
  decisionEvents.replaceChildren();
  const values = Array.isArray(events) ? events : [];
  if (!values.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 9;
    cell.textContent = "No governance decisions have been recorded yet.";
    row.append(cell);
    decisionEvents.append(row);
    return;
  }
  for (const event of values) {
    const row = document.createElement("tr");
    const occurredAt = new Date(event.occurred_at);
    appendTableCell(
      row,
      Number.isNaN(occurredAt.getTime())
        ? "Unknown"
        : occurredAt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
    );
    appendTableCell(row, event.source || "unknown");
    appendTableCell(row, [event.boundary, event.actor, event.token_type, event.staff_role]
      .filter(Boolean).join(" / ") || "No identity");
    appendTableCell(row, event.lifecycle_point || "unknown");
    appendTableCell(row, event.action || "unknown", { code: true });

    const decisionCell = document.createElement("td");
    const decisionBadge = document.createElement("span");
    decisionBadge.className = `decision-badge ${statusClass(event.decision)}`;
    decisionBadge.textContent = String(event.decision || "unknown").replaceAll("_", " ");
    decisionCell.append(decisionBadge);
    row.append(decisionCell);
    appendTableCell(row, event.matched_rule || "no rule matched", { code: true });
    appendTableCell(row, provenanceLabel(event.provenance, { action: event.decision }));
    appendTableCell(row, `${Number(event.evaluation_ms || 0).toFixed(3)} ms`);
    decisionEvents.append(row);
  }
}

function renderPolicy(policy) {
  const safePolicy = policy || {};
  policyCaption.textContent = safePolicy.name
    ? `${safePolicy.name} version ${safePolicy.version || "unknown"}`
    : "Active packaged policy";
  defaultAction.textContent = String(safePolicy.default_action || "unknown").replaceAll("_", " ");
  policyDigest.textContent = safePolicy.digest || "Unknown";
  policyRules.replaceChildren();
  for (const rule of Array.isArray(safePolicy.rules) ? safePolicy.rules : []) {
    const row = document.createElement("tr");
    appendTableCell(row, rule.stage || "unknown");
    appendTableCell(row, rule.name || "unnamed");
    appendTableCell(row, rule.action || "unknown");
    appendTableCell(row, provenanceLabel(rule.provenance, {
      includeSource: true,
      action: rule.action,
    }));
    appendTableCell(row, rule.condition || "No condition", { code: true });
    policyRules.append(row);
  }
  refreshPolicyFilterOptions();
  applyPolicyFilters();
}

function policyCellText(row, column) {
  return row.cells[column]?.textContent.trim() || "";
}

function refreshPolicyFilterOptions() {
  const rows = [...policyRules.rows];
  for (const control of policyFilterControls) {
    if (control.tagName !== "SELECT") {
      continue;
    }
    const column = Number(control.dataset.policyFilter);
    const values = [...new Set(rows.map((row) => policyCellText(row, column)))].sort();
    const selected = values.includes(control.value) ? control.value : "";
    const options = [new Option("All", "")];
    for (const value of values) {
      options.push(new Option(value, value));
    }
    control.replaceChildren(...options);
    control.value = selected;
  }
}

function applyPolicyFilters() {
  const active = policyFilterControls
    .map((control) => ({
      column: Number(control.dataset.policyFilter),
      value: control.value.trim().toLowerCase(),
      exact: control.tagName === "SELECT",
    }))
    .filter((filter) => filter.value);
  const rows = [...policyRules.rows];
  let visible = 0;
  for (const row of rows) {
    const matches = active.every((filter) => {
      const text = policyCellText(row, filter.column).toLowerCase();
      return filter.exact ? text === filter.value : text.includes(filter.value);
    });
    row.hidden = !matches;
    if (matches) {
      visible += 1;
    }
  }
  policyFilterStatus.textContent = active.length
    ? `Showing ${visible} of ${rows.length} rules.`
    : "";
}

for (const control of policyFilterControls) {
  control.addEventListener(control.tagName === "SELECT" ? "change" : "input", applyPolicyFilters);
}

function renderEvidence(evidence) {
  evidenceControls.replaceChildren();
  for (const control of Array.isArray(evidence?.controls) ? evidence.controls : []) {
    const item = document.createElement("li");
    const heading = document.createElement("div");
    const name = document.createElement("strong");
    const status = document.createElement("span");
    heading.className = "evidence-heading";
    name.textContent = `${control.id}: ${control.title}`;
    status.className = `evidence-status ${statusClass(control.status)}`;
    status.textContent = String(control.status || "gap").replaceAll("_", " ");
    heading.append(name, status);
    item.append(heading);

    const evidenceItems = Array.isArray(control.evidence) ? control.evidence : [];
    if (evidenceItems.length) {
      const detail = document.createElement("small");
      detail.textContent = `Evidence: ${evidenceItems.join("; ")}`;
      item.append(detail);
    }
    if (control.limitation) {
      const limitation = document.createElement("small");
      limitation.textContent = `Limitation: ${control.limitation}`;
      item.append(limitation);
    }
    evidenceControls.append(item);
  }
}

function renderPrivacy(privacy) {
  const labels = {
    retention: "Retention",
    raw_prompts: "Raw prompts collected",
    raw_arguments: "Raw arguments collected",
    raw_results: "Raw results collected",
    member_data: "Member data collected",
    raw_identity_claims: "Raw identity claims collected",
  };
  privacyControls.replaceChildren();
  for (const [key, label] of Object.entries(labels)) {
    const item = document.createElement("li");
    const strong = document.createElement("strong");
    strong.textContent = `${label}: `;
    item.append(strong, document.createTextNode(String(privacy?.[key] ?? "unknown").replaceAll("_", " ")));
    privacyControls.append(item);
  }
}

function renderGovernance(snapshot) {
  const status = snapshot.status || "unknown";
  governanceOverallStatus.className = `status-badge ${statusClass(status)}`;
  governanceOverallStatus.textContent = String(status).replaceAll("_", " ");

  const events = snapshot.events || {};
  const counts = events.counts || {};
  governanceRetainedLimit = Number(events.retained_limit || 0);
  const recentEvents = Array.isArray(events.recent_events) ? events.recent_events : [];
  const visibleEvents = governanceBaselineAt === null
    ? recentEvents
    : recentEvents.filter((event) => {
      const occurredAt = new Date(event.occurred_at).getTime();
      return Number.isFinite(occurredAt) && occurredAt > governanceBaselineAt;
    });
  const visibleCounts = governanceBaselineAt === null
    ? counts
    : visibleEvents.reduce(
      (totals, event) => {
        if (event.decision === "allow") {
          totals.allow += 1;
        } else if (event.decision === "deny") {
          totals.deny += 1;
        }
        return totals;
      },
      { allow: 0, deny: 0 },
    );
  allowedCount.textContent = String(visibleCounts.allow || 0);
  deniedCount.textContent = String(visibleCounts.deny || 0);
  totalCount.textContent = String(
    governanceBaselineAt === null ? events.total || 0 : visibleEvents.length,
  );
  retainedCount.textContent = `${
    governanceBaselineAt === null ? events.retained || 0 : visibleEvents.length
  } / ${governanceRetainedLimit}`;

  renderServices(snapshot.services);
  enforcementMode.textContent = String(snapshot.runtime?.enforcement || "unknown").replaceAll("_", " ");
  sandboxStatus.textContent = [
    snapshot.runtime?.sandbox?.provider || "unknown",
    snapshot.runtime?.sandbox?.status || "unknown",
  ].join(" — ").replaceAll("_", " ");
  renderCircuits(snapshot.runtime?.circuits, snapshot.services);
  renderEvents(visibleEvents);
  renderPolicy(snapshot.policy);
  renderEvidence(snapshot.evidence);
  renderPrivacy(snapshot.privacy);
}

async function refreshGovernance({ announce = false } = {}) {
  refreshGovernanceButton.disabled = true;
  try {
    const response = await fetch("/api/governance/snapshot", {
      headers: { Accept: "application/json" },
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "Governance data is unavailable.");
    }
    renderGovernance(payload);
    if (announce) {
      governanceUpdateStatus.textContent = "Governance data refreshed.";
    }
  } catch (error) {
    governanceOverallStatus.className = "status-badge unavailable";
    governanceOverallStatus.textContent = "Unavailable";
    governanceUpdateStatus.textContent = error.message || "Governance data is unavailable.";
  } finally {
    refreshGovernanceButton.disabled = false;
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearError();
  if (busy) return;
  if (!accessToken) {
    showError("Choose a persona and sign in before sending.");
    personaSelector.focus();
    return;
  }
  const content = input.value.trim();
  if (!content) {
    showError("Enter a message before sending.");
    input.focus();
    return;
  }

  addMessage("user", content);
  history.push({ role: "user", content });
  history = history.slice(-20);
  input.value = "";
  characterCount.textContent = "0 / 4000";
  setBusy(true);

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json", Accept: "application/json",
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify({ messages: history }),
    });
    const payload = await response.json();
    if (!response.ok) {
      if (response.status === 401) {
        accessToken = null;
        identityStatus.textContent = "Your sign-in expired. Sign in again.";
      }
      throw new Error(chatErrorMessage(payload));
    }
    addMessage("assistant", payload.message, payload.policy_notice);
    history.push({ role: "assistant", content: payload.message });
    history = history.slice(-20);
  } catch (error) {
    const failedTurn = history.at(-1);
    if (failedTurn?.role === "user" && failedTurn.content === content) {
      history.pop();
    }
    const lastTurn = history.at(-1);
    if (accessToken && lastTurn?.role === "assistant" && lastTurn.content.startsWith(APPROVAL_HEADING)) {
      const latestActions = messagesElement.querySelectorAll(".approval-actions");
      latestActions[latestActions.length - 1]
        ?.querySelectorAll("button")
        .forEach((button) => {
          button.disabled = false;
          button.setAttribute("aria-pressed", "false");
        });
    }
    showError(error.message || "The chat service could not be reached.");
  } finally {
    setBusy(false);
    refreshGovernance();
    input.focus();
  }
});

function clearIdentityConversation() {
  accessToken = null;
  history = [];
  messagesElement.replaceChildren();
  input.value = "";
  characterCount.textContent = "0 / 4000";
  clearError();
  setBusy(false);
}

personaSelector.addEventListener("change", () => {
  clearIdentityConversation();
  renderRoleAccessPreview(personaSelector.value);
  identityStatus.textContent = "Persona changed. Sign in to start a new conversation.";
});

signInButton.addEventListener("click", async () => {
  if (busy) return;
  clearIdentityConversation();
  const persona = personaSelector.value;
  if (!persona) {
    showError("Choose a persona first.");
    personaSelector.focus();
    return;
  }
  setBusy(true);
  identityStatus.textContent = "Signing in...";
  try {
    const response = await fetch("/api/mock-identity/signin", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ persona }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(chatErrorMessage(payload));
    if (typeof payload.access_token !== "string" || payload.token_type !== "Bearer"
        || payload.persona !== persona) {
      throw new Error("The identity service returned an invalid sign-in response.");
    }
    accessToken = payload.access_token;
    const label = personaSelector.selectedOptions[0].textContent;
    identityStatus.textContent = `Signed in as ${label}.`;
  } catch (error) {
    accessToken = null;
    identityStatus.textContent = "Sign-in failed. Try signing in again.";
    showError(error.message || "The identity service could not be reached.");
  } finally {
    setBusy(false);
  }
});

input.addEventListener("input", () => {
  characterCount.textContent = `${input.value.length} / 4000`;
});

input.addEventListener("keydown", (event) => {
  if (event.ctrlKey && event.key === "Enter") {
    event.preventDefault();
    form.requestSubmit();
  }
});

document.querySelectorAll(".example").forEach((button) => {
  button.addEventListener("click", () => {
    input.value = button.dataset.question || "";
    characterCount.textContent = `${input.value.length} / 4000`;
    input.focus();
  });
});

clearButton.addEventListener("click", () => {
  history = [];
  governanceBaselineAt = Date.now();
  messagesElement.replaceChildren();
  addMessage(
    "assistant",
    "Conversation cleared. Ask about a synthetic member, churn risk, or FUM outflow permitted by your role.",
  );
  allowedCount.textContent = "0";
  deniedCount.textContent = "0";
  totalCount.textContent = "0";
  retainedCount.textContent = `0 / ${governanceRetainedLimit}`;
  renderEvents([]);
  governanceUpdateStatus.textContent = (
    "Conversation and visible governance decisions cleared. "
    + "New decisions will appear here."
  );
  clearError();
  input.focus();
});

refreshGovernanceButton.addEventListener("click", () => {
  refreshGovernance({ announce: true });
});

pauseGovernanceButton.addEventListener("click", () => {
  governancePaused = !governancePaused;
  pauseGovernanceButton.setAttribute("aria-pressed", String(governancePaused));
  pauseGovernanceButton.textContent = governancePaused ? "Resume updates" : "Pause updates";
  governanceUpdateStatus.textContent = governancePaused
    ? "Automatic governance updates paused."
    : "Automatic governance updates resumed.";
  if (!governancePaused) {
    refreshGovernance();
  }
});

window.setInterval(() => {
  if (!governancePaused && document.visibilityState === "visible") {
    refreshGovernance();
  }
}, 5000);

renderRoleAccessPreview(personaSelector.value);
checkHealth();
refreshGovernance();
