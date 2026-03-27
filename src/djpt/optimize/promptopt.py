"""Optional prompt-optimization integration points."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROMPT_FILES = [
    "audio_to_theory.md",
    "theory_to_strudel.md",
    "refine_strudel.md",
]


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
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def snapshot_prompt_templates(
    *,
    prompts_root: str | Path,
    output_path: str | Path,
) -> dict[str, str]:
    prompts_root = Path(prompts_root)
    output_path = Path(output_path)
    payload: dict[str, str] = {}
    for prompt_name in PROMPT_FILES:
        prompt_path = prompts_root / prompt_name
        if not prompt_path.exists():
            continue
        payload[prompt_path.name] = prompt_path.read_text(encoding="utf-8")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload
