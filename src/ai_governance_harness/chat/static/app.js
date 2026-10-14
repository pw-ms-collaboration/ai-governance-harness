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
const demoDenyButton = document.querySelector("#demo-deny");
const allowedCount = document.querySelector("#allowed-count");
const deniedCount = document.querySelector("#denied-count");
const totalCount = document.querySelector("#total-count");
const retainedCount = document.querySelector("#retained-count");
const serviceStatuses = document.querySelector("#service-statuses");
const enforcementMode = document.querySelector("#enforcement-mode");
const sandboxStatus = document.querySelector("#sandbox-status");
const policyDigest = document.querySelector("#policy-digest");
const circuitStatuses = document.querySelector("#circuit-statuses");
const decisionEvents = document.querySelector("#decision-events");
const policyRules = document.querySelector("#policy-rules");
const policyCaption = document.querySelector("#policy-caption");
const defaultAction = document.querySelector("#default-action");
const evidenceControls = document.querySelector("#evidence-controls");
const privacyControls = document.querySelector("#privacy-controls");

let history = [];
let governancePaused = false;

function addMessage(role, content, policyNotice = null) {
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
  item.append(article);
  messagesElement.append(item);
  messagesElement.scrollTop = messagesElement.scrollHeight;
}

function setBusy(isBusy) {
  input.disabled = isBusy;
  sendButton.disabled = isBusy;
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

function makeStatusBadge(value, prefix = "") {
  const badge = document.createElement("span");
  badge.className = `status-badge ${statusClass(value)}`;
  badge.textContent = `${prefix}${String(value || "unknown").replaceAll("_", " ")}`;
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

function renderCircuits(circuits) {
  circuitStatuses.replaceChildren();
  const entries = Object.entries(circuits || {});
  if (!entries.length) {
    const empty = document.createElement("p");
    empty.textContent = "No remote circuit state is available.";
    circuitStatuses.append(empty);
    return;
  }
  for (const [name, state] of entries) {
    const card = document.createElement("div");
    const heading = document.createElement("strong");
    const value = document.createElement("span");
    card.className = "circuit-card";
    heading.textContent = name.replaceAll("_", " ");
    value.textContent = String(state).replaceAll("_", " ");
    card.append(heading, value);
    circuitStatuses.append(card);
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
    cell.colSpan = 8;
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
  allowedCount.textContent = String(counts.allow || 0);
  deniedCount.textContent = String(counts.deny || 0);
  totalCount.textContent = String(events.total || 0);
  retainedCount.textContent = `${events.retained || 0} / ${events.retained_limit || 0}`;

  renderServices(snapshot.services);
  enforcementMode.textContent = String(snapshot.runtime?.enforcement || "unknown").replaceAll("_", " ");
  sandboxStatus.textContent = [
    snapshot.runtime?.sandbox?.provider || "unknown",
    snapshot.runtime?.sandbox?.status || "unknown",
  ].join(" — ").replaceAll("_", " ");
  renderCircuits(snapshot.runtime?.circuits);
  renderEvents(events.recent_events);
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
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ messages: history }),
    });
    const payload = await response.json();
    if (!response.ok) {
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
    showError(error.message || "The chat service could not be reached.");
  } finally {
    setBusy(false);
    refreshGovernance();
    input.focus();
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
  messagesElement.replaceChildren();
  addMessage(
    "assistant",
    "Conversation cleared. Ask for a synthetic customer's account profile by member ID.",
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

demoDenyButton.addEventListener("click", async () => {
  demoDenyButton.disabled = true;
  governanceUpdateStatus.textContent = "Evaluating a fixed prohibited action.";
  try {
    const response = await fetch("/api/governance/demo/deny", {
      method: "POST",
      headers: { Accept: "application/json" },
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "The default-deny demonstration failed.");
    }
    governanceUpdateStatus.textContent = `${payload.message} Decision: ${payload.decision}.`;
    await refreshGovernance();
  } catch (error) {
    governanceUpdateStatus.textContent = error.message || "The default-deny demonstration failed.";
  } finally {
    demoDenyButton.disabled = false;
  }
});

window.setInterval(() => {
  if (!governancePaused && document.visibilityState === "visible") {
    refreshGovernance();
  }
}, 5000);

checkHealth();
refreshGovernance();
