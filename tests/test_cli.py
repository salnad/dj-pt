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
