// Landing page. Two jobs only: reveal sections on scroll, and show one real recent
// decision in the hero preview frame (read only, no controls, no mocked data).

function wireScrollReveal() {
  const targets = document.querySelectorAll(".reveal");
  if (!targets.length) return;
  if (!("IntersectionObserver" in window)) {
    targets.forEach((el) => el.classList.add("is-visible"));
    return;
  }
  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      }
    },
    { threshold: 0.15 }
  );
  targets.forEach((el) => observer.observe(el));
}

async function loadHeroPreview() {
  const body = document.getElementById("hero-preview-body");
  if (!body) return;
  try {
    const resp = await fetch("/api/decisions?limit=1");
    if (!resp.ok) throw new Error(`${resp.status} ${resp.statusText}`);
    const decisions = await resp.json();
    body.innerHTML = "";
    if (!decisions.length) {
      body.innerHTML = '<p class="empty-state">No real decisions logged yet. Open the dashboard to run the first one.</p>';
      return;
    }
    const d = decisions[0];
    const badge = document.createElement("span");
    badge.className = `risk-badge risk-${d.risk_level || "moderate"}`;
    badge.textContent = (d.risk_level || "unknown").toUpperCase();
    const site = document.createElement("p");
    site.className = "preview-site";
    site.textContent = d.site_name;
    const role = document.createElement("p");
    role.className = "preview-role";
    role.textContent = d.worker_role;
    const action = document.createElement("p");
    action.className = "preview-action";
    action.textContent = d.recommended_action;
    body.append(badge, site, role, action);
  } catch (err) {
    body.innerHTML = `<p class="error-state">Could not load a live decision: ${err.message}</p>`;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  wireScrollReveal();
  loadHeroPreview();
});
