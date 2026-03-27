from __future__ import annotations

from pathlib import Path

from djpt.audio.features import analyze_audio
from djpt.audio.metrics import compare_analyses
from djpt.config import AppConfig
from djpt.schemas import AudioAnalysis, SimilarityReport


def compare_audio(
    target: str | Path | AudioAnalysis,
    candidate_path: str | Path,
    *,
    code: str | None = None,
    config: AppConfig | None = None,
) -> SimilarityReport:
    target_analysis = target if isinstance(target, AudioAnalysis) else analyze_audio(target, config=config)
    candidate_analysis = analyze_audio(candidate_path, config=config)
    return compare_analyses(target_analysis, candidate_analysis, code=code)
