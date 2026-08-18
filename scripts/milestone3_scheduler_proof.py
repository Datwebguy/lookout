"""Milestone 3 — autonomous scheduler live proof.

Loads real registered sites, runs one real autonomous tick over all of them (no human
prompt drives an individual site's computation), then ticks again immediately to prove
the per-site-per-hour cache actually avoids re-querying FortyGuard. Run with:
    PYTHONPATH=<repo root> python scripts/milestone3_scheduler_proof.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fortyguard import FortyGuardClient  # noqa: E402
from fortyguard.exceptions import FortyGuardError  # noqa: E402
from lookout.cache import SignalCache  # noqa: E402
from lookout.scheduler import Scheduler, SiteSignals  # noqa: E402
from lookout.sites import Site, load_sites  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
SITES_PATH = REPO_ROOT / "lookout" / "data" / "sites.json"
CACHE_PATH = REPO_ROOT / "lookout" / "data" / "signal_cache.json"

BASELINE_YEARS = [2024, 2025]  # trimmed from full 2021-present to bound demo API credits


def section(title: str) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def print_signals(site: Site, signals: SiteSignals) -> None:
    tag = "[CACHE]" if signals.from_cache else "[LIVE] "
    print(f"{tag} {site.name} ({site.worker_profile.role})")
    print(f"        now={signals.now_celsius:.2f}°C  baseline={signals.baseline_now_celsius:.2f}°C  "
          f"forward({signals.target_hour})={signals.forward_projected_celsius:.2f}°C  "
          f"anomaly={signals.forward_anomaly_celsius:+.2f}°C  "
          f"exceedance({signals.exceedance_window_days}d)={signals.exceedance_hours:.2f}h")


def print_error(site: Site, exc: Exception) -> None:
    print(f"[FAIL]  {site.name}: {exc}", file=sys.stderr)


def main() -> int:
    try:
        client = FortyGuardClient()
    except FortyGuardError as exc:
        print(f"FAIL: could not construct client — {exc}", file=sys.stderr)
        return 1

    sites = load_sites(SITES_PATH)
    print(f"Loaded {len(sites)} registered sites from {SITES_PATH}")
    for s in sites:
        print(f"  - {s.id}: {s.name} ({s.lat}, {s.lon}) — {s.worker_profile.role}")

    cache = SignalCache(CACHE_PATH)
    scheduler = Scheduler(
        client, sites, cache,
        baseline_years=BASELINE_YEARS,
        target_hour="18:00",
        on_signals=print_signals,
        on_error=print_error,
    )

    section("TICK 1 — autonomous pass, real FortyGuard calls expected for every site")
    results_1 = scheduler.tick()
    if len(results_1) != len(sites):
        print(f"FAIL (loud): expected {len(sites)} results, got {len(results_1)}", file=sys.stderr)
        return 1
    if any(r.from_cache for r in results_1):
        print("FAIL: tick 1 should be all-live, but a result came from cache", file=sys.stderr)
        return 1

    section("TICK 2 — same hour, immediately after — should be all cache hits (0 new calls)")
    results_2 = scheduler.tick()
    if not all(r.from_cache for r in results_2):
        print("FAIL (loud): tick 2 expected all cache hits — caching is not working", file=sys.stderr)
        return 1
    print("CONFIRMED: every site served from cache on the second tick — no redundant credits spent.")

    section("DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
