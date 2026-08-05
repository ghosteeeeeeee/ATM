# Merge Corruption Fix — z=None in Trade Records (2026-05-21)

## What Happened

19 closed trades on 2026-05-20/21: 12 losses, 7 winners. All showed `z=None` in PostgreSQL `signal_z_score` column despite `zscore-pump` appearing in their `sources` field.

**Root cause (two-layer):**

### Layer 1 — signal_schema.py merge UPDATE destroys valid z_score

When `add_signal()` finds an existing row (within 5 min) and merges, the UPDATE statement unconditionally writes every indicator field from the NEW signal's parameters:

```python
# BUGGY — R&S passes z_score=None, wipe valid z from zscore-pump:
UPDATE signals SET
    z_score=?,
    ...
WHERE id=?
```

`rs.py` calls `add_signal(token, direction, signal_type='rs-r<NN>', source=sig['source'], confidence)` — no `z_score`, no `rsi_14`, no `macd_*`. Python defaults to `None`. The UPDATE writes `None` into every indicator field, destroying whatever `zscore_pump` had written.

Signal firing order determines outcome:
- R&S fires AFTER zscore-pump → z=None (wiped)
- R&S fires BEFORE zscore-pump → z=valid (preserved by timing luck)

### Layer 2 — _live_zscore() in signal_compactor grabs newest row

At line 1662:
```python
ORDER BY created_at DESC LIMIT 1
```

Returns the MOST RECENT signal row. If the most recent is R&S-only (no z), returns None even if an earlier row had valid z. COALESCE in layer 1 fixes this.

## The Fixes (all implemented 2026-05-21)

### Fix 1 — COALESCE in merge UPDATE (signal_schema.py lines 697-714)

```python
# Preserve existing value when new signal passes None:
z_score=COALESCE(?, z_score),
z_score_tier=COALESCE(?, z_score_tier),
rsi_14=COALESCE(?, rsi_14),
macd_value=COALESCE(?, macd_value),
macd_signal=COALESCE(?, macd_signal),
macd_hist=COALESCE(?, macd_hist),
```

When R&S calls with `z_score=None`: COALESCE(None, existing_z) → existing_z (preserved).
When zscore_pump calls with real `z_score=2.621`: COALESCE(2.621, existing_z) → 2.621 (replaces).

### Fix 2 — signal_z_score written to trade records (hl-sync-guardian.py)

`add_orphan_trade()` gained `signal_z_score: float = None` param. Both orphan paths (Path A UPDATE, Path B INSERT) now write `signal_z_score` to PostgreSQL trades table. Column already existed (col 78/99).

### Fix 3 — RS touch count gate in decider_run (decider_run.py lines ~1050-1069)

Parse touch count from `sig_src` (format: `rs-s<N>` or `rs-r<N>`), apply threshold:
- Base threshold: `RS_DECIDER_MIN_TOUCHES = 100`
- Z-score bonus: if `|z| >= 2.5`, threshold drops to `RS_DECIDER_ZBONUS_TOUCHES = 50`
- Confidence penalty: `-15` if touches < threshold
- Block if effective `sig_conf < RS_DECIDER_CONF_FLOOR = 55`

Constants added to `hermes_constants.py` (no hardcoding).

## All Files Modified

| File | Change | Status |
|------|--------|--------|
| `signal_schema.py` | COALESCE in merge UPDATE | ✅ Compiles clean |
| `decider_run.py` | ZSCORE-GATE + TOUCH-GATE | ✅ Compiles clean |
| `hermes_constants.py` | 5 new RS_DECIDER constants | ✅ Compiles clean |
| `hl-sync-guardian.py` | signal_z_score param + INSERT col | ✅ Compiles clean |

## New Constants (hermes_constants.py)

```python
RS_DECIDER_MIN_TOUCHES = 100       # base touch threshold for RS entries
RS_DECIDER_ZBONUS_TOUCHES = 50     # relaxed threshold when |z| >= 2.5
RS_DECIDER_ZBONUS_ZSCORE = 2.5    # z-score bonus activation threshold
RS_DECIDER_CONF_PENALTY = 15       # confidence deduction when touches < threshold
RS_DECIDER_CONF_FLOOR = 55        # block threshold after penalty
```

## Prevention — Any Signal That Calls add_signal() Without Indicator Params

Any signal that omits `z_score`, `rsi_14`, `macd_*` params is a potential wipe agent. The COALESCE fix protects all of them simultaneously. Check for future vulnerabilities:

```bash
grep -n "add_signal(" /root/.hermes/scripts/signals/*.py | grep -v "z_score\|rsi_14\|macd"
```

## Key Lesson

**The merge UPDATE in `add_signal()` is destructive when the caller passes `None` for indicator fields.** Every signal that calls `add_signal()` without carrying all indicator fields (z_score, rsi_14, macd_*) will corrupt prior indicator values on merge unless COALESCE is used. The fix is in the SQL layer — not in call sites. Never rely on timing luck for data integrity.