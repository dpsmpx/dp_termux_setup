#!/usr/bin/env bash
set -euo pipefail
if [[ -z "${PREFIX:-}" || "$PREFIX" != */com.termux/files/usr ]]; then
  echo "Run this manager inside Termux." >&2
  exit 2
fi
if ! command -v python >/dev/null 2>&1; then
  read -r -p "Python is required. Install it with pkg? [y/N] " answer
  case "$answer" in y|Y|yes|YES|д|да) pkg install python ;; *) echo "Cancelled."; exit 0 ;; esac
fi
exec python "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/scripts/manager.py" "$@"
