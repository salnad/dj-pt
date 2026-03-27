from pathlib import Path

from djpt.optimize.promptopt import (
    describe_prompt_optimization,
    prompt_optimization_summary_dict,
    snapshot_prompt_templates,
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


def test_snapshot_prompt_templates_writes_prompt_bundle(tmp_path: Path):
    prompts_root = tmp_path / "prompts"
    prompts_root.mkdir(parents=True)
    (prompts_root / "audio_to_theory.md").write_text("alpha", encoding="utf-8")
    (prompts_root / "theory_to_strudel.md").write_text("beta", encoding="utf-8")
    output_path = tmp_path / "snapshots" / "prompts.json"

    payload = snapshot_prompt_templates(prompts_root=prompts_root, output_path=output_path)

    assert output_path.exists()
    assert payload["audio_to_theory.md"] == "alpha"
    assert payload["theory_to_strudel.md"] == "beta"
