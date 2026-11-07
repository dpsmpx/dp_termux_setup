#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ "${PREFIX:-}" == */com.termux/files/usr ]] || { echo "Run inside Termux." >&2; exit 2; }
[[ "$(uname -m)" == "aarch64" ]] || { echo "This profile targets Android ARM64." >&2; exit 2; }
[[ "$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')" == "3.14" ]] || {
  echo "This profile targets Python 3.14." >&2; exit 2;
}
(cd "$ROOT" && sha256sum -c manifests/artifact-sha256.txt)
HF="$ROOT/artifacts/debs/python-hf-xet_1.8.0_aarch64.deb"
TOK="$ROOT/artifacts/debs/python-tokenizers_0.23.3_aarch64.deb"
SAFE="$ROOT/artifacts/wheels/safetensors-0.8.0-cp310-abi3-android_24_arm64_v8a.whl"
REGEX="$ROOT/artifacts/wheels/regex-2026.11.7-cp314-cp314-android_24_arm64_v8a.whl"
REQ="$ROOT/manifests/python-pip-ml-requirements.txt"
for file in "$HF" "$TOK" "$SAFE" "$REGEX" "$REQ"; do
  [[ -f "$file" ]] || { echo "Missing repository artifact: $file" >&2; exit 1; }
done
PLAN="$(apt-get install --simulate "$HF" "$TOK" 2>&1)" || { printf '%s\n' "$PLAN"; exit 1; }
printf '%s\n' "$PLAN"
if grep -q '^Remv ' <<<"$PLAN"; then
  echo "APT plans to remove packages; refusing to continue." >&2
  exit 1
fi
read -r -p "Proceed with installing the two Termux packages? [y/N] " answer
case "$answer" in y|Y|yes|YES|д|да) ;; *) echo "Cancelled."; exit 0 ;; esac
apt-get install "$HF" "$TOK"
python -m pip install --no-index --no-deps "$SAFE"
python -m pip install --no-index --no-deps "$REGEX"
python -m pip install -r "$REQ"
python -m pip check
