# Handoff — Lookout

> **Purpose:** the living state of the build. Update this at the END of every work session (or agent run) so the next session — human or agent — starts with full context. Keep it short and current; move durable facts to memory.md.

---

## Current status
- **Phase / milestone:** Milestone 1 complete (live API proof + forecast verification). Ready to start Milestone 2 (Signals layer).
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

## In progress
- Nothing active. Milestone 2 (Signals layer: baseline, historical-analog forward signal, exceedance/persistence duration read) is next up.

## Next up (top of the queue)
1. Milestone 2: area-weighted mean across overlapping tiles for a real site polygon; historical baseline ("normal for this site, this hour"); historical-analog forward projection; `exceedance`/`persistence` duration read.
2. Milestone 3: autonomous scheduler loop over registered sites.

## Blockers / waiting on
- None currently.

## Decisions made (most recent first)
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
- **Never query FortyGuard for today's calendar date** — confirmed empty regardless of hour. Any "current" read should use the most recent date that's at least 1 day old; the historical-analog signal covers the "ahead" need.
- Proof script lives at `scripts/milestone1_live_proof.py` in the repo — reusable for future spot-checks, ran with `PYTHONPATH=<repo root> python scripts/milestone1_live_proof.py` (needed because the script isn't invoked with `-m`, so the repo root isn't auto-added to `sys.path`).

---

### Session log (append one block per session)
```
[2026-08-18] Claude (agent session)
- Did: Cloned repo from Quickstart template (github.com/Datwebguy/lookout) into working directory; installed dependencies; created .env (user supplied real API key); wrote scripts/milestone1_live_proof.py and ran it against the real FortyGuard API across multiple diagnostic rounds; wrote all six planning docs (CLAUDE.md, memory.md, prd.md, architecture.md, project-plan.md, handoff.md) into the repo root with real findings folded in.
- Learned / decided: (1) FortyGuard has no live intraday forecast — today's calendar date returns zero data at any hour, past or future, due to ~1-day ingestion lag; historical-analog is the confirmed sole forward mechanism. (2) Units are genuinely Celsius, confirmed live, despite the shipped client's own docstring claiming °F for tcm — real response overrides even the client's inline comments. (3) tcm tile field path confirmed: properties.average_temperature/min_temperature/max_temperature; stats_data nests real stats under temperature_stats, not flat. (4) Location-sensitivity confirmed real (different tile counts and stats for two nearby polygons on a working date).
- Left for next: Milestone 2 (signals layer) — area-weighted mean, historical baseline, historical-analog forward projection, exceedance/persistence duration read, all built on the verified field paths and the confirmed no-forecast constraint. Not yet committed to git — awaiting user review of Milestone 1 before committing per the "commit after each working milestone" rule.
```
