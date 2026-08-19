"""Proactive action + decision logging (Milestone 5; PRD FR4/FR6).

After a real LLM decision (lookout.agent.decide), this module:
1. Determines — from the real forward-projection number the agent already gathered, not
   from the LLM's own prose — whether an upcoming danger window exists, and if so
   pre-schedules a break ahead of it. Code-driven so it can't be talked around by a vaguely
   worded rationale.
2. Emits a real, timestamped alert now (a visible log). No external channel is wired yet —
   that's Milestone 6 — so this never claims a fake "sent" status, per CLAUDE.md.
3. Appends every decision to a persistent decision log with the real inputs that produced
   it (PRD FR6) — proof the agent is real, not theater.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fortyguard import FortyGuardClient
from openai import OpenAI

from .agent import Decision, decide
from .signals import most_recent_available_date
from .sites import Site

ACTIONABLE_RISK_LEVELS = {"moderate", "high", "extreme"}


@dataclass
class ProactiveAlert:
    site_id: str
    site_name: str
    triggered_at: str  # real UTC timestamp
    projected_celsius: float
    threshold_celsius: float
    target_hour: str
    break_start: str
    break_end: str
    message: str


def _latest_forward_projection(decision: Decision) -> dict | None:
    for entry in reversed(decision.real_inputs):
        if entry["tool"] == "get_forward_and_baseline" and "error" not in entry["result"]:
            return entry["result"]
    return None


def assess_proactive_action(
    decision: Decision,
    *,
    anchor_date: str,
    threshold_celsius: float,
    break_duration_minutes: int = 30,
) -> ProactiveAlert | None:
    """Fires only when both are true: the LLM itself rated this actionable risk, AND the
    real forward-projection number it gathered crosses the threshold. Neither condition
    alone is enough — this keeps the proactive trigger grounded in real data, not just
    the model's wording.
    """
    if decision.risk_level not in ACTIONABLE_RISK_LEVELS:
        return None

    forward = _latest_forward_projection(decision)
    if forward is None or forward["projected_target_celsius"] < threshold_celsius:
        return None

    target_hour = forward["target_hour"]
    target_dt = datetime.strptime(f"{anchor_date} {target_hour}", "%Y-%m-%d %H:%M")
    break_start = target_dt - timedelta(minutes=break_duration_minutes)
    break_end = target_dt

    return ProactiveAlert(
        site_id=decision.site_id,
        site_name=decision.site_name,
        triggered_at=datetime.now(timezone.utc).isoformat(),
        projected_celsius=forward["projected_target_celsius"],
        threshold_celsius=threshold_celsius,
        target_hour=target_hour,
        break_start=break_start.isoformat(),
        break_end=break_end.isoformat(),
        message=(
            f"[LOOKOUT ALERT] {decision.site_name}: projected {forward['projected_target_celsius']:.1f}°C "
            f"at {target_hour} (threshold {threshold_celsius}°C). Pre-scheduled break "
            f"{break_start.strftime('%H:%M')}-{break_end.strftime('%H:%M')}. Risk: {decision.risk_level}."
        ),
    )


class AlertLog:
    """A real, visible alert channel. Not an external notification (that's Milestone 6) —
    this never fakes a "sent" status; it prints and durably logs, which is the honest
    fallback CLAUDE.md calls for when a live channel isn't wired yet.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def emit(self, alert: ProactiveAlert) -> None:
        print(alert.message)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(alert)) + "\n")


class DecisionLog:
    """Every autonomous decision, with the real inputs that produced it (PRD FR6)."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def append(self, decision: Decision) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        record = asdict(decision)
        record["logged_at"] = datetime.now(timezone.utc).isoformat()
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")


def decide_and_act(
    openai_client: OpenAI,
    fortyguard_client: FortyGuardClient,
    site: Site,
    decision_log: DecisionLog,
    alert_log: AlertLog,
    *,
    anchor_date: str | None = None,
    threshold_celsius: float = 35.0,
    baseline_years: list[int],
) -> tuple[Decision, ProactiveAlert | None]:
    """One full autonomous cycle for a site: real decision, real proactive check, real log."""
    anchor_date = anchor_date or most_recent_available_date().isoformat()

    decision = decide(
        openai_client, fortyguard_client, site,
        anchor_date=anchor_date, threshold_celsius=threshold_celsius, baseline_years=baseline_years,
    )
    decision_log.append(decision)

    alert = assess_proactive_action(decision, anchor_date=anchor_date, threshold_celsius=threshold_celsius)
    if alert is not None:
        alert_log.emit(alert)

    return decision, alert
