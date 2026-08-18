"""Milestone 1 — live API proof.

Real FortyGuard calls only. No mocked data. Run with:
    python scripts/milestone1_live_proof.py
"""

from __future__ import annotations

import json
import sys

from dotenv import load_dotenv

load_dotenv()

from fortyguard import FortyGuardClient  # noqa: E402
from fortyguard.exceptions import FortyGuardError  # noqa: E402


def polygon(lon_min: float, lat_min: float, lon_max: float, lat_max: float) -> dict:
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [lon_min, lat_min],
                            [lon_max, lat_min],
                            [lon_max, lat_max],
                            [lon_min, lat_max],
                            [lon_min, lat_min],
                        ]
                    ],
                },
            }
        ],
    }


PHOENIX_A = polygon(-112.08, 33.44, -112.06, 33.46)
PHOENIX_B = polygon(-112.03, 33.44, -112.01, 33.46)  # shifted ~4.6km east

TODAY = "2026-08-18"
PAST_HOUR_TODAY = "10:00"   # already elapsed in Phoenix local time (UTC-7) — safe historical read
FUTURE_HOUR_TODAY = "18:00"  # ~4h15m ahead of current Phoenix local time — forecast probe


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

    # --- Test A: real tcm read for polygon A, past hour today -------------
    section("TEST A — tcm snapshot, Polygon A, past hour today (baseline real read)")
    try:
        resp_a = client.create_heatmap(
            polygon_aoi=PHOENIX_A,
            start_date=TODAY,
            start_time=PAST_HOUR_TODAY,
            filter_type=1,
            granularity=100,
            analytic_type="tcm",
        )
    except FortyGuardError as exc:
        print(f"FAIL (loud): Test A call failed — {exc}", file=sys.stderr)
        return 1

    print("activity_id:", resp_a["activity_id"])
    stats_a = resp_a["result"].get("stats_data")
    print("stats_data:", json.dumps(stats_a, indent=2)[:2000])

    tiles_a = resp_a["result"].get("tiles") or resp_a["result"].get("features")
    if tiles_a:
        sample = tiles_a[0]
        print("\nSample tile properties (Polygon A):")
        print(json.dumps(sample.get("properties", sample), indent=2))
        if "average_temperature" not in sample.get("properties", sample):
            print(
                "WARNING: 'average_temperature' key not found on tile — "
                "field-path assumption from memory.md may be wrong.",
                file=sys.stderr,
            )
    else:
        print("WARNING: no tiles/features array found in result — inspect full payload below.")
        print(json.dumps(resp_a["result"], indent=2)[:3000])

    # --- Test B: move the polygon, confirm the value actually changes -----
    section("TEST B — tcm snapshot, Polygon B (moved ~4.6km east), same hour")
    try:
        resp_b = client.create_heatmap(
            polygon_aoi=PHOENIX_B,
            start_date=TODAY,
            start_time=PAST_HOUR_TODAY,
            filter_type=1,
            granularity=100,
            analytic_type="tcm",
        )
    except FortyGuardError as exc:
        print(f"FAIL (loud): Test B call failed — {exc}", file=sys.stderr)
        return 1

    print("activity_id:", resp_b["activity_id"])
    stats_b = resp_b["result"].get("stats_data")
    print("stats_data:", json.dumps(stats_b, indent=2)[:2000])

    n_a = (stats_a or {}).get("n_cells", 0)
    n_b = (stats_b or {}).get("n_cells", 0)
    print("\nPolygon A stats_data vs Polygon B stats_data:")
    print("  A:", stats_a, " n_cells:", n_a)
    print("  B:", stats_b, " n_cells:", n_b)
    if n_a == 0 and n_b == 0:
        print(
            "INCONCLUSIVE: both polygons returned 0 cells — cannot confirm "
            "values differ by location yet.",
            file=sys.stderr,
        )
    elif stats_a == stats_b:
        print("WARNING: identical stats_data for two different locations.", file=sys.stderr)
    else:
        print("CONFIRMED: values differ when the polygon moves.")

    # --- Test C: forecast probe — future start_time on today's date -------
    section("TEST C — forecast probe: future start_time on TODAY's date")
    try:
        resp_c = client.create_heatmap(
            polygon_aoi=PHOENIX_A,
            start_date=TODAY,
            start_time=FUTURE_HOUR_TODAY,
            filter_type=1,
            granularity=100,
            analytic_type="tcm",
        )
        n_c = (resp_c["result"].get("stats_data") or {}).get("n_cells", 0)
        print("activity_id:", resp_c["activity_id"])
        print("stats_data:", json.dumps(resp_c["result"].get("stats_data"), indent=2)[:2000])
        if n_c > 0:
            print("\nFORECAST RESULT: returned real cell data for a future start_time today -> LIVE FORECAST WORKS")
        else:
            print("\nFORECAST RESULT: call completed but returned 0 cells -> INCONCLUSIVE (not a confirmed pass)")
    except FortyGuardError as exc:
        print(f"\nFORECAST RESULT: call failed/errored -> {exc}")
        print("FORECAST RESULT: NO live forecast — must use historical-analog fallback.")

    def probe(label: str, start_date: str, start_time: str, poly=PHOENIX_A) -> None:
        section(f"{label} — start_date={start_date} start_time={start_time}")
        try:
            resp = client.create_heatmap(
                polygon_aoi=poly,
                start_date=start_date,
                start_time=start_time,
                filter_type=1,
                granularity=100,
                analytic_type="tcm",
            )
        except FortyGuardError as exc:
            print(f"FAIL (loud): call failed — {exc}", file=sys.stderr)
            return
        result = resp["result"]
        stats = result.get("stats_data")
        tiles = result.get("map_data", {}).get("features", [])
        print("activity_id:", resp["activity_id"])
        print("stats_data keys:", list((stats or {}).keys()))
        print("tile count:", len(tiles))
        if tiles:
            print("Sample tile properties:")
            print(json.dumps(tiles[0].get("properties", tiles[0]), indent=2))
            temp_stats = (stats or {}).get("temperature_stats")
            if temp_stats:
                print("temperature_stats:", json.dumps(temp_stats, indent=2))
        else:
            print("-> NO DATA for this date/time.")

    # --- Test D: known historical date (diagnostic — isolate today's-data-latency vs broken request)
    probe("TEST D — diagnostic: known-historical date (2024-07-15)", "2024-07-15", "14:00")

    # --- Test E/F: find the recency boundary of available data
    probe("TEST E — yesterday, Polygon A", "2026-08-17", "10:00", PHOENIX_A)
    probe("TEST F — 3 days ago", "2026-08-15", "10:00")
    probe("TEST G — 7 days ago", "2026-08-11", "10:00")

    # --- Test H: real location-sensitivity check on a date that HAS data
    probe("TEST H — yesterday, Polygon B (moved ~4.6km east)", "2026-08-17", "10:00", PHOENIX_B)

    section("DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
