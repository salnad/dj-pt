from djpt.benchmark import summarize_results
from djpt.schemas import BenchmarkResult


def test_summarize_results_returns_average_and_count(tmp_path):
    results = [
        BenchmarkResult(fixture_id="a", best_score=0.8, best_code="code-a", run_dir=tmp_path / "a"),
        BenchmarkResult(fixture_id="b", best_score=0.6, best_code="code-b", run_dir=tmp_path / "b"),
    ]

    summary = summarize_results(results)

    assert summary["count"] == 2
    assert summary["average_score"] == 0.7


def test_summarize_results_empty():
    assert summarize_results([]) == {"count": 0, "average_score": 0.0}


def test_summarize_results_tracks_best_fixture(tmp_path):
    results = [
        BenchmarkResult(fixture_id="a", best_score=0.8, best_code="code-a", run_dir=tmp_path / "a"),
        BenchmarkResult(fixture_id="b", best_score=0.9, best_code="code-b", run_dir=tmp_path / "b"),
    ]

    summary = summarize_results(results)

    assert summary["best_fixture_id"] == "b"
    assert summary["best_score"] == 0.9
