# transcripto macOS installer (planned)

**Status:** Design note — not shipped yet. Today you install from a git clone with `uv sync`.

## Goal

Users download a **single installer** (`.pkg` or `.dmg`) that:

1. Installs transcripto under a standard path, e.g. **`/opt/transcripto`**
2. Installs a CLI on **`PATH`** (e.g. `/opt/transcripto/bin/transcripto` → symlink in `/usr/local/bin`)
3. Writes config to **`~/.config/transcripto/config.yaml`**
4. Ensures **ffmpeg** is present (or prompts to install via Homebrew)
5. Guides **`hf auth login`** and accept **gated** [pyannote community-1](https://huggingface.co/pyannote/speaker-diarization-community-1) terms — see [HUGGINGFACE.md](HUGGINGFACE.md)
6. Runs **`hf download`** for Whisper + pyannote weights into `~/.cache/huggingface/hub`
7. Runs **`transcripto check`** (offline verification)

No git clone required for end users.

## Proposed layout

```text
/opt/transcripto/
  bin/transcripto
  bin/hf
  .venv/              # uv-managed Python env (mlx-whisper + pyannote)
  share/config.yaml.example
  share/doc/README.md
```

User data stays outside `/opt`:

| Data | Location |
|------|----------|
| Config | `~/.config/transcripto/config.yaml` |
| Model cache | `~/.cache/huggingface/` |
| Transcripts + archived videos | `~/Transcripts/` (configurable) |

## Installer phases

| Phase | Action |
|-------|--------|
| 1 | Copy payload to `/opt/transcripto` |
| 2 | `uv sync` or ship a pre-built venv in the package |
| 3 | `transcripto init` |
| 4 | `hf auth login` + accept pyannote terms |
| 5 | `hf download` (Whisper + pyannote per config) |
| 6 | `transcripto check` |

## Open decisions

- **Signed `.pkg`** vs unsigned script + Homebrew cask
- Whether to **bundle Python** or require Homebrew `python@3.12`
- **PyTorch size** in the package (~large); no way around it while using pyannote
- Updates: new `.pkg` vs `transcripto self-update` (out of scope for v1)

## Interim (today)

From a clone:

```bash
./install.sh
```

That runs the full one-time flow (uv, CLI on PATH, Homebrew tools, HF downloads, `transcripto setup`). See [HUGGINGFACE.md](HUGGINGFACE.md) for manual steps. It does **not** install to `/opt` yet.
