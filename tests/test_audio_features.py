from __future__ import annotations

import numpy as np
import soundfile as sf

from djpt.audio.features import analyze_audio
from djpt.config import AppConfig


def test_analyze_audio_extracts_basic_features(tmp_path):
    sample_rate = 32000
    seconds = 1.0
    times = np.linspace(0, seconds, int(sample_rate * seconds), endpoint=False)
    audio = 0.2 * np.sin(2 * np.pi * 440 * times)
    audio_path = tmp_path / "tone.wav"
    sf.write(audio_path, audio, sample_rate)

    config = AppConfig.from_env(tmp_path).model_copy(
        update={
            "workspace_root": tmp_path,
            "renderer_root": tmp_path / "renderer",
            "prompts_root": tmp_path / "prompts",
            "benchmarks_root": tmp_path / "benchmarks",
            "runs_root": tmp_path / "runs",
        }
    ).ensure_directories()

    analysis = analyze_audio(audio_path, config=config)

    assert analysis.duration_seconds > 0.9
    assert analysis.sample_rate == config.default_sample_rate
    assert analysis.rms > 0
    assert analysis.normalized_path is not None
    assert analysis.normalized_path.exists()
    assert len(analysis.chroma_mean) == 12
    assert len(analysis.mfcc_mean) == 13
