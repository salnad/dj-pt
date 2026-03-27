from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AudioFileMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: Path
    duration_seconds: float
    sample_rate: int
    channels: int
    format_name: str | None = None


class AudioCanonicalizationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_path: Path
    output_path: Path
    sample_rate: int
    channels: int
    duration_seconds: float


class AudioAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: Path
    normalized_path: Path | None = None
    sample_rate: int
    duration_seconds: float
    tempo_bpm: float | None = None
    beat_times_seconds: list[float] = Field(default_factory=list)
    rms: float = 0.0
    spectral_centroid_hz: float = 0.0
    zero_crossing_rate: float = 0.0
    harmonic_ratio: float = 0.0
    percussive_ratio: float = 0.0
    onset_strength_mean: float = 0.0
    onset_density: float = 0.0
    estimated_key: str | None = None
    top_pitch_classes: list[str] = Field(default_factory=list)
    chroma: list[list[float]] = Field(default_factory=list)
    mfcc: list[list[float]] = Field(default_factory=list)
    log_mel: list[list[float]] = Field(default_factory=list)
    onset_envelope: list[float] = Field(default_factory=list)
    chroma_mean: list[float] = Field(default_factory=list)
    mfcc_mean: list[float] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class StructuredTheoryDescription(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_path: Path
    feature_summary: dict[str, Any]
    deterministic_description: str
    llm_description: str | None = None
    final_description: str


class CandidateBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidates: list[str] = Field(default_factory=list)
    raw_response: str | None = None


class ScoreBreakdown(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chroma: float
    mfcc: float
    onset: float
    tempo: float
    duration: float
    loudness: float
    embedding: float | None = None
    conciseness: float = 0.0


class SimilarityReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_score: float
    breakdown: ScoreBreakdown
    notes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RenderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    output_path: Path
    cycles: float = 4.0
    cps: float = 2.0
    format: str = "wav"
    sample_rate: int = 44100
    max_polyphony: int = 16
    multi_channel_orbits: bool = False


class RenderResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: bool
    output_path: Path | None = None
    format: str = "wav"
    sample_rate: int | None = None
    duration_seconds: float | None = None
    code: str
    error: str | None = None
    logs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CandidateResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    iteration: int = 0
    rendered_path: str | None = None
    render: RenderResult | None = None
    score: SimilarityReport | None = None
    prompt_name: str | None = None
    critique: str | None = None


class RunManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    target_path: Path
    run_dir: Path
    theory_description: StructuredTheoryDescription | None = None
    candidates: list[CandidateResult] = Field(default_factory=list)
    best_candidate: CandidateResult | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class BenchmarkFixture(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fixture_id: str
    code_path: Path
    target_path: Path | None = None
    cycles: float = 4.0
    cps: float = 2.0
    notes: str | None = None


class BenchmarkResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fixture_id: str
    best_score: float
    best_code: str
    run_dir: Path
    metadata: dict[str, Any] = Field(default_factory=dict)

