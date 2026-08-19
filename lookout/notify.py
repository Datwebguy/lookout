"""Real alert delivery channels (Milestone 6; PRD FR5).

Posts the real alert message to whichever real webhook(s) are configured via env vars.
Never claims a "sent" status that didn't actually happen — an unconfigured or failed
channel is reported as exactly that, not silently skipped or faked as delivered.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import requests

from .proactive import ProactiveAlert


@dataclass
class DeliveryResult:
    channel: str
    configured: bool
    sent: bool
    detail: str


def _post_slack(url: str, message: str) -> DeliveryResult:
    try:
        resp = requests.post(url, json={"text": message}, timeout=10)
    except requests.RequestException as exc:
        return DeliveryResult("slack", True, False, f"request failed: {exc}")
    if resp.ok:
        return DeliveryResult("slack", True, True, f"HTTP {resp.status_code}")
    return DeliveryResult("slack", True, False, f"HTTP {resp.status_code}: {resp.text[:200]}")


def _post_discord(url: str, message: str) -> DeliveryResult:
    try:
        resp = requests.post(url, json={"content": message}, timeout=10)
    except requests.RequestException as exc:
        return DeliveryResult("discord", True, False, f"request failed: {exc}")
    if resp.ok:
        return DeliveryResult("discord", True, True, f"HTTP {resp.status_code}")
    return DeliveryResult("discord", True, False, f"HTTP {resp.status_code}: {resp.text[:200]}")


class WebhookNotifier:
    """Reads SLACK_WEBHOOK_URL / DISCORD_WEBHOOK_URL from the environment by default.
    A channel with no URL configured is still reported in the results, marked
    `configured=False` — never silently dropped.
    """

    def __init__(self, slack_url: str | None = None, discord_url: str | None = None):
        self.slack_url = slack_url if slack_url is not None else os.getenv("SLACK_WEBHOOK_URL")
        self.discord_url = discord_url if discord_url is not None else os.getenv("DISCORD_WEBHOOK_URL")

    def send(self, alert: ProactiveAlert) -> list[DeliveryResult]:
        results: list[DeliveryResult] = []
        if self.slack_url:
            results.append(_post_slack(self.slack_url, alert.message))
        else:
            results.append(DeliveryResult("slack", False, False, "SLACK_WEBHOOK_URL not set"))
        if self.discord_url:
            results.append(_post_discord(self.discord_url, alert.message))
        else:
            results.append(DeliveryResult("discord", False, False, "DISCORD_WEBHOOK_URL not set"))
        return results


class DeliveryLog:
    """Real, append-only record of every delivery attempt and its real outcome."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def append(self, alert: ProactiveAlert, results: list[DeliveryResult]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "logged_at": datetime.now(timezone.utc).isoformat(),
            "alert": asdict(alert),
            "delivery": [asdict(r) for r in results],
        }
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
