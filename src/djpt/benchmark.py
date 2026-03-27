from __future__ import annotations

import json
from pathlib import Path

from djpt.llm.generation import CandidateGenerator, DeterministicAudioToCodeProvider
from djpt.optimize.search import FitOptions, run_search
from djpt.schemas import BenchmarkFixture, BenchmarkResult


def load_manifest(path: Path) -> list[BenchmarkFixture]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    fixtures = payload.get("fixtures", [])
    return [BenchmarkFixture.model_validate(item) for item in fixtures]


def summarize_results(results: list[BenchmarkResult]) -> dict:
    if not results:
        return {"count": 0, "average_score": 0.0}
    average = sum(result.best_score for result in results) / len(results)
    best = max(results, key=lambda result: result.best_score)
    return {
        "count": len(results),
        "average_score": average,
        "best_fixture_id": best.fixture_id,
        "best_score": best.best_score,
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


def run_benchmark(
    manifest_path: str | Path,
    generator: CandidateGenerator | None = None,
    *,
    options: FitOptions | None = None,
) -> dict:
    fixtures = load_manifest(Path(manifest_path))
    generator = generator or CandidateGenerator(DeterministicAudioToCodeProvider())
    options = options or FitOptions(iterations=2, candidate_count=3, beam_width=2)

    results = [_run_fixture(fixture, generator, options) for fixture in fixtures]
    summary = summarize_results(results)
    summary["fixtures"] = [result.model_dump(mode="json") for result in results]
    return summary
