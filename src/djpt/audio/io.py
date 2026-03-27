from __future__ import annotations

import json
import subprocess
from pathlib import Path

from djpt.config import AppConfig, settings
from djpt.schemas import AudioCanonicalizationResult, AudioFileMetadata


def probe_audio(path: Path, config: AppConfig | None = None) -> AudioFileMetadata:
    resolved = config or settings
    command = [
        resolved.ffprobe_binary,
        "-v",
        "error",
        "-show_entries",
        "stream=codec_name,channels,sample_rate,duration:format=duration,format_name",
        "-of",
        "json",
        str(path),
    ]
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    payload = json.loads(completed.stdout)
    streams = payload.get("streams", [])
    audio_stream = next((stream for stream in streams if stream.get("codec_name")), {})
    duration = payload.get("format", {}).get("duration") or audio_stream.get("duration") or 0.0
    sample_rate = int(audio_stream.get("sample_rate") or resolved.default_sample_rate)
    channels = int(audio_stream.get("channels") or 1)
    return AudioFileMetadata(
        path=path,
        duration_seconds=float(duration),
        sample_rate=sample_rate,
        channels=channels,
        format_name=payload.get("format", {}).get("format_name"),
    )


def canonicalize_audio(
    input_path: Path,
    output_path: Path,
    *,
    sample_rate: int | None = None,
    mono: bool | None = None,
    config: AppConfig | None = None,
) -> AudioCanonicalizationResult:
    resolved = config or settings
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sr = sample_rate or resolved.default_sample_rate
    channels = 1 if (mono if mono is not None else resolved.default_mono) else 2
    command = [
        resolved.ffmpeg_binary,
        "-y",
        "-i",
        str(input_path),
        "-ac",
        str(channels),
        "-ar",
        str(sr),
        "-vn",
        str(output_path),
    ]
    subprocess.run(command, check=True, capture_output=True, text=True)
    metadata = probe_audio(output_path, resolved)
    return AudioCanonicalizationResult(
        input_path=input_path,
        output_path=output_path,
        sample_rate=metadata.sample_rate,
        channels=metadata.channels,
        duration_seconds=metadata.duration_seconds,
    )


def convert_audio(
    input_path: Path,
    output_path: Path,
    *,
    config: AppConfig | None = None,
    bitrate: str = "192k",
) -> AudioFileMetadata:
    resolved = config or settings
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        resolved.ffmpeg_binary,
        "-y",
        "-i",
        str(input_path),
    ]
    if output_path.suffix.lower() == ".mp3":
        command.extend(["-codec:a", "libmp3lame", "-b:a", bitrate])
    command.append(str(output_path))
    subprocess.run(command, check=True, capture_output=True, text=True)
    return probe_audio(output_path, resolved)

