from __future__ import annotations

import numpy as np

from djpt.audio.metrics import (
    chroma_dtw_distance,
    duration_penalty,
    loudness_penalty,
    onset_envelope_distance,
    tempo_penalty,
)


def test_basic_penalties_are_ordered() -> None:
    assert duration_penalty(4.0, 4.0) == 0.0
    assert tempo_penalty(120.0, 120.0) == 0.0
    assert loudness_penalty(0.2, 0.2) == 0.0


def test_chroma_distance_is_low_for_identical_arrays() -> None:
    chroma = np.eye(12, 12)
    assert chroma_dtw_distance(chroma, chroma) < 0.01


def test_onset_distance_is_low_for_identical_arrays() -> None:
    onset = np.array([0.0, 0.4, 0.1, 0.8, 0.2])
    assert onset_envelope_distance(onset, onset) < 0.01
