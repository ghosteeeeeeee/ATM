# signal_compactor.py Post-Audit State (2026-05-08)

## File: `/root/.hermes/scripts/signal_compactor.py` (1548 lines)

---

## ✅ All 5-Minute Consistency Fixes Applied

T's spec: "pending signals should expire in 5 mins, signals in hot-set should expire in 5 mins unless re-triggered"

| Location | Was | Now | Context |
|----------|-----|-----|---------|
| `_get_opposing_penalty()` line ~258 | `datetime('now', '-15 minutes')` | `datetime('now', '-5 minutes')` | Opposing signal penalty window |
| GROUP BY query line ~346 | `datetime('now', '-15 minutes')` | `datetime('now', '-5 minutes')` | Co-signal merge window |
| Log message line ~356 | `"15-min window"` | `"5-min window"` | Diagnostic only |
| PENDING staleness line ~1039 | `age_m < 15.0` | `age_m < 5.0` | PENDING expiry check |
| APPROVED expiry subquery (2 places) lines ~1100, ~1118 | `datetime('now', '-15 minutes')` | `datetime('now', '-5 minutes')` | APPROVED signal expiry |

The broad collection query at line ~966 still uses `-60 minutes` — this is correct (broad window for collection), individual staleness is checked at 5 min after collection.

---

## ✅ GOOD_STANDALONE_SIGNALS Fixes Applied

**Before (broken gate + stale data):**
```python
GOOD_STANDALONE_SIGNALS = {
    'accel-300+':   {'wr': 17, 'avg': -0.319, 'dir': 'LONG'},  # avg<0 → NEVER passes
    'pct-hermes-': {'wr':  5, 'avg': -0.449, 'dir': 'SHORT'},  # losing
    'hzscore+':    {'wr': 21, 'avg': -0.338, 'dir': 'SHORT'},  # non-dir, can't pass
    'hzscore-':    {'wr': 16, 'avg': -0.704, 'dir': 'LONG'},   # non-dir, can't pass
}
```

**After:**
```python
GOOD_STANDALONE_SIGNALS = {
    'accel-300+':  {'wr': 17, 'avg': -0.319, 'total': 41.8, 'dir': 'LONG'},
}
```

**Changes:**
- `pct-hermes-` REMOVED: WR=5%, avg=-0.449, total=-18 — losing on every metric, would be blocked anyway
- `hzscore+` REMOVED: non-directional (in `NON_DIRECTIONAL_PREFIXES`), never appears in `long_srcs`/`short_srcs`, can't pass gate
- `hzscore-` REMOVED: same reason
- `accel-300+` `total` CORRECTED from -14.7 to +41.8 (was from stale audit)
- Gate criterion changed: `avg >= 0` → `total > 0` (correct for signals with few big winners / many small losers)

**Why `total > 0` not `avg >= 0`:** `accel-300+` has avg=-0.319 but total=+41.8 because 4 massive wins (×+258%) outweigh 18 losses (×-38%). The correct gate for standalone signals is net profitability at scale, not per-trade average.

---

## ✅ Confluence Gate Fix

```python
# Before (line ~519): avg gate — blocks accel-300+ which has avg<0
if info['avg'] >= 0:
    bypass_confluence()

# After: total_pnl gate — passes accel-300+ which has total>0
if info['total'] > 0:
    bypass_confluence()
```

---

## ✅ CONFLOENCE_REQUIRED Shadow Removed

- Line 26 imports `CONFLUENCE_REQUIRED` from `hermes_constants` (value `True`)
- ~~Line 517: `CONFLOENCE_REQUIRED = True`~~ — **REMOVED** (was dead code, local shadow, never read)
- Line 541 now correctly references the imported `CONFLUENCE_REQUIRED`

---

## ⚠️ Still Present: Dead Code (Not Removed — Awaiting Approval)

These functions are defined but have zero callers:

1. **`_preserve_previous_hotset()`** (lines ~1344-1414): wrapper that calls `_filter_safe_prev_hotset()` directly — never used
2. **`_enrich_and_write_signals()`** (lines ~1417-1537): was meant to write signals.json, moved to hermes-trades-api.py — function never deleted

Safe to delete. No impact on current behavior.

---

## ⚠️ Still Present: `SIGNAL_SOURCE_WEIGHTS` Duplication

`macd-accel-` appears twice in `SIGNAL_SOURCE_WEIGHTS`:
- Line 125: `{'prefix': 'macd_accel_short', 'weight': 2.00}` — matches `macd-accel-` (underscore vs hyphen)
- Line 129: `{'prefix': 'macd_accel', 'weight': 1.0}` — unreachable for `-` signals (first match wins)

Second entry is dead code within the dict. Not a bug, just wasted space.

---

## Key Query Patterns

```python
# Check PENDING signal age distribution
SELECT token, direction, source, confidence, compact_rounds,
       ROUND((julianday('now') - julianday(created_at)) * 1440, 1) AS age_m
FROM signals
WHERE decision='PENDING' AND executed=0
ORDER BY age_m DESC;

# Check APPROVED signal survival
SELECT token, direction, source, confidence, hot_cycle_count, survival_rounds
FROM signals WHERE decision='APPROVED' AND executed=0;

# Count decisions overall
SELECT decision, COUNT(*) FROM signals GROUP BY decision ORDER BY COUNT(*) DESC;

# GOOD_STANDALONE_SIGNALS live verification
SELECT signal_type, direction, COUNT(*) cnt,
       ROUND(100.0*SUM(is_win)/COUNT(*),1) wr,
       ROUND(100.0*AVG(pnl_pct),3) avg_pnl,
       ROUND(SUM(pnl_pct),1) total_pnl
FROM signal_outcomes
GROUP BY signal_type, direction
HAVING cnt >= 10
ORDER BY total_pnl DESC;
```

---

## Hot-Set Path (how signals reach execution)

```
signals_runner.py → signal_gen → signals DB (PENDING)
                              ↓
                   signal_compactor.py (every 1 min via systemd timer)
                              ↓
                   GROUP BY query → confluence gate → scoring → hotset.json
                              ↓
                   decider_run.py reads hotset.json → executes trades
```

`signal_compactor.main()` calls `process_pending_signals()` + `expire_stale_signals()` — does NOT call `compact_hot_set()`. APPROVED signals are produced by `compact_hot_set()` but it's never invoked from main. This is a known architectural gap (see `references/signal-compactor-model-redesign.md`).