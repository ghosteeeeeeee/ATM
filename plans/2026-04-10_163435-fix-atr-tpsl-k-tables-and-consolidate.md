# Fix ATR TP/SL — Consolidate k Tables & Tighten SL

## Problem Statement
MET LONG entry $0.1332, current $0.13558. DB SL=$0.134413 but T estimates ~$0.135.

Live MET: price=$0.13558, ATR(14)=$0.000590 (0.44% — very low volatility).

## Root Cause Analysis

**4 places compute ATR TP/SL with different k tables:**

| Script | k for ATR <1% | k for ATR 1-3% | k for ATR >3% | Status |
|---|---|---|---|---|
| `decider_run.py` (canonical) | k=2.5 | k=1.5 | k=2.5 | WRONG: k=2.5 is too LOOSE for low-vol |
| `position_manager.py` | k=1.5 | k=2.0 | k=2.5 | WRONG: inverted logic |
| `batch_tpsl_rewrite.py` | k=2.0 | k=2.0 | k=1.5 | WRONG: inverted logic |
| `hl-sync-guardian.py` | k=2.5 + MIN_ATR_PCT=1.5% floor | k=1.5 + MIN_ATR_PCT=1.5% | k=2.5 | LOOSE: 1.5% min floor too wide for low-vol |

**Current MET SL = $0.134413 implies k≈2.0x ATR** (some mix of these broken tables).

**Correct MET SL at k=1.0: $0.13558 - 1×$0.000590 = $0.134990 ≈ $0.135** (T's estimate).

## Proposed Canonical k Table

For low-vol tokens (ATR <1% of price), use k=1.0 for tighter, more responsive SL:

| ATR% | k | Rationale |
|---|---|---|
| <1% (LOW_VOL) | k=1.0 | Tight SL — these are stable tokens, don't need wide stops |
| 1-3% (NORMAL_VOL) | k=2.0 | Balanced |
| >3% (HIGH_VOL) | k=2.5 | Wide SL for volatile tokens |

TP multiplier = k_tp × ATR where k_tp = 2.5 × k (consistent R:R).

## Actions

### 1. Fix `decider_run.py` — canonical source of truth
- [ ] Fix `_atr_multiplier()` k table
- [ ] Fix `_compute_dynamic_sl()` MIN_ATR_PCT floor (1.0% not 1.5%)
- [ ] Fix `_compute_dynamic_tp()` MIN_TP_PCT (2.0% not 3.0%)
- [ ] Fix `k_tp` multipliers in `_compute_dynamic_tp()`: k_tp = 2.5 × k
- [ ] Add `k_tp` to canonical docstring

### 2. Remove `batch_tpsl_rewrite.py` from active use
- [ ] It duplicates guardian.py's TP/SL reconciliation
- [ ] Guardian runs continuously; batch_tpsl_rewrite every minute can overwrite with wrong k table
- [ ] Mask the systemd timer if it exists

### 3. Fix `position_manager.py` — new trade entry
- [ ] Fix `_atr_multiplier()` k table to match decider_run
- [ ] Change MIN_ATR_PCT from 0.0075 to 0.010 (1.0%)
- [ ] Make `_dr_atr()` proxy use the corrected canonical function

### 4. Apply fix to current MET position
- [ ] Run guardian reconcile or direct DB update to tighten SL to canonical

### 5. Verify no other overwriters
- [ ] `self_close_watcher.py` uses k=2.0, k_tp=5.0 — review if this conflicts
- [ ] `ai_decider.py` reads `stop_loss` from DB — no computation, ok

## MET Corrected Values (ATR=0.44%)

| | k | Price | Distance |
|---|---|---|---|
| SL | 1.0 | $0.13499 | -0.44% |
| TP | 2.5 | $0.13968 | +3.02% |

## Files to Modify
- `/root/.hermes/scripts/decider_run.py` — canonical
- `/root/.hermes/scripts/position_manager.py` — new trades
- `/root/.hermes/scripts/hl-sync-guardian.py` — already calls decider_run, check MIN_ATR_PCT
- Mask: `batch_tpsl_rewrite.timer` if systemd timer exists
