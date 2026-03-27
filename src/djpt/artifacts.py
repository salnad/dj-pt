from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from djpt.config import AppConfig, settings


def timestamp_id() -> str:
    return datetime.now(UTC).strftime("%Y%m%d-%H%M%S")


def create_run_dir(prefix: str = "run", config: AppConfig | None = None) -> Path:
    resolved = config or settings
    base = resolved.runs_root
    attempt = 0
    while True:
        suffix = timestamp_id() if attempt == 0 else f"{timestamp_id()}-{attempt}"
        run_dir = base / f"{prefix}-{suffix}"
        try:
            run_dir.mkdir(parents=True, exist_ok=False)
            return run_dir
        except FileExistsError:
            attempt += 1


def write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True, default=str)
        handle.write("\n")
    return path


def write_text(path: Path, contents: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents, encoding="utf-8")
    return path
