---
name: ollama-heartbeat
description: Complete SOP for testing software changes with backups and rollback. Use when testing any significant software change on Tokyo or Dallas.
metadata: {"clawdbot":{"emoji":"🐲","os":["linux"],"requires":{"bins":["ollama","node","git"]},"install":[{"id":"install-ollama","kind":"exec","command":"curl -fsSL https://ollama.com/install.sh | sh","label":"Install Ollama"}]}}
---

# Software Testing SOP (with Backup & Rollback)

## When to Use
- Testing new AI models (Ollama, etc.)
- Making significant config changes
- Any change that could break the system

---

## Phase 1: Pre-Test Backup

### 1. Commit current state to git
```bash
cd /var/www/html
git add -A
git commit -m "Pre-[change-name] backup - $(date +%Y-%m-%d\ %H:%M)"
```

### 2. Sync to backup server (Dallas)
```bash
rsync -avz --delete /var/www/html/ root@172.96.137.105:/var/www/html/
```

### 3. Create rollback note in shared notes
```bash
cat >> /root/shared_notes/notes.md << 'EOF'

---
**Urgency: TEST IN PROGRESS**

Testing [description]. If issues:
1. Check /rollback for snapshot
2. Run: `cd /var/www/html && git log --oneline`
3. Restore: `git checkout <commit-hash> -- .`

**Last good commit:** [commit-hash]
EOF
```

### 4. Sync notes to backup server
```bash
rsync -avz /root/shared_notes/notes.md root@172.96.137.105:/root/shared_notes/
```

---

## Phase 2: Run Test

### Example: Install and test Ollama heartbeat
```bash
# Install Ollama (if not installed)
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2:1b

# Test the script
/root/.openclaw/workspace/scripts/heartbeat.sh

# Measure execution time
time /root/.openclaw/workspace/scripts/heartbeat.sh
```

---

## Phase 3: Verification

### Check if working
```bash
# Check service is running
ps aux | grep ollama

# Test API
curl -s http://localhost:11434/api/generate -d '{"model": "llama3.2:1b", "prompt": "Hi", "stream": false}'

# Check logs
tail /root/shared_notes/heartbeat.log
```

### If broken - Rollback
```bash
cd /var/www/html
git checkout <last-good-commit-hash> -- .
git commit -m "Rollback to pre-test state"
rsync -avz /var/www/html/ root@172.96.137.105:/var/www/html/
```

---

## Phase 4: Post-Test Cleanup

### If successful:
1. Commit the changes
2. Update notes with success status
3. Sync to backup
4. Remove urgency note

```bash
cd /var/www/html
git add -A
git commit -m "Post-test: [change description]"

# Update notes
sed -i '/Urgency: TEST IN PROGRESS/d' /root/shared_notes/notes.md

# Sync
rsync -avz /root/shared_notes/notes.md root@172.96.137.105:/root/shared_notes/
rsync -avz /var/www/html/ root@172.96.137.105:/var/www/html/
```

---

## Quick Reference

| Action | Command |
|--------|---------|
| Backup | `cd /var/www/html && git add -A && git commit -m "Backup"` |
| Sync to Dallas | `rsync -avz /var/www/html/ root@172.96.137.105:/var/www/html/` |
| Sync notes | `rsync -avz /root/shared_notes/notes.md root@172.96.137.105:/root/shared_notes/` |
| View history | `git log --oneline` |
| Rollback | `git checkout <hash> -- .` |
| Check service | `ps aux \| grep <service-name>` |
| Check logs | `tail /root/shared_notes/heartbeat.log` |

---

## Testing Notification Template

For partner server (Ro), include in notes:

```
---
**⚠️ URGENT: [Test Name] In Progress**

Jo is testing [description] on [server].

**If things break:**
1. Check /rollback for snapshot
2. Run: `cd /var/www/html && git log --oneline`
3. To restore: `git checkout <commit-hash> -- .`

**Last good commit:** [hash]

[Partner] - if [server] goes silent, you may need to SSH in and rollback.
```
