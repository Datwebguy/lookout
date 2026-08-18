"""Autonomous scheduler — the source of Lookout's autonomy (PRD G1 / FR2).

Iterates every registered site on its own interval and pulls real FortyGuard signals for
each, with no human prompt triggering an individual tick. `run_forever()` is the real
deployment loop; `tick()` runs exactly one autonomous pass and is what proof/demo scripts
call directly instead of waiting out a real interval.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Callable

from fortyguard import FortyGuardClient

from .cache import SignalCache
from .signals import (
    SignalUnavailableError,
    area_weighted_mean_temperature,
    duration_signal,
    historical_analog_forward,
    most_recent_available_date,
)
from .sites import Site


@dataclass
class SiteSignals:
    site_id: str
    site_name: str
    computed_at: str  # real UTC timestamp of this autonomous read
    anchor_date: str
    anchor_hour: str
    target_hour: str
    now_celsius: float
    baseline_now_celsius: float  # "normal for this site, this hour"
    forward_projected_celsius: float
    forward_anomaly_celsius: float
    exceedance_hours: float
    exceedance_window_days: int
    from_cache: bool = False


def compute_site_signals(
    client: FortyGuardClient,
    site: Site,
    *,
    anchor_date: str,
    anchor_hour: str,
    target_hour: str,
    baseline_years: list[int],
    exceedance_window_days: int = 7,
    threshold: float = 35.0,
) -> SiteSignals:
    """Every real FortyGuard call this site needs for one autonomous decision: current
    reading, historical-analog forward projection (which also yields the "normal for this
    hour" baseline), and a duration read. Raises `SignalUnavailableError` if any real call
    comes back empty — the caller decides whether that sidelines just this site or the tick.
    """
    now_temp = area_weighted_mean_temperature(client, site.site_polygon, anchor_date, anchor_hour)

    forward = historical_analog_forward(
        client,
        site.site_polygon,
        target_date=anchor_date,
        target_hour_time=target_hour,
        anchor_date=anchor_date,
        anchor_hour_time=anchor_hour,
        years=baseline_years,
        actual_anchor_celsius=now_temp,  # reuse — don't re-query the same real value
    )

    window_start = (date.fromisoformat(anchor_date) - timedelta(days=exceedance_window_days - 1)).isoformat()
    exceedance_hours = duration_signal(
        client, site.site_polygon, window_start, anchor_date,
        threshold=threshold, direction="above", analytic_type="exceedance",
    )

    return SiteSignals(
        site_id=site.id,
        site_name=site.name,
        computed_at=datetime.now(timezone.utc).isoformat(),
        anchor_date=anchor_date,
        anchor_hour=anchor_hour,
        target_hour=target_hour,
        now_celsius=now_temp,
        baseline_now_celsius=forward.baseline_anchor_celsius,
        forward_projected_celsius=forward.projected_celsius,
        forward_anomaly_celsius=forward.anomaly_celsius,
        exceedance_hours=exceedance_hours,
        exceedance_window_days=exceedance_window_days,
    )


class Scheduler:
    def __init__(
        self,
        client: FortyGuardClient,
        sites: list[Site],
        cache: SignalCache,
        *,
        baseline_years: list[int],
        target_hour: str = "18:00",
        interval_seconds: int = 3600,
        on_signals: Callable[[Site, SiteSignals], None] | None = None,
        on_error: Callable[[Site, Exception], None] | None = None,
    ):
        self.client = client
        self.sites = sites
        self.cache = cache
        self.baseline_years = baseline_years
        self.target_hour = target_hour
        self.interval_seconds = interval_seconds
        self.on_signals = on_signals or (lambda site, signals: None)
        self.on_error = on_error or (lambda site, exc: None)

    def tick(self) -> list[SiteSignals]:
        """One autonomous pass over every registered site. Real calls; per-site-per-hour
        cached to respect credits; one site's `SignalUnavailableError` is reported via
        `on_error` and does not stop the rest of the loop.
        """
        anchor_date = most_recent_available_date().isoformat()
        anchor_hour = "14:00"  # fixed real hour used for the anchor reading each tick
        hour_bucket = f"{anchor_date}T{anchor_hour[:2]}"

        results: list[SiteSignals] = []
        for site in self.sites:
            cache_key = self.cache.key(site.id, hour_bucket)
            cached = self.cache.get(cache_key)
            if cached is not None:
                signals = SiteSignals(**{**cached, "from_cache": True})
                results.append(signals)
                self.on_signals(site, signals)
                continue

            try:
                signals = compute_site_signals(
                    self.client,
                    site,
                    anchor_date=anchor_date,
                    anchor_hour=anchor_hour,
                    target_hour=self.target_hour,
                    baseline_years=self.baseline_years,
                )
            except SignalUnavailableError as exc:
                self.on_error(site, exc)
                continue

            self.cache.set(cache_key, asdict(signals))
            results.append(signals)
            self.on_signals(site, signals)

        return results

    def run_forever(self) -> None:
        """The real autonomous loop — no human prompt triggers a tick."""
        while True:
            self.tick()
            time.sleep(self.interval_seconds)
