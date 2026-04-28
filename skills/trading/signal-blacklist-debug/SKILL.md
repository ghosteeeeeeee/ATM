---
name: signal-blacklist-debug
description: Debug Hermes signal pipeline when signals are silently blocked by SIGNAL_SOURCE_BLACKLIST or fail to reach the hot-set
category: trading
tags: [hermes, signals, blacklist, debugging]
---

# Signal Blacklist Debug Skill

## When to Use
When signals are generated but don't appear in the hot-set, or when only some signal types are visible while others are silently blocked.

## The Core Mechanism

`SIGNAL_SOURCE_BLACKLIST` in `hermes_constants.py` blocks signals at the `add_signal()` level in `signal_schema.py`. There are TWO separate checks:

```python
# Exact match check (signal_schema.py line ~397)
if source in SIGNAL_SOURCE_BLACKLIST:
    return None  # blocked

# Component-level check for comma-separated merged sources (line ~402)
for component in source.split(','):
    if component in SIGNAL_SOURCE_BLACKLIST:
        return None  # blocked — even if one component is blocklisted
```

**Critical: exact match blocks the full string. Component check blocks any merged signal containing a blocklisted component.**

## Key Naming Convention
The system uses directional suffixes:
- `hzscore+` / `hzscore-` — z-score long/short
- `vel-hermes+` / `vel-hermes-` — velocity long/short
- `pct-hermes+` / `pct-hermes-` — percentile long/short
- `hmacd+` / `hmacd-` — MTF MACD long/short
- `fast-momentum+` / `fast-momentum-` — fast momentum long/short

**Bare names** (`hzscore`, `vel-hermes`, `pct-hermes`) are **blocklisted**. **Suffixed names** (`hzscore+`, `vel-hermes-`) are **allowed**.

This means: if code generates `source='vel-hermes'` (bare) but the blacklist only has `'vel-hermes'` (bare), it gets blocked. If the code generates `source='vel-hermes+'` (suffixed), the exact match `'vel-hermes'` does NOT match `'vel-hermes+'`, so it passes.

## Debug Steps

1. **Query the DB** — see what sources are actually in the signals table:
```bash
sqlite3 data/signals_hermes_runtime.db "SELECT source, decision, COUNT(*) FROM signals WHERE created_at > datetime('now', '-24 hours') GROUP BY source, decision ORDER BY decision, COUNT(*) DESC;"
```

2. **Check the blacklist** — exact entries:
```bash
cd /root/.hermes/scripts && python3 -c "from hermes_constants import SIGNAL_SOURCE_BLACKLIST; print(SIGNAL_SOURCE_BLACKLIST)"
```

3. **Trace `add_signal()`** — the function returns `None` silently when blocked. Add debug prints at the return points in `signal_schema.py` lines 392, 394, 398, 404.

4. **Understand merge behavior** — multiple `add_signal()` calls for the same `token+direction` are **merged** into one row with comma-separated sources. Components are unioned, not replaced. So if Signal A has `source='hzscore+,mtf-momentum'` and Signal B has `source='rsi'`, the merge produces `source='hzscore+,mtf-momentum,rsi'`.

5. **Cascading effect** — adding `'rsi'` to the blacklist blocks ALL merged signals containing `rsi` as a component, including good signals like `mtf-momentum,rsi` (historically 28 EXECUTED, 3 APPROVED). Always check the full impact before adding component-level blocks.

## Signal Types and Their Sources
- `pattern_scanner` — source: `pattern_scanner` (always single-source, not mergeable)
- `fast_momentum` — source: `fast-momentum+` or `fast-momentum-` (directional)
- `momentum` — source: built from `compute_score()`, typically `momentum` or `mtf-{sources}` (merged)
- `mtf_zscore` — source: `hzscore+` or `hzscore-` (from `_run_mtf_macd_signals()`)
- `mtf_macd` — source: `hmacd+` or `hmacd-` (from `_run_mtf_macd_signals()`)
- `percentile_rank` — source: `pct-hermes+` or `pct-hermes-` (from `_run_mtf_macd_signals()`)
- `velocity` — source: `vel-hermes+` or `vel-hermes-` (from `_run_mtf_macd_signals()`)

## Approval Flow
After `add_signal()` writes to DB, signals flow through:
1. **signal_compactor.py** — filters to top 20 by confidence, applies SOURCE_BLACKLIST component check, sets APPROVED/REJECTED
2. **ai_decider.py** (defunct but still runs) — can override APPROVED signals
3. **Stale cleanup** — APPROVED signals older than 30 min expire

Single-source signals must have 2+ components in their `source` field to pass the compactor's confluence check. They stay PENDING until a second source fires for the same token+direction.

## Common Failure Patterns
- Code generates `source='vel-hermes'` (bare) but blacklist has `'vel-hermes'` — blocked. Fix: use `f'vel-hermes{vel_dir_char}'`
- `rsi` added to blacklist blocks ALL signals containing `rsi` as component — cascading destruction of good signals
- Merge artifacts like `hzscore+,hzscore-` (both directions in same source) — blocked as contradictory
- `hmacd+-` / `hmacd-+` — blocked as MTF disagreement merge artifacts
