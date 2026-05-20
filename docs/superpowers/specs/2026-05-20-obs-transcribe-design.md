# obs-transcribe — Design Spec

**Date:** 2026-05-20  
**Status:** Approved (brainstorming)  
**Approach:** Python CLI + mlx-whisper (fully local, Apple Silicon)

---

## Summary

Local transcription tool for OBS `.mov` recordings. Extracts audio with ffmpeg, transcribes with mlx-whisper on Apple Silicon, and writes plain text plus subtitle formats. Supports one-shot CLI runs and an optional watch-folder daemon. No cloud APIs; audio stays on the Mac.

---

## Repository & delivery

| Item | Value |
|------|-------|
| **Local path** | `/Users/gadoury/github/digg-consulting/obs-transcribe` |
| **GitHub** | Private repository under the `digg-consulting` GitHub org/account (create during implementation) |
| **Sibling projects** | Same parent folder as `article-to-pdf-app`, `cursor-ollama-gateway` |

Implementation plan should include: `git init`, initial commit, `gh repo create --private` (or equivalent), and push. Not required for v1 feature code to function locally.

---

## Requirements

| Area | Decision |
|------|----------|
| Outputs | `.txt`, `.srt`, `.vtt`; optional `.json` (timed segments) |
| Privacy | Fully local |
| Interface | CLI + optional watch folder |
| Language | Mostly English; multilingual model + auto-detect per file |
| Typical length | 15–60 minutes |
| Speakers | Nice-to-have later; not v1 |
| Output location | Configurable; default beside source file |
| Re-runs | Skip if outputs exist; `--force` to overwrite |
| Python tooling | **uv** (`uv sync`, `uv run`, `.python-version`) |

---

## Goals & scope

### v1 includes

- Transcribe OBS `.mov` (optional `.mp4`, `.mkv` via config)
- Emit `.txt`, `.srt`, `.vtt` (+ optional `.json`)
- CLI: single file, directory (recursive), `--force`, output mode flags
- Watch mode: monitor configured folders, queue jobs, skip existing outputs
- Config file for defaults
- Progress logging for long jobs
- `obs-transcribe check` for dependency verification

### v1 excludes

- GUI, cloud APIs, real-time streaming transcription
- Guaranteed speaker diarization (hooks only for v2)

### Dependencies

- Homebrew **ffmpeg**
- **uv** + Python 3.12+ (via `.python-version`)
- **mlx-whisper** + cached MLX models (first run downloads)

---

## Architecture

### Pipeline

```
.mov → ffmpeg (16 kHz mono WAV, temp) → mlx-whisper → writers → .txt / .srt / .vtt / .json
```

### Components

| Component | Responsibility |
|-----------|----------------|
| **CLI** | Parse args, load config, dispatch jobs |
| **Config** | `~/.config/obs-transcribe/config.yaml` defaults |
| **Job runner** | One recording → one job; `--force`; single-worker queue in watch mode |
| **Audio extractor** | ffmpeg → temp WAV; deleted after job |
| **Transcriber** | mlx-whisper; auto language detection |
| **Writers** | Plain text, SRT, VTT, optional JSON |
| **Watcher** | watchdog; debounce; enqueue new files |

### Job lifecycle

1. Discover inputs (filter by extension).
2. Skip if outputs exist and not `--force`.
3. Extract audio to temp.
4. Transcribe (reuse loaded model across batch/queue).
5. Write outputs per output mode.
6. Cleanup temp audio.

### Output modes

| Mode | Behavior |
|------|----------|
| `beside` (default) | Outputs next to source file |
| `mirror` | Preserve relative path under configurable root |
| `flat` | All outputs in one directory (unique basenames) |

CLI flags override config per run: `--output-mode`, `--output-dir`.

### Watch mode

- Command: `obs-transcribe watch`
- Debounce ~2s; optional stable file-size check before enqueue
- Single-worker queue (one transcription at a time)
- Graceful `Ctrl+C`; no partial final outputs until write step completes

### Model defaults

| Setting | Default |
|---------|---------|
| Model | `large-v3` (configurable; `medium` for speed) |
| Language | `auto` |
| Timestamps | Segment-level (sufficient for SRT/VTT) |

### v2 hook: speaker diarization

- Optional stage after transcription (e.g. pyannote)
- Config `diarization: true` + HF token; off by default
- Prefix lines in `.txt` with speaker labels when enabled

---

## CLI & config

### Commands

| Command | Purpose |
|---------|---------|
| `obs-transcribe transcribe <path>` | File or directory |
| `obs-transcribe watch` | Watch-folder daemon |
| `obs-transcribe init` | Write default config |
| `obs-transcribe check` | Verify ffmpeg, MLX, model cache |

### Key flags (`transcribe`)

| Flag | Effect |
|------|--------|
| `--force` | Re-transcribe even if outputs exist |
| `--output-mode` | `beside` \| `mirror` \| `flat` |
| `--output-dir` | Target for mirror/flat |
| `--model` | Whisper model size/name |
| `--language` | ISO hint or `auto` |
| `--formats` | e.g. `txt,srt,vtt,json` |
| `--recursive` | Walk subdirectories (default on for dirs) |

**Exit codes:** `0` success, `1` partial failure, `2` fatal (deps/config).

### Config example

```yaml
model: large-v3
language: auto
output_mode: beside
output_dir: ~/Transcripts
formats: [txt, srt, vtt]
watch:
  enabled: true
  paths:
    - ~/Movies/OBS
  debounce_seconds: 2
  extensions: [.mov, .mp4]
```

Env override: `OBS_TRANSCRIBE_CONFIG`.

### Error handling

| Failure | Behavior |
|---------|----------|
| Missing ffmpeg | Fail fast; hint `brew install ffmpeg` |
| No audio stream | Log error; continue batch |
| Transcription crash | No partial outputs; suggest smaller model |
| Disk full | Fail job; cleanup temp |
| File still recording | Debounce + stable-size check |

Logging to stderr; optional `--verbose`.

### Security & privacy

- No network after initial model download
- Temp audio deleted after each job
- Config paths only; no shell execution from config values

---

## uv workflow

| Task | Command |
|------|---------|
| Install | `uv sync` |
| Run CLI | `uv run obs-transcribe <command>` |
| Tests | `uv run pytest` |
| Python pin | `.python-version` (e.g. `3.12`) |

Dev dependencies in `[dependency-groups] dev` in `pyproject.toml`.

Optional post-v1: `uv tool install` for global CLI on PATH.

---

## Project layout

```
obs-transcribe/
├── .python-version
├── pyproject.toml          # uv-managed
├── README.md
├── src/obs_transcribe/
│   ├── cli.py
│   ├── config.py
│   ├── pipeline.py
│   ├── writers.py
│   ├── watcher.py
│   └── ffmpeg_util.py
├── tests/
│   └── fixtures/
└── docs/superpowers/specs/
    └── 2026-05-20-obs-transcribe-design.md
```

---

## Testing & verification

### Automated

- **Unit:** writers (segments → SRT/VTT), skip logic, output path resolution
- **Integration (slow):** short WAV through full pipeline
- **CLI:** `check`, `init`, transcribe on fixture

### Manual (definition of done)

1. `uv sync` && `uv run obs-transcribe check` passes after `brew install ffmpeg`
2. One real OBS `.mov` → `.txt`, `.srt`, `.vtt` beside file
3. Second run skips; `--force` overwrites
4. `watch` picks up new file in configured folder
5. README documents install and examples

### Performance (M4, ~30 min)

| Model | Rough wall time |
|-------|-----------------|
| `medium` | ~5–15 min |
| `large-v3` | ~10–25 min |

---

## Alternatives considered

| Approach | Why not chosen |
|----------|----------------|
| faster-whisper | Portable but slower on M4 vs MLX |
| whisper.cpp shell pipeline | Weak fit for watch folder + configurable outputs |
| Cloud APIs | User requirement: fully local |

---

## Next step

After spec approval: invoke **writing-plans** skill for implementation plan (scaffold repo, uv project, mlx-whisper pipeline, CLI, watcher, private GitHub publish).
