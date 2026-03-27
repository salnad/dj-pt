from djpt.audio.calibration import derive_bands


def test_derive_bands_orders_quality_thresholds() -> None:
    bands = derive_bands(
        self_scores=[0.96, 0.93, 0.95],
        perturbed_scores=[0.72, 0.70, 0.74],
        unrelated_scores=[0.22, 0.18, 0.25],
    )

    assert bands.excellent > bands.usable > bands.poor
