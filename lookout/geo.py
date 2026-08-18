"""Small real geometry helpers shared by the signals and sites modules."""

from __future__ import annotations

import math


def square_polygon(lon: float, lat: float, half_width_km: float) -> dict:
    """A GeoJSON square polygon centered on (lon, lat), `half_width_km` from center to edge.

    Real trig-based degree conversion (not a fixed constant) — longitude degrees shrink
    with latitude, so this stays accurate away from the equator.
    """
    lat_rad = math.radians(lat)
    dlat = half_width_km / 110.574
    dlon = half_width_km / (111.320 * math.cos(lat_rad))
    lon_min, lon_max = lon - dlon, lon + dlon
    lat_min, lat_max = lat - dlat, lat + dlat
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
