# djpt

`djpt` is an audio-to-Strudel experimentation harness for turning a target audio clip into:

- a structured music-theory-oriented description
- candidate Strudel code
- an offline-rendered audio file
- a similarity score with metric breakdown

The core idea is to make audio-to-code matching measurable and optimizable:

1. normalize and analyze a target `mp3`/`wav`
2. derive interpretable music features
3. generate concise Strudel candidates
4. render them offline with Strudel
5. score candidates against the target
6. iterate

## Status

This repository now contains the scaffolding for that system, including:

- a Python package for audio analysis, scoring, prompting, and orchestration
- a browser-based Strudel renderer subproject
- CLI entrypoints
- tests for scoring, calibration, search-loop plumbing, and CLI behavior

The project is intentionally **CLI-first**.

## Architecture

### Python

Python owns:

- audio normalization via `ffmpeg`
- feature extraction via `librosa`
- similarity scoring
- run artifact management
- LLM prompt orchestration
- iterative candidate search
- benchmark summarization

### Renderer

The `renderer/` subproject owns:

- loading Strudel in a browser context
- evaluating Strudel code
- offline rendering through Web Audio / `OfflineAudioContext`
- headless Chrome orchestration through Puppeteer

## Why this split?

Strudel audio rendering is browser-centric, while Python has the better ecosystem for audio analysis and optimization loops.

## Scoring philosophy

The inner loop uses **reference-based clip-vs-clip scoring**, not raw waveform MSE and not FAD as a primary metric.

Current baseline components:

- chroma similarity
- MFCC similarity
- onset envelope similarity
- tempo similarity
- duration similarity
- loudness similarity
- a soft conciseness penalty on generated code

This makes the score more stable and explainable than naive waveform diffing.

## Install

### Python

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Renderer

```bash
npm --prefix renderer install
npm --prefix renderer run build
```

If your Python environment does not support `venv`, this also works in the cloud VM:

```bash
python3 -m pip install --user -e ".[dev]" --break-system-packages
```

### Environment

Set:

```bash
export OPENAI_API_KEY=...
```

Optional overrides:

- `DJPT_CHROME_PATH`
- `DJPT_SAMPLE_RATE`
- `DJPT_DEFAULT_CPS`
- `DJPT_DEFAULT_CYCLES`

## CLI

### Print config

```bash
python3 -m djpt.cli config
```

### Analyze an audio file

```bash
python3 -m djpt.cli analyze path/to/input.mp3
```

### Render Strudel code

```bash
python3 -m djpt.cli render 'note("c3 eb3 g3").s("sawtooth")' runs/example.wav
```

### Score two files

```bash
python3 -m djpt.cli score path/to/target.wav path/to/candidate.wav
```

### Run the search harness

```bash
python3 -m djpt.cli fit path/to/target.mp3
```

### Inspect benchmark fixtures

```bash
python3 -m djpt.cli benchmark benchmarks/simple/manifest.json
```

### Generate benchmark targets from Strudel fixtures

```bash
python3 scripts/generate_benchmark_targets.py
```

## Benchmarks and prompt optimization

The repository includes hooks for:

- benchmark fixture manifests
- aggregate score reporting
- optional DSPy-based prompt optimization

These are structured to be optional so the baseline install remains lighter.

## Limitations

- This does **not** guarantee exact reconstruction of arbitrary audio.
- Matching quality is bounded by the Strudel palette and synthesis expressivity.
- The current intended MVP is **synth-first**.
- Thresholds are empirical and should be calibrated against benchmark fixtures.

## Licensing

This project is licensed under `AGPL-3.0-or-later` to align with the Strudel packages it integrates.