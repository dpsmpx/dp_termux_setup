# Binary artifacts and privacy review

Review date: 2026-11-07

This note records the device-side read-only binary audit and the resulting
compatibility decision. It is not a certification that arbitrary future
builds or repository changes are free of personal data.

## Scope

The review covered the five binary artifacts listed in
`manifests/artifact-sha256.txt`:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `artifacts/debs/python-hf-xet_1.8.0_aarch64.deb` | 2,484,600 | `6dcd3b28bf10b2ff44ec4d24d81e397e8030c5e9675775371ce134c088be56b0` |
| `artifacts/debs/python-tokenizers_0.23.3_aarch64.deb` | 1,716,472 | `2ff955dc2928a658c44cd972ee4f45e0009e69b98a92180b5ae29b3e1ba8c454` |
| `artifacts/sources/safetensors-0.8.0.tar.gz` | 325,846 | `fabaf3e0f18a6618d9b36560682562157f77c2b71fcffc7b432be2baed9d753d` |
| `artifacts/wheels/safetensors-0.8.0-cp310-abi3-android_24_arm64_v8a.whl` | 527,551 | `29263ee16e3d5c96304890a48aaf8579c3f16d0acba412f361a250047849dfe3` |
| `artifacts/wheels/regex-2026.11.7-cp314-cp314-android_24_arm64_v8a.whl` | 555,918 | `ab44a913600a21284b965816992936336bb7cfb04a406b6d2f7b4a9186b1de2d` |

All five local files matched the committed SHA-256 manifest during the v7
audit. The scanner processed 127 archive members and parsed four ELF members.
There were no archive read errors or hash failures.

## Findings

The local device audit reported:

- Zero matches against the two local Git identity email values used for
  comparison.
- Zero recognized token-pattern hits.
- Zero private-key header hits.
- Zero exact or substring matches against the local project-name markers
  supplied to the v6 audit.
- 142 distinct other email strings in package metadata/code. The scanner
  suppressed their values. They did not match the compared local Git identity
  values; they may be upstream author, maintainer or project contact metadata.
- 28 Termux HOME path occurrences in the Safetensors wheel, all under the
  standard `.cargo` or `.cache` roots. The audit found no Termux HOME paths
  outside those roots.
- Unix `/home` path strings in the two DEB packages and Safetensors wheel.
  Most account labels were classified by the audit as common CI or package
  builder labels. The redacted v6 report retained 28 path/member pairs with
  account labels it could not classify: 26 under a Cargo `registry/src` layout
  and two under another, undisclosed layout in the Safetensors wheel.

The v7 ELF-section pass counted 1,089 Unix `/home` path occurrences and
28 Termux HOME path occurrences across the parsed ELF members. It classified
the following path-string occurrences as being in allocated ELF sections:

| Artifact | Allocated-section path occurrences |
|---|---:|
| `python-hf-xet` extension | 784 |
| `tokenizers` extension | 231 |
| Safetensors extension | 56 |

Additional path occurrences appeared in non-allocated SBOM and
`direct_url.json` archive members. These counts are scanner occurrence counts,
not counts of unique people, machines or source files.

The audit intentionally suppresses raw path and account values. Consequently,
the 28 unclassified `/home` path/member pairs cannot be attributed to a named
individual, the repository owner or a specific CI provider from the report
alone. Their presence is a build-environment disclosure, not evidence by
itself that the paths belong to the repository owner.

## What absolute paths mean for installation

An absolute source/build path embedded as a string in an ELF section is not,
by itself, a library dependency or a request to open that path. A section
marked as allocated may be mapped into process memory, but that does not make
every string it contains an instruction to access the filesystem.

ELF dependency lookup is controlled by dynamic-linking metadata, including
`DT_NEEDED`, `DT_RPATH` and `DT_RUNPATH`, rather than by arbitrary source
path strings. See [elf(5)](https://man7.org/linux/man-pages/man5/elf.5.html).

Therefore, the path strings found by this audit do not by themselves prevent
installation or import on a clean Termux device. Actual compatibility still
depends on architecture, Android ABI, required shared libraries, and the
Python runtime. In particular, the Safetensors wheel is tagged
`cp310-abi3`, but its ELF directly needs `libpython3.14.so`; the tested
artifact is specific to the documented Termux CPython 3.14 environment.

## Build hygiene and limitations

- Rebuilding solely to remove these paths is not required for installation.
- `strip --strip-debug` is not a complete remedy: some path strings were
  found in allocated sections.
- For future Rust builds, `--remap-path-prefix=FROM=TO` can normalize
  compiler-emitted paths. Rust documents this as best-effort; paths inserted
  by external tools may require separate handling:
  [Rust remap source paths](https://doc.rust-lang.org/rustc/remap-source-paths.html).
- The repository's source privacy scanner deliberately skips binary formats
  such as DEB and wheel files. Binary artifacts therefore require their own
  review; a clean source scan alone is not sufficient.
- The checks searched for known token formats, private-key headers, compared
  Git identity values, known project markers and path patterns. They do not
  prove that no other personal data could exist in arbitrary binary content.

## Decision recorded

For this artifact set, absolute build paths are treated as technical build
metadata and not as an installation blocker. The audit found no match to the
compared local Git email values, no recognized token or private-key header,
and no match to the local project-name markers. The remaining unclassified
`/home` path prefixes are documented above rather than silently described
as verified CI paths.

Do not remove or rewrite existing binaries solely because absolute source
paths are present. If a future release requires stricter build-environment
anonymization, rebuild the Rust extensions with path remapping, re-run
functional validation, and update the artifact hashes in the manifest.
