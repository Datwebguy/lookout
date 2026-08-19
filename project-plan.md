# Project Plan — Lookout

**Sprint:** 18–30 Aug 2026 · **Submission:** 30 Aug, 11:59 PM GST
**Golden rule for every milestone:** it's "done" only when it runs on REAL FortyGuard data. No mocks, no theater.

## Phase 0 — Setup (before real coding)
- [x] Generate API key at dashboard.fortyguard.com → Profile → Create API Key. Confirm Premium + credits.
- [x] Create repo from the Quickstart template (github.com/Datwebguy/lookout).
- [x] `pip install -r requirements.txt`; copy `.env.example` → `.env`; paste key (git-ignored).
- [x] Real API round-trip confirmed wired up (see Milestone 1).
- [x] Add CLAUDE.md, prd.md, architecture.md, memory.md, handoff.md to repo root.

## Milestone 1 — Live API proof (foundation; nothing else until this is green) — ✅ DONE 2026-08-18
- [x] Using the official client, submit a small real Phoenix polygon (`create_heatmap`, `tcm`, `granularity=100`), print `resp["activity_id"]` and `resp["result"]["stats_data"]`.
- [x] Confirm `properties.average_temperature` is where the tile temp lives; confirm values change when you move the polygon (Polygon A: 367 tiles, mean 39.88 °C vs Polygon B ~4.6km east: 412 tiles, mean 39.85 °C).
- [x] **Verify forecasting:** empirically tested — today's date returns zero data at any hour (past or future); yesterday and older return full real data. **No live forecast; historical-analog is the confirmed forward mechanism.** Recorded in handoff.md + memory.md.

## Milestone 2 — Signals layer — ✅ DONE 2026-08-18
- [x] Area-weighted mean over the tiles a site polygon overlaps (don't nearest-tile). Real result: 40.03°C for a real ~200m×155m worksite.
- [x] Historical baseline ("normal for this site, this hour") from prior years. Real result: 40.12°C mean from real 2023/2024/2025 samples.
- [x] Forward signal: historical analog (climatology + persistence projection). Real result: 38.88°C projected for 18:00 today.
- [x] Duration read via `analytic_type=exceedance`/`persistence` over a multi-hour window (`filter_type` 2 or 4). Real result: 84.29h exceedance, 8.00h persistence over a real 7-day window.
- [x] **Bonus finding, fixed:** discovered and fixed a real minimum-query-area threshold (~2km) — signals layer now always submits a bounding query AOI and area-weights against the real (smaller) site polygon. See memory.md.

## Milestone 3 — Autonomous loop — ✅ DONE 2026-08-18
- [x] Registered-sites store (lat/lng + worker profile). `lookout/sites.py` + `lookout/data/sites.json` — 2 real Phoenix sites, distinct worker profiles.
- [x] Scheduler iterates sites on an interval and calls the signals layer per site — no human prompt triggers it. `lookout/scheduler.py` — `tick()` for one autonomous pass, `run_forever()` for real deployment. Real result: construction site 40.04°C vs delivery hub 39.81°C — genuinely different real readings per site in one autonomous pass.
- [x] Per-site caching (per hour) to respect credits. `lookout/cache.py` — confirmed live: tick 2 (same hour) served both sites from cache, zero new API calls.

## Milestone 4 — Decision policy (the reasoning; where we win) — ✅ DONE 2026-08-18
- [x] LLM tool-use: agent calls the FortyGuard client as a tool. `lookout/agent.py` — OpenAI `gpt-5.6-luna`, Responses API, real `get_current_temperature`/`get_forward_and_baseline`/`get_exceedance_duration` tools bound to `lookout/signals.py`.
- [x] Prompt + schema → `{risk_level, recommended_action, timing, rationale}`, personalized by worker profile. Structured output via `text.format` json_schema.
- [x] Prove the same site yields different actions for different profiles. Real result: same construction-site polygon, swapped worker profile (construction laborer vs. delivery driver with cardiac history) → both rated `risk_level: extreme` (correct — genuinely extreme heat for anyone), but `recommended_action`/`timing`/`rationale` differed substantively, each correctly citing the specific worker's real risk factors.

## Milestone 5 — Proactive action
- [ ] Detect an upcoming danger window (from historical-analog) and pre-schedule a break + emit an alert *now*.
- [ ] Log every autonomous decision with its real inputs.

## Milestone 6 — Alert channel
- [ ] Real notification out (webhook/email/SMS via a real provider). If not wired in time, a real visible alert log — never a faked "sent".

## Milestone 7 — Demo UI
- [ ] Live feed of autonomous decisions across sites.
- [ ] Per-worker view: real temp, forward curve, action + rationale.
- [ ] Build the "money shot": weather-app single number vs. Lookout's per-block, per-worker autonomous decision.

## Milestone 8 — Harden + rehearse
- [ ] Real end-to-end runs on Phoenix coordinates, repeatedly.
- [ ] Edge cases: API timeout; non-US coordinate (refuse cleanly); today's-date request (no data — handle gracefully, don't crash).
- [ ] Record a backup video of a real run. Rehearse < 3 min narration.

## Submission checklist (30 Aug)
- [ ] Live demo URL (no login, stays up through judging).
- [ ] Video (YouTube/Loom, ≤ 3 min).
- [ ] Code repo (if private, add **Hackathon-FG** as collaborator).
- [ ] Submission form: team name, members/emails, primary track = Agentic (06), secondary tags = Cities (01) + Government (04); disclose AI tools + external datasets used.
- [ ] Confirm key is NOT in the repo or frontend.
