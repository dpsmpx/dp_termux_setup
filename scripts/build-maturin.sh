#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

MATURIN_VERSION="1.16.0"
CARGO_ROOT="${CARGO_INSTALL_ROOT:-$HOME/.local}"
MATURIN="$CARGO_ROOT/bin/maturin"
JOBS="${CARGO_BUILD_JOBS:-2}"

command -v cargo >/dev/null 2>&1 || {
  echo "cargo is required. Install the Termux Rust package first." >&2
  exit 1
}
command -v rustc >/dev/null 2>&1 || {
  echo "rustc is required." >&2
  exit 1
}

if [[ -x "$MATURIN" ]] && "$MATURIN" --version | grep -Fq "maturin $MATURIN_VERSION"; then
  echo "Maturin $MATURIN_VERSION already installed at $MATURIN"
  exit 0
fi

mkdir -p "$CARGO_ROOT/bin"
CARGO_BUILD_JOBS="$JOBS" cargo install maturin \
  --version "$MATURIN_VERSION" \
  --locked \
  --no-default-features \
  --root "$CARGO_ROOT" \
  --force

"$MATURIN" --version
