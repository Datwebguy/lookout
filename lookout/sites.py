"""Registered worker sites — the list the autonomous scheduler iterates on its own."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .geo import square_polygon

# A typical worksite footprint, per CLAUDE.md ("a few hundred meters per side").
DEFAULT_SITE_HALF_WIDTH_KM = 0.075  # ~150m across


@dataclass
class WorkerProfile:
    role: str
    shift_hours: str  # e.g. "06:00-14:00"
    risk_flags: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class Site:
    id: str
    name: str
    lat: float
    lon: float
    worker_profile: WorkerProfile
    site_polygon: dict | None = None  # real small worksite footprint; derived if omitted
    # Optional per-site alert channel override. None means "use the server's default
    # SLACK_WEBHOOK_URL / DISCORD_WEBHOOK_URL" (see lookout/notify.py).
    slack_webhook_url: str | None = None
    discord_webhook_url: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.worker_profile, dict):
            self.worker_profile = WorkerProfile(**self.worker_profile)
        if self.site_polygon is None:
            self.site_polygon = square_polygon(self.lon, self.lat, DEFAULT_SITE_HALF_WIDTH_KM)


def load_sites(path: str | Path) -> list[Site]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"No registered-sites file at {path}")
    raw = json.loads(path.read_text())
    return [Site(**s) for s in raw]


def save_sites(sites: list[Site], path: str | Path) -> None:
    payload = [
        {
            "id": s.id,
            "name": s.name,
            "lat": s.lat,
            "lon": s.lon,
            "worker_profile": asdict(s.worker_profile),
            "site_polygon": s.site_polygon,
            "slack_webhook_url": s.slack_webhook_url,
            "discord_webhook_url": s.discord_webhook_url,
        }
        for s in sites
    ]
    Path(path).write_text(json.dumps(payload, indent=2))
