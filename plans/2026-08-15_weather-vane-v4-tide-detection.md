# Weather Vane v4 — Tide Detection (Updated with Backtests)

**Date:** 2026-08-15
**Status:** BACKTESTED — BTC 3h momentum is the fastest tide indicator
**Key Finding:** No truly predictive indicator exists in our data. BTC 3h momentum is the FASTEST lagging indicator — faster than SHORT win rate but still backward-looking.

---

## Backtest Summary (14 days, 836 trades)

### BTC Momentum Windows

| Window | Indicator | BEST for | WR | PnL |
|--------|-----------|----------|-----|-----|
| 3h momentum falling | -0.5% to -0.1% | SHORT | **70.6%** | **+$0.41** |
| 3h momentum rising | 0.1% to 0.5% | LONG | 47.5% | +$0.58 |
| 5h momentum flat | -0.1% to 0.1% | SHORT | **94.4%** | **+$1.49** (18T only) |
| 5h momentum rising | 0.1% to 0.5% | SHORT | 40.0% | -$1.35 |

### BTC Acceleration (adds noise, not signal)

| BTC accel | SHORT WR | LONG WR |
|-----------|----------|---------|
| >0.1 (accelerating up) | 50.8% | 69.2% (13T) |
| <-0.1 (accelerating down) | 40.9% | 46.3% |

Acceleration alone doesn't improve predictions — it adds noise. BTC momentum alone is cleaner.

### SHORT Win Rate as Confirmation (lagging)

| SHORT WR | SHORT WR | Gap |
|----------|----------|-----|
| >55% (10-trade) | 56.4% WR, +$0.33 | 18.3pt vs <45% |
| <45% (10-trade) | 38.1% WR, -$1.24 | |

### Combined: BTC Momentum + SHORT Win Rate

| Scenario | LONG | SHORT |
|----------|------|-------|
| BTC 3h falling + SHORT WR<45% | — | BEST: SHORT confirms losing |
| BTC 3h rising + SHORT WR>55% | — | SHORT still losing despite WR |

---

## Honest Assessment

**Is it predictive?** No. BTC momentum is backward-looking (what happened in last 3 hours). SHORT win rate is even more backward-looking (requires 5+ losses).

**What we actually have:**
- BTC 3h momentum = FASTEST lagging indicator (shifts within 3 hours)
- SHORT win rate = SLOWEST lagging indicator (requires 5+ losses)
- Neither is truly predictive

**The practical value:** BTC momentum gets there FIRST. By the time SHORT win rate drops to 45%, BTC momentum has already been falling for 3+ hours. Using BTC momentum means we react 2-3 hours earlier than SHORT win rate alone.

**What would be truly predictive:** Nothing in our current data. We'd need:
- Real-time order flow (not available)
- Funding rate changes (not tracked)
- Open interest shifts (not tracked)
- Cross-exchange arbitrage signals (not tracked)

---

## Design: Tide Detection (Revised)

### Primary Signal: BTC 3h Momentum

```python
btc_mom_3h = (btc_close[now] - btc_close[3h_ago]) / btc_close[3h_ago] * 100
```

- **Falling (-0.5% to -0.1%):** SHORT favored (70.6% WR)
- **Rising (0.1% to 0.5%):** LONG favored (47.5% WR vs SHORT 40.2%)
- **Flat (-0.1% to 0.1%):** Neutral — no bias

### Confirmation: SHORT Win Rate (10-trade window)

Used as CONFIRMATION, not primary signal:
- SHORT WR >55% confirms bearish tide
- SHORT WR <45% confirms bullish tide

### Combined Rule

```
Bearish tide: BTC 3h momentum falling AND SHORT WR > 55%
  → Suppress LONG (0.7x)

Bullish tide: BTC 3h momentum rising AND SHORT WR < 45%
  → Suppress SHORT (0.7x)

Otherwise: no suppression
```

### Why This Works

1. BTC momentum shifts FIRST (3-hour window)
2. SHORT win rate confirms LATER (requires 5+ trades)
3. Together: BTC momentum detects the shift, SHORT win rate confirms it happened
4. Soft penalty (0.7x) — counter-tide trades still fire, just ranked lower

### Params

```python
TIDE_ENABLED = True
TIDE_PENALTY = 0.7
TIDE_BTC_MOM_WINDOW = 3          # hours for BTC momentum
TIDE_BTC_MOM_FALLING = -0.1     # % — below this = falling
TIDE_BTC_MOM_RISING = 0.1       # % — above this = rising
TIDE_SHORT_WR_WINDOW = 10        # trades for confirmation
TIDE_SHORT_WR_THRESHOLD_HIGH = 55
TIDE_SHORT_WR_THRESHOLD_LOW = 45
```

---

## What We Learned

1. **SHORT win rate is too slow** — requires 5+ losses, by then damage is done
2. **BTC momentum is faster** — shifts within 3 hours, catches the wave earlier
3. **Acceleration adds noise** — not useful as standalone signal
4. **No truly predictive indicator exists** in our data — we're always one step behind
5. **The best approach:** fastest lagging indicator (BTC momentum) + confirmation (SHORT win rate)

---

## Files to Modify

| File | Change |
|------|--------|
| `scripts/hermes_constants.py` | Add TIDE_* params |
| `scripts/signal_compactor.py` | Add `get_tide_penalty()`, `_get_btc_momentum()`, integrate into `_score_signal()` |
