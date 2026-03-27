from __future__ import annotations

import json
import subprocess

from djpt.config import AppConfig
from djpt.schemas import RenderRequest, RenderResult


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

    result = RenderResult.model_validate(data)
    result.logs.extend(logs)
    return result

