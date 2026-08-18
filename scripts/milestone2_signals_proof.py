"""Milestone 2 — signals layer live proof.

Runs every function in lookout/signals.py against the real FortyGuard API for a real
Phoenix worksite polygon. No mocked data; failures are loud. Run with:
    PYTHONPATH=<repo root> python scripts/milestone2_signals_proof.py
"""

from __future__ import annotations

import json
import sys
from datetime import date, timedelta

from dotenv import load_dotenv

load_dotenv()

from fortyguard import FortyGuardClient  # noqa: E402
from fortyguard.exceptions import FortyGuardError  # noqa: E402
from lookout.signals import (  # noqa: E402
    SignalUnavailableError,
    area_weighted_mean_temperature,
    duration_signal,
    historical_analog_forward,
    historical_baseline,
    most_recent_available_date,
)

# A real ~200m x 155m worksite in Phoenix — smaller than several 100m grid tiles, so the
# area-weighted intersection logic is genuinely exercised, not a trivial single-tile lookup.
WORKSITE = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {},
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [-112.0710, 33.4443],
                        [-112.0688, 33.4443],
                        [-112.0688, 33.4457],
                        [-112.0710, 33.4457],
                        [-112.0710, 33.4443],
                    ]
                ],
            },
        }
    ],
}

ANCHOR_DATE = most_recent_available_date()  # 3-day safety margin — see lookout/signals.py docstring
ANCHOR_DATE_STR = ANCHOR_DATE.isoformat()
TODAY_STR = date.today().isoformat()
BASELINE_YEARS = [2023, 2024, 2025]  # trimmed from full 2021-present to bound demo API credits


def section(title: str) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def main() -> int:
    try:
        client = FortyGuardClient()
    except FortyGuardError as exc:
        print(f"FAIL: could not construct client — {exc}", file=sys.stderr)
        return 1

    # --- 1. Area-weighted mean tcm --------------------------------------
    section(f"1. area_weighted_mean_temperature — real worksite, {ANCHOR_DATE_STR} 14:00")
    try:
        temp = area_weighted_mean_temperature(client, WORKSITE, ANCHOR_DATE_STR, "14:00")
        print(f"Area-weighted mean temperature: {temp:.4f} °C")
    except SignalUnavailableError as exc:
        print(f"FAIL (loud): {exc}", file=sys.stderr)
        return 1

    # --- 2. Historical baseline ------------------------------------------
    section("2. historical_baseline — 'normal for this site, this hour' (14:00, past 3 years)")
    try:
        baseline = historical_baseline(client, WORKSITE, ANCHOR_DATE_STR[5:], "14:00", BASELINE_YEARS)
        print(f"Baseline mean: {baseline.mean_celsius:.4f} °C")
        print(f"Samples used: {baseline.samples}")
        print(f"Missing years (no data, reported not hidden): {baseline.missing_years}")
    except SignalUnavailableError as exc:
        print(f"FAIL (loud): {exc}", file=sys.stderr)
        return 1

    # --- 3. Historical-analog forward projection -------------------------
    section("3. historical_analog_forward — project 18:00 TODAY (no live forecast exists)")
    try:
        forward = historical_analog_forward(
            client,
            WORKSITE,
            target_date=TODAY_STR,
            target_hour_time="18:00",
            anchor_date=ANCHOR_DATE_STR,
            anchor_hour_time="14:00",
            years=BASELINE_YEARS,
        )
        print(f"Actual anchor reading ({ANCHOR_DATE_STR} 14:00): {forward.actual_anchor_celsius:.4f} °C")
        print(f"Baseline for anchor hour (normal 14:00):  {forward.baseline_anchor_celsius:.4f} °C")
        print(f"Anomaly (actual - normal):                {forward.anomaly_celsius:+.4f} °C")
        print(f"Baseline for target hour (normal 18:00):  {forward.baseline_target_celsius:.4f} °C")
        print(f"PROJECTED temperature at 18:00 today:     {forward.projected_celsius:.4f} °C")
    except SignalUnavailableError as exc:
        print(f"FAIL (loud): {exc}", file=sys.stderr)
        return 1

    # --- 4. Duration: exceedance + persistence ----------------------------
    section("4. duration_signal — exceedance & persistence, last 7 days, threshold 35°C above")
    window_start = (ANCHOR_DATE - timedelta(days=6)).isoformat()
    try:
        exceedance_hours = duration_signal(
            client, WORKSITE, window_start, ANCHOR_DATE_STR, threshold=35.0, direction="above",
            analytic_type="exceedance",
        )
        print(f"Exceedance ({window_start}..{ANCHOR_DATE_STR}): {exceedance_hours:.2f} hours above 35°C")
    except SignalUnavailableError as exc:
        print(f"FAIL (loud): {exc}", file=sys.stderr)
        return 1

    try:
        persistence_hours = duration_signal(
            client, WORKSITE, window_start, ANCHOR_DATE_STR, threshold=35.0, direction="above",
            analytic_type="persistence",
        )
        print(f"Persistence ({window_start}..{ANCHOR_DATE_STR}): {persistence_hours:.2f} hours longest continuous run above 35°C")
    except SignalUnavailableError as exc:
        print(f"FAIL (loud): {exc}", file=sys.stderr)
        return 1

    section("DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
