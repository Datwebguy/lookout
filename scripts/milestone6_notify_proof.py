"""Milestone 6 — alert channel live proof.

Delivers real, already-triggered alerts (from lookout/data/alerts.jsonl, produced by a
real Milestone 5 run) to whichever real webhook(s) are configured, and honestly reports
delivery status per channel — never a faked "sent". Reuses real alerts already on disk
instead of re-running the full FortyGuard+OpenAI pipeline just to test delivery. Run with:
    PYTHONPATH=<repo root> python scripts/milestone6_notify_proof.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from lookout.notify import DeliveryLog, WebhookNotifier  # noqa: E402
from lookout.proactive import ProactiveAlert  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
ALERTS_PATH = REPO_ROOT / "lookout" / "data" / "alerts.jsonl"
DELIVERY_LOG_PATH = REPO_ROOT / "lookout" / "data" / "deliveries.jsonl"


def section(title: str) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def main() -> int:
    if not ALERTS_PATH.exists():
        print(
            f"FAIL: no alerts found at {ALERTS_PATH} — run "
            "scripts/milestone5_proactive_proof.py first to generate a real alert.",
            file=sys.stderr,
        )
        return 1

    alert_records = [json.loads(line) for line in ALERTS_PATH.read_text().splitlines() if line.strip()]
    if not alert_records:
        print(f"FAIL: {ALERTS_PATH} is empty.", file=sys.stderr)
        return 1

    notifier = WebhookNotifier()
    delivery_log = DeliveryLog(DELIVERY_LOG_PATH)

    if not notifier.slack_url and not notifier.discord_url:
        print(
            "FAIL: neither SLACK_WEBHOOK_URL nor DISCORD_WEBHOOK_URL is set in .env — "
            "nothing to actually deliver to. Add at least one real webhook URL.",
            file=sys.stderr,
        )
        return 1

    for record in alert_records:
        alert = ProactiveAlert(**record)
        section(f"DELIVER — {alert.site_name}")
        print(f"Message: {alert.message}")
        results = notifier.send(alert)
        for r in results:
            status = "SENT" if r.sent else ("NOT CONFIGURED" if not r.configured else "FAILED")
            print(f"  [{r.channel}] {status} — {r.detail}")
        delivery_log.append(alert, results)

    section("VERIFY PERSISTENCE")
    lines = DELIVERY_LOG_PATH.read_text().splitlines()
    print(f"Delivery log now has {len(lines)} real record(s) at {DELIVERY_LOG_PATH}")

    section("DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
