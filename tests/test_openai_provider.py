from djpt.llm.generation import DeterministicAudioToCodeProvider
from djpt.llm.description import build_structured_description
from djpt.schemas import AudioAnalysis


def _analysis() -> AudioAnalysis:
    return AudioAnalysis(
        path="example.wav",
        sample_rate=32000,
        duration_seconds=1.0,
        tempo_bpm=120.0,
        estimated_key="C",
        top_pitch_classes=["C", "E", "G", "B"],
    )


def test_deterministic_provider_describe_returns_fallback():
    provider = DeterministicAudioToCodeProvider()
    description = build_structured_description(_analysis())
    assert provider.describe(
        feature_summary=description.feature_summary,
        deterministic_description=description.deterministic_description,
    ) == description.deterministic_description
