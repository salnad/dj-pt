from __future__ import annotations

import json
from pathlib import Path

from djpt.schemas import BenchmarkFixture, BenchmarkResult


def load_manifest(path: Path) -> list[BenchmarkFixture]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    fixtures = payload.get("fixtures", [])
    return [BenchmarkFixture.model_validate(item) for item in fixtures]


def summarize_results(results: list[BenchmarkResult]) -> dict:
    if not results:
        return {"count": 0, "average_score": 0.0}
    average = sum(result.best_score for result in results) / len(results)
    return {
        "count": len(results),
        "average_score": average,
    }


def unresolved_fixtures(fixtures: list[BenchmarkFixture]) -> list[BenchmarkFixture]:
    return [fixture for fixture in fixtures if fixture.target_path is None]


def resolved_fixtures(fixtures: list[BenchmarkFixture]) -> list[BenchmarkFixture]:
    return [fixture for fixture in fixtures if fixture.target_path is not None]
