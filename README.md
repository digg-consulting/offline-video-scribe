# Offline Video Scribe (OVS)

Turn a video file into `.txt`, `.srt`, and `.vtt` on your Mac. Everything runs locally; videos and transcripts stay **outside** this repo.

**CLI:** `offline-video-scribe` (`ovs` → symlink in `~/.local/bin`)  
**Design spec:** `~/Projects/docs/superpowers/specs/2026-05-20-transcripto-design.md`  
**Prepare models (Hugging Face CLI):** [docs/HUGGINGFACE.md](docs/HUGGINGFACE.md)  
**Future macOS installer (`/opt`):** [docs/INSTALLER.md](docs/INSTALLER.md)

---

## Two phases: Prepare → Use

| Phase | What | Network |
|-------|------|---------|
| **Prepare** (once) | `hf auth login`, accept gated terms, `hf download …` | Hugging Face CLI only |
| **Use** | `offline-video-scribe transcribe`, `watch` | **Offline only** — no HF calls, no tokens in OVS |

OVS **does not download models** and **does not store Hugging Face tokens**. All weights must be in `~/.cache/digg/ovs/huggingface/hub` before first use (see [XDG layout](#xdg-layout) below).

**One-time vs daily:** Run `offline-video-scribe setup` or `check` once after installing models. After that, use `offline-video-scribe transcribe` only — it rechecks local models automatically and stops with clear errors if something is missing (you do not need `check` every day).

---

## One-time install (recommended)

From the repo root (needs [uv](https://docs.astral.sh/uv/) and [Homebrew](https://brew.sh/)):

```bash
cd /path/to/offline-video-scribe
chmod +x install.sh    # once, if needed
./install.sh
```

That script runs, in order: `uv sync` → `uv tool install` (CLI on PATH) → `ln -sf` `ovs` → `offline-video-scribe` → `brew install ffmpeg huggingface-cli` → `hf auth login` (if needed) → model downloads → `offline-video-scribe setup`.

You will be prompted once for HF login; open the pyannote model page in the browser when the script asks (gated model). Re-run `./install.sh` if a download fails after accepting terms.

Manual steps and troubleshooting: [docs/HUGGINGFACE.md](docs/HUGGINGFACE.md).

### Uninstall

```bash
./uninstall.sh
```

Prompts you to **keep or delete** config, Hugging Face model cache, and transcript output. Always removes the `offline-video-scribe` CLI, `ovs` symlink, and repo `.venv`. Does not remove Homebrew packages, `hf` login, or the git repo.

```bash
./uninstall.sh --dry-run   # preview
./uninstall.sh -y          # defaults: remove config; keep models & transcripts
```

**Already have models cached?** The script skips `hf download` when `offline-video-scribe check` passes.

**Whisper-only** (no diarization): set `diarization: false` in config, then `SKIP_HF=1 ./install.sh` after Whisper is cached, or edit repos before install:

```bash
WHISPER_REPO=mlx-community/whisper-small-mlx ./install.sh
```

---

## XDG layout

OVS follows the [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html) under the `digg/ovs` namespace:

| Purpose | Path |
|---------|------|
| Config, preferences, settings | `~/.config/digg/ovs/` (`config.yaml`, `config.yaml.example`) |
| Cache (HF models) | `~/.cache/digg/ovs/huggingface/hub` |
| Data (tool install, libraries) | `~/.local/share/digg/ovs/tool/` |
| CLI executable | `~/.local/bin/offline-video-scribe` (`ovs` → symlink) |

`./install.sh` sets `HF_HOME`, `UV_TOOL_DIR`, and `PATH` accordingly. Existing installs under `~/.config/ovs` or `~/.cache/huggingface` are still detected until you migrate or re-download.

Override config: `export OVS_CONFIG=/path/to/config.yaml`

---

## Prerequisites checklist

| Step | Command / action |
|------|------------------|
| ffmpeg | `brew install ffmpeg` |
| Hugging Face CLI | `brew install huggingface-cli` (or `pip install -U "huggingface_hub[cli]"`) |
| HF login | `hf auth login` then `hf whoami` — [docs/HUGGINGFACE.md](docs/HUGGINGFACE.md) |
| **Gated model access** | Open [pyannote/speaker-diarization-community-1](https://huggingface.co/pyannote/speaker-diarization-community-1) → **Agree** (same HF account) |
| Download Whisper | `hf download mlx-community/whisper-medium-mlx --include "config.json" --include "weights.npz"` |
| Download diarization | `hf download pyannote/speaker-diarization-community-1` |
| Config + verify | `offline-video-scribe setup` or `check` |

Expected `check` output when ready:

```text
ffmpeg: ok
mlx-whisper: ok
pyannote.audio: ok
model whisper/medium (mlx-community/whisper-medium-mlx): ready
model diarization (pyannote/speaker-diarization-community-1): ready
diarization: enabled (pyannote/speaker-diarization-community-1)
offline-video-scribe: ready (offline — local models verified)
```

**Folder exists but `check` says not ready?** Hugging Face may have only stored LFS pointers (~100 bytes). Run `offline-video-scribe check --verbose`, then re-download:

```bash
hf download mlx-community/whisper-medium-mlx --include "config.json" --include "weights.npz"
hf download pyannote/speaker-diarization-community-1
```

`weights.npz` for `medium` should be about **1 GB**, not a tiny pointer file.

---

## Daily use (one command)

After the one-time prepare + `offline-video-scribe setup` above:

```bash
offline-video-scribe transcribe ~/Movies/your-recording.mov
```

Run `offline-video-scribe check` again only if you change `model` in config, re-download weights, or something fails.

Default **`archive`** mode: one folder under `output_dir` with the video + transcripts:

```text
~/Transcripts/your-recording/
  your-recording.mov
  your-recording.vtt
```

VTT/SRT use **Speaker 1**, **Speaker 2**, … (diarization on by default).

**Disable diarization:** `diarization: false` in config, or `--no-diarization`.

---

## Commands

| Command | Purpose |
|---------|---------|
| `init` | Install config file only |
| `setup` | Config + offline prerequisite check |
| `check` | Verify ffmpeg, deps, local model cache (offline) |
| `transcribe <path>` | Transcribe (local models only) |
| `watch` | Watch folders for new videos |

---

## Models

| Config `model` | Hugging Face repo | Approx. size | Gated? |
|----------------|-------------------|--------------|--------|
| `medium` (default) | `mlx-community/whisper-medium-mlx` | ~1 GB | No |
| `medium-8bit` | `mlx-community/whisper-medium-mlx-8bit` | smaller | No |
| `small` | `mlx-community/whisper-small-mlx` | smaller | No |
| `large-v3` | `mlx-community/whisper-large-v3-mlx` | ~3 GB | No |

**Diarization (default on):** `pyannote/speaker-diarization-community-1` — **gated**, [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/). Accept terms on Hugging Face before `hf download`.

**`hf download` per model** (after changing config):

```bash
# Whisper (always include config + weights)
hf download mlx-community/whisper-medium-mlx --include "config.json" --include "weights.npz"
hf download mlx-community/whisper-small-mlx --include "config.json" --include "weights.npz"
hf download mlx-community/whisper-large-v3-mlx --include "config.json" --include "weights.npz"

# Diarization (gated — accept terms on model page first)
hf download pyannote/speaker-diarization-community-1
```

Then `offline-video-scribe check`. See [docs/HUGGINGFACE.md](docs/HUGGINGFACE.md) for the full table and troubleshooting.

---

## Advanced

<details>
<summary>Output modes, uv run, global CLI, developers</summary>

**Output modes:** `archive` (default), `beside`, `mirror`, `flat` — see `config/config.yaml.example`.

**Without activating venv:** `uv run offline-video-scribe …` from the repo directory, or `./bin/offline-video-scribe …`.

**Global CLI:** `./install.sh` or `uv tool install -e .` plus `ln -sf` — installs `offline-video-scribe`; `~/.local/bin/ovs` points at it

**Developers:** `pytest -v`

</details>

## License

MIT
