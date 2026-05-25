#!/usr/bin/env bash
# One-time install: Python env, CLI on PATH, optional Homebrew tools and HF models.
# Usage: ./install.sh [-y]
# Re-run is safe (skips steps that already succeeded).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

# XDG layout (see src/ovs/xdg.py)
export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-${HOME}/.config}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-${HOME}/.cache}"
export XDG_DATA_HOME="${XDG_DATA_HOME:-${HOME}/.local/share}"
APP_SLUG="offline-video-scribe"
OVS_CONFIG_DIR="${XDG_CONFIG_HOME}/digg/${APP_SLUG}"
export HF_HOME="${HF_HOME:-${XDG_CACHE_HOME}/huggingface}"
export HF_HUB_CACHE="${HF_HUB_CACHE:-${HF_HOME}/hub}"
# uv tool install → ${UV_TOOL_DIR}/offline-video-scribe/bin/offline-video-scribe
export UV_TOOL_DIR="${UV_TOOL_DIR:-${XDG_DATA_HOME}/digg/${APP_SLUG}}"
export PATH="${HOME}/.local/bin:${PATH}"

CLI_NAME="offline-video-scribe"
CLI_BIN="${HOME}/.local/bin/${CLI_NAME}"
CLI_ALIAS_BIN="${HOME}/.local/bin/ovs"

WHISPER_REPO="${WHISPER_REPO:-mlx-community/whisper-medium-mlx}"
DIARIZATION_REPO="${DIARIZATION_REPO:-pyannote/speaker-diarization-community-1}"
PYANNOTE_GATE_URL="https://huggingface.co/pyannote/speaker-diarization-community-1"
SKIP_HF="${SKIP_HF:-0}"
ASSUME_YES=0
UPDATE_MODE=0

step() { echo ""; echo "==> $*"; }

usage() {
  cat <<'EOF'
Usage: ./install.sh [options]

Installs the CLI (uv sync + uv tool install). Other steps are optional and prompted:

  - Homebrew: ffmpeg, huggingface-cli (if missing)
  - Hugging Face login and model downloads (if not already cached)

Options:
  --update, -U  Upgrade mode: refresh CLI only; no brew/model download prompts
  -y, --yes     Accept default "yes" for optional prompts (install mode only)
  -h, --help    Show this help

Environment:
  SKIP_HF=1     Skip all Hugging Face prompts and downloads
  WHISPER_REPO  Override default Whisper repo
  DIARIZATION_REPO  Override default diarization repo

Re-run is safe. Use ./update.sh as a shortcut for ./install.sh --update.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --update | -U) UPDATE_MODE=1; shift ;;
    -y | --yes) ASSUME_YES=1; shift ;;
    -h | --help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

ask_yes_no() {
  local prompt="$1"
  local default="${2:-n}"
  if [[ "$ASSUME_YES" == "1" ]]; then
    [[ "$default" == "y" || "$default" == "Y" ]]
    return
  fi
  local hint="y/N"
  [[ "$default" == "y" || "$default" == "Y" ]] && hint="Y/n"
  read -r -p "    $prompt [$hint] " reply
  reply="${reply:-$default}"
  [[ "$reply" =~ ^[Yy] ]]
}

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

warn_missing() {
  local cmd="$1"
  local hint="$2"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "    Warning: $cmd not found — $hint"
  fi
}

print_model_manual_steps() {
  echo ""
  echo "    Models are a prerequisite for transcribe/watch. Prepare manually:"
  echo ""
  if command -v "$CLI_NAME" >/dev/null 2>&1; then
    "$CLI_NAME" check 2>&1 | sed 's/^/    /' || true
  else
    echo "    brew install huggingface-cli"
    echo "    hf auth login"
    echo "    hf download ${WHISPER_REPO} --include \"config.json\" --include \"weights.npz\""
    echo "    # Gated — accept terms: ${PYANNOTE_GATE_URL}"
    echo "    hf download ${DIARIZATION_REPO}"
    echo "    ${CLI_NAME} check"
  fi
  echo ""
  echo "    Full guide: docs/HUGGINGFACE.md"
}

models_cached() {
  command -v "$CLI_NAME" >/dev/null 2>&1 && "$CLI_NAME" check >/dev/null 2>&1
}

install_brew_packages() {
  local pkg
  for pkg in ffmpeg huggingface-cli; do
    if brew list "$pkg" >/dev/null 2>&1; then
      echo "    $pkg: already installed"
    else
      echo "    Installing $pkg..."
      brew install "$pkg"
    fi
  done
}

download_models() {
  need_cmd hf
  step "Hugging Face login"
  if hf whoami >/dev/null 2>&1; then
    echo "    Already logged in: $(hf whoami 2>/dev/null | head -1 || true)"
  elif ask_yes_no "Log in to Hugging Face now (hf auth login)?" "y"; then
    echo "    Token: https://huggingface.co/settings/tokens"
    hf auth login
  else
    echo "    Skipped login — cannot download without hf auth login."
    print_model_manual_steps
    return 1
  fi

  echo ""
  echo "    Before diarization: open in your browser (same HF account) and click Agree:"
  echo "    ${PYANNOTE_GATE_URL}"
  echo ""

  step "Downloading Whisper (${WHISPER_REPO})"
  hf download "$WHISPER_REPO" \
    --include "config.json" \
    --include "weights.npz"

  step "Downloading diarization (${DIARIZATION_REPO})"
  if ! hf download "$DIARIZATION_REPO"; then
    echo "" >&2
    echo "Diarization download failed. If you see 403 / GatedRepoError:" >&2
    echo "  1. Open ${PYANNOTE_GATE_URL}" >&2
    echo "  2. Agree to the model terms (same user as hf auth login)" >&2
    echo "  3. Re-run: ./install.sh" >&2
    echo "" >&2
    echo "Or set diarization: false in ${OVS_CONFIG_DIR}/config.yaml" >&2
    return 1
  fi
  return 0
}

refresh_config_example() {
  local example="${ROOT}/config/config.yaml.example"
  if [[ -f "$example" ]]; then
    mkdir -p "$OVS_CONFIG_DIR"
    cp "$example" "${OVS_CONFIG_DIR}/config.yaml.example"
    echo "    Updated ${OVS_CONFIG_DIR}/config.yaml.example"
  fi
}

warn_prerequisites() {
  warn_missing ffmpeg "required for transcribe (brew install ffmpeg)"
  warn_missing hf "required to download models (brew install huggingface-cli)"
}

if [[ "$UPDATE_MODE" == "1" ]]; then
  step "Upgrade Offline Video Scribe"
else
  step "Install Offline Video Scribe"
fi

step "Checking uv"
need_cmd uv

step "Installing Python dependencies (uv sync)"
if [[ -d "${ROOT}/tests" ]]; then
  uv sync
else
  uv sync --no-group dev
fi

step "Installing CLI on PATH (uv tool install)"
uv tool uninstall ovs 2>/dev/null || true
uv tool uninstall "${CLI_NAME}" 2>/dev/null || true
uv tool install -e . --force
if [[ ! -x "$CLI_BIN" ]]; then
  echo "Expected executable at ${CLI_BIN} after uv tool install" >&2
  exit 1
fi
ln -sf "$CLI_BIN" "$CLI_ALIAS_BIN"
echo "    ${CLI_BIN}"
echo "    ${CLI_ALIAS_BIN} -> ${CLI_NAME}"
if [[ -f "${ROOT}/VERSION" ]]; then
  echo "    Release: $(cat "${ROOT}/VERSION")"
fi
if command -v "$CLI_NAME" >/dev/null 2>&1; then
  echo "    $("$CLI_NAME" --version 2>/dev/null || true)"
fi

step "${CLI_NAME} config"
"$CLI_NAME" init
refresh_config_example

if [[ "$UPDATE_MODE" == "1" ]]; then
  step "Prerequisites (verify only)"
  warn_prerequisites
  MODELS_READY=0
  if models_cached; then
    echo "    Models OK — ${CLI_NAME} check passed."
    MODELS_READY=1
  else
    echo "    Models not ready:"
    "$CLI_NAME" check 2>&1 | sed 's/^/    /' || true
    print_model_manual_steps
  fi
  if [[ "$MODELS_READY" == "1" ]]; then
    "$CLI_NAME" setup
  else
    "$CLI_NAME" setup --skip-model
  fi
  echo ""
  echo "Upgrade complete."
else
  step "Optional: Homebrew tools (ffmpeg + Hugging Face CLI)"
  if command -v brew >/dev/null 2>&1; then
    missing_brew=()
    for pkg in ffmpeg huggingface-cli; do
      if ! brew list "$pkg" >/dev/null 2>&1; then
        missing_brew+=("$pkg")
      fi
    done
    if [[ ${#missing_brew[@]} -eq 0 ]]; then
      echo "    ffmpeg and huggingface-cli already installed via Homebrew."
    elif ask_yes_no "Install missing Homebrew packages (${missing_brew[*]})?" "n"; then
      install_brew_packages
    else
      echo "    Skipped Homebrew installs."
      warn_prerequisites
    fi
  else
    echo "    Homebrew not found — skipped."
    warn_prerequisites
  fi

  MODELS_READY=0
  if [[ "$SKIP_HF" == "1" ]]; then
    echo ""
    echo "    SKIP_HF=1 — skipping Hugging Face model prompts and downloads."
    if models_cached; then
      MODELS_READY=1
      echo "    Models already cached."
    else
      print_model_manual_steps
    fi
  else
    step "Model cache (prerequisite for transcribe)"
    if models_cached; then
      echo "    Models already in cache — ${CLI_NAME} check passed."
      MODELS_READY=1
    else
      echo "    Models are not in your local Hugging Face cache yet."
      "$CLI_NAME" check 2>&1 | sed 's/^/    /' || true
      echo ""
      if ask_yes_no "Download Whisper + diarization models now (large download)?" "n"; then
        if download_models && models_cached; then
          echo "    Models ready."
          MODELS_READY=1
        else
          echo "" >&2
          echo "Model download incomplete. Finish manually, then run: ${CLI_NAME} check" >&2
          print_model_manual_steps
        fi
      else
        echo "    Skipped model download."
        print_model_manual_steps
      fi
    fi
  fi

  if [[ "$MODELS_READY" == "1" ]]; then
    step "${CLI_NAME} setup (config + offline verification)"
    "$CLI_NAME" setup
  else
    step "${CLI_NAME} setup (config only — models not verified)"
    "$CLI_NAME" setup --skip-model
    echo ""
    echo "    Install finished, but models are not ready. Run ${CLI_NAME} check after downloading."
  fi
  echo ""
  echo "Done."
fi

echo ""
echo "Daily use:"
echo "  ${CLI_NAME} transcribe /path/to/video.mov"
echo "  # shortcut: ovs -> ${CLI_NAME}"
echo ""
echo "Docs: docs/INSTALL.md  docs/HUGGINGFACE.md"
echo "Upgrade: ./update.sh"
echo "Uninstall: ./uninstall.sh"
