"""Score calibration helpers."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean

from djpt.audio.utils import clamp01


@dataclass(slots=True)
class CalibrationBands:
    excellent: float
    usable: float
    poor: float


def derive_bands(self_scores: list[float], perturbed_scores: list[float], unrelated_scores: list[float]) -> CalibrationBands:
    if not self_scores or not perturbed_scores or not unrelated_scores:
        raise ValueError("Calibration requires self, perturbed, and unrelated scores.")

    self_mean = mean(self_scores)
    perturbed_mean = mean(perturbed_scores)
    unrelated_mean = mean(unrelated_scores)

    return CalibrationBands(
        excellent=clamp01((self_mean + perturbed_mean) / 2),
        usable=clamp01((perturbed_mean + unrelated_mean) / 2),
        poor=clamp01(unrelated_mean),
    )
