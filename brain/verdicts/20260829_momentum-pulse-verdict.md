# Independent Verdict: Momentum Pulse Signal

**Auditor:** Own-Conclusions Skill (Independent)
**Date:** 2026-08-29
**Files Read:** momentum-pulse-signal.md, r2_trend_long.py, hermes_constants.py, volatility_gate.py
**Data Analyzed:** TURBO, DOGE, ENA, ETH, BTC (14d, 1m and 5m candles)

---

## Executive Summary

**Overall Verdict: DISAGREE** with the claims made in the momentum-pulse-signal.md plan.

The signal has **fundamental design flaws** and the claimed backtest results are **significantly overstated**. The signal would NOT have caught the TURBO pump it was designed for, and the claimed ENA performance (64.2% WR, +69.76% PnL) is not reproducible.

---

## Claim-by-Claim Verdicts

### Claim 1: "3 consecutive green candles + SMA(10) + RSI 50-75 + ATR expanding catches micro-cap pumps"

**Verdict: DISAGREE**

**Evidence:**
- **TURBO Aug 28 13:00-22:00 UTC analysis:** 0 signals fired during this period
- **Root cause:** 77.1% of TURBO 1m candles have `open == close` (flat candles), so "3 consecutive green candles" rule NEVER triggers
- **5m candles (better data):** TURBO had 16 trades with only 37.5% WR and -2.00% PnL
- **Overall 5m backtest:** 52 trades, 36.5% WR, +1.91% PnL across 5 tokens

**Confidence: HIGH**

**Notes:**
- The "3 consecutive green candles" rule is **fundamentally flawed** because it depends on candle OHLC structure, which is unreliable in the available data
- ATR(14) > SMA(ATR,20) filter is too restrictive — blocks most entries
- RSI 50-75 range is reasonable but combined with other filters, too few signals fire

---

### Claim 2: "ENA is the standout performer (64.2% WR, +69.76% PnL)"

**Verdict: DISAGREE**

**Evidence:**
- **My 5m backtest:** ENA had 53.3% WR, +6.93% PnL (not 64.2% WR, +69.76%)
- **My 1m backtest:** ENA had 44.4% WR, +8.19% PnL
- **Discrepancy:** Claimed PnL is 10x higher than reproducible results
- **Possible explanation:** Original backtest may have used different parameters, time period, or had data quality issues

**Confidence: HIGH**

**Notes:**
- ENA does perform best among tested tokens, but nowhere near claimed levels
- The +69.76% PnL claim is **not reproducible** with the specified rules

---

### Claim 3: "TURBO missed because R² > 0.70 blocked 84% of checks"

**Verdict: DISAGREE**

**Evidence:**
- **Momentum pulse signal does NOT use R² filter** — this is a r2_trend_long filter
- **My R² analysis of TURBO:** Only 78.2% of 16-bar windows had R² < 0.70 (not 84%)
- **TURBO actually had 16 trades** on 5m candles — not "missed"
- **TURBO performance:** 37.5% WR, -2.00% PnL (poor, but not "missed")

**Confidence: HIGH**

**Notes:**
- The claim conflates two different signals: momentum_pulse (no R² filter) and r2_trend_long (uses R²)
- TURBO data quality is poor: 77.1% flat candles, 73.9% zero volume
- The signal DOES fire on TURBO — it just doesn't perform well

---

### Claim 4: "The signal works best on tokens with strong momentum trends"

**Verdict: PARTIAL**

**Evidence:**
- **ENA (best performer):** 53.3% WR, +6.93% PnL — moderate momentum
- **BTC (worst performer):** 25.0% WR, -0.43% PnL — strong trend but low volatility
- **TURBO (micro-cap):** 37.5% WR, -2.00% PnL — high volatility but poor data
- **Pattern:** Signal works better on mid-cap tokens with moderate volatility, not necessarily "strong momentum trends"

**Confidence: MEDIUM**

**Notes:**
- The signal seems to work best on tokens with **consistent volatility** (like ENA)
- Micro-cap tokens (TURBO) have poor data quality, making backtests unreliable
- Large-cap tokens (BTC, ETH) have low ATR, so few signals fire

---

## Design Flaw Analysis

### Flaw 1: "3 consecutive green candles" rule is unreliable
- **Problem:** Depends on OHLC structure, which is synthetic/placeholder in 77% of TURBO data
- **Impact:** Signal never fires on TURBO during the pump it was designed for
- **Fix:** Use close-to-close momentum instead of candle color

### Flaw 2: ATR expansion filter is too restrictive
- **Problem:** ATR(14) > SMA(ATR,20) blocks most entries
- **Impact:** Only 52 trades across 5 tokens in 14 days (very low frequency)
- **Fix:** Use ATR percentile or relaxation factor

### Flaw 3: Exit rules are suboptimal
- **Problem:** 68% of exits are stop-losses (33/49), indicating poor entry timing
- **Impact:** Negative expectancy on 4/5 tokens
- **Fix:** Tighter entry filters or wider stops

### Flaw 4: Data quality issues invalidate backtest
- **Problem:** 77% of TURBO 1m candles have open == close
- **Impact:** Cannot reliably test "green candle" rules
- **Fix:** Use 5m candles or fix data collection

---

## Comparison with Existing Signals

| Signal | Core Logic | Overlap with Momentum Pulse |
|--------|------------|----------------------------|
| **r2_trend_long** | R² > 0.70, slope > 0 | Low — different entry criteria |
| **hzscore** | MTF Z-Score extremes | Low — mean-reversion vs momentum |
| **mover** | Top movers + confluence | Medium — both momentum-based |
| **wave_catcher** | Velocity spikes | High — similar momentum detection |

**Overlap Risk:** MEDIUM — momentum_pulse may duplicate wave_catcher/mover signals during strong moves.

---

## Recommendations

### 1. Do NOT implement as-is
The signal has fundamental flaws and the claimed performance is not reproducible.

### 2. If pursuing this concept, redesign:
- Replace "3 green candles" with **close-to-close momentum** (>X% over N bars)
- Use **ATR percentile** instead of ATR > SMA
- Add **volume filter** (currently missing — volume data is unreliable)
- Test on **5m candles only** (1m data quality is poor)

### 3. Fix data quality first
- 77% of TURBO 1m candles have open == close
- 73.9% have zero volume
- Cannot reliably backtest any signal on this data

### 4. Consider merging with wave_catcher
- wave_catcher already catches velocity spikes
- momentum_pulse adds RSI/ATR filters — could be added to wave_catcher instead

---

## Final Verdict

**AGREE / DISAGREE / PARTIAL:** **DISAGREE**

The momentum pulse signal as described:
- ❌ Would NOT have caught the TURBO pump (0 signals fired)
- ❌ ENA performance is overstated (53% WR vs claimed 64%)
- ❌ TURBO R² claim is incorrect (different signal, wrong percentage)
- ❌ Overall performance is mediocre (36.5% WR, +1.91% PnL)
- ⚠️ Has fundamental design flaws (green candle rule, ATR filter)
- ⚠️ Data quality issues invalidate backtest results

**Recommendation:** Redesign from scratch or merge filters into existing signals (wave_catcher, mover).

---

**Files Created:**
- `/root/.hermes/scripts/backtest_momentum_pulse.py` — 1m backtest script
- `/root/.hermes/scripts/backtest_momentum_pulse_5m.py` — 5m backtest script (recommended)
- `/root/.hermes/brain/verdicts/20260829_momentum-pulse-verdict.md` — this verdict