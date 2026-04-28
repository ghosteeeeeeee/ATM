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