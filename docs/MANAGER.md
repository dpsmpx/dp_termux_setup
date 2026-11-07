# Text manager

Start from a complete repository checkout:

```bash
bash dp-termux-setup.sh
```

To inspect the interface from a checkout, run:

```bash
bash scripts/preview-manager.sh
```

Or run the manager directly:

```bash
python scripts/manager.py --preview
```

The preview requires only Python's standard library. It does not call `pkg`,
APT, network download functions, storage-permission commands or installation
routines, and it does not write files. It runs without a full repository checkout. The
standalone file can manage Termux package groups and the optional SDK/NDK
downloads; the pinned AI profile and repository privacy audit require the
full checkout with its manifests and local artifacts.

## Main menu

1. Install selected package groups
2. Search for and install one package
3. Install the optional AI / Hugging Face profile
4. Download and install Android SDK, NDK, or both
5. Update package lists or upgrade packages
6. Request Android shared-storage permission
7. Show environment status
8. Run the repository privacy audit
0. Exit

Package groups are selected explicitly. APT simulation is displayed before
installation, and any transaction that proposes removing packages is
refused. Updates and storage permission are separate actions.

SDK and NDK archives are community ARM64 builds from lzhiyong/termux-ndk,
not official Google binary releases. The manager verifies archive size and
SHA-256, checks extraction paths, validates the payload and refuses to
overwrite an existing installation. Read the upstream release information
before installing third-party toolchains.
