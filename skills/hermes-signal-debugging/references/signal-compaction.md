---
name: signal-compaction
description: Deterministic hot-set compaction via signal_compactor.py. Active system (ai_decider.py is DEFUNCT). Manages hot-set size limit, ranking, and survival tracking.
version: 2.0.0
author: Hermes Agent
license: MIT
tags: [trading, signals, hot-set, signal-compactor]
input_files:
  - /root/.hermes/data/signals_hermes_runtime.db
  - /var/www/hermes/data/hotset.json
output_files:
  - /var/www/hermes/data/hotset.json
---

# Signal Compaction

Deterministic hot-set compaction — **LLM-free**, pure Python scoring. Runs every 1 minute via `hermes-signal-compactor.timer`.

**Active system: `signal_compactor.py`**. Both `ai_decider.py` AND `breakout_engine.py` also write hotset.json — this is a DUAL-WRITER bug (see hermes-dual-writer-debug).

## Key Facts

| Item | Value |
|------|-------|
| Script | `/root/.hermes/scripts/signal_compactor.py` |
| Hot-set file | `/var/www/hermes/data/hotset.json` (NOT `/root/.hermes/hot-set.json` — that file does not exist) |
| Signal DB | `/root/.hermes/data/signals_hermes_runtime.db` |
**Timer (FIXED 2026-04-27)**: `hermes-signal-compactor.timer` was firing every **1 minute** (`OnCalendar=*:0/1:00`) instead of 5. Changed to `OnCalendar=*:0/5:00`. Timer reload+restart confirmed. Next fire at nearest 5-min boundary. Compactor service needs restart to pick up Python code changes.
**Writers (FIXED 2026-04-27)**: `signal_compactor.py` is the sole authoritative writer. `breakout_engine.py` writes directly to hot-set.json (correct — breakout entries bypass DB). `ai_decider.py` line 1857 write was blocked (commented out). Only `signal_compactor.py` should appear in `grep -n "hotset.json" /root/.hermes/scripts/*.py` as an active writer.
| Scoring | Deterministic: confidence × survival_bonus × staleness_mult (minutes) × regime_mult × source_mult × speed_mult |
| Signal limit | Top 10 (hardcoded at line 478: `scored[:10]`) |
| Scoring | Deterministic: confidence × survival_bonus × staleness_mult (minutes) × regime_mult × source_mult × speed_mult |\n| Staleness | `-20% per minute` → 0.0 at 5 min (dead signal). Fixed 2026-04-26. Staleness recomputed from `entry_origin_ts` on every preserve cycle (2026-04-27 fix). |

## What signal_compactor Does

1. Query PENDING signals (last 240 min, conf ≥ 60, not executed)
2. Detect multi-timeframe LONG/SHORT conflicts — reject conflicted tokens
3. Merge sources per token+direction (GROUP_CONCAT for confluence check)
4. Score each signal with deterministic formula
5. Rank and select top 10
6. Cross-direction conflict filter (keep higher-scoring per token)
7. Deduplicate by token+direction
8. Apply safety filters (blacklists, delist, Solana-only, open-position block)
9. Track survival_round from previous hot-set
10. Write `/var/www/hermes/data/hotset.json`

## Changing the Hot-Set Size Limit

The limit is **hardcoded** at line 478 of `signal_compactor.py`:
```python
top_signals = scored[:10]  # was [:20]
```

Search pattern: `scored\[:20\]` or look for `scored.sort` + slice 3 lines below.

## ⚠️ is_stale NOT Used as Filter — Stale Tokens Enter Hot-Set During Choppy Markets (2026-04-29)

**Symptom**: SpeedTracker computes `is_stale=True` correctly (flat velocity <0.2% on 5m AND 15m), and stores it in `token_speeds` DB table — but stale tokens STILL enter the hot-set. T describes being "clobbered with sideways chop."

**Root cause**: `signal_compactor.py` reads `is_stale` from the DB (`token_speeds` table) and writes it to the hot-set JSON output, but **never checks it as a rejection criterion** during scoring. The pre-filter (lines 355-380) checks blacklist/delist/Solana-only/open-position — `is_stale` is not among them.

**What IS checked vs what SHOULD be checked:**

| Field | Checked as Filter? | Effect |
|-------|---------------------|--------|
| `speed_percentile` | YES — score boost (+15% if ≥80) | Rewards fast tokens, harmless |
| `is_stale` | NO — logged only | **Stale tokens enter freely** |
| `is_overextended` | NO — logged only | Overextended tokens enter freely |

**Empirical evidence** (23:03 UTC):
```
ANIME: stale=1, speed=79.7, vel5m=0.064%  ← STALE, in hot-set
APEX:  stale=1, speed=89.0, vel5m=0.120%  ← STALE, in hot-set
COMP:  stale=1, speed=59.9, vel5m=0.004%  ← STALE, in hot-set
EIGEN: stale=1, speed=0.0,  vel5m=0.0%    ← COMPLETELY FLAT, in hot-set
TAO:   stale=1, speed=68.3, vel5m=0.026% ← STALE, in hot-set
UNI:   stale=1, speed=64.7, vel5m=0.016% ← STALE, in hot-set
```

**The fix location**: `signal_compactor.py` pre-filter section (around line 360 — after delist/Solana checks). Add:
```python
# Hard block: stale tokens (flat for 15+ min) don't enter hot-set
if speed_data.get('is_stale'):
    log(f"  🛡️ [STALE-SKIP] {token}: is_stale=True (vel_5m={vel_5m:.4f}%), skipping")
    continue
```

**Note**: `is_stale=True` tokens are identified by BOTH 5m AND 15m velocity being below `STALE_VELOCITY_THRESHOLD` (0.2%). This means the token has been flat for at least 15 minutes — these are the exact setups that get "clobbered with sideways chop."

**Why speed_percentile doesn't catch this**: In a choppy market, ALL tokens move <0.2%/5m. Every token's velocity clusters near zero → every token gets a similar high `speed_percentile` (relative ranking is meaningless when everything is flat). The percentile ranking is a relative measure, not an absolute one.

**Key difference**: `is_stale` is an ABSOLUTE measure (velocity < threshold). `speed_percentile` is a RELATIVE measure (rank vs universe). Only `is_stale` works during chop.

---

## CRITICAL: Dual-Writer Bug — Three Scripts Write hotset.json

**Symptom**: Hot-set tokens wildly fluctuate every cycle. Staleness values in file don't match computed values. Timer fires every 1 minute instead of 5.

**Writers found**:
1. `signal_compactor.py` — via systemd timer every 5 min (correct)
2. `ai_decider.py` line 1857 — `json.dump({'hotset': hotset_entries, 'source': 'ai_decider', ...}, f)` — runs every pipeline cycle
3. `breakout_engine.py` line 544 — direct `json.dump({'hotset': entries, ...}, f)` — runs every 60 min

**Effect**: ai_decider.py overwrites hotset.json between compactor runs with its own entries, causing wild fluctuations. breakout_engine.py overwrites with yet another set of entries every 60 min.

**Fix**: Block ai_decider.py and breakout_engine.py from writing hotset.json:
- `ai_decider.py` line ~1857: comment out or remove the `json.dump({'hotset': ...}, f)` block
- `breakout_engine.py` line ~544: remove or guard the hotset.json write
- Verify only signal_compactor.py writes: `grep -n "hotset.json" /root/.hermes/scripts/*.py`

## Changing the Run Frequency

signal_compactor does NOT run inside `run_pipeline.py`. It runs via its own systemd timer:
```bash
systemctl cat hermes-signal-compactor.timer
```

**FIXED (2026-04-27)**: Timer now fires every **5 minutes** (`OnCalendar=*:0/5:00`). Was previously misconfigured to 1 min causing excessive churn and fast round depletion.

To verify current setting:
```bash
systemctl cat hermes-signal-compactor.timer | grep OnCalendar
systemctl list-timers hermes-signal-compactor.timer
```

To change frequency:
```bash
sudo sed -i 's/:0\\/1:/:0\\/5:/g' /etc/systemd/system/hermes-signal-compactor.timer
systemctl daemon-reload && systemctl restart hermes-signal-compactor.timer
sudo systemctl restart hermes-signal-compactor.service  # Restart service to pick up Python code changes
```

## Manual Run

```bash
# Normal (writes hotset.json)
python3 /root/.hermes/scripts/signal_compactor.py

# Dry run (log only, no write)
python3 /root/.hermes/scripts/signal_compactor.py --dry

# Verbose (per-signal scoring details)
python3 /root/.hermes/scripts/signal_compactor.py --verbose
```

## Debugging Missing/Empty Hot-Set

### Deadlock: compactor crashes every cycle
If `signal_compactor.py` throws an exception every run, hotset.json goes stale:
```
hotset.json → {timestamp: <old>, stale: True}
pipeline skips compaction → hotset never refreshes
```
**Fix**: Write a fresh hotset.json to break deadlock:
```python
import json, time
hotset = {"hotset": [], "compaction_cycle": 999, "timestamp": time.time()}
with open('/var/www/hermes/data/hotset.json', 'w') as f:
    json.dump(hotset, f)
```

### Query window too short
The query window is 240 minutes (`created_at > datetime('now', '-240 minutes')`). If signals are generated less frequently than that, the hot-set can go empty.

### All signals filtered out
Check the compaction log (`/var/www/hermes/logs/trading.log`) for `[HOTSET-FILTER]` and `⚔️` entries — these show which tokens were rejected and why.

## CRITICAL BUG: Staleness Static on Preserve (GRIFFAIN Stuck Pattern)

When `_filter_safe_prev_hotset` preserves a hot-set entry across cycles, it refreshes `entry['timestamp'] = time.time()` but **does NOT recompute `entry['staleness']`**. The stored staleness becomes permanently stuck — the entry ages but its staleness value never decreases, so it never expires.

**Symptom:** A specific token (e.g., GRIFFAIN) stays in hot-set forever with staleness ~0.83 while genuinely older entries expire correctly.

**Root cause:** `_filter_safe_prev_hotset` (line ~1002) only refreshes timestamp:
```python
entry['timestamp'] = time.time()  # staleness NOT recomputed!
```

**Fix (2026-04-26):** Track `entry_origin_ts` — the time the combo first entered the hot-set this session. On preserve, recompute:
```python
age_m = (time.time() - entry['entry_origin_ts']) / 60
entry['staleness'] = max(0, 1 - age_m * 0.2)
```

Required changes:
1. `_filter_safe_prev_hotset`: initialize `entry_origin_ts = entry.get('entry_origin_ts', entry.get('timestamp', time.time()))`, then recompute staleness on preserve
2. Step 9 (new entries from PENDING): add `'entry_origin_ts': time.time()` 
3. JSON output: write `entry_origin_ts` so it persists in hot-set.json

**Backward compat:** If an existing hot-set entry lacks `entry_origin_ts`, initialize it to `entry.get('timestamp')` so staleness immediately starts from the true age.

---

## Confluence Gate — CONFLUENCE_REQUIRED Toggle

The confluence gate is controlled by `CONFLUENCE_REQUIRED` in `hermes_constants.py`:

```python
CONFLUENCE_REQUIRED = True   # True = require 2+ sources; False = allow single-source
```

**Current behavior (True):** Single-source signals are blocked from hot-set. They stay PENDING until a second source arrives for the same token+direction. Exception: `breakout` source bypasses the gate.

**Disabled (False):** Single-source signals are allowed to pass through to hot-set.

**Location in signal_compactor.py:**
```python
if CONFLUENCE_REQUIRED and len(source_parts) < 2 and source != 'breakout':
    log(f"  🔒 [CONFLUENCE-GATE-BLOCK] {token} {direction}: single-source {{{source}}} — waiting for 2nd source")
    continue
```

**To toggle:** Edit `CONFLUENCE_REQUIRED` in `hermes_constants.py`, then:
```bash
sudo systemctl restart hermes-signal-compactor.service
```

**History:** The confluence gate was previously hardcoded. It was made toggleable on 2026-04-28.

---

## CRITICAL: Confluence Gate — SQL vs Python Source Count

**The bug (2026-04-22):** `HAVING COUNT(*) >= 2` in the SQL query was **always 1** because the query groups by `token, direction` — producing one row per token+direction pair. `COUNT(*)` counts rows in the group, not distinct sources in `GROUP_CONCAT`. The Python confluence gate at line 287 was unreachable because the SQL was already returning 0 rows.

**Wrong approach:**
```sql
GROUP BY token, direction
HAVING COUNT(*) >= 2   -- WRONG: always 1 row per group
```

**Correct approach:** Remove the SQL filter entirely — rely on Python's `source_parts` count:
```python
source_parts = [p.strip() for p in (source or '').split(',') if p.strip()]
if len(source_parts) < 2:
    log(f"  🔒 [CONFLUENCE-GATE] {token} {direction}: single-source — waiting for 2nd source")
    continue
```

The `GROUP_CONCAT` merges all sources per token+direction into a single comma-separated string. Python then parses that string to count distinct sources. The SQL query returns 1 row per token+direction (regardless of source count), so `COUNT(*)` and `COUNT(DISTINCT source)` both equal 1.

**Rule:** When grouping by `token, direction` and using `GROUP_CONCAT` for sources, never use `HAVING COUNT(...)` to check source count — use Python's `len(source_parts)` after splitting the merged string.

## HOT-SET Output Schema

Format (numbered entries, highest priority first, max 10):
```
1. TOKEN | DIRECTION | CONF={.}% | ROUNDS={n} | WAVE={wave_phase} | MOM={momentum_score} | SPD={speed_percentile} | OVEREXT={bool} // TOKEN — {reason}
2. TOKEN | DIRECTION | CONF={.}% | ROUNDS={n} | WAVE={wave_phase} | MOM={momentum_score} | SPD={speed_percentile} | OVEREXT={bool} // TOKEN — {reason}
...
```

**Delimiter rule**: Use `//` to separate structured fields from REASON. Never use `|` inside REASON text.

## Hot-Set Entry Fields

| Field | Source | Notes |
|-------|--------|-------|
| TOKEN | signal.token | |
| DIRECTION | signal.direction | LONG or SHORT |
| CONF | signal.confidence | 0-100 |
| ROUNDS | signal.survival_rounds | Survival rounds — consecutive hot-set cycles. APPROVED signals only. PENDING always 0. |
| WAVE | signal.wave_phase | e.g., accelerating, decelerating, neutral |
| MOM | signal.momentum_score | 0-100 |
| SPD | signal.speed_percentile | 0-100 |
| OVEREXT | signal.is_overextended | true/false |
| REASON | computed string | After `//` delimiter |
| entry_origin_ts | time.time() | When combo first entered hot-set this session — used to compute staleness across preserve cycles |
| staleness | max(0, 1 - age_min × 0.2) | -20%/min from entry_origin_ts. 0.0 = dead signal (5 min). MUST be recomputed on every preserve cycle — NOT just set once on entry. |

---

## ⚠️ BUG 19 RECURRENCE — Timer Reverted to 1-Min (2026-04-29)

**The 2026-04-27 fix did not persist.** Every audit must verify the timer:

```bash
systemctl show hermes-signal-compactor.timer | grep OnCalendar
# EXPECTED: OnCalendar=*-*-* *:0/5:00
# ACTUAL (recurring): OnCalendar=*-*-* *:00/1:00  ← timer reverts
```

**Why it reverts:** The timer file at `/etc/systemd/system/hermes-signal-compactor.timer` can be overwritten by system updates, config management tools, or Docker/image rebuilds. Treat this as a **recurring failure point** — always check on every audit.

**Fix (apply again if reverted):**
```bash
sudo sed -i 's/OnCalendar=\*:\0\/1:00/OnCalendar=*:\0\/5:00/' /etc/systemd/system/hermes-signal-compactor.timer
systemctl daemon-reload && systemctl restart hermes-signal-compactor.timer
systemctl restart hermes-signal-compactor.service
```

---

## ⚠️ STALENESS FROZEN ON READ — Empirical Evidence (2026-04-29)

Despite Bug 17 fix (entry_origin_ts carry-forward), empirical checks show staleness values in the live `hotset.json` do NOT match computed-from-origin values:

```
SKY SHORT: age=6.38min stored_staleness=0.2913 computed=0.0000
XLM SHORT: age=6.38min stored_staleness=0.2913 computed=0.0000
DYM LONG:  age=2.84min stored_staleness=1.0000 computed=0.4327
```

The `_filter_safe_prev_hotset` fix recomputes staleness during compactor execution (write-time), but the stored value in `hotset.json` is written once and only updated on the NEXT compaction cycle. Consumers that read `hotset.json` between compaction cycles get frozen staleness values.

**Impact:** OPP-PENALTY reads fresh from DB so scoring is unaffected. But any code reading `hotset.json` directly (e.g., guardian, dashboards) sees wrong staleness.

**Fix needed:** Staleness should be recomputed at read-time in `_get_hotset_signals()` or wherever the file is consumed, not just at write-time in `_filter_safe_prev_hotset`.

---

## Live Audit Checklist

Run this full check whenever investigating signal pipeline issues or as a routine health audit:

```bash
# 1. TIMER — verify 5-min not 1-min
systemctl show hermes-signal-compactor.timer | grep OnCalendar

# 2. HOT-SET FILE — check age, entry count, cycle
python3 -c "
import json, time
from datetime import datetime
with open('/var/www/hermes/data/hotset.json') as f:
    d = json.load(f)
age = time.time() - d['timestamp']
print(f'hotset.json age: {age:.0f}s ({age/60:.1f}min)')
print(f'Entries: {len(d[\"hotset\"])}')
print(f'Cycle: {d[\"compaction_cycle\"]}')
"

# 3. STALENESS CORRECTNESS — verify stored vs computed
python3 -c "
import json, time
with open('/var/www/hermes/data/hotset.json') as f:
    d = json.load(f)
now = time.time()
mismatches = 0
for e in d['hotset']:
    age = (now - e['entry_origin_ts']) / 60
    computed = max(0.0, 1.0 - age * 0.2)
    stored = e['staleness']
    if abs(computed - stored) > 0.05:
        print(f'STALE: {e[\"token\"]} age={age:.2f}m stored={stored:.4f} computed={computed:.4f}')
        mismatches += 1
print(f'Check complete: {mismatches} mismatches')
"

# 4. DB FUNNEL + STALE PENDING
python3 -c "
import sqlite3
conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
c = conn.cursor()
c.execute('SELECT decision, COUNT(*) FROM signals GROUP BY decision')
for r in c.fetchall(): print(f'  {r[0]}: {r[1]}')
c.execute('''
    SELECT COUNT(*) FROM signals
    WHERE decision=\"PENDING\" AND executed=0
    AND created_at < datetime(\"now\", \"-5 minutes\")
''')
stale = c.fetchone()[0]
print(f'PENDING >5min old (should be 0): {stale}')
if stale > 50:
    print('  ⚠️  HIGH stale count — compactor may be stalled')
conn.close()
"

# 5. OPP-PENALTY SPOT CHECK
cd /root/.hermes/scripts && python3 -c "
import sqlite3
conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
c = conn.cursor()
c.execute('''
    SELECT token, direction, source, confidence FROM signals
    WHERE decision IN (\"PENDING\",\"APPROVED\") AND executed=0
    AND created_at > datetime(\"now\",\"-5 minutes\")
    AND confidence >= 60
    ORDER BY created_at DESC LIMIT 10
''')
for r in c.fetchall(): print(f'  {r[0]} {r[1]}: conf={r[3]} src={r[2]}')
conn.close()
"

# 6. COMPACTOR DRY RUN — errors and key log lines
cd /root/.hermes/scripts && python3 signal_compactor.py --dry 2>&1 | grep -E "OPP-PENALTY|ERROR|Traceback|LOSS-COOLDOWN|STALLED|PASS" | head -20
```