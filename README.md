# Offline Video Scribe (OVS)

Turn a video file into `.txt`, `.srt`, and `.vtt` on your Mac. Everything runs locally; videos and transcripts stay **outside** this repo.

**CLI:** `offline-video-scribe` (`ovs` → symlink in `~/.local/bin`)  
**Install (release tarball, no git clone):** [docs/INSTALL.md](docs/INSTALL.md)  
**Distribution notes:** [docs/INSTALLER.md](docs/INSTALLER.md)  
**Prepare models (Hugging Face CLI):** [docs/HUGGINGFACE.md](docs/HUGGINGFACE.md)

---

## Two phases: Prepare → Use

| Phase | What | Network |
|-------|------|---------|
| **Prepare** (once) | `hf auth login`, accept gated terms, `hf download …` | Hugging Face CLI only |
| **Use** | `offline-video-scribe transcribe`, `watch` | **Offline only** — no HF calls, no tokens in OVS |

OVS **does not download models** and **does not store Hugging Face tokens**. All weights must be in `~/.cache/huggingface/hub` before first use (see [XDG layout](#xdg-layout) below).

**One-time vs daily:** Run `offline-video-scribe setup` or `check` once after installing models. After that, use `offline-video-scribe transcribe` only — it rechecks local models automatically and stops with clear errors if something is missing (you do not need `check` every day).

---

## Install (no git clone)

**End users:** download a release tarball or use the bootstrap script — see **[docs/INSTALL.md](docs/INSTALL.md)**.

```bash
# Pin a version (recommended)
curl -fsSL https://raw.githubusercontent.com/digg-consulting/offline-video-scribe/main/scripts/bootstrap-install.sh | OVS_VERSION=0.1.0 bash
```

Or download `offline-video-scribe-<version>-macos.tar.gz` from [GitHub Releases](https://github.com/digg-consulting/offline-video-scribe/releases), extract, and run `./install.sh`.

**Developers:** clone this repo and run `./install.sh` from the root (includes test dependencies).

`install.sh` installs the CLI (`uv sync`, `uv tool install`, `ovs` symlink). It **asks** before Homebrew packages (`ffmpeg`, `huggingface-cli`) and before downloading models. `offline-video-scribe check` / `transcribe` enforce the model cache at runtime.

| Script | Purpose |
|--------|---------|
| `./install.sh` | First-time install (prompts for brew/models) |
| `./update.sh` | Upgrade CLI (new release tarball or `git pull` in clone) — [docs/INSTALL.md#upgrade](docs/INSTALL.md#upgrade) |
| `./install.sh -y` | Non-interactive install |
| `SKIP_HF=1 ./install.sh` | Skip Hugging Face prompts |

**Maintainers — publish a release:** [docs/RELEASE.md](docs/RELEASE.md) (`./scripts/publish-release.sh` pushes `v*` tag → GitHub Actions uploads tarball)

Manual model steps: [docs/HUGGINGFACE.md](docs/HUGGINGFACE.md).

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

OVS follows the [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html) under the `digg/offline-video-scribe` namespace:

| Purpose | Path |
|---------|------|
| Config, preferences, settings | `~/.config/digg/offline-video-scribe/` (`config.yaml`, `config.yaml.example`) |
| Cache (HF models) | `~/.cache/huggingface/hub` |
| Data (uv tool install) | `~/.local/share/digg/offline-video-scribe/` |
| CLI executable | `~/.local/bin/offline-video-scribe` (`ovs` → symlink) |

`./install.sh` sets `HF_HOME` (default `~/.cache/huggingface`), `UV_TOOL_DIR` to the data path above, and `PATH` accordingly. Legacy dirs under `digg/ovs` are still read for config and HF cache when present.

Override config: `export OVS_CONFIG=/path/to/config.yaml`

---

## Prerequisites checklist

During `./install.sh`, you are **prompted** before installing Homebrew packages and before downloading models (see [docs/INSTALL.md](docs/INSTALL.md)). Or prepare manually:

| Step | Command / action |
|------|------------------|
| ffmpeg | `brew install ffmpeg` (or agree when `install.sh` asks) |
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

**`.vtt`** is the closed-caption source of truth: per-segment `start --> end` cues with **Speaker 1**, **Speaker 2**, … (diarization on by default). **`.txt`** is derived from that same VTT content — without diarization it mirrors the VTT cue layout; with diarization it is reformatted for reading (`M:SS | Speaker N` headers, consecutive same-speaker cues bundled). SRT uses the same per-cue speaker labels as VTT.

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

**Global CLI:** `./install.sh` (clone or release tarball), or `uv tool install -e .` from a clone

**Release:** `./scripts/make-release.sh` — publish `dist/*.tar.gz` on a GitHub Release (`v*` tag)

**Developers:** `pytest -v` (from git clone; `uv sync` includes dev deps)

</details>

## License

MIT
