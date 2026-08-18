# PRD — Lookout

## 1. One-liner
**Lookout** is an autonomous AI agent that watches over outdoor workers in extreme heat and acts *before* danger hits — monitoring each worker's exact site with FortyGuard's hyperlocal temperature data, and firing personalized safety actions without being asked.

## 2. Problem
Extreme heat is the deadliest weather hazard, and outdoor workers (construction, delivery, landscaping) are the most exposed. The tools they have are reactive and coarse: a weather app shows one city-wide "feels-like" number and waits for someone to check it. But heat is hyperlocal — a single block can run several degrees hotter than the reading downtown — and the moment to act is *before* the danger window, not after someone is already sick. Heat deaths are overwhelmingly preventable; the information exists but never reaches the person in time.

## 3. Users & buyer
- **Primary user:** the outdoor worker. The experience is warm, personal, and low-effort — they don't operate it; it looks out for them.
- **Buyer / deployer:** cities and employers (matches who FortyGuard sells to). The worker is protected; the employer or city deploys and pays. This dual framing is deliberate — warm demo, serious go-to-market.

## 4. Hackathon fit
- **Primary track:** Track 06 — Agentic AI ("autonomous agents that plan, call, and sequence FortyGuard endpoints from a natural-language goal, without human intervention").
- **Secondary tags:** Track 01 (Resilient Cities), Track 04 (Government & Environment — worker-safety alerts).
- **Judging (40/35/15/10):** Impact & Relevance, Technical Execution, Innovation, Communication. The autonomy and the "only possible with FortyGuard's data" story are where we score.

## 5. Goals
- G1 — Demonstrate genuine autonomy: the agent monitors, decides, and acts on its own loop, not in response to a user prompt.
- G2 — Make hyperlocal personalization visceral: the same site yields different actions for different worker profiles.
- G3 — Reason about **duration** of danger (how long a site stays past a threshold), not just peak temperature.
- G4 — Every number and decision in the demo comes from a real FortyGuard call + real LLM reasoning (see the golden rule in memory.md).

## 6. Functional requirements
- FR1 — Maintain a list of registered worker sites (lat/lng + worker profile).
- FR2 — On an autonomous schedule, for each site: pull current hyperlocal temperature, a historical-analog forward signal, and a historical baseline via FortyGuard.
- FR3 — Feed those real inputs to an LLM that outputs `{risk_level, recommended_action, timing, rationale}`, personalized to the worker profile.
- FR4 — Detect an upcoming danger window and act proactively (pre-schedule a break, emit an alert) before it arrives.
- FR5 — Emit alerts through a real channel (webhook/email/SMS) or, if not wired in time, a real visible alert log — never a faked "sent".
- FR6 — Log every autonomous decision with the real inputs that produced it.
- FR7 — A minimal UI: a live feed of autonomous decisions + a per-worker detail view (temp, forward curve, action, rationale).

## 7. Non-functional requirements
- NFR1 — US-only coverage; handle non-US coordinates cleanly (refuse, don't crash).
- NFR2 — API key stays server-side only; never in frontend, repo, or demo network traffic (disqualification risk).
- NFR3 — Respect credits: cache per site per hour (data is hourly); failed calls are free but avoid needless polling.
- NFR4 — Fail loudly on missing key / failed call; no silent fallback to fake data.
- NFR5 — Never request FortyGuard data for today's calendar date — verified live to always return empty (see memory.md Gotchas); always query at least 1 day in the past.

## 8. Success criteria (demo)
A judge changes the coordinate or the worker profile and the output **really changes** because a real call ran. The "money shot" is a side-by-side: a normal weather app's single city-wide number vs. Lookout's per-block, per-worker, autonomously-made decision with a break already scheduled.

## 9. Out of scope (for the sprint)
- Production routing engine, real worker onboarding at scale, native mobile app, payment/settlement. Curated real-world reference data (e.g. actual Phoenix cooling centers) is acceptable and labeled as such.

## 10. Key open question — RESOLVED (2026-08-18)
Whether FortyGuard supports true short-range forecasting (future `start_time` today) or only historical data. **Verified empirically: no.** The entire current calendar day returns zero data regardless of hour (~1-day ingestion lag), not specifically a future-time restriction. Lookout's proactive layer runs on the **historical-analog fallback** exclusively. See architecture.md §4 and memory.md Gotchas for the full test evidence.
