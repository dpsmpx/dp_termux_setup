#!/usr/bin/env python3
"""Scan repository files for common accidental secret and personal-data leaks.

This is a review aid, not a guarantee. It never prints matched secret text.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
from pathlib import Path

PATTERNS = [
    ("private key", re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("GitHub fine-grained token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{30,}\b")),
    ("Hugging Face token", re.compile(r"\bhf_[A-Za-z0-9]{20,}\b")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
    ("credentials in URL", re.compile(r"https?://[^\s/@:]+:[^\s/@]+@", re.IGNORECASE)),
    ("email address", re.compile(r"(?<![\w.+-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")),
    ("Termux home path", re.compile(r"/data/data/com\.termux/files/" + r"home/[^/\s]+")),
    ("Android shared-storage path", re.compile(r"/(?:sdcard|storage/emulated/0)(?:/|$)", re.IGNORECASE)),
    ("Windows user profile path", re.compile(r"[A-Za-z]:\\Users\\[^\\\s]+", re.IGNORECASE)),
]

SENSITIVE_NAMES = {
    ".ssh", ".gnupg", ".aws", ".netrc", ".pypirc", ".npmrc",
    ".git-credentials", ".claude", ".config", ".cache", ".bash_history", ".zsh_history",
    "local-device-snapshot", "termux-migration", "credentials", "secrets",
}
SENSITIVE_PARTS = ("backup", "migration", "credential", "secret", "history", "huggingface", "models", "datasets", "inventory")
SENSITIVE_SUFFIXES = {".gpg", ".pem", ".key", ".p12", ".pfx", ".keystore", ".sqlite", ".sqlite3", ".db"}
BINARY_SUFFIXES = {".deb", ".whl", ".xz", ".zst", ".zip", ".png", ".jpg", ".jpeg", ".webp", ".so"}


def candidate_files(root: Path) -> list[Path]:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-co", "--exclude-standard", "-z"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if result.returncode == 0:
            values = [root / item.decode("utf-8", "surrogateescape") for item in result.stdout.split(b"\0") if item]
            return sorted(
                set(
                    path for path in values
                    if path.is_symlink() or path.is_file()
                )
            )
    except FileNotFoundError:
        pass

    found: list[Path] = []
    for current, dirs, files in os.walk(root):
        dirs[:] = [name for name in dirs if name != ".git" and name not in {"__pycache__", ".venv", "venv", "node_modules"}]
        for name in files:
            path = Path(current) / name
            if path.is_symlink() or path.is_file():
                found.append(path)
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.expanduser().resolve()
    if not root.is_dir():
        parser.error(f"repository directory does not exist: {root}")

    findings: list[tuple[str, str, int | None]] = []
    files = candidate_files(root)
    for path in files:
        relative = path.relative_to(root)
        if path.is_symlink():
            findings.append((str(relative), "symbolic link; target not followed", None))
            continue
        parts = {part.lower() for part in relative.parts}
        sensitive_part = any(
            part in SENSITIVE_NAMES
            or part.startswith(".env") and part != ".env.example"
            or any(fragment in part for fragment in SENSITIVE_PARTS)
            for part in parts
        )
        if sensitive_part:
            findings.append((str(relative), "sensitive filename/path", None))
            continue
        if path.suffix.lower() in SENSITIVE_SUFFIXES:
            findings.append((str(relative), "sensitive file extension", None))
            continue
        if path.suffix.lower() in BINARY_SUFFIXES:
            continue
        try:
            raw = path.read_bytes()
        except OSError:
            continue
        if b"\0" in raw[:4096]:
            continue
        try:
            content = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(content.splitlines(), start=1):
            for label, pattern in PATTERNS:
                if pattern.search(line):
                    findings.append((str(relative), label, line_number))

    # Git author/committer addresses are part of repository history, not the
    # working tree. Flag non-noreply addresses without printing them.
    try:
        history = subprocess.run(
            ["git", "-C", str(root), "log", "--all", "--format=%H%x1f%ae%x1f%ce"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
        if history.returncode == 0:
            for record in history.stdout.splitlines():
                fields = record.split("\x1f")
                if len(fields) != 3:
                    continue
                commit, author_email, committer_email = fields
                for role, email in (("author", author_email), ("committer", committer_email)):
                    normalized = email.strip().lower()
                    github_noreply_suffix = "@users.noreply.github.com"
                    github_noreply_address = "noreply" + chr(64) + "github.com"
                    if normalized and not normalized.endswith(github_noreply_suffix) and normalized not in {github_noreply_address, ""}:
                        findings.append((f"git-history:{commit[:12]}", f"non-noreply {role} email metadata", None))
    except FileNotFoundError:
        pass

    print(f"Privacy audit: {len(files)} repository files inspected")
    if findings:
        print(f"Potential findings: {len(findings)}")
        for path, label, line in findings:
            suffix = f":{line}" if line is not None else ""
            print(f"  REVIEW {path}{suffix} — {label}")
        print("\nНе публикуй репозиторий до ручной проверки каждого пункта.")
        return 1
    print("No common secret or personal-data patterns detected.")
    print("This is not a guarantee: inspect Git commit metadata, binary files and diffs too.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
