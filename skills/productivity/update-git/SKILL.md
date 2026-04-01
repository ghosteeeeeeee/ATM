---
name: update-git
description: Package Hermes repo and update /var/www/git/index.html download page. Run after significant code changes.
---

# update-git — Package Hermes repo and update /var/www/git/index.html

## When to Use
Run this **after any significant change** to the Hermes codebase (new features, bug fixes, config changes) when you want to:
- Save a deployable zip archive
- Update the git archives download page at `/var/www/git/index.html`
- Preserve old zips (never deleted, just add new ones)

## Prerequisites
- Working directory: `/root/.hermes`
- Write access to `/var/www/git/`
- Git repo must be clean or tracked

## Steps

### 1. Git add / commit dirty changes
```bash
cd /root/.hermes
git add -A
git status  # review what's staged
git commit -m "your message"  # or skip if nothing to commit
```

### 2. Check if anything changed
```bash
LATEST_COMMIT=$(ls /var/www/git/ATM-Hermes-*-full-*.zip 2>/dev/null | sort | tail -1 | grep -o '[0-9a-f]\{7\}' | head -1)
CURRENT=$(git rev-parse --short HEAD)
if [ "$LATEST_COMMIT" = "$CURRENT" ]; then
    echo "Latest zip ($LATEST_COMMIT) matches HEAD — no new changes, skipping"
    exit 0
fi
if [ -n "$LATEST_COMMIT" ] && git rev-parse --verify ${LATEST_COMMIT} >/dev/null 2>&1; then
    CHANGES=$(git diff --stat ${LATEST_COMMIT}..HEAD --name-only)
    echo "Changes since $LATEST_COMMIT: $CHANGES"
fi
```

### 3. Generate filenames and archive
Naming: `ATM-Hermes-YYYYMMDD-HHMM-full-COMMIT.zip` and `ATM-Hermes-YYYYMMDD-HHMM-fix-COMMIT.zip`
```bash
COMMIT=$(git rev-parse --short HEAD)
TS=$(date +"%Y%m%d-%H%M")
FULL_ZIP="ATM-Hermes-${TS}-full-${COMMIT}.zip"
FIX_ZIP="ATM-Hermes-${TS}-fix-${COMMIT}.zip"
DATE=$(date +"%b %d, %Y %H:%M UTC")
COMMIT_MSG=$(git log -1 --format="%s")
FULL_SIZE=$(du -h /tmp/${FULL_ZIP} 2>/dev/null | cut -f1)

# Full repo
git archive --prefix=hermes/ HEAD | gzip > /tmp/${FULL_ZIP}
FULL_SIZE=$(du -h /tmp/${FULL_ZIP} | cut -f1)

# Copy to web
cp /tmp/${FULL_ZIP} /var/www/git/
chmod 644 /var/www/git/${FULL_ZIP}
echo "Created: ${FULL_ZIP} (${FULL_SIZE})"
```

### 4. Create fix-only zip (changed files only)
```bash
LAST_FULL=$(ls /var/www/git/ATM-Hermes-*-full-*.zip 2>/dev/null | sort | tail -1)
LAST_COMMIT=""
if [ -n "$LAST_FULL" ]; then
    LAST_COMMIT=$(echo $LAST_FULL | grep -o '[0-9a-f]\{7\}' | head -1)
fi

if [ -n "$LAST_COMMIT" ] && git rev-parse --verify ${LAST_COMMIT} >/dev/null 2>&1; then
    CHANGED_FILES=$(git diff --name-only ${LAST_COMMIT}..HEAD 2>/dev/null)
else
    CHANGED_FILES=$(git diff --name-only HEAD 2>/dev/null)
fi

if [ -n "$CHANGED_FILES" ]; then
    mkdir -p /tmp/hermes-fix/
    for f in $CHANGED_FILES; do
        [ -f "$f" ] && mkdir -p /tmp/hermes-fix/$(dirname $f) && cp -r "$f" /tmp/hermes-fix/"$f"
    done
    (cd /tmp && tar czf ${FIX_ZIP} hermes-fix/ && rm -rf hermes-fix/)
    cp /tmp/${FIX_ZIP} /var/www/git/
    chmod 644 /var/www/git/${FIX_ZIP}
    FIX_SIZE=$(du -h /var/www/git/${FIX_ZIP} | cut -f1)
    echo "Fix: ${FIX_ZIP} (${FIX_SIZE})"
fi
```

### 5. Update index.html
```python
#!/usr/bin/env python3
import re

COMMIT = "cc6ffc9"      # set from shell: COMMIT=$(git rev-parse --short HEAD)
TS     = "20260330-2145" # set from shell: TS=$(date +"%Y%m%d-%H%M")
DATE   = "Mar 30, 2026 21:45 UTC"
MSG    = "your commit message"
SIZE_FULL = "6.2M"
SIZE_FIX  = "77K"

FULL_ZIP = f"ATM-Hermes-{TS}-full-{COMMIT}.zip"
FIX_ZIP  = f"ATM-Hermes-{TS}-fix-{COMMIT}.zip"

with open('/var/www/git/index.html') as f:
    html = f.read()

# Increment commit counter
html = re.sub(r'stat-val">(\d+)', lambda m: f'stat-val">{int(m.group(1))+1}', html, count=1)

# Update header latest ref (ATM-Hermes-...-full- pattern)
html = re.sub(r'ATM-Hermes-[0-9]{8}-[0-9]{4}-full-[0-9a-f]{7}\.zip', FULL_ZIP, html, count=1)

# Update header download button hrefs and labels
old_full_link = re.search(r'href="(/git/ATM-Hermes-[^"]+\.zip)"', html)
old_fix_link  = re.search(r'href="(/git/ATM-Hermes-[^"]+\.zip)"', html)
if old_full_link:
    html = html.replace(f'href="{old_full_link.group(1)}"', f'href="/git/{FULL_ZIP}"', 1)
    html = re.sub(r'>Download Latest Full \([0-9a-f]+\)', f'>Download Latest Full ({COMMIT})', html, count=1)
if old_fix_link:
    # replace second occurrence
    html = html.replace(f'href="{old_fix_link.group(1)}"', f'href="/git/{FIX_ZIP}"', 1)
    html = re.sub(r'>Download Fix Only \([0-9a-f]+\)', f'>Download Fix Only ({COMMIT})', html, count=1)

# Remove LATEST from existing rows, add FIX badge to existing fix rows
html = re.sub(r' <span class="tag-latest">LATEST</span>', '', html)
html = re.sub(r' <span class="badge-fix">FIX ONLY</span>', '', html)

new_rows = f"""<tr>
  <td><a href="{FULL_ZIP}">{FULL_ZIP}</a> <span class="tag-latest">LATEST</span></td>
  <td>{DATE}</td>
  <td class="size">{SIZE_FULL}</td>
  <td>{MSG}</td>
</tr>
<tr>
  <td><a href="{FIX_ZIP}">{FIX_ZIP}</a> <span class="badge-fix">FIX ONLY</span></td>
  <td>{DATE}</td>
  <td class="size">{SIZE_FIX}</td>
  <td>{MSG}</td>
</tr>
"""
header = '<tr><th>File</th><th>Date</th><th>Size</th><th>Contents</th></tr>'
html = html.replace(header, header + '\n' + new_rows)

with open('/var/www/git/index.html', 'w') as f:
    f.write(html)
print(f"Updated index.html with {FULL_ZIP}")
```

### 6. Verify
```bash
gunzip -l /var/www/git/${FULL_ZIP} | head -3
grep -c "${FULL_ZIP}" /var/www/git/index.html  # expect 3
```

## Pitfalls
- **Don't delete old zips** — never remove anything from `/var/www/git/`
- **Filesystem path:** `/var/www/git/`, **URL path:** `/git/`
- `tag-latest` badge moves down after each update
- `git diff --name-only HEAD` only sees staged changes — `git add -A` first
- Fix zip only has changed files; full zip is the entire repo
- If no changes since last zip, just skip (exit 0)
- **Naming format is strict:** `ATM-Hermes-YYYYMMDD-HHMM-full-COMMIT.zip`

## CRITICAL: Symlink Prevention
Before zipping, verify NO symlinks exist in the repo:
```bash
find /root/.hermes -type l 2>/dev/null
```
If any symlinks are found, they MUST be replaced with real files before zipping. Use:
```bash
# For a symlink that points to another file in the repo:
cp /path/to/target /path/to/link
rm /path/to/link
# Then commit the change before zipping
```
Symlinks with absolute paths (e.g. `/root/.hermes/...`) will break on any other machine.
Symlinks are resolved by `git archive` but still cause issues for users who clone or unzip.

## Verification
```bash
ls -lh /var/www/git/${FULL_ZIP}
grep "${FULL_ZIP}" /var/www/git/index.html | wc -l  # expect 3
```
