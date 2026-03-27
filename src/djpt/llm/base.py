from __future__ import annotations

from typing import Any, Protocol, Sequence

from djpt.schemas import CandidateBatch, CandidateResult, StructuredTheoryDescription


class AudioToCodeProvider(Protocol):
    name: str

    def describe(
        self,
        *,
        feature_summary: dict[str, Any],
        deterministic_description: str,
    ) -> str | None:
        ...

    def generate_candidates(
        self,
        *,
        description: StructuredTheoryDescription,
        prompt_name: str,
        candidate_count: int,
        top_candidates: Sequence[CandidateResult] | None = None,
    ) -> CandidateBatch:
        ...


def provider_name(provider: AudioToCodeProvider) -> str:
    return getattr(provider, "name", provider.__class__.__name__.lower())
