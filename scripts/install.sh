#!/usr/bin/env bash
# Delegates to the root one-time installer.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec "$ROOT/install.sh" "$@"
