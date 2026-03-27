from __future__ import annotations

from pathlib import Path

from djpt.config import AppConfig
from djpt.renderer_client import render_strudel
from djpt.schemas import RenderRequest


def test_renderer_client_reports_missing_script(tmp_path: Path) -> None:
    config = AppConfig.from_env()
    config = config.model_copy(update={"renderer_root": tmp_path / "renderer-missing"})

    request = RenderRequest(
        code='note("c3").s("sine")',
        output_path=tmp_path / "out.wav",
    )
    result = render_strudel(request, config)

    assert result.success is False
    assert result.error is not None
    assert "Renderer script not found" in result.error


def test_renderer_client_reports_non_json_stdout(tmp_path: Path) -> None:
    renderer_root = tmp_path / "renderer"
    scripts_dir = renderer_root / "scripts"
    scripts_dir.mkdir(parents=True)
    script_path = scripts_dir / "render-cli.mjs"
    script_path.write_text('console.log("not-json")\n', encoding="utf-8")

    config = AppConfig.from_env(tmp_path).model_copy(
        update={
            "workspace_root": tmp_path,
            "renderer_root": renderer_root,
            "prompts_root": tmp_path / "prompts",
            "benchmarks_root": tmp_path / "benchmarks",
            "runs_root": tmp_path / "runs",
        }
    )
    request = RenderRequest(
        code='note("c3").s("sine")',
        output_path=tmp_path / "out.wav",
    )

    result = render_strudel(request, config)

    assert result.success is False
    assert result.error is not None
    assert "invalid JSON" in result.error


def test_renderer_client_normalizes_camel_case_renderer_payload(tmp_path: Path) -> None:
    renderer_root = tmp_path / "renderer"
    scripts_dir = renderer_root / "scripts"
    scripts_dir.mkdir(parents=True)
    script_path = scripts_dir / "render-cli.mjs"
    script_path.write_text(
        'console.log(JSON.stringify({"success":true,"outputPath":"'
        + str(tmp_path / "out.wav")
        + '","format":"wav","sampleRate":32000,"durationSeconds":1.5,"code":"note(\\"c3\\").s(\\"sine\\")"}))\n',
        encoding="utf-8",
    )
    (tmp_path / "out.wav").write_bytes(b"RIFFstub")

    config = AppConfig.from_env(tmp_path).model_copy(
        update={
            "workspace_root": tmp_path,
            "renderer_root": renderer_root,
            "prompts_root": tmp_path / "prompts",
            "benchmarks_root": tmp_path / "benchmarks",
            "runs_root": tmp_path / "runs",
        }
    )

    result = render_strudel(
        RenderRequest(
            code='note("c3").s("sine")',
            output_path=tmp_path / "out.wav",
        ),
        config,
    )

    assert result.success is True
    assert result.output_path == tmp_path / "out.wav"
