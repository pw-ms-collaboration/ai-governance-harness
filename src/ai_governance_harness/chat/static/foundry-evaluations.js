"use strict";

(() => {
  const element = (id) => document.getElementById(`foundry-${id}`);
  const select = element("evaluation-select");
  let evalCursor = null;
  let runCursor = null;
  let busy = false;
  let jobActive = false;
  let starting = false;
  let jobTimer = null;
  let jobLoaded = false;

  function text(tag, value) {
    const node = document.createElement(tag);
    node.textContent = value ?? "Not supplied";
    return node;
  }

  function badge(value, outcome) {
    const node = text("span", value);
    node.className = `status-badge ${outcome}`;
    return node;
  }

  async function get(path, cursor = null) {
    const query = cursor ? `?after=${encodeURIComponent(cursor)}` : "";
    const response = await fetch(`/api/foundry/evaluations${path}${query}`);
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "Foundry results are unavailable.");
    return payload;
  }

  async function action(work) {
    if (busy) return;
    busy = true;
    element("error").hidden = true;
    element("status").textContent = "Loading Foundry results...";
    const buttons = [element("refresh"), element("more-evaluations"), element("more-runs")];
    buttons.forEach((button) => { button.disabled = true; });
    select.disabled = true;
    try {
      await work();
    } catch (error) {
      element("status").textContent = "Foundry results could not be loaded. Previously loaded data, if any, is unchanged.";
      element("error").textContent = error.message;
      element("error").hidden = false;
    } finally {
      busy = false;
      buttons.forEach((button) => { button.disabled = false; });
      select.disabled = select.options.length === 0;
    }
  }

  async function runs(append = false) {
    const data = await get(`/${encodeURIComponent(select.value)}/runs`, append ? runCursor : null);
    if (!append) element("runs").replaceChildren();
    for (const run of data.items) {
      const row = document.createElement("tr");
      const counts = run.counts || {};
      row.append(text("td", run.name || run.id));
      row.append(text("td", run.created_at ? new Date(run.created_at * 1000).toLocaleString() : null));
      const status = document.createElement("td");
      status.append(badge(
        (run.status || "unknown").replaceAll("_", " "),
        run.error || ["failed", "error", "cancelled"].includes(run.status) ? "error" : "neutral",
      ));
      if (run.error) status.append(text("p", run.error));
      row.append(status);
      const scored = run.status === "completed"
        && Number.isInteger(counts.passed) && Number.isInteger(counts.total)
        && counts.total > 0 && counts.passed >= 0 && counts.passed <= counts.total;
      row.append(text("td", scored
        ? `${Math.round(counts.passed / counts.total * 100)}% (${counts.passed} / ${counts.total})`
        : "Not available"));
      const results = document.createElement("td");
      results.className = "foundry-run-counts";
      for (const [label, value, outcome] of [
        ["passed", counts.passed, "passed"],
        ["failed", counts.failed, "failed"],
        ["errors", counts.errored, "error"],
      ]) results.append(badge(`${value ?? "?"} ${label}`, value > 0 ? outcome : "neutral"));
      results.append(text("span", `${counts.total ?? "?"} total cases`));
      row.append(results);
      const report = document.createElement("td");
      if (run.report_url) {
        const link = text("a", "Open in Foundry");
        link.href = run.report_url;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.setAttribute("aria-label", `Open ${run.name || run.id} in Foundry`);
        report.append(link);
      } else report.append(text("span", "Report unavailable"));
      row.append(report);
      element("runs").append(row);
    }
    runCursor = data.next;
    element("more-runs").hidden = !runCursor;
    element("status").textContent = element("runs").children.length ? "Foundry run history loaded." : "No Foundry runs exist for this evaluation yet.";
  }

  async function evaluations(append = false, preferredId = null) {
    const data = await get("", append ? evalCursor : null);
    const previous = preferredId || select.value;
    if (!append) select.replaceChildren();
    for (const evaluation of data.items) {
      const option = text("option", evaluation.name || evaluation.id);
      option.value = evaluation.id;
      select.append(option);
    }
    if ([...select.options].some((option) => option.value === previous)) select.value = previous;
    evalCursor = data.next;
    element("more-evaluations").hidden = !evalCursor;
    if (!append) {
      element("runs").replaceChildren();
      element("more-runs").hidden = true;
      if (select.options.length) await runs();
    }
    element("refresh").textContent = "Refresh Foundry results";
    if (!select.options.length) element("status").textContent = "No Foundry evaluation definitions exist yet. Registered evaluators are not evaluation runs.";
  }

  element("refresh").addEventListener("click", () => action(() => evaluations()));
  element("more-evaluations").addEventListener("click", () => action(() => evaluations(true)));
  element("more-runs").addEventListener("click", () => action(() => runs(true)));
  select.addEventListener("change", () => {
    element("runs").replaceChildren();
    element("more-runs").hidden = true;
    action(() => runs());
  });

  async function loadJob(id = null) {
    window.clearTimeout(jobTimer);
    try {
      const response = await fetch(`/api/foundry/evaluation-jobs${id ? `/${encodeURIComponent(id)}` : ""}`);
      const job = await response.json();
      if (!response.ok) throw new Error(job.error || "Evaluation job status is unavailable.");
      const wasActive = jobActive;
      const restoring = !jobLoaded;
      jobLoaded = true;
      jobActive = job?.status === "running";
      element("run").disabled = jobActive || starting;
      element("run").textContent = jobActive ? "Running Eval..." : "Run Eval";
      element("job-status").textContent = jobActive
        ? `Running agent scenarios and Foundry evaluation: ${job.run_id}`
        : job ? `Evaluation ${job.status}: ${job.run_id}` : "Ready to run the packaged agent evaluation.";
      if (job && ["error", "cancelled"].includes(job.status)) {
        element("job-error").textContent = job.error || "Evaluation did not complete. Check Foundry before retrying.";
        element("job-error").hidden = false;
      }
      if (jobActive) jobTimer = window.setTimeout(() => loadJob(job.run_id), 2000);
      else if ((wasActive || restoring) && job?.eval_id) {
        if (busy) jobTimer = window.setTimeout(() => action(() => evaluations(false, job.eval_id)), 1000);
        else await action(() => evaluations(false, job.eval_id));
      }
    } catch (error) {
      element("run").disabled = true;
      element("job-status").textContent = "Job status unavailable. Reload to reconnect before starting another evaluation.";
      element("job-error").textContent = error.message;
      element("job-error").hidden = false;
    }
  }

  element("run").addEventListener("click", async () => {
    if (jobActive || starting) return;
    if (!window.confirm("Run the enabled packaged agent scenarios and submit their public responses to Foundry for judging? Commented-out scenarios are skipped. This performs model inference and may incur charges.")) return;
    starting = true;
    element("run").disabled = true;
    element("run").textContent = "Starting Eval...";
    element("job-error").hidden = true;
    element("job-status").textContent = "Starting agent evaluation...";
    try {
      const response = await fetch("/api/foundry/evaluation-jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ confirm_inference: true, confirm_submit: true }),
      });
      const job = await response.json();
      if (!response.ok && response.status !== 409) throw new Error(job.error || "Evaluation could not be started.");
      starting = false;
      jobActive = true;
      await loadJob(job.run_id);
    } catch (error) {
      starting = false;
      await loadJob();
      element("job-error").textContent = error.message;
      element("job-error").hidden = false;
    }
  });
  loadJob();
})();
