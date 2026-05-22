#!/usr/bin/env bash
# One-time install: Python env, CLI on PATH, Homebrew tools, HF models, OVS setup.
# Usage: ./install.sh
# Re-run is safe (skips steps that already succeeded).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

# XDG layout (see src/ovs/xdg.py)
export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-${HOME}/.config}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-${HOME}/.cache}"
export XDG_DATA_HOME="${XDG_DATA_HOME:-${HOME}/.local/share}"
OVS_CONFIG_DIR="${XDG_CONFIG_HOME}/digg/ovs"
OVS_CACHE_DIR="${XDG_CACHE_HOME}/digg/ovs"
OVS_DATA_DIR="${XDG_DATA_HOME}/digg/ovs"
export HF_HOME="${HF_HOME:-${OVS_CACHE_DIR}/huggingface}"
export HF_HUB_CACHE="${HF_HUB_CACHE:-${HF_HOME}/hub}"
export UV_TOOL_DIR="${UV_TOOL_DIR:-${OVS_DATA_DIR}/tool}"
export PATH="${HOME}/.local/bin:${PATH}"

CLI_NAME="offline-video-scribe"
CLI_BIN="${HOME}/.local/bin/${CLI_NAME}"
CLI_ALIAS_BIN="${HOME}/.local/bin/ovs"

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

step "Installing Offline Video Scribe on PATH (uv tool install)"
uv tool uninstall ovs 2>/dev/null || true
uv tool install -e .
if [[ ! -x "$CLI_BIN" ]]; then
  echo "Expected executable at ${CLI_BIN} after uv tool install" >&2
  exit 1
fi
ln -sf "$CLI_BIN" "$CLI_ALIAS_BIN"
echo "    ${CLI_BIN}"
echo "    ${CLI_ALIAS_BIN} -> ${CLI_NAME}"

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

  step "${CLI_NAME} config"
  "$CLI_NAME" init

  step "Checking if models are already cached"
  if "$CLI_NAME" check >/dev/null 2>&1; then
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
      echo "Or disable diarization in ${OVS_CONFIG_DIR}/config.yaml and re-run with:" >&2
      echo "  SKIP_HF=1 ./install.sh   # only if you already have Whisper cached" >&2
      exit 1
    fi
  fi
else
  step "Skipping Hugging Face downloads (SKIP_HF=1)"
  "$CLI_NAME" init
fi

step "${CLI_NAME} setup (config + offline verification)"
"$CLI_NAME" setup

echo ""
echo "Done. One-time install complete."
echo ""
echo "Daily use:"
echo "  ${CLI_NAME} transcribe /path/to/video.mov"
echo "  # shortcut: ovs -> ${CLI_NAME}"
echo ""
echo "Docs: docs/HUGGINGFACE.md"
echo "Uninstall: ./uninstall.sh"
