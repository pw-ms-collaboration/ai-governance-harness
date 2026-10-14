(() => {
  "use strict";

  const SVG_NS = "http://www.w3.org/2000/svg";
  const POLL_MS = 2000;
  const TRAVEL_MS = 1800;
  const STAGGER_MS = 320;
  const MAX_IN_FLIGHT = 24;
  const MAX_TICKER = 25;
  const MAX_CATCH_UP = 12;

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
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

  const OUTCOMES = {
    allow: { label: "Policy allowed", decisions: ["allow"] },
    deny: { label: "Policy denied", decisions: ["deny"] },
    approval: { label: "Approval required", decisions: ["require_approval"] },
    other: { label: "Warn / log / other", decisions: ["warn", "log", "transform", "escalate"] },
  };

  const seen = new Set();
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
      addTickerRow(event, outcome, true);
    }
  }

  function animate(event, replay = false) {
    const outcome = outcomeFor(event.decision);
    const source = ["mcp", "gateway"].includes(event.source) ? event.source : "chat";
    if (reducedMotion.matches || inFlight >= MAX_IN_FLIGHT) {
      arrive(event, outcome, replay);
      return;
    }

    const inbound = document.querySelector(`#flow-in-${source}`);
    const outbound = document.querySelector(`#flow-out-${outcome}`);
    const inLength = inbound.getTotalLength();
    const outLength = outbound.getTotalLength();
    const particle = createShape(outcome);
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

  function addTickerRow(event, outcome, isNew) {
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
    ticker.prepend(row);
    while (ticker.children.length > MAX_TICKER) {
      ticker.lastElementChild.remove();
    }
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
      events.slice(-8).forEach((event) => addTickerRow(event, outcomeFor(event.decision), false));
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
    const recent = latestEvents.slice(-MAX_CATCH_UP);
    if (recent.length === 0) {
      announcer.textContent = "No recent decisions to replay.";
      return;
    }
    announcer.textContent = `Replaying ${recent.length} recent decisions.`;
    play(recent, true);
  });

  new MutationObserver(resumeNow).observe(panel, { attributes: true, attributeFilter: ["hidden"] });
  document.addEventListener("visibilitychange", resumeNow);

  poll();
})();
