---
name: update-git
description: Package Hermes repo and publish to GitHub releases + local /var/www/git/ index. Run after significant code changes.
---

# update-git — Package Hermes & Publish to GitHub Releases

## When to Use
Run this **after any significant change** to the Hermes codebase (new features, bug fixes, config changes). It:
1. Commits staged changes
2. Builds the zip (full repo)
3. Pushes to GitHub
4. Creates a GitHub release with the zip as a downloadable asset
5. Updates the local `/var/www/git/index.html` download page

## Prerequisites
- Working directory: `/root/.hermes`
- GitHub token in `~/.netrc` or env `GITHUB_TOKEN` (machine-readable format: `api.github.com login=<token>`)
- Remote `github` configured: `https://github.com/ghosteeeeeeee/ATM.git`
- Write access to `/var/www/git/`

## GitHub Token Setup
```bash
# Option 1: ~/.netrc (machine format)
echo "machine api.github.com login ghp_YOURTOKEN" >> ~/.netrc
chmod 600 ~/.netrc

# Option 2: env variable
export GITHUB_TOKEN="ghp_YOURTOKEN"
```

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

# Get token from ~/.netrc (supports both "login=<token>" and "login <token>" formats)
GH = None
netrc_path = Path.home() / ".netrc"
if netrc_path.exists():
    content = netrc_path.read_text()
    # Try "login=<token>" format first
    if "api.github.com" in content:
        try:
            GH = content.split("login=")[1].split()[0]
        except:
            pass
    # Try "login <token>" format (space-separated)
    if not GH or not GH.startswith('ghp_'):
        for line in content.split('\n'):
            if 'api.github.com' in line:
                for part in line.split():
                    if part.startswith('ghp_'):
                        GH = part
                        break
GITHUB_TOKEN = GH

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
        print(f"[!] Uncommitted changes:\n{dirty}")
        print("    Run: cd /root/.hermes && git add -A && git commit -m 'your msg'")
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

    # 6. Push to GitHub (both remotes)
    if not no_push:
        print("Pushing to GitHub...")
        sh("git", "push", "github", "main", "--force", check=False)
        print("  Pushed to github/main")

    # 7. Create GitHub release (as draft first so we can upload assets)
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

    # 8. Upload zip to GitHub release
    zip_basename = os.path.basename(full_zip)
    with open(full_zip, "rb") as f:
        zip_data = f.read()

    import urllib.request
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
    with urllib.request.urlopen(req) as resp:
        asset = json.loads(resp.read())

    github_dl = asset["browser_download_url"]
    print(f"  GitHub: {github_dl}")

    # 8b. Publish the draft release
    print("Publishing release...")
    github_api("PATCH", f"releases/{release_id}", data={"draft": False})

    # 9. Copy to local /var/www/git/
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

### Build
```bash
cd /root/.hermes
COMMIT=$(git rev-parse --short HEAD)
TS=$(date +"%Y%m%d-%H%M")
git archive --prefix=hermes/ -o /tmp/ATM-Hermes-${TS}-full-${COMMIT}.zip HEAD
```

### Push to GitHub
```bash
git push github main
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
- **Don't delete old zips** — never remove anything from `/var/www/git/`
- **Symlinks break standalone zips** — always check with `find . -type l` before zipping
- Fix zip is NOT uploaded to GitHub (too small to be worth the API call — users download the full zip)
- GitHub releases are append-only; old releases accumulate — this is fine
- The local `/var/www/git/index.html` only shows the LATEST local zip; GitHub shows all releases
- If GitHub token is invalid, GitHub push/upload will fail with 401/403

## Verification
```bash
# Check the release
curl -s "https://api.github.com/repos/ghosteeeeeeee/ATM/releases/latest" | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print(d['tag_name'], d['assets'][0]['name'])"

# Check local
ls -lh /var/www/git/ATM-Hermes-*-full-*.zip | tail -3
```
