"""Optional prompt-optimization integration points."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from djpt.artifacts import create_run_dir, write_json, write_text
from djpt.audio.analysis import compare_audio
from djpt.audio.features import analyze_audio
from djpt.config import AppConfig
from djpt.llm.description import build_structured_description
from djpt.renderer_client import render_strudel
from djpt.schemas import (
    BenchmarkFixture,
    BenchmarkResult,
    RenderRequest,
    ScoreBreakdown,
    SimilarityReport,
)

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


def _load_optional_dspy():
    import dspy

    try:
        from dspy.teleprompt import MIPROv2  # type: ignore[attr-defined]
    except ImportError:
        from dspy import MIPROv2  # type: ignore[no-redef]

    return dspy, MIPROv2


def _load_resolved_fixtures(manifest_path: Path) -> list[BenchmarkFixture]:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    fixtures = [BenchmarkFixture.model_validate(item) for item in payload.get("fixtures", [])]
    return [fixture for fixture in fixtures if fixture.target_path is not None]


def _skip_result(
    *,
    run_dir: Path,
    manifest_path: Path,
    before_snapshot_path: Path,
    capability_snapshot_path: Path,
    reason: str,
    message: str,
    output_path: Path | None = None,
) -> dict[str, Any]:
    payload = {
        "status": "skipped",
        "reason": reason,
        "message": message,
        "run_dir": str(run_dir),
        "manifest_path": str(manifest_path),
        "before_snapshot_path": str(before_snapshot_path),
        "capability_snapshot_path": str(capability_snapshot_path),
        "after_snapshot_path": None,
        "baseline_results_path": None,
        "optimized_results_path": None,
        "summary": None,
    }
    write_json(run_dir / "promptopt-result.json", payload)
    if output_path is not None:
        write_json(output_path, payload)
    return payload


def _persist_program_state(program: Any, destination: Path) -> Path:
    if hasattr(program, "save"):
        try:
            program.save(str(destination))
            return destination
        except Exception:
            pass

    if hasattr(program, "dump_state"):
        try:
            write_json(destination, program.dump_state())
            return destination
        except Exception:
            pass

    write_text(destination, repr(program))
    return destination


def _summarize_benchmark_results(results: list[BenchmarkResult]) -> dict[str, Any]:
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


def _sanitize_code(prediction: Any) -> str:
    code = str(getattr(prediction, "code", "") or "").strip()
    return code.strip("`")


def _evaluate_program(
    *,
    program: Any,
    examples: list[dict[str, Any]],
    output_dir: Path,
    config: AppConfig,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    benchmark_results: list[BenchmarkResult] = []

    for example in examples:
        fixture: BenchmarkFixture = example["fixture"]
        prediction = program(description_json=example["description_json"])
        code = _sanitize_code(prediction)

        render = render_strudel(
            RenderRequest(
                code=code,
                output_path=output_dir / f"{fixture.fixture_id}.wav",
                cycles=fixture.cycles,
                cps=fixture.cps,
                sample_rate=config.default_sample_rate,
                max_polyphony=config.max_polyphony,
                format="wav",
            ),
            config,
        )

        score_report: SimilarityReport | None = None
        score_value = 0.0
        if render.success and render.output_path:
            score_report = compare_audio(
                Path(example["target_path"]),
                Path(render.output_path),
                code=code,
                config=config,
            )
            score_value = score_report.total_score

        benchmark_results.append(
            BenchmarkResult(
                fixture_id=fixture.fixture_id,
                best_score=score_value,
                best_code=code,
                run_dir=output_dir,
                metadata={
                    "target_path": example["target_path"],
                    "render_path": str(render.output_path) if render.output_path else None,
                },
            )
        )
        records.append(
            {
                "fixture_id": fixture.fixture_id,
                "code": code,
                "render": render.model_dump(mode="json"),
                "score": None if score_report is None else score_report.model_dump(mode="json"),
            }
        )

    aggregate = _summarize_benchmark_results(benchmark_results)
    payload = {"results": records, "aggregate": aggregate}
    write_json(output_dir / "results.json", payload)
    return payload


def run_prompt_optimization(
    manifest_path: str | Path,
    *,
    output_path: str | Path | None = None,
    config: AppConfig | None = None,
    max_examples: int = 3,
    auto: str = "light",
    iterations: int = 1,
    candidate_count: int = 1,
    beam_width: int = 1,
) -> dict[str, Any]:
    resolved = (config or AppConfig.from_env()).ensure_directories()
    manifest_path = Path(manifest_path).resolve()
    optional_output_path = Path(output_path).resolve() if output_path is not None else None

    run_dir = create_run_dir("promptopt", resolved)
    before_snapshot_path = run_dir / "prompt-templates-before.json"
    capability_snapshot_path = run_dir / "prompt-optimization-summary.json"
    snapshot_prompt_templates(prompts_root=resolved.prompts_root, output_path=before_snapshot_path)
    snapshot_prompt_optimization_summary(output_path=capability_snapshot_path)

    if not prompt_optimization_available():
        return _skip_result(
            run_dir=run_dir,
            manifest_path=manifest_path,
            before_snapshot_path=before_snapshot_path,
            capability_snapshot_path=capability_snapshot_path,
            reason="dspy_unavailable",
            message="DSPy is not installed. Install the promptopt extras to enable optimization.",
            output_path=optional_output_path,
        )

    if not resolved.openai_api_key:
        return _skip_result(
            run_dir=run_dir,
            manifest_path=manifest_path,
            before_snapshot_path=before_snapshot_path,
            capability_snapshot_path=capability_snapshot_path,
            reason="missing_openai_api_key",
            message="OPENAI_API_KEY is required for prompt optimization.",
            output_path=optional_output_path,
        )

    fixtures = _load_resolved_fixtures(manifest_path)
    if not fixtures:
        return _skip_result(
            run_dir=run_dir,
            manifest_path=manifest_path,
            before_snapshot_path=before_snapshot_path,
            capability_snapshot_path=capability_snapshot_path,
            reason="no_resolved_fixtures",
            message="No fixtures with target audio are available for prompt optimization.",
            output_path=optional_output_path,
        )

    dspy, MIPROv2 = _load_optional_dspy()
    dspy.configure(lm=dspy.LM(f"openai/{resolved.openai_model}", api_key=resolved.openai_api_key))

    examples = []
    for fixture in fixtures[:max_examples]:
        target_path = Path(fixture.target_path).resolve() if fixture.target_path else fixture.code_path.resolve()
        analysis = analyze_audio(target_path, resolved)
        description = build_structured_description(analysis)
        examples.append(
            {
                "fixture": fixture,
                "target_path": str(target_path),
                "description_json": json.dumps(description.model_dump(mode="json"), indent=2, sort_keys=True),
            }
        )

    class StrudelCandidateSignature(dspy.Signature):
        """Write concise synth-only Strudel code from a structured description."""

        description_json = dspy.InputField(desc="Structured theory description JSON.")
        code = dspy.OutputField(desc="Valid concise synth-only Strudel code.")

    class StrudelCandidateProgram(dspy.Module):
        def __init__(self) -> None:
            super().__init__()
            self.generator = dspy.Predict(StrudelCandidateSignature)

        def forward(self, description_json: str):
            return self.generator(description_json=description_json)

    trainset = [
        dspy.Example(
            fixture_id=example["fixture"].fixture_id,
            description_json=example["description_json"],
            target_path=example["target_path"],
        ).with_inputs("description_json")
        for example in examples
    ]

    metric_counter = {"value": 0}
    metric_dir = run_dir / "metric-evals"

    def metric(example: Any, prediction: Any, trace: Any = None) -> float:
        del trace
        code = _sanitize_code(prediction)
        if not code:
            return 0.0
        fixture = next((item for item in examples if item["fixture"].fixture_id == example.fixture_id), None)
        if fixture is None:
            return 0.0

        metric_counter["value"] += 1
        render = render_strudel(
            RenderRequest(
                code=code,
                output_path=metric_dir / f"{metric_counter['value']:04d}-{example.fixture_id}.wav",
                cycles=fixture["fixture"].cycles,
                cps=fixture["fixture"].cps,
                sample_rate=resolved.default_sample_rate,
                max_polyphony=resolved.max_polyphony,
                format="wav",
            ),
            resolved,
        )
        if not render.success or not render.output_path:
            return 0.0
        report = compare_audio(
            Path(fixture["target_path"]),
            Path(render.output_path),
            code=code,
            config=resolved,
        )
        return float(report.total_score)

    baseline_program = StrudelCandidateProgram()
    baseline = _evaluate_program(
        program=baseline_program,
        examples=examples,
        output_dir=run_dir / "baseline",
        config=resolved,
    )

    optimizer = MIPROv2(metric=metric, auto=auto)
    optimized_program = optimizer.compile(baseline_program, trainset=trainset)
    optimized = _evaluate_program(
        program=optimized_program,
        examples=examples,
        output_dir=run_dir / "optimized",
        config=resolved,
    )

    after_snapshot_path = _persist_program_state(
        optimized_program,
        run_dir / "optimized-program-state.json",
    )

    payload = {
        "status": "completed",
        "run_dir": str(run_dir),
        "manifest_path": str(manifest_path),
        "before_snapshot_path": str(before_snapshot_path),
        "capability_snapshot_path": str(capability_snapshot_path),
        "after_snapshot_path": str(after_snapshot_path),
        "baseline_results_path": str(run_dir / "baseline" / "results.json"),
        "optimized_results_path": str(run_dir / "optimized" / "results.json"),
        "fixture_ids": [example["fixture"].fixture_id for example in examples],
        "baseline_summary": baseline["aggregate"],
        "optimized_summary": optimized["aggregate"],
        "metadata": {
            "auto": auto,
            "max_examples": len(examples),
            "search_options": {
                "iterations": iterations,
                "candidate_count": candidate_count,
                "beam_width": beam_width,
            },
        },
    }
    write_json(run_dir / "promptopt-result.json", payload)
    if optional_output_path is not None:
        write_json(optional_output_path, payload)
    return payload
