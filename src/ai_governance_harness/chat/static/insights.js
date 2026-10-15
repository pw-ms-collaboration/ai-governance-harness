"use strict";

(() => {
  const button = document.querySelector("#refresh-insights");
  const range = document.querySelector("#insights-range");
  const status = document.querySelector("#insights-status");
  const badge = document.querySelector("#insights-state");
  const data = document.querySelector("#insights-data");
  const outcomes = [
    { key: "allow", label: "Policy allowed", color: "#087f8c", dash: "" },
    { key: "deny", label: "Policy denied", color: "#b42318", dash: "6 3" },
    { key: "require_approval", label: "Approval required", color: "#845400", dash: "2 3" },
  ];

  function element(tag, text, className = "") {
    const node = document.createElement(tag);
    node.textContent = text;
    node.className = className;
    return node;
  }

  function svgElement(tag, attributes) {
    const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (const [name, value] of Object.entries(attributes)) node.setAttribute(name, String(value));
    return node;
  }

  function renderVisuals(metrics, spans) {
    const decisions = metrics.filter((row) => row.name === "governance.policy.decision.count");
    const totals = Object.fromEntries(outcomes.map(({ key }) => [
      key, decisions.filter((row) => row.outcome === key).reduce((sum, row) => sum + (row.total || 0), 0),
    ]));
    const total = Object.values(totals).reduce((sum, value) => sum + value, 0);
    const kpis = document.querySelector("#insights-kpis");
    kpis.replaceChildren();
    for (const item of [{ key: "total", label: "Total evaluations" }, ...outcomes]) {
      const card = element("div", "", `outcome-${item.key}`);
      card.append(element("dt", item.label), element("dd",
        decisions.length ? (item.key === "total" ? total : totals[item.key]) : "No data"));
      kpis.append(card);
    }
    const distribution = document.querySelector("#insights-distribution");
    distribution.replaceChildren();
    for (const item of outcomes) {
      const percentage = total > 0 ? 100 * totals[item.key] / total : 0;
      const row = element("div", "", "distribution-row");
      const track = element("div", "", "distribution-track");
      const fill = element("div", "", `distribution-fill outcome-${item.key}`);
      fill.style.width = `${percentage}%`;
      track.append(fill);
      row.append(element("span", item.label), element("strong",
        decisions.length ? `${totals[item.key]} (${percentage.toFixed(1)}%)` : "No data"), track);
      distribution.append(row);
    }
    document.querySelector("#insights-distribution-note").textContent = total > 0
      ? "Counts combine exported chat and MCP policy evaluations, not unique user requests."
      : "No recorded policy evaluations in this window. Check activity and ingestion delay.";

    const buckets = new Map();
    for (const row of decisions) {
      if (!row.timestamp || !outcomes.some((item) => item.key === row.outcome)) continue;
      if (!buckets.has(row.timestamp)) buckets.set(row.timestamp, { timestamp: row.timestamp });
      const bucket = buckets.get(row.timestamp);
      bucket[row.outcome] = (bucket[row.outcome] || 0) + (row.total || 0);
    }
    const timeline = [...buckets.values()].sort((a, b) => Date.parse(a.timestamp) - Date.parse(b.timestamp));
    table("#insights-trend-values", timeline, (row) => [
      displayTime(row.timestamp), ...outcomes.map((item) => row[item.key] ?? "No data"),
    ], 4);
    const trend = document.querySelector("#insights-trend");
    trend.replaceChildren();
    if (!timeline.length) {
      trend.append(element("p", "No timeline data in this window."));
    } else {
      const svg = svgElement("svg", { viewBox: "0 0 640 240", role: "img", "aria-label": "Policy decision counts by time. Values are in the table below." });
      const max = Math.max(1, ...timeline.flatMap((row) => outcomes.map((item) => row[item.key] || 0)));
      const start = Date.parse(timeline[0].timestamp);
      const end = Date.parse(timeline.at(-1).timestamp);
      const x = (row) => end === start ? 330 : 50 + 560 * (Date.parse(row.timestamp) - start) / (end - start);
      for (const fraction of [0, 0.5, 1]) {
        const y = 200 - fraction * 170;
        svg.append(svgElement("line", { x1: 50, x2: 610, y1: y, y2: y, stroke: "#c5cede" }));
        const label = svgElement("text", { x: 42, y: y + 5, "text-anchor": "end", fill: "#526078", "font-size": 13 });
        label.textContent = String(Math.round(max * fraction));
        svg.append(label);
      }
      const legend = element("div", "", "chart-legend");
      for (const item of outcomes) {
        const points = timeline.filter((row) => row[item.key] !== undefined);
        // Isolated markers avoid implying continuous coverage through ingestion gaps.
        for (const row of points) {
          const dot = svgElement(item.key === "deny" ? "rect" : "circle", item.key === "deny"
            ? { x: x(row) - 4, y: 200 - 170 * row[item.key] / max - 4, width: 8, height: 8, fill: item.color }
            : { cx: x(row), cy: 200 - 170 * row[item.key] / max, r: item.key === "allow" ? 4 : 6, fill: item.key === "allow" ? item.color : "white", stroke: item.color, "stroke-width": 2 });
          const title = svgElement("title", {});
          title.textContent = `${displayTime(row.timestamp)}: ${item.label} ${row[item.key]}`;
          dot.append(title);
          svg.append(dot);
        }
        legend.append(element("span", `${item.key === "deny" ? "■" : item.key === "allow" ? "●" : "○"} ${item.label}`, `legend-${item.key}`));
      }
      for (const [row, position, anchor] of [[timeline[0], 50, "start"], [timeline.at(-1), 610, "end"]]) {
        const label = svgElement("text", { x: position, y: 226, "text-anchor": anchor, fill: "#526078", "font-size": 12 });
        label.textContent = new Date(row.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
        svg.append(label);
      }
      trend.append(svg, legend);
    }
    policySpans = spans.filter((row) => row.name === "evaluate.governance.policy")
      .sort((a, b) => Date.parse(b.timestamp) - Date.parse(a.timestamp));
  }

  let policySpans = [];
  const policyFilter = document.querySelector("#policy-feed-filter");
  const policyService = document.querySelector("#policy-feed-service");

  function renderPolicyLog() {
    const outcome = policyFilter.value;
    const rows = policySpans.filter((row) =>
      (outcome === "all" || (outcome === "blocked" ? row.outcome === "deny" || row.outcome === "require_approval" : row.outcome === outcome))
      && (policyService.value === "all" || row.service === policyService.value)).slice(0, 50);
    const blocked = policySpans.filter((row) => row.outcome === "deny" || row.outcome === "require_approval").length;
    document.querySelector("#policy-feed-count").textContent = policySpans.length
      ? `${policySpans.length} retained · ${blocked} blocked` : "No data";
    const runs = new Set(policySpans.length ? spansWithAgent() : []);
    const body = document.querySelector("#insights-policy-feed");
    body.replaceChildren();
    if (!rows.length) {
      const row = document.createElement("tr");
      const empty = element("td", policySpans.length ? "No decisions match this filter." : "No retained policy spans in this window.");
      empty.colSpan = 7;
      row.append(empty);
      body.append(row);
      return;
    }
    for (const span of rows) {
      const row = element("tr", "", `outcome-${span.outcome}`);
      const label = outcomes.find((item) => item.key === span.outcome)?.label || "Not recorded";
      const badge = element("span", label, `outcome-badge outcome-${span.outcome}`);
      const outcomeCell = document.createElement("td");
      outcomeCell.append(badge);
      const ruleCell = document.createElement("td");
      ruleCell.append(span.rule ? element("code", ruleLabel(span.rule)) : element("span", "Not recorded", "muted"));
      const runCell = document.createElement("td");
      if (span.operation_id && runs.has(span.operation_id)) {
        const link = element("button", `View run ${span.operation_id.slice(0, 8)}`, "policy-run-link");
        link.type = "button";
        link.dataset.operation = span.operation_id;
        runCell.append(link);
      } else {
        runCell.append(element("span", span.operation_id ? span.operation_id.slice(0, 8) : "None", "muted"));
      }
      row.append(
        element("td", new Date(span.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })),
        outcomeCell, ruleCell,
        element("td", span.stage ? stageLabel(span.stage) : "Not recorded", span.stage ? "stage-cell" : "muted"),
        element("td", span.service.replace("ai-governance-harness-", "")),
        element("td", span.duration_ms === null || span.duration_ms === undefined ? "Unknown" : span.duration_ms < 1 ? "< 1 ms" : formatDuration(span.duration_ms), "num"),
        runCell,
      );
      body.append(row);
    }
  }

  function spansWithAgent() {
    return genaiSpans.filter((row) => row.name.startsWith("invoke_agent ") && row.operation_id).map((row) => row.operation_id);
  }

  policyFilter.addEventListener("change", renderPolicyLog);
  policyService.addEventListener("change", renderPolicyLog);
  document.querySelector("#insights-policy-feed").addEventListener("click", (event) => {
    const link = event.target.closest("button[data-operation]");
    if (!link) return;
    selectRun(link.dataset.operation);
    document.querySelector("#genai-title").scrollIntoView({ behavior: "smooth", block: "start" });
    genaiRuns.querySelector(`button[data-operation="${link.dataset.operation}"]`)?.focus({ preventScroll: true });
  });

  function cell(row, value) {
    const element = document.createElement("td");
    element.textContent = value === null || value === undefined || value === "" ? "No data" : String(value);
    row.append(element);
  }

  function table(selector, rows, values, columns) {
    const body = document.querySelector(selector);
    body.replaceChildren();
    if (!rows.length) {
      const row = document.createElement("tr");
      const element = document.createElement("td");
      element.colSpan = columns;
      element.textContent = "No matching telemetry in this window. Check activity, export settings, or ingestion delay.";
      row.append(element);
      body.append(row);
      return;
    }
    for (const item of rows) {
      const row = document.createElement("tr");
      for (const value of values(item)) cell(row, value);
      body.append(row);
    }
  }

  function displayTime(value) {
    return value ? new Date(value).toLocaleString() : "No data";
  }

  const genaiLayers = [
    { key: "agent", label: "Agent", match: (name) => name.startsWith("invoke_agent ") },
    { key: "inference", label: "Model inference", match: (name) => name.startsWith("chat ") },
    { key: "tool", label: "Tool", match: (name) => name.startsWith("execute_tool ") },
    { key: "mcp", label: "MCP", match: (name) => /^(MCP send |tools\/call |mcp\.tool\.|http\.server\.request$)/.test(name) },
    { key: "policy", label: "Policy", match: (name) => name === "evaluate.governance.policy" },
    { key: "guardrail", label: "Guardrail", match: (name) => name.startsWith("apply_guardrail ") },
    { key: "approval", label: "Human approval", match: (name) => name === "governance.human_approval" },
  ];
  const approvalOutcomes = [
    { key: "requested", label: "Approval requested" },
    { key: "approved", label: "Approved by human" },
    { key: "declined", label: "Declined by human" },
    { key: "cancelled", label: "Approval cancelled" },
    { key: "not_approved", label: "Not approved" },
  ];
  const approvalLabel = (outcome) => approvalOutcomes.find((item) => item.key === outcome)?.label || "Human approval";
  const guardrailOutcomes = [
    { key: "passed", label: "Passed" },
    { key: "triggered", label: "Triggered" },
    { key: "error", label: "Error" },
  ];
  const reasonLabel = (reason) => reason && reason !== "none" ? reason.replaceAll("_", " ") : "None";
  // The toolkit reports no rule when default_action applies; label it explicitly.
  const ruleLabel = (rule) => rule === "unmatched" ? "default deny (no rule matched)" : rule;
  const genaiRuns = document.querySelector("#genai-runs");
  const genaiShowPolicy = document.querySelector("#genai-show-policy");
  let genaiSpans = [];
  let genaiSelected = "";

  function genaiLayer(name) {
    return genaiLayers.find((layer) => layer.match(name));
  }

  function spanStart(row) {
    return Date.parse(row.timestamp);
  }

  function formatDuration(ms) {
    if (ms === null || ms === undefined) return "No data";
    if (ms >= 1000) return `${(ms / 1000).toFixed(2)} s`;
    return `${ms.toFixed(ms < 10 ? 1 : 0)} ms`;
  }

  function sumDuration(rows) {
    return rows.reduce((sum, row) => sum + (row.duration_ms || 0), 0);
  }

  function policyCounts(rows) {
    return Object.fromEntries(outcomes.map(({ key }) => [key, rows.filter((row) => row.outcome === key).length]));
  }

  function runSpans(operationId) {
    return genaiSpans.filter((row) => row.operation_id === operationId)
      .sort((a, b) => spanStart(a) - spanStart(b));
  }

  function renderGenai(metrics, spans) {
    genaiSpans = spans.filter((row) => row.timestamp && genaiLayer(row.name));
    const count = (prefix) => spans.filter((row) => row.name.startsWith(prefix)).length;
    const tokens = (name) => {
      const rows = metrics.filter((row) => row.name === name);
      return rows.length ? rows.reduce((sum, row) => sum + (row.total || 0), 0).toLocaleString() : "No data";
    };
    const inference = spans.filter((row) => row.name.startsWith("chat ") && row.duration_ms !== null);
    const kpis = document.querySelector("#genai-kpis");
    kpis.replaceChildren();
    for (const [label, value, note, tone] of [
      ["Agent runs", count("invoke_agent "), "agent"],
      ["Model calls", count("chat "), "inference"],
      ["Tool calls", count("execute_tool "), "tool"],
      ["Input tokens", tokens("gen_ai.client.inference.usage.input_tokens"), "tokens"],
      ["Output tokens", tokens("gen_ai.client.inference.usage.output_tokens"), "tokens"],
      ["Mean model latency", inference.length ? formatDuration(sumDuration(inference) / inference.length) : "No data", "inference"],
      ["Human approvals", ...approvalSummary(metrics), "approval"],
    ].map((entry) => entry.length === 3 ? [entry[0], entry[1], "", entry[2]] : entry)) {
      const card = element("div", "", `kpi-${tone}`);
      card.append(element("dt", label), element("dd", String(value)));
      if (note) card.append(element("dd", note, "kpi-note"));
      kpis.append(card);
    }

    const runs = genaiSpans.filter((row) => row.name.startsWith("invoke_agent ") && row.operation_id)
      .sort((a, b) => spanStart(b) - spanStart(a)).slice(0, 15);
    genaiRuns.replaceChildren();
    if (!runs.length) genaiRuns.append(element("li", "No agent runs retained in this window."));
    for (const run of runs) {
      const related = runSpans(run.operation_id);
      const tools = [...new Set(related.filter((row) => row.name.startsWith("execute_tool "))
        .map((row) => row.name.slice("execute_tool ".length)))];
      const policies = policyCounts(related.filter((row) => genaiLayer(row.name).key === "policy"));
      const failed = related.some((row) => row.outcome === "failure");
      const approval = related.filter((row) => genaiLayer(row.name).key === "approval").at(-1);
      const status = failed ? "error" : policies.deny ? "deny" : policies.require_approval || approval ? "approval" : "ok";
      const statusLabel = failed ? "Error" : policies.deny ? "Policy denied" : approval ? approvalLabel(approval.outcome) : policies.require_approval ? "Approval required" : "Completed";
      const button = element("button", "", `genai-run status-${status}`);
      button.type = "button";
      button.dataset.operation = run.operation_id;
      button.setAttribute("aria-label", `${displayTime(run.timestamp)}, ${statusLabel}, ${formatDuration(run.duration_ms)}, tools: ${tools.join(", ") || "none"}`);
      const toolList = element("span", "", "run-tools");
      if (tools.length) for (const tool of tools) toolList.append(element("span", tool));
      else toolList.append(element("span", "No tools", "no-tools"));
      const modelCalls = related.filter((row) => row.name.startsWith("chat ")).length;
      const policyTotal = Object.values(policies).reduce((sum, value) => sum + value, 0);
      const fired = related.filter((row) => row.name.startsWith("apply_guardrail ") && row.outcome === "triggered").length;
      button.append(
        element("span", "", "run-status"),
        element("span", new Date(run.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }), "run-time"),
        element("span", formatDuration(run.duration_ms), "run-duration"),
        toolList,
        element("span", `${statusLabel} · ${modelCalls} model call${modelCalls === 1 ? "" : "s"} · ${policyTotal} policy check${policyTotal === 1 ? "" : "s"}${fired ? ` · ${fired} guardrail${fired === 1 ? "" : "s"} fired` : ""}`, "run-meta"),
      );
      const item = document.createElement("li");
      item.append(button);
      genaiRuns.append(item);
    }
    selectRun(runs.some((run) => run.operation_id === genaiSelected) ? genaiSelected : runs[0]?.operation_id);
  }

  function approvalSummary(metrics) {
    const rows = metrics.filter((row) => row.name === "governance.human_approval.count");
    if (!rows.length) return ["No data", ""];
    const total = (key) => rows.filter((row) => row.outcome === key).reduce((sum, row) => sum + (row.total || 0), 0);
    const declined = total("declined") + total("cancelled") + total("not_approved");
    return [`${total("approved")} approved`, `${declined} declined · ${total("requested")} requested`];
  }

  function selectRun(operationId) {
    genaiSelected = operationId || "";
    for (const button of genaiRuns.querySelectorAll("button[data-operation]")) {
      button.setAttribute("aria-pressed", String(button.dataset.operation === genaiSelected));
    }
    renderWaterfall(genaiSelected);
  }

  function renderSummary(all, runMs) {
    const summary = document.querySelector("#genai-run-summary");
    summary.replaceChildren();
    const model = sumDuration(all.filter((row) => row.name.startsWith("chat ")));
    const tool = sumDuration(all.filter((row) => row.name.startsWith("execute_tool ")));
    const segments = [
      { label: "Model inference", value: model, color: "var(--g-inference)" },
      { label: "Tools and MCP", value: tool, color: "var(--g-tool)" },
      { label: "Agent overhead", value: Math.max(0, runMs - model - tool), color: "var(--g-agent)" },
    ];
    const bar = element("div", "", "genai-breakdown");
    bar.setAttribute("aria-hidden", "true");
    const legend = element("dl", "", "genai-breakdown-legend");
    legend.setAttribute("aria-label", "Where the run time went");
    segments.forEach((segment, index) => {
      const share = runMs > 0 ? 100 * segment.value / runMs : 0;
      const part = element("span", "");
      part.style.width = `${Math.min(100, share)}%`;
      part.style.background = segment.color;
      part.style.animationDelay = `${index * 150}ms`;
      part.title = `${segment.label}: ${formatDuration(segment.value)}`;
      bar.append(part);
      const entry = element("div", "");
      entry.style.setProperty("--swatch", segment.color);
      entry.append(element("dt", segment.label), element("dd", `${formatDuration(segment.value)} (${share.toFixed(0)}%)`));
      legend.append(entry);
    });
    const facts = element("div", "", "genai-run-facts");
    const policies = policyCounts(all.filter((row) => genaiLayer(row.name).key === "policy"));
    for (const outcome of outcomes) {
      if (policies[outcome.key]) facts.append(element("span", `${policies[outcome.key]} ${outcome.label.toLowerCase()}`, `fact outcome-${outcome.key}`));
    }
    const guardrails = all.filter((row) => genaiLayer(row.name).key === "guardrail");
    const fired = guardrails.filter((row) => row.outcome === "triggered" || row.outcome === "error").length;
    if (guardrails.length) {
      facts.append(element("span", `${guardrails.length} guardrail${guardrails.length === 1 ? "" : "s"} · ${fired} fired`, `fact${fired ? " outcome-deny" : ""}`));
    }
    const operation = element("span", "Operation ");
    operation.append(element("code", all[0].operation_id));
    const usage = runTokens(all);
    if (usage.calls) {
      facts.append(element("span", `${(usage.input + usage.output).toLocaleString()} tokens · ${formatCost(usage.cost)}`, "fact"));
    }
    facts.append(element("span", `Total ${formatDuration(runMs)}`, "fact"), operation);
    summary.append(bar, legend, facts);
  }

  function renderWaterfall(operationId) {
    const waterfall = document.querySelector("#genai-waterfall");
    waterfall.replaceChildren();
    document.querySelector("#genai-run-summary").replaceChildren();
    if (!operationId) {
      waterfall.append(element("p", "No GenAI agent runs retained in this window. Send a chat message, wait for Azure ingestion (2–5 minutes), then reload."));
      return;
    }
    const all = runSpans(operationId);
    const byId = new Map(all.filter((row) => row.span_id).map((row) => [row.span_id, row]));
    const start = Math.min(...all.map(spanStart));
    const end = Math.max(...all.map((row) => spanStart(row) + (row.duration_ms || 0)));
    const total = Math.max(1, end - start);
    const agent = all.find((row) => row.name.startsWith("invoke_agent "));
    renderSummary(all, agent?.duration_ms ?? total);

    const showPolicy = genaiShowPolicy.checked;
    // Passed guardrails are summarised in the run facts; keep only fired ones unless checks are expanded.
    const isRoutineCheck = (row) => {
      const key = genaiLayer(row.name).key;
      return key === "policy" || (key === "guardrail" && row.outcome === "passed");
    };
    const rows = showPolicy ? all : all.filter((row) => !isRoutineCheck(row));
    const visible = new Set(rows);
    // Hidden policy checks render as markers on their nearest visible ancestor.
    const markers = new Map();
    if (!showPolicy) {
      for (const row of all.filter((item) => genaiLayer(item.name).key === "policy")) {
        let host = byId.get(row.parent_id);
        const seen = new Set();
        while (host && !visible.has(host) && !seen.has(host)) {
          seen.add(host);
          host = byId.get(host.parent_id);
        }
        host = host && visible.has(host) ? host : agent || rows[0];
        if (!host) continue;
        if (!markers.has(host)) markers.set(host, []);
        markers.get(host).push(row);
      }
    }
    const depth = (row) => {
      let level = 0;
      const seen = new Set();
      for (let parent = byId.get(row.parent_id); parent && !seen.has(parent); parent = byId.get(parent.parent_id)) {
        seen.add(parent);
        level += 1;
      }
      return level;
    };
    const position = (time) => `${100 * (time - start) / total}%`;

    const axis = element("div", "", "genai-row genai-axis");
    axis.setAttribute("aria-hidden", "true");
    const ticks = element("div", "", "genai-track");
    for (const fraction of [0, 0.25, 0.5, 0.75, 1]) {
      const tick = element("span", fraction ? formatDuration(total * fraction) : "0");
      tick.style.left = `${fraction * 100}%`;
      ticks.append(tick);
    }
    axis.append(element("span", "Span"), ticks, element("span", "Duration", "span-duration"));
    const list = element("div", "");
    list.style.display = "contents";
    list.setAttribute("role", "list");
    list.setAttribute("aria-label", `Spans for operation ${operationId}, ${formatDuration(total)}`);
    waterfall.append(axis, list);

    rows.forEach((row, index) => {
      const layer = genaiLayer(row.name);
      const item = element("div", "", "genai-row");
      item.setAttribute("role", "listitem");
      const name = element("span", "", "span-name");
      name.style.paddingLeft = `${Math.min(depth(row), 6) * 0.9}rem`;
      const title = element("span", row.name, `span-title layer-${layer.key}`);
      title.title = row.name;
      const meta = element("span", "", "span-meta");
      meta.append(element("span", row.service.replace("ai-governance-harness-", ""), "service-pill"), element("span", layer.label));
      if (row.outcome === "failure") meta.append(element("span", "Error", "error"));
      if (layer.key === "policy") {
        const outcome = outcomes.find((item) => item.key === row.outcome);
        if (outcome) meta.append(element("span", outcome.label, `outcome-${outcome.key}`));
      }
      if (layer.key === "approval") meta.append(element("span", approvalLabel(row.outcome), `approval-${row.outcome}`));
      if (layer.key === "guardrail" && row.outcome !== "passed") {
        const outcome = guardrailOutcomes.find((item) => item.key === row.outcome);
        if (outcome) meta.append(element("span", `${outcome.label}${row.rule && row.rule !== "none" ? `: ${reasonLabel(row.rule)}` : ""}`, row.outcome === "error" ? "outcome-require_approval" : "outcome-deny"));
      }
      const hosted = markers.get(row) || [];
      const counts = policyCounts(hosted);
      for (const outcome of outcomes) {
        if (counts[outcome.key]) meta.append(element("span", `${counts[outcome.key]} ${outcome.label.toLowerCase()}`, `outcome-${outcome.key}`));
      }
      name.append(title, meta);

      const track = element("div", "", "genai-track");
      track.setAttribute("aria-hidden", "true");
      const flagged = ["failure", "deny", "triggered", "error"].includes(row.outcome);
      const bar = element("div", "", `genai-bar layer-${layer.key}${flagged ? " failure" : ""}`);
      bar.style.left = position(spanStart(row));
      bar.style.width = `${100 * (row.duration_ms || 0) / total}%`;
      bar.style.animationDelay = `${index * 50}ms`;
      bar.title = `${row.name}: ${formatDuration(row.duration_ms)}`;
      track.append(bar);
      for (const policy of hosted) {
        const marker = element("span", "", `policy-marker outcome-${policy.outcome}`);
        marker.style.left = position(spanStart(policy));
        marker.style.animationDelay = `${300 + index * 50}ms`;
        marker.title = `${outcomes.find((item) => item.key === policy.outcome)?.label || "Policy check"} · ${policy.service.replace("ai-governance-harness-", "")}`;
        track.append(marker);
      }
      item.append(name, track, element("span", formatDuration(row.duration_ms), "span-duration"));
      list.append(item);
    });
  }

  genaiRuns.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-operation]");
    if (button) selectRun(button.dataset.operation);
  });
  genaiShowPolicy.addEventListener("change", () => renderWaterfall(genaiSelected));

  const stageOrder = ["agent_startup", "input", "pre_model", "post_model", "pre_tool", "post_tool", "output", "agent_shutdown"];
  const stageLabel = (stage) => stage ? stage.replaceAll("_", " ") : "unknown";

  function relativeTime(value) {
    const minutes = Math.round((Date.now() - Date.parse(value)) / 60000);
    if (!Number.isFinite(minutes)) return "unknown";
    if (minutes < 1) return "just now";
    if (minutes < 60) return `${minutes} min ago`;
    return `${Math.round(minutes / 60)} h ago`;
  }

  function renderHotspots(rules) {
    const byRule = new Map();
    const byStage = new Map();
    for (const row of rules) {
      const total = row.total || 0;
      const entry = byRule.get(row.name) || { name: row.name, policy: row.policy, stages: new Set(), services: new Set(), allow: 0, deny: 0, require_approval: 0, last: "" };
      entry[row.outcome] += total;
      if (row.stage) entry.stages.add(row.stage);
      entry.services.add(row.service.replace("ai-governance-harness-", ""));
      if (row.outcome !== "allow" && (!entry.last || Date.parse(row.timestamp) > Date.parse(entry.last))) entry.last = row.timestamp;
      byRule.set(row.name, entry);
      const stage = byStage.get(row.stage) || { allow: 0, deny: 0, require_approval: 0 };
      stage[row.outcome] += total;
      byStage.set(row.stage, stage);
    }
    const blocking = [...byRule.values()].map((rule) => ({ ...rule, blocked: rule.deny + rule.require_approval }))
      .filter((rule) => rule.blocked > 0).sort((a, b) => b.blocked - a.blocked || a.name.localeCompare(b.name));
    const totalBlocked = blocking.reduce((sum, rule) => sum + rule.blocked, 0);
    const totalAll = [...byRule.values()].reduce((sum, rule) => sum + rule.allow + rule.deny + rule.require_approval, 0);
    const worstStage = [...byStage.entries()].map(([stage, counts]) => [stage, counts.deny + counts.require_approval])
      .filter(([, count]) => count > 0).sort((a, b) => b[1] - a[1])[0];

    const kpis = document.querySelector("#hotspot-kpis");
    kpis.replaceChildren();
    const hasData = rules.length > 0;
    for (const [label, value, tone] of [
      ["Blocked decisions", hasData ? totalBlocked.toLocaleString() : "No data", "deny"],
      ["Block rate", totalAll ? `${(100 * totalBlocked / totalAll).toFixed(1)}%` : "No data", "deny"],
      ["Rules that blocked", hasData ? blocking.length : "No data", "approval"],
      ["Top rule share", totalBlocked ? `${Math.round(100 * blocking[0].blocked / totalBlocked)}%` : "No data", "approval"],
      ["Hottest stage", worstStage ? stageLabel(worstStage[0]) : "None", "mcp"],
      ["Rules evaluated", hasData ? byRule.size : "No data", "allow"],
    ]) {
      const card = element("div", "", `kpi-${tone}`);
      card.append(element("dt", label), element("dd", String(value)));
      kpis.append(card);
    }

    const list = document.querySelector("#hotspot-rules");
    list.replaceChildren();
    if (!hasData) {
      list.append(element("li", "No rule-level data in this window yet. Rule names are exported from now on; send a chat and allow 2 to 5 minutes for Azure ingestion.", "hotspot-empty"));
    } else if (!blocking.length) {
      list.append(element("li", "No denials or approval holds in this window. Every evaluated rule allowed execution.", "hotspot-empty"));
    }
    const max = blocking[0]?.blocked || 1;
    blocking.slice(0, 8).forEach((rule, index) => {
      const item = element("li", "", `hotspot-rule${index === 0 ? " top" : ""}`);
      item.style.setProperty("--delay", `${index * 70}ms`);
      const head = element("div", "", "hotspot-rule-head");
      head.append(element("span", `#${index + 1}`, "hotspot-rank"), element("code", ruleLabel(rule.name)),
        element("strong", rule.blocked.toLocaleString(), "hotspot-count"));
      const bar = element("div", "", "hotspot-bar");
      bar.setAttribute("aria-hidden", "true");
      for (const key of ["deny", "require_approval"]) {
        if (!rule[key]) continue;
        const fill = element("span", "", `hotspot-fill outcome-${key}`);
        fill.style.width = `${100 * rule[key] / max}%`;
        bar.append(fill);
      }
      const meta = element("div", "", "hotspot-meta");
      if (rule.deny) meta.append(element("span", `${rule.deny} denied`, "pill outcome-deny"));
      if (rule.require_approval) meta.append(element("span", `${rule.require_approval} approval`, "pill outcome-require_approval"));
      for (const stage of rule.stages) meta.append(element("span", stageLabel(stage), "pill stage"));
      meta.append(element("span", `${[...rule.services].join(" + ")} · ${rule.policy || "policy unknown"} · last ${relativeTime(rule.last)}`, "hotspot-source"));
      item.append(head, bar, meta);
      list.append(item);
    });

    const body = document.querySelector("#hotspot-stage-rows");
    body.replaceChildren();
    const stages = [...byStage.keys()].sort((a, b) => (stageOrder.indexOf(a) + 1 || 99) - (stageOrder.indexOf(b) + 1 || 99));
    const peak = Math.max(1, ...[...byStage.values()].flatMap((counts) => Object.values(counts)));
    if (!stages.length) {
      const row = document.createElement("tr");
      const empty = element("td", "No rule-level data in this window.");
      empty.colSpan = 4;
      row.append(empty);
      body.append(row);
    }
    for (const stage of stages) {
      const counts = byStage.get(stage);
      const row = document.createElement("tr");
      row.append(element("th", stageLabel(stage)));
      row.firstChild.scope = "row";
      for (const key of ["allow", "deny", "require_approval"]) {
        const value = counts[key];
        const td = element("td", value ? value.toLocaleString() : "0", `heat outcome-${key}${value ? "" : " zero"}`);
        td.style.setProperty("--heat", value ? (0.15 + 0.4 * value / peak).toFixed(2) : "0");
        row.append(td);
      }
      body.append(row);
    }
  }

  let pricing = null;

  function tokenCost(input, output, cached = 0) {
    if (!pricing) return null;
    const uncached = Math.max(0, input - cached);
    return (uncached * pricing.input_per_million + cached * pricing.cached_input_per_million
      + output * pricing.output_per_million) / 1e6;
  }

  function formatCost(value) {
    if (value === null || value === undefined) return "No price set";
    const digits = value > 0 && value < 1 ? 4 : 2;
    return new Intl.NumberFormat(undefined, {
      style: "currency", currency: pricing.currency, minimumFractionDigits: digits, maximumFractionDigits: digits,
    }).format(value);
  }

  function runTokens(spans) {
    const calls = spans.filter((row) => row.name.startsWith("chat ") && row.input_tokens !== null && row.input_tokens !== undefined);
    const sum = (key) => calls.reduce((total, row) => total + (row[key] || 0), 0);
    const reasoningKnown = calls.some((row) => row.reasoning_tokens !== null && row.reasoning_tokens !== undefined);
    const totals = { calls: calls.length, input: sum("input_tokens"), output: sum("output_tokens"), cached: sum("cached_tokens"), reasoning: reasoningKnown ? sum("reasoning_tokens") : null };
    totals.cost = tokenCost(totals.input, totals.output, totals.cached);
    return totals;
  }

  function renderTokenomics(usage) {
    const sum = (name) => usage.filter((row) => row.name === name).reduce((total, row) => total + (row.total || 0), 0);
    const inputName = "gen_ai.client.inference.usage.input_tokens";
    const outputName = "gen_ai.client.inference.usage.output_tokens";
    const input = sum(inputName);
    const output = sum(outputName);
    const calls = usage.filter((row) => row.name === inputName).reduce((total, row) => total + (row.samples || 0), 0);
    const windowCost = tokenCost(input, output);
    const runs = [...new Set(spansWithAgent())].map((operationId) => ({ operationId, run: genaiSpans.find((row) => row.operation_id === operationId && row.name.startsWith("invoke_agent ")), ...runTokens(runSpans(operationId)) }))
      .filter((run) => run.calls > 0);
    const retained = runTokens(genaiSpans);
    const hasData = usage.length > 0;
    const reasoningShare = retained.reasoning !== null && retained.output > 0
      ? ` · ${Math.round(100 * retained.reasoning / retained.output)}% reasoning` : "";
    const meanRunCost = runs.length ? runs.reduce((total, run) => total + (run.cost || 0), 0) / runs.length : null;
    const kpis = document.querySelector("#token-kpis");
    kpis.replaceChildren();
    for (const [label, value, tone, note] of [
      ["Total tokens", hasData ? (input + output).toLocaleString() : "No data", "tokens", ""],
      ["Input tokens", hasData ? input.toLocaleString() : "No data", "inference", ""],
      ["Output tokens", hasData ? output.toLocaleString() : "No data", "agent", reasoningShare.slice(3)],
      ["Estimated cost", hasData ? formatCost(windowCost) : "No data", "cost", "Whole window"],
      ["Mean cost per agent run", meanRunCost === null ? "No data" : formatCost(meanRunCost), "cost", runs.length ? `${runs.length} retained run${runs.length === 1 ? "" : "s"}` : ""],
      ["Mean tokens per model call", calls ? Math.round((input + output) / calls).toLocaleString() : "No data", "tool", calls ? `${calls} call${calls === 1 ? "" : "s"}` : ""],
    ]) {
      const card = element("div", "", `kpi-${tone}`);
      card.append(element("dt", label), element("dd", String(value)));
      if (note) card.append(element("dd", note, "kpi-note"));
      kpis.append(card);
    }

    const buckets = new Map();
    for (const row of usage) {
      if (!row.timestamp) continue;
      const bucket = buckets.get(row.timestamp) || { timestamp: row.timestamp, input: 0, output: 0 };
      bucket[row.name === inputName ? "input" : "output"] += row.total || 0;
      buckets.set(row.timestamp, bucket);
    }
    const timeline = [...buckets.values()].sort((a, b) => Date.parse(a.timestamp) - Date.parse(b.timestamp));
    const trend = document.querySelector("#token-trend");
    trend.replaceChildren();
    if (!timeline.length) {
      trend.append(element("p", "No token usage recorded in this window.", "muted"));
    } else {
      const peak = Math.max(1, ...timeline.map((row) => row.input + row.output));
      const svg = svgElement("svg", { viewBox: "0 0 640 220", role: "img", "aria-label": `Tokens per time bucket. ${input.toLocaleString()} input and ${output.toLocaleString()} output tokens in total.` });
      const defs = svgElement("defs", {});
      const pattern = svgElement("pattern", { id: "token-output-hatch", width: 6, height: 6, patternUnits: "userSpaceOnUse", patternTransform: "rotate(45)" });
      pattern.append(svgElement("rect", { width: 6, height: 6, fill: "#0f2f66" }), svgElement("line", { x1: 0, y1: 0, x2: 0, y2: 6, stroke: "#ffffff", "stroke-width": 2 }));
      defs.append(pattern);
      svg.append(defs);
      for (const fraction of [0, 0.5, 1]) {
        const y = 190 - fraction * 165;
        svg.append(svgElement("line", { x1: 56, x2: 630, y1: y, y2: y, stroke: "#d5dce8" }));
        const label = svgElement("text", { x: 50, y: y + 4, "text-anchor": "end", fill: "#526078", "font-size": 12 });
        label.textContent = Math.round(peak * fraction).toLocaleString();
        svg.append(label);
      }
      const slot = 574 / timeline.length;
      const width = Math.max(4, Math.min(48, slot * 0.7));
      timeline.forEach((row, index) => {
        const x = 56 + slot * index + (slot - width) / 2;
        const inputHeight = 165 * row.input / peak;
        const outputHeight = 165 * row.output / peak;
        const group = svgElement("g", { class: "token-bar" });
        group.style.animationDelay = `${index * 40}ms`;
        group.append(
          svgElement("rect", { x, y: 190 - inputHeight, width, height: inputHeight, fill: "#4a7fd4", rx: 2 }),
          svgElement("rect", { x, y: 190 - inputHeight - outputHeight, width, height: outputHeight, fill: "url(#token-output-hatch)", rx: 2 }),
        );
        const title = svgElement("title", {});
        title.textContent = `${displayTime(row.timestamp)}: ${row.input.toLocaleString()} input, ${row.output.toLocaleString()} output, about ${formatCost(tokenCost(row.input, row.output))}`;
        group.append(title);
        svg.append(group);
      });
      for (const [row, position, anchor] of [[timeline[0], 56, "start"], [timeline.at(-1), 630, "end"]]) {
        const label = svgElement("text", { x: position, y: 212, "text-anchor": anchor, fill: "#526078", "font-size": 12 });
        label.textContent = new Date(row.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
        svg.append(label);
      }
      const legend = element("div", "", "chart-legend token-legend");
      legend.append(element("span", "■ Input tokens", "legend-input"), element("span", "▨ Output tokens (hatched)", "legend-output"));
      trend.append(svg, legend);
    }

    const split = document.querySelector("#token-split");
    split.replaceChildren();
    if (!hasData || !pricing || !windowCost) {
      split.append(element("p", hasData ? "Set token prices to estimate cost." : "No token usage recorded in this window.", "muted"));
    } else {
      const segments = [
        { label: "Input tokens", value: tokenCost(input, 0), color: "var(--g-inference)" },
        { label: "Output tokens", value: tokenCost(0, output), color: "var(--g-agent)" },
      ];
      const bar = element("div", "", "genai-breakdown");
      bar.setAttribute("aria-hidden", "true");
      const legend = element("dl", "", "genai-breakdown-legend");
      legend.setAttribute("aria-label", "Estimated cost by token type");
      segments.forEach((segment, index) => {
        const share = 100 * segment.value / windowCost;
        const part = element("span", "");
        part.style.width = `${share}%`;
        part.style.background = segment.color;
        part.style.animationDelay = `${index * 150}ms`;
        bar.append(part);
        const entry = element("div", "");
        entry.style.setProperty("--swatch", segment.color);
        entry.append(element("dt", segment.label), element("dd", `${formatCost(segment.value)} (${share.toFixed(0)}%)`));
        legend.append(entry);
      });
      split.append(bar, legend);
    }

    const body = document.querySelector("#token-runs");
    body.replaceChildren();
    const ranked = runs.sort((a, b) => (b.cost || 0) - (a.cost || 0) || b.input + b.output - a.input - a.output).slice(0, 10);
    if (!ranked.length) {
      const row = document.createElement("tr");
      const empty = element("td", "No retained agent runs with token usage in this window.");
      empty.colSpan = 7;
      row.append(empty);
      body.append(row);
    }
    for (const run of ranked) {
      const row = document.createElement("tr");
      const runCell = document.createElement("td");
      const link = element("button", `View run ${run.operationId.slice(0, 8)}`, "policy-run-link");
      link.type = "button";
      link.dataset.operation = run.operationId;
      runCell.append(link);
      row.append(
        element("td", run.run?.timestamp ? new Date(run.run.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }) : "Unknown"),
        element("td", String(run.calls), "num"),
        element("td", run.input.toLocaleString(), "num"),
        element("td", run.output.toLocaleString(), "num"),
        element("td", run.reasoning === null ? "Not recorded" : run.reasoning.toLocaleString(), run.reasoning === null ? "muted" : "num"),
        element("td", formatCost(run.cost), "num"),
        runCell,
      );
      body.append(row);
    }

    document.querySelector("#token-pricing-note").textContent = pricing
      ? `Estimated at ${pricing.currency} ${pricing.input_per_million} input, ${pricing.cached_input_per_million} cached input and ${pricing.output_per_million} output per 1M tokens for ${pricing.model}. These are list prices, not your bill; set GENAI_PRICE_* to your contracted rates. Window totals come from exported token metrics; per-run rows come from retained traces and apply the cached-input rate.`
      : "No token prices are configured, so cost is not estimated.";
  }

  document.querySelector("#token-runs").addEventListener("click", (event) => {
    const link = event.target.closest("button[data-operation]");
    if (!link) return;
    selectRun(link.dataset.operation);
    document.querySelector("#genai-title").scrollIntoView({ behavior: "smooth", block: "start" });
    genaiRuns.querySelector(`button[data-operation="${link.dataset.operation}"]`)?.focus({ preventScroll: true });
  });

  function render(rows) {
    const metrics = rows.filter((row) => row.kind === "metric");
    renderVisuals(metrics, rows.filter((row) => row.kind === "span"));
    renderHotspots(rows.filter((row) => row.kind === "rule"));
    renderGenai(metrics, rows.filter((row) => row.kind === "span"));
    renderPolicyLog();
    renderTokenomics(rows.filter((row) => row.kind === "usage"));
    const services = ["ai-governance-harness-chat", "ai-governance-harness-mcp"];
    table("#insights-metrics", services, (service) => {
      const sum = (name, outcome = "") => {
        const matches = metrics.filter((row) =>
          row.service === service && row.name === name && row.outcome === outcome);
        return matches.length ? matches.reduce((value, row) => value + (row.total || 0), 0) : null;
      };
      // Histograms export aggregate sums and counts, not individual evaluations.
      const durations = metrics.filter((row) =>
        row.service === service && row.name === "governance.policy.evaluation.duration");
      const samples = durations.reduce((sum, row) => sum + (row.samples || 0), 0);
      const total = durations.reduce((sum, row) => sum + (row.total || 0), 0);
      return [
        service,
        sum("governance.policy.decision.count", "allow"),
        sum("governance.policy.decision.count", "deny"),
        sum("governance.policy.decision.count", "require_approval"),
        samples > 0 ? `${(1000 * total / samples).toFixed(3)} ms` : null,
        sum("mcp.tool.call.count"),
        sum("gen_ai.client.inference.usage.input_tokens"),
        sum("gen_ai.client.inference.usage.output_tokens"),
      ];
    }, 8);
    table("#insights-spans", rows.filter((row) => row.kind === "span"), (row) => [
      displayTime(row.timestamp), row.service, row.name,
      row.duration_ms === null ? null : `${row.duration_ms.toFixed(3)} ms`,
      row.outcome, row.operation_id, row.span_id, row.parent_id,
    ], 8);
    table("#insights-logs", rows.filter((row) => row.kind === "log"), (row) => [
      displayTime(row.timestamp), row.service, row.name, row.outcome, row.operation_id,
    ], 5);
  }

  async function load() {
    button.disabled = true;
    range.disabled = true;
    data.hidden = true;
    badge.className = "status-badge neutral";
    badge.textContent = "Loading";
    status.textContent = "Querying Azure metadata. This may take up to 30 seconds.";
    try {
      const response = await fetch(`/api/observability/history?hours=${range.value}`, {
        headers: { Accept: "application/json" },
        signal: AbortSignal.timeout(35000),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "Azure history is unavailable.");
      if (!Array.isArray(payload.rows)) throw new Error("Invalid history response.");
      pricing = payload.pricing && typeof payload.pricing === "object" ? payload.pricing : null;
      render(payload.rows);
      data.hidden = false;
      badge.className = "status-badge ready";
      badge.textContent = payload.rows.length ? "History received" : "No data";
      status.textContent = `Last ${payload.hours} hour(s). Fetched ${displayTime(payload.fetched_at)}. ${payload.cached ? "Cached result (up to 60 seconds)." : "Fresh Azure query."} `;
    } catch (error) {
      badge.className = "status-badge unavailable";
      badge.textContent = "Unavailable";
      status.textContent = error.name === "TimeoutError"
        ? "Azure history timed out. Retry later."
        : error.message || "Azure history could not be reached.";
    } finally {
      button.disabled = false;
      range.disabled = false;
    }
  }

  button.addEventListener("click", load);
  range.addEventListener("change", load);
})();
