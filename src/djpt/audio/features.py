from __future__ import annotations

from pathlib import Path

import librosa
import numpy as np

from djpt.audio.io import canonicalize_audio
from djpt.config import AppConfig
from djpt.schemas import AudioAnalysis

PITCH_CLASSES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def _estimate_key(chroma_mean: np.ndarray) -> tuple[str | None, list[str]]:
    if chroma_mean.size != 12:
        return None, []
    ranked = np.argsort(chroma_mean)[::-1]
    top_pitch_classes = [PITCH_CLASSES[index] for index in ranked[:4]]
    return top_pitch_classes[0], top_pitch_classes


def analyze_audio(path: str | Path, config: AppConfig | None = None) -> AudioAnalysis:
    resolved = config or AppConfig.from_env()
    input_path = Path(path).resolve()

    normalized_dir = resolved.runs_root / "normalized"
    normalized_dir.mkdir(parents=True, exist_ok=True)
    normalized_path = normalized_dir / f"{input_path.stem}-{resolved.default_sample_rate}hz.wav"
    canonicalize_audio(
        input_path=input_path,
        output_path=normalized_path,
        sample_rate=resolved.default_sample_rate,
        mono=True,
        config=resolved,
    )

    audio, sample_rate = librosa.load(normalized_path, sr=resolved.default_sample_rate, mono=True)
    duration_seconds = float(librosa.get_duration(y=audio, sr=sample_rate))
    tempo_bpm, beat_frames = librosa.beat.beat_track(y=audio, sr=sample_rate)
    beat_times = librosa.frames_to_time(beat_frames, sr=sample_rate).tolist()

    rms = librosa.feature.rms(y=audio)[0]
    spectral_centroid = librosa.feature.spectral_centroid(y=audio, sr=sample_rate)[0]
    zero_crossing_rate = librosa.feature.zero_crossing_rate(y=audio)[0]
    onset_envelope = librosa.onset.onset_strength(y=audio, sr=sample_rate)
    chroma = librosa.feature.chroma_cqt(y=audio, sr=sample_rate)
    mfcc = librosa.feature.mfcc(y=audio, sr=sample_rate, n_mfcc=13)
    mel = librosa.feature.melspectrogram(y=audio, sr=sample_rate, n_mels=64)
    log_mel = librosa.power_to_db(mel, ref=np.max)
    harmonic, percussive = librosa.effects.hpss(audio)

    chroma_mean = np.mean(chroma, axis=1) if chroma.size else np.array([])
    estimated_key, top_pitch_classes = _estimate_key(chroma_mean)
    harmonic_energy = float(np.mean(np.abs(harmonic))) if harmonic.size else 0.0
    percussive_energy = float(np.mean(np.abs(percussive))) if percussive.size else 0.0
    energy_total = max(harmonic_energy + percussive_energy, 1e-9)

    return AudioAnalysis(
        path=input_path,
        normalized_path=normalized_path,
        sample_rate=sample_rate,
        duration_seconds=duration_seconds,
        tempo_bpm=float(tempo_bpm) if tempo_bpm else None,
        beat_times_seconds=[float(value) for value in beat_times],
        rms=float(np.mean(rms)) if rms.size else 0.0,
        spectral_centroid_hz=float(np.mean(spectral_centroid)) if spectral_centroid.size else 0.0,
        zero_crossing_rate=float(np.mean(zero_crossing_rate)) if zero_crossing_rate.size else 0.0,
        harmonic_ratio=harmonic_energy / energy_total,
        percussive_ratio=percussive_energy / energy_total,
        onset_strength_mean=float(np.mean(onset_envelope)) if onset_envelope.size else 0.0,
        onset_density=float(
            np.count_nonzero(onset_envelope > np.mean(onset_envelope)) / max(duration_seconds, 1e-9)
        ),
        estimated_key=estimated_key,
        top_pitch_classes=top_pitch_classes,
        chroma=chroma.tolist(),
        mfcc=mfcc.tolist(),
        log_mel=log_mel.tolist(),
        onset_envelope=onset_envelope.tolist(),
        chroma_mean=chroma_mean.tolist(),
        mfcc_mean=np.mean(mfcc, axis=1).tolist() if mfcc.size else [],
        metadata={
            "normalized_path": str(normalized_path),
            "beat_count": len(beat_times),
        },
    )
