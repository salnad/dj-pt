from djpt.optimize.promptopt import describe_prompt_optimization


def test_describe_prompt_optimization_reports_expected_metadata():
    summary = describe_prompt_optimization()
    assert summary.metadata["package"] == "dspy-ai"
    assert summary.notes
