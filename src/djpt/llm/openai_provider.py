from __future__ import annotations

import json
from typing import Sequence

from openai import OpenAI

from djpt.config import AppConfig
from djpt.llm.base import AudioToCodeProvider
from djpt.llm.generation import build_refinement_prompt, build_theory_to_strudel_prompt, load_prompt
from djpt.schemas import CandidateBatch, CandidateResult, StructuredTheoryDescription


class OpenAIProvider(AudioToCodeProvider):
    name = "openai"

    def __init__(self, config: AppConfig | None = None):
        self._config = config or AppConfig.from_env()
        self._client = OpenAI(api_key=self._config.openai_api_key)

    def describe(
        self,
        *,
        feature_summary: dict,
        deterministic_description: str,
    ) -> str | None:
        if not self._config.openai_api_key:
            return None

        template = load_prompt("audio_to_theory.md")
        user_prompt = template.format(
            feature_summary_json=json.dumps(feature_summary, indent=2, sort_keys=True),
        )
        response = self._client.responses.create(
            model=self._config.openai_model,
            input=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "Rewrite structured audio features into a short, music-theory-oriented "
                                "description. Be factual and concise."
                            ),
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": f"{user_prompt}\n\nDeterministic fallback:\n{deterministic_description}",
                        }
                    ],
                },
            ],
            temperature=0.2,
        )
        return self._extract_text(response)

    def generate_candidates(
        self,
        *,
        description: StructuredTheoryDescription,
        prompt_name: str,
        candidate_count: int,
        top_candidates: Sequence[CandidateResult] | None = None,
    ) -> CandidateBatch:
        if not self._config.openai_api_key:
            return CandidateBatch(candidates=[], raw_response=None)

        if prompt_name == "refine_strudel":
            user_prompt = build_refinement_prompt(
                description,
                top_candidates or [],
                candidate_count,
            )
        else:
            prior_best = top_candidates[0] if top_candidates else None
            user_prompt = build_theory_to_strudel_prompt(description, candidate_count, prior_best=prior_best)

        response = self._client.responses.create(
            model=self._config.openai_model,
            input=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "You write concise, valid synth-only Strudel code. "
                                "Return strict JSON with a top-level 'candidates' array of strings."
                            ),
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": user_prompt}],
                },
            ],
            temperature=0.35,
            text={"format": {"type": "json_object"}},
        )
        raw = self._extract_text(response)
        if not raw:
            return CandidateBatch(candidates=[], raw_response=None)

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return CandidateBatch(candidates=[], raw_response=raw)

        candidates: list[str] = []
        for item in data.get("candidates", []):
            if isinstance(item, str) and item.strip():
                candidates.append(item.strip().strip("`"))
        return CandidateBatch(candidates=candidates[:candidate_count], raw_response=raw)

    @staticmethod
    def _extract_text(response: object) -> str | None:
        text = getattr(response, "output_text", None)
        if text:
            return text.strip()

        chunks: list[str] = []
        for item in getattr(response, "output", []):
            for content in getattr(item, "content", []):
                chunk = getattr(content, "text", None)
                if chunk:
                    chunks.append(chunk)
        if chunks:
            return "\n".join(chunks).strip()
        return None
