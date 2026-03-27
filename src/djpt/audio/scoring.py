from __future__ import annotations

from djpt.audio.utils import clamp01
from djpt.schemas import ScoreBreakdown, SimilarityReport


DEFAULT_WEIGHTS = {
    "chroma": 0.35,
    "mfcc": 0.25,
    "onset": 0.20,
    "tempo": 0.10,
    "duration": 0.05,
    "loudness": 0.05,
}


def conciseness_penalty(code: str) -> float:
    char_penalty = min(len(code) / 800.0, 1.0)
    line_penalty = min(max(code.count("\n"), 0) / 20.0, 1.0)
    chain_penalty = min(code.count(".") / 30.0, 1.0)
    repeated_modulation_penalty = min(
        code.count("slow(") + code.count("fast("),
        10,
    ) / 10.0
    return (
        (char_penalty * 0.40)
        + (line_penalty * 0.20)
        + (chain_penalty * 0.20)
        + (repeated_modulation_penalty * 0.20)
    )


def build_similarity_report(
    *,
    chroma: float,
    mfcc: float,
    onset: float,
    tempo: float,
    duration: float,
    loudness: float,
    code: str | None = None,
    weights: dict[str, float] | None = None,
    notes: list[str] | None = None,
) -> SimilarityReport:
    weights = weights or DEFAULT_WEIGHTS
    breakdown = ScoreBreakdown(
        chroma=clamp01(chroma),
        mfcc=clamp01(mfcc),
        onset=clamp01(onset),
        tempo=clamp01(tempo),
        duration=clamp01(duration),
        loudness=clamp01(loudness),
        embedding=None,
        conciseness=0.0 if code is None else conciseness_penalty(code),
    )
    base_score = (
        breakdown.chroma * weights["chroma"]
        + breakdown.mfcc * weights["mfcc"]
        + breakdown.onset * weights["onset"]
        + breakdown.tempo * weights["tempo"]
        + breakdown.duration * weights["duration"]
        + breakdown.loudness * weights["loudness"]
    )
    adjusted = max(base_score - (breakdown.conciseness * 0.10), 0.0)
    return SimilarityReport(
        total_score=adjusted,
        breakdown=breakdown,
        notes=notes
        or [
            "Composite score uses reference-based similarity metrics.",
            "Conciseness is a soft penalty applied after audio similarity aggregation.",
        ],
    )
