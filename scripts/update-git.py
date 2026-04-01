#!/usr/bin/env python3
"""
update-git — Build Hermes zip + publish to GitHub releases + update local index.
Usage: python3 scripts/update-git.py [--no-push] [--dry-run]
"""
import subprocess, os, re, json, sys, time
from pathlib import Path

HERMES = Path("/root/.hermes")
WWW_GIT = Path("/var/www/git")
GITHUB_REPO = "ghosteeeeeeee/ATM"

def get_token():
    # 1. Env var (highest priority)
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    # 2. .secrets.local (Hermes secrets file)
    secrets = HERMES / ".secrets.local"
    if secrets.exists():
        for line in secrets.read_text().splitlines():
            if line.startswith("GITHUB_TOKEN="):
                return line.split("=", 1)[1].strip().strip('"')
    # 3. ~/.netrc (legacy fallback)
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
    sys.exit("ERROR: No GITHUB_TOKEN env var, .secrets.local, or ~/.netrc found")

TOKEN = get_token()

def sh(*cmd, cwd=HERMES, check=True):
    # Accept either sh("cmd arg1 arg2") string or sh("cmd", "arg1", "arg2") args
    if len(cmd) == 1 and isinstance(cmd[0], str):
        import shlex
        cmd = tuple(shlex.split(cmd[0]))
    r = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    if r.returncode and check:
        sys.exit(f"FAIL: {' '.join(cmd)}\n{r.stderr}")
    return r.stdout.strip()

def github(method, path, data=None, base="https://api.github.com"):
    import urllib.request
    url = f"{base}/repos/{GITHUB_REPO}/{path}"
    hdrs = {
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    body = None
    if data:
        hdrs["Content-Type"] = "application/json"
        body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

def main():
    dry = "--dry-run" in sys.argv
    no_push = "--no-push" in sys.argv

    dirty = sh("git", "status", "--porcelain")
    if dirty:
        print(f"[!] Uncommitted changes:\n{dirty}")
        print("    Run: cd /root/.hermes && git add -A && git commit -m 'msg'")
        sys.exit(1)

    symlinks = sh("find . -type l", check=False)
    if symlinks:
        print(f"[!] SYMLINKS FOUND — resolve before zipping")
        sys.exit(1)

    commit = sh("git rev-parse --short HEAD")
    ts = time.strftime("%Y%m%d-%H%M")
    full_zip = f"/tmp/ATM-Hermes-{ts}-full-{commit}.zip"
    commit_msg = sh("git", "log", "-1", "--format=%s")
    date_str = time.strftime("%b %d, %Y %H:%M UTC")

    print(f"Building: {full_zip}")
    sh("git", "archive", "--prefix=hermes/", "-o", full_zip, "HEAD")
    zip_size = os.path.getsize(full_zip)
    zip_mb = zip_size / 1024 / 1024
    print(f"  {zip_mb:.1f}MB, {sh('unzip', '-l', full_zip, check=False).count(chr(10))} entries")

    if dry:
        print(f"[dry-run] Would create release v{ts}")
        return

    if not no_push:
        print("Pushing to GitHub...")
        sh("git", "push", "github", "main", check=False)

    print("Creating GitHub release...")
    release = github("POST", "releases", data={
        "tag_name": f"v{ts}",
        "target_commitish": "main",
        "name": f"Hermes {date_str}",
        "body": f"**{commit_msg}**\n\nFull repo ({zip_mb:.1f}MB)",
        "draft": True, "prerelease": False,  # draft=True = immutable until published
    })
    rid = release["id"]
    upload_url = release["upload_url"].replace("{?name,label}", "?name=")

    import urllib.request
    with open(full_zip, "rb") as f:
        zip_data = f.read()
    req = urllib.request.Request(
        f"{upload_url}{os.path.basename(full_zip)}",
        data=zip_data,
        headers={
            "Authorization": f"token {TOKEN}",
            "Content-Type": "application/zip",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }, method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        asset = json.loads(resp.read())
    github_dl = asset["browser_download_url"]
    print(f"  GitHub: {github_dl}")

    # Publish the draft release
    github("PATCH", f"releases/{rid}", data={"draft": False})
    print(f"  Published!")

    WWW_GIT.mkdir(parents=True, exist_ok=True)
    local_dest = WWW_GIT / os.path.basename(full_zip)
    with open(full_zip, "wb") as dst:
        dst.write(zip_data)
    print(f"  Local:  http://localhost:54321/git/{os.path.basename(full_zip)}")

    index_path = WWW_GIT / "index.html"
    if index_path.exists():
        html = index_path.read_text()
        html = re.sub(r' <span class="tag-latest">LATEST</span>', '', html)
        new_row = f"""<tr>
  <td><a href="{os.path.basename(full_zip)}">{os.path.basename(full_zip)}</a> <span class="tag-latest">LATEST</span></td>
  <td class="date">{date_str}</td>
  <td class="size">{zip_mb:.1f}MB</td>
  <td><a href="{github_dl}" target="_blank">GitHub</a> {commit_msg}</td>
</tr>"""
        header = '<tr><th>File</th><th>Date</th><th>Size</th><th>Contents</th></tr>'
        html = html.replace(header, header + "\n" + new_row)
        html = re.sub(r'(Download Latest Full [^<]+</a>)',
                      rf'\1 | <a href="{github_dl}" target="_blank">GitHub</a>', html, count=1)
        index_path.write_text(html)
        print(f"  Updated index.html")

    os.unlink(full_zip)
    print(f"\nDone! https://github.com/{GITHUB_REPO}/releases/tag/v{ts}")

if __name__ == "__main__":
    main()
