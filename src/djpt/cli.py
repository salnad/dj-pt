from __future__ import annotations

import json
from pathlib import Path

import typer

from djpt.audio.analysis import compare_audio
from djpt.audio.features import analyze_audio
from djpt.audio.calibration import derive_bands
from djpt.benchmark import (
    load_manifest,
    resolved_fixtures,
    run_benchmark,
    summarize_results,
    unresolved_fixtures,
)
from djpt.llm.generation import CandidateGenerator, DeterministicAudioToCodeProvider
from djpt.optimize.search import FitOptions, run_search
from djpt.optimize.promptopt import prompt_optimization_available
from djpt.config import AppConfig
from djpt.renderer_client import render_strudel
from djpt.schemas import RenderRequest

app = typer.Typer(help="Audio-to-Strudel analysis and optimization harness.")


def _print_json(payload: object) -> None:
    typer.echo(json.dumps(payload, indent=2, sort_keys=True, default=str))


@app.callback()
def main() -> None:
    """CLI entrypoint."""


@app.command()
def config() -> None:
    """Print resolved configuration."""

    _print_json(AppConfig.from_env().model_dump(mode="json"))


@app.command()
def analyze(
    audio_path: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False),
) -> None:
    """Analyze an input audio file and emit a structured summary."""

    analysis = analyze_audio(audio_path)
    _print_json(analysis.model_dump(mode="json"))


@app.command()
def render(
    code: str = typer.Argument(...),
    output_path: Path = typer.Argument(..., help="Destination WAV/MP3 path."),
    cycles: float = typer.Option(4.0, help="Number of cycles to render."),
    cps: float = typer.Option(0.5, help="Cycles per second."),
) -> None:
    """Render Strudel code to audio."""

    config = AppConfig.from_env()
    request = RenderRequest(
        code=code,
        output_path=output_path.resolve(),
        format=output_path.suffix.lstrip(".") or "wav",
        cycles=cycles,
        cps=cps,
        sample_rate=config.default_sample_rate,
        max_polyphony=config.max_polyphony,
    )
    result = render_strudel(request, config)
    _print_json(result.model_dump(mode="json"))


@app.command()
def score(
    target_path: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False),
    candidate_path: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False),
) -> None:
    """Compare a target file with a rendered candidate."""

    report = compare_audio(target_path.resolve(), candidate_path.resolve())
    _print_json(report.model_dump(mode="json"))


@app.command()
def fit(
    audio_path: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False),
    iterations: int = typer.Option(3, help="Search iterations."),
    candidate_count: int = typer.Option(4, help="Candidates per iteration."),
    beam_width: int = typer.Option(2, help="Top candidates to retain each iteration."),
    cycles: float = typer.Option(4.0, help="Cycles to render for each candidate."),
    cps: float = typer.Option(0.5, help="Cycles per second for rendering."),
) -> None:
    """Run the iterative search loop for a target file."""

    provider = DeterministicAudioToCodeProvider()
    manifest = run_search(
        audio_path.resolve(),
        CandidateGenerator(provider),
        options=FitOptions(
            iterations=iterations,
            candidate_count=candidate_count,
            beam_width=beam_width,
            cycles=cycles,
            cps=cps,
        ),
    )
    _print_json(manifest.model_dump(mode="json"))


@app.command()
def benchmark(
    manifest_path: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False),
    run: bool = typer.Option(False, "--run", help="Execute the deterministic benchmark loop."),
    iterations: int = typer.Option(1, help="Benchmark search iterations when --run is used."),
    candidate_count: int = typer.Option(1, help="Candidates per iteration when --run is used."),
    beam_width: int = typer.Option(1, help="Beam width when --run is used."),
) -> None:
    """Run benchmark fixtures."""

    fixtures = load_manifest(manifest_path.resolve())
    benchmark_summary = (
        run_benchmark(
            manifest_path.resolve(),
            CandidateGenerator(DeterministicAudioToCodeProvider()),
            options=FitOptions(
                iterations=iterations,
                candidate_count=candidate_count,
                beam_width=beam_width,
                cycles=4.0,
                cps=0.5,
            ),
        )
        if run
        else summarize_results([])
    )
    if run:
        summary = benchmark_summary.model_dump(mode="json")
        results = summary["fixtures"]
        run_dir = summary["metadata"].get("results_path")
    else:
        summary = benchmark_summary
        results = []
        run_dir = None
    _print_json(
        {
            "manifest_path": str(manifest_path.resolve()),
            "fixture_count": len(fixtures),
            "fixture_ids": [fixture.fixture_id for fixture in fixtures],
            "resolved_fixture_ids": [fixture.fixture_id for fixture in resolved_fixtures(fixtures)],
            "unresolved_fixture_ids": [fixture.fixture_id for fixture in unresolved_fixtures(fixtures)],
            "summary": summary,
            "results": results,
            "run_dir": run_dir,
            "dspy_available": prompt_optimization_available(),
        }
    )


@app.command()
def calibrate(
    self_scores: list[float] = typer.Option(..., help="Scores from self-comparisons."),
    perturbed_scores: list[float] = typer.Option(..., help="Scores from mild perturbations."),
    unrelated_scores: list[float] = typer.Option(..., help="Scores from unrelated clips."),
) -> None:
    """Derive score calibration bands."""

    bands = derive_bands(self_scores, perturbed_scores, unrelated_scores)
    _print_json(
        {
            "excellent": bands.excellent,
            "usable": bands.usable,
            "poor": bands.poor,
        }
    )

