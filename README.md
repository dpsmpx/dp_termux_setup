# dp_termux_setup

Interactive, modular text manager for Termux on Android. It installs only
components explicitly selected by the user. It is not a device backup tool.

## Preview the interface — download only one file

This read-only preview requires only Python and performs no package installs,
downloads or filesystem changes:

```bash
curl -fL https://raw.githubusercontent.com/dpsmpx/dp_termux_setup/main/scripts/manager.py -o manager.py
python manager.py --preview
```

## Run the manager from a full checkout

```bash
git clone https://github.com/dpsmpx/dp_termux_setup.git
cd dp_termux_setup
bash dp-termux-setup.sh
```

Python's standard library is sufficient for the interface. No AI libraries,
Android SDK/NDK, large compilers or development toolchains are installed by
default. Every package group is optional.

## Components

- Base Termux tools, shell utilities and package search
- C/C++, Python, Rust, Node.js and Java/Gradle
- Android build helpers from Termux repositories
- Scientific Python and PyTorch/multimedia packages
- Separate optional Hugging Face profile
- Optional ARM64 Android SDK and NDK r29 community archives
- Termux updates, storage permission, environment status and privacy scan

Before installing packages, the manager shows an APT simulation. It refuses
transactions that plan package removals. SDK and NDK archives have pinned
SHA-256 checksums, are validated before extraction, and never overwrite an
existing destination.

## Optional Python/ML profile

The repository retains one tested Android ARM64 / CPython 3.14 profile.
It is separate from the default package groups. Verify tracked artifacts
before installing:

```bash
sha256sum -c manifests/artifact-sha256.txt
bash scripts/install-ml-stack.sh
python scripts/verify-ml-stack.py
```

## Privacy

The manager does not upload personal files or scan a user's home directory.
Device inventories are created only after explicit confirmation. The current
capture script writes them under `manifests/local-device-snapshot/` inside the
working tree; that directory is gitignored, but it is not outside the repository.
Inspect it locally and never force-add or commit it. Never commit backups, caches,
credentials, model weights, private keys or raw device inventories.

Run `python scripts/privacy_audit.py` before committing. This is a safety
net, not a guarantee; review source, artifacts and Git metadata manually.

The current pinned Python/ML profile is based on one validated environment.
Package availability and compatibility vary across Termux releases and
repositories. Review package transactions and third-party toolchain sources.

## Роль относительно DPmetaApp

Решение автора от 10–11 ноября 2026 — [docs/direction/DP_META_APP.md](docs/direction/DP_META_APP.md).
