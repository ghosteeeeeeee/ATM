# zscore=None in Combo Signals — Guardian Doesn't Filter (2026-05-21)

## Context

19 trades analyzed from 2026-05-20 evening / 2026-05-21 morning session. Systematically losing on `rs-rXXX,zscore-pump-` and `rs-sXXX,zscore-pump+` combo signals while winning on pure `rs-rXXX` signals or standalone `zscore-pump-` signals with valid z.

## Symptom

All combo signals (source like `rs-r3071,zscore-pump-`) show `z_score=NULL` in the signals table — even though the zscore-pump component did compute a real z value when it fired.

Guardian sees `z=None` and has **no z-score gate** — it cannot distinguish between:
1. zscore-pump fired but its z got merged-over to NULL (signal IS corrupted)
2. zscore-pump never fired at all and the combo is pure RS (signal is just RS)

Result: Guardian treats corrupted combo signals the same as clean RS signals, reducing effective quality filtering.

## Root Cause Chain

### Step 1 — zscore-pump fires, writes valid z
`zscore_pump.scan_zscore_pump_signals()` → `detect_zscore_pump()` → `add_signal(source='zscore-pump-', z_score=-2.467)` → INSERT with z=-2.467 in signals table.

### Step 2 — RS fires within ~5 min, merges
`rs_signals.scan_rs_signals()` → `add_signal(source='rs-r3071,zscore-pump-', z_score=None)` → finds existing row, MERGEs.

### Step 3 — Merge UPDATE overwrites z with NULL
`signal_schema.py` `add_signal()` merge UPDATE at ~line 706:
```python
c.execute('''UPDATE signals SET ... z_score=?, ... WHERE id=?''', (z_score, z_score_tier, ...))
```
Caller (RS signal) passes `z_score=None` → overwrites the valid -2.467 with NULL.

### Step 4 — Guardian reads stale z=None
`signal_compactor._enrich_and_write_signals()` → `signals.json` gets `zscore: null` from `_live_zscore()`. Guardian sees null and cannot apply any z-quality filter.

### Step 5 — Trade enters on false confluence
The combo `rs-r3071,zscore-pump-` looks like RS + momentum confirmation. In reality momentum signal contributed nothing — it was silently overwritten.

## Key Data Points

| Pattern | z_valid | Count |
|---------|---------|-------|
| Standalone `zscore-pump-` (source='zscore-pump±') | 84% | 77 signals |
| Combo with comma (e.g. `rs-rXXX,zscore-pump-`) | 30% | 23 signals |
| Pure `rs-rXXX` (no zscore) | N/A | many |

**Win/Loss by source type:**
- Pure rs with 300+ touches: WIN (AAVE, ADA, ANIME at 22:23)
- `rs-rXXX,zscore-pump-` with z=None: ALL LOSSES (ANIME 00:45, XLM, UMA, ENS, BSV, 0G)
- Same combo with valid z: mixed (UMA had z=-2.337 but still lost due to tiny level)

## Guardian Gap — No z-None Filter

The guardian (`hl-sync-guardian.py`) processes trades with `signal_z_score=None` in the DB even when source contains `zscore-pump`. There is no check:

```python
# Missing logic:
if 'zscore-pump' in signal_source and signal_z_score is None:
    # This signal claimed zscore-pump but has no z → reject or tighten SL
    apply_tighter_stop_loss()
    # OR: reject entirely until fix is applied
```

## Related Prior Bug

Previous incident (2026-05-17, same reference file) identified the same root cause — `add_signal()` merge UPDATE overwrites z_score with NULL when RS fires after zscore-pump.

The fix suggested was:
```python
# In add_signal() merge UPDATE — COALESCE to preserve existing:
z_score=COALESCE(?, z_score)
```

But this was never applied, OR it was applied incompletely (the RS→zscore merge path was fixed but not the zscore-pump→combo path).

## Fix Priority

1. **Guardian-level z-filter** (highest impact): if signal source contains `zscore-pump` but `z_score IS NULL`, either reject the trade or apply max-tight SL (-1.5%) and 0.5x size. This prevents the corrupted combo from behaving like a confirmed signal.

2. **Fix the merge UPDATE** in `signal_schema.py`: ensure `COALESCE(z_score, z_score)` semantics so incoming NULL doesn't overwrite existing value.

3. **Write `signal_z_score` to trade record at entry**: guardian should capture z_score at entry so post-trade analysis has ground truth. Currently it writes NULL to trade records even when source includes zscore-pump.

## DB Access

```python
# Quick check for z=None in combo signals (last 24h)
import sqlite3
conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
cur = conn.cursor()
cur.execute("""
    SELECT token, source, z_score, created_at
    FROM signals
    WHERE source LIKE '%,zscore-pump%'
      AND created_at >= datetime('now', '-24 hours')
    ORDER BY created_at DESC
""")
rows = cur.fetchall()
for r in rows:
    print(f"{r[0]:10} z={r[2]} src={r[1][:50]}")
conn.close()
```

## Trade-Level DB Schema (brain.trades)

| Column | Type | Note |
|--------|------|------|
| signal | TEXT | comma-separated source list e.g. `rs-r3071,zscore-pump-` |
| signal_z_score | REAL | **NOT written** — always NULL even with zscore-pump in signal |
| signal_z_score_tier | TEXT | always NULL |
| signal_momentum_state | TEXT | always NULL |
| regime | TEXT | always NULL for recent trades |

This means post-trade analysis cannot filter on z-score quality — the feedback loop is broken.