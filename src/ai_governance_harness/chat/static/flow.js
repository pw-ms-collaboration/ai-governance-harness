(() => {
  "use strict";

  const SVG_NS = "http://www.w3.org/2000/svg";
  const POLL_MS = 2000;
  const TRAVEL_MS = 1800;
  const STAGGER_MS = 320;
  const MAX_IN_FLIGHT = 24;
  const MAX_TICKER = 25;
  const MAX_CATCH_UP = 12;
  const MAX_HISTORY = 100;

  const panel = document.querySelector("#panel-observability");
  const svg = document.querySelector("#flow-svg");
  if (!panel || !svg) {
    return;
  }

  const particles = document.querySelector("#flow-particles");
  const gate = document.querySelector("#flow-gate");
  const gateStage = document.querySelector("#flow-gate-stage");
  const statusBadge = document.querySelector("#flow-status");
  const pauseButton = document.querySelector("#flow-pause");
  const replayButton = document.querySelector("#flow-replay");
  const ticker = document.querySelector("#flow-ticker");
  const announcer = document.querySelector("#flow-announcer");
  const tickerTitle = document.querySelector("#flow-ticker-title");
  const tickerEmpty = document.querySelector("#flow-ticker-empty");
  const filterSummary = document.querySelector("#flow-filter-summary");
  const clearButton = document.querySelector("#flow-filter-clear");
  const filterChips = [...panel.querySelectorAll(".flow-filters .flow-chip")];
  const flowSection = svg.closest(".flow-panel");
  const gatePopover = document.querySelector("#flow-gate-popover");
  const gatePopoverMeta = document.querySelector("#flow-gate-popover-meta");
  const gatePopoverList = document.querySelector("#flow-gate-popover-list");
  const gatePopoverFoot = document.querySelector("#flow-gate-popover-foot");
  const gatePopoverClose = gatePopover.querySelector(".flow-gate-popover-close");
  const MAX_GATE_RULES = 8;
  let gatePinned = false;
  let gateHideTimer = null;
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

  const OUTCOMES = {
    allow: { label: "Policy allowed", decisions: ["allow"] },
    deny: { label: "Policy denied", decisions: ["deny"] },
    approval: { label: "Approval required", decisions: ["require_approval"] },
    other: { label: "Warn / log / other", decisions: ["warn", "log", "transform", "escalate"] },
  };

  const SOURCES = { chat: "Chat", gateway: "Gateway", mcp: "MCP" };

  const seen = new Set();
  const filters = { outcome: "all", source: "all" };
  let history = [];
  let latestEvents = [];
  let initialised = false;
  let paused = false;
  let inFlight = 0;
  let pollTimer = null;

  function outcomeFor(decision) {
    const value = String(decision || "").toLowerCase();
    for (const [key, outcome] of Object.entries(OUTCOMES)) {
      if (outcome.decisions.includes(value)) {
        return key;
      }
    }
    return "other";
  }

  function sourceFor(event) {
    return ["mcp", "gateway"].includes(event.source) ? event.source : "chat";
  }

  function matchesFilter(event) {
    return (filters.outcome === "all" || outcomeFor(event.decision) === filters.outcome)
      && (filters.source === "all" || sourceFor(event) === filters.source);
  }

  function eventKey(event) {
    return `${event.source}:${event.sequence}:${event.occurred_at}`;
  }

  function label(value) {
    return String(value || "unknown").replaceAll("_", " ");
  }

  function setStatus(text, state) {
    statusBadge.textContent = text;
    statusBadge.className = `flow-status ${state}`;
  }

  function pulse(element, className) {
    element.classList.remove(className);
    void element.getBoundingClientRect();
    element.classList.add(className);
  }

  function updateCounts(counts) {
    for (const [key, outcome] of Object.entries(OUTCOMES)) {
      const total = outcome.decisions.reduce((sum, decision) => sum + Number(counts?.[decision] || 0), 0);
      const node = document.querySelector(`#flow-count-${key}`);
      if (node && node.textContent !== String(total)) {
        node.textContent = String(total);
      }
    }
  }

  function createShape(outcome) {
    const group = document.createElementNS(SVG_NS, "g");
    group.setAttribute("class", `flow-particle flow-${outcome}`);
    let shape;
    if (outcome === "allow") {
      shape = document.createElementNS(SVG_NS, "circle");
      shape.setAttribute("r", "9");
    } else if (outcome === "deny") {
      shape = document.createElementNS(SVG_NS, "rect");
      shape.setAttribute("x", "-8");
      shape.setAttribute("y", "-8");
      shape.setAttribute("width", "16");
      shape.setAttribute("height", "16");
    } else if (outcome === "approval") {
      shape = document.createElementNS(SVG_NS, "polygon");
      shape.setAttribute("points", "0,-11 11,0 0,11 -11,0");
    } else {
      shape = document.createElementNS(SVG_NS, "polygon");
      shape.setAttribute("points", "0,-11 10,8 -10,8");
    }
    group.append(shape);
    return group;
  }

  function arrive(event, outcome, replay) {
    const node = document.querySelector(`#flow-node-${outcome}`);
    if (node) {
      pulse(node, "pulse");
    }
    if (!replay) {
      addToHistory(event);
    }
  }

  function animate(event, replay = false) {
    const outcome = outcomeFor(event.decision);
    const source = sourceFor(event);
    if (reducedMotion.matches || inFlight >= MAX_IN_FLIGHT) {
      arrive(event, outcome, replay);
      return;
    }

    const inbound = document.querySelector(`#flow-in-${source}`);
    const outbound = document.querySelector(`#flow-out-${outcome}`);
    const inLength = inbound.getTotalLength();
    const outLength = outbound.getTotalLength();
    const particle = createShape(outcome);
    particle.classList.toggle("is-dimmed", !matchesFilter(event));
    particles.append(particle);
    inFlight += 1;

    let gateReached = false;
    const started = performance.now();
    const step = (now) => {
      const progress = Math.min((now - started) / TRAVEL_MS, 1);
      let point;
      if (progress < 0.5) {
        point = inbound.getPointAtLength(inLength * (progress / 0.5));
      } else {
        if (!gateReached) {
          gateReached = true;
          gateStage.textContent = `${label(event.lifecycle_point)} · ${label(event.decision)}`;
          pulse(gate, "active");
        }
        point = outbound.getPointAtLength(outLength * ((progress - 0.5) / 0.5));
      }
      particle.setAttribute("transform", `translate(${point.x} ${point.y})`);
      if (progress < 1) {
        window.requestAnimationFrame(step);
        return;
      }
      particle.remove();
      inFlight -= 1;
      arrive(event, outcome, replay);
    };
    window.requestAnimationFrame(step);
  }

  function formatTime(value) {
    const date = new Date(value);
    return Number.isNaN(date.getTime())
      ? "--:--:--"
      : date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  }

  function buildTickerRow(event, isNew) {
    const outcome = outcomeFor(event.decision);
    const row = document.createElement("li");
    row.className = `flow-${outcome}${isNew ? " flow-new" : ""}`;

    const time = document.createElement("time");
    time.dateTime = event.occurred_at || "";
    time.textContent = formatTime(event.occurred_at);

    const origin = document.createElement("span");
    origin.textContent = `${label(event.source)} · ${label(event.lifecycle_point)}`;

    const detail = document.createElement("span");
    const action = document.createElement("code");
    action.textContent = event.action || "unknown";
    const rule = document.createElement("span");
    rule.className = "flow-rule";
    rule.textContent = ` rule ${event.matched_rule || "none"}`;
    detail.append(action, rule);

    const result = document.createElement("span");
    result.className = "flow-outcome-text";
    result.textContent = OUTCOMES[outcome].label;

    row.append(time, origin, detail, result);
    return row;
  }

  function filterDescription() {
    const parts = [];
    if (filters.outcome !== "all") {
      parts.push(OUTCOMES[filters.outcome].label.toLowerCase());
    }
    if (filters.source !== "all") {
      parts.push(`from ${SOURCES[filters.source]}`);
    }
    return parts.join(" ");
  }

  function renderTicker(newKeys = new Set()) {
    const matching = history.filter(matchesFilter);
    const rows = matching.slice(0, MAX_TICKER).map((event) => buildTickerRow(event, newKeys.has(eventKey(event))));
    ticker.replaceChildren(...rows);

    const filtered = filters.outcome !== "all" || filters.source !== "all";
    const description = filterDescription();
    tickerTitle.textContent = filtered ? `Latest decisions: ${description}` : "Latest decisions";
    filterSummary.textContent = filtered
      ? `${matching.length} of ${history.length} recent decisions match`
      : `${history.length} recent decisions`;
    clearButton.hidden = !filtered;
    tickerEmpty.hidden = matching.length > 0;
    tickerEmpty.textContent = filtered
      ? `No ${description} decisions in the recent window.`
      : "No decisions yet. Send a chat message to see live policy decisions.";
    renderGatePopover();
  }

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) {
      node.className = className;
    }
    if (text !== undefined) {
      node.textContent = text;
    }
    return node;
  }

  function summariseRules(events) {
    const groups = new Map();
    for (const event of events) {
      const outcome = outcomeFor(event.decision);
      const rule = event.matched_rule || "";
      const key = `${rule}|${outcome}`;
      let group = groups.get(key);
      if (!group) {
        group = { rule, outcome, count: 0, points: new Set(), sources: new Set(), totalMs: 0, timed: 0 };
        groups.set(key, group);
      }
      group.count += 1;
      group.points.add(label(event.lifecycle_point));
      group.sources.add(SOURCES[sourceFor(event)]);
      if (typeof event.evaluation_ms === "number") {
        group.totalMs += event.evaluation_ms;
        group.timed += 1;
      }
    }
    return [...groups.values()].sort((a, b) => b.count - a.count || a.rule.localeCompare(b.rule));
  }

  function buildRuleRow(group) {
    const row = el("li", `flow-gate-rule flow-${group.outcome}`);
    const dot = el("span", "flow-gate-rule-dot");
    dot.setAttribute("aria-hidden", "true");
    const body = el("div", "flow-gate-rule-body");
    const name = el("code", "flow-gate-rule-name", group.rule || "No matching rule");
    const avg = group.timed ? ` · ${(group.totalMs / group.timed).toFixed(2)} ms` : "";
    const detail = group.rule
      ? `${[...group.points].join(", ")} · ${[...group.sources].join(", ")}${avg}`
      : `Default deny: no allow rule matched · ${[...group.points].join(", ")}`;
    body.append(name, el("span", "flow-gate-rule-detail", detail));
    const badge = el("span", "flow-gate-rule-count", `${group.count}`);
    badge.setAttribute("aria-label", `${group.count} ${OUTCOMES[group.outcome].label.toLowerCase()}`);
    row.append(dot, body, badge);
    return row;
  }

  function renderGatePopover() {
    if (gatePopover.hidden) {
      return;
    }
    const matching = history.filter(matchesFilter);
    const groups = summariseRules(matching);
    const description = filterDescription();
    gatePopoverMeta.textContent = matching.length
      ? `${groups.length} rule outcome${groups.length === 1 ? "" : "s"} across the last ${matching.length}${description ? ` ${description}` : ""} decisions`
      : "No decisions in the recent window yet.";
    const rows = groups.slice(0, MAX_GATE_RULES).map(buildRuleRow);
    if (groups.length > MAX_GATE_RULES) {
      rows.push(el("li", "flow-gate-rule-more", `+${groups.length - MAX_GATE_RULES} more`));
    }
    gatePopoverList.replaceChildren(...rows);
    const policies = [...new Set(matching.map((event) => event.policy_name).filter(Boolean))];
    const modes = [...new Set(matching.map((event) => event.enforcement_mode).filter(Boolean))];
    gatePopoverFoot.textContent = policies.length
      ? `Policy ${policies.join(", ")}${modes.length ? ` · ${modes.join(", ")} mode` : ""}`
      : "";
    gatePopoverFoot.hidden = !policies.length;
  }

  function positionGatePopover() {
    const shield = gate.querySelector("path").getBoundingClientRect();
    const host = flowSection.getBoundingClientRect();
    const width = gatePopover.offsetWidth;
    const centre = shield.left - host.left + shield.width / 2;
    const left = Math.min(Math.max(centre - width / 2, 12), host.width - width - 12);
    gatePopover.style.left = `${Math.max(left, 12)}px`;
    gatePopover.style.top = `${shield.bottom - host.top + 10}px`;
    gatePopover.style.setProperty("--arrow-left", `${centre - Math.max(left, 12) - 6}px`);
  }

  function openGatePopover(pin) {
    window.clearTimeout(gateHideTimer);
    gatePinned = gatePinned || pin;
    gatePopover.hidden = false;
    gate.setAttribute("aria-expanded", "true");
    gate.classList.add("is-open");
    renderGatePopover();
    positionGatePopover();
  }

  function closeGatePopover(returnFocus = false) {
    window.clearTimeout(gateHideTimer);
    gatePinned = false;
    gatePopover.hidden = true;
    gate.setAttribute("aria-expanded", "false");
    gate.classList.remove("is-open");
    if (returnFocus) {
      gate.focus();
    }
  }

  function scheduleGateHide() {
    if (gatePinned) {
      return;
    }
    window.clearTimeout(gateHideTimer);
    gateHideTimer = window.setTimeout(() => closeGatePopover(), 180);
  }

  function addToHistory(event) {
    if (history.some((item) => eventKey(item) === eventKey(event))) {
      return;
    }
    history = [event, ...history].slice(0, MAX_HISTORY);
    renderTicker(new Set([eventKey(event)]));
  }

  function applyFilterState() {
    for (const chip of filterChips) {
      chip.setAttribute("aria-pressed", String(filters[chip.dataset.filter] === chip.dataset.value));
    }
    for (const node of svg.querySelectorAll("[data-filter]")) {
      const active = filters[node.dataset.filter];
      node.classList.toggle("is-selected", active === node.dataset.value);
      node.classList.toggle("is-dimmed", active !== "all" && active !== node.dataset.value);
      if (node.hasAttribute("aria-pressed")) {
        node.setAttribute("aria-pressed", String(active === node.dataset.value));
      }
    }
    for (const path of svg.querySelectorAll(".flow-paths path")) {
      const [, direction, value] = path.id.split("-");
      const active = filters[direction === "in" ? "source" : "outcome"];
      path.classList.toggle("is-dimmed", active !== "all" && active !== value);
    }
    renderTicker();
  }

  function setFilter(kind, value, toggle = false) {
    filters[kind] = toggle && filters[kind] === value ? "all" : value;
    applyFilterState();
    const description = filterDescription();
    const count = history.filter(matchesFilter).length;
    announcer.textContent = description
      ? `Showing ${count} ${description} decisions.`
      : `Showing all ${history.length} recent decisions.`;
  }

  function announce(events) {
    const totals = {};
    for (const event of events) {
      const name = OUTCOMES[outcomeFor(event.decision)].label.toLowerCase();
      totals[name] = (totals[name] || 0) + 1;
    }
    const parts = Object.entries(totals).map(([name, count]) => `${count} ${name}`);
    announcer.textContent = `${events.length} new decision${events.length === 1 ? "" : "s"}: ${parts.join(", ")}.`;
  }

  function play(events, replay = false) {
    events.forEach((event, index) => {
      window.setTimeout(() => animate(event, replay), index * STAGGER_MS);
    });
  }

  function chronological(events) {
    return [...events].sort((a, b) => String(a.occurred_at).localeCompare(String(b.occurred_at)));
  }

  function ingest(snapshot) {
    const eventsBlock = snapshot.events || {};
    const events = chronological(Array.isArray(eventsBlock.recent_events) ? eventsBlock.recent_events : []);
    latestEvents = events;
    updateCounts(eventsBlock.counts || {});

    const fresh = events.filter((event) => !seen.has(eventKey(event)));
    fresh.forEach((event) => seen.add(eventKey(event)));

    if (!initialised) {
      initialised = true;
      history = [...events].reverse().slice(0, MAX_HISTORY);
      renderTicker();
      return;
    }
    if (fresh.length === 0) {
      return;
    }
    announce(fresh);
    play(fresh.slice(-MAX_CATCH_UP));
  }

  function isActive() {
    return !paused && !panel.hidden && document.visibilityState === "visible";
  }

  async function poll() {
    pollTimer = null;
    if (isActive() || (!initialised && !paused)) {
      try {
        const response = await fetch("/api/governance/snapshot", {
          headers: { Accept: "application/json" },
          cache: "no-store",
        });
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        ingest(await response.json());
        setStatus("Live", "live");
      } catch {
        setStatus("Reconnecting", "error");
      }
    }
    schedule();
  }

  function schedule() {
    if (pollTimer === null) {
      pollTimer = window.setTimeout(poll, POLL_MS);
    }
  }

  function resumeNow() {
    if (!isActive()) {
      return;
    }
    if (pollTimer !== null) {
      window.clearTimeout(pollTimer);
      pollTimer = null;
    }
    poll();
  }

  pauseButton.addEventListener("click", () => {
    paused = !paused;
    pauseButton.setAttribute("aria-pressed", String(paused));
    pauseButton.textContent = paused ? "Resume" : "Pause";
    if (paused) {
      setStatus("Paused", "paused");
    } else {
      resumeNow();
    }
  });

  replayButton.addEventListener("click", () => {
    const recent = latestEvents.filter(matchesFilter).slice(-MAX_CATCH_UP);
    if (recent.length === 0) {
      announcer.textContent = "No recent decisions to replay.";
      return;
    }
    announcer.textContent = `Replaying ${recent.length} recent decisions.`;
    play(recent, true);
  });

  for (const chip of filterChips) {
    chip.addEventListener("click", () => setFilter(chip.dataset.filter, chip.dataset.value));
  }

  clearButton.addEventListener("click", () => {
    filters.outcome = "all";
    setFilter("source", "all");
  });

  svg.addEventListener("keydown", (event) => {
    if (event.target === gate && (event.key === "Enter" || event.key === " ")) {
      event.preventDefault();
      if (gatePinned) {
        closeGatePopover();
      } else {
        openGatePopover(true);
      }
      return;
    }
    const node = event.target.closest?.("[data-filter][role=button]");
    if (node && (event.key === "Enter" || event.key === " ")) {
      event.preventDefault();
      setFilter(node.dataset.filter, node.dataset.value, true);
    }
  });

  svg.addEventListener("click", (event) => {
    if (event.target.closest("#flow-gate")) {
      if (gatePinned) {
        closeGatePopover();
      } else {
        openGatePopover(true);
      }
      return;
    }
    const node = event.target.closest("[data-filter]");
    if (node) {
      setFilter(node.dataset.filter, node.dataset.value, true);
    }
  });

  gate.addEventListener("mouseenter", () => openGatePopover(false));
  gate.addEventListener("mouseleave", scheduleGateHide);
  gate.addEventListener("focus", () => openGatePopover(false));
  gate.addEventListener("blur", (event) => {
    if (!gatePopover.contains(event.relatedTarget)) {
      scheduleGateHide();
    }
  });
  gatePopover.addEventListener("mouseenter", () => window.clearTimeout(gateHideTimer));
  gatePopover.addEventListener("mouseleave", scheduleGateHide);
  gatePopoverClose.addEventListener("click", () => closeGatePopover(true));
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !gatePopover.hidden) {
      closeGatePopover(gate.contains(document.activeElement) || gatePopover.contains(document.activeElement));
    }
  });
  document.addEventListener("click", (event) => {
    if (gatePinned && !gatePopover.contains(event.target) && !gate.contains(event.target)) {
      closeGatePopover();
    }
  });
  window.addEventListener("resize", () => {
    if (!gatePopover.hidden) {
      positionGatePopover();
    }
  });

  new MutationObserver(resumeNow).observe(panel, { attributes: true, attributeFilter: ["hidden"] });
  document.addEventListener("visibilitychange", resumeNow);

  poll();
})();
