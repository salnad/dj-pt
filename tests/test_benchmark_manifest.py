from pathlib import Path

from djpt.benchmark import load_manifest


def test_load_manifest_parses_fixture_models() -> None:
    manifest = load_manifest(Path("benchmarks/simple/manifest.json"))
    assert len(manifest) == 3
    assert manifest[0].fixture_id == "bright-arp"
