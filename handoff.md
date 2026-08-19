# Handoff — Lookout

> **Purpose:** the living state of the build. Update this at the END of every work session (or agent run) so the next session — human or agent — starts with full context. Keep it short and current; move durable facts to memory.md.

---

## Current status
- **Phase / milestone:** Milestones 1-6 complete on real data (live API proof, signals layer, autonomous scheduler loop, LLM decision policy, proactive action + logging, real Slack alert delivery). Milestone 6 not yet committed. Ready to start Milestone 7 (demo UI).
- **Last updated:** 2026-08-19 by Claude (agent session)
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
- **Milestone 3 — autonomous scheduler loop, done for real:**
  - `lookout/sites.py` + `lookout/data/sites.json` — 2 real registered Phoenix sites with distinct worker profiles (construction laborer, delivery driver).
  - `lookout/cache.py` — per-site-per-hour JSON cache.
  - `lookout/scheduler.py` — `Scheduler.tick()` runs one real autonomous pass over every registered site (no human prompt per site); `run_forever()` is the real deployment loop.
  - `scripts/milestone3_scheduler_proof.py` ran clean end-to-end: tick 1 pulled real, genuinely different signals per site (construction 40.04°C vs delivery 39.81°C, different baselines/forward projections/exceedance); tick 2 (same hour) served both sites entirely from cache — zero redundant API calls, confirmed live. Committed (b3e34ba).
- **Milestone 4 — decision policy, done for real. LLM provider changed from the originally-locked Claude/Anthropic to OpenAI (`gpt-5.6-luna`) — user preference, not a technical constraint; see Decisions below.**
  - `lookout/agent.py` — real OpenAI Responses API tool-use: `get_current_temperature`/`get_forward_and_baseline`/`get_exceedance_duration` tools, each a genuine call into `lookout/signals.py`. Two-phase design (tool-gathering loop, then a separate structured-output call) because the Responses API can't combine `tools` and `text.format` json_schema in one call.
  - `scripts/milestone4_agent_proof.py` ran clean end-to-end, real signals + real LLM reasoning: construction site (own profile) → `risk_level: extreme`, action citing "no shade, heavy PPE, concrete pour"; SAME site polygon with the delivery driver's profile swapped in → also `extreme` (correct — genuinely extreme heat for anyone that day) but `recommended_action`/`timing`/`rationale` substantively different, citing "cardiac history" and "un-air-conditioned vehicle" instead. Delivery site on its own profile produced a third, independently-grounded real decision. Committed (36109f4).
- **Milestone 5 — proactive action + decision logging, done for real:**
  - `Decision` (in `lookout/agent.py`) now also carries `real_inputs`: every real tool call the agent made (`{tool, args, result}`), not just its final prose — needed so the decision log has genuine real inputs, not just LLM text.
  - `lookout/proactive.py` — `assess_proactive_action` fires only when BOTH the LLM's own `risk_level` is actionable AND the real forward-projection number it gathered crosses the threshold (code-driven check, not swayed by wording alone); pre-schedules a break window ending exactly at the projected danger hour. `AlertLog`/`DecisionLog` are real append-only JSONL files (`lookout/data/alerts.jsonl`, `lookout/data/decision_log.jsonl`, both git-ignored — runtime state).
  - `scripts/milestone5_proactive_proof.py` ran clean end-to-end: construction site → alert fired, projected 41.7°C at 14:00, break pre-scheduled 13:30-14:00; delivery site → alert fired, projected 41.0°C at 18:00, break pre-scheduled 17:30-18:00. Both logs verified to have actually grown (0→2 lines each) by reading the files back after the run, not just trusting return values. Committed (e7232c9).
- **Milestone 6 — real alert channel, done for real (Slack live; Discord wired but unconfigured):**
  - `lookout/notify.py` — `WebhookNotifier` posts to real Slack (`{"text": ...}`) and/or Discord (`{"content": ...}`) incoming webhooks, each independently read from `SLACK_WEBHOOK_URL`/`DISCORD_WEBHOOK_URL`. `DeliveryResult` always reports the real outcome per channel — `sent`/`configured` are separate booleans, so "not configured" is never confused with "sent" or silently dropped. `DeliveryLog` persists every delivery attempt (`lookout/data/deliveries.jsonl`, git-ignored).
  - User set up a real Slack incoming webhook (api.slack.com/apps → Blank app → Incoming Webhooks). `scripts/milestone6_notify_proof.py` reused the two real alerts already persisted from Milestone 5 (rather than re-running the full FortyGuard+OpenAI pipeline just to test delivery) and POSTed both — real result: **2/2 `HTTP 200` from Slack**, Discord honestly reported "not configured" since no URL was set for it.

## In progress
- Nothing active.

## Next up (top of the queue)
1. Commit Milestone 6 (`lookout/notify.py`, `scripts/milestone6_notify_proof.py`, `.gitignore`, doc updates).
2. Milestone 7: demo UI — live feed of autonomous decisions across sites, per-worker detail view (real temp, forward curve, action + rationale), the "money shot" comparison (weather-app single number vs. Lookout's per-block per-worker decision). The data already exists in `lookout/data/decision_log.jsonl` and `alerts.jsonl` to build this on top of.

## Blockers / waiting on
- None currently.

## Decisions made (most recent first)
- **LLM provider = OpenAI (`gpt-5.6-luna`), not Claude/Anthropic.** User preference, changed 2026-08-18 mid-build — not a FortyGuard or technical requirement. `gpt-5.6-luna` chosen specifically for cost ($0.20/$1.20 per 1M tokens vs $5/$30 flagship `gpt-5.6-sol`) per explicit user request; verified pricing and exact model-ID strings live against the OpenAI docs rather than guessing. Real proof cost was a few cents total. Uses the Responses API (`client.responses.create`), not Chat Completions.
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
- **Alert channel: RESOLVED 2026-08-19.** User chose webhook over email/SMS (fastest real setup, no account/SDK needed), and asked for both Slack and Discord support. Slack is live and verified (real `HTTP 200` deliveries); Discord is coded and wired the same way but the user hasn't set up a webhook for it yet — add `DISCORD_WEBHOOK_URL` to `.env` whenever that's wanted, no code changes needed.

## Notes for the next session
- Golden rule: real data only, fail loudly, never stub temperature.
- Key server-side only; never commit it; ignore the leaked key floating in the Slack channel.
- Field paths confirmed against a real response: `average_temperature`/`min_temperature`/`max_temperature` on tcm tile `properties`; `stats_data.temperature_stats.{minimum,maximum,mean,standard_deviation}` for the aggregate; no `properties.temperature`.
- **Never query FortyGuard for today's calendar date, and treat "yesterday" as unreliable too** — use `lookout.signals.most_recent_available_date()` (3-day margin) for anything that needs to be stable, e.g. a demo. The historical-analog signal covers the "ahead" need.
- **Never submit a small site polygon directly as the query AOI** — use `lookout.signals.area_weighted_mean_temperature`/`duration_signal`, which build a real ~2km bounding AOI automatically and area-weight against the actual site polygon. A worksite AOI under ~1.5-2km per side returns zero tiles.
- `.env` also needs `SLACK_WEBHOOK_URL` (live) and optionally `DISCORD_WEBHOOK_URL` for real alert delivery. Same rule as API keys: never paste a webhook URL into chat if avoidable — write it straight into `.env`.
- Proof scripts live at `scripts/milestone{1,2,3,4,5,6}_*.py` — reusable for future spot-checks, run with `PYTHONPATH=<repo root> python scripts/<name>.py` (needed because the scripts aren't invoked with `-m`, so the repo root isn't auto-added to `sys.path`).
- Registered sites live in `lookout/data/sites.json` (tracked in git); the per-site-per-hour cache lives alongside it at `lookout/data/signal_cache.json` (git-ignored — real runtime state, not source).
- `.env` now needs `OPENAI_API_KEY` (not `ANTHROPIC_API_KEY` — CLAUDE.md updated). Never paste a raw key into chat — write it directly into `.env` yourself; a key pasted into a conversation is in that transcript permanently.

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
- Left for next: Milestone 3 (autonomous scheduler loop). Committed Milestone 2 (2456e50).

[2026-08-18, part 4] Claude (agent session)
- Did: Built Milestone 3 — lookout/geo.py (shared square_polygon helper, refactored out of signals.py to avoid duplicating the same trig math in the sites module), lookout/sites.py (Site/WorkerProfile dataclasses, JSON load/save), lookout/cache.py (per-site-per-hour JSON cache), lookout/scheduler.py (compute_site_signals + Scheduler.tick()/run_forever()). Registered 2 real Phoenix sites with deliberately different worker profiles in lookout/data/sites.json. Added actual_anchor_celsius reuse param to historical_analog_forward so the scheduler doesn't re-query a value it already has. Ran scripts/milestone3_scheduler_proof.py against the real API: tick 1 produced genuinely different real signals per site; tick 2 (same hour) hit cache for both sites with zero new calls.
- Learned / decided: The autonomy mechanism (Scheduler.tick(), no per-site human trigger) and credit-respecting cache both work correctly against real multi-site data. Worker profiles are stored and loaded but don't yet influence the computed signals themselves (by design — that differentiation happens in Milestone 4's LLM decision layer, not the signals layer).
- Left for next: Milestone 4 (decision policy). Committed Milestone 3 (b3e34ba).

[2026-08-18, part 5] Claude (agent session)
- Did: User asked to switch the LLM provider from Claude/Anthropic to OpenAI mid-build (explicitly a preference, not a FortyGuard requirement) and specifically requested the cheapest available tier. Verified current OpenAI API patterns live (WebFetch against developers.openai.com — Responses API, function-calling tool shape, structured-output text.format, since training-data model names like gpt-4o are stale) rather than guessing, and verified real gpt-5.6-sol/terra/luna pricing before picking luna ($0.20/$1.20 per 1M — cheapest). Updated the locked LLM decision in memory.md, CLAUDE.md, architecture.md. Installed openai SDK, removed anthropic from requirements.txt. Wrote lookout/agent.py (two-phase: tool-gathering loop, then structured-output call — OpenAI's Responses API can't combine tools + text.format in one call, unlike Claude) and scripts/milestone4_agent_proof.py. User pasted their raw OpenAI key directly into chat; wrote it to .env without echoing it back and flagged that pasting secrets into chat isn't ideal (already logged in the transcript regardless). Ran the proof end-to-end against real FortyGuard + OpenAI: 3 real decisions, confirmed personalization works (same site + swapped profile → same risk_level "extreme" but substantively different action/timing/rationale, each correctly citing the specific worker's real risk factors).
- Learned / decided: OpenAI's Responses API architecture forces a two-call pattern (gather via tools, then format via schema) where Claude's API would allow one combined call — documented in memory.md so future work on lookout/agent.py doesn't assume the Claude-style combined pattern. Real proof cost was a few cents total on the luna tier.
- Left for next: Milestone 5 (proactive action). Committed Milestone 4 (36109f4).

[2026-08-18, part 6] Claude (agent session)
- Did: Built Milestone 5. Added `real_inputs` field to `Decision` (in `lookout/agent.py`) and populated it during the tool-gathering loop — every `{tool, args, result}` the agent actually called, so the decision log has genuine real inputs, not just the LLM's final prose. Wrote `lookout/proactive.py`: `assess_proactive_action` (fires only when the LLM's risk_level AND the real forward-projection number both cross the threshold — code-driven, not swayed by wording alone; pre-schedules a break ending exactly at the projected danger hour), `AlertLog` and `DecisionLog` (real append-only JSONL files, git-ignored as runtime state). Wrote `scripts/milestone5_proactive_proof.py` and ran it against real FortyGuard + OpenAI for both registered sites.
- Learned / decided: Both real sites triggered a genuine proactive alert (construction: 41.7°C projected at 14:00, break pre-scheduled 13:30-14:00; delivery: 41.0°C at 18:00, break pre-scheduled 17:30-18:00) — verified the decision log and alert log actually grew by reading the files back after the run, not just trusting return values. The proactive trigger requiring BOTH the LLM's own risk assessment AND a real threshold-crossing number (not either alone) keeps it grounded in real data rather than exploitable by vague LLM wording.
- Left for next: Milestone 6 (alert channel). Committed Milestone 5 (e7232c9).

[2026-08-19] Claude (agent session)
- Did: Built Milestone 6. Asked the user which channel (webhook/email/SMS) and which webhook platform — they chose webhook, both Slack and Discord. Wrote `lookout/notify.py`: `WebhookNotifier` posts real Slack (`{"text"}`) and Discord (`{"content"}`) payloads, each independently configured via env var; `DeliveryResult` always reports the real per-channel outcome (sent/failed/not-configured) so nothing is silently skipped or faked; `DeliveryLog` persists every delivery attempt. Walked the user through creating a real Slack incoming webhook (blank app → Incoming Webhooks, not the OAuth/scopes page they initially landed on). User pasted the real webhook URL into chat; wrote it to `.env` without echoing it back further. Wrote `scripts/milestone6_notify_proof.py` — deliberately reused the two real alerts already persisted in `lookout/data/alerts.jsonl` from Milestone 5 instead of re-running the full FortyGuard+OpenAI pipeline just to test delivery. Ran it: both alerts POSTed to the real Slack channel, `HTTP 200` both times; Discord correctly reported "not configured."
- Learned / decided: Reusing already-real, already-persisted data (rather than regenerating it) is a legitimate way to keep a proof both honest and cheap when the thing being tested (delivery) doesn't depend on the thing that's expensive to regenerate (the LLM decision). Discord is fully wired in code but unconfigured — add `DISCORD_WEBHOOK_URL` to `.env` whenever wanted, zero code changes needed.
- Left for next: Milestone 7 (demo UI) — live decision feed + per-worker detail view, built on `lookout/data/decision_log.jsonl` and `alerts.jsonl`, which already have real records. Not yet committed.
```
