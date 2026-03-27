from djpt.optimize.promptopt import describe_prompt_optimization, prompt_optimization_summary_dict


def test_describe_prompt_optimization_reports_expected_metadata():
    summary = describe_prompt_optimization()
    assert summary.metadata["package"] == "dspy-ai"
    assert summary.notes


def test_prompt_optimization_summary_dict_contains_availability_flag():
    payload = prompt_optimization_summary_dict()
    assert "available" in payload
    assert payload["metadata"]["package"] == "dspy-ai"
