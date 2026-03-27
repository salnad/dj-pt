from __future__ import annotations

from pathlib import Path

from djpt.config import AppConfig
from djpt.optimize.search import FitOptions


def test_fit_options_defaults(tmp_path: Path) -> None:
    config = AppConfig.from_env(tmp_path)
    assert FitOptions().iterations == config.default_iterations
