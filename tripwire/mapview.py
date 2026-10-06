"""Choose where the map starts: centred on the data, zoomed to fit it."""

import math

import numpy as np

MIN_ZOOM = 0.4  # whole world fits in a ~650px-wide map
MAX_ZOOM = 9.0  # one city-sized cluster


def fit_view(lons, lats) -> dict:
    """latitude / longitude / zoom for a deck.gl map showing these points.

    Uses the 1st-99th percentile so one stray point on the far side of the world does not zoom
    everything out. World size at zoom z is 512 * 2**z pixels, so span degrees need
    zoom ~ log2(360 / span).
    """
    lons, lats = np.asarray(lons, dtype=float), np.asarray(lats, dtype=float)
    if lons.size == 0:
        return {"latitude": 20.0, "longitude": 10.0, "zoom": MIN_ZOOM}
    lon_lo, lon_hi = np.percentile(lons, [1, 99])
    lat_lo, lat_hi = np.percentile(lats, [1, 99])
    span = max(lon_hi - lon_lo, (lat_hi - lat_lo) * 1.6, 1e-6)  # maps are wider than tall
    zoom = min(max(math.log2(360 / span) - 0.3, MIN_ZOOM), MAX_ZOOM)
    return {
        "latitude": float((lat_lo + lat_hi) / 2),
        "longitude": float((lon_lo + lon_hi) / 2),
        "zoom": float(zoom),
    }
