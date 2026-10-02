#!/usr/bin/env bash
# Restore the owner-provided competition-data bridge without DrivenData credentials.
# Hash equality verifies this bridge's identity, NOT independent organizer provenance.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "${PYTHON_BIN:-${ROOT}/.venv/bin/python}" "${ROOT}/scripts/restore_data.py" "$@"
