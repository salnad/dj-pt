"""Optional prompt-optimization integration points."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def prompt_optimization_available() -> bool:
    try:
        import dspy  # noqa: F401
    except ImportError:
        return False
    return True


@dataclass(slots=True)
class PromptOptimizationSummary:
    available: bool
    optimizer: str | None
    notes: list[str]
    metadata: dict[str, Any]


def describe_prompt_optimization() -> PromptOptimizationSummary:
    available = prompt_optimization_available()
    return PromptOptimizationSummary(
        available=available,
        optimizer="DSPy MIPROv2" if available else None,
        notes=[
            "Prompt optimization is optional and benchmark-driven.",
            "The intended optimizer is DSPy MIPROv2 with the composite audio similarity score as the metric.",
        ],
        metadata={"package": "dspy-ai"},
    )


def prompt_optimization_summary_dict() -> dict[str, Any]:
    summary = describe_prompt_optimization()
    return {
        "available": summary.available,
        "optimizer": summary.optimizer,
        "notes": summary.notes,
        "metadata": summary.metadata,
    }


def snapshot_prompt_optimization_summary(*, output_path: str | None = None) -> dict[str, Any]:
    payload = prompt_optimization_summary_dict()
    if output_path is not None:
        from pathlib import Path
        import json

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload
