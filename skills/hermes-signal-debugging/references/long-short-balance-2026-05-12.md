# LONG/SHORT Balance Fixes — 2026-05-12

## Problem: System Biased Toward LONG

Hot-set was dominated by LONG entries (83% base confidence from accel-300+) while SHORT signals competed with base 55-65%. LONG entries consistently outscored SHORT in hot-set rankings.

## Fix 1: Lowered accel-300+ Confidence Cap

**File:** `signals/accel_300.py` line 390

**Before:**
```python
confidence = int(min(80, 65 + max(0, (sig['gap_pct'] - MIN_GAP_PCT) * 80) + gap_bonus))
```

**After:**
```python
confidence = int(min(70, 65 + max(0, (sig['gap_pct'] - MIN_GAP_PCT) * 80) + gap_bonus))
# Comment updated: MIN_GAP_PCT=0.10 → base 65, larger gap → up to 70 (cap lowered 2026-05-12 to reduce LONG bias)
```

**Effect:** accel-300+ now emits 60-70 (was 60-80). SHORT signals (ema9-sma20-: 62-68, hh_hl_breakout SHORT: 65) now competitive with LONG.

## Fix 2: trend_purity Required for ALL Trades (Both LONG and SHORT)

**File:** `signal_compactor.py` — two locations updated

**Location 1 — run_compaction hot-set final filter (~line 856):**
```python
# ── Trend purity required for ALL entries (2026-05-12) ───────────────────
if direction == 'LONG':
    source_parts = [p.strip() for p in (src or '').split(',') if p.strip()]
    has_trend_purity_pos = 'trend_purity+' in source_parts
    has_tl_break_long = 'tl_break_long' in source_parts
    if not has_trend_purity_pos and not has_tl_break_long:
        log(f"  🚫 [HOTSET-FILTER] {tkn}: LONG blocked — requires trend_purity+ or tl_break_long (has: {src})")
        continue
else:  # SHORT
    source_parts = [p.strip() for p in (src or '').split(',') if p.strip()]
    has_trend_purity_neg = 'trend_purity-' in source_parts
    if not has_trend_purity_neg:
        log(f"  🚫 [HOTSET-FILTER] {tkn}: SHORT blocked — requires trend_purity- (has: {src})")
        continue
```

**Location 2 — _filter_safe_prev_hotset (~line 1304):**
Same pattern applied to preserved entries from previous hot-set.

**Effect:** Replaced the previous LONG-only `accel-300+` requirement. Both LONG and SHORT now require trend_purity anchor. `tl_break_long` remains exempt (its own breakout signal).

**Consequence:** Many existing hot-set entries (STBL, GALA, TAO, DASH, SNX with only ma-death/hh_hl/ema9-sma20 sources) will be blocked next compaction — none have trend_purity.

## Fix 3: HH_HL Breakout SHORT Fires at Bounce Point

**Problem:** `hh_hl_breakout SHORT` fires 99% at the bounce point near the LL (resistance), not on confirmed breakdown. The signal fires when price approaches the swing low from above, catches the bounce, and reverses against us.

**Root cause:** `HH_HL_BREAKOUT_THRESHOLD = 0.05%` is too loose — accepts weak breakdown attempts that immediately bounce. The signal fires on the approach to the LL, not on decisive breakdown confirmation.

**Pattern observed:** STBL SHORT with `hh_hl_breakout hhh-short4,hhh-short5`, GALA SHORT same, TAO SHORT same, DASH SHORT same, SNX SHORT same — all firing at same time at bounce point.

**Proposed fix (not yet implemented — pending T decision):**
Add range-position filter in `signals/hh_hl.py` `detect_hh_hl_breakout()`:
```python
# SHORT: only fire when price is in bottom third of recent range
recent_high = max(c['high'] for c in candles[-20:])
atr = _compute_atr(candles)
if price > recent_high - atr:  # price too close to range top — bounce territory
    return None
```

Alternatively: raise `HH_HL_BREAKOUT_THRESHOLD` from 0.05% to 0.10-0.15% to require more conviction.

**Note:** trend_purity- requires 1% crash below EMA to fire — too strict for bounce-at-LL scenarios. The range-position filter is the correct approach for hh_hl SHORT specifically.

## Why SHORT Confidence Appears Lower (Structural)

The dominant SHORT signals emit structurally lower base confidence:
- `ema9-sma20-`: 55-68 base (gap formula doesn't reward moderate gaps)
- `hh_hl_breakout` SHORT: flat 65
- `ma_cross` death cross: 55-65

LONG dominated by `accel-300+`: 60-80 (now 60-70 after cap lowering).

The score formula is symmetric — no direction multiplier bias. The gap is entirely in raw emitted confidence per signal type.