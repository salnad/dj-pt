from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture
def sine_wave_path(tmp_path: Path) -> Path:
    sample_rate = 32000
    seconds = 1.0
    times = np.linspace(0, seconds, int(sample_rate * seconds), endpoint=False)
    audio = 0.2 * np.sin(2 * np.pi * 440 * times)
    audio_path = tmp_path / "tone.wav"
    sf.write(audio_path, audio, sample_rate)
    return audio_path
