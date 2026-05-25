# Hugging Face: prepare models

OVS (Offline Video Scribe) is **offline-only** at runtime. It does **not** download weights, store tokens, or contact huggingface.co during `check`, `transcribe`, or `watch`.

Use the **Hugging Face CLI** (`hf`) once to populate `~/.cache/huggingface/hub`, then use `offline-video-scribe`.

**Install:** [INSTALL.md](INSTALL.md) — `install.sh` **asks** before downloading models; you can skip and follow this guide instead.

When using `./install.sh`, `HF_HOME` defaults to `~/.cache/huggingface`. For manual downloads:

```bash
export HF_HOME="${HF_HOME:-$HOME/.cache/huggingface}"
export HF_HUB_CACHE="${HF_HUB_CACHE:-$HF_HOME/hub}"
```

---

## Step-by-step (default config)

### 1. Install the Hugging Face CLI

```bash
brew install huggingface-cli
# or: pip install -U "huggingface_hub[cli]"
hf --version
```

### 2. Log in (read token)

```bash
hf auth login
# Paste a read token from https://huggingface.co/settings/tokens
# Or set for this shell only:
# export HF_TOKEN="hf_..."
```

Verify:

```bash
hf whoami
```

### 3. Accept gated terms (diarization only)

Default config uses **pyannote/speaker-diarization-community-1**, which is **gated**.

1. Log in at https://huggingface.co (same account as your token).
2. Open https://huggingface.co/pyannote/speaker-diarization-community-1
3. Click **Agree and access repository** (CC-BY-4.0).

Skip this step if you set `diarization: false` in config (Whisper-only).

### 4. Download Whisper (transcription)

Default `model: medium` → **mlx-community/whisper-medium-mlx** (~1 GB):

```bash
hf download mlx-community/whisper-medium-mlx \
  --include "config.json" \
  --include "weights.npz"
```

Confirm the weight file is full size (not an LFS pointer):

```bash
ls -lh ~/.cache/huggingface/hub/models--mlx-community--whisper-medium-mlx/snapshots/*/weights.npz
# expect ~1 GB for medium
```

### 5. Download pyannote (speaker diarization)

```bash
hf download pyannote/speaker-diarization-community-1
```

### 6. Verify with OVS

```bash
offline-video-scribe check
# or: offline-video-scribe check --verbose
```

Expected last line:

```text
offline-video-scribe: ready (offline — local models verified)
```

Weights live under `~/.cache/huggingface/hub` (not in the OVS git repo). OVS also reads a legacy cache at `~/.cache/digg/ovs/huggingface/hub` if the standard path is empty.

---

## Quick copy-paste (default config)

```bash
hf auth login
# Browser: https://huggingface.co/pyannote/speaker-diarization-community-1 → Agree

hf download mlx-community/whisper-medium-mlx --include "config.json" --include "weights.npz"
hf download pyannote/speaker-diarization-community-1

offline-video-scribe check
```

---

## Repos per config value

| Config | `hf download` repo | Notes |
|--------|-------------------|--------|
| `model: medium` | `mlx-community/whisper-medium-mlx` | `--include "config.json" --include "weights.npz"` |
| `model: medium-8bit` | `mlx-community/whisper-medium-mlx-8bit` | same includes |
| `model: small` | `mlx-community/whisper-small-mlx` | same includes |
| `model: large-v3` | `mlx-community/whisper-large-v3-mlx` | ~3 GB |
| `diarization_pipeline` (default) | `pyannote/speaker-diarization-community-1` | **Gated** — accept terms first |

After changing `model` or `diarization_pipeline` in `~/.config/digg/offline-video-scribe/config.yaml`, run the matching `hf download` commands, then `offline-video-scribe check`.

### Whisper-only (no diarization)

```yaml
# ~/.config/digg/offline-video-scribe/config.yaml
diarization: false
```

```bash
hf download mlx-community/whisper-medium-mlx --include "config.json" --include "weights.npz"
offline-video-scribe check
```

---

## Gated models (403 errors)

A **gated** model requires:

1. A valid **access token** (`hf auth login` or `HF_TOKEN`)
2. **Accepted user conditions** on the model page (same HF account)

If either is missing, `hf download` fails with:

```text
GatedRepoError: 403 Client Error
Cannot access gated repo … you are not in the authorized list
```

### Fix a 403 on pyannote

1. Log in at https://huggingface.co (same account as your token).
2. Open https://huggingface.co/pyannote/speaker-diarization-community-1
3. Click **Agree and access repository**.
4. Retry: `hf download pyannote/speaker-diarization-community-1`

---

## Licenses

OVS does not ship these weights; you download them under each publisher’s terms.

| Component | Repo | Access | License |
|-----------|------|--------|---------|
| Transcription (`medium`) | [mlx-community/whisper-medium-mlx](https://huggingface.co/mlx-community/whisper-medium-mlx) | Open | Whisper (MIT) + mlx-community conversion — see repo README |
| Diarization (default) | [pyannote/speaker-diarization-community-1](https://huggingface.co/pyannote/speaker-diarization-community-1) | **Gated** | [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/) |
| Legacy diarization | [pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1) | **Gated** (separate acceptance) | See that model page |

**OVS** code is MIT (`LICENSE`); that does not cover downloaded weights.

---

## Token storage (for `hf` CLI only)

OVS does **not** read Keychain or `HF_TOKEN`. The Hugging Face CLI stores credentials for downloads:

| Method | Storage |
|--------|---------|
| `hf auth login` | macOS Keychain (`huggingface.co` / `hf_user`) or `~/.cache/huggingface/token` |
| `export HF_TOKEN="hf_..."` | Environment (used by `hf download` in that shell) |

```bash
hf auth login
hf whoami
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `check` says whisper not ready, folder exists | Re-download with `--include "weights.npz"`; file should be ~1 GB, not ~100 bytes (LFS pointer) |
| 403 on pyannote | Accept terms on the model page, then `hf download` again |
| Wrong model in config | `hf download` the repo for your `model` / `diarization_pipeline`, then `offline-video-scribe check` |

```bash
offline-video-scribe check --verbose
```

---

## What OVS verifies offline

`offline-video-scribe check` confirms:

- Whisper: `config.json` + full weight file (≥ 1 MB) under a hub **snapshot** directory
- Diarization (if enabled): `config.yaml`, weight files, and a local pyannote load test

Runtime sets `HF_HUB_OFFLINE=1` so huggingface_hub cannot reach the network during transcribe/watch.
