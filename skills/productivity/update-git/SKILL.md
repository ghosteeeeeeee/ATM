---
name: update-git
description: Package Hermes repo and publish to GitHub releases + local /var/www/git/ index. Run after significant code changes.
---

# update-git — Package Hermes & Publish to GitHub Releases

## When to Use
Run this **after any significant change** to the Hermes codebase (new features, bug fixes, config changes). It:
0. **SECRETS SCAN** (mandatory — see below)
1. Commits staged changes
2. Builds the zip (full repo)
3. Pushes to GitHub
4. Creates a GitHub release with the zip as a downloadable asset
5. Updates the local `/var/www/git/index.html` download page

## Step 0 — Show Files grouped by type (before staging)

Hermes is a **mixed repo** (trading system + personal docs + experiments + memories). `git add -A` would commit ~100 non-trading files. Always show the user a grouped list first:

```bash
cd /root/.hermes && git status --porcelain | grep '^[ M]' | grep -v '^??' | sed 's/^[ M] //' | sort > /tmp/changed.txt
```

**Two-step staging for signals/ folder:** New untracked files in signals/ are NOT included when you `git add scripts/signals/` on tracked files. You must stage them separately:
```bash
# Step 1: stage all tracked changes
git add scripts/signals/__init__.py scripts/signals/accel_300.py scripts/signals/rs.py ...
# Step 2: explicitly add new untracked signal files
git add scripts/signals/ema_angle.py scripts/signals/mtp_zscore.py scripts/signals/zscore_pump.py scripts/signals/zscore_rising.py
```

Group them and present to user:

| Category | Examples |
|---|---|
| Trading signals | `scripts/accel_300_signals.py`, `scripts/gap300_signals.py`, `scripts/rs_signals.py` |
| Trading scripts | `scripts/signal_compactor.py`, `scripts/hyperliquid-trader.py`, `scripts/position_manager.py` |
| Trading backtest/utils | `scripts/backfill_*.py`, `scripts/atr_cache.py` |
| Trading core | `scripts/hermes_constants.py`, `scripts/brain.py` |
| Trading skills (deleted) | `skills/trading/*-debug/SKILL.md` (pruned one-off debug skills) |
| Non-trading scripts | `scripts/hebbian_*.py`, `scripts/run_pipeline.py` |
| Non-trading skills | `skills/creative/`, `skills/mlops/`, `skills/red-teaming/` |
| Meta/system | `CONTEXT.md`, `SOUL.md`, `processes.json`, `brain/` |
| Data/logs | `brain/*.db`, `wandb-local/`, `archive/signals/` |

Let the user pick what to include. The script will NOT proceed if uncommitted changes exist — it will print them and exit.

## Step 1 — Mandatory Secrets Audit (DO NOT SKIP)

Before committing, scan ALL changed files for accidentally-committed secrets.

### Known danger files (always verify these are clean before pushing):
- `auth.json` — tracked in git, has previously contained real API keys. **ALWAYS restore it before staging**, even if you didn't touch it — editors modify it on open:
  ```bash
  git checkout HEAD -- auth.json
  ```
  Then re-check with `git diff --name-only | grep auth.json` (should be empty).
- `scripts/_secrets.py` — loads from `.secrets.local`, must NEVER contain real values. Always `git checkout HEAD -- scripts/_secrets.py` if staged.
- `.netrc` / `~/.netrc` — contains GitHub token. Never commit.
- Any file matching secret patterns in staged diffs.

### Pattern scan (run before `git add -A`):
```bash
cd /root/.hermes

# Check tracked danger files
git diff --name-only | grep -E "auth.json|_secrets.py|\.netrc" && echo "DANGER: secret files modified"

# Scan all staged diffs for secrets
git diff | grep -E "ghp_[a-zA-Z0-9]{36,}|sk-ant-[a-zA-Z0-9]{50,}|sk-cp-[a-zA-Z0-9]{32,}" && echo "SECRETS IN DIFF!"

# Restore known-clean files if modified
git checkout HEAD -- auth.json scripts/_secrets.py
```

### If secrets are found:
1. `git checkout HEAD -- <file>` to restore clean version
2. Add the file to `.gitignore` if it should never be tracked (e.g., `.secrets.local`)
3. Notify user — do NOT push until resolved

### wandb/ directories:
wandb offline runs are huge. Ensure these are in `.gitignore` before committing:
```
# ─── W&B ──────────────────────────────────────────────────────────────────────
wandb/
scripts/wandb/offline-run-*/
scripts/wandb/debug*.log
scripts/wandb/latest-run
wandb-local/
```
If they were committed previously, `git checkout HEAD -- <file>` to restore tracked versions, then add ignores.

## Prerequisites
- Working directory: `/root/.hermes`
- GitHub token in `/root/.hermes/.secrets.local` (`GITHUB_TOKEN=ghp_...`)
- Remote `github` configured: `https://github.com/ghosteeeeeeee/ATM.git`
- Write access to `/var/www/git/`

## Pushing to GitHub — ALWAYS Use push_gh.py

**NEVER use `git push` directly.** The token in `.git/config` may be stale/masked, causing "could not read Username" errors. Always use the canonical push script:

```bash
python3 /root/.hermes/skills/productivity/update-git/references/push_gh.py
```

This script:
1. Reads `GITHUB_TOKEN` from `.secrets.local` (canonical source)
2. Cleans any stale token from `.git/config` remote URL
3. Pushes via embedded token URL (no credential prompts)

**If push_gh.py fails:** The token in `.secrets.local` is expired. See Token Recovery below.

## The Script

Save as `scripts/update-git.py` and run with `python3 scripts/update-git.py`:

```python
#!/usr/bin/env python3
"""
update-git — Build Hermes zip + publish to GitHub releases + update local index.
Usage: python3 scripts/update-git.py [--no-push] [--dry-run]
"""
import subprocess, os, re, json, sys, tempfile, time
from pathlib import Path

HERMES = Path("/root/.hermes")
WWW_GIT = Path("/var/www/git")
GITHUB_REPO = "ghosteeeeeeee/ATM"

# Token: get from _secrets first (primary), fall back to ~/.netrc
GH = None
try:
    sys.path.insert(0, str(Path(__file__).parent))
    from _secrets import GITHUB_TOKEN as _t
    if _t and _t not in ("", "***") and _t.startswith("ghp_"):
        GH = _t
except Exception:
    pass
if not GH:
    netrc_path = Path.home() / ".netrc"
    if netrc_path.exists():
        content = netrc_path.read_text()
        for line in content.split('\n'):
            if 'api.github.com' in line:
                for part in line.split():
                    if part.startswith('ghp_'):
                        GH = part
                        break
if not GH:
    sys.exit("ERROR: No valid GITHUB_TOKEN found in _secrets or ~/.netrc")

def sh(*cmd, cwd=HERMES, check=True):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode and check:
        sys.exit(f"FAIL: {' '.join(cmd)}\n{r.stderr}")
    return r.stdout.strip()

def github_api(method, path, data=None, base="https://api.github.com"):
    url = f"{base}/repos/{GITHUB_REPO}/{path}"
    hdrs = {
        "Authorization": f"token {GH}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if data:
        hdrs["Content-Type"] = "application/json"
    import urllib.request
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data else None,
                                  headers=hdrs, method=method)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

def main():
    dry = "--dry-run" in sys.argv
    no_push = "--no-push" in sys.argv

    # 1. Ensure clean-ish state
    dirty = sh("git", "status", "--porcelain")
    if dirty:
        print(f"[!] Uncommitted changes (see list above — grouped by type):\n{dirty}")
        print("\n    Selective staging required for this mixed repo.")
        print("    Show user the grouped list, let them choose what to commit.")
        if not dry:
            sys.exit(1)

    # 2. Check symlinks (critical — break standalone zips)
    symlinks = sh("find", ".", "-type", "l", check=False)
    # Known exception: scripts/ai_decider.py -> ai-decider.py (required for underscore import)
    symlinks_clean = "\n".join(l for l in symlinks.splitlines()
                                 if 'ai_decider.py' not in l)
    if symlinks_clean.strip():
        print(f"[!] SYMLINKS FOUND — must resolve before zipping:")
        print(symlinks_clean)
        sys.exit(1)

    # 3. Get version info
    commit = sh("git", "rev-parse", "HEAD")[0:7]
    ts = time.strftime("%Y%m%d-%H%M")
    full_zip = f"/tmp/ATM-Hermes-{ts}-full-{commit}.zip"
    commit_msg = sh("git", "log", "-1", "--format=%s")
    date_str = time.strftime("%b %d, %Y %H:%M UTC")

    # 4. Check if already released
    if not dry:
        try:
            releases = github_api("GET", "releases")
            existing = next((r for r in releases if r["tag_name"] == f"v{ts}"), None)
            if existing:
                print(f"Release v{ts} already exists — skipping")
                return
        except Exception:
            pass

    # 5. Build zip
    print(f"Building: {full_zip}")
    sh("git", "archive", "--prefix=hermes/", "-o", full_zip, "HEAD")
    zip_size = os.path.getsize(full_zip)
    zip_mb = zip_size / 1024 / 1024
    print(f"  {zip_mb:.1f}MB, {sh('unzip', '-l', full_zip, check=False).count(chr(10))} entries")

    if dry:
        print(f"[dry-run] Would create release v{ts}")
        return

    # 6. Push to GitHub using push_gh.py (canonical push mechanism)
    if not no_push:
        print("Pushing to GitHub...")
        push_script = HERMES / "skills" / "productivity" / "update-git" / "references" / "push_gh.py"
        r = subprocess.run(["python3", str(push_script)], capture_output=True, text=True)
        if r.returncode:
            print(f"  Push failed: {r.stderr.strip()}")
            sys.exit(1)
        print("  Pushed to github/main")

    # 7. Create GitHub release (draft=true — immutable once published, but we'll add zip first)
    print("Creating GitHub release...")
    release_data = {
        "tag_name": f"v{ts}",
        "target_commitish": "main",
        "name": f"Hermes {date_str}",
        "body": f"**{commit_msg}**\n\nFull repo: `{full_zip}` ({zip_mb:.1f}MB)",
        "draft": True,
        "prerelease": False,
    }
    release = github_api("POST", "releases", data=release_data)
    release_id = release["id"]
    upload_url = release["upload_url"].replace("{?name,label}", "?name=")

    # 8. Upload zip to GitHub release (may fail if repo has immutable releases enabled)
    zip_basename = os.path.basename(full_zip)
    with open(full_zip, "rb") as f:
        zip_data = f.read()

    import urllib.request, urllib.error
    github_dl = None
    req = urllib.request.Request(
        f"{upload_url}{zip_basename}",
        data=zip_data,
        headers={
            "Authorization": f"token {GH}",
            "Content-Type": "application/zip",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            asset = json.loads(resp.read())
        github_dl = asset["browser_download_url"]
        print(f"  GitHub: {github_dl}")
        # Publish the draft release only if upload succeeded
        print("Publishing release...")
        github_api("PATCH", f"releases/{release_id}", data={"draft": False})
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        if "immutable" in body:
            print(f"  GitHub: release is immutable (zip upload blocked) — using local endpoint only")
            github_dl = f"https://github.com/{GITHUB_REPO}/releases/tag/v{ts}"
        else:
            print(f"  GitHub upload failed ({e.code}): {body[:200]}")
            github_dl = f"https://github.com/{GITHUB_REPO}/releases/tag/v{ts}"

    # 9. Copy to local /var/www/git/ (primary distribution — works regardless of GitHub)
    WWW_GIT.mkdir(parents=True, exist_ok=True)
    local_dest = WWW_GIT / zip_basename
    with open(full_zip, "rb") as src, open(local_dest, "wb") as dst:
        dst.write(zip_data)
    print(f"  Local:  http://localhost:54321/git/{zip_basename}")

    # 10. Update index.html
    index_path = WWW_GIT / "index.html"
    if index_path.exists():
        html = index_path.read_text()
        # Add LATEST badge
        if '<span class="tag-latest">' in html:
            html = re.sub(r' <span class="tag-latest">LATEST</span>', '', html)
        new_row = f"""<tr>
  <td><a href="{zip_basename}">{zip_basename}</a> <span class="tag-latest">LATEST</span></td>
  <td class="date">{date_str}</td>
  <td class="size">{zip_mb:.1f}MB</td>
  <td><a href="{github_dl}" target="_blank">GitHub</a> {commit_msg}</td>
</tr>"""
        header = '<tr><th>File</th><th>Date</th><th>Size</th><th>Contents</th></tr>'
        html = html.replace(header, header + "\n" + new_row)
        # Add GitHub download button to header
        html = re.sub(r'(Download Latest Full [^<]+</a>)',
                      rf'\1 | <a href="{github_dl}" target="_blank">GitHub</a>', html, count=1)
        index_path.write_text(html)
        print(f"  Updated: {index_path}")

    # 11. Cleanup
    os.unlink(full_zip)
    print(f"\nDone! Release: https://github.com/{GITHUB_REPO}/releases/tag/v{ts}")

if __name__ == "__main__":
    main()
```

## Manual Steps (if script fails)

### Scenario 1: Script blocks on uncommitted changes

The script exits with code 1 if `git status --porcelain` shows any modified files — this is intentional for safety. Workaround: the commit already exists in git history, so `git archive` builds from HEAD regardless of working tree state:

```bash
cd /root/.hermes
COMMIT=$(git rev-parse --short HEAD)   # e.g. de86b7c
TS=$(date +"%Y%m%d-%H%M")             # e.g. 20260513-0033
FULL_ZIP="/tmp/ATM-Hermes-${TS}-full-${COMMIT}.zip"

git archive --prefix=hermes/ -o "$FULL_ZIP" HEAD
# Verify
ls -lh "$FULL_ZIP"   # e.g. 29MB
unzip -l "$FULL_ZIP" | tail -1   # e.g. 8349 files
```

Then push + create release + copy to /var/www/git manually (see below).

### Push to GitHub
```bash
# ALWAYS use push_gh.py — never raw git push
python3 /root/.hermes/skills/productivity/update-git/references/push_gh.py
```

### Create release + upload via curl
```bash
TOKEN="ghp_YOURTOKEN"
REPO="ghosteeeeeeee/ATM"
TS=$(date +"%Y%m%d-%H%M")
ZIP="/tmp/ATM-Hermes-${TS}-full-$(git rev-parse --short HEAD).zip"

# Create release
RELEASE=$(curl -s -X POST \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/$REPO/releases \
  -d "{\"tag_name\":\"v${TS}\",\"name\":\"Hermes $(date +'%b %d, %Y')\",\"draft\":false}")
RID=$(echo $RELEASE | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

# Upload zip
curl -s -X POST \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/zip" \
  --data-binary "@${ZIP}" \
  "https://uploads.github.com/repos/$REPO/releases/${RID}/assets?name=$(basename $ZIP)"
```

## Pitfalls
- **NEVER `git add -A` on Hermes** — this is a mixed repo. Always show grouped file list first and get user approval on what to stage.
- **SECRETS FIRST** — Always run the Step 0 secrets audit before staging. auth.json and `_secrets.py` have been accidentally committed with real keys in the past.
- **auth.json always modified by editors** — run `git checkout HEAD -- auth.json` every time before staging, even if you didn't touch it.
- **Don't delete old zips** — never remove anything from `/var/www/git/`
- **Symlinks break standalone zips** — always check with `find . -type l` before zipping
- Fix zip is NOT uploaded to GitHub (too small to be worth the API call — users download the full zip)
- GitHub releases are append-only; old releases accumulate — this is fine
- **NEVER use `git push` directly** — always use `push_gh.py`. The token in `.git/config` may be stale/masked, causing "could not read Username" errors.
- **Never use `git remote set-url` to store a token** — the token gets stored visibly in `.git/config` and can cause credential prompts. Use `push_gh.py` instead.
- **Token check in script rejects masked tokens** — `_secrets.py` contains `GITHUB_TOKEN=***...` patterns where the real token is masked with asterisks. The script's `if _t not in ("", "***")` check should work but when calling API from inline Python (not via the script), use `sys.path.insert` + `from _secrets import GITHUB_TOKEN` directly — do NOT try to parse the token with regex from the file text.

## Token Retrieval — Use .secrets.local

**`.secrets.local` is the canonical token source.** The push script reads from here. Never use `~/.netrc` or `git remote set-url`.

```bash
# Verify token works:
curl -s -o /dev/null -w "%{http_code}" -X GET "https://api.github.com/repos/ghosteeeeeeee/ATM" \
  -H "Authorization: Bearer $(python3 -c "with open('/root/.hermes/.secrets.local') as f: [print(v.strip().strip('\"').strip(\"'\")) for l in f if l.startswith('GITHUB_TOKEN=') for k,_,v in [l.partition('=')] if k=='GITHUB_TOKEN']")"
# 200 = valid, 401 = expired
```

### Single-File Commit Workflow
If the user says "only X.py committed" or "just commit one file", they want a **single-file commit without the full staged list review**. Steps:
1. `git add scripts/hl-sync-guardian.py` (or whichever file)
2. `git diff --cached --stat` — show them what will be committed
3. Commit and push — do NOT block on the grouped-list review
4. Push via `python3 /root/.hermes/skills/productivity/update-git/references/push_gh.py`
5. If push fails, the token is expired — see Token Recovery below

## Token Recovery (push fails, token expired)
When `push_gh.py` fails with `could not read Username` or 401, the token in `.secrets.local` is expired:

1. Ask user for a new GitHub PAT (classic, `repo` scope)
2. Update `.secrets.local` with new token: `sed -i 's/GITHUB_TOKEN="oldvalue"/GITHUB_TOKEN="newvalue"/' /root/.hermes/.secrets.local`
3. Push via `python3 /root/.hermes/skills/productivity/update-git/references/push_gh.py`

## GitHub Immutable Releases — ZIP Upload May Still Work

This repo has **"Immutable releases\" enabled** (repo → Settings → Releases). In practice, new draft releases created via API may still accept zip uploads — the immutable flag seems to apply at publish time, not creation. Upload succeeded for release `v20260513-0033` (id 321521695). If upload fails with:

```
{"message":"Cannot upload assets to an immutable release."}
```

...then fall back to local endpoint only: zip goes to `/var/www/git/` and is served at `http://localhost:54321/git/<zip>`. The GitHub release page exists (with zero assets) but users download from the local URL.

**Workflow:**
1. Push to GitHub via `push_gh.py`
2. Create release (draft=true so it's not immediately visible — but once created immutable)
3. Copy zip to `/var/www/git/` and update `index.html`
4. Release is visible at `https://github.com/ghosteeeeeeee/ATM/releases/tag/<tag>` but has no downloadable assets

**To fix permanently:** Disable "Immutable releases" in repo Settings → Releases → uncheck "Set all new releases to immutable". Then assets can be uploaded to new releases.

## Selective Staging — Python script (not `git add -A`)

Hermes requires **selective staging** — `git add -A` commits everything including brain docs, plans, memories, and non-trading skills. Use the staging script instead:

**Selective staging pattern (manual):**

1. Show all tracked changes grouped by type:
```bash
cd /root/.hermes
git status --porcelain | grep '^[ M]' | grep -v '^??' | sed 's/^[ M] //' | sort
```

2. Group and present to user. User's preferred categories:
   - **Signals**: `scripts/*_signals.py`, `scripts/signals/` (new directory)
   - **Core trading**: `signal_compactor`, `decider_run`, `live-decider`, `hyperliquid*`, `position_manager`, `hl-sync-guardian`
   - **ATR**: `atr_cache`, `atr_dry_run`, `force_atr_update`
   - **Archive/Runner**: `archive-signals`, `signals_runner`

### Stage signals/ folder completely (tracked + new files)
# New untracked files in signals/ are NOT included in `git add scripts/signals/` — add them explicitly:
git add scripts/signals/ \
  scripts/signals/ema_angle.py \
  scripts/signals/mtp_zscore.py \
  scripts/signals/zscore_pump.py \
  scripts/signals/zscore_rising.py

### Stage with explicit file list (user-approved pattern)
# For user-approved staging lists, use explicit paths — do NOT rely on directory staging to pull in new files:
git add \
  scripts/signals/__init__.py \
  scripts/signals/accel_300.py \
  scripts/signals/rs.py \
  scripts/signals/ema_angle.py \
  scripts/signals/mtp_zscore.py \
  scripts/signals/zscore_pump.py \
  scripts/signals/zscore_rising.py \
  scripts/signal_compactor.py \
  scripts/signal_gen.py \
  scripts/signal_schema.py \
  scripts/decider_run.py \
  scripts/hl-sync-guardian.py \
  scripts/hyperliquid_exchange.py \
  scripts/position_manager.py \
  scripts/cascade_flip.py \
  scripts/hermes_constants.py \
  scripts/brain.py \
  scripts/15m_regime_scanner.py \
  scripts/breakout_engine.py \
  scripts/close_position.py \
  scripts/graceful_close.py \
  scripts/checkpoint_utils.py \
  scripts/error_breadcrumbs.py \
  scripts/event_log.py \
  scripts/hermes_write_with_lock.py \
  scripts/hermes_file_lock.py \
  scripts/backtest_candle.py \
  scripts/backtest_patterns.py \
  scripts/backtest_minimax.py \
  scripts/backfill_72h.py \
  scripts/backfill_hl_pnl.py \
  scripts/backfill_orphan_hl_prices.py \
  scripts/backfill_prices.py \
  scripts/candle_tuner.py \
  scripts/check_mirror.py \
  scripts/macd_rules.py \
  scripts/mtf_macd_backtest.py \
  scripts/pattern_scanner.py \
  scripts/purge_and_compact.py \
  scripts/rsi_backtest.py \
  scripts/speed_tracker.py \
  scripts/study_winning_combos.py \
  scripts/top150.py \
  scripts/wasp.py \
  scripts/zscore_momentum.py \
  scripts/pump_hunter.py \
  scripts/profit_monster.py \
  scripts/price_collector.py \
  scripts/metrics_collector.py \
  scripts/smoke_test.py \
  scripts/trading-checklist.py \
  scripts/update-trades-json.py \
  scripts/rebuild_ab_results.py \
  scripts/self_close_watcher.py \
  scripts/oc_signal_importer.py
```

4. Verify staging: `git status --short | grep '^M ' | wc -l` (should be ~25 files max for a typical trading commit)

5. Unstage any forbidden files that snuck in: `git reset HEAD <file>` for brain/, memories/, .db, wandb/, etc.

**Always show the user the grouped list FIRST** — never stage without approval.

Also add `wandb/` to `.gitignore` proactively — those offline runs are huge and should never be committed:
```
# ─── W&B ──────────────────────────────────────────────────────────────────────
wandb/
scripts/wandb/offline-run-*/
scripts/wandb/debug*.log
scripts/wandb/latest-run
wandb-local/
```

**Signals/ folder staging note:** `git add scripts/signals/` on a tracked folder does NOT auto-stage new untracked files in that folder — always add them explicitly alongside the tracked files.

## Verification
```bash
# Check the release
curl -s "https://api.github.com/repos/ghosteeeeeeee/ATM/releases/latest" | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print(d['tag_name'], d['assets'][0]['name'])"

# Check local
ls -lh /var/www/git/ATM-Hermes-*-full-*.zip | tail -3
```
