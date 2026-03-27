from __future__ import annotations

import json
from pathlib import Path

from djpt.artifacts import create_run_dir, write_json
from djpt.llm.generation import CandidateGenerator, DeterministicAudioToCodeProvider
from djpt.optimize.search import FitOptions, run_search
from djpt.schemas import BenchmarkFixture, BenchmarkResult, BenchmarkRunSummary


def load_manifest(path: Path) -> list[BenchmarkFixture]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    fixtures = payload.get("fixtures", [])
    return [BenchmarkFixture.model_validate(item) for item in fixtures]


def summarize_results(results: list[BenchmarkResult]) -> dict:
    if not results:
        return {"count": 0, "average_score": 0.0, "fixtures": []}
    average = sum(result.best_score for result in results) / len(results)
    best = max(results, key=lambda result: result.best_score)
    return {
        "count": len(results),
        "average_score": average,
        "best_fixture_id": best.fixture_id,
        "best_score": best.best_score,
        "fixtures": [result.model_dump(mode="json") for result in results],
    }


def unresolved_fixtures(fixtures: list[BenchmarkFixture]) -> list[BenchmarkFixture]:
    return [fixture for fixture in fixtures if fixture.target_path is None]


def resolved_fixtures(fixtures: list[BenchmarkFixture]) -> list[BenchmarkFixture]:
    return [fixture for fixture in fixtures if fixture.target_path is not None]


def _run_fixture(
    fixture: BenchmarkFixture,
    generator: CandidateGenerator,
    options: FitOptions,
) -> BenchmarkResult:
    target = fixture.target_path or fixture.code_path
    manifest = run_search(
        target,
        generator,
        options=FitOptions(
            iterations=options.iterations,
            candidate_count=options.candidate_count,
            beam_width=options.beam_width,
            cycles=fixture.cycles,
            cps=fixture.cps,
        ),
    )
    best_candidate = manifest.best_candidate
    return BenchmarkResult(
        fixture_id=fixture.fixture_id,
        best_score=best_candidate.score.total_score if best_candidate and best_candidate.score else 0.0,
        best_code=best_candidate.code if best_candidate else "",
        run_dir=manifest.run_dir,
        metadata={
            "target_path": str(target),
            "candidate_count": len(manifest.candidates),
        },
    )


def persist_benchmark_summary(
    *,
    manifest_path: Path,
    summary: BenchmarkRunSummary,
) -> Path:
    benchmark_dir = create_run_dir("benchmark")
    summary_path = benchmark_dir / "benchmark-summary.json"
    write_json(
        summary_path,
        {
            "manifest_path": str(manifest_path),
            **summary.model_dump(mode="json"),
        },
    )
    return summary_path


def run_benchmark(
    manifest_path: str | Path,
    generator: CandidateGenerator | None = None,
    *,
    options: FitOptions | None = None,
) -> BenchmarkRunSummary:
    manifest_path = Path(manifest_path)
    fixtures = load_manifest(manifest_path)
    generator = generator or CandidateGenerator(DeterministicAudioToCodeProvider())
    options = options or FitOptions(iterations=2, candidate_count=3, beam_width=2)

    results = [_run_fixture(fixture, generator, options) for fixture in fixtures]
    aggregate = summarize_results(results)
    summary = BenchmarkRunSummary(
        count=aggregate["count"],
        average_score=aggregate["average_score"],
        best_fixture_id=aggregate.get("best_fixture_id"),
        best_score=aggregate.get("best_score"),
        fixtures=results,
    )
    summary_path = persist_benchmark_summary(
        manifest_path=manifest_path,
        summary=summary,
    )
    summary.results_path = summary_path
    summary.metadata["manifest_path"] = str(manifest_path)
    summary.metadata["results_path"] = str(summary_path)
    return summary
