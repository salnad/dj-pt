from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from djpt.artifacts import create_run_dir, write_json, write_text
from djpt.audio.analysis import compare_audio
from djpt.audio.features import analyze_audio
from djpt.config import AppConfig
from djpt.llm.description import build_structured_description
from djpt.llm.generation import CandidateGenerator
from djpt.renderer_client import render_strudel
from djpt.schemas import CandidateResult, RenderRequest, RunManifest


@dataclass(slots=True)
class FitOptions:
    iterations: int = 3
    candidate_count: int = 4
    beam_width: int = 2
    cycles: float = 4.0
    cps: float = 0.5


def run_search(
    target_path: str | Path,
    candidate_generator: CandidateGenerator,
    *,
    config: AppConfig | None = None,
    options: FitOptions | None = None,
) -> RunManifest:
    resolved = config or AppConfig.from_env()
    resolved.ensure_directories()
    target_path = Path(target_path).resolve()

    opts = options or FitOptions(
        iterations=resolved.default_iterations,
        candidate_count=resolved.default_candidate_count,
        beam_width=resolved.default_beam_width,
        cycles=resolved.default_cycles,
        cps=resolved.default_cps,
    )

    run_dir = create_run_dir("fit", resolved)
    target_analysis = analyze_audio(target_path, resolved)
    description = build_structured_description(target_analysis)

    write_json(run_dir / "target_analysis.json", target_analysis.model_dump(mode="json"))
    write_json(run_dir / "theory_description.json", description.model_dump(mode="json"))
    write_text(run_dir / "theory.txt", description.final_description)

    all_candidates: list[CandidateResult] = []
    best_candidate: CandidateResult | None = None
    frontier = candidate_generator.generate_initial_candidates(
        description,
        candidate_count=opts.candidate_count,
    ).candidates

    for iteration in range(opts.iterations):
        iteration_dir = run_dir / f"iteration-{iteration:02d}"
        iteration_dir.mkdir(parents=True, exist_ok=True)
        iteration_results: list[CandidateResult] = []

        for candidate_index, code in enumerate(frontier):
            base_name = f"candidate-{candidate_index:02d}"
            render_path = iteration_dir / f"{base_name}.wav"
            render_result = render_strudel(
                RenderRequest(
                    code=code,
                    output_path=render_path,
                    cycles=opts.cycles,
                    cps=opts.cps,
                    sample_rate=resolved.default_sample_rate,
                    max_polyphony=resolved.max_polyphony,
                    format="wav",
                ),
                resolved,
            )
            candidate = CandidateResult(
                code=code,
                iteration=iteration,
                render=render_result,
                rendered_path=str(render_result.output_path) if render_result.output_path else None,
            )
            if render_result.success and render_result.output_path:
                candidate.score = compare_audio(
                    target_analysis,
                    Path(render_result.output_path),
                    code=code,
                    config=resolved,
                )
            iteration_results.append(candidate)
            write_json(iteration_dir / f"{base_name}.json", candidate.model_dump(mode="json"))
            write_text(iteration_dir / f"{base_name}.strudel", code)

        ranked = sorted(
            iteration_results,
            key=lambda item: item.score.total_score if item.score else -1.0,
            reverse=True,
        )
        all_candidates.extend(iteration_results)
        if ranked and (best_candidate is None or _score_of(ranked[0]) > _score_of(best_candidate)):
            best_candidate = ranked[0]

        if iteration >= opts.iterations - 1:
            break

        survivors = ranked[: opts.beam_width]
        next_batch = candidate_generator.generate_refined_candidates(
            description,
            survivors,
            candidate_count=opts.candidate_count,
        )
        frontier = next_batch.candidates or [candidate.code for candidate in survivors]

    manifest = RunManifest(
        run_id=run_dir.name,
        target_path=target_path,
        run_dir=run_dir,
        theory_description=description,
        candidates=all_candidates,
        best_candidate=best_candidate,
        metadata={
            "iterations": opts.iterations,
            "candidate_count": opts.candidate_count,
            "beam_width": opts.beam_width,
            "cycles": opts.cycles,
            "cps": opts.cps,
        },
    )
    write_json(run_dir / "manifest.json", manifest.model_dump(mode="json"))
    return manifest


def _score_of(candidate: CandidateResult) -> float:
    return candidate.score.total_score if candidate.score else -1.0


def describe_candidate(candidate: CandidateResult) -> str:
    if candidate.score is None:
        return "Candidate failed before scoring."
    breakdown = candidate.score.breakdown
    return (
        f"score={candidate.score.total_score:.4f}, "
        f"chroma={breakdown.chroma:.4f}, mfcc={breakdown.mfcc:.4f}, "
        f"onset={breakdown.onset:.4f}, tempo={breakdown.tempo:.4f}, "
        f"duration={breakdown.duration:.4f}, loudness={breakdown.loudness:.4f}"
    )

