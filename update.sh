#!/usr/bin/env bash
# Upgrade an existing install from a release tree or git clone.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
exec "${ROOT}/install.sh" --update "$@"
