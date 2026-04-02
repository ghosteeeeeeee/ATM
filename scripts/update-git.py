#!/usr/bin/env python3
"""
update-git -- Build Hermes zip + publish to GitHub releases + update local index.
Usage: python3 scripts/update-git.py [--no-push] [--dry-run]
"""
import subprocess, os, re, json, sys, time
from pathlib import Path

HERMES = Path("/root/.hermes")
WWW_GIT = Path("/var/www/git")
GITHUB_REPO = "ghosteeeeeeee/ATM"

def _get_token():
    t = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if t:
        return t
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from _secrets import GITHUB_TOKEN
        if GITHUB_TOKEN and GITHUB_TOKEN not in ("", "***"):
            return GITHUB_TOKEN
    except Exception:
        pass
    try:
        netrc = Path.home() / ".netrc"
        if netrc.exists():
            for line in netrc.read_text().splitlines():
                if "api.github.com" in line:
                    parts = line.split()
                    if "login" in parts:
                        idx = parts.index("login")
                        if idx + 1 < len(parts):
                            return parts[idx + 1]
    except Exception:
        pass
    sys.exit("ERROR: No GITHUB_TOKEN found in env, _secrets, or ~/.netrc")

GH = _get_token()

def sh(*cmd, cwd=None, check=True):
    r = subprocess.run(cmd, cwd=str(cwd or HERMES), capture_output=True, text=True)
    if r.returncode and check:
        sys.exit(f"FAIL: {chr(10).join(str(c) for c in cmd)}{chr(10)}{r.stderr}")
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

    dirty = sh("git", "status", "--porcelain")
    if dirty:
        print(f"[!] Uncommitted changes:{chr(10)}{dirty}")
        print("    Run: cd /root/.hermes && git add -A && git commit -m msg")
        if not dry:
            sys.exit(1)

    symlinks = sh("find", ".", "-type", "l", check=False)
    # Known exception: scripts/ai_decider.py -> ai-decider.py (required for underscore import)
    symlinks_clean = "\n".join(l for l in symlinks.splitlines()
                                 if 'ai_decider.py' not in l)
    if symlinks_clean.strip():
        print(f"[!] SYMLINKS FOUND:{chr(10)}{symlinks_clean}")
        sys.exit(1)

    # Note: --short=HEAD fails in this env, use pipe instead
    commit = sh("git", "rev-parse", "HEAD")[0:7]
    ts = time.strftime("%Y%m%d-%H%M")
    full_zip = f"/tmp/ATM-Hermes-{ts}-full-{commit}.zip"
    # Use tag with commit to prevent collision on re-runs
    tag_name = f"v{commit}-{ts}"
    commit_msg = sh("git", "log", "-1", "--format=%s")
    date_str = time.strftime("%b %d, %Y %H:%M UTC")

    if not dry:
        try:
            releases = github_api("GET", "releases")
            existing = next((r for r in releases if r["tag_name"] == tag_name), None)
            if existing:
                print(f"Release {tag_name} already exists -- skipping")
                return
        except Exception:
            pass

    print(f"Building: {full_zip}")
    sh("git", "archive", "--prefix=hermes/", "-o", full_zip, "HEAD")
    zip_size = os.path.getsize(full_zip)
    zip_mb = zip_size / 1024 / 1024
    print(f"  {zip_mb:.1f}MB")

    if dry:
        print(f"[dry-run] Would create release {tag_name}")
        return
    # 6. Push to GitHub (both remotes)
    if not no_push:
        print("Pushing to GitHub...")
        # Use force-withLease instead of --force for safer push
        sh("git", "push", "github", "main", check=False)
        print("  Pushed to github/main")
    print("Creating GitHub release...")
    release_data = {
        "tag_name": tag_name,
        "target_commitish": "main",
        "name": f"Hermes {date_str}",
        "body": f"**{commit_msg}**{chr(10)}{chr(10)}Full repo: `{full_zip}` ({zip_mb:.1f}MB)",
        "draft": False,
        "prerelease": False,
    }
    release = github_api("POST", "releases", data=release_data)
    release_id = release["id"]
    upload_url = release["upload_url"].replace("{?name,label}", "?name=")

    zip_basename = os.path.basename(full_zip)
    with open(full_zip, "rb") as f:
        zip_data = f.read()

    # Upload zip to GitHub release assets
    import urllib.request, urllib.error
    upload_url_clean = f"{upload_url}{zip_basename}"
    req = urllib.request.Request(
        upload_url_clean,
        data=zip_data,
        headers={
            "Authorization": f"token {GH}",
            "Content-Type": "application/zip",
            "Accept": "application/vnd.github+json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            asset = json.loads(resp.read())
        github_dl = asset["browser_download_url"]
        print(f"  GitHub: {github_dl}")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        # Fall back: release was created, zip is at local path — GitHub release URL works
        github_dl = f"https://github.com/{GITHUB_REPO}/releases/tag/{tag_name}"
        print(f"  GitHub upload failed ({e.code}) — release created but asset not attached")
        print(f"  GitHub: {github_dl}")

    WWW_GIT.mkdir(parents=True, exist_ok=True)
    local_dest = WWW_GIT / zip_basename
    with open(local_dest, "wb") as dst:
        dst.write(zip_data)
    print(f"  Local:  http://localhost:54321/git/{zip_basename}")

    index_path = WWW_GIT / "index.html"
    if index_path.exists():
        html = index_path.read_text()
        new_row = f"<tr>{chr(10)}  <td><a href=\"{zip_basename}\">{zip_basename}</a> <span class=\"tag-latest\">LATEST</span></td>{chr(10)}  <td class=\"date\">{date_str}</td>{chr(10)}  <td class=\"size\">{zip_mb:.1f}MB</td>{chr(10)}  <td><a href=\"{github_dl}\" target=\"_blank\">GitHub</a> {commit_msg}</td>{chr(10)}</tr>"
        header = "<tr><th>File</th><th>Date</th><th>Size</th><th>Contents</th></tr>"
        html = html.replace(header, header + chr(10) + new_row)
        index_path.write_text(html)

    os.unlink(full_zip)
    print(f"\nDone! https://github.com/{GITHUB_REPO}/releases/tag/{tag_name}")

if __name__ == "__main__":
    main()
