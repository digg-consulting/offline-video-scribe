#!/usr/bin/env bash
# Create git tag v<version> from pyproject.toml and push to origin.
# GitHub Actions (.github/workflows/release.yml) builds and uploads the tarball.
#
# Usage:
#   ./scripts/publish-release.sh           # interactive confirm
#   ./scripts/publish-release.sh --dry-run
#   ./scripts/publish-release.sh -y        # skip confirm
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

DRY_RUN=0
ASSUME_YES=0

usage() {
  cat <<'EOF'
Usage: publish-release.sh [options]

Reads version from pyproject.toml, tags v<version>, pushes to origin.
Triggers GitHub Actions to build offline-video-scribe-<version>-macos.tar.gz.

Options:
  --dry-run   Print commands only; do not tag or push
  -y, --yes   Skip confirmation prompt
  -h, --help  Show help

Before running:
  - Commit all release changes on the branch you want tagged (usually main)
  - Set version in pyproject.toml
  - uv run python -m pytest  (recommended)
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

version="$(grep -E '^version = ' pyproject.toml | head -1 | sed -E 's/^version = "([^"]+)"/\1/')"
if [[ -z "$version" ]]; then
  echo "Could not read version from pyproject.toml" >&2
  exit 1
fi

tag="v${version}"

if ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo "Not a git repository." >&2
  exit 1
fi

if git rev-parse "$tag" >/dev/null 2>&1; then
  echo "Tag ${tag} already exists locally." >&2
  exit 1
fi

if git ls-remote --exit-code origin "refs/tags/${tag}" >/dev/null 2>&1; then
  echo "Tag ${tag} already exists on origin." >&2
  exit 1
fi

if [[ -n "$(git status --porcelain)" ]]; then
  echo "Warning: working tree has uncommitted changes." >&2
  git status -sb >&2
  if [[ "$ASSUME_YES" != "1" && "$DRY_RUN" != "1" ]]; then
    read -r -p "Continue anyway? [y/N] " reply
    [[ "$reply" =~ ^[Yy] ]] || exit 1
  fi
fi

echo "Version:  ${version}"
echo "Tag:      ${tag}"
echo "Commit:   $(git rev-parse --short HEAD)"
echo "Remote:   origin"
echo ""
echo "After push, GitHub Actions will:"
echo "  - run scripts/make-release.sh"
echo "  - attach dist/offline-video-scribe-${version}-macos.tar.gz to GitHub Release ${tag}"
echo ""

run() {
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "    [dry-run] $*"
  else
    "$@"
  fi
}

if [[ "$ASSUME_YES" != "1" && "$DRY_RUN" != "1" ]]; then
  read -r -p "Create and push tag ${tag}? [y/N] " reply
  [[ "$reply" =~ ^[Yy] ]] || { echo "Cancelled."; exit 0; }
fi

run git tag -a "$tag" -m "Release ${version}"
run git push origin "$tag"

echo ""
if [[ "$DRY_RUN" == "1" ]]; then
  echo "Dry run complete."
else
  echo "Pushed ${tag}. Watch: https://github.com/digg-consulting/offline-video-scribe/actions"
  echo "Release asset: offline-video-scribe-${version}-macos.tar.gz"
fi
