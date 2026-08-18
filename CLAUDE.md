# Lookout — Build Guide (CLAUDE.md)

> Read this file fully at the start of every session before writing or changing code.
> It is the single source of truth for what Lookout is and how it must be built.

---

## 1. What we're building
**Lookout** is an **autonomous AI agent** that watches over outdoor workers in extreme heat and acts *before* danger hits.

It continuously monitors the exact worksite of each registered worker using FortyGuard's hyperlocal temperature data, reasons about that specific person's risk, and — without being asked — decides and fires personalized heat-safety actions (alert + pre-scheduled rest break) before a dangerous threshold is crossed.

- **End user:** the outdoor worker (construction, delivery, landscaping). The experience is warm and personal.
- **Buyer:** cities and employers (this matches who FortyGuard sells to).
- **Hackathon track:** Track 06 — Agentic AI. Autonomy is the whole point: *analyze, decide, and automate without human intervention.* A chatbot that only answers when asked does NOT satisfy this track.

One-line pitch: *"Lookout watches every worker's block in real time and calls the break before the heat does."*

---

## 2. The golden rule — real intelligence, no theater
Every number and every decision the demo shows **must come from a real FortyGuard API call and real LLM reasoning.** Change the location or the worker profile — the output must really change because real code ran.

- **Never** hardcode, mock, or fake a temperature value. If the API key or a call fails, **fail loudly** — do not silently substitute fake data.
- Reference data (cooling-center locations, danger thresholds) MAY be a **curated, genuinely real-world set** that is static. That is bounded scope, not fake — but it must be real places / real numbers, and labeled as a curated set.
- If you (the agent) are ever tempted to stub the temperature data "to keep moving," STOP and flag it to the user instead.

---

## 3. Hard constraints from FortyGuard's API (confirmed — build to these exactly)
- **Coverage: United States only.** Non-US coordinates fail or return empty. Handle explicitly (refuse, don't crash).
- **Data:** 2-meter ambient air temperature, ~20-meter resolution, hourly. History from **1 January 2021** to present. **All temperatures are in Celsius** — verified live 2026-08-18 (see §3a); ignore the `fortyguard/client.py` docstring, which incorrectly says tcm tiles are in °F.
- **Forecasting — VERIFIED 2026-08-18, does NOT work today. See §3a for the full result.** Lookout's proactive layer runs on a **historical-analog** fallback, not a live forecast.
- **The API is ASYNCHRONOUS and polygon-based — this shapes the whole build.** You do NOT get a temperature by asking for a lat/lng. You `POST /v1/heatmap` with a small **polygon** — get an `activity_id` — poll `GET /v1/status/{activity_id}` until `Completed` — read the result. **Use the official `fortyguard` Python client (below) — it does the submit-and-poll in one call**, so you don't hand-roll this.
- **A worksite is SMALLER than a tile — this matters.** Finest granularity is 60 m; a typical site spans just a few tiles. Don't do a nearest-tile lookup (it discards most of the site). Compute an **area-weighted mean over every tile the site polygon overlaps** — the Quickstart's parcel notebooks show exactly this pattern. Coordinates are `[longitude, latitude]`; ring must be closed (first pair == last pair). Area caps apply (Basic tier is capped at 10 mi²; hackathon Premium keys allow more).
- **At site scale, peak temperature is nearly flat — DURATION is what separates danger.** The repo measured it: across a small AOI the daily-peak spread is under 1 °C, but exceedance spread is 6–15 hours. **So Lookout should reason primarily on how LONG a site stays past a danger threshold, not just the peak.** That's the `exceedance` / `persistence` analytics — and it's a stronger, more defensible pitch than "it's hot right now."
- **`filter_type`:** `1` = single hour (needs `start_time`), `2` = hour range same day (`start_time`+`end_time`), `3` = whole day (start_time ignored), `4` = date range (add `end_date`, capped ~31 days).
- **`granularity`:** `60`, `80`, or `100` meters. Smaller = finer + more credits. Use `100` while testing.
- **Analytics (`analytic_type`, needs a multi-hour/day window — `filter_type` 2 or 4):** `tcm` (default, snapshot temp in °C) · `time_of_measure` (UTC hour of the cell's peak) · `exceedance` (**count of HOURS past `threshold`, not degree-hours** — a value of 6 means six hours past it) · `persistence` (longest continuous run of such hours). `exceedance`/`persistence` require `threshold` (°C, default 30) and `direction` (`above`/`below`).
- **Reading results — the tile field names differ by type.** `tcm` tiles carry `properties.average_temperature` / `min_temperature` / `max_temperature` (°C) — **confirmed live**, real sample: `{"tile_id": 0, "average_temperature": 39.85, "min_temperature": 39.85, "max_temperature": 39.85}`. `stats_data` for a `tcm` call carries `temperature_stats` (`minimum`/`maximum`/`mean`/`standard_deviation`) plus distribution arrays — not a flat set of fields. The analysis types (`exceedance`/`persistence`/`time_of_measure`) carry `properties.value` (interpret with `stats_data.units`, e.g. `hour`). **`properties.temperature` does not exist — code that reads it finds nothing.**
- **`env_params` heat index is a trap — read this before using it.** Its heat-index series applies one `temperature` anchor across all 24 hours and varies only humidity, so it artificially **peaks around 2 a.m.** and is only meaningful at the afternoon hot hour. It also resolves on a **coarse weather grid** — two sites >1 km apart can return identical arrays. For "feels-like" use `apparent_temperature_celsius` (which follows the real diurnal cycle); use the **heatmap** layers (not env_params) to tell nearby sites apart.
- **Credits:** deducted only on **successful** completion; failed tasks are free. Check balance with `client.fetch_api_key_usage()`.
- **Demo city: Phoenix, AZ** (dramatic heat; FortyGuard's own demo city). Test exclusively on real US coordinates, e.g. lat `33.4484`, lon `-112.0740`.

### 3a. Forecast verification result (live, 2026-08-18)
Tested with the real key against `create_heatmap` (`tcm`, `filter_type=1`, granularity 100) over a small Phoenix polygon:

| Test | start_date | start_time | Result |
|---|---|---|---|
| Past hour, **today** | 2026-08-18 (today) | 10:00 (already elapsed) | `n_cells: 0`, empty `map_data.features` |
| Future hour, **today** | 2026-08-18 (today) | 18:00 (not yet elapsed) | `n_cells: 0`, empty `map_data.features` |
| Yesterday | 2026-08-17 | 10:00 | **367 real tiles**, mean 39.88 °C |
| 3 days ago | 2026-08-15 | 10:00 | **367 real tiles**, mean 37.97 °C |
| 7 days ago | 2026-08-11 | 10:00 | **367 real tiles**, mean 35.59 °C |
| Known historical | 2024-07-15 | 14:00 | **367 real tiles**, mean 39.69 °C |

**Verdict: today's calendar date returns zero data no matter the hour — past or future.** This isn't specifically a "future `start_time` fails" restriction as the README implied; the entire *current* day is unavailable, consistent with roughly a 1-day data-ingestion lag. Once a date is even one day old, it returns full real data instantly.

**Conclusion: there is no live intraday forecast available through this endpoint as of the hackathon window.** Lookout's proactive layer must use the **historical-analog** fallback — same hour / same calendar week from 2021–last year — to project the next few hours, exactly as planned as the fallback. Do not attempt to query "a few hours ahead of now" expecting real data; it will always come back empty.

---

## 4. Architecture
```
                 ┌────────────────────────────────┐
                 │  Autonomous scheduler loop     │  ← runs on its own, no human prompt
                 │  (iterates registered sites)   │
                 └────────────────┬────────────────┘
                                  │ for each worker site
                                  ▼
   ┌───────────────┐    ┌────────────────────────┐    ┌──────────────────────┐
   │ FortyGuard    │───▶│  Agent (LLM + tools)    │───▶│  Decision policy      │
   │ API client    │    │  calls API as a tool    │    │  {risk, action,       │
   │ (real calls)  │    │  reasons over inputs    │    │  timing, rationale}   │
   └───────────────┘    └─────────────┬───────────┘    └──────────┬───────────┘
                                       │                          │
                                       ▼                          ▼
                             ┌───────────────┐          ┌────────────────────┐
                             │ Alert channel │          │  Decision log      │
                             │ (real output) │          │ (real inputs kept) │
                             └───────────────┘          └────────────────────┘
                                       │
                                       ▼
                             ┌────────────────────────────┐
                             │ Demo UI: live decision feed │
                             │ + per-worker detail view    │
                             └────────────────────────────┘
```

**Key idea:** the LLM calls the FortyGuard client as a **tool**, so the reasoning is genuine tool-use, not a hardcoded branch. The scheduler makes it autonomous.

---

## 5. Tech stack
- **Language: Python** (fastest path for an LLM tool-calling agent). *If the team prefers Node/TypeScript, switch — but keep the same structure and rules.*
- LLM: Claude via the Anthropic API, using tool-use for the FortyGuard calls.
- HTTP client for FortyGuard. Scheduler via a simple loop / async task.
- UI: keep minimal — a live feed of autonomous decisions + a per-worker detail view. The star is the agent, not chrome.

---

## 6. Configuration — nothing hardcoded
All FortyGuard and LLM config comes from environment variables. **Do not paste keys into code.**

```
FORTYGUARD_API_KEY   = fg_live_...   (generate at dashboard.fortyguard.com → Profile → Create API Key; git-ignored, server-side only)
FORTYGUARD_BASE_URL  = https://api.fortyguard.com   (dev override: https://tos-enterprise-api.dev.app.fortyguard.com)
ANTHROPIC_API_KEY    = <Anthropic key>
```

**Build on the official `fortyguard` Python client — don't hand-roll HTTP.** Repo created from the Quickstart template (github.com/FortyGuard-Tech/temperature-api-quickstart), which ships the client under `fortyguard/` and handles submit-and-poll for you.

**Client methods Lookout will use** (each submits + polls; pass `wait=False` to poll yourself):
```
client.create_heatmap(polygon_aoi, start_date, start_time, filter_type, granularity, analytic_type=..., threshold=..., direction=...)
client.environmental_parameters(...)   # heat index / AQI / solar / apparent_temperature_celsius at a point
client.heat_intelligence(...)          # Premium PDF report
client.satellite_segmentation(...)     # Premium — tree-canopy / land cover (optional: "why is this site hot")
client.get_status(activity_id) / client.wait_for(activity_id)
client.fetch_api_key_usage()           # credit balance
```

**Core call (verified live, this is the real shape):**
```python
from dotenv import load_dotenv; load_dotenv()
from fortyguard import FortyGuardClient
client = FortyGuardClient()  # reads FORTYGUARD_API_KEY

resp = client.create_heatmap(
    polygon_aoi={
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature", "properties": {},
            "geometry": {"type": "Polygon", "coordinates": [[
                [-112.08, 33.44], [-112.06, 33.44],
                [-112.06, 33.46], [-112.08, 33.46],
                [-112.08, 33.44],
            ]]},
        }],
    },
    start_date="2026-08-17", start_time="10:00",   # must be at least 1 day old — see §3a
    filter_type=1, granularity=100,
)
print(resp["activity_id"])
print(resp["result"]["map_data"]["features"][0]["properties"])  # tcm: average_temperature (°C)
print(resp["result"]["stats_data"]["temperature_stats"])         # minimum/maximum/mean/standard_deviation
```

For the **duration-based danger logic** (the strong version of Lookout), use a multi-hour window:
```python
resp = client.create_heatmap(polygon_aoi=site, start_date="2026-08-01", end_date="2026-08-17",
                             filter_type=4, analytic_type="exceedance", threshold=35.0, direction="above")
# analysis tiles carry properties.value (hours past threshold); stats_data.units == "hour"
```

---

## 7. Build order (each step is done only when it runs on REAL data)
1. **Live API proof — ✅ DONE (2026-08-18).** Submitted real Phoenix polygons to `/v1/heatmap`, polled to `Completed`, confirmed real temperature results, confirmed values change when the polygon moves, and empirically verified the forecast question (§3a: no live forecast — use historical-analog).
2. **Baseline + duration.** Add the "normal for this site, this hour" baseline from history, and an `exceedance`/`persistence` call so the agent can reason about how *long* a site stays dangerous, not just the peak. Real values only. Forward signal = historical-analog (confirmed mechanism, per §3a).
3. **Autonomous loop.** Scheduler iterates registered sites, calls the API client per site, passes real temp + historical-analog + baseline to the LLM.
4. **Decision policy.** LLM outputs {risk_level, recommended_action, timing, rationale}; the same block yields different actions for different worker profiles.
5. **Proactive action.** Using the historical-analog mechanism, detect an upcoming threshold crossing, pre-schedule a break, and emit an alert *now*. Log every decision with its real inputs.
6. **Alert channel.** Real notification out (webhook/email/SMS via a real provider). If a live channel can't be wired in time, write to a real visible alert log — never fake a "sent" status.
7. **Demo UI.** Live decision feed + per-worker view (real temp, historical-analog curve, agent's action + rationale).
8. **Harden + rehearse.** Real end-to-end runs on Phoenix coordinates. Handle API timeout, non-US coordinate (refuse cleanly), today's-date requests (no data — don't crash, treat as "not yet available").

---

## 8. Coding conventions & guardrails
- Small, focused changes. One milestone at a time. Commit to git after each working milestone.
- Fail loudly on missing key / failed call. No silent fallbacks to fake data.
- Keep the FortyGuard client as the ONLY place that talks to the API; the agent uses it as a tool.
- Log real inputs alongside every autonomous decision (needed to prove the agent is real).
- Do not invent FortyGuard endpoints or response fields — confirm from docs, and trust a real response over any doc (including this file and the client's own source comments — see §3's unit note).
- Never request data outside the US, before 2021, or for today's date (no data yet — see §3a).

---

## 9. Definition of done (the demo)
The winning demo moment is a **side-by-side**:
- *What a normal weather app shows* — one city-wide number.
- *What Lookout shows* — this block, this worker, this decision, right now, made autonomously, with a rationale, and a break already scheduled from the historical-analog forward signal.

If a judge changes the coordinate or the worker profile and the output really changes from a real call, you've won the core argument.
