#!/usr/bin/env bash
# Download a release tarball and run install.sh (no git clone).
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/digg-consulting/offline-video-scribe/main/scripts/bootstrap-install.sh | bash
#   OVS_VERSION=0.1.0 ./scripts/bootstrap-install.sh
#   ./scripts/bootstrap-install.sh -- -y
set -euo pipefail

GITHUB_REPO="${GITHUB_REPO:-digg-consulting/offline-video-scribe}"
OVS_VERSION="${OVS_VERSION:-}"
INSTALL_DIR="${OVS_INSTALL_DIR:-${HOME}/.local/share/digg/offline-video-scribe-releases}"
ASSUME_YES="${ASSUME_YES:-0}"

usage() {
  cat <<EOF
Usage: bootstrap-install.sh [options] [-- install.sh args...]

Downloads offline-video-scribe from GitHub Releases and runs ./install.sh.

Environment:
  OVS_VERSION     Release tag without 'v' (default: latest from GitHub API)
  GITHUB_REPO     owner/repo (default: digg-consulting/offline-video-scribe)
  OVS_INSTALL_DIR Extract directory (default: ~/.local/share/digg/offline-video-scribe-releases)

Options:
  -y, --yes       Pass -y to install.sh
  -h, --help      Show help

Example:
  OVS_VERSION=0.1.0 ./scripts/bootstrap-install.sh
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -y | --yes) ASSUME_YES=1; shift ;;
    -h | --help) usage; exit 0 ;;
    --)
      shift
      break
      ;;
    *)
      break
      ;;
  esac
done

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1" >&2
    exit 1
  }
}

need_cmd curl
need_cmd tar

resolve_version() {
  if [[ -n "$OVS_VERSION" ]]; then
    echo "$OVS_VERSION"
    return
  fi
  need_cmd python3
  OVS_VERSION="$(
    python3 - <<'PY' "$GITHUB_REPO"
import json, sys, urllib.request
repo = sys.argv[1]
url = f"https://api.github.com/repos/{repo}/releases/latest"
req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
with urllib.request.urlopen(req, timeout=30) as r:
    data = json.load(r)
tag = data.get("tag_name", "")
print(tag.lstrip("v"))
PY
  )"
  if [[ -z "$OVS_VERSION" ]]; then
    echo "Could not resolve latest release. Set OVS_VERSION=0.1.0" >&2
    exit 1
  fi
  echo "Latest release: ${OVS_VERSION}" >&2
}

version="$(resolve_version)"
asset="offline-video-scribe-${version}-macos.tar.gz"
url="https://github.com/${GITHUB_REPO}/releases/download/v${version}/${asset}"
dest_dir="${INSTALL_DIR}/${asset%.tar.gz}"
archive="${INSTALL_DIR}/${asset}"

mkdir -p "$INSTALL_DIR"

if [[ -f "${dest_dir}/install.sh" ]] && [[ "$(cat "${dest_dir}/VERSION" 2>/dev/null || true)" == "$version" ]]; then
  echo "Already extracted: ${dest_dir}"
else
  echo "Downloading ${url}"
  curl -fsSL -o "$archive" "$url"
  rm -rf "$dest_dir"
  tar -xzf "$archive" -C "$INSTALL_DIR"
  echo "Extracted to ${dest_dir}"
fi

install_args=()
[[ "$ASSUME_YES" == "1" ]] && install_args+=(-y)
install_args+=("$@")

exec "${dest_dir}/install.sh" "${install_args[@]}"
