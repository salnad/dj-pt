from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    manifest_path = root / "benchmarks" / "simple" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    targets_dir = root / "benchmarks" / "generated"
    targets_dir.mkdir(parents=True, exist_ok=True)

    for fixture in manifest.get("fixtures", []):
        target_path = targets_dir / f"{fixture['fixture_id']}.wav"
        target_path.write_text(
            "Placeholder benchmark target. Generate with `djpt benchmark --render-fixtures` once renderer is available.\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
