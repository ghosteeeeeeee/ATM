---
name: signal-compaction
description: Clean up stale signals and rebuild the hot-set. Frees the ai-decider pipeline from backlogged WAIT/PENDING signals, forces hot-set rebuild so empty position slots get filled.
version: 1.0.0
author: Hermes Agent
license: MIT
tags: [trading, signals, hot-set, maintenance]
input_files:
  - /root/.hermes/data/signals_hermes_runtime.db
  - /var/www/hermes/data/hotset.json
output_files:
  - /var/www/hermes/data/hotset.json
---

# Signal Compaction

Clean up stale signals in the Hermes signal database and rebuild `hotset.json`.

## Problem

The ai-decider hot-set logic (`_load_hot_rounds`) only considers signals created within the **last 3 hours**. Old WAIT/PENDING/APPROVED signals accumulate and block the pipeline:

- **WAIT signals** (e.g. from 07:48, now 12+ hours old) sit unreviewed
- **_load_hot_rounds** ignores them → hot-set stays tiny
- **decider-run** finds 0 APPROVED signals → 2 position slots stay empty
- Meanwhile **22,876 SKIPPED/EXPIRED** signals pile up, slowing DB queries

## What This Skill Does

1. **Audit** — report current signal counts by decision state and age
2. **Expire stale signals** — mark PENDING/APPROVED/WAIT signals older than 3 hours as EXPIRED
3. **Archive old dead signals** — DELETE SKIPPED/EXPIRED signals older than 24 hours (optional, run with `--archive`)
4. **Rebuild hot-set** — force `_load_hot_rounds` + rewrite `hotset.json`
5. **Report** — before/after counts + new hot-set contents

## Safety Rules

- **Stale window = 3 hours** — matches `_load_hot_rounds` `created_at > datetime('now', '-3 hours')` filter exactly
- **Archive cutoff = 24 hours** — SKIPPED/EXPIRED signals older than 24h are dead weight
- **DELETE, not DROP TABLE** — only removes rows, schema stays intact
- **hotset.json always valid** — if rebuild fails, old file is not overwritten
- **Backup DB before archive** — `cp signals_hermes_runtime.db signals_hermes_runtime.db.bak`

## Usage

```bash
# Dry-run (default — shows what would be done)
python3 /root/.hermes/skills/signal-compaction/scripts/compact.py

# Apply expirations (mark stale PENDING/APPROVED/WAIT as EXPIRED)
python3 /root/.hermes/skills/signal-compaction/scripts/compact.py --expire

# Apply + archive old SKIPPED/EXPIRED (DELETE rows > 24h old)
python3 /root/.hermes/skills/signal-compaction/scripts/compact.py --expire --archive

# Rebuild hot-set only (no DB changes)
python3 /root/.hermes/skills/signal-compaction/scripts/compact.py --rebuild-only
```

## When to Run

- Position slots aren't filling despite high-confidence PENDING signals
- ai-decider seems stuck or hot-set is very small (< 5 tokens)
- After a trading session ends and you want to reset signal state
- Scheduled: every 4-6 hours during active trading to prevent backlog
- **"No signals in last 30 mins" logged AND hotset.json stale** → check DB row count first (`SELECT COUNT(*) FROM signals`)

## Hotset Staleness Deadlock (CRITICAL)

If `ai_decider.py` crashes every cycle (e.g., NameError, unhandled exception), the compaction never runs, and `hotset.json` ages past the 3600s threshold:

```
hotset.json → {timestamp: <old>, stale: True}
pipeline skips compaction → "Compaction already run this cycle" 
hotset never refreshes → deadlock
```

**Manual unlock**: Write a fresh hotset.json to break the deadlock:

```python
import json, time
hotset = {
    "hotset": [],          # empty = no stale tokens
    "compaction_cycle": 999,  # any high number
    "timestamp": time.time()  # now = not stale
}
with open('/root/.hermes/data/hotset.json', 'w') as f:
    json.dump(hotset, f)
```

This forces `is_hard_stale` to return False on next cycle, allowing normal compaction to resume.

**Current paths** (verify if stale):
- hotset.json: `/root/.hermes/data/hotset.json`
- signal DB: `/root/.hermes/data/signals_hermes_runtime.db`
- pipeline log: `/root/.hermes/logs/pipeline.log`
- hotset stale threshold: 3600s (1 hour) in `ai_decider.py`

**Verification**: After unlocking, inject a test signal and verify end-to-end:

```python
from hermes_tools import terminal
# Add test signal
terminal("cd /root/.hermes/scripts && python3 -c \"from ai_decider import add_signal; add_signal('BCH', 'LONG', 'test', 'deadlock-verification', confidence=65.0, value=34.1, z_score=-1.198, z_score_tier='suppressed')\"")

# Then check:
# 1. DB has the signal
terminal("sqlite3 /root/.hermes/data/signals_hermes_runtime.db \"SELECT token, direction, confidence, decision FROM signals ORDER BY id DESC LIMIT 3\"")
# 2. hotset.json updated within 2 minutes
# BCH should appear in hotset.json
```

**"No signals in last 30 mins — skipping" in logs**: Can mean two things:
1. NORMAL: `_do_compaction_llm()` found 0 PENDING signals in DB, but hot-set is healthy → fallback preserves existing hotset.
2. PROBLEM: Signal DB is genuinely empty (0 rows in `signals` table) AND hotset.json is stale → deadlock. Check: `SELECT COUNT(*) FROM signals`.

Distinguish by checking DB row count. If 0 rows and hotset.json is stale (>3600s), manual unlock needed (see below).

## Key Time Windows

| Signal state | Stale threshold | Action |
|-------------|-----------------|--------|
| PENDING/APPROVED/WAIT | > 3 hours | Mark EXPIRED |
| SKIPPED/EXPIRED | > 24 hours | DELETE (with --archive) |
| EXECUTED | never deleted | Keep for A/B analysis |

## HOT-SET Output Schema (Final — as used in .hermes/prompt/main-prompt.md)

Format (numbered entries, highest priority first, max 20):
```
1. TOKEN | DIRECTION | CONF={.}% | ROUNDS={n} | WAVE={wave_phase} | MOM={momentum_score} | SPD={speed_percentile} | OVEREXT={bool} // TOKEN — {reason}
2. TOKEN | DIRECTION | CONF={.}% | ROUNDS={n} | WAVE={wave_phase} | MOM={momentum_score} | SPD={speed_percentile} | OVEREXT={bool} // TOKEN — {reason}
...
```

Key delimiter rule: **Use `//` to separate structured fields from free-text REASON**. Never use `|` inside REASON text — `|` is the field delimiter. The `//` delimiter avoids collision with `|` that may appear in natural language reasons (e.g., "HYPE | momentum").

Full HOT-SET entry fields:
| Field | Source | Notes |
|-------|--------|-------|
| TOKEN | signal.token | |
| DIRECTION | signal.direction | LONG or SHORT |
| CONF | signal.confidence | 0-100 |
| ROUNDS | signal.compact_rounds | Survival rounds — more rounds = stronger signal |
| WAVE | signal.wave_phase | e.g., ascending, peak, descending, accumulation |
| MOM | signal.momentum_score | 0-100 |
| SPD | signal.speed_percentile | 0-100 |
| OVEREXT | signal.is_overextended | true/false |
| REASON | signal.reason | After `//` delimiter |

Counter-pressure: If a hot-set LONG develops SHORT pressure over successive rounds, confidence decreases until replaced. ROUNDS carry forward survival strength.

## Hot-Set Entry Filters (verify current in ai_decider.py)

| Filter | Threshold | Notes |
|--------|-----------|-------|
| Confidence | ≥ 50%? | MIN_CONFIDENCE_FLOOR = 50 in signal_schema.py — verify actual hotset filter in `_do_compaction_llm()` |
| Decision | PENDING only | Only PENDING signals are ranked by LLM; APPROVED signals bypass ranking |
| Direction | LONG or SHORT | Both pass |