#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/manifests/local-device-snapshot"

mkdir -p "$OUT"

echo "Capturing installed DPKG package inventory..."
dpkg-query -W -f='${binary:Package}==${Version}\t${db:Status-Abbrev}\n' \
  | sort > "$OUT/dpkg-packages.tsv"

echo "Capturing pip-visible Python distributions..."
python -m pip freeze --all | sort > "$OUT/python-pip-freeze.txt"

echo "Capturing Python runtime..."
python - <<'PY' > "$OUT/python-runtime.txt"
import platform
import sys
import sysconfig

print("version:", sys.version.replace("\n", " "))
print("platform:", sysconfig.get_platform())
print("soabi:", sysconfig.get_config_var("SOABI"))
print("machine:", platform.machine())
PY

echo "Capturing native build toolchain..."
{
  echo "kernel_arch: $(uname -m)"
  echo
  echo "[rustc]"
  rustc -vV 2>&1 || true
  echo
  echo "[cargo]"
  cargo --version 2>&1 || true
  echo
  echo "[clang]"
  clang --version 2>&1 || true
  echo
  echo "[maturin]"
  "$HOME/.local/bin/maturin" --version 2>&1 || true
  echo
  echo "[openblas]"
  pkg-config --modversion openblas 2>&1 || true
} > "$OUT/native-toolchain.txt"

echo "Capturing artifact checksums..."
if compgen -G "$ROOT/artifacts/debs/*" >/dev/null ||
   compgen -G "$ROOT/artifacts/sources/*" >/dev/null ||
   compgen -G "$ROOT/artifacts/wheels/*" >/dev/null; then
  (
    cd "$ROOT"
    find artifacts -type f ! -name SHA256SUMS -print0 \
      | sort -z \
      | xargs -0 -r sha256sum
  ) > "$ROOT/artifacts/SHA256SUMS"
fi

echo
echo "Snapshots written inside the checkout: manifests/local-device-snapshot/"
echo "The directory is gitignored, not outside the repository. Review locally; do not force-add or commit it."
