// Lookout dashboard. Real data only, scoped by user Google identity / workspace session.

const RISK_CLASS = {
  low: "risk-low",
  moderate: "risk-moderate",
  high: "risk-high",
  extreme: "risk-extreme",
};

function getActiveUserId() {
  const googleUser = localStorage.getItem("lookout_google_user");
  if (googleUser) {
    try {
      const parsed = JSON.parse(googleUser);
      if (parsed && parsed.user_id) return parsed.user_id;
    } catch (e) {
      // ignore invalid json
    }
  }
  let localId = localStorage.getItem("lookout_workspace_id");
  if (!localId) {
    localId = "ws_" + Math.random().toString(36).substring(2, 11);
    localStorage.setItem("lookout_workspace_id", localId);
  }
  return localId;
}

function getActiveUserObj() {
  const googleUser = localStorage.getItem("lookout_google_user");
  if (googleUser) {
    try {
      return JSON.parse(googleUser);
    } catch (e) {}
  }
  return null;
}

function riskBadge(riskLevel) {
  const cls = RISK_CLASS[riskLevel] || "risk-moderate";
  const span = document.createElement("span");
  span.className = `risk-badge ${cls}`;
  span.textContent = riskLevel ? riskLevel.toUpperCase() : "UNKNOWN";
  return span;
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

function renderSiteGrid(sites, decisions) {
  const grid = document.getElementById("site-grid");
  grid.innerHTML = "";
  if (!sites.length) {
    grid.innerHTML = `
      <div class="empty-sites" style="grid-column: 1 / -1;">
        <p><strong>No registered outdoor sites in your workspace yet.</strong></p>
        <p style="font-size: 0.9em; margin-top: 6px; color: var(--text-muted);">Click "Add a site" above to register your first worksite and configure heat safety webhooks.</p>
      </div>
    `;
    return;
  }
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
    feed.innerHTML = '<p class="empty-state">No autonomous decisions recorded for your workspace yet.</p>';
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
    summary.textContent = "Why: operational inputs & rationale";
    const rationale = document.createElement("p");
    rationale.className = "rationale";
    rationale.textContent = d.rationale;
    details.append(summary, rationale);

    item.append(head, action, details);
    feed.appendChild(item);
  }
}

function setUpdating(isUpdating) {
  for (const id of ["site-grid", "decision-feed"]) {
    const el = document.getElementById(id);
    if (el) el.classList.toggle("is-updating", isUpdating);
  }
}

async function loadAll() {
  const statusEl = document.getElementById("run-status");
  const userId = getActiveUserId();
  try {
    const [sites, decisions] = await Promise.all([
      fetchJSON(`/api/sites?user_id=${encodeURIComponent(userId)}`),
      fetchJSON(`/api/decisions?user_id=${encodeURIComponent(userId)}&limit=50`),
    ]);
    renderSiteGrid(sites, decisions);
    renderFeed(decisions);
  } catch (err) {
    statusEl.hidden = false;
    statusEl.className = "run-status is-error";
    statusEl.textContent = `Could not load workspace data: ${err.message}`;
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
      text.textContent = `Running heat safety check across your workspace sites. ${secs}s elapsed.`;
      statusEl.append(spinner, text);
    };
    updateElapsed();
    timerHandle = setInterval(updateElapsed, 1000);

    try {
      const userId = getActiveUserId();
      const data = await fetchJSON(`/api/run?user_id=${encodeURIComponent(userId)}`, { method: "POST" });
      clearInterval(timerHandle);
      const failed = data.results.filter((r) => r.error);
      if (failed.length) {
        statusEl.className = "run-status is-error";
        statusEl.textContent = `Finished with ${failed.length} error(s). ${failed.map((f) => `${f.site_name}: ${f.error}`).join(" ")}`;
      } else {
        statusEl.className = "run-status is-success";
        statusEl.textContent = `Done. ${data.results.length} site(s) checked.`;
      }
      await loadAll();
    } catch (err) {
      clearInterval(timerHandle);
      statusEl.className = "run-status is-error";
      statusEl.textContent = `The safety check failed: ${err.message}`;
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
    const userId = getActiveUserId();

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
      workspace_id: userId,
    };

    if (Number.isNaN(payload.lat) || Number.isNaN(payload.lon)) {
      statusEl.className = "form-status is-error";
      statusEl.textContent = "Find your address first, using the Find button.";
      return;
    }
    if (!payload.name || !payload.worker_profile.role || !payload.worker_profile.shift_hours) {
      statusEl.className = "form-status is-error";
      statusEl.textContent = "Fill in site name, role, and shift hours.";
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
    statusEl.textContent = "Registering your site.";

    try {
      await fetchJSON("/api/sites", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      statusEl.className = "form-status is-success";
      statusEl.textContent = "Site registered successfully. Safety checks will execute on your active schedule.";
      form.reset();
      document.getElementById("location-result").textContent = "";
      document.getElementById("location-result").className = "location-result";
      await loadAll();
    } catch (err) {
      statusEl.className = "form-status is-error";
      statusEl.textContent = `Could not register the site: ${err.message}`;
    } finally {
      submitBtn.disabled = false;
    }
  });
}

function wireFindLocation() {
  const addressInput = document.getElementById("site-address");
  const findBtn = document.getElementById("find-location-btn");
  const resultEl = document.getElementById("location-result");
  const latInput = document.getElementById("site-lat");
  const lonInput = document.getElementById("site-lon");
  if (!addressInput || !findBtn) return;

  function invalidate() {
    latInput.value = "";
    lonInput.value = "";
    resultEl.textContent = "";
    resultEl.className = "location-result";
  }

  addressInput.addEventListener("input", invalidate);

  findBtn.addEventListener("click", async () => {
    const query = addressInput.value.trim();
    if (!query) {
      resultEl.className = "location-result is-error";
      resultEl.textContent = "Type an address first.";
      return;
    }
    findBtn.disabled = true;
    resultEl.className = "location-result";
    resultEl.textContent = "Looking up address.";
    try {
      const result = await fetchJSON(`/api/geocode?q=${encodeURIComponent(query)}`);
      latInput.value = result.lat;
      lonInput.value = result.lon;
      resultEl.className = "location-result is-found";
      resultEl.textContent = `Found: ${result.display_name}`;
    } catch (err) {
      invalidate();
      resultEl.className = "location-result is-error";
      resultEl.textContent = `Could not find address: ${err.message}`;
    } finally {
      findBtn.disabled = false;
    }
  });
}

function setupGoogleAuthUI() {
  const userProfileEl = document.getElementById("user-profile");
  const gSignInEl = document.getElementById("g_id_signin");
  const signoutBtn = document.getElementById("signout-btn");
  const avatarImg = document.getElementById("user-avatar-img");
  const nameSpan = document.getElementById("user-name-span");

  const user = getActiveUserObj();
  if (user) {
    if (gSignInEl) gSignInEl.hidden = true;
    if (userProfileEl) userProfileEl.hidden = false;
    if (avatarImg) avatarImg.src = user.picture || "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ccircle cx='50' cy='50' r='50' fill='%230a2540'/%3E%3Ctext x='50%25' y='65%25' dominant-baseline='middle' text-anchor='middle' font-size='50' fill='white'%3E%F0%9F%90%A7%3C/text%3E%3C/svg%3E";
    if (nameSpan) nameSpan.textContent = user.name || user.email;
  } else {
    if (gSignInEl) gSignInEl.hidden = false;
    if (userProfileEl) userProfileEl.hidden = true;
  }

  if (signoutBtn) {
    signoutBtn.addEventListener("click", () => {
      localStorage.removeItem("lookout_google_user");
      localStorage.removeItem("lookout_workspace_id");
      window.location.reload();
    });
  }

  if (window.google && google.accounts && google.accounts.id) {
    google.accounts.id.initialize({
      client_id: "109827364512-lookout-auth.apps.googleusercontent.com",
      callback: async (response) => {
        try {
          const base64Url = response.credential.split(".")[1];
          const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
          const payload = JSON.parse(decodeURIComponent(atob(base64).split("").map((c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2)).join("")));
          
          const userObj = {
            user_id: payload.sub,
            email: payload.email,
            name: payload.name || payload.email,
            picture: payload.picture || "",
          };
          localStorage.setItem("lookout_google_user", JSON.stringify(userObj));
          setupGoogleAuthUI();
          await loadAll();
        } catch (e) {
          console.error("Google Auth verification failed:", e);
        }
      },
    });

    if (gSignInEl && !user) {
      google.accounts.id.renderButton(gSignInEl, {
        theme: "outline",
        size: "medium",
        shape: "pill",
        text: "signin_with",
      });
    }
  }
}

document.addEventListener("DOMContentLoaded", () => {
  setupGoogleAuthUI();
  loadAll();
  wireRunButton();
  wireAddSiteForm();
  wireFindLocation();
});
