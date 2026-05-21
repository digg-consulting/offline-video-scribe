#!/usr/bin/env bash
# One-time install: Python env, CLI on PATH, Homebrew tools, HF models, OVS setup.
# Usage: ./install.sh
# Re-run is safe (skips steps that already succeeded).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

WHISPER_REPO="${WHISPER_REPO:-mlx-community/whisper-medium-mlx}"
DIARIZATION_REPO="${DIARIZATION_REPO:-pyannote/speaker-diarization-community-1}"
PYANNOTE_GATE_URL="https://huggingface.co/pyannote/speaker-diarization-community-1"
SKIP_HF="${SKIP_HF:-0}"

step() { echo ""; echo "==> $*"; }

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

step "Checking uv"
need_cmd uv

step "Installing Python dependencies (uv sync)"
uv sync

step "Installing OVS on PATH (uv tool install)"
uv tool install -e .

step "Homebrew tools (ffmpeg + Hugging Face CLI)"
need_cmd brew
for pkg in ffmpeg huggingface-cli; do
  if brew list "$pkg" >/dev/null 2>&1; then
    echo "    $pkg: already installed"
  else
    echo "    Installing $pkg…"
    brew install "$pkg"
  fi
done

if [[ "$SKIP_HF" != "1" ]]; then
  need_cmd hf
  step "Hugging Face login"
  if ! hf whoami >/dev/null 2>&1; then
    echo "    Log in when prompted (read token: https://huggingface.co/settings/tokens)"
    hf auth login
  else
    echo "    Already logged in: $(hf whoami 2>/dev/null | head -1 || true)"
  fi

  step "ovs config"
  ovs init

  step "Checking if models are already cached"
  if ovs check >/dev/null 2>&1; then
    echo "    Models already ready — skipping hf download."
  else
    echo ""
    echo "    Before diarization download: open this URL in your browser (same HF account) and click Agree:"
    echo "    $PYANNOTE_GATE_URL"
    echo ""

    step "Downloading Whisper ($WHISPER_REPO)"
    hf download "$WHISPER_REPO" \
      --include "config.json" \
      --include "weights.npz"

    step "Downloading diarization ($DIARIZATION_REPO)"
    if ! hf download "$DIARIZATION_REPO"; then
      echo "" >&2
      echo "Diarization download failed. If you see 403 / GatedRepoError:" >&2
      echo "  1. Open $PYANNOTE_GATE_URL" >&2
      echo "  2. Agree to the model terms (logged in as the same user as hf auth login)" >&2
      echo "  3. Re-run: ./install.sh" >&2
      echo "" >&2
      echo "Or disable diarization in ~/.config/ovs/config.yaml and re-run with:" >&2
      echo "  SKIP_HF=1 ./install.sh   # only if you already have Whisper cached" >&2
      exit 1
    fi
  fi
else
  step "Skipping Hugging Face downloads (SKIP_HF=1)"
  ovs init
fi

step "ovs setup (config + offline verification)"
ovs setup

echo ""
echo "Done. One-time install complete."
echo ""
echo "Daily use:"
echo "  ovs transcribe /path/to/video.mov"
echo ""
echo "Docs: docs/HUGGINGFACE.md"
echo "Uninstall: ./uninstall.sh"
