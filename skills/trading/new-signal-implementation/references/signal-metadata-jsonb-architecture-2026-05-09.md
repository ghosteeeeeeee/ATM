# Signal Metadata JSONB Architecture
**Date:** 2026-05-09
**Purpose:** Eliminate per-column sprawl when adding new signals to Hermes

## Problem
Adding N new signals required N new PostgreSQL columns, N SQLite columns, and edits to brain.py INSERT, decider_run execute_trade, signal_compactor hotset entry, and archive-trades.py — every time.

## Solution: Two-Tier Signal Value Storage

### Tier 1 — Source string (no column needed)
Signal type identifier encoded in `source` field. Works for basic signals that don't need per-signal analytics.

### Tier 2 — JSONB catch-all (new)
Two new columns carry all signal metadata as a dict:

```
_signal_metadata JSONB  -- signal indicator values (RSI, MACD, z_score, etc.)
_exp_metadata     JSONB  -- experiment variant metadata
```

New signals add key-value pairs to the dict. Zero schema changes ever again.

## Pipeline Flow

```
Signal script
  ↓ add_signal(signal_metadata={...})
signals_hermes_runtime.db  (signal_metadata TEXT column)
  ↓ signal_compactor reads MAX(signal_metadata)
hotset entry  (signal_metadata field in JSON)
  ↓ decider_run passes --signal-metadata-json
brain.py add_trade(signal_metadata=dict)
  ↓ PostgreSQL _signal_metadata JSONB column
```

## Files Modified (2026-05-09)

| File | Change |
|------|--------|
| `brain.py` | `add_trade()` gains `signal_metadata: dict`, `exp_metadata: dict` params; `json.dumps()` to JSONB; argparse `--signal-metadata-json`, `--exp-metadata-json` |
| `decider_run.py` | `execute_trade()` gains `signal_metadata=None`; serializes and passes `--signal-metadata-json` to brain.py |
| `signal_compactor.py` | SQL query adds `MAX(signal_metadata) AS signal_metadata` (index 11); hotset entry passes through |
| `archive-trades.py` | Adds `_signal_metadata TEXT`, `_exp_metadata TEXT` to schema; both branches handle JSON columns |
| SQLite signals DB | Adds `signal_metadata TEXT` column |
| PostgreSQL trades table | Adds `_signal_metadata JSONB`, `_exp_metadata JSONB` columns |

## Critical Invariant

**brain.py INSERT must stay balanced: N columns = N expressions**

- 41 columns (pre-migration): 41 expressions — ✅ verified at d31692f
- 43 columns (post-migration): 42 `%s` placeholders + 1 `NOW()` = 43 expressions — ✅ balanced

`NOW()` is an expression, not a placeholder. Every column add must maintain this balance.

## Adding a New Signal

1. In the signal script: `add_signal(..., signal_metadata={'new_signal': value})`
2. signal_compactor reads it via `MAX(signal_metadata)` in GROUP BY
3. Hotset entry gets `'signal_metadata': row[11]`
4. decider_run passes `sig.get('signal_metadata')` as `--signal-metadata-json`
5. brain.py writes `json.dumps(signal_metadata)` to `_signal_metadata` JSONB column
6. Analysis: `WHERE _signal_metadata LIKE '%new_signal%'`

No per-column additions anywhere.

## Lessons Learned

### Unit Mismatch Is the Most Common Bug Type
A function returns a value in one unit (e.g., `%`), a threshold constant is defined in another unit (e.g., decimal fraction) in `hermes_constants.py`. The comparison silently passes when it shouldn't.

**Pattern that bit us (2026-05-09):**
- `breakout_strength` from `_classify_structure()` = `%` (e.g., `0.014 = 0.014%`)
- `HH_HL_BREAKOUT_THRESHOLD = 0.0005` = decimal fraction (`= 0.05%`)
- `0.014 >= 0.0005` always True — phantom breakouts

**Rule:** Before comparing any threshold constant against a computed value: (1) find where the computed value is created and check its unit, (2) find where the threshold is defined and check its unit, (3) normalize before comparing. Variable names are NOT reliable unit indicators.

### ATR-Normalized Thresholds Vary Wildly by Token
`_BOUNCE_THRESH_ATR=0.20` seemed reasonable for BTC (ATR ~0.5% → threshold 0.10% of price).
For ADA (ATR=0.024%), the same multiplier gave `0.0048%` of price — noise-level.
The fallback path (`price * 0.0015`) was 31x wider — making the ATR path unreachable.

**Rule:** Compute absolute threshold value in price units for a representative low-ATR token before setting an ATR multiplier. A threshold that seems reasonable for BTC becomes unreachable for low-ATR tokens.