#!/usr/bin/env python3
"""
push_gh.py — Canonical push mechanism for Hermes.

Reads GITHUB_TOKEN from .secrets.local, cleans any stale token from
.git/config remote URL, and pushes via embedded-URL to avoid git
credential helper prompts.

Usage:
    python3 /root/.hermes/skills/productivity/update-git/references/push_gh.py
"""
import subprocess, pathlib, re

HERMES = pathlib.Path("/root/.hermes")
REPO_URL = "https://github.com/ghosteeeeeeee/ATM.git"

# ── 1. Read token from .secrets.local ────────────────────────────────────────
secrets = HERMES / ".secrets.local"
token = None
if secrets.exists():
    for line in secrets.read_text().splitlines():
        line = line.strip()
        if "=" in line:
            k, _, v = line.partition("=")
            v = v.strip().strip('"').strip("'")
            if k == "GITHUB_TOKEN" and len(v) > 20 and v.startswith("ghp_"):
                token = v
                break

if not token:
    print("ERROR: No valid GITHUB_TOKEN found in .secrets.local")
    raise SystemExit(1)

print(f"Using token: {token[:10]}...")

# ── 2. Clean stale tokens from .git/config remote URL ───────────────────────
# git remote set-url stores token visibly and can cause "could not read Username"
# if the token is masked/redacted. Always reset to clean URL first.
git_config = HERMES / ".git" / "config"
if git_config.exists():
    content = git_config.read_text()
    # Match any https://TOKEN@github.com pattern and replace with clean URL
    clean_url = re.sub(
        r'https://[^@]+@github\.com/ghosteeeeeeee/ATM\.git',
        REPO_URL,
        content
    )
    if clean_url != content:
        git_config.write_text(clean_url)
        print("Cleaned stale token from .git/config")

# ── 3. Push via embedded token URL ──────────────────────────────────────────
push_url = f"https://{token}@github.com/ghosteeeeeeee/ATM.git"
r = subprocess.run(
    ["git", "-C", str(HERMES), "push", push_url, "main"],
    capture_output=True, text=True
)
print(r.stdout)
if r.stderr:
    print(r.stderr)
print("RC:", r.returncode)
raise SystemExit(r.returncode)
