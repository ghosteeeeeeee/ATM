#!/usr/bin/env python3
"""
daily_git_commit.py — Automated daily commit of all trading system changes.

Runs every 24 hours via systemd timer. Commits all modified/new files
with a descriptive message based on what changed.
"""
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

HERMES = '/root/.hermes'


def strip_losers_block(text):
    """Return `text` with the single `LOSERS = ...` assignment removed — plus any blank
    lines immediately following it, because the sanctioned losers_tracker rewrite also
    rewrites that gap (the live file has one extra newline there and a strict remainder
    compare rejected the legit diff). Every other ALL_CAPS set in this file
    (LOSERS_LONG, SHORT_BLACKLIST, ...) is left untouched."""
    out = []
    lines = text.splitlines(keepends=True)
    i = 0
    while i < len(lines):
        if re.match(r'^LOSERS\s*=', lines[i]):
            if lines[i].rstrip('\r\n').endswith('{'):
                i += 1
                while i < len(lines) and lines[i].strip() != '}':
                    i += 1
                i += 1  # consume the closing brace too
            else:
                i += 1  # single-line assignment
            while i < len(lines) and lines[i].strip() == '':
                i += 1  # blank lines the rewrite owns
            continue
        out.append(lines[i])
        i += 1
    return ''.join(out)


def constants_diff_is_losers_only(cwd=None):
    """True iff HEAD and the working tree differ ONLY inside the `LOSERS = ...` assignment
    (the losers_tracker daily rewrite).

    Location-aware by construction: everything except that assignment is stripped from
    both versions and the remainders must be byte-identical, so a flag, a threshold, a
    comment, or a member-add to ANY other set in the file rejects it. The earlier
    line-text heuristic accepted `+    'ETH'` inside SHORT_BLACKLIST because 'ETH' looks
    like a set member (bug_hunter #157 HIGH). Reads `git show HEAD:` + the worktree file
    (never `git diff`), so the answer does not depend on what happens to be staged —
    the #156 exception failed because it ran after `git add -A`."""
    res = subprocess.run('git show HEAD:scripts/hermes_constants.py', shell=True,
                         cwd=cwd or HERMES, capture_output=True, text=True, timeout=60)
    if res.returncode != 0:
        return False  # not in HEAD -> cannot be the sanctioned daily rewrite
    try:
        with open(os.path.join(cwd or HERMES, 'scripts', 'hermes_constants.py')) as f:
            cur = f.read()
    except OSError:
        return False
    if res.stdout == cur:
        return False  # nothing actually changed
    return strip_losers_block(res.stdout) == strip_losers_block(cur)


def run(cmd, cwd=None):
    """Run a shell command and return output."""
    result = subprocess.run(cmd, shell=True, cwd=cwd or HERMES,
                            capture_output=True, text=True, timeout=60)
    return result.stdout.strip(), result.returncode


def selfcheck():
    """4-case predicate check in a throwaway git repo (incl. the staged case that
    broke the #156 exception on its 07:15 live test)."""
    import shutil
    import tempfile
    tmp = tempfile.mkdtemp(prefix='dgc_')
    try:
        def g(cmd):
            out, rc = run(cmd, cwd=tmp)
            assert rc == 0, f'{cmd} -> {out}'
        g('git init -q')
        g('git config user.email t@t')
        g('git config user.name t')
        os.makedirs(os.path.join(tmp, 'scripts'), exist_ok=True)
        path = os.path.join(tmp, 'scripts', 'hermes_constants.py')
        with open(path, 'w') as f:
            f.write("LOSERS = {\n    'ME',\n    'PUMP'\n}\nFOO = 1\n"
                    "SHORT_BLACKLIST = {\n    'AAA',\n}\n")
        g('git add -A')
        g('git commit -qm init')
        # 1. LOSERS-block-only, unstaged -> pass
        with open(path, 'w') as f:
            f.write("LOSERS = set()\nFOO = 1\n"
                    "SHORT_BLACKLIST = {\n    'AAA',\n}\n")
        assert constants_diff_is_losers_only(tmp) is True, 'case1 LOSERS-only unstaged'
        # 2. same diff AFTER git add -A -> still pass (the #157 regression)
        g('git add -A')
        assert constants_diff_is_losers_only(tmp) is True, 'case2 LOSERS-only staged'
        # 3. rogue non-LOSERS hunk, staged -> reject
        with open(path, 'w') as f:
            f.write("LOSERS = set()\nFOO = 2\n"
                    "SHORT_BLACKLIST = {\n    'AAA',\n}\n")
        g('git add -A')
        assert constants_diff_is_losers_only(tmp) is False, 'case3 rogue flag staged'
        # 4. comment-only edit elsewhere, staged -> reject
        g('git checkout -q -- .')
        with open(path, 'w') as f:
            f.write("LOSERS = {\n    'ME',\n    'PUMP'\n}\nFOO = 1  # touched\n"
                    "SHORT_BLACKLIST = {\n    'AAA',\n}\n")
        g('git add -A')
        assert constants_diff_is_losers_only(tmp) is False, 'case4 comment-only staged'
        # 5. member-add to ANOTHER all-caps set (the #157 HIGH bypass) -> reject
        g('git checkout -q -- .')
        with open(path, 'w') as f:
            f.write("LOSERS = {\n    'ME',\n    'PUMP'\n}\nFOO = 1\n"
                    "SHORT_BLACKLIST = {\n    'AAA',\n    'ETH',\n}\n")
        g('git add -A')
        assert constants_diff_is_losers_only(tmp) is False, 'case5 blacklist member add'
        # 6. LOSERS rewrite PLUS a blacklist add in the same diff (piggyback) -> reject
        g('git checkout -q -- .')
        with open(path, 'w') as f:
            f.write("LOSERS = set()\nFOO = 1\n"
                    "SHORT_BLACKLIST = {\n    'AAA',\n    'ETH',\n}\n")
        g('git add -A')
        assert constants_diff_is_losers_only(tmp) is False, 'case6 piggyback hunk'
        # 7. byte-identical file -> reject (nothing changed)
        g('git checkout -q -- .')
        assert constants_diff_is_losers_only(tmp) is False, 'case7 unchanged'
        # 8. the real losers_tracker shape: rewrite + the blank line it owns after the
        #    block -> must still pass (this is the live file today)
        with open(path, 'w') as f:
            f.write("LOSERS = set()\n\nFOO = 1\n"
                    "SHORT_BLACKLIST = {\n    'AAA',\n}\n")
        g('git add -A')
        assert constants_diff_is_losers_only(tmp) is True, 'case8 rewrite + owned blank line'
        # 9. blank-line-only change FAR from the block -> reject (whitespace elsewhere
        #    is not the sanctioned rewrite's business)
        g('git checkout -q -- .')
        with open(path, 'w') as f:
            f.write("LOSERS = {\n    'ME',\n    'PUMP'\n}\nFOO = 1\n"
                    "SHORT_BLACKLIST = {\n    'AAA',\n}\n\n\n")
        g('git add -A')
        assert constants_diff_is_losers_only(tmp) is False, 'case9 stray blank lines at EOF'
        print('SELF-CHECK PASS (9/9: LOSERS-only unstaged/staged, rogue, comment, '
              'blacklist member, piggyback, unchanged, owned blank line, stray blank lines)')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


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

    # GUARD: an unlogged hermes_constants.py edit must never ride into an auto-commit.
    # Rogue edits landed between agent runs twice: 2026-10-05 (freeze violation, CEO
    # reverted) and 2026-10-26 02:19 (same PROFIT_MONSTER_BYPASS pump-chain removal,
    # backdated comment, caught by brain_auditor before this timer fired at 07:15).
    # Constants changes are committed deliberately by the agent that makes them,
    # with a brain/changes_log.json entry — not silently by the daily sweep.
    # EXCEPTION (brain_auditor #156): scripts/losers_tracker.py owns the LOSERS
    # block and rewrites it daily at 06:05 (systemd hermes-losers-tracker). Only a
    # LOSERS-block-only diff passes; any other hunk is unstaged and reported.
    # brain_auditor #157 FIX: the decision is taken BEFORE `git add -A` and the
    # predicate reads `git diff HEAD`. As first shipped it ran AFTER staging, so
    # `git diff` was always empty -> `changed == []` -> False -> the exception could
    # never pass and the 07:15 live test unstaged the legit LOSERS rewrite (the
    # commit message still claimed it). Deciding first also keeps the message honest.
    constants_in_files = any(f == 'scripts/hermes_constants.py' for _, f in files)
    keep_constants = constants_in_files and constants_diff_is_losers_only()
    if constants_in_files and not keep_constants:
        files = [f for f in files if f[1] != 'scripts/hermes_constants.py']
        if not files:
            print("Only an unlogged hermes_constants.py change present — nothing to commit.")
            print("GUARD: scripts/hermes_constants.py NOT staged — commit constants changes "
                  "deliberately with a brain/changes_log.json entry "
                  "(revert with: git checkout -- scripts/hermes_constants.py)")
            return

    # Categorize
    categories = categorize_changes(files)

    # Build message
    message = build_commit_message(categories)

    # Stage all changes
    run('git add -A')
    print("Staged all changes")

    # TOCTOU re-check: the decision above was taken from a pre-staging snapshot. If the
    # file changed in the window, the staged content is not what was vetted and the
    # commit message (already built) would claim the wrong thing — abort instead.
    if keep_constants and not constants_diff_is_losers_only():
        print("GUARD: scripts/hermes_constants.py changed between the LOSERS-only decision "
              "and staging — ABORTING commit (re-run; do not let an unvetted constants "
              "edit land with a message that describes the earlier diff).")
        return

    if constants_in_files and not keep_constants:
        _, rc_restore = run('git restore --staged scripts/hermes_constants.py')
        if rc_restore != 0:
            # Never claim "NOT staged" while it still is — that is the lie this guard exists to prevent.
            print("GUARD: FAILED to unstage scripts/hermes_constants.py — ABORTING commit. "
                  "Unstage manually: git restore --staged scripts/hermes_constants.py")
            return
        print("GUARD: scripts/hermes_constants.py NOT staged — commit constants changes "
              "deliberately with a brain/changes_log.json entry "
              "(revert with: git checkout -- scripts/hermes_constants.py)")
    elif keep_constants:
        print("GUARD: hermes_constants.py diff is LOSERS-block-only "
              "(losers_tracker daily rewrite) — staged deliberately")

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
    if '--selfcheck' in sys.argv:
        selfcheck()
    else:
        main()
