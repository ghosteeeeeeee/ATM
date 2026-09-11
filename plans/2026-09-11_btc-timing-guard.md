# BTC Timing Guard — Per-Signal-Type Momentum Filter

**Date:** 2026-09-11
**Status:** PLAN → MOE REVIEW
**Trigger:** 16/27 losers (59%) had entry issues — chasing BTC momentum with wrong signal types. pump-chain+ loses 70% when BTC > +0.3%. pump-chain- loses 60% when BTC < -0.3%.
**Core Insight:** The problem isn't "when to trade" — it's "which signals chase and which don't." Solution: per-signal-type thresholds, not blanket filters.

---

## Problem Statement

From the last 50 trades:

| Signal Type | BTC State at Entry | Win Rate | Problem |
|-------------|-------------------|----------|---------|
| pump-chain+ | BTC > +0.3% | 30% | Chasing rally |
| pump-chain- | BTC < -0.3% | 40% | Chasing drop |
| pullback-entry- | BTC < -0.2% | 44% | Chasing drop |
| open-skies+ | BTC > +1.0% | 67% | Doesn't chase |
| mover+ | Any | 80% | Doesn't chase |

**12/27 losers were "chasing" — entering after BTC already moved in the trade direction.**

### Specific Losing Examples

**LONG chasing (pump-chain+):**
| Coin | PnL | BTC 30m | What Happened |
|------|-----|---------|---------------|
| AVAX | -4.48% | +2.21% | BTC already rallied 2.2%, alt already moved |
| ARB | -5.90% | +2.57% | BTC already rallied 2.6%, entered at top |
| BABY | -3.82% | +1.33% | BTC already up 1.3%, chasing |
| DOGE | -3.23% | +0.54% | BTC up 0.5%, late entry |

**SHORT chasing (pump-chain- / pullback-entry-):**
| Coin | PnL | BTC 30m | What Happened |
|------|-----|---------|---------------|
| AIXBT | -3.33% | -0.42% | BTC already dropped 0.4%, shorted at bottom |
| NOT | -4.28% | -0.35% | Shorted into falling knife |
| BCH | -5.48% | -0.32% | Shorted after drop complete |
| AVAX | -8.14% | -0.25% | Shorted into bounce (BTC 1h was +1.64%) |

---

## Solution: Signal-Type Aware Guard

### How It Works

Add per-signal-type BTC momentum thresholds to `_score_signal()`:

- **pump-chain+** → blocked when BTC > +0.3% (already rallied, don't chase)
- **pump-chain-** → blocked when BTC < -0.3% (already dropped, don't chase)
- **pullback-entry+** → blocked when BTC > +0.2% (more sensitive)
- **pullback-entry-** → blocked when BTC < -0.2% (more sensitive)
- **open-skies+** → blocked only when BTC > +1.0% (aggressive signal, allow higher)
- **accel-300-v4-short-** → blocked when BTC < -0.15% (very sensitive)

### Constants

```python
BTC_TIMING_GUARD_ENABLED = True

# Per-signal-type thresholds (BTC 30m momentum)
BTC_TIMING_GUARD_PUMP_CHAIN_LONG = 0.30    # % — block pump-chain+ if BTC > this
BTC_TIMING_GUARD_PUMP_CHAIN_SHORT = -0.30  # % — block pump-chain- if BTC < this
BTC_TIMING_GUARD_PULLBACK_LONG = 0.20      # % — block pullback-entry+ if BTC > this
BTC_TIMING_GUARD_PULLBACK_SHORT = -0.20    # % — block pullback-entry- if BTC < this
BTC_TIMING_GUARD_OPEN_SKIES_LONG = 1.00    # % — open-skies+ is aggressive, allow higher
BTC_TIMING_GUARD_ACCEL_SHORT = -0.15       # % — accel-300-v4-short- is sensitive

BTC_TIMING_GUARD_LOG_ONLY = True           # True = log only, don't block (48h test)
```

### Implementation

~25 lines in `signal_compactor.py`, after the BTC chop gate check.

---

## Expected Impact

| Signal | Threshold | Trades Blocked | Bad Blocked | Good Blocked | Net |
|--------|-----------|---------------|-------------|--------------|-----|
| pump-chain+ | BTC > +0.3% | 5 | 4 | 1 | +$17.55 |
| pump-chain- | BTC < -0.3% | 3 | 2 | 1 | +$7.61 |
| pullback-entry- | BTC < -0.2% | 4 | 2 | 2 | +$3.74 |
| **Total** | | **12** | **8** | **4** | **+$28.90** |

**Conservative estimate:** Even 50% effectiveness → +$14 saved per 50 trades.

---

## Risks

| Risk | Mitigation |
|------|-----------|
| Over-filtering pump-chain | Threshold is per-signal, not global |
| Missing valid entries | Only blocks when BTC has already moved significantly |
| Threshold drift | Monitor win rate of blocked vs allowed trades |
| Interaction with chop gate | Timing guard runs after chop gate — no conflict |

---

## Testing Plan

1. **LOG-ONLY (48h):** Add timing guard, log what would be blocked
2. **Review:** Check if blocked trades were actually losers
3. **Enable:** Set LOG_ONLY=False after clean logs
4. **Monitor:** Track win rate improvement

---

## Files to Modify

| File | Change | Lines |
|------|--------|-------|
| `scripts/hermes_constants.py` | Add 8 timing guard constants | ~10 lines |
| `scripts/signal_compactor.py` | Add timing guard check | ~25 lines |

**Total: ~35 lines + 8 constants.**
