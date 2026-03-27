from __future__ import annotations

import json
from textwrap import dedent

from djpt.schemas import AudioAnalysis


def structured_audio_summary(analysis: AudioAnalysis) -> dict:
    return {
        "path": str(analysis.path),
        "sample_rate_hz": analysis.sample_rate,
        "duration_seconds": round(analysis.duration_seconds, 4),
        "tempo_bpm": None if analysis.tempo_bpm is None else round(analysis.tempo_bpm, 2),
        "estimated_key": analysis.estimated_key,
        "rms": round(analysis.rms, 6),
        "spectral_centroid_hz": round(analysis.spectral_centroid_hz, 3),
        "zero_crossing_rate": round(analysis.zero_crossing_rate, 6),
        "harmonic_ratio": round(analysis.harmonic_ratio, 6),
        "percussive_ratio": round(analysis.percussive_ratio, 6),
        "beat_count": len(analysis.beat_times_seconds),
        "top_pitch_classes": analysis.top_pitch_classes,
    }


def deterministic_theory_description(analysis: AudioAnalysis) -> str:
    tempo = "unknown tempo" if analysis.tempo_bpm is None else f"around {analysis.tempo_bpm:.0f} BPM"
    key = analysis.estimated_key or "unclear tonal center"
    transient = "percussive" if analysis.percussive_ratio > analysis.harmonic_ratio else "harmonic"
    brightness = "bright" if analysis.spectral_centroid_hz >= 2200 else "dark"
    pitch_focus = ", ".join(analysis.top_pitch_classes[:4]) if analysis.top_pitch_classes else "no dominant pitch classes"
    return dedent(
        f"""
        Short audio clip lasting {analysis.duration_seconds:.2f} seconds, {tempo}, tonal center approximately {key}.
        Overall character is {transient} and {brightness}.
        Dominant pitch classes: {pitch_focus}.
        RMS energy {analysis.rms:.4f}; average spectral centroid {analysis.spectral_centroid_hz:.0f} Hz.
        Use concise Strudel code and make tempo/cps assumptions explicit.
        """
    ).strip()


def build_structured_theory_description(
    analysis: AudioAnalysis,
    *,
    llm_description: str | None = None,
) -> dict:
    deterministic = deterministic_theory_description(analysis)
    return {
        "source_path": analysis.path,
        "feature_summary": structured_audio_summary(analysis),
        "deterministic_description": deterministic,
        "llm_description": llm_description,
        "final_description": llm_description or deterministic,
    }


def build_audio_to_theory_prompt(analysis: AudioAnalysis) -> str:
    from pathlib import Path

    prompt_path = Path(__file__).resolve().parents[3] / "prompts" / "audio_to_theory.md"
    template = prompt_path.read_text(encoding="utf-8").strip()
    return template.format(
        feature_summary_json=json.dumps(structured_audio_summary(analysis), indent=2),
    )


def build_structured_description(
    analysis: AudioAnalysis,
    *,
    llm_description: str | None = None,
):
    from djpt.schemas import StructuredTheoryDescription

    payload = build_structured_theory_description(analysis, llm_description=llm_description)
    return StructuredTheoryDescription.model_validate(payload)
