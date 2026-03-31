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
LATEST_COMMIT=$(ls /var/www/git/hermes-full-*.zip 2>/dev/null | head -1 | grep -o '[0-9a-f]\{7\}' | head -1)
if [ -n "$LATEST_COMMIT" ] && git rev-parse --verify ${LATEST_COMMIT} >/dev/null 2>&1; then
    CHANGES=$(git diff --stat ${LATEST_COMMIT}..HEAD --name-only)
fi
if [ -z "$CHANGES" ]; then
    echo "No changes since last zip — skip"
    exit 0
fi
```

### 3. Generate filenames and archive
```bash
COMMIT=$(git rev-parse --short HEAD)
DATE=$(date +"%b %d, %Y %H:%M UTC")
FULL_ZIP="hermes-full-${COMMIT}.zip"
FIX_ZIP="hermes-fix-${COMMIT}.zip"
COMMIT_MSG=$(git log -1 --format="%s")

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
LAST_FULL=$(ls /var/www/git/hermes-full-*.zip 2>/dev/null | sort | tail -1)
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
Read the current file, update header stats and links, prepend new zip row at top of table.

**Changes in the HTML:**
- Update commit count: `stat-val">N` (first `.stat` div, the number)
- Update latest ref in header: `hermes-full-OLD.zip` → `hermes-full-NEW.zip`
- Update download links: both `href` values to new commit
- Prepend new table row at top with `tag-latest`; remove `tag-latest` from previous first row

### 6. Verify
```bash
gunzip -l /var/www/git/${FULL_ZIP} | head -3
grep -c "hermes-full-${COMMIT}.zip" /var/www/git/index.html  # expect 3
```

## Pitfalls
- **Don't delete old zips** — never remove anything from `/var/www/git/`
- **Filesystem path:** `/var/www/git/`, **URL path:** `/git/`
- `tag-latest` badge moves down after each update
- `git diff --name-only HEAD` only sees staged changes — `git add -A` first
- Fix zip only has changed files; full zip is the entire repo
- If no changes since last zip, just skip (exit 0)

## Verification
```bash
ls -lh /var/www/git/hermes-full-${COMMIT}.zip
grep "hermes-full-${COMMIT}.zip" /var/www/git/index.html | wc -l  # expect 3
```
