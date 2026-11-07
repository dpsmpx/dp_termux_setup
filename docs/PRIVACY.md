# Privacy and repository hygiene

This repository contains generic scripts, documentation, curated manifests
and verified artifacts. It is not a personal Termux backup.

The manager does not collect or upload home-directory files, Android shared
storage, SSH/GPG keys, tokens, shell histories, browser profiles, Claude
Code data, Hugging Face caches, model weights, datasets or encrypted
backups.

Local package inventories are created only by an explicit command. The current
`scripts/capture-manifests.sh` writes them to
`manifests/local-device-snapshot/` inside the checkout. `.gitignore` excludes
that directory from normal Git status/add operations, but ignored does not mean
outside the repository: inspect it locally and never use `git add -f` on it.
Treat inventories as device-specific data; inspect them before sharing.

Before committing, run:

```bash
python scripts/privacy_audit.py
git status --short
git diff --check
```

The audit reports filenames and line numbers, not matched secret contents.
It checks common tokens, private-key headers, email addresses, local paths,
sensitive filenames and Git author/committer metadata. It cannot guarantee
that binary files or arbitrary data are safe; review them manually.

Do not use `git add -f` to bypass ignore rules for backups, caches,
credentials, local SDK/NDK installations or device snapshots. If a secret
was committed, revoke it and rewrite history. Coordinate force-pushes with
all existing clones.
