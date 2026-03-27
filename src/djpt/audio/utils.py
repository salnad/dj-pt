from __future__ import annotations

import math


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def mean_or_zero(values: list[float]) -> float:
    if not values:
        return 0.0
    return float(sum(values) / len(values))


def gaussian_similarity(distance: float, sigma: float) -> float:
    sigma = max(float(sigma), 1e-9)
    return math.exp(-((float(distance) ** 2) / (2.0 * sigma**2)))
