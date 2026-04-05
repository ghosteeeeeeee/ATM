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

## Key Time Windows

| Signal state | Stale threshold | Action |
|-------------|-----------------|--------|
| PENDING/APPROVED/WAIT | > 3 hours | Mark EXPIRED |
| SKIPPED/EXPIRED | > 24 hours | DELETE (with --archive) |
| EXECUTED | never deleted | Keep for A/B analysis |

## Hot-Set Entry Filters (2026-04-05)

Tokens must pass **both** to enter `hotset.json`:

| Filter | Threshold | Reason |
|--------|-----------|--------|
| Confidence | ≥ 70% | Low-confidence signals (< 70%) have poor WR |
| Momentum (speed) | > 0% | `momentum_score = 0%` means stalled/dead — skip |