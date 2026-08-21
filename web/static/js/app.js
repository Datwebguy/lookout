// Lookout dashboard. Fetches only real data from the backend. Nothing here is mocked:
// every number rendered on this page came from a real FortyGuard or OpenAI call logged
// by the Python agent.

const RISK_CLASS = {
  low: "risk-low",
  moderate: "risk-moderate",
  high: "risk-high",
  extreme: "risk-extreme",
};

function riskBadge(riskLevel) {
  const cls = RISK_CLASS[riskLevel] || "risk-moderate";
  const span = document.createElement("span");
  span.className = `risk-badge ${cls}`;
  span.textContent = riskLevel ? riskLevel.toUpperCase() : "UNKNOWN";
  return span;
}

function extractNowReading(decision) {
  const inputs = decision.real_inputs || [];
  const temps = inputs.filter((i) => i.tool === "get_current_temperature" && i.result && i.result.celsius != null);
  if (temps.length) return temps[temps.length - 1].result.celsius;
  const forward = inputs.find((i) => i.tool === "get_forward_and_baseline" && i.result && i.result.actual_now_celsius != null);
  return forward ? forward.result.actual_now_celsius : null;
}

function timeAgo(isoString) {
  if (!isoString) return "";
  const then = new Date(isoString).getTime();
  const diffMs = Date.now() - then;
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

async function fetchJSON(url, options) {
  const resp = await fetch(url, options);
  if (!resp.ok) {
    const text = await resp.text().catch(() => "");
    throw new Error(`${resp.status} ${resp.statusText}${text ? `: ${text}` : ""}`);
  }
  return resp.json();
}

function latestDecisionPerSite(decisions) {
  const map = new Map();
  for (const d of decisions) {
    if (!map.has(d.site_id)) map.set(d.site_id, d);
  }
  return map;
}

function renderMoneyShot(decisions) {
  const container = document.getElementById("money-shot-cards");
  container.innerHTML = "";
  const latest = latestDecisionPerSite(decisions);
  if (latest.size === 0) {
    container.innerHTML = '<p class="empty-state">No decisions yet. Run a live check to see real per site results.</p>';
    return;
  }
  for (const d of latest.values()) {
    const card = document.createElement("div");
    card.className = "money-card";
    const temp = extractNowReading(d);
    card.appendChild(riskBadge(d.risk_level));
    const tempEl = document.createElement("p");
    tempEl.className = "money-card-temp";
    tempEl.textContent = temp != null ? `${temp.toFixed(1)}°C` : "No reading";
    const siteEl = document.createElement("p");
    siteEl.className = "money-card-site";
    siteEl.textContent = d.site_name;
    const roleEl = document.createElement("p");
    roleEl.className = "money-card-role";
    roleEl.textContent = d.worker_role;
    const actionEl = document.createElement("p");
    actionEl.className = "money-card-action";
    actionEl.textContent = d.recommended_action;
    card.append(tempEl, siteEl, roleEl, actionEl);
    container.appendChild(card);
  }
}

function renderSiteGrid(sites, decisions) {
  const grid = document.getElementById("site-grid");
  grid.innerHTML = "";
  const latest = latestDecisionPerSite(decisions);
  for (const site of sites) {
    const card = document.createElement("article");
    card.className = "site-card";
    const head = document.createElement("div");
    head.className = "site-card-head";
    const h4 = document.createElement("h4");
    h4.textContent = site.name;
    head.appendChild(h4);
    const decision = latest.get(site.id);
    if (decision) head.appendChild(riskBadge(decision.risk_level));
    const role = document.createElement("p");
    role.className = "site-card-role";
    role.textContent = `${site.worker_profile.role} · ${site.worker_profile.shift_hours}`;
    card.append(head, role);

    if (site.worker_profile.risk_flags && site.worker_profile.risk_flags.length) {
      const flags = document.createElement("div");
      flags.className = "site-card-flags";
      for (const flag of site.worker_profile.risk_flags) {
        const pill = document.createElement("span");
        pill.className = "flag-pill";
        pill.textContent = flag;
        flags.appendChild(pill);
      }
      card.appendChild(flags);
    }

    const action = document.createElement("p");
    if (decision) {
      action.className = "site-card-action";
      action.textContent = decision.recommended_action;
    } else {
      action.className = "site-card-empty";
      action.textContent = "No decision yet for this site.";
    }
    card.appendChild(action);
    grid.appendChild(card);
  }
}

function renderFeed(decisions) {
  const feed = document.getElementById("decision-feed");
  feed.innerHTML = "";
  if (!decisions.length) {
    feed.innerHTML = '<p class="empty-state">No decisions yet.</p>';
    return;
  }
  for (const d of decisions.slice(0, 20)) {
    const item = document.createElement("article");
    item.className = "feed-item";

    const head = document.createElement("div");
    head.className = "feed-item-head";
    const left = document.createElement("div");
    const siteSpan = document.createElement("span");
    siteSpan.className = "feed-item-site";
    siteSpan.textContent = `${d.site_name}, ${d.worker_role}`;
    left.appendChild(siteSpan);
    const time = document.createElement("span");
    time.className = "feed-item-time";
    time.textContent = timeAgo(d.logged_at);
    head.append(left, riskBadge(d.risk_level), time);

    const action = document.createElement("p");
    action.className = "feed-item-action";
    action.textContent = d.recommended_action;

    const details = document.createElement("details");
    const summary = document.createElement("summary");
    summary.textContent = "Why: real inputs and rationale";
    const rationale = document.createElement("p");
    rationale.className = "rationale";
    rationale.textContent = d.rationale;
    details.append(summary, rationale);

    item.append(head, action, details);
    feed.appendChild(item);
  }
}

function setUpdating(isUpdating) {
  for (const id of ["money-shot-cards", "site-grid", "decision-feed"]) {
    document.getElementById(id).classList.toggle("is-updating", isUpdating);
  }
}

async function loadAll() {
  const statusEl = document.getElementById("run-status");
  try {
    const [sites, decisions] = await Promise.all([
      fetchJSON("/api/sites"),
      fetchJSON("/api/decisions?limit=50"),
    ]);
    renderMoneyShot(decisions);
    renderSiteGrid(sites, decisions);
    renderFeed(decisions);
  } catch (err) {
    statusEl.hidden = false;
    statusEl.className = "run-status is-error";
    statusEl.textContent = `Could not load data: ${err.message}`;
  }
}

function wireRunButton() {
  const btn = document.getElementById("run-now-btn");
  const statusEl = document.getElementById("run-status");
  let timerHandle = null;

  btn.addEventListener("click", async () => {
    btn.disabled = true;
    setUpdating(true);
    statusEl.hidden = false;
    statusEl.className = "run-status";
    const startedAt = Date.now();
    const updateElapsed = () => {
      const secs = Math.round((Date.now() - startedAt) / 1000);
      statusEl.innerHTML = "";
      const spinner = document.createElement("span");
      spinner.className = "spinner";
      spinner.setAttribute("aria-hidden", "true");
      const text = document.createElement("span");
      text.textContent = `Checking every site right now. This can take a minute or two. ${secs}s elapsed.`;
      statusEl.append(spinner, text);
    };
    updateElapsed();
    timerHandle = setInterval(updateElapsed, 1000);

    try {
      const data = await fetchJSON("/api/run", { method: "POST" });
      clearInterval(timerHandle);
      const failed = data.results.filter((r) => r.error);
      if (failed.length) {
        statusEl.className = "run-status is-error";
        statusEl.textContent = `Finished with ${failed.length} error(s). ${failed.map((f) => `${f.site_name}: ${f.error}`).join(" ")}`;
      } else {
        statusEl.className = "run-status is-success";
        statusEl.textContent = `Done. ${data.results.length} new real decision(s) below.`;
      }
      await loadAll();
    } catch (err) {
      clearInterval(timerHandle);
      statusEl.className = "run-status is-error";
      statusEl.textContent = `The live check failed: ${err.message}`;
    } finally {
      setUpdating(false);
      btn.disabled = false;
    }
  });
}

function wireAddSiteForm() {
  const form = document.getElementById("add-site-form");
  if (!form) return;
  const statusEl = document.getElementById("add-site-status");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = new FormData(form);
    const riskFlagsRaw = (data.get("risk_flags") || "").toString().trim();

    const payload = {
      name: (data.get("name") || "").toString().trim(),
      lat: parseFloat(data.get("lat")),
      lon: parseFloat(data.get("lon")),
      worker_profile: {
        role: (data.get("role") || "").toString().trim(),
        shift_hours: (data.get("shift_hours") || "").toString().trim(),
        risk_flags: riskFlagsRaw ? riskFlagsRaw.split(",").map((s) => s.trim()).filter(Boolean) : [],
        notes: (data.get("notes") || "").toString().trim(),
      },
      slack_webhook_url: (data.get("slack_webhook_url") || "").toString().trim() || null,
      discord_webhook_url: (data.get("discord_webhook_url") || "").toString().trim() || null,
    };

    if (!payload.name || Number.isNaN(payload.lat) || Number.isNaN(payload.lon) || !payload.worker_profile.role || !payload.worker_profile.shift_hours) {
      statusEl.className = "form-status is-error";
      statusEl.textContent = "Fill in site name, latitude, longitude, role, and shift hours.";
      return;
    }
    if (!payload.slack_webhook_url && !payload.discord_webhook_url) {
      statusEl.className = "form-status is-error";
      statusEl.textContent = "Add a Slack or Discord webhook so your alerts have their own channel.";
      return;
    }

    const submitBtn = form.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    statusEl.className = "form-status";
    statusEl.textContent = "Registering the site.";

    try {
      await fetchJSON("/api/sites", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      statusEl.className = "form-status is-success";
      statusEl.textContent = "Site registered. It will get its first decision on the next live check.";
      form.reset();
      await loadAll();
    } catch (err) {
      statusEl.className = "form-status is-error";
      statusEl.textContent = `Could not register the site: ${err.message}`;
    } finally {
      submitBtn.disabled = false;
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  loadAll();
  wireRunButton();
  wireAddSiteForm();
});
