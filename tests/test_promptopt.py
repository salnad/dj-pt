from pathlib import Path

from djpt.optimize.promptopt import (
    describe_prompt_optimization,
    prompt_optimization_summary_dict,
    snapshot_prompt_optimization_summary,
)


def test_describe_prompt_optimization_reports_expected_metadata():
    summary = describe_prompt_optimization()
    assert summary.metadata["package"] == "dspy-ai"
    assert summary.notes


def test_prompt_optimization_summary_dict_contains_availability_flag():
    payload = prompt_optimization_summary_dict()
    assert "available" in payload
    assert payload["metadata"]["package"] == "dspy-ai"


def test_snapshot_prompt_optimization_summary_writes_file(tmp_path: Path):
    output_path = tmp_path / "promptopt" / "summary.json"
    payload = snapshot_prompt_optimization_summary(output_path=output_path)

    assert output_path.exists()
    assert payload["metadata"]["package"] == "dspy-ai"
