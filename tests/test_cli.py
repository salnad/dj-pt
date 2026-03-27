from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from djpt.cli import app


runner = CliRunner()


def test_config_command_runs() -> None:
    result = runner.invoke(app, ["config"])
    assert result.exit_code == 0
    assert "workspace_root" in result.stdout


def test_analyze_command_reports_audio(tmp_path: Path, sine_wave_path: Path) -> None:
    placeholder = tmp_path / "placeholder.wav"
    placeholder.write_bytes(b"not-a-real-wave")

    bad_result = runner.invoke(app, ["analyze", str(placeholder)])
    assert bad_result.exit_code != 0

    good_result = runner.invoke(app, ["analyze", str(sine_wave_path)])
    assert good_result.exit_code == 0
    assert "duration_seconds" in good_result.stdout


def test_benchmark_command_reports_manifest_summary(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        '{"fixtures":[{"fixture_id":"demo","code_path":"benchmarks/simple/snippets/bright-arp.strudel","target_path":null,"cycles":4,"cps":0.5}]}',
        encoding="utf-8",
    )

    result = runner.invoke(app, ["benchmark", str(manifest_path)])

    assert result.exit_code == 0
    assert '"fixture_count": 1' in result.stdout


def test_promptopt_command_reports_snapshot(tmp_path: Path) -> None:
    output_path = tmp_path / "promptopt-summary.json"

    result = runner.invoke(app, ["promptopt", str(output_path)])

    assert result.exit_code == 0
    assert output_path.exists()
    assert '"snapshot_path"' in result.stdout
