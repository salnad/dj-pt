from __future__ import annotations

from djpt.audio.calibration import derive_bands
from djpt.audio.scoring import conciseness_penalty


def test_conciseness_penalty_prefers_shorter_code() -> None:
    short_code = 'note("c4").s("sine")'
    long_code = '\n'.join(
        [
            '$: note("c4 e4 g4 b4").s("sawtooth").room(0.3).delay(0.2).delayfeedback(0.5)',
            '$: note("c3").s("square").slow(2).gain(0.7).room(0.4).delay(0.1)',
            '$: note("g2").s("triangle").fast(4).pan(0.2).room(0.5).delay(0.25)',
        ]
    )

    assert conciseness_penalty(short_code) < conciseness_penalty(long_code)


def test_calibration_bands_are_ordered() -> None:
    bands = derive_bands(
        self_scores=[0.95, 0.97, 0.99],
        perturbed_scores=[0.62, 0.7, 0.74],
        unrelated_scores=[0.12, 0.2, 0.24],
    )

    assert bands.excellent > bands.usable > bands.poor
