"""Milestone 5 — proactive action live proof.

Runs one full real autonomous cycle per registered site: real LLM decision, real
code-driven proactive-danger check (grounded in the real forward-projection number, not
LLM prose), a real visible alert emission if triggered, and a persisted decision log entry
with real inputs. Run with:
    PYTHONPATH=<repo root> python scripts/milestone5_proactive_proof.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fortyguard import FortyGuardClient  # noqa: E402
from fortyguard.exceptions import FortyGuardError  # noqa: E402
from openai import OpenAI  # noqa: E402
from lookout.proactive import AlertLog, DecisionLog, decide_and_act  # noqa: E402
from lookout.sites import load_sites  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
SITES_PATH = REPO_ROOT / "lookout" / "data" / "sites.json"
DECISION_LOG_PATH = REPO_ROOT / "lookout" / "data" / "decision_log.jsonl"
ALERT_LOG_PATH = REPO_ROOT / "lookout" / "data" / "alerts.jsonl"

BASELINE_YEARS = [2024, 2025]
THRESHOLD_CELSIUS = 35.0


def section(title: str) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def main() -> int:
    try:
        fg_client = FortyGuardClient()
    except FortyGuardError as exc:
        print(f"FAIL: could not construct FortyGuard client — {exc}", file=sys.stderr)
        return 1

    openai_client = OpenAI()

    sites = load_sites(SITES_PATH)
    decision_log = DecisionLog(DECISION_LOG_PATH)
    alert_log = AlertLog(ALERT_LOG_PATH)

    decision_log_lines_before = decision_log.path.read_text().splitlines() if decision_log.path.exists() else []
    alert_log_lines_before = alert_log.path.read_text().splitlines() if alert_log.path.exists() else []

    for site in sites:
        section(f"AUTONOMOUS CYCLE — {site.name} ({site.worker_profile.role})")
        decision, alert = decide_and_act(
            openai_client, fg_client, site, decision_log, alert_log,
            threshold_celsius=THRESHOLD_CELSIUS, baseline_years=BASELINE_YEARS,
        )
        print(f"risk_level: {decision.risk_level}")
        print(f"recommended_action: {decision.recommended_action}")
        print(f"real_inputs gathered: {[e['tool'] for e in decision.real_inputs]}")
        if alert is not None:
            print("\nPROACTIVE ALERT FIRED (real, code-driven check — not just LLM wording):")
            print(f"  {alert.message}")
        else:
            print("\nNo proactive alert fired for this site/decision.")

    section("VERIFY PERSISTENCE — real files actually grew")
    decision_log_lines_after = decision_log.path.read_text().splitlines()
    alert_log_lines_after = alert_log.path.read_text().splitlines() if alert_log.path.exists() else []

    new_decisions = len(decision_log_lines_after) - len(decision_log_lines_before)
    new_alerts = len(alert_log_lines_after) - len(alert_log_lines_before)
    print(f"Decision log: {len(decision_log_lines_before)} -> {len(decision_log_lines_after)} lines (+{new_decisions})")
    print(f"Alert log:    {len(alert_log_lines_before)} -> {len(alert_log_lines_after)} lines (+{new_alerts})")

    if new_decisions != len(sites):
        print(f"FAIL (loud): expected {len(sites)} new decision log entries, got {new_decisions}", file=sys.stderr)
        return 1

    print("\nSample persisted decision log record (most recent):")
    print(json.dumps(json.loads(decision_log_lines_after[-1]), indent=2)[:1500])

    section("DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
