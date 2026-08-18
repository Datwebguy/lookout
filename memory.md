# Memory — Lookout (durable facts; keep in context always)

> These are stable truths for the build. If something here is ever contradicted by a real API response, trust the real response and update this file.

## The golden rule
Real intelligence, no theater. Every number and decision the demo shows must come from a **real FortyGuard call** + **real LLM reasoning**. Change the location or worker profile → output must really change. Never hardcode/mock/fake a temperature. On failure, **fail loudly** — never silently substitute fake data. Curated real-world reference data (e.g. actual Phoenix cooling centers) is allowed if genuinely real and labeled as a curated set.

## What we're building
**Lookout** — an autonomous AI agent that monitors each outdoor worker's exact site with FortyGuard's hyperlocal temperature data and acts *before* danger hits (alerts + pre-scheduled breaks), without being asked. Track 06 (Agentic AI). Autonomy is the point; a prompt-and-answer chatbot does NOT satisfy the track.

## Verified FortyGuard facts (from the official Quickstart repo + live calls 2026-08-18)
- **Base URL:** `https://api.fortyguard.com` (dev: `https://tos-enterprise-api.dev.app.fortyguard.com`).
- **Auth:** `api-key: <key>` header + `Content-Type: application/json`. No Bearer/OAuth.
- **Async:** submit → `activity_id` → poll `GET /v1/status/{id}` until `Completed`. The official `fortyguard` client does this in one call and returns `{"activity_id", "result"}`. **Build on the client.**
- **Coverage:** US only (non-US fails/empty). **Units:** Celsius everywhere — **confirmed live** (real sample: 39.85 °C in Phoenix in August, physically consistent; ignore `fortyguard/client.py`'s docstring, which incorrectly claims tcm tiles are °F — the live response overrides the shipped client's own comment). **History:** 2021–present, but "present" is unreliable for the most recent ~1-2 calendar days (see Gotchas — this is wider and less predictable than a simple fixed lag).
- **Polygon:** `[longitude, latitude]`, closed ring (first == last). Area caps (Basic 10 mi²; Premium more). Hackathon keys are Premium — all endpoints unlocked.
- **A worksite is smaller than a tile** (min granularity 60 m). Use an **area-weighted mean over overlapping tiles**, never nearest-tile.
- **There's a real minimum query-area threshold, confirmed live: ~1.5–2 km per side.** Submitting a small worksite polygon (200 m up to 1.5 km per side) directly as the query AOI returns **zero tiles**, even on dates otherwise 100% reliable — confirmed by testing the same small polygon against two separately-proven-reliable dates. A ~2 km box works consistently. **Always submit a bounding query AOI sized above this threshold (built around the site's centroid), then area-weight the returned tiles against the real, smaller site polygon** — implemented in `lookout/signals.py` (`_bounding_query_aoi`). This was the actual root cause of what first looked like an API outage.
- **`filter_type`:** 1 hour · 2 hour-range · 3 whole-day · 4 date-range (≤31 days).
- **`analytic_type`** (needs filter_type 2 or 4): `tcm` (snapshot °C) · `time_of_measure` · `exceedance` (**COUNT OF HOURS** past threshold, NOT degree-hours) · `persistence` (longest continuous run). exceedance/persistence need `threshold` (°C, default 30) + `direction` (above/below).
- **Reading tiles — confirmed live:** tcm tile `properties` = `{"tile_id", "average_temperature", "min_temperature", "max_temperature"}` (°C). `stats_data` for a tcm call carries `temperature_stats` (`minimum`/`maximum`/`mean`/`standard_deviation`) plus distribution arrays — not flat fields directly on `stats_data`. Analysis types (`exceedance`/`persistence`/`time_of_measure`) → `properties.value` (units in `stats_data.units`). **`properties.temperature` DOES NOT EXIST.**
- **`granularity`:** 60 / 80 / 100 m (smaller = finer + more credits). Use 100 while testing.
- **Credits:** deducted only on `Completed`; failed tasks free. Balance via `client.fetch_api_key_usage()`.
- **Endpoints:** `/v1/heatmap`, `/v1/env_params`, `/v1/satellite`(P), `/v1/streetview`(P), `/v1/heat_intelligence`(P), `/v1/status/{id}`, `/v1/system/fetch-api-key-usage`.

## Gotchas (these will bite if forgotten)
- **FORECAST RESULT (verified live 2026-08-18): NO live forecast.** Queried `create_heatmap` (tcm, filter_type=1) for TODAY's date at both a past hour (10:00, already elapsed) and a future hour (18:00, not yet elapsed) — **both returned `n_cells: 0` / empty `map_data.features`**, identically. Lookout's proactive/forward layer uses **historical analog** (same hour/week, prior years) exclusively — do not attempt a live intraday forecast against this endpoint, it will always come back empty for today's date.
- **"Yesterday" is NOT reliably available either — confirmed live, this changed within one session.** A specific date (2026-08-17) returned full real data (367 tiles) twice early in a session; retried later with the identical query and got zero tiles 3x in a row, while dates 3+ days old (and a 2024 date) stayed consistently available throughout the same session. **Treat only dates ≥3 days old as reliable** (`lookout.signals.most_recent_available_date()` encodes this). Don't assume a fixed "N days behind = safe" rule without margin — the boundary moved during actual testing.
- **`env_params` heat index is misleading:** anchors one temp across 24h, varies only humidity → artificially peaks ~2 a.m.; also coarse (nearby sites can be identical). Use `apparent_temperature_celsius` for feels-like; use heatmap layers to tell sites apart.
- **At site scale, peak temp is nearly flat — DURATION separates danger.** Lead reasoning with exceedance/persistence hours, not peak.
- **Don't trust the shipped client's own source comments blindly either.** `fortyguard/client.py`'s docstring says tcm tiles are in °F — a real live call proved this wrong (values are Celsius). A real API response outranks even the official client's inline documentation.

## Design decisions (locked)
- Primary user = outdoor worker; buyer = city/employer. Demo city = **Phoenix, AZ** (e.g. 33.4484, -112.0740).
- Language = Python; LLM = Claude via Anthropic API with tool-use.
- Reason over: now (tcm) · ahead (historical analog — forecast confirmed unavailable) · baseline · duration (exceedance) · worker profile.
- Tracks: primary Agentic (06); secondary Cities (01), Government (04).

## Security
- API key **server-side only** — never in frontend, repo, or demo network traffic (disqualification risk). `.env` git-ignored (confirmed on repo clone).
- A **leaked key** exists in the hackathon Slack channel — ignore it; generate your own (done, live key in `.env`, not committed).

## Demo definition of done
Judge changes coordinate or worker profile → output really changes from a real call. Money shot: weather-app single number vs. Lookout's per-block, per-worker, autonomous decision with a break already scheduled.
