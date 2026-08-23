# Spec: Re-enable MAE Guard + Multi-Alt Divergence Filter

**Date:** 2026-08-23
**Status:** REVISED after independent review
**Review Findings:** Critical bug fixed (wrong constant target), integration code added, rollback plan included

---

## Change 1: Re-enable MAE Guard at 2.0% (conservative start)

### What
Re-enable the MAE (Maximum Adverse Excursion) Guard that cuts LONG positions when price drops more than threshold from peak.

### Why
- Aug 23 crash: 3 trades lost $0.83 total. MAE Guard would have cut them faster.
- Current state: `CL_MAE_GUARD_ENABLED = False` (disabled 2026-08-23)
- The ATR-aware version in `btc_crash_filter.py` scales threshold dynamically
- **Conservative start at 2.0%** — prior analysis showed 1.5% costs -$5.43/week. Start at 2.0%, tighten to 1.5% only if ATR-aware version proves profitable.

### CRITICAL: Correct Constant Target

The ATR-aware code uses `CL_MAE_GUARD_BASE_THRESHOLD`, NOT `CL_MAE_GUARD_THRESHOLD`:

```python
# btc_crash_filter.py:check_position_protection() line 453:
threshold = CL_MAE_GUARD_BASE_THRESHOLD * atr_ratio  # ← THIS is the active constant

# cut_loser.py:run_mae_guard() line 371:
if mae_from_peak >= CL_MAE_GUARD_THRESHOLD:  # ← Only used in LEGACY FALLBACK
```

### Files to Modify

**`scripts/hermes_constants.py`** (lines 819, 1015-1016):
```python
# BEFORE (line 819):
CL_MAE_GUARD_BASE_THRESHOLD = 0.025     # 2.5% base — scales with ATR

# AFTER:
CL_MAE_GUARD_BASE_THRESHOLD = 0.020     # 2.0% base — conservative start, scales with ATR

# BEFORE (lines 1015-1016):
CL_MAE_GUARD_ENABLED    = False  # DISABLED 2026-08-23
CL_MAE_GUARD_THRESHOLD  = 0.030  # 3.0%

# AFTER:
CL_MAE_GUARD_ENABLED    = True   # RE-ENABLED 2026-08-23 — ATR-aware version scales dynamically
CL_MAE_GUARD_THRESHOLD  = 0.020  # 2.0% — legacy fallback (must match BASE_THRESHOLD)
```

### How It Works (existing code)
The ATR-aware MAE Guard in `btc_crash_filter.py:check_position_protection()`:
1. Gets token's ATR% from volatility_gate
2. Scales threshold: `base_threshold * (token_atr / baseline_atr)`
3. If BTC is crashing (-0.5% in 5m): tightens by `CL_MAE_GUARD_BTC_CRASH_MULTIPLIER` (0.6)
4. Minimum threshold: 1% (never cut tighter than this)

**Example with 2.0% base:**
- Normal vol (ATR 0.8%): threshold = 2.0% * (0.8/0.8) = 2.0%
- Low vol (ATR 0.5%): threshold = 2.0% * (0.5/0.8) = 1.25%
- High vol (ATR 1.2%): threshold = 2.0% * (1.2/0.8) = 3.0%
- BTC crashing: threshold *= 0.6 → 1.2% (cuts faster during crashes)

### Rollback Plan
```python
# If MAE Guard causes net loss after 7 days:
CL_MAE_GUARD_ENABLED = False  # ← instant disable, no restart needed
```
Monitor: `grep "MAE-GUARD" /root/.hermes/logs/cut_loser.log`

### Risk Assessment
| Risk | Impact | Mitigation |
|------|--------|------------|
| Cuts winners that recover | Medium | ATR scaling + 2.0% base (conservative) |
| Too aggressive in low vol | Low | Minimum 1% threshold |
| Prior -$5.43/week loss | Medium | Start at 2.0%, not 1.5%; monitor daily |

---

## Change 2: Multi-Alt Divergence Filter (Layer 6)

### What
Add Layer 6 to `btc_crash_filter.py`: detect when multiple alts are weak while BTC is falling — early warning of cascade risk.

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

**`scripts/btc_crash_filter.py`** (new function + integration):

```python
# ── Layer 6: Multi-Alt Divergence ──────────────────────────────────────────

def _check_multi_alt_divergence(btc_closes: list) -> Tuple[bool, int, list]:
    """Check if multiple alts are weak while BTC is falling.

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

### Integration into check_crash()

```python
# In check_crash(), after Layer 4 (acceleration):

# Layer 6: Multi-Alt Divergence
multi_alt_blocked, weak_count, weak_alts = _check_multi_alt_divergence(btc_closes)
if multi_alt_blocked:
    triggered_layers.append('MULTI_ALT')

# ... severity logic ...

# After severity assessment, apply MULTI_ALT block INDEPENDENTLY:
if multi_alt_blocked:
    signal.blocked = True
    signal.severity = 'WARNING'
    signal.layer = 'MULTI_ALT'
    signal.reason = (f'Multi-alt weakness: {weak_count} alts diverging '
                    f'{MULTI_ALT_DIVERGENCE_THRESHOLD}%+ below BTC')
    signal.block_until = time.time() + (MULTI_ALT_BLOCK_DURATION_MIN * 60)
    # Note: MULTI_ALT block is INDEPENDENT of severity logic.
    # If PRICE also triggers, the LONGER block duration wins.
    if price_blocked and signal.block_until < time.time() + (PRICE_BLOCK_DURATION * 60):
        signal.block_until = time.time() + (PRICE_BLOCK_DURATION * 60)
```

### Block Duration Interaction
| Scenario | Block Duration |
|----------|---------------|
| MULTI_ALT only | 10 minutes |
| PRICE only | 3-10 minutes (severity-based) |
| MULTI_ALT + PRICE | Max of both (longer wins) |
| MULTI_ALT + CONTAGION | 10 minutes (MULTI_ALT dominates) |

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
| Misses crashes without alt weakness | Medium | Layers 1-4 still active |
| Token-specific weakness triggers filter | Low | Reference alts are major caps, not niche |
| Block duration conflicts with severity | Low | Max-of-both logic prevents early expiry |

---

## Integration Points

### Where MAE Guard Runs
- `cut_loser.py` → `run_mae_guard()` → called every wake (1min)
- Tries `btc_crash_filter.py:check_position_protection()` first (ATR-aware)
- Falls back to legacy `CL_MAE_GUARD_THRESHOLD` if import fails

### Where Multi-Alt Filter Runs
- `btc_crash_filter.py:check_crash()` → called from `decider_run.py` before hot-set iteration
- Sets `signal.blocked = True` + `signal.block_until`
- `decider_run.py` checks `_btc_crash_blocked` flag

### Interaction Between Changes
```
MAE Guard (cut_loser.py)          Multi-Alt Filter (btc_crash_filter.py)
        │                                    │
        ▼                                    ▼
  Cuts EXISTING                  Blocks NEW entries
  LONG positions                 during weakness
        │                                    │
        └──────────┬─────────────────────────┘
                   ▼
           CASCADE PROTECTION
```

---

## Implementation Order

1. **Re-enable MAE Guard** — change `CL_MAE_GUARD_ENABLED`, `CL_MAE_GUARD_BASE_THRESHOLD`, `CL_MAE_GUARD_THRESHOLD`
2. **Add multi-alt constants** — 6 new constants in hermes_constants.py
3. **Add `_check_multi_alt_divergence()` function** — new function in btc_crash_filter.py
4. **Integrate into `check_crash()`** — add Layer 6 call + block logic
5. **Test with diagnostic** — `python3 btc_crash_filter.py`
6. **Monitor for 7 days** — check cut_loser.log + pipeline.log
7. **Decision point** — if MAE Guard profitable at 2.0%, consider tightening to 1.5%

---

## Verification

After implementation:
1. `python3 scripts/btc_crash_filter.py` — check diagnostic output
2. `grep "MAE-GUARD" /root/.hermes/logs/cut_loser.log` — monitor triggers
3. `grep "MULTI-ALT" /root/.hermes/logs/pipeline.log` — monitor triggers
4. Backtest on 7d data to verify no regression
5. After 7 days: check if MAE Guard is net positive at 2.0%

---

## Rollback

If either change causes problems:
```python
# Instant disable (no restart needed):
CL_MAE_GUARD_ENABLED = False           # disables MAE Guard
MULTI_ALT_DIVERGENCE_ENABLED = False   # disables multi-alt filter
```
