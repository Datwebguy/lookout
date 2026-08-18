"""Signals layer — the only place besides `fortyguard/` that reasons about temperature data.

Every function here makes real `FortyGuardClient` calls and fails loudly (raises
`SignalUnavailableError`) rather than substituting fake data, per the golden rule in
memory.md. Nothing in this module invents a temperature.

Confirmed live against the real API (2026-08-18, see handoff.md):
- `tcm` tiles: `properties.average_temperature` (°C), real per-tile `geometry` (Polygon).
- `exceedance`/`persistence` tiles: `properties.value` (hours), same per-tile `geometry`.
- FortyGuard has NO live forecast: today's calendar date returns zero tiles at any hour.
  All "ahead" reasoning here uses historical analog, never a live forecast call.
- The most recent 1-2 calendar days can be unreliable even when older dates work
  consistently (see `most_recent_available_date`'s docstring) — use a real safety margin.
- There is a real minimum query-area threshold: a small worksite polygon (~200m-1.5km per
  side) submitted directly as the query AOI returns zero tiles even on dates that are
  otherwise reliable; a ~2km box works consistently. So every function here submits a
  bounding query AOI sized above that threshold, and area-weights the *result* against the
  actual (possibly much smaller) site polygon — exactly the "worksite smaller than a tile"
  pattern CLAUDE.md describes, just with the minimum now grounded in a real measurement
  rather than a guess.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, timedelta

from shapely.geometry import shape

from fortyguard import FortyGuardClient
from fortyguard.exceptions import FortyGuardError


class SignalUnavailableError(RuntimeError):
    """Raised when FortyGuard returns no usable data. Never caught to substitute fake data."""


# Empirically verified live (2026-08-18): a ~1.5km-per-side query AOI returned zero tiles on
# a date otherwise reliable (2024-07-15); a ~2km-per-side AOI returned 367 real tiles on that
# same date, and consistently across many other dates/times. Half-width in km, so this yields
# a ~2km square.
MIN_QUERY_HALF_WIDTH_KM = 1.0


def _site_shape(site_polygon: dict):
    return shape(site_polygon["features"][0]["geometry"])


def _bounding_query_aoi(site_geom, half_width_km: float = MIN_QUERY_HALF_WIDTH_KM) -> dict:
    """A GeoJSON query AOI centered on `site_geom`'s centroid, sized above FortyGuard's
    empirically observed minimum query-area threshold. This is what gets submitted to the
    API — the real (possibly much smaller) site polygon is only used afterwards, to
    area-weight which returned tiles actually count and by how much.
    """
    centroid = site_geom.centroid
    lat_rad = math.radians(centroid.y)
    dlat = half_width_km / 110.574
    dlon = half_width_km / (111.320 * math.cos(lat_rad))
    lon_min, lon_max = centroid.x - dlon, centroid.x + dlon
    lat_min, lat_max = centroid.y - dlat, centroid.y + dlat
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


def _area_weighted(features: list[dict], site_geom, value_key: str) -> float:
    """Area-weight `properties[value_key]` across every tile that overlaps `site_geom`.

    A worksite can be smaller than a tile, or straddle several — never nearest-tile.
    """
    weighted_sum = 0.0
    total_overlap = 0.0
    for f in features:
        tile_geom = shape(f["geometry"])
        overlap = tile_geom.intersection(site_geom).area
        if overlap <= 0:
            continue
        weighted_sum += f["properties"][value_key] * overlap
        total_overlap += overlap
    if total_overlap == 0:
        raise SignalUnavailableError(
            "FortyGuard returned tiles, but none overlap the site polygon geometry — "
            "check the site polygon and query AOI are in the same place."
        )
    return weighted_sum / total_overlap


def area_weighted_mean_temperature(
    client: FortyGuardClient,
    site_polygon: dict,
    query_date: str,
    query_time: str,
    granularity: int = 100,
) -> float:
    """Real `tcm` snapshot for a site, area-weighted over every tile overlapping the site.

    Submits a bounding query AOI sized above FortyGuard's minimum query-area threshold
    (see `_bounding_query_aoi`), then weights the returned tiles by their overlap with the
    actual `site_polygon` — so a worksite far smaller than that AOI still gets a real,
    site-specific reading, not the AOI's average.

    `query_date` should be at least a few days before today — FortyGuard's most recent 1-2
    calendar days can be unreliable even when older dates work consistently (verified live;
    see memory.md Gotchas / `most_recent_available_date`). Raises `SignalUnavailableError`
    if FortyGuard returns no tiles.
    """
    site_geom = _site_shape(site_polygon)
    query_aoi = _bounding_query_aoi(site_geom)
    try:
        resp = client.create_heatmap(
            polygon_aoi=query_aoi,
            start_date=query_date,
            start_time=query_time,
            filter_type=1,
            granularity=granularity,
            analytic_type="tcm",
        )
    except FortyGuardError as exc:
        raise SignalUnavailableError(f"tcm call failed for {query_date} {query_time}: {exc}") from exc

    features = resp["result"].get("map_data", {}).get("features", [])
    if not features:
        raise SignalUnavailableError(
            f"FortyGuard returned zero tiles for {query_date} {query_time}. "
            "If query_date is today or very recent, this is expected — see memory.md Gotchas."
        )
    return _area_weighted(features, site_geom, "average_temperature")


@dataclass
class BaselineResult:
    mean_celsius: float
    samples: list[tuple[int, float]] = field(default_factory=list)  # (year, temp) that succeeded
    missing_years: list[int] = field(default_factory=list)  # years with no data — reported, not hidden


def historical_baseline(
    client: FortyGuardClient,
    site_polygon: dict,
    month_day: str,  # "MM-DD"
    hour_time: str,  # "HH:MM"
    years: list[int],
    granularity: int = 100,
) -> BaselineResult:
    """"Normal for this site, this hour" — real area-weighted mean averaged across `years`
    on the same calendar day. Some years may have no data (e.g. a specific date/hour gap);
    those are recorded in `missing_years`, not silently dropped from view.
    """
    samples: list[tuple[int, float]] = []
    missing: list[int] = []
    for year in years:
        query_date = f"{year}-{month_day}"
        try:
            temp = area_weighted_mean_temperature(client, site_polygon, query_date, hour_time, granularity)
            samples.append((year, temp))
        except SignalUnavailableError:
            missing.append(year)
    if not samples:
        raise SignalUnavailableError(
            f"No historical data for any of {years} on {month_day} at {hour_time}."
        )
    mean = sum(t for _, t in samples) / len(samples)
    return BaselineResult(mean_celsius=mean, samples=samples, missing_years=missing)


@dataclass
class ForwardProjection:
    projected_celsius: float
    baseline_target_celsius: float
    baseline_anchor_celsius: float
    actual_anchor_celsius: float
    anomaly_celsius: float


def historical_analog_forward(
    client: FortyGuardClient,
    site_polygon: dict,
    target_date: str,  # "YYYY-MM-DD" — e.g. today; only its month/day drive the baseline curve
    target_hour_time: str,  # the future hour-of-day being projected
    anchor_date: str,  # most recent real reading, e.g. yesterday
    anchor_hour_time: str,  # hour of that most recent real reading
    years: list[int],
    granularity: int = 100,
) -> ForwardProjection:
    """Projects a likely temperature at `target_hour_time` since FortyGuard has no live
    forecast (verified live — see memory.md). Uses climatology + persistence, a standard
    nowcasting technique: baseline(target_hour) + (today's actual anomaly at the anchor hour).

    Every number in this projection is a real FortyGuard read; only the addition is a
    computed heuristic, not a fabricated value. `anomaly` captures "today is running N
    degrees above/below normal," carried forward to the target hour's normal.
    """
    target_month_day = target_date[5:]  # "MM-DD"
    anchor_month_day = anchor_date[5:]
    baseline_target = historical_baseline(client, site_polygon, target_month_day, target_hour_time, years, granularity)
    baseline_anchor = historical_baseline(client, site_polygon, anchor_month_day, anchor_hour_time, years, granularity)
    actual_anchor = area_weighted_mean_temperature(client, site_polygon, anchor_date, anchor_hour_time, granularity)

    anomaly = actual_anchor - baseline_anchor.mean_celsius
    projected = baseline_target.mean_celsius + anomaly

    return ForwardProjection(
        projected_celsius=projected,
        baseline_target_celsius=baseline_target.mean_celsius,
        baseline_anchor_celsius=baseline_anchor.mean_celsius,
        actual_anchor_celsius=actual_anchor,
        anomaly_celsius=anomaly,
    )


def duration_signal(
    client: FortyGuardClient,
    site_polygon: dict,
    start_date: str,
    end_date: str,
    threshold: float = 35.0,
    direction: str = "above",
    analytic_type: str = "exceedance",  # "exceedance" or "persistence"
    granularity: int = 100,
) -> float:
    """Real area-weighted hours-past-threshold (`exceedance`) or longest continuous run
    (`persistence`) over [start_date, end_date] (<=31 days; `end_date` should be a few days
    before today — see `most_recent_available_date`). Units are hours
    (`stats_data.units == "hour"`, confirmed live). Submits a bounding query AOI sized above
    FortyGuard's minimum query-area threshold (see `area_weighted_mean_temperature`), then
    weights by overlap with the real `site_polygon`.
    """
    if analytic_type not in ("exceedance", "persistence"):
        raise ValueError("analytic_type must be 'exceedance' or 'persistence'")
    site_geom = _site_shape(site_polygon)
    query_aoi = _bounding_query_aoi(site_geom)
    try:
        resp = client.create_heatmap(
            polygon_aoi=query_aoi,
            start_date=start_date,
            end_date=end_date,
            filter_type=4,
            granularity=granularity,
            analytic_type=analytic_type,
            threshold=threshold,
            direction=direction,
        )
    except FortyGuardError as exc:
        raise SignalUnavailableError(
            f"{analytic_type} call failed for {start_date}..{end_date}: {exc}"
        ) from exc

    features = resp["result"].get("map_data", {}).get("features", [])
    if not features:
        raise SignalUnavailableError(f"FortyGuard returned zero tiles for {start_date}..{end_date}.")
    return _area_weighted(features, site_geom, "value")


def most_recent_available_date(today: date | None = None, safety_margin_days: int = 3) -> date:
    """A date that should reliably have real FortyGuard data.

    Today's calendar date is always empty (verified live). Live testing also showed
    "yesterday" is NOT reliably available: it returned real tiles multiple times earlier
    in a session, then returned empty on a later retry of the identical query, while dates
    3+ days old stayed consistently available throughout. So this defaults to a 3-day
    margin rather than 1 — treat anything newer than that as potentially still settling.
    Callers needing the freshest possible reading should still try progressively older
    dates and handle `SignalUnavailableError`, rather than assuming a fixed cutoff.
    """
    today = today or date.today()
    return today - timedelta(days=safety_margin_days)
