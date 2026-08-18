"""Per-site-per-hour signal cache.

FortyGuard's data is hourly (memory.md), so re-querying the same site within the same
hour wastes real credits without adding real information. This is a plain JSON file —
adequate for the sprint (architecture.md), and persists across scheduler restarts so a
crash/redeploy doesn't throw away an hour's worth of already-paid-for reads.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class SignalCache:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._data: dict[str, Any] = (
            json.loads(self.path.read_text()) if self.path.exists() else {}
        )

    @staticmethod
    def key(site_id: str, hour_bucket: str) -> str:
        """`hour_bucket` should identify a real calendar hour, e.g. '2026-08-18T14'."""
        return f"{site_id}:{hour_bucket}"

    def has(self, cache_key: str) -> bool:
        return cache_key in self._data

    def get(self, cache_key: str) -> Any | None:
        return self._data.get(cache_key)

    def set(self, cache_key: str, value: Any) -> None:
        self._data[cache_key] = value
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, indent=2))
