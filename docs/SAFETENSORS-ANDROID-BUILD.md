# Build Safetensors 0.8.0 for Termux Android ARM64

## Verified build inputs

- Source: `safetensors-0.8.0.tar.gz`
- Source SHA-256: `fabaf3e0f18a6618d9b36560682562157f77c2b71fcffc7b432be2baed9d753d`
- Python: 3.14.10, platform `android-24-arm64_v8a`
- Rust/Cargo: 1.99.1, host `aarch64-linux-android`
- Clang: 21.1.8, target `aarch64-unknown-linux-android24`
- Maturin: 1.16.0 (built locally with Cargo)
- PyO3: 0.28.3, `abi3-py310`
- Safetensors Python binding: release 0.8.0

## Rebuild

From the repository root:

```bash
bash scripts/build-maturin.sh
bash scripts/build-safetensors.sh
```

The build script uses the current Termux Python interpreter explicitly and does not force a foreign Linux target. On the reference device Maturin detected the native Android platform and produced:

`safetensors-0.8.0-cp310-abi3-android_24_arm64_v8a.whl`

## Verified output

- Wheel size: 516 KiB (reported by `ls -lh`)
- Wheel SHA-256: `29263ee16e3d5c96304890a48aaf8579c3f16d0acba412f361a250047849dfe3`
- ELF class: ELF64
- ELF machine: AArch64 (183)
- ELF type: shared object (DYN)
- NEEDED: `libpython3.14.so`, `libdl.so`, `libc.so`
- RPATH: Termux `$PREFIX/lib`

The wheel metadata advertises the CPython stable ABI from 3.10, but the inspected ELF directly needs `libpython3.14.so`. Therefore the tested artifact is specific to the Python 3.14 Termux runtime unless a rebuilt artifact is inspected and validated for another runtime.

## Functional validation performed

The built extension was imported successfully. It read a real 520,212-byte Xet-backed test checkpoint, exposed 100 tensors, loaded 126,851 tensor elements into PyTorch 2.15.0, then saved and reloaded the tensors. All tensor values matched after the roundtrip.

## Reproducibility

Cargo dependencies are described by the upstream `bindings/python/Cargo.lock`. Keep the source archive and built wheel with their hashes. Do not edit the upstream source archive in place. Any patches must be stored as separate patch files and documented.

## Embedded build paths and portability

A read-only binary review on 2026-11-07 found absolute build/source path strings
inside the Safetensors extension, including paths shaped like Cargo's
`registry/src` cache and Termux `.cargo` / `.cache` directories. The device-side
audit redacted the account names; it reported 26 `/home` path/member pairs in
`registry/src` and two additional `/home` paths whose account/layout could not
be identified from the redacted report. It found no Termux HOME paths outside
the standard `.cargo` and `.cache` roots.

The ELF scan classified 56 `/home` path-string occurrences in the Safetensors
shared object as residing in allocated sections. An allocated ELF section can
be mapped into process memory; this classification does **not** mean the
dynamic loader treats every string in that section as a file dependency or
tries to open the source path. ELF library lookup is driven by dynamic-linking
metadata such as `DT_NEEDED`, `DT_RPATH` and `DT_RUNPATH`, not by arbitrary
source-path strings embedded in the binary. See
[elf(5)](https://man7.org/linux/man-pages/man5/elf.5.html).

Therefore, these embedded paths do not by themselves prevent installation on
a clean Termux device. They may disclose details about a build account or
build layout to someone inspecting the binary, so they remain a build-metadata
privacy consideration. The redacted audit did not establish whether the two
unidentified path prefixes belong to a particular person or CI service.

No binary rewrite or `strip --strip-debug` step is required for runtime
compatibility. The scan showed that some path strings occur in allocated
sections, so removing debug sections alone would not guarantee their removal.
For future reproducible/public builds, Rust supports
`--remap-path-prefix=FROM=TO` to normalize compiler-emitted paths. This is a
best-effort compiler feature; paths introduced by external tools may need
separate handling. See the
[Rust compiler documentation](https://doc.rust-lang.org/rustc/remap-source-paths.html).

This path metadata is separate from the wheel's actual runtime compatibility:
the ELF directly needs `libpython3.14.so`. Despite the `cp310-abi3` wheel tag,
the artifact documented here is validated for the CPython 3.14 Termux runtime,
not assumed to be portable to arbitrary Python versions or non-Termux systems.
