#!/usr/bin/env bash
# Uninstall OVS: interactive keep/delete for config, models, and transcripts.
# Usage: ./uninstall.sh [--dry-run] [-y]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

WHISPER_REPO="${WHISPER_REPO:-mlx-community/whisper-medium-mlx}"
DIARIZATION_REPO="${DIARIZATION_REPO:-pyannote/speaker-diarization-community-1}"
CONFIG_DIR="${HOME}/.config/ovs"
CONFIG_FILE="${CONFIG_DIR}/config.yaml"
if [[ -n "${HF_HUB_CACHE:-}" ]]; then
  HF_HUB="$HF_HUB_CACHE"
elif [[ -n "${HF_HOME:-}" ]]; then
  HF_HUB="${HF_HOME}/hub"
else
  HF_HUB="${HOME}/.cache/huggingface/hub"
fi

DRY_RUN=0
ASSUME_YES=0

usage() {
  cat <<'EOF'
Usage: ./uninstall.sh [options]

Removes ovs (CLI + repo .venv). Prompts what else to delete:

  - Config (~/.config/ovs/config.yaml)
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

echo "ovs uninstall"
echo ""
echo "Will always remove (if present):"
echo "  - uv tool: ovs (global CLI)"
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

step "Removing ovs CLI (uv tool uninstall)"
run uv tool uninstall ovs || true

step "Removing project virtualenv"
if [[ -d "$ROOT/.venv" ]]; then
  run rm -rf "$ROOT/.venv"
else
  echo "    .venv not found — skipped"
fi

if [[ "$DELETE_CONFIG" == "1" ]]; then
  step "Removing config"
  if [[ -f "$CONFIG_FILE" ]]; then
    run rm -f "$CONFIG_FILE"
  fi
  if [[ "$DRY_RUN" != "1" ]] && [[ -d "$CONFIG_DIR" ]] && [[ -z "$(ls -A "$CONFIG_DIR" 2>/dev/null)" ]]; then
    run rmdir "$CONFIG_DIR"
  elif [[ "$DRY_RUN" == "1" ]] && [[ -d "$CONFIG_DIR" ]]; then
    echo "    [dry-run] rmdir $CONFIG_DIR  # if empty"
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
