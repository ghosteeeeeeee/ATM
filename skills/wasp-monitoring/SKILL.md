---
name: wasp-monitoring
description: Operate and maintain the Hermes WASP monitoring daemon (/root/.hermes/scripts/wasp.py) — triage ERROR/WARNING output, distinguish false positives from real failures, fix stale hardcoded thresholds, know what to auto-fix vs flag to T.
category: trading
author: Hermes (cron session 2026-07-13)
created: 2026-07-13
---

# WASP Monitoring — Triage, Threshold Maintenance, and Auto-Fix Boundaries

WASP is the `/root/.hermes/scripts/wasp.py` health & anomaly daemon run every 30 min via
`hermes-wasp.timer` (NOT crontab — T uses systemd exclusively per SOPS). It aggregates
~20+ health checks (prices, HL cache, Ollama, hotset, signals, ab-testing, etc.) and emits
CRITICAL/ERROR/WARNING/INFO lines to `/root/.hermes/logs/wasp.log`.

This skill covers the class of bugs WASP itself accumulates: **stale hardcoded thresholds,
environment-assumption drift, and false positives that mask real failures**.

---

## When to Load This Skill

- A WASP run produced ERRORs or WARNINGs that don't match reality (system is healthy but flagged)
- WASP added a new check that's flagging known-good state
- A core data source shrank/grew (e.g. HL universe pruned) and WASP's hardcoded count broke
- You're deciding whether a WASP issue is safe to auto-fix or needs T's review
- The user asks "why does WASP keep flagging X"

---

## Quick Triage Workflow

```bash
# 1. Run WASP and capture
cd /root/.hermes/scripts && python3 wasp.py 2>&1 | head -40

# 2. For each ERROR/WARNING, check the corresponding source-of-truth independently.
#    NEVER trust WASP's interpretation without verification.

# 3. Categorize:
#    REAL → log + flag to T
#    FALSE POSITIVE from stale threshold → fix the threshold + add a comment explaining why
#    FALSE POSITIVE from environment drift (cron vs systemd, etc.) → fix the check itself
#    TRANSIENT (cold start, race) → leave alone, will self-resolve
```

**Canonical truth hierarchy:** live systemd status + journalctl > source DB/files > WASP output.
Always verify WASP's flag against the actual system state before fixing anything.

---

## What WASP Checks (and the Stale-Threshold Failure Mode)

WASP encodes numerical expectations as **hardcoded constants** at the top of each `check_*()`
function. Examples that have drifted:

| Check | Stale Assumption | Current Reality | When It Drifted |
|-------|------------------|-----------------|-----------------|
| `prices: Only N tokens` | `expected ~229` | ~83 (HL pruned delisted + @XXX IDs filtered) | Apr 2026 |
| `cron: WASP cron job not installed` | `crontab -l` check | T uses systemd timers exclusively | SOPS says "no cron" |
| `ollama: Generate check failed` (15s timeout) | Cold-start treated as failure | First /api/generate after model load is slow | Ollama behavior |

**Pattern:** WASP was written assuming specific environment state at a specific point in time.
When the environment changes (HL universe shrinks, infra switches from cron to systemd, model
warmup behavior shifts), WASP's literal thresholds become wrong.

**Diagnostic command — for any "Only N tokens / expected M" ERROR:**
```bash
python3 -c "
import requests
r = requests.post('https://api.hyperliquid.xyz/info', json={'type':'meta'}, timeout=10)
names = [u['name'] for u in r.json()['universe'] if not u.get('isDelisted')]
print('live HL active universe:', len(names))
"
# Compare to what price_collector's SKIP_TOKENS removes from that
python3 -c "from hermes_constants import SHORT_BLACKLIST, LONG_BLACKLIST; print('SKIP_TOKENS:', len(SHORT_BLACKLIST | LONG_BLACKLIST))"
# Result: live_HL - SKIP_TOKENS ≈ actual prices.json token count
```

**Always set the new floor BELOW the real count with a clear comment** — the threshold is
meant to catch a sudden collapse (collector broke), not to match a moving target. Example:
```python
# Was: if count < 200: bug("ERROR", "prices", f"Only {count} tokens (expected ~229)")
# Now: floor at 50 — anything below means the collector actually broke
if count < 50:
    bug("ERROR", "prices", f"Only {count} tokens in prices.json (expected ~83)")
```

---

## Auto-Fix vs Flag-To-T Decision Matrix

WASP itself is **monitoring tooling**, not the hot-set or trade execution path. Modifications
to wasp.py are SAFE to apply directly per the Bug Fix Rule ("If a bug fix is obvious, fix it
directly without asking").

| Issue Type | Safe to Auto-Fix? | Rationale |
|------------|-------------------|-----------|
| Stale hardcoded count/age threshold | ✅ YES | Monitoring code only; no trade impact |
| Wrong environment assumption (cron vs systemd, paths) | ✅ YES | Same — monitoring only |
| False-positive categorization (ERROR → WARNING) | ✅ YES | Just changing severity |
| Adding a new check | ⚠️ ASK T | New check = new noise surface |
| Removing an existing check | ⚠️ ASK T | May hide a real signal |
| Changing WASP's output format/destination | ⚠️ ASK T | Downstream consumers may parse it |
| Fixing logic in hot-set / signals / decider | ❌ NEVER | Trading rules: "very surgical" |
| Changing ATR TP/SL thresholds | ❌ NEVER | Trading rules: "ask T first" |
| Touching hermes_constants.py | ❌ NEVER | Per SOUL: critical file |

**Always do a sanity rerun after auto-fixes:**
```bash
cd /root/.hermes/scripts && python3 -c "import py_compile; py_compile.compile('wasp.py', doraise=True)"
cd /root/.hermes/scripts && python3 wasp.py 2>&1 | head -20
# Confirm: ERROR count dropped, no new WARNINGs introduced
```

---

## Common WASP False Positives and Their Fixes

### 1. "prices: Only N tokens in prices.json (expected ~229)"

**Cause:** HL universe shrunk OR price_collector filters more tokens than WASP knows about.

**Fix:**
```python
# In wasp.py, the check_prices() function (around line 89):
count = len(prices)
if count < 50:  # floor — actual universe is ~83 as of Apr 2026
    bug("ERROR", "prices", f"Only {count} tokens in prices.json (expected ~83)")
```

**Why 50 not 200:** 50 is a generous floor — anything below means the collector actually broke
(delisted filtering went too far, network died, etc.), not that the universe shrunk further.

### 2. "cron: WASP cron job not installed"

**Cause:** WASP checks `crontab -l` but T uses systemd timers per SOPS.

**Fix:**
```python
# Replace crontab -l check with systemctl check:
result = subprocess.run(
    ["systemctl", "is-enabled", "hermes-wasp.timer"],
    capture_output=True, text=True, timeout=5,
)
if result.returncode != 0 or result.stdout.strip() != "enabled":
    bug("WARNING", "cron", f"WASP systemd timer not enabled ({result.stdout.strip()})")
```

### 3. "ollama: Generate check failed: HTTPConnectionPool ... Read timed out"

**Two real causes** — diagnose by listing ALL ollama processes before assuming anything:

**Cause A — Orphan `ollama serve` competing with systemd-managed instance:**
A manual `ollama serve` was started at some point and never killed. Now two `ollama serve`
processes are running (one managed by systemd, one detached), each spawning its own runners
for every model. Requests get routed to whichever runner is free, but the second-server's
runners sit mostly idle until requests round-robin to them, while the managed-server's
runners saturate. End result: sustained 6-15s `/api/generate` latency with periodic 500s
exactly at the 15s timeout.

Diagnostic:
```bash
ps -eo pid,ppid,stat,%cpu,%mem,etime,cmd | grep -E "ollama" | grep -v grep
# Look for TWO `ollama serve` rows where the older one has elapsed time of hours,
# AND neither one's PPID is the other. If you see that pattern, you have a duplicate.
```

Distinguishing field: **`etime`** — systemd-managed serves get restarted fresh (etime small);
an orphan serve drifts upward over hours/days.

Auto-fix:
```bash
# 1. Identify the orphan: it's the one with PPID=1 (not a child of anything),
#    AND higher elapsed time than the systemd one. Usually PID is the LOWER-numbered one
#    of the two `ollama serve` rows.
systemctl restart ollama                # spawns new systemd-managed instance
# wait a few seconds for it to come up, then:
ps -eo pid,ppid,etime,cmd | grep "ollama serve" | grep -v grep
# Find the orphan (older elapsed time, PPID=1, NOT the one systemd just spawned)
kill -TERM <orphan_pid>
# Confirm one serve process remains, all runners are children of it
```

After killing the orphan, perform one warmup `/api/generate` (cold load takes ~25s,
subsequent calls drop to 3-5s). Re-run WASP — ERROR gone.

Reference incident: 2026-07-14 21:15 UTC WASP run. Two `ollama serve` processes were running
(PID 2839707 system-managed from yesterday + PID 3248823 orphan from 16:25). After
`systemctl restart ollama` + `kill -TERM 3248823`, Ollama response time dropped from
6-15s (with 500s) to 3.50s and WASP cleared the ERROR.

**Cause B — Cold-start latency on first `/api/generate` after model load:**
First `/api/generate` call after Ollama wakes up takes >15s. The model loads from
disk on first use.

**Verification (always do before treating as real):**
```bash
curl -sS --max-time 5 http://localhost:11434/api/tags | head -3
# Should return JSON with model list in <1s — proves Ollama is alive
ps aux | grep ollama | grep -v grep
# Should show ONE `ollama serve` + its runner children
```

**If Ollama is actually alive AND only one serve process:** this is transient. WASP's 15s
timeout is too tight for cold-start. Can be safely relaxed to 30s OR retried. Don't
auto-fix the timeout — flag to T because changing the read timeout could mask real Ollama
hangs.

**Real CPU overload vs cold-start vs orphan-serve (differentiate by looking at the log):**
```bash
journalctl -u ollama --since "5 min ago" --no-pager | grep "POST.*api/generate"
```
- **Cold-start pattern:** the failing call is the FIRST generate after a quiet period
  (only `/api/tags` GETs in the preceding minutes). Confirm: it's transient, leave alone.
- **Real overload pattern:** other processes are working hard (`candle_predictor`,
  `signals_runner`, etc. — `ps -ef | grep python`), the model runner has high accumulated
  CPU time (e.g. 5h+), and recent generates show a degrading ramp (1s → 6s → 17s → 30s+
  with 500 errors). This is a stuck/overloaded runner — flag to T for a model restart.
  Check the runner with:
  ```bash
  ps -p <runner_pid> -o pid,stat,%cpu,%mem,etime,cmd
  # %CPU > 50%, etime > 1h, accumulated cpu time is the giveaway
  ```

**Why this matters (2026-07-14 incident):** the Ollama-timeout ERROR was masking a real
overload where the runner was at 72% CPU × 5h46m. Repeated 30s+ 500s indicated the
runner needed a `systemctl restart ollama`. WASP correctly flagged it as ERROR — the
pitfall was treating it as the cold-start case and dismissing it.

### 4. "ab-testing: 1 orphaned AB result rows"

**Cause:** Legacy aggregate row in `ab_results` table with `variant_id IS NULL OR =''`.
Usually one-off, harmlessly sitting there from a deleted variant.

**Verification:**
```python
import psycopg2
conn = psycopg2.connect('host=/var/run/postgresql dbname=brain user=postgres')
cur = conn.cursor()
cur.execute("SELECT * FROM ab_results WHERE variant_id IS NULL OR variant_id = ''")
# Inspect — usually it's a 'sl-distance-test' aggregate from before A/B versioning tightened
```

**Decision:** Don't auto-DELETE — could be a real test result being misclassified. Flag to T
with the row contents.

### 5. "trailing-stop: N stale momentum_cache entries > 2h old"

**Cause:** `momentum_cache` table has rows for tokens no longer in active universe.

**Decision:** Flag to T. The fix involves a cleanup SQL or a blacklist filter, both of which
touch the live trading path.

### 6. "signals: Rapid-fire duplicate signals"

**Cause:** Single signal type (e.g. accel_300) firing repeatedly for the same token within
short windows — often indicates the signal's de-duplication window is too short, or it's
re-firing due to data gaps.

**Decision:** Flag to T. Signal logic is hot-set territory per trading rules.

### 7. "hotset: Hotset empty (within grace)"

**Cause:** WASP itself OR pipeline just ran; hotset not yet repopulated.

**Decision:** Ignore if the grace period hasn't elapsed (typically 2 min). If persistent, it's
a real pipeline issue — load `hermes-pipeline-debug`.

### 8. "paper-hl-sync: 'str' object has no attribute 'get'"

**Cause:** WASP treated HL position data as a list of dicts but HL returned a dict
(`{coin: {size, direction, entry_px, unrealized_pnl, leverage}}`).

**Reference:** `hermes-pipeline-debug/references/hl-position-api-return-shapes.md` has the
exact data shape. This was patched in wasp.py line 777 on 2026-07-13.

**Pattern:** Always iterate HL positions via `.items()` not by indexing as a list.

### 9. WASP timer is enabled but has no next trigger

**Cause:** `hermes-wasp.service` was configured as `Type=oneshot` with `RemainAfterExit=yes`.
The service remains `active (exited)` forever, so an `OnUnitActiveSec=` timer cannot activate
it again. `systemctl is-enabled` alone misses this failure.

**Fix:** Remove `RemainAfterExit=yes`, then reload and reset the timer/service state:
```bash
systemctl daemon-reload
systemctl stop hermes-wasp.service
systemctl restart hermes-wasp.timer
systemctl list-timers hermes-wasp.timer --all --no-pager
```
Verify `RemainAfterExit=no`, service is `inactive (dead)` between runs, and the timer has a
real `NEXT` timestamp.

### 10. Paper-HL sync says `'str' object has no attribute 'get'`

`get_open_hype_positions_curl()` returns `{TOKEN: {size, direction, ...}}`; derive tokens from
`positions.keys()` (or `.items()`), not by iterating it as list rows. Keep a guarded list fallback
only for backward compatibility.

### 11. Pipeline heartbeat reports millions of minutes stale

`pipeline_heartbeat.json` is a component map such as
`{"decider_run": {"timestamp": "...Z"}, "position_manager": {...}}`, not a flat object with a
top-level timestamp. Parse all valid component timestamps and compare against the newest one.

### 12. Obsolete ai-decider warning

`ai_decider.py` is defunct. The current deterministic `signal_compactor.py` lifecycle uses
`PENDING`, `EXPIRED`, and `EXECUTED`, not `APPROVED`/`WAIT`. Health-check recent
`EXPIRED`/`EXECUTED` updates instead; do not infer Ollama failure from obsolete DB states.

---

## Verifying WASP Itself Is Healthy

After auto-fixes, do a sanity check:

```bash
# 1. WASP completes without crashing
cd /root/.hermes/scripts && timeout 120 python3 wasp.py > /tmp/wasp_check.log 2>&1
echo "exit: $?"
tail -10 /tmp/wasp_check.log

# 2. WASP timer is enabled and last fired recently
systemctl status hermes-wasp.timer | grep -E "Active:|enabled"
systemctl list-timers hermes-wasp.timer

# 3. WASP log is being written to
ls -la /root/.hermes/logs/wasp.log
tail -5 /root/.hermes/logs/wasp.log

# 4. Error counts trending down over multiple runs
grep -c "ERROR" /root/.hermes/logs/wasp.log  # last 24h
```

---

## Threshold Reference (Updated 2026-07-13)

When updating any WASP threshold, add a comment with the date and the source of truth:

```python
# 2026-07-13: HL universe is ~83 (Hyperliquid pruned delisted coins + price_collector
# filters @XXX numeric IDs + SKIP_TOKENS). Floor 50 catches actual collector failures
# without false-flagging normal shrunk universe.
if count < 50:
    bug(...)
```

**Active thresholds as of 2026-07-13:**

| Check | Threshold | Source of Truth |
|-------|-----------|-----------------|
| prices.json age | < 120s | `cat /root/.hermes/data/prices.json \| jq .updated` |
| prices.json token count | >= 50 | live HL active universe - SKIP_TOKENS |
| hl-cache age | < 240s | `_ts` in `/var/www/hermes/data/hl_cache.json`; price_collector currently runs ~105–175s |
| ollama generate | < 15s (cold-start flag) | `curl /api/tags` succeeds |
| ollama runner CPU/etime | < 50% CPU AND < 1h accumulated | `ps -o %cpu,etime,cmd` on the `ollama runner` PID. Past 5h uptime at high CPU = likely stuck |
| WASP timer | enabled | `systemctl is-enabled hermes-wasp.timer` |

---

## Related Skills

- `hermes-pipeline-debug` — pipeline-level freezes / stale signals / lock contention
- `verify-prices` — candle/price data integrity audit
- `hl-trading-debug` — Hyperliquid API/sync failures
- `trading-system-audit` — full codebase audit