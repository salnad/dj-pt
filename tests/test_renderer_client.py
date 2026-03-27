from __future__ import annotations

from pathlib import Path

from djpt.config import AppConfig
from djpt.renderer_client import render_strudel
from djpt.schemas import RenderRequest


def test_renderer_client_reports_missing_script(tmp_path: Path) -> None:
    config = AppConfig.from_env()
    config = config.model_copy(update={"renderer_root": tmp_path / "renderer-missing"})

    request = RenderRequest(
        code='note("c3").s("sine")',
        output_path=tmp_path / "out.wav",
    )
    result = render_strudel(request, config)

    assert result.success is False
    assert result.error is not None
    assert "Renderer script not found" in result.error
