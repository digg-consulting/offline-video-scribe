#!/usr/bin/env bash
# Build a macOS release tarball (option B distribution). No git clone required for end users.
# Usage: ./scripts/make-release.sh
# Output: dist/offline-video-scribe-<version>-macos.tar.gz
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

version="$(grep -E '^version = ' pyproject.toml | head -1 | sed -E 's/^version = "([^"]+)"/\1/')"
if [[ -z "$version" ]]; then
  echo "Could not read version from pyproject.toml" >&2
  exit 1
fi

name="offline-video-scribe-${version}-macos"
staging="${ROOT}/dist/staging/${name}"
archive="${ROOT}/dist/${name}.tar.gz"

rm -rf "$staging"
mkdir -p "$staging" "${ROOT}/dist"

echo "Building release ${version} -> dist/${name}.tar.gz"

cp install.sh uninstall.sh "$staging/"
chmod +x "$staging/install.sh" "$staging/uninstall.sh"

if [[ -f update.sh ]]; then
  cp update.sh "$staging/"
  chmod +x "$staging/update.sh"
fi

echo "$version" >"$staging/VERSION"

cp pyproject.toml uv.lock README.md LICENSE "$staging/"
[[ -f .python-version ]] && cp .python-version "$staging/"

# Copy source without __pycache__ / .pyc
mkdir -p "$staging/src"
cp -R src/ovs "$staging/src/"
find "$staging" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find "$staging" -name '*.pyc' -delete 2>/dev/null || true

cp -R config docs "$staging/"
cp -R bin "$staging/" 2>/dev/null || true

# User-facing install guide (no git required)
cat >"$staging/INSTALL.txt" <<EOF
Offline Video Scribe ${version} (macOS)

Prerequisites on PATH:
  - uv       https://docs.astral.sh/uv/
  - ffmpeg   (optional: install.sh can prompt for Homebrew)

Install:
  tar xzf ${name}.tar.gz
  cd ${name}
  ./install.sh

Upgrade (after downloading a newer release):
  cd ${name}
  ./update.sh

Models are not included. install.sh will ask to download, or see docs/HUGGINGFACE.md.

Uninstall: ./uninstall.sh
EOF

tar -czf "$archive" -C "${ROOT}/dist/staging" "$name"

echo "Created: $archive"
echo "Size: $(du -h "$archive" | awk '{print $1}')"
echo ""
echo "Publish: attach dist/${name}.tar.gz to a GitHub Release tagged v${version}"
