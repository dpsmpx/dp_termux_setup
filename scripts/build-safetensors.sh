#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE="$ROOT/artifacts/sources/safetensors-0.8.0.tar.gz"
EXPECTED_SHA="fabaf3e0f18a6618d9b36560682562157f77c2b71fcffc7b432be2baed9d753d"
MATURIN="${MATURIN:-$HOME/.local/bin/maturin}"
PYTHON="${PYTHON:-$PREFIX/bin/python}"
WORK="${DP_TERMUX_BUILD_DIR:-$HOME/.cache/dp-termux-setup-build}"
OUT="$ROOT/artifacts/wheels"

[[ -f "$SOURCE" ]] || { echo "Missing $SOURCE; run scripts/stage-local-artifacts.sh" >&2; exit 1; }
[[ -x "$MATURIN" ]] || { echo "Maturin not found: $MATURIN" >&2; exit 1; }
[[ -x "$PYTHON" ]] || { echo "Termux Python not found: $PYTHON" >&2; exit 1; }

ACTUAL_SHA="$(sha256sum "$SOURCE" | awk '{print $1}')"
[[ "$ACTUAL_SHA" == "$EXPECTED_SHA" ]] || { echo "Safetensors source SHA-256 mismatch" >&2; exit 1; }

PY_MINOR="$("$PYTHON" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
[[ "$PY_MINOR" == "3.14" ]] || { echo "This recorded wheel profile requires Python 3.14; found $PY_MINOR" >&2; exit 1; }

"$MATURIN" --version
mkdir -p "$WORK/source" "$OUT"
tar -xzf "$SOURCE" -C "$WORK/source"
PROJECT="$WORK/source/safetensors-0.8.0"
[[ -f "$PROJECT/pyproject.toml" ]] || { echo "Unexpected source archive layout" >&2; exit 1; }

cd "$PROJECT"
CARGO_BUILD_JOBS="${CARGO_BUILD_JOBS:-2}" "$MATURIN" build \
  --release \
  --interpreter "$PYTHON" \
  --out "$OUT" \
  --jobs "${CARGO_BUILD_JOBS:-2}" \
  -v

WHEEL="$OUT/safetensors-0.8.0-cp310-abi3-android_24_arm64_v8a.whl"
[[ -f "$WHEEL" ]] || { echo "Expected Android wheel not produced: $WHEEL" >&2; exit 1; }

echo
echo "Built wheel:"
ls -lh "$WHEEL"
sha256sum "$WHEEL"
