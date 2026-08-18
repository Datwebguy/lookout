# Handoff — Lookout

> **Purpose:** the living state of the build. Update this at the END of every work session (or agent run) so the next session — human or agent — starts with full context. Keep it short and current; move durable facts to memory.md.

---

## Current status
- **Phase / milestone:** Milestone 1 and Milestone 2 (Signals layer) both complete on real data. Milestone 2 not yet committed. Ready to start Milestone 3 (autonomous scheduler loop).
- **Last updated:** 2026-08-18 by Claude (agent session)
- **Repo:** https://github.com/Datwebguy/lookout
- **Live demo URL:** <none yet>

## Done so far
- Concept, PRD, architecture, plan, and memory docs written and agreed.
- Name locked: **Lookout**.
- API specs verified against the official Quickstart repo.
- Repo cloned from the FortyGuard Quickstart template; `fortyguard/`, `notebooks/`, `requirements.txt`, `.env.example` confirmed present.
- Dependencies installed (`pip install -r requirements.txt`).
- `.env` created from `.env.example`; real `FORTYGUARD_API_KEY` added by the user (never printed/logged/committed).
- **Milestone 1 — live API proof, done for real:**
  - Real `create_heatmap` calls against a small Phoenix polygon, `tcm`, granularity 100. Real `activity_id`s and `stats_data` printed (see `scripts/milestone1_live_proof.py` output).
  - Confirmed the tile field path: `properties.average_temperature`/`min_temperature`/`max_temperature` — real sample `{"tile_id": 0, "average_temperature": 39.85, ...}`.
  - Confirmed values genuinely differ by location: Polygon A (367 tiles, mean 39.88 °C) vs. Polygon B moved ~4.6km east (412 tiles, mean 39.85 °C, different min/max/tile-count) — real difference, not doc claims.
  - **Verified units are Celsius live** (39.85 °C sample is physically consistent with Phoenix in August) — this directly contradicts `fortyguard/client.py`'s own docstring, which claims tcm tiles are °F. Real response wins; the client's inline comment is wrong.
  - **Forecast question resolved empirically — see below.**
- **Milestone 2 — signals layer, done for real (real numbers, see Session log part 3):**
  - `lookout/signals.py`: `area_weighted_mean_temperature`, `historical_baseline`, `historical_analog_forward`, `duration_signal` — every one makes real calls and fails loudly (`SignalUnavailableError`), never fabricates a value.
  - `scripts/milestone2_signals_proof.py` ran clean end-to-end: area-weighted mean 40.03°C; baseline 40.12°C from real 2023/2024/2025 samples; forward projection 38.88°C for 18:00 today (climatology + persistence, since there's no live forecast); exceedance 84.29h and persistence 8.00h over the last real 7-day window.
  - Discovered and fixed a real minimum-query-area constraint (see Decisions below) — this was the root cause of an earlier apparent "outage," not a real backend failure.

## In progress
- Nothing active.

## Next up (top of the queue)
1. Commit Milestone 2 (`lookout/signals.py`, `scripts/milestone2_signals_proof.py`, doc updates).
2. Milestone 3: autonomous scheduler loop over registered sites, built on the signals layer.

## Blockers / waiting on
- None currently. (The apparent backend outage logged earlier this session turned out to have two real, now-understood causes — see Decisions below — not an actual FortyGuard outage.)

## Decisions made (most recent first)
- **Signals layer always submits a ~2km bounding query AOI, never the raw site polygon.** Live testing found a real minimum query-area threshold: a small worksite polygon (200m up to 1.5km per side) returns zero tiles even on dates otherwise 100% reliable (confirmed on 2024-07-15 and 2026-08-15, both proven reliable with a larger box); a ~2km box works consistently. `lookout/signals.py` now builds a `_bounding_query_aoi` around the site's centroid for every API call, then area-weights the *result* against the real (smaller) site polygon — this was the actual root cause of what first looked like a live outage.
- **Use a 3-day safety margin for "the most recent available date," not 1 day.** Live testing showed "yesterday" is NOT reliably available — it returned real data multiple times early in a session, then returned empty on an identical retry later, while dates 3+ days old stayed consistently available throughout. `most_recent_available_date()` defaults to `today - 3 days`.
- **Forecast mechanism = historical-analog, not live forecast** (see Open questions below for the evidence). This changes every downstream milestone that touches "ahead"/"forward" signal — always use historical-analog, never attempt to query today's date expecting real-time or near-future data.
- Trust a real API response over even the shipped client's own source-code comments — `fortyguard/client.py` incorrectly documents tcm units as °F; live data proved Celsius.
- Build on the official `fortyguard` Python client, not hand-rolled HTTP.
- Reason on **duration** of danger (exceedance/persistence), not just peak temp.
- Primary user = outdoor worker; buyer = city/employer. Demo city = Phoenix.
- Primary track = Agentic (06); secondary = Cities (01), Government (04).

## Open questions (resolve, then record answer here + in memory.md)
- **Forecasting: RESOLVED 2026-08-18.** Tested `create_heatmap` (tcm, filter_type=1) for today's date (2026-08-18) at both a past hour (10:00, already elapsed) and a future hour (18:00, not yet elapsed) — **both returned `n_cells: 0`, empty `map_data.features`**, identically. The same polygon for yesterday (2026-08-17), 3 days ago, 7 days ago, and a 2024 date all returned full real data (367+ tiles) instantly. **Answer: NO live forecast — the entire current calendar day is unavailable (~1-day ingestion lag), not specifically a future-`start_time` restriction. Use historical-analog exclusively for the forward signal.**
- Alert channel: which real provider (webhook/email/SMS)? → still open, decide during Milestone 6.

## Notes for the next session
- Golden rule: real data only, fail loudly, never stub temperature.
- Key server-side only; never commit it; ignore the leaked key floating in the Slack channel.
- Field paths confirmed against a real response: `average_temperature`/`min_temperature`/`max_temperature` on tcm tile `properties`; `stats_data.temperature_stats.{minimum,maximum,mean,standard_deviation}` for the aggregate; no `properties.temperature`.
- **Never query FortyGuard for today's calendar date, and treat "yesterday" as unreliable too** — use `lookout.signals.most_recent_available_date()` (3-day margin) for anything that needs to be stable, e.g. a demo. The historical-analog signal covers the "ahead" need.
- **Never submit a small site polygon directly as the query AOI** — use `lookout.signals.area_weighted_mean_temperature`/`duration_signal`, which build a real ~2km bounding AOI automatically and area-weight against the actual site polygon. A worksite AOI under ~1.5-2km per side returns zero tiles.
- Proof scripts live at `scripts/milestone1_live_proof.py` and `scripts/milestone2_signals_proof.py` — reusable for future spot-checks, run with `PYTHONPATH=<repo root> python scripts/<name>.py` (needed because the scripts aren't invoked with `-m`, so the repo root isn't auto-added to `sys.path`).

---

### Session log (append one block per session)
```
[2026-08-18, part 1] Claude (agent session)
- Did: Cloned repo from Quickstart template (github.com/Datwebguy/lookout) into working directory; installed dependencies; created .env (user supplied real API key); wrote scripts/milestone1_live_proof.py and ran it against the real FortyGuard API across multiple diagnostic rounds; wrote all six planning docs (CLAUDE.md, memory.md, prd.md, architecture.md, project-plan.md, handoff.md) into the repo root with real findings folded in. Committed (ab98f74).
- Learned / decided: (1) FortyGuard has no live intraday forecast — today's calendar date returns zero data at any hour, past or future, due to ~1-day ingestion lag; historical-analog is the confirmed sole forward mechanism. (2) Units are genuinely Celsius, confirmed live, despite the shipped client's own docstring claiming °F for tcm — real response overrides even the client's inline comments. (3) tcm tile field path confirmed: properties.average_temperature/min_temperature/max_temperature; stats_data nests real stats under temperature_stats, not flat. (4) Location-sensitivity confirmed real (different tile counts and stats for two nearby polygons on a working date).
- Left for next: Milestone 2 (signals layer).

[2026-08-18, part 2] Claude (agent session)
- Did: Verified exceedance/persistence response shape live (properties.value, flat stats_data with min/max/mean/units="hour") — real result: 271 of 384 possible hours exceeded 35°C over Aug 1-17 at the test site, a plausible ~70% for Phoenix in August. Wrote lookout/signals.py (area_weighted_mean_temperature, historical_baseline, historical_analog_forward, duration_signal) and scripts/milestone2_signals_proof.py. Ran the proof script — first call failed with zero tiles for a small worksite polygon. Diagnosed thoroughly rather than assuming a bug: tested worksite sizes from 200m up to the exact known-good 2km box, and granularity 60 vs 100 — all came back empty. Checked credits (fine, 1.89M remaining) and the raw status payload (no error field, genuinely empty). Retried the identical known-good query 3x — empty every time.
- Learned / decided: Initially looked like a real FortyGuard-side outage; SignalUnavailableError correctly refused to substitute fake data per the golden rule rather than assume success.
- Left for next: Investigate further before assuming outage.

[2026-08-18, part 3] Claude (agent session)
- Did: Investigated the apparent outage properly instead of just waiting it out. Isolated two distinct, real, now-understood causes by testing systematically: (1) retried the exact known-good 2km polygon+date+hour 3x, still empty at first — but then testing older dates (3/7 days back, 2024-07-15) against the SAME known-good box showed they still worked fine, only "yesterday" was bad, meaning it wasn't a full outage. (2) Testing the small worksite polygon directly against a confirmed-reliable date (2024-07-15) also came back empty, isolating that the actual worksite-sized polygon (200m-1.5km) was too small an AOI regardless of date. Fixed lookout/signals.py to submit a real ~2km bounding query AOI (built around the site polygon's centroid) instead of the raw site polygon, and to area-weight results against the real site geometry afterward. Also bumped most_recent_available_date()'s safety margin from 1 to 3 days given the yesterday-instability finding. Reran scripts/milestone2_signals_proof.py end-to-end — all four signals succeeded with real, coherent numbers (area-weighted mean 40.03°C; baseline 40.12°C from 2023/2024/2025; forward projection 38.88°C for 18:00 today, math verified: 38.9735 + -0.0948 = 38.8787; exceedance 84.29h and persistence 8.00h over a real 7-day window).
- Learned / decided: There is a real FortyGuard minimum query-area threshold (somewhere between 1.5km and 2km per side) — a worksite-sized polygon submitted directly returns zero tiles even on perfectly good dates. Also confirmed "yesterday" specifically can flip from available to unavailable within the same session, while 3+-day-old dates stayed reliable throughout. Neither of these is a bug in our code or a genuine outage — both are now handled for real in lookout/signals.py.
- Left for next: Milestone 3 (autonomous scheduler loop). Commit Milestone 2 first.
```
