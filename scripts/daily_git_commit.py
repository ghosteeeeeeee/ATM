#!/usr/bin/env python3
"""
daily_git_commit.py — Automated daily commit of all trading system changes.

Runs every 24 hours via systemd timer. Commits all modified/new files
with a descriptive message based on what changed.
"""
import os
import subprocess
import sys
from datetime import datetime, timezone

HERMES = '/root/.hermes'


def run(cmd, cwd=None):
    """Run a shell command and return output."""
    result = subprocess.run(cmd, shell=True, cwd=cwd or HERMES,
                           capture_output=True, text=True, timeout=60)
    return result.stdout.strip(), result.returncode


def get_changed_files():
    """Get list of changed files (modified, new, deleted)."""
    stdout, _ = run('git status --porcelain')
    files = []
    for line in stdout.split('\n'):
        if line.strip():
            status = line[:2].strip()
            filepath = line[3:].strip()
            files.append((status, filepath))
    return files


def categorize_changes(files):
    """Categorize changes for commit message."""
    categories = {
        'scripts': [],
        'signals': [],
        'skills': [],
        'plans': [],
        'automation': [],
        'docs': [],
        'other': []
    }

    for status, filepath in files:
        if 'scripts/' in filepath:
            if 'signals/' in filepath:
                categories['signals'].append(filepath)
            else:
                categories['scripts'].append(filepath)
        elif 'skills/' in filepath:
            categories['skills'].append(filepath)
        elif 'plans/' in filepath:
            categories['plans'].append(filepath)
        elif 'automation/' in filepath:
            categories['automation'].append(filepath)
        elif filepath.endswith('.md'):
            categories['docs'].append(filepath)
        else:
            categories['other'].append(filepath)

    return categories


def build_commit_message(categories):
    """Build a descriptive commit message."""
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d')

    parts = [f"Daily trading system update ({now})"]

    for cat, files in categories.items():
        if files:
            parts.append(f"\n{cat.title()} ({len(files)} files):")
            for f in files[:5]:  # Show first 5
                parts.append(f"  - {f}")
            if len(files) > 5:
                parts.append(f"  ... and {len(files) - 5} more")

    return '\n'.join(parts)


def main():
    print(f"[{datetime.now(timezone.utc).isoformat()}] Starting daily git commit...")

    # Check for changes
    files = get_changed_files()
    if not files:
        print("No changes to commit.")
        return

    print(f"Found {len(files)} changed files")

    # Categorize
    categories = categorize_changes(files)

    # Build message
    message = build_commit_message(categories)

    # Stage all changes
    run('git add -A')
    print("Staged all changes")

    # Commit
    stdout, rc = run(f'git commit -m "{message}"')
    if rc == 0:
        print(f"Committed successfully: {stdout}")
    else:
        print(f"Commit failed: {stdout}")
        return

    # Push using canonical script
    push_script = os.path.join(HERMES, 'skills/productivity/update-git/references/push_gh.py')
    if os.path.exists(push_script):
        stdout, rc = run(f'python3 {push_script}')
        if rc == 0:
            print("Pushed to remote")
        else:
            print(f"Push failed: {stdout}")
    else:
        print("Push script not found, skipping push")


if __name__ == '__main__':
    main()
