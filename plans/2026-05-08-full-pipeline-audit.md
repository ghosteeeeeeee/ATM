# HERMES TRADING SYSTEM — FULL PIPELINE AUDIT
**Date:** 2026-05-08
**Scope:** signals/ → signal_runner → signal_compactor → decider_run → guardian/position_manager
**Status:** BUGS IDENTIFIED — FIXES PENDING

---

## PRIORITY SUMMARY

| P# | File | Line | Severity | Issue | Status |
|----|------|------|----------|-------|--------|
| 1 | signals/ema20_50.py | 60-61,338 | **P0** | Source `+`/`-` inverted for LONG/SHORT | PENDING |
| 2 | signals/guppy.py | 144,146,350 | **P0** | `MIN_GROUP_SLOPE`, `SLOW_TREND_LOOKBACK` undefined | PENDING |
| 3 | hl-sync-guardian.py | 2683 | **P0** | `_record_trade_outcome` never called — signal_outcomes DB dead | PENDING |
| 4 | hermes_constants.py | 248-251 | P1 | ATR_SL_MAX=1% (spec=2%), ATR_TP_MIN=1.5% (spec=0.75%) | PENDING |
| 5 | signals/guppy.py | full | P1 | No hot-set gate — runs full universe | PENDING |
| 6 | signals/macd_accel.py | 273+ | P1 | Uses stale `candles.db` instead of `price_history` | PENDING |
| 7 | signal_gen.py | 935 | P1 | `detect_phase()` called twice for SHORT (copy-paste dup) | PENDING |
| 8 | signal_gen.py | 2043-2045 | P1 | `_fast_zscore` silent None on insufficient data | PENDING |
| 9 | position_manager.py | 2481-2499 | P1 | `trailing_active` always False — dead skip code | PENDING |
| 10 | signals/r2_trend.py | 195 | P2 | Hardcoded `120` instead of `CANDLES_STALENESS_SEC` | PENDING |
| 11 | signals/hh_hl.py | 229+ | P2 | ATR not validated against MIN/MAX bounds | PENDING |
| 12 | signals/hzscore.py | 118 | P3 | Source `+`/`-` convention inverted vs other signals | PENDING |
| 13 | signals/vel_hermes.py | 138,147 | P3 | Same `+`/`-` inversion | PENDING |
| 14 | signals/counter_flip.py | 272 | P3 | Source from sub-detector not direction-based | PENDING |
| 15 | signals/r2_rev_5m.py | 36 | P3 | Imports non-existent `paths` module | PENDING |
| 16 | signal_compactor.py | 239-279 | Prior | Opposing penalty counts parts not signal rows | PENDING |
| 17 | signal_compactor.py | 465-466 | Prior | Column index fragility `row[8]`, `row[10]` | PENDING |
| — | hermes_constants.py | 87-101 | — | `SIGNAL_SOURCE_BLACKLIST = {}` | ✅ VERIFIED — kill-switch system active, no action needed |
| — | pattern_scanner | — | — | No kill-switch flag | ✅ VERIFIED — not in active pipeline |

---

## CONFIRMED WORKING ✅
- Guardian k_tp formula (k × 1.25 × atr_pct)
- Guardian breach handling (loss cooldown, DB columns `exit_price`/`hype_realized_pnl_usdt`, FileLock on hotset read)
- Guardian DRY mode default `--apply` flag
- Position manager stale timeouts (losers=15min, winners=30min — NOT swapped ✅)
- Position manager net_pnl for win/loss classification
- ATR_TP_K_MULT = 1.25 consistently applied across guardian + position_manager
- Orphan detection in guardian
- All 27 signal scripts compile clean (no syntax errors)

---

## BUG DETAIL

### P0-1 — KILLSWITCH REPLACEMENT (Verified 2026-05-08) ✅
**Finding:** `SIGNAL_SOURCE_BLACKLIST` is empty `{}` — this is **correct**. The blacklist was replaced by per-source `*_ENABLED` kill-switch flags checked in `signal_schema.py add_signal()` Layer 2.

**Active killswitches (18 disabled, 25 enabled):**
```
DISABLED: PCT_HERMES_ENABLED, VEL_HERMES_ENABLED, VEL_HERMES_PLUS_ENABLED,
HZSCORE_ENABLED, MOMENTUM_ENABLED, MOMENTUM_PLUS_ENABLED, MOMENTUM_MINUS_ENABLED,
MTF_MOMENTUM_ENABLED, MTF_MOMENTUM_PLUS_ENABLED, MTF_MOMENTUM_MINUS_ENABLED,
PHASE_ACCEL_ENABLED, FAST_MOMENTUM_ENABLED, FAST_MOMENTUM_MINUS_ENABLED,
GAP_300_ENABLED, MA_CROSS_PLUS_ENABLED, MA_CROSS_5M_PLUS_ENABLED,
R2_REV_ENABLED, HMACD_ENABLED
```

**Missing kill-switch:** `pattern_scanner` has NO `PATTERN_SCANNER_ENABLED` flag anywhere. However, `pattern_scanner` is NOT in `signals/__init__.py` registry, NOT called by `signals_runner.py`, and `signal_gen.py` is removed from pipeline. `pattern_scanner` is **not in the active pipeline** — P1-12 is non-issue. If it is ever re-added, a kill-switch must be created.

**Status:** ✅ Kill-switch system is active and working. No action needed on P0-1.

---

### P0-1 — ema20_50 SOURCE TAG INVERTED
**File:** `signals/ema20_50.py` lines 60-61, 338
**Current:**
```python
SOURCE_LONG  = 'em2050-'
SOURCE_SHORT = 'em2050+'
...
source = SOURCE_SHORT if direction == 'LONG' else SOURCE_LONG  # line 338
```
**Impact:** LONG signals write `source='em2050-'` and SHORT write `source='em2050+'`. Hot-set scoring treats these as separate sources with independent weights — opposite of intent.
**Fix:**
```python
SOURCE_LONG  = 'em2050+'
SOURCE_SHORT = 'em2050-'
# source = SOURCE_LONG if direction == 'LONG' else SOURCE_SHORT
```

---

### P0-3 — guppy UNDEFINED CONSTANTS
**File:** `signals/guppy.py` lines 144, 146, 350
**Current:** `MIN_GROUP_SLOPE` and `SLOW_TREND_LOOKBACK` used but never defined.
**Impact:** `NameError` if `detect_guppy_signal()` is called.
**Fix:** Add at top of guppy.py:
```python
MIN_GROUP_SLOPE     = 0.0001   # per-bar slope threshold
SLOW_TREND_LOOKBACK = 10       # bars for slow group trend lookback
```

---

### P0-4 — _record_trade_outcome NEVER CALLED
**File:** `hl-sync-guardian.py` line 2683 (definition) — zero call sites confirmed.
**Impact:** `signal_outcomes` SQLite DB never written by guardian. All guardian-initiated closes (orphan, breach, cut-loser, blocklist sweep, stale rotation) skip outcome recording. Self-correction on losses is dead.
**Fix:** Add calls after every `conn.commit()` in all close paths:
- `_close_paper_trade_db` — after `conn.commit()`
- `_close_orphan_paper_trade_by_id` — after `conn.commit()`
- Breach handler (normal) — after `conn.commit()`
- Breach handler (self-close) — after `conn_sc.commit()`
- Cut-loser success path — after `conn_cut.commit()`
- `_sweep_blocklist_trades` — after each `_close_paper_trade_db` call

---

### P1-5 — guppy NO HOT-SET GATE
**File:** `signals/guppy.py`
Runs on all tokens in `prices_dict.keys()` (full universe 150 tokens). No hot-set restriction.
**Fix:** Add hot-set enforcement matching other signals' pattern.

---

### P1-6 — macd_accel USES STALE candles.db
**File:** `signals/macd_accel.py` lines 273+
**Current:** Reads from `candles.db/candles_1m` with no freshness guard.
**Fix:** Switch to `price_history` table with `MAX(timestamp)` freshness check.

---

### P1-7 — ATR SL/TP CAPS DON'T MATCH SPEC
**File:** `hermes_constants.py` lines 248-251
**Current:**
```python
ATR_SL_MAX = 0.010   # 1.0% (spec: 2.0%)
ATR_TP_MIN = 0.015   # 1.5% (spec: 0.75%)
```
**Fix:**
```python
ATR_SL_MAX = 0.020   # 2.0% cap
ATR_TP_MIN = 0.0075  # 0.75% floor
```

---

### P1-8 — detect_phase DUPLICATE CALL
**File:** `signal_gen.py` line 935
**Current:** `phase = detect_phase(...)` appears twice consecutively.
**Fix:** Remove the duplicate line.

---

### P1-9 — _fast_zscore SILENT FAILURE
**File:** `signal_gen.py` lines 2043-2045
**Issue:** For `len==1`, `std=1` fallback prevents `std==0` check from catching it. `stdev` raises `StatisticsError` silently.
**Fix:**
```python
if len(prices_subset) < 3:
    return None
std = statistics.stdev(prices_subset)
if std == 0:
    return None
```

---

### P1-10 — trailing_active DEAD CODE
**File:** `position_manager.py` lines 2481, 2496, 2498-2499, 2653
**Current:** `trailing_active = False` hardcoded everywhere.
**Impact:** Lines 2498-2499 are unreachable dead code. Cascade flip `not trailing_active` is always True.
**Fix:** Either remove dead code (lines 2496, 2498-2499) or wire `trailing_active = True` when trailing SL is active.

---

### P2-11 — r2_trend HARDCODED STALENESS
**File:** `signals/r2_trend.py` line 195
**Fix:** Use `CANDLES_STALENESS_SEC` from hermes_constants.

---

### P2-12 — hh_hl ATR NO BOUNDS CHECK
**File:** `signals/hh_hl.py` line 229+
**Fix:** Add guard: reject signal if `atr_pct < MIN_ATR_PCT or atr_pct > MAX_SL_PCT`.

---

### P2-13 — pattern_scanner FULL UNIVERSE
**File:** `signal_gen.py` lines 2273-2307
**Fix:** Add hot-set token gate.

---

### P3-14 through P3-17 — CONVENTIONS
- **hzscore.py:118** — `'hzscore-'` for LONG, `'hzscore+'` for SHORT (inverted vs convention)
- **vel_hermes.py:138,147** — same inversion
- **counter_flip.py:272** — source from sub-detector not direction
- **r2_rev_5m.py:36** — imports non-existent `paths` module

---

### PRIOR AUDIT BUGS (still pending)

**signal_compactor.py opposing penalty** (BUG-NEW-5):
```python
# Current (wrong): counts source components
opp_source_count += len(opp_parts)
# Fix: count opposing direction rows
opp_source_count += len(opp_sources)
```

**signal_compactor.py column index** (BUG-NEW-6):
```python
# Current (fragile):
compact_rounds = row[8]
combo_key      = row[10]
# Fix: named column access via cursor.description
```

---

## FIX ORDER

1. **P0-1** — ema20_50.py source inversion (clears bad data from hot-set scoring)
2. **P0-2** — guppy.py undefined constants (NameError on call — clear crasher)
3. **P0-3** — guardian `_record_trade_outcome` call sites (signal_outcomes DB dead — self-correction on losses disabled)
4. **P1-4** — hermes_constants.py ATR caps to T's spec (SL_MAX=2%, TP_MIN=0.75%)
5. **P1-7** — signal_gen.py `_fast_zscore` silent failure
6. **P1-8** — signal_gen.py duplicate detect_phase
7. **P1-9** — position_manager trailing_active dead code
8. **P2-10** — r2_trend hardcoded staleness
9. **P2-11** — hh_hl ATR bounds check
10. **P1-5** — guppy hot-set gate
11. **P1-6** — macd_accel candles.db → price_history
12. **P3-12 through P3-15** — convention fixes
13. **signal_compactor** — prior audit bugs (opposing penalty, column index)
