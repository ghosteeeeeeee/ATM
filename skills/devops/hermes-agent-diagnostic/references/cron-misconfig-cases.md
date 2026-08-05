# Cron job failure patterns — captured transcripts

Real failure transcripts from `hermes cron list`, captured 2026-07-13. Use these to pattern-match when a new error shows up. Each pattern includes the verbatim error, root cause, and fix recipe.

## Pattern A — Script-as-filename (bash body saved as literal path)

### Symptom
```
Last run:  2026-07-13T21:15:44.888196+00:00  error: Script not found: 
/root/.hermes/scripts/#!/bin/bash
# Check pipeline health: no stale lock, clean cycle in last 90s, no errors
lock_age=0
if [ -f /tmp/hermes-pipeline.lock ]; then
    lock_age=$(($(date +%s) - $(stat -c %Y /tmp/hermes-pipeline.lock 2>/dev/null || echo 0)))
fi

last_done=$(journalctl -u hermes-pipeline --since "90 seconds ago" -q 2>/dev/null | grep "Pipeline done" | tail -1 | grep -oP '\d{2}:\d{2}:\d{2}' || echo "")
errors=$(journalctl -u hermes-pipeline --since "5 minutes ago" -q 2>/dev/null | grep -c "ERROR\|CRITICAL" || echo 0)

if [ $lock_age -gt 120 ]; then
    echo "[WARN] lock stale ${lock_age}s"
elif [ -z "$last_done" ]; then
    echo "[WARN] no cycle in 90s"
elif [ "$errors" -gt 0 ]; then
    echo "[FAIL] $errors errors in last 5min"
else
    echo "[OK] pipeline clean"
fi
```

Notice the error message continues into the script body — the entire multi-line bash script is reported as the missing filename. That visual signature (error message followed by what looks like shell code) is the smoking gun.

### Root cause
The cron job was created with `no_agent=True` (script mode) and `script=` containing a multi-line bash body. The cron scheduler stored the script body **as the literal filename** in the jobs database instead of writing the body to a file and storing the path. Every tick, the scheduler tries to execute a file literally named `#!/bin/bash\n# Check pipeline health...` which obviously doesn't exist.

### Fix recipe
1. **Extract the bash body** from `hermes cron list` output (everything after `error: Script not found: ` is the body).
2. **Write it to a real file** under `/root/.hermes/scripts/`:
   ```bash
   cat > /root/.hermes/scripts/pipeline-watch.sh <<'EOF'
   #!/bin/bash
   # Check pipeline health: no stale lock, clean cycle in last 90s, no errors
   ... (full body) ...
   EOF
   chmod +x /root/.hermes/scripts/pipeline-watch.sh
   ```
3. **Update the cron job** to point at the real file:
   ```bash
   hermes cron update <job-id> --script /root/.hermes/scripts/pipeline-watch.sh
   ```
4. **Verify** next tick shows `Last run: ... ok`.

### Prevention
When creating a `no_agent=True` cron job with `cronjob` tool, **always pre-write the script to a file** and pass the path. Don't pass the script body inline if it's multi-line.

## Pattern B — HTTP 429 Token Plan exhaustion

### Symptom
```
Last run:  2026-07-13T17:53:52.989941+00:00  error: RuntimeError: HTTP 429: 
Token Plan usage limit reached: Upgrade your Token Plan or purchase 
Credits for more usage. (2056)
```

### Root cause
The job is an LLM-driven eval/analysis task (every ~4h) that's calling the model API and getting rate-limited because the Token Plan budget is exhausted. The error code `(2056)` is provider-specific but the pattern (`HTTP 429: Token Plan usage limit reached`) is universal across providers using subscription tiers.

### Fix recipe (in order of preference)
1. **Top up Token Plan / buy credits** — if the eval is valuable, pay for it.
2. **Drop to a cheaper model**: `hermes cron update <job-id> --model <cheap-model>` (e.g. switch from opus to haiku/mini).
3. **Reduce frequency**: `hermes cron update <job-id> --schedule "every 8h"` or whatever.
4. **Pause until plan renews**: `hermes cron pause <job-id>`.
5. **Remove entirely**: `hermes cron remove <job-id>`.

### Detection
```bash
hermes cron list 2>&1 | grep -B1 "HTTP 429\|Token Plan\|usage limit"
```

## Pattern F — Skill archived but cron job still references it

### Symptom
The job's output file (`~/.hermes/cron/output/<job-id>/<timestamp>.md`) starts with:

```
⚠️ Skill(s) not found and skipped: <skill-name>
Start your response with a brief notice so the user is aware, e.g.:
'⚠️ Skill(s) not found and skipped: <skill-name>'
```

The agent then runs the prompt without the skill instructions, improvising — usually succeeding in a "good enough" way but losing the structured audit/output the skill was supposed to guarantee.

### Root cause
Skill was moved to `.archive/` (manually or by the curator) but the cron job referencing it was never updated. Real example from 2026-07-13: `closed-trades-eval` cron job referenced the `closed-trades-eval` skill, which lived at `/root/.hermes/skills/.archive/closed-trades-eval/SKILL.md` (archived Apr 28). The job was created Apr 3 — before the archive — and never updated.

### Detection recipe
```bash
# Find cron jobs referencing skills that have been archived
python3 <<'EOF'
import json, os
d = json.load(open('/root/.hermes/cron/jobs.json'))
for j in d.get('jobs', []):
    for s in j.get('skills', []):
        active = os.path.isdir(f'/root/.hermes/skills/{s}')
        archived = os.path.isdir(f'/root/.hermes/skills/.archive/{s}')
        if archived and not active:
            print(f'ORPHAN: {j["id"][:8]} ({j.get("name","?")}) references archived skill "{s}"')
EOF
```

### Fix options
1. **Restore the skill from archive**: `mv ~/.hermes/skills/.archive/<skill-name> ~/.hermes/skills/<skill-name>`
2. **Remove the skill reference from the job**: `hermes cron edit <id>`, delete the `skills:` line
3. **Replace with a different skill** that covers the same territory
4. **Delete the job entirely** if the audit is no longer needed (`hermes cron remove <id>`)

### Prevention
Before archiving any skill, grep for it in `~/.hermes/cron/jobs.json` and update any referencing jobs first:
```bash
grep -r "<skill-name>" /root/.hermes/cron/jobs.json
```

## Pattern C — Python traceback in cron output

### Symptom
```
Last run:  2026-07-13T...  error: Traceback (most recent call last):
  File "/root/.hermes/...", line N, in <module>
    ...
KeyError: 'foo'
```

### Root cause
A real bug in the prompt-driven agent code. Need to read the traceback and fix the underlying issue.

### Fix recipe
1. Copy the full traceback.
2. Identify the file + line.
3. Read 10-20 lines of context around the failure.
4. Patch the bug (typically: missing null check, KeyError on dict access, wrong env var name).
5. Verify the next tick succeeds.

## Pattern D — Systemd service `failed` but cron `ok` (false positive)

### Symptom
```bash
systemctl list-units --type=service --all | grep hermes
● hermes-git-release.service     loaded failed failed
```

But `hermes cron list` shows the corresponding job as `Last run: ... ok`.

### Root cause
The service is a `Type=oneshot` wrapper around a script that legitimately exits non-zero (e.g. `update-git.py` refuses to commit dirty trees). The timer is what should be active, and it is — the cron job is succeeding every tick.

### Fix
**None needed.** This is by-design. If the noise bothers you:
- Change the service to `SuccessExitStatus=1` so it shows `exited` instead of `failed`.
- Or filter it out of your monitoring.

## Pattern E — `Last run:` field empty (never ran)

### Symptom
```
Name:      some-job
Schedule:  */15 * * * *
Next run:  2026-07-13T21:15:00+00:00
Deliver:   local
[no Last run line]
```

### Root cause
Job was created recently and hasn't fired yet, OR job is paused (`[paused]` tag visible).

### Fix
- If `Next run:` is in the future → wait.
- If `Next run:` is in the past and `Last run` empty → paused. `hermes cron resume <id>`.
- If `[paused]` tag present and that's intentional → leave it.

## Quick triage command

```bash
# All cron failures across the board
hermes cron list 2>&1 | grep -B1 "error:"

# Specifically script-as-filename
hermes cron list 2>&1 | grep -B1 "Script not found"

# Specifically Token Plan exhaustion
hermes cron list 2>&1 | grep -B1 "HTTP 429\|Token Plan"

# Jobs that never ran
hermes cron list 2>&1 | awk '/^  [a-f0-9]+/{job=$0; getline name; getline sched; getline repeat; getline next; getline deliver; getline skills; getline mode; getline last; if (last !~ /Last run:/) print job, "NEVER RAN"}'
```
