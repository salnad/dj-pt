from __future__ import annotations

import subprocess
from pathlib import Path

from djpt.benchmark import run_benchmark
from djpt.llm.generation import CandidateGenerator, DeterministicAudioToCodeProvider
from djpt.optimize.search import FitOptions


def test_run_benchmark_builds_fixture_results(tmp_path: Path) -> None:
    fixture_dir = tmp_path / "fixtures"
    fixture_dir.mkdir(parents=True)
    manifest_path = fixture_dir / "manifest.json"
    snippet_path = fixture_dir / "demo.strudel"
    target_path = fixture_dir / "demo.wav"
    snippet_path.write_text('$: note("c4").s("sine")\n', encoding="utf-8")
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=1",
            str(target_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    manifest_path.write_text(
        (
            '{"fixtures":[{"fixture_id":"demo","code_path":"'
            + str(snippet_path)
            + '","target_path":"'
            + str(target_path)
            + '","cycles":2,"cps":0.5}]}'
        ),
        encoding="utf-8",
    )

    provider = DeterministicAudioToCodeProvider()
    summary = run_benchmark(
        manifest_path,
        CandidateGenerator(provider),
        options=FitOptions(iterations=1, candidate_count=1, beam_width=1, cycles=2, cps=0.5),
    )

    assert summary["count"] == 1
    assert summary["fixtures"][0]["fixture_id"] == "demo"
