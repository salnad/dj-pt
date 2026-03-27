from __future__ import annotations

import librosa
import numpy as np
from scipy.spatial.distance import cdist

from djpt.audio.scoring import build_similarity_report
from djpt.audio.utils import clamp01, gaussian_similarity
from djpt.schemas import AudioAnalysis, SimilarityReport


def duration_penalty(duration_a: float, duration_b: float) -> float:
    longest = max(duration_a, duration_b, 1e-9)
    return float(min(abs(duration_a - duration_b) / longest, 1.0))


def tempo_penalty(tempo_a: float, tempo_b: float) -> float:
    fastest = max(tempo_a, tempo_b, 1.0)
    return float(min(abs(tempo_a - tempo_b) / fastest, 1.0))


def loudness_penalty(rms_a: float, rms_b: float) -> float:
    baseline = max(abs(rms_a), abs(rms_b), 1e-9)
    return float(min(abs(rms_a - rms_b) / baseline, 1.0))


def chroma_dtw_distance(chroma_a: np.ndarray, chroma_b: np.ndarray) -> float:
    if chroma_a.size == 0 or chroma_b.size == 0:
        return 1.0

    distance_matrix = cdist(chroma_a.T, chroma_b.T, metric="cosine")
    accumulated_cost, _ = librosa.sequence.dtw(C=distance_matrix)
    if accumulated_cost.size == 0:
        return 1.0

    final_cost = float(accumulated_cost[-1, -1])
    path_length = max(chroma_a.shape[1], chroma_b.shape[1], 1)
    return float(np.clip(final_cost / path_length, 0.0, 2.0) / 2.0)


def mfcc_distance(mfcc_a: np.ndarray, mfcc_b: np.ndarray) -> float:
    if mfcc_a.size == 0 or mfcc_b.size == 0:
        return 1.0

    mean_a = np.mean(mfcc_a, axis=1)
    mean_b = np.mean(mfcc_b, axis=1)
    euclidean = np.linalg.norm(mean_a - mean_b)
    normalized = euclidean / max(np.linalg.norm(mean_a) + np.linalg.norm(mean_b), 1e-9)
    return float(np.clip(normalized, 0.0, 1.0))


def log_mel_distance(log_mel_a: np.ndarray, log_mel_b: np.ndarray) -> float:
    if log_mel_a.size == 0 or log_mel_b.size == 0:
        return 1.0

    bins = min(log_mel_a.shape[1], log_mel_b.shape[1])
    if bins == 0:
        return 1.0

    seq_a = log_mel_a[:, :bins]
    seq_b = log_mel_b[:, :bins]
    mean_a = np.mean(seq_a, axis=1)
    mean_b = np.mean(seq_b, axis=1)
    cosine = cdist(mean_a[None, :], mean_b[None, :], metric="cosine")[0, 0]
    if np.isnan(cosine):
        return 1.0
    return float(np.clip(cosine, 0.0, 1.0))


def onset_envelope_distance(onset_a: np.ndarray, onset_b: np.ndarray) -> float:
    if onset_a.size == 0 or onset_b.size == 0:
        return 1.0

    target_length = max(len(onset_a), len(onset_b))
    aligned_a = librosa.util.fix_length(onset_a, size=target_length)
    aligned_b = librosa.util.fix_length(onset_b, size=target_length)
    if np.allclose(aligned_a, 0) and np.allclose(aligned_b, 0):
        return 0.0

    cosine = cdist(aligned_a[None, :], aligned_b[None, :], metric="cosine")[0, 0]
    if np.isnan(cosine):
        return 1.0
    return float(np.clip(cosine, 0.0, 1.0))


def beat_alignment_penalty(beats_a: np.ndarray, beats_b: np.ndarray) -> float:
    if beats_a.size == 0 or beats_b.size == 0:
        return 1.0

    count = min(len(beats_a), len(beats_b))
    trimmed_a = beats_a[:count]
    trimmed_b = beats_b[:count]
    error = np.mean(np.abs(trimmed_a - trimmed_b))
    baseline = max(trimmed_a[-1], trimmed_b[-1], 1.0)
    return float(np.clip(error / baseline, 0.0, 1.0))


def compare_analyses(
    target: AudioAnalysis,
    candidate: AudioAnalysis,
    *,
    code: str | None = None,
) -> SimilarityReport:
    target_chroma = np.asarray(target.chroma, dtype=float)
    candidate_chroma = np.asarray(candidate.chroma, dtype=float)
    target_mfcc = np.asarray(target.mfcc, dtype=float)
    candidate_mfcc = np.asarray(candidate.mfcc, dtype=float)
    target_log_mel = np.asarray(target.log_mel, dtype=float)
    candidate_log_mel = np.asarray(candidate.log_mel, dtype=float)
    target_onset = np.asarray(target.onset_envelope, dtype=float)
    candidate_onset = np.asarray(candidate.onset_envelope, dtype=float)
    target_beats = np.asarray(target.beat_times_seconds, dtype=float)
    candidate_beats = np.asarray(candidate.beat_times_seconds, dtype=float)

    chroma_distance = chroma_dtw_distance(target_chroma, candidate_chroma)
    mfcc_delta = mfcc_distance(target_mfcc, candidate_mfcc)
    mel_delta = log_mel_distance(target_log_mel, candidate_log_mel)
    onset_delta = onset_envelope_distance(target_onset, candidate_onset)
    beat_delta = beat_alignment_penalty(target_beats, candidate_beats)
    tempo_delta = tempo_penalty(target.tempo_bpm or 0.0, candidate.tempo_bpm or 0.0)
    duration_delta = duration_penalty(target.duration_seconds, candidate.duration_seconds)
    loudness_delta = loudness_penalty(target.rms, candidate.rms)

    chroma_similarity = gaussian_similarity(chroma_distance, sigma=0.18)
    mfcc_similarity = clamp01(
        (gaussian_similarity(mfcc_delta, sigma=0.18) * 0.5)
        + (gaussian_similarity(mel_delta, sigma=0.20) * 0.5)
    )
    onset_similarity = clamp01(
        (gaussian_similarity(onset_delta, sigma=0.22) * 0.7)
        + ((1.0 - beat_delta) * 0.3)
    )
    tempo_similarity = clamp01(gaussian_similarity(tempo_delta, sigma=0.18))
    duration_similarity = clamp01(1.0 - duration_delta)
    loudness_similarity = clamp01(1.0 - loudness_delta)

    report = build_similarity_report(
        chroma=chroma_similarity,
        mfcc=mfcc_similarity,
        onset=onset_similarity,
        tempo=tempo_similarity,
        duration=duration_similarity,
        loudness=loudness_similarity,
        code=code,
        notes=[
            f"Chroma DTW distance: {chroma_distance:.4f}",
            f"MFCC distance: {mfcc_delta:.4f}",
            f"Log-mel distance: {mel_delta:.4f}",
            f"Onset distance: {onset_delta:.4f}; beat penalty: {beat_delta:.4f}",
            f"Tempo penalty: {tempo_delta:.4f}; duration penalty: {duration_delta:.4f}",
        ],
    )
    report.metadata.update(
        {
            "chroma_distance": chroma_distance,
            "mfcc_distance": mfcc_delta,
            "log_mel_distance": mel_delta,
            "onset_distance": onset_delta,
            "beat_penalty": beat_delta,
            "tempo_penalty": tempo_delta,
            "duration_penalty": duration_delta,
            "loudness_penalty": loudness_delta,
        }
    )
    return report
