from __future__ import annotations

import json
import subprocess
from pathlib import Path

from djpt.audio.io import probe_audio
from djpt.config import AppConfig
from djpt.schemas import RenderRequest, RenderResult


def _normalize_renderer_payload(data: dict) -> dict:
    normalized = dict(data)
    if "outputPath" in normalized and "output_path" not in normalized:
        normalized["output_path"] = normalized.pop("outputPath")
    elif "outputPath" in normalized:
        normalized.pop("outputPath")
    if "sampleRate" in normalized and "sample_rate" not in normalized:
        normalized["sample_rate"] = normalized.pop("sampleRate")
    elif "sampleRate" in normalized:
        normalized.pop("sampleRate")
    if "durationSeconds" in normalized and "duration_seconds" not in normalized:
        normalized["duration_seconds"] = normalized.pop("durationSeconds")
    elif "durationSeconds" in normalized:
        normalized.pop("durationSeconds")
    return normalized


def _augment_render_result_metadata(
    result: RenderResult,
    *,
    settings: AppConfig,
    exit_code: int,
) -> RenderResult:
    if result.success and result.output_path:
        resolved_path = Path(result.output_path)
        if resolved_path.exists():
            try:
                metadata = probe_audio(resolved_path, settings)
            except subprocess.CalledProcessError:
                result.metadata.setdefault("exit_code", exit_code)
                result.metadata["probe_error"] = "ffprobe_failed"
                return result

            result.sample_rate = metadata.sample_rate
            result.duration_seconds = metadata.duration_seconds
            result.metadata.update(
                {
                    "channels": metadata.channels,
                    "format_name": metadata.format_name,
                    "exit_code": exit_code,
                }
            )
        else:
            result.success = False
            result.error = f"Renderer reported success but output file was missing: {resolved_path}"
            result.metadata["exit_code"] = exit_code
    else:
        result.metadata.setdefault("exit_code", exit_code)
    return result


def render_strudel(request: RenderRequest, config: AppConfig | None = None) -> RenderResult:
    settings = config or AppConfig.from_env()
    script_path = settings.renderer_root / "scripts" / "render-cli.mjs"

    if not script_path.exists():
        return RenderResult(
            success=False,
            code=request.code,
            format=request.format,
            error=f"Renderer script not found at {script_path}",
        )

    payload = request.model_dump(mode="json")
    process = subprocess.run(
        [
            "node",
            str(script_path),
            "--job-json",
            json.dumps(payload),
        ],
        cwd=settings.workspace_root,
        check=False,
        capture_output=True,
        text=True,
    )

    logs = [line for line in process.stderr.splitlines() if line.strip()]
    stdout = process.stdout.strip()
    if not stdout:
        return RenderResult(
            success=False,
            code=request.code,
            format=request.format,
            error="Renderer produced no JSON output.",
            logs=logs,
            metadata={"exit_code": process.returncode},
        )

    try:
        data = json.loads(stdout)
    except json.JSONDecodeError as exc:
        return RenderResult(
            success=False,
            code=request.code,
            format=request.format,
            error=f"Renderer returned invalid JSON: {exc}",
            logs=logs + [stdout],
            metadata={"exit_code": process.returncode},
        )

    result = RenderResult.model_validate(_normalize_renderer_payload(data))
    result.logs.extend(logs)
    return _augment_render_result_metadata(
        result,
        settings=settings,
        exit_code=process.returncode,
    )

