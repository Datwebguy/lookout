# Architecture — Lookout

## 1. System overview
```
        ┌──────────────────────────────────┐
        │  Autonomous scheduler loop       │  runs on its own; no human prompt
        │  (iterates registered sites)     │
        └────────────────┬──────────────────┘
                         │ per site (lat/lng + worker profile)
                         ▼
   ┌───────────────┐   ┌───────────────────────┐   ┌───────────────────────┐
   │ FortyGuard     │──▶  Agent (LLM + tools)  │──▶│  Decision policy      │
   │ client (real)  │   │  calls client as tool │   │ {risk, action,        │
   │ submit + poll  │   │  reasons over inputs  │   │  timing, rationale}   │
   └───────────────┘   └───────────┬───────────┘   └──────────┬───────────┘
                                   │                          │
                                   ▼                          ▼
                         ┌───────────────┐          ┌───────────────────┐
                         │ Alert channel  │          │ Decision log       │
                         │ (real output)  │          │ (real inputs kept) │
                         └───────────────┘          └───────────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────────┐
                    │ Demo UI: live decision feed +    │
                    │ per-worker detail view           │
                    └──────────────────────────────────┘
```
**Key idea:** the LLM calls the FortyGuard client as a *tool*, so reasoning is genuine tool-use, not a hardcoded branch. The scheduler makes it autonomous.

## 2. Components
- **FortyGuard client layer** — thin wrapper over the official `fortyguard` Python client (from the Quickstart template). The ONLY place that talks to the API. Exposes: current temperature for a site, a historical-analog forward signal, a historical baseline, and a duration/exceedance read.
- **Scheduler** — loops over registered sites on an interval; the source of autonomy.
- **Agent** — LLM (Claude via Anthropic API) with tool-use; receives real inputs, returns a structured decision.
- **Decision policy** — the prompt + schema that turns inputs + worker profile into `{risk_level, recommended_action, timing, rationale}`.
- **Alert channel** — real notification out; falls back to a real visible log.
- **Decision log** — persists every decision with the real inputs that produced it (proof the agent is real).
- **UI** — minimal live feed + per-worker view.

## 3. FortyGuard integration (verified against the official Quickstart repo + live calls, 2026-08-18)
- **Base URL:** `https://api.fortyguard.com` (dev: `https://tos-enterprise-api.dev.app.fortyguard.com`).
- **Auth:** header `api-key: <key>` + `Content-Type: application/json`. No Bearer/OAuth.
- **Async submit-poll:** POST an endpoint → get `activity_id` → poll `GET /v1/status/{activity_id}` until `Completed`. **The official client does this in one call** (`client.create_heatmap(...)` → `{"activity_id", "result"}`). Build on the client; do not hand-roll HTTP.
- **Coverage:** US only. **Units:** Celsius throughout — confirmed live (39.85 °C sample, Phoenix August; the shipped client's own docstring incorrectly says °F, disregard it). **History:** 2021–present, but "present" lags ~1 day — see §4.
- **Polygon:** coords are `[longitude, latitude]`, closed ring (first == last). Area caps apply (Basic 10 mi²; hackathon Premium allows more).
- **A worksite is smaller than a tile** (finest granularity 60 m). Do NOT nearest-tile lookup. Compute an **area-weighted mean over every tile the site polygon overlaps** (see the Quickstart parcel notebooks).
- **`filter_type`:** 1 single hour · 2 hour range · 3 whole day · 4 date range (≤31 days).
- **`analytic_type`** (needs `filter_type` 2 or 4): `tcm` (snapshot °C) · `time_of_measure` · `exceedance` (**count of HOURS** past `threshold`, not degree-hours) · `persistence` (longest continuous run). `exceedance`/`persistence` need `threshold` (°C, default 30) + `direction`.
- **Reading tiles — confirmed live.** `tcm` tile `properties` = `{"tile_id", "average_temperature", "min_temperature", "max_temperature"}` (°C). `stats_data` for `tcm` carries `temperature_stats` (`minimum`/`maximum`/`mean`/`standard_deviation`) plus distribution arrays, not flat fields. Analysis types (`exceedance`/`persistence`/`time_of_measure`) → `properties.value` (units in `stats_data.units`). **`properties.temperature` does not exist.**
- **`env_params` caveat:** its heat-index series anchors one temperature across 24h and varies only humidity, so it peaks ~2 a.m. and is coarse (nearby sites can return identical arrays). Use `apparent_temperature_celsius` for feels-like; use heatmap layers to discriminate between sites.
- **Endpoints:** `/v1/heatmap`, `/v1/env_params`, `/v1/satellite` (Premium), `/v1/streetview` (Premium), `/v1/heat_intelligence` (Premium), `/v1/status/{id}`, `/v1/system/fetch-api-key-usage`.

## 4. Forecasting (resolved — verified live, 2026-08-18)
The hackathon FAQ/Slack claimed heatmaps forecast up to 12h ahead; the Quickstart README claimed a future `start_date` fails. **Empirical test with the real key resolved this precisely:**

- A `tcm` call for **today's date** at a past hour (already elapsed) → `n_cells: 0`, empty `map_data.features`.
- The same call for **today's date** at a future hour (not yet elapsed) → `n_cells: 0`, empty `map_data.features` — identical to the past-hour result.
- The same polygon for **yesterday, 3 days ago, 7 days ago, and a 2024 date** → full real data every time (367+ tiles, real stats).

**Verdict: the current calendar day is entirely unavailable (~1-day ingestion lag), regardless of hour.** It is not a "future start_time" restriction specifically — "today" as a whole isn't queryable yet. **There is no live intraday forecast through this endpoint.**

**Design consequence:** Lookout's proactive/forward layer uses **historical analog only** — same hour, same calendar week, from 2021–last year — to project the next few hours' danger. This is the sole forward mechanism; do not build code paths that assume a live forecast will ever return data for today's date.

## 5. Core signals the agent reasons over
1. **Now:** current hyperlocal temperature at the site (area-weighted `tcm`, using the most recent date with data — i.e. not today).
2. **Ahead:** historical analog for the next hours (confirmed sole forward mechanism — see §4).
3. **Baseline:** "normal for this site, this hour" from history.
4. **Duration:** `exceedance`/`persistence` — how long the site stays past the danger threshold. *At site scale this separates danger better than peak temp, which is nearly flat locally.*
5. **Worker profile:** job type, exposure, risk factors — drives personalization.

## 6. Data model (minimal)
- `Site`: id, name, lat, lng, polygon (derived), worker_profile.
- `WorkerProfile`: role, shift_hours, risk_flags (e.g. heart condition), notes.
- `Decision`: site_id, timestamp, inputs (temp, historical-analog projection, baseline, exceedance), risk_level, action, timing, rationale.

## 7. Tech stack
- **Python** (fastest path for an LLM tool-calling agent; pairs with the official client). Node/TS acceptable if the team prefers — keep the same structure.
- **LLM:** Claude via Anthropic API, tool-use for FortyGuard calls.
- **UI:** minimal (a lightweight web feed + per-worker view). The agent is the star, not chrome.
- **Persistence:** simple store for sites + decision log (SQLite/JSON is fine for the sprint).

## 8. Cross-cutting rules
- Real intelligence, no theater (memory.md). Fail loudly; never stub temperature.
- Key server-side only; `.env` git-ignored.
- Cache per site per hour to respect credits.
- US-only, Celsius, closed-ring polygons, requests only for dates at least 1 day old — validate before calling.
