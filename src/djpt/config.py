from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field


load_dotenv()


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_root: Path
    renderer_root: Path
    prompts_root: Path
    benchmarks_root: Path
    runs_root: Path
    default_sample_rate: int = 32000
    default_mono: bool = True
    default_cycles: float = 4.0
    default_cps: float = 0.5
    max_polyphony: int = 16
    default_iterations: int = 3
    default_candidate_count: int = 4
    default_beam_width: int = 2
    chrome_executable: str = "/usr/local/bin/google-chrome"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    render_build_on_demand: bool = True
    ffmpeg_binary: str = "ffmpeg"
    ffprobe_binary: str = "ffprobe"

    @classmethod
    def from_env(cls, workspace_root: Path | None = None) -> "AppConfig":
        root = workspace_root or Path(__file__).resolve().parents[2]
        return cls(
            workspace_root=root,
            renderer_root=root / "renderer",
            prompts_root=root / "prompts",
            benchmarks_root=root / "benchmarks",
            runs_root=root / "runs",
            default_sample_rate=int(os.getenv("DJPT_SAMPLE_RATE", "32000")),
            default_mono=os.getenv("DJPT_DEFAULT_MONO", "1") != "0",
            default_cycles=float(os.getenv("DJPT_DEFAULT_CYCLES", "4.0")),
            default_cps=float(os.getenv("DJPT_DEFAULT_CPS", "0.5")),
            max_polyphony=int(os.getenv("DJPT_MAX_POLYPHONY", "16")),
            default_iterations=int(os.getenv("DJPT_DEFAULT_ITERATIONS", "3")),
            default_candidate_count=int(os.getenv("DJPT_DEFAULT_CANDIDATES", "4")),
            default_beam_width=int(os.getenv("DJPT_DEFAULT_BEAM_WIDTH", "2")),
            chrome_executable=os.getenv("DJPT_CHROME_PATH", "/usr/local/bin/google-chrome"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_model=os.getenv("DJPT_OPENAI_MODEL", "gpt-4.1-mini"),
            render_build_on_demand=os.getenv("DJPT_RENDER_BUILD_ON_DEMAND", "1") != "0",
            ffmpeg_binary=os.getenv("DJPT_FFMPEG", "ffmpeg"),
            ffprobe_binary=os.getenv("DJPT_FFPROBE", "ffprobe"),
        )

    def ensure_directories(self) -> "AppConfig":
        self.runs_root.mkdir(parents=True, exist_ok=True)
        return self


class PromptConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_candidates: int = Field(default=4, ge=1, le=12)
    max_prompt_characters: int = Field(default=220, ge=40)
    max_code_lines: int = Field(default=4, ge=1)


settings = AppConfig.from_env().ensure_directories()
