---
name: install-consolidation
description: Consolidate duplicate code directories safely — verify active install, byte-compare files, trace history, check refs before deleting
triggers:
  - "there are multiple copies of the same codebase"
  - "which install is actually running"
  - "duplicate scripts directories"
  - "consolidate hermes installs"
---

# Install Consolidation — Verify Before Deleting Duplicate Directories

## When to Use
When multiple similar-looking code directories exist and you need to consolidate to one canonical location without breaking a running system.

## Core Principle
**Verify identity, trace references, then delete** — never assume duplicate dirs are safe to remove just because they look similar.

## Step-by-Step

### 1. Map all relevant directories
```bash
ls -d /root/hermes* /root/trading* 2>/dev/null
find /root -maxdepth 3 -type d -name "*hermes*" -o -name "*trading*" -o -name "*export*" 2>/dev/null
```

### 2. Identify the active install (the one actually running)
```bash
# Check systemd service WorkingDirectory
systemctl cat <service> | grep WorkingDirectory

# Check cron jobs
grep -r "<keyword>" /etc/cron.d /etc/crontab /var/spool/cron

# Check scripts themselves for hardcoded paths
grep -r "<old-path>" /root/.hermes/scripts/*.py
```

### 3. Compare files byte-for-byte
```bash
# List file counts
ls /dir1/*.py | wc -l
ls /dir2/*.py | wc -l

# For shared files, diff
diff /dir1/script.py /dir2/script.py

# Check all key pipeline scripts at once
for f in run_pipeline.py ai_decider.py decider_run.py signal_gen.py hermes-trades-api.py position_manager.py brain.py; do
    echo "=== $f ==="
    diff "/dir1/$f" "/dir2/$f" 2>/dev/null | head -5
done
```

### 4. Trace how the duplication arose (session archaeology)
```bash
session_search query="hermes-v3 hermes-export install path"
```
Look for:
- When the secondary dir was created
- Which session created it
- What the original intent was
- Whether files were edited in one but not the other

### 5. Verify no active references before deleting
```bash
# Check systemd, cron, and scripts
grep -r "<old-path>" /etc/systemd/system /etc/cron.d /var/spool/cron /root/.hermes/scripts/*.py 2>/dev/null | grep -v ".git"

# Check config files
grep -r "<old-path>" /root/.hermes/ 2>/dev/null | grep -v ".git" | grep -v "report"
```

### 6. Archive, don't delete (until confirmed safe)
```bash
mv /old/dir /root/hermes-archive-$(date +%Y%m%d)/
```

### 7. Update memory
```bash
memory action=replace target=memory \
  content="Primary install: /path/to/active/scripts/ — archive paths exist but are not referenced by systemd or cron" \
  old_text="<previous text referencing the old paths>"
```

### 8. Verify pipeline/system still healthy after move
```bash
systemctl status hermes-pipeline
tail -5 /root/.hermes/logs/pipeline.log
```

## Lessons Learned (from hermes consolidation 2026-04-13)
- Files being byte-for-byte identical is NOT enough — need to trace what created them and why
- systemd WorkingDirectory is the authoritative source of truth for which install is live
- Session history reveals whether old dirs were accidentally created vs intentionally kept
- Reports/docs can reference old paths — those are historical records, leave them
- Always check for other copies (trading-system-export, hermes-export, hermes-v3, etc.) in the same parent dir
- The "consolidation" was actually just archiving — no file content needed to be merged, just the confusion about which one was live
