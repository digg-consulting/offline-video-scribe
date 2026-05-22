#!/usr/bin/env bash
# Uninstall OVS: interactive keep/delete for config, models, and transcripts.
# Usage: ./uninstall.sh [--dry-run] [-y]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

WHISPER_REPO="${WHISPER_REPO:-mlx-community/whisper-medium-mlx}"
DIARIZATION_REPO="${DIARIZATION_REPO:-pyannote/speaker-diarization-community-1}"
XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-${HOME}/.config}"
XDG_CACHE_HOME="${XDG_CACHE_HOME:-${HOME}/.cache}"
CONFIG_DIR="${XDG_CONFIG_HOME}/digg/ovs"
CONFIG_FILE="${CONFIG_DIR}/config.yaml"
LEGACY_CONFIG="${HOME}/.config/ovs/config.yaml"
OVS_CACHE_DIR="${XDG_CACHE_HOME}/digg/ovs"
if [[ -n "${HF_HUB_CACHE:-}" ]]; then
  HF_HUB="$HF_HUB_CACHE"
elif [[ -n "${HF_HOME:-}" ]]; then
  HF_HUB="${HF_HOME}/hub"
elif [[ -d "${OVS_CACHE_DIR}/huggingface/hub" ]]; then
  HF_HUB="${OVS_CACHE_DIR}/huggingface/hub"
else
  HF_HUB="${HOME}/.cache/huggingface/hub"
fi
OVS_DATA_DIR="${XDG_DATA_HOME:-${HOME}/.local/share}/digg/ovs"
CLI_NAME="offline-video-scribe"
CLI_BIN="${HOME}/.local/bin/${CLI_NAME}"
CLI_ALIAS_BIN="${HOME}/.local/bin/ovs"

DRY_RUN=0
ASSUME_YES=0

usage() {
  cat <<'EOF'
Usage: ./uninstall.sh [options]

Removes offline-video-scribe (CLI + ovs symlink + repo .venv). Prompts what else to delete:

  - Config (~/.config/digg/ovs/config.yaml)
  - Hugging Face model cache (ovs repos only)
  - Transcript output folder (from config, default ~/Transcripts)

Options:
  --dry-run   Show actions without changing anything
  -y, --yes   Accept default answers (keep models and transcripts; remove config)
  -h, --help  Show this help

Not removed: Homebrew ffmpeg/huggingface-cli, hf login, git repo.
Re-install: ./install.sh
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift ;;
    -y | --yes) ASSUME_YES=1; shift ;;
    -h | --help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

step() { echo ""; echo "==> $*"; }

repo_to_folder() {
  echo "models--${1//\//--}"
}

dir_size() {
  if [[ -d "$1" ]]; then
    du -sh "$1" 2>/dev/null | awk '{print $1}' || echo "?"
  else
    echo "-"
  fi
}

run() {
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "    [dry-run] $*"
  else
    "$@"
  fi
}

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

# Resolve paths from config before .venv may be removed
OUTPUT_DIR="${HOME}/Transcripts"
if [[ -f "$CONFIG_FILE" ]] && [[ -d "$ROOT/.venv" ]]; then
  if paths="$(uv run python -c "
from pathlib import Path
from ovs.config import load_config
from ovs.transcriber import resolve_model_repo
c = load_config()
print(resolve_model_repo(c.model))
print(c.diarization_pipeline if c.diarization else '')
print(Path(c.output_dir).expanduser())
" 2>/dev/null)"; then
    WHISPER_REPO="$(echo "$paths" | sed -n '1p')"
    dia="$(echo "$paths" | sed -n '2p')"
    [[ -n "$dia" ]] && DIARIZATION_REPO="$dia"
    out="$(echo "$paths" | sed -n '3p')"
    [[ -n "$out" ]] && OUTPUT_DIR="$out"
  fi
fi

WHISPER_CACHE="${HF_HUB}/$(repo_to_folder "$WHISPER_REPO")"
DIARIZATION_CACHE="${HF_HUB}/$(repo_to_folder "$DIARIZATION_REPO")"

echo "Offline Video Scribe uninstall"
echo ""
echo "Will always remove (if present):"
echo "  - uv tool: ${CLI_NAME}"
echo "  - symlink: ${CLI_ALIAS_BIN} -> ${CLI_NAME}"
echo "  - ${ROOT}/.venv"
echo ""
echo "You choose keep or delete for:"
echo "  - Config:        ${CONFIG_FILE}"
echo "  - Whisper cache: ${WHISPER_CACHE} ($(dir_size "$WHISPER_CACHE"))"
echo "  - Diarization:   ${DIARIZATION_CACHE} ($(dir_size "$DIARIZATION_CACHE"))"
echo "  - Transcripts:   ${OUTPUT_DIR} ($(dir_size "$OUTPUT_DIR"))"
echo ""
echo "Never removed: brew packages (ffmpeg, huggingface-cli), hf login, this git repo."

if ! ask_yes_no "Continue uninstall?" "n"; then
  echo "Cancelled."
  exit 0
fi

DELETE_CONFIG=0
DELETE_MODELS=0
DELETE_OUTPUT=0

if ask_yes_no "Delete config file?" "y"; then DELETE_CONFIG=1; fi
if ask_yes_no "Delete Hugging Face model cache (both repos above)?" "n"; then DELETE_MODELS=1; fi
if ask_yes_no "Delete transcript output directory?" "n"; then DELETE_OUTPUT=1; fi

step "Removing CLI (uv tool uninstall + ovs symlink)"
run uv tool uninstall ovs 2>/dev/null || true
run uv tool uninstall "${CLI_NAME}" || true
if [[ -L "$CLI_ALIAS_BIN" ]] || [[ -e "$CLI_ALIAS_BIN" ]]; then
  run rm -f "$CLI_ALIAS_BIN"
  echo "    removed ${CLI_ALIAS_BIN}"
fi
if [[ -d "${OVS_DATA_DIR}/tool" ]]; then
  run rm -rf "${OVS_DATA_DIR}/tool"
  echo "    removed ${OVS_DATA_DIR}/tool"
fi

step "Removing project virtualenv"
if [[ -d "$ROOT/.venv" ]]; then
  run rm -rf "$ROOT/.venv"
else
  echo "    .venv not found — skipped"
fi

if [[ "$DELETE_CONFIG" == "1" ]]; then
  step "Removing config"
  for f in "$CONFIG_FILE" "$LEGACY_CONFIG"; do
    if [[ -f "$f" ]]; then
      run rm -f "$f"
    fi
  done
  if [[ "$DRY_RUN" != "1" ]] && [[ -d "$CONFIG_DIR" ]] && [[ -z "$(ls -A "$CONFIG_DIR" 2>/dev/null)" ]]; then
    run rmdir "$CONFIG_DIR"
  elif [[ "$DRY_RUN" == "1" ]] && [[ -d "$CONFIG_DIR" ]]; then
    echo "    [dry-run] rmdir $CONFIG_DIR  # if empty"
  fi
  legacy_dir="${HOME}/.config/ovs"
  if [[ "$DRY_RUN" != "1" ]] && [[ -d "$legacy_dir" ]] && [[ -z "$(ls -A "$legacy_dir" 2>/dev/null)" ]]; then
    run rmdir "$legacy_dir"
  fi
else
  echo ""
  echo "    Kept config: $CONFIG_FILE"
fi

if [[ "$DELETE_MODELS" == "1" ]]; then
  step "Removing Hugging Face model cache (ovs repos)"
  for dir in "$WHISPER_CACHE" "$DIARIZATION_CACHE"; do
    if [[ -d "$dir" ]]; then
      run rm -rf "$dir"
      echo "    removed $dir"
    else
      echo "    not found: $dir"
    fi
  done
else
  echo ""
  echo "    Kept model cache under $HF_HUB"
fi

if [[ "$DELETE_OUTPUT" == "1" ]]; then
  step "Removing transcript output"
  if [[ -d "$OUTPUT_DIR" ]]; then
    run rm -rf "$OUTPUT_DIR"
    echo "    removed $OUTPUT_DIR"
  else
    echo "    not found: $OUTPUT_DIR"
  fi
else
  echo ""
  echo "    Kept transcripts: $OUTPUT_DIR"
fi

echo ""
if [[ "$DRY_RUN" == "1" ]]; then
  echo "Dry run complete — no changes made."
else
  echo "Uninstall complete."
fi
echo "Re-install anytime: ./install.sh"
