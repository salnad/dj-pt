from __future__ import annotations

import json
from pathlib import Path

from djpt.benchmark import load_manifest
from djpt.config import AppConfig
from djpt.renderer_client import render_strudel
from djpt.schemas import RenderRequest


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    config = AppConfig.from_env(root)
    manifest_path = root / "benchmarks" / "simple" / "manifest.json"
    targets_dir = root / "benchmarks" / "generated"
    targets_dir.mkdir(parents=True, exist_ok=True)

    rendered = []
    for fixture in load_manifest(manifest_path):
        code = fixture.code_path.read_text(encoding="utf-8").strip()
        target_path = targets_dir / f"{fixture.fixture_id}.wav"
        result = render_strudel(
            RenderRequest(
                code=code,
                output_path=target_path,
                cycles=fixture.cycles,
                cps=fixture.cps,
                sample_rate=config.default_sample_rate,
                max_polyphony=config.max_polyphony,
                format="wav",
            ),
            config,
        )
        rendered.append(
            {
                "fixture_id": fixture.fixture_id,
                "success": result.success,
                "output_path": str(result.output_path) if result.output_path else None,
                "error": result.error,
            }
        )

    print(json.dumps({"rendered": rendered}, indent=2))


if __name__ == "__main__":
    main()
