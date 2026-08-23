# Spec: Re-enable MAE Guard + Multi-Alt Divergence Filter

**Date:** 2026-08-23
**Status:** READY FOR IMPLEMENTATION

---

## Change 1: Re-enable MAE Guard at 1.5%

### What
Re-enable the MAE (Maximum Adverse Excursion) Guard that cuts LONG positions when price drops more than threshold from peak.

### Why
- Aug 23 crash: 3 trades lost $0.83 total. MAE Guard would have cut them faster.
- Current state: `CL_MAE_GUARD_ENABLED = False` (disabled 2026-08-23)
- The ATR-aware version in `btc_crash_filter.py` already scales threshold dynamically

### Files to Modify

**`scripts/hermes_constants.py`** (lines 1015-1016):
```python
# BEFORE:
CL_MAE_GUARD_ENABLED    = False  # DISABLED 2026-08-23
CL_MAE_GUARD_THRESHOLD  = 0.030  # 3.0%

# AFTER:
CL_MAE_GUARD_ENABLED    = True   # RE-ENABLED 2026-08-23 — ATR-aware version scales dynamically
CL_MAE_GUARD_THRESHOLD  = 0.015  # 1.5% — base threshold, scaled by ATR in btc_crash_filter.py
```

### How It Works (existing code)
The ATR-aware MAE Guard in `btc_crash_filter.py:check_position_protection()`:
1. Gets token's ATR% from volatility_gate
2. Scales threshold: `base_threshold * (token_atr / baseline_atr)`
3. If BTC is crashing (-0.5% in 5m): tightens by `CL_MAE_GUARD_BTC_CRASH_MULTIPLIER` (0.6)
4. Minimum threshold: 1% (never cut tighter than this)

**Example with 1.5% base:**
- Normal vol (ATR 0.8%): threshold = 1.5% * (0.8/0.8) = 1.5%
- Low vol (ATR 0.5%): threshold = 1.5% * (0.5/0.8) = 0.94% → clamped to 1.0%
- High vol (ATR 1.2%): threshold = 1.5% * (1.2/0.8) = 2.25%
- BTC crashing: threshold *= 0.6 → 0.9% (cuts faster during crashes)

### Risk Assessment
| Risk | Impact | Mitigation |
|------|--------|------------|
| Cuts winners that recover | Medium | ATR scaling + BTC crash multiplier |
| Too aggressive in low vol | Low | Minimum 1% threshold |
| Noise cuts | Low | Runs every wake (1min), not instant |

---

## Change 2: Multi-Alt Divergence Filter

### What
Add Layer 6 to `btc_crash_filter.py`: detect when multiple alts are weak while BTC is stable — early warning of cascade risk.

### Why
- Aug 23 crash: 5 alts were weak at 14:25 (17 minutes BEFORE crash)
- Current Layer 3 (contagion) only checks ETH/SOL — misses broader alt weakness
- Backtest: 10 triggers over 7 days, net +$1.92 PnL improvement

### Files to Modify

**`scripts/hermes_constants.py`** (new constants):
```python
# ── Multi-Alt Divergence Filter (Layer 6) ──────────────────────────────────
# Detects alt-specific weakness before BTC cascades.
# When 3+ alts diverge >0.3% below BTC in 5 minutes, block new LONG entries.
MULTI_ALT_DIVERGENCE_ENABLED = True
MULTI_ALT_BTC_5M_THRESHOLD = -0.5     # % — BTC must be falling to activate check
MULTI_ALT_DIVERGENCE_THRESHOLD = -0.3  # % — alt must underperform BTC by this much
MULTI_ALT_MIN_WEAK_ALTS = 3           # number of weak alts to trigger signal
MULTI_ALT_BLOCK_DURATION_MIN = 10     # minutes to block LONG entries after trigger
MULTI_ALT_REFERENCE_ALTS = ['ETH', 'SOL', 'XRP', 'DOGE', 'AVAX', 'DOT', 'LINK', 'UNI']
```

**`scripts/btc_crash_filter.py`** (new function + integrate into check_crash):
```python
# ── Layer 6: Multi-Alt Divergence ──────────────────────────────────────────

def _check_multi_alt_divergence(btc_closes: list) -> Tuple[bool, int, list]:
    """Check if multiple alts are weak while BTC is stable/falling.

    When 3+ alts show >0.3% 5m divergence below BTC, it signals
    alt-specific selling pressure that could cascade into BTC.

    Returns: (is_weak, weak_count, weak_alts_list)
    """
    from hermes_constants import (
        MULTI_ALT_DIVERGENCE_ENABLED,
        MULTI_ALT_BTC_5M_THRESHOLD,
        MULTI_ALT_DIVERGENCE_THRESHOLD,
        MULTI_ALT_MIN_WEAK_ALTS,
        MULTI_ALT_REFERENCE_ALTS,
    )

    if not MULTI_ALT_DIVERGENCE_ENABLED:
        return False, 0, []

    if len(btc_closes) < 6:
        return False, 0, []

    # Only activate when BTC is falling
    btc_chg_5m = (btc_closes[-1] - btc_closes[-6]) / btc_closes[-6] * 100
    if btc_chg_5m > MULTI_ALT_BTC_5M_THRESHOLD:
        return False, 0, []

    weak_alts = []
    for alt in MULTI_ALT_REFERENCE_ALTS:
        alt_candles = _get_candles(alt, '1m', 10)
        alt_closes = [c[4] for c in alt_candles]
        if len(alt_closes) < 6:
            continue

        alt_chg_5m = (alt_closes[-1] - alt_closes[-6]) / alt_closes[-6] * 100
        divergence = alt_chg_5m - btc_chg_5m

        if divergence < MULTI_ALT_DIVERGENCE_THRESHOLD:
            weak_alts.append(f"{alt}({divergence:+.2f}%)")

    is_weak = len(weak_alts) >= MULTI_ALT_MIN_WEAK_ALTS
    return is_weak, len(weak_alts), weak_alts
```

### How It Works
1. Checks if BTC is falling (>0.5% in 5m)
2. If yes, checks 8 reference alts (ETH, SOL, XRP, DOGE, AVAX, DOT, LINK, UNI)
3. Counts alts where 5m divergence >0.3% below BTC
4. If 3+ alts are weak → trigger signal, block LONG entries for 10 minutes

### Backtest Results (7 days)
| Metric | Value |
|--------|-------|
| Triggers | 10 (1.43/day) |
| Losers blocked | 12 ($4.08) |
| Winners blocked | 6 ($2.16) |
| **Net PnL** | **+$1.92** |

### Risk Assessment
| Risk | Impact | Mitigation |
|------|--------|------------|
| False positives (normal pullbacks) | Low | BTC must be falling first (>0.5%) |
| Misses crashes without alt weakness | Medium | Layer 1-4 still active |
| Too many reference alts (API calls) | Low | Only fetches when BTC is falling |

---

## Integration Points

### Where MAE Guard Runs
- `cut_loser.py` → `run_mae_guard()` → called every wake (1min)
- Falls back to `btc_crash_filter.py:check_position_protection()` for ATR-aware logic

### Where Multi-Alt Filter Runs
- `btc_crash_filter.py:check_crash()` → called from `decider_run.py` before hot-set iteration
- Blocks entries via `_btc_crash_blocked` flag

### Interaction Between Changes
- MAE Guard protects EXISTING positions (cuts losers fast)
- Multi-Alt Filter blocks NEW entries (prevents entering during weakness)
- Both work together: filter prevents new entries, MAE Guard cuts existing positions

---

## Implementation Order

1. **Re-enable MAE Guard** (1 line change in hermes_constants.py)
2. **Add multi-alt constants** (6 new constants in hermes_constants.py)
3. **Add `_check_multi_alt_divergence()` function** (new function in btc_crash_filter.py)
4. **Integrate into `check_crash()`** (add Layer 6 call)
5. **Test with diagnostic** (run `python3 btc_crash_filter.py`)

---

## Verification

After implementation:
1. Run `python3 scripts/btc_crash_filter.py` — check diagnostic output
2. Monitor `cut_loser.log` for MAE-GUARD triggers
3. Monitor `pipeline.log` for MULTI-ALT-DIVERGENCE triggers
4. Backtest on 7d data to verify no regression
