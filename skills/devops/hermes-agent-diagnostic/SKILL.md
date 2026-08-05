---
name: hermes-agent-diagnostic
description: Health-check the Hermes Agent runtime (NOT the Hermes crypto-trading system — see Pitfall 1) — covers `hermes doctor` hang workaround, `hermes status`/`cron list`/`gateway status`/`mcp list`/`sessions stats`/`tools list` substitution surface, cron-job misconfig patterns (script-as-filename, HTTP 429 Token Plan, archived-skill-still-referenced, cron verb disambiguation), gateway-in-manual-mode detection, token/cost analysis via `hermes insights` + state.db SQL, and known-broken subcommands.
---

# Hermes Agent Runtime Diagnostic

When the user says "diagnose hermes" / "check the hermes install" / "is hermes healthy", they usually mean **the Hermes Agent runtime** — the framework itself (CLI, gateway, cron, MCP, sessions, skills), NOT the Hermes crypto-trading system that happens to also be called "Hermes". See Pitfall 1 for the disambiguation rule.

## Disambiguation rule (Hermes Agent vs Hermes trading system)

Two completely different systems share the name "Hermes" in this environment. Pick the right one **first**, before running any checks. Wrong choice = wrong diagnostic, wasted time, confused user.

| What you find in cwd / paths | Means | Use |
|---|---|---|
| `/root/.hermes/scripts/signal_compactor.py`, `hl-sync-guardian.py`, hot-set.json | **Trading system** | `trading-system-audit` + `smoke-test-fast-scan` skills |
| `/root/hermes-agent/hermes_cli/main.py`, `~/.hermes/config.yaml`, `hermes doctor` | **Hermes Agent runtime** | This skill |

When ambiguous, ask one quick clarifying question with choices rather than guessing. The user is usually in one or the other context and a single choice resolves it. Do NOT default to the trading system just because `/root/.hermes/scripts/` exists — that path is shared (Hermes Agent's working dir is `~/.hermes` even though the agent code lives at `/root/hermes-agent`).

## The `hermes doctor` hang — and the substitute surface

**Pitfall 2 (most important): `hermes doctor` hangs silently.** Reproduced 2026-07-13 — `timeout 60 hermes doctor` exits 124 with zero stdout. `strace` shows it binds `::1` IPv6 and waits on a network call (likely API validation). Don't burn 60s of user time waiting. Use the substitute surface instead — equivalent coverage, all responsive:

```bash
hermes --version                                    # version + install method
hermes status --all                                 # model, providers, toolsets, gateway, cron count
hermes config path && hermes config check           # config sanity + missing-env warnings
hermes cron list                                    # every job + last-run ok/error + script errors
hermes sessions stats                               # sessions DB size + message count
hermes mcp list                                     # MCP servers + transport + status
hermes gateway status                               # gateway PID + service mode
hermes tools list                                   # enabled/disabled toolsets
```

This gives you: version drift, provider/key health, cron health, gateway health, session DB growth, MCP wiring, toolset state — everything `hermes doctor` would have shown plus the actual last-run cron statuses that `doctor` doesn't surface.

If you really need to try `hermes doctor`, **always wrap it in `timeout 30`** so a hang doesn't stall the diagnostic.

## Cron-job failure patterns to recognize

When scanning `hermes cron list`, two recurring failure shapes show up over and over:

### A. Script-as-filename (broken `script:` field)
```
Last run:  2026-07-13T21:15:44  error: Script not found: 
/root/.hermes/scripts/#!/bin/bash
# Check pipeline health: ...
lock_age=0
if [ -f /tmp/hermes-pipeline.lock ]; then
```

**Cause:** When a `no_agent=True` cron job is created with a multi-line bash script in its `script` field, the cron scheduler stored the script body as the literal filename path instead of writing it to a file. Every tick it tries to execute a file literally named `#!/bin/bash`.

**Fix:**
1. Extract the bash body from the job's `script` field (visible in `hermes cron list` output).
2. Write it to a real file: `cat > /root/.hermes/scripts/<descriptive-name>.sh <<'EOF' ... EOF; chmod +x ...`
3. Update the job: `hermes cron update <id> --script /root/.hermes/scripts/<descriptive-name>.sh`

### B. HTTP 429 Token Plan from periodic eval job
```
Last run:  2026-07-13T17:53:52  error: RuntimeError: HTTP 429: 
Token Plan usage limit reached: Upgrade your Token Plan or purchase 
Credits for more usage. (2056)
```

**Cause:** A scheduled eval/analysis job (every ~4h) is hitting the Token Plan rate limit. Recurring failures mean the plan is exhausted or the model is too expensive for the call frequency.

**Fix options (in order):**
1. Top up Token Plan / buy credits
2. Drop the job's model to a cheaper tier (`hermes cron update <id> --model <cheap-model>`)
3. Reduce frequency (`hermes cron update <id> --schedule "every 8h"` etc.)
4. Pause until plan is renewed (`hermes cron pause <id>`)

## Other things `hermes status --all` exposes that need interpretation

| Field | Normal | Watch out if |
|---|---|---|
| `Gateway Service → Status` | `✓ running` (systemd) | `running manually, not as a system service` — won't survive reboots; consider `hermes gateway install` |
| `Gateway Service → Manager` | `systemd` | `systemd (user)` — only works while user session is alive |
| `Gateway State JSON → platforms.api_server.state` | `connected` or absent | `disconnected` — API server adapter registered but offline |
| `Active agents` | 0 when idle | >0 during a normal session, persistent >0 indicates stuck agent |
| `Sessions DB size` | Grows ~1-10 MB/day | >2 GB → consider `hermes sessions prune --older-than 90` |
| `Scheduled Jobs` | Active count = Total | Mismatch means paused jobs |
| API Keys `✗ (not set)` | Expected for unused providers | Provider you're actively using shows `✗` → broken setup |

## Cron job health — the right way to read `hermes cron list`

The output is a per-job block. The two fields that matter for triage:

1. **`Last run: ... ok`** — fine, ignore.
2. **`Last run: ... error: <message>`** — broken. Read the message.
   - If error starts with `Script not found:` → Pitfall A above.
   - If error starts with `RuntimeError: HTTP 429` → Pitfall B above.
   - If error starts with `RuntimeError:` or `ConnectionError` → transient, check next tick.
   - If error is a Python traceback → save the trace, dig into the script.

A common false positive: `Hermes Git Release` service in systemd shows `failed` every tick because `update-git.py` correctly refuses to commit dirty trees. Not a bug — exit-1-by-design.

## Quick health-check script

Save as `~/.hermes/scripts/hermes-agent-health.sh` (chmod +x) and run via `bash ~/.hermes/scripts/hermes-agent-health.sh`:

```bash
#!/bin/bash
# Hermes Agent runtime health snapshot — runs in <10s, no network.
set +e
echo "=== VERSION ==="
hermes --version 2>&1 | head -3

echo "=== STATUS (one-liner summary) ==="
hermes status 2>&1 | grep -E "Model:|Gateway:|Cron Jobs:|Sessions:" | head -5

echo "=== CRON FAILURES ==="
hermes cron list 2>&1 | grep -B1 "error:" | head -20

echo "=== GATEWAY ==="
hermes gateway status 2>&1 | head -3

echo "=== MCP SERVERS ==="
hermes mcp list 2>&1 | tail -10

echo "=== SESSIONS DB SIZE ==="
hermes sessions stats 2>&1 | grep -E "Total sessions|Database size"

echo "=== DISK / SECRETS PERMS ==="
df -h /root 2>&1 | tail -2
stat -c '%n %a' ~/.hermes/config.yaml ~/.hermes/.env ~/.hermes/auth.json 2>&1
```

## Cron command verbs — common traps

The `hermes cron` subcommand set has tripped up even experienced users (including me — `update` does not exist):

| You want to... | Verb | Notes |
|---|---|---|
| List active jobs | `hermes cron list` | Paused jobs are HIDDEN from default output |
| List everything including paused | `hermes cron list --all` | Use this when checking for stuck/disabled work |
| Create a job | `hermes cron create ...` | or `add` (alias) |
| Edit a job's prompt/schedule/skills | `hermes cron edit <id>` | The right verb for in-place edits. **`update` is not a valid verb.** |
| Pause (don't delete) | `hermes cron pause <id>` | Job stays in DB, hidden from `list`. Verify via `list --all`. |
| Resume a paused job | `hermes cron resume <id>` | |
| Run immediately | `hermes cron run <id>` | Triggers next tick (doesn't wait for schedule) |
| Delete | `hermes cron remove <id>` | or `rm` / `delete` (aliases) |

**Pitfall:** Running `hermes cron update <id>` produces `error: argument cron_command: invalid choice: 'update'` — wastes 5s of diagnostic time and surfaces as "broken CLI" until you remember the actual verb is `edit`. Same trap applies to other cron actions: trust the help output (`hermes cron --help`) before guessing.

## Token / cost analysis — when the user asks "where are tokens going"

When the user follows up the diagnostic with "analyse token usage" / "where is the burn" / "what's costing so much", `hermes insights` is the entry point but it has known shape traps.

### The "30 days is misleading" trap

`hermes insights` defaults to a 30-day window. On this system (2026-07-13) almost all activity happened today — the 30-day summary showed 1,083 sessions with 285M tokens, but 985 of those sessions were today alone. **Always check the date range first** — if the period span is one day, the "30 day" framing is a lie. Use `--days 1` or `--days 7` to get a truer picture.

### The cost-not-tracked gap

Hermes's `insights` tool reports token counts but `actual_cost_usd` is **0.0 across the board** when the active provider is MiniMax (verified 2026-07-13). The MiniMax SDK doesn't expose pricing back to Hermes, so cost analysis is tokens-only. Don't promise the user USD numbers — give tokens + per-provider breakdown instead.

### Filter pattern: per-source breakdown

```bash
hermes insights --source cron       # only cron sessions
hermes insights --source cli        # only CLI sessions
hermes insights --source subagent   # subagent delegation cost
```

The `--source` filter is essential — the default view buries the per-platform breakdown in a small table.

### Deeper per-job cost via state.db (when `insights` isn't enough)

`hermes insights` aggregates but doesn't show per-cron-job cost. Query `~/.hermes/state.db` directly to get per-job token totals — this is where you'll find outlier jobs:

```bash
sqlite3 ~/.hermes/state.db <<'EOF'
.mode column
.headers on
SELECT 
  CASE 
    WHEN title LIKE 'hermes-pipeline%' THEN 'hermes-pipeline'
    WHEN title LIKE 'profit-monster%' THEN 'profit-monster'
    WHEN title LIKE 'hype-paper-sync%' THEN 'hype-paper-sync'
    WHEN title LIKE 'wasp-health%' THEN 'wasp-health'
    WHEN title LIKE 'closed-trades%' THEN 'closed-trades-eval'
    WHEN title LIKE 'study-winning%' THEN 'study-winning-combos'
    WHEN title LIKE 'signals-compact%' THEN 'signals-compact'
    WHEN title LIKE 'Candle Predictor%' THEN 'candle-predictor-15min'
    ELSE title
  END as job,
  COUNT(*) as sessions,
  SUM(input_tokens+output_tokens+cache_read_tokens) as total_tokens,
  ROUND(AVG(input_tokens+output_tokens+cache_read_tokens),0) as avg_tok
FROM sessions
WHERE source='cron'
GROUP BY 1
ORDER BY total_tokens DESC;
EOF
```

### Top-spending cron outliers to watch for

Captured 2026-07-13:
- **`candle-predictor-15min`**: 427K tokens/run average — **15× the median**. If on every-15min schedule, that's ~7.7M tokens/day from one job. Suspect root cause: loading multi-hour candle history per token into LLM context each tick. First thing to disable when chasing cost.
- **Two `Hermes Signal Audit` cron sessions**: 5.0M + 4.3M tokens, both at 13:57:23 on Jul 13 (130ms apart, same model). **9.27M tokens in 130ms is not normal.** Either a one-off massive analysis OR a context-explosion bug. Always inspect `~/.hermes/cron/output/<job-id>/` for the actual prompt when you see >1M tokens in a single session.

See `references/token-usage-analysis.md` for the full SQL toolkit + per-cron-job baseline data.

## What NOT to do

- ❌ Don't run `hermes doctor` without `timeout 30` — it hangs silently.
- ❌ Don't fix the trading system when the user asked about the Agent runtime (or vice versa). Ask if ambiguous.
- ❌ Don't assume `hermes status --all` exit-0 = fully healthy — it doesn't surface cron `error:` lines. Always check `hermes cron list` separately.
- ❌ Don't `git checkout -- file` anything under `/root/hermes-agent` to "fix" a corruption — the agent code lives at `/root/hermes-agent`, not `/root/.hermes/`.
- ❌ Don't try to fix `hermes doctor` by editing it — it's bundled, read-only, and you'll waste time. Use the substitute surface.
- ❌ Don't use `hermes cron update` — the verb doesn't exist; use `edit`. Don't run `hermes cron list` and assume you're seeing everything — paused jobs are hidden unless you pass `--all`.
- ❌ Don't trust `terminal(background=True)` returning `exit_code: 0` as "the script finished in milliseconds." See "Pitfall 3 — `background=True` exit code is the wrapper, not the script" below.

## Pitfall 3 — `terminal(background=True)` exit code is the wrapper, not the script

When you call `terminal(command="python3 long_script.py", background=True, ...)`, the
wrapper returns **within ~100ms** with `exit_code: 0` (and an `output_preview` of
the very first lines, if any have flushed). That `0` is the **wrapper subprocess**
that spawned the long-running script, NOT the long-running script itself. The
real script is still booting (or has been running for hours) and you only know
its actual status by:

1. `process(action="poll", session_id=...)` — returns `status: "running"` or `"exited"` with the **real** exit code
2. `process(action="wait", session_id=...)` — blocks up to 180s, returns when status changes
3. Tailing the script's own log file directly (`/var/log/<service>.log`, `/tmp/<job>.log`, etc.)

**Concrete failure mode (observed 2026-07-15 03:30):** agent ran
`terminal(command="python3 /root/.hermes/scripts/candle_predictor.py --nowandb --interval=15", background=True)`
and got back `exit_code: 0, session_id: proc_5ea5f1e960c3, pid: 3415096` almost
instantly. Briefly thought the script had finished. The wrapper had only spawned
the process; the real Python script was still importing torch + sqlite3 + the
LLM runner. Verified liveness with `ps -p 3415096 -o pid,stat,etime,cmd` (showed
`STAT=Ssl ELAPSED=00:11 CMD=...candle_predictor.py...`) and only then trusted it
was actually running.

**Rule of thumb:** `terminal(background=True)` returning ≤ 2 seconds with
`exit_code: 0` for a script that should take 20+ minutes = wrapper exit, not
script exit. The real status is in `process(session_id=...)`. When in doubt,
check `ps -p <pid>` directly.

**Related to but distinct from** the foreground-timeout pattern in
`candle-predictor-tuner` → `references/running-predictor.md` — that's about
`terminal(foreground=True)` killing long runs at 300s. This pitfall is the
**opposite** direction: `background=True` "succeeds" too quickly and the agent
trusts the early exit_code instead of polling the real session.

## Scheduled-script checklist (for any long-running command, not just cron)

When a user prompt (especially a cron job) hands you a literal command to run
that you know takes >2 minutes, do not paste it into a default `terminal()` call.
Apply this checklist BEFORE the first `terminal()` invocation:

1. **Estimate wall time.** If > 60s, plan for `background=True` from the start.
2. **Pick a log file.** The script almost certainly has one (`/var/log/<svc>.log`,
   `/tmp/<job>.log`, or write-to-stdout-and-tail-it). Tail it with `process`
   polls — that's the source of truth, not the `terminal()` return.
3. **Save the `session_id`.** You'll need it for `process(action="wait"|"poll")`
   in 180s chunks. The `wait` action clamps at 180s server-side regardless of
   the `timeout` parameter you pass.
4. **Check for stale locks / preflight state** if the script uses one
   (e.g. `/tmp/candle-predictor.lock`, `/tmp/hermes-pipeline.lock`). A 300s
   timeout from a previous run leaves these behind and silently wedges the
   next run.
5. **Build the verification command** for after the run completes (DB count,
   post-run report script, etc.) so you can report results in one shot.

This applies to any long-running command — predictors, backfills, full-codebase
audits, batched backtests. The pattern is identical; only the log path and
verification command change.

## Files for deeper dive

- `references/diagnostic-commands.md` — full substitute command list with expected output templates.
- `references/cron-misconfig-cases.md` — captured real cron failure transcripts (script-as-filename, HTTP 429, traceback patterns) with reproduction recipes.
- `references/token-usage-analysis.md` — `hermes insights` filter patterns, state.db SQL toolkit for per-job cost, and the "all activity is today" trap.
