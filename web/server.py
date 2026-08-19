"""Lookout demo web server (Milestone 7).

Serves the landing page + live dashboard and a thin real-data API on top of the existing
lookout package. Never fabricates a response: /api/decisions and /api/alerts read the real
JSONL logs Milestones 4-6 already produce, and /api/run triggers a genuine autonomous cycle
(real FortyGuard + real OpenAI calls) rather than returning canned data.
"""

from __future__ import annotations

import json
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from fortyguard import FortyGuardClient  # noqa: E402
from fortyguard.exceptions import FortyGuardError  # noqa: E402
from openai import OpenAI  # noqa: E402

from lookout.notify import DeliveryLog, WebhookNotifier  # noqa: E402
from lookout.proactive import AlertLog, DecisionLog, decide_and_act  # noqa: E402
from lookout.sites import load_sites  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "lookout" / "data"
SITES_PATH = DATA_DIR / "sites.json"
DECISION_LOG_PATH = DATA_DIR / "decision_log.jsonl"
ALERT_LOG_PATH = DATA_DIR / "alerts.jsonl"
DELIVERY_LOG_PATH = DATA_DIR / "deliveries.jsonl"
STATIC_DIR = Path(__file__).resolve().parent / "static"

BASELINE_YEARS = [2024, 2025]
THRESHOLD_CELSIUS = 35.0

app = FastAPI(title="Lookout")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _read_jsonl(path: Path, limit: int | None = None) -> list[dict]:
    if not path.exists():
        return []
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    records = [json.loads(line) for line in lines]
    records.reverse()  # most recent first
    return records[:limit] if limit else records


@app.get("/api/sites")
def get_sites() -> list[dict]:
    sites = load_sites(SITES_PATH)
    return [
        {
            "id": s.id,
            "name": s.name,
            "lat": s.lat,
            "lon": s.lon,
            "worker_profile": {
                "role": s.worker_profile.role,
                "shift_hours": s.worker_profile.shift_hours,
                "risk_flags": s.worker_profile.risk_flags,
                "notes": s.worker_profile.notes,
            },
        }
        for s in sites
    ]


@app.get("/api/decisions")
def get_decisions(limit: int = 50) -> list[dict]:
    return _read_jsonl(DECISION_LOG_PATH, limit)


@app.get("/api/alerts")
def get_alerts(limit: int = 50) -> list[dict]:
    return _read_jsonl(ALERT_LOG_PATH, limit)


@app.post("/api/run")
def run_now() -> dict:
    """Trigger one real autonomous cycle for every registered site, right now.

    Real FortyGuard + real OpenAI calls per site (roughly a minute or two each) — no
    mocked or cached-looking response. Failures are surfaced, not swallowed.
    """
    try:
        fg_client = FortyGuardClient()
    except FortyGuardError as exc:
        raise HTTPException(status_code=500, detail=f"FortyGuard client error: {exc}") from exc

    openai_client = OpenAI()
    sites = load_sites(SITES_PATH)
    decision_log = DecisionLog(DECISION_LOG_PATH)
    alert_log = AlertLog(ALERT_LOG_PATH)
    notifier = WebhookNotifier()
    delivery_log = DeliveryLog(DELIVERY_LOG_PATH)

    results = []
    for site in sites:
        try:
            decision, alert = decide_and_act(
                openai_client, fg_client, site, decision_log, alert_log,
                threshold_celsius=THRESHOLD_CELSIUS, baseline_years=BASELINE_YEARS,
            )
        except Exception as exc:  # noqa: BLE001 - surface any real failure to the caller
            results.append({"site_id": site.id, "site_name": site.name, "error": str(exc)})
            continue

        delivery = None
        if alert is not None:
            delivery_results = notifier.send(alert)
            delivery_log.append(alert, delivery_results)
            delivery = [{"channel": r.channel, "sent": r.sent, "configured": r.configured, "detail": r.detail} for r in delivery_results]

        results.append({
            "site_id": site.id,
            "site_name": site.name,
            "risk_level": decision.risk_level,
            "recommended_action": decision.recommended_action,
            "timing": decision.timing,
            "rationale": decision.rationale,
            "alert": None if alert is None else {
                "message": alert.message,
                "projected_celsius": alert.projected_celsius,
                "target_hour": alert.target_hour,
                "break_start": alert.break_start,
                "break_end": alert.break_end,
            },
            "delivery": delivery,
        })

    return {"results": results}


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(str(STATIC_DIR / "index.html"))
