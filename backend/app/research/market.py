from __future__ import annotations

import math
from datetime import datetime
from decimal import Decimal
from statistics import median
from typing import Sequence


def percentile(values: Sequence[float], p: float) -> float:
    """Linear-interpolated percentile for a sequence of floats."""
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * min(max(p, 0.0), 1.0)
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    fraction = position - low
    return ordered[low] + (ordered[high] - ordered[low]) * fraction


def robust_sigma(values: Sequence[float]) -> float:
    """Median-absolute-deviation based sigma; resistant to outliers."""
    if len(values) < 2:
        return 0.0
    centre = median(values)
    deviations = [abs(value - centre) for value in values]
    return 1.4826 * median(deviations)


def ols_slope(points: Sequence[tuple[float, float]]) -> float:
    """Simple least-squares slope; returns 0 when there is no spread in x."""
    n = len(points)
    if n < 3:
        return 0.0
    mean_x = sum(x for x, _ in points) / n
    mean_y = sum(y for _, y in points) / n
    denominator = sum((x - mean_x) ** 2 for x, _ in points)
    if denominator == 0:
        return 0.0
    return sum((x - mean_x) * (y - mean_y) for x, y in points) / denominator


def estimate_likely_price(
    observations: Sequence[tuple[datetime, Decimal]],
    *,
    horizon_days: float = 1.0,
    window: int = 12,
) -> dict[str, object]:
    """
    Estimate the next plausible sell price from a history of observed prices.

    Uses a robust recent median, a short trend from ordinary least squares,
    and clamps the prediction inside the historical 10th-90th percentile band.
    Confidence grows with sample count and shrinks with relative volatility.
    """
    if not observations:
        return {
            "estimated": None,
            "confidence": 0.0,
            "volatility": 0.0,
            "trend_pct_per_day": 0.0,
            "sample_count": 0,
        }

    ordered = sorted(observations, key=lambda pair: pair[0])
    times = [moment for moment, _ in ordered]
    values = [float(price) for _, price in ordered]

    centre = median(values)
    sigma = robust_sigma(values)
    recent = values[-max(2, window):]
    recent_times = times[-max(2, window):]
    recent_centre = median(recent)

    origin = recent_times[0]
    x_values = [(moment - origin).total_seconds() / 86400.0 for moment in recent_times]
    slope = ols_slope(list(zip(x_values, recent)))

    lower = percentile(values, 0.10)
    upper = percentile(values, 0.90)
    predicted = recent_centre + slope * horizon_days
    predicted = min(max(predicted, lower), upper)

    sample_count = len(values)
    base = 0.20 + 0.55 * (1.0 - math.exp(-sample_count / 12.0))
    volatility_penalty = 0.35 * min(1.0, sigma / max(abs(centre), 1e-9))
    confidence = min(0.95, max(0.05, base - volatility_penalty))
    trend_pct = slope / max(abs(recent_centre), 1e-9) * 100.0

    return {
        "estimated": Decimal(str(round(predicted, 6))),
        "confidence": round(confidence, 4),
        "volatility": round(sigma / max(abs(centre), 1e-9), 6),
        "trend_pct_per_day": round(trend_pct, 4),
        "sample_count": sample_count,
    }
