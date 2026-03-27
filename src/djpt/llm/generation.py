from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from djpt.llm.base import AudioToCodeProvider
from djpt.schemas import CandidateBatch, CandidateResult, SimilarityReport, StructuredTheoryDescription


def load_prompt(name: str) -> str:
    prompt_path = Path(__file__).resolve().parents[3] / "prompts" / name
    return prompt_path.read_text(encoding="utf-8").strip()


def build_theory_to_strudel_prompt(
    description: StructuredTheoryDescription,
    candidate_count: int,
    prior_best: CandidateResult | None = None,
) -> str:
    template = load_prompt("theory_to_strudel.md")
    description_json = json.dumps(description.model_dump(mode="json"), indent=2)
    prior_json = json.dumps(prior_best.model_dump(mode="json"), indent=2) if prior_best else "null"
    return template.format(
        description_json=description_json,
        candidate_count=candidate_count,
        prior_best_json=prior_json,
    )


def build_refinement_prompt(
    description: StructuredTheoryDescription,
    top_candidates: Iterable[CandidateResult],
    candidate_count: int,
) -> str:
    template = load_prompt("refine_strudel.md")
    candidates_json = json.dumps([candidate.model_dump(mode="json") for candidate in top_candidates], indent=2)
    description_json = json.dumps(description.model_dump(mode="json"), indent=2)
    return template.format(
        description_json=description_json,
        candidates_json=candidates_json,
        candidate_count=candidate_count,
    )


@dataclass(slots=True)
class CandidateGenerator:
    provider: AudioToCodeProvider

    def generate_initial_candidates(
        self,
        description: StructuredTheoryDescription,
        candidate_count: int = 4,
    ) -> CandidateBatch:
        return self.provider.generate_candidates(
            description=description,
            prompt_name="theory_to_strudel",
            candidate_count=candidate_count,
        )

    def generate_refined_candidates(
        self,
        description: StructuredTheoryDescription,
        top_candidates: Iterable[CandidateResult],
        candidate_count: int = 4,
    ) -> CandidateBatch:
        return self.provider.generate_candidates(
            description=description,
            prompt_name="refine_strudel",
            candidate_count=candidate_count,
            top_candidates=list(top_candidates),
        )


@dataclass(slots=True)
class DeterministicAudioToCodeProvider:
    """Fallback provider that emits simple synth-only candidates without an API call."""

    name: str = "deterministic"

    def describe(
        self,
        *,
        feature_summary: dict[str, object],
        deterministic_description: str,
    ) -> str | None:
        return deterministic_description

    def generate_candidates(
        self,
        *,
        description: StructuredTheoryDescription,
        prompt_name: str,
        candidate_count: int = 4,
        top_candidates: list[CandidateResult] | None = None,
    ) -> CandidateBatch:
        tempo_bpm = description.feature_summary.get("tempo_bpm") or 120.0
        cps = max(round(float(tempo_bpm) / 240.0, 3), 0.125)
        key = (description.feature_summary.get("estimated_key") or "C").replace("#", "s")

        seeds = [
            f'setcps({cps})\n$: note("{key}4 {key}4 {key}5 {key}4").s("sine")',
            f'setcps({cps})\n$: note("{key}2 ~ {key}2 ~").s("square").slow(2)',
            f'setcps({cps})\n$: note("{key}4 {key}5").s("triangle").fast(2)',
            f'setcps({cps})\n$: note("{key}3").s("sawtooth").slow(4)',
        ]
        if top_candidates:
            seeds = [candidate.code for candidate in top_candidates] + seeds
        unique = []
        seen = set()
        for code in seeds:
            if code not in seen:
                unique.append(code)
                seen.add(code)
        return CandidateBatch(candidates=unique[:candidate_count], raw_response="deterministic")


def candidate_result_from_score(
    *,
    code: str,
    iteration: int,
    score: SimilarityReport | None = None,
    prompt_name: str | None = None,
    critique: str | None = None,
) -> CandidateResult:
    return CandidateResult(
        code=code,
        iteration=iteration,
        score=score,
        prompt_name=prompt_name,
        critique=critique,
    )
