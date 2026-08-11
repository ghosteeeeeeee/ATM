# Signal Degradation Analysis — Aug 5-11, 2026

**Date:** 2026-08-11
**Status:** Action plan needed
**Root Cause:** Market structure shift + SL/trailing params misfiring during transition

---

## Executive Summary

Between Aug 5-11, the trading system experienced a signal quality collapse. The primary cause is **not** a single breaking change — it's the combination of a market regime shift (trending → compressed/ranging) coinciding with aggressive SL/trailing tightening that was inappropriate for the new regime.

**Key finding:** `bb_bounce+,hzscore+` was 80% WR on Aug 9 under 1.2% SL. The same signal at 0.5% SL became 25% WR. The signal quality was fine; the risk management became too aggressive for mean-reversion trades in a flat market.

---

## Data Sources

| Source | Path | Purpose |
|--------|------|---------|
| Signal outcomes DB | `/root/.hermes/data/signals_hermes_runtime.db` | All trade records, PnL, win/loss |
| Candles DB | `/root/.hermes/data/candles.db` | Price data, ATR calculations |
| Pipeline log | `/root/.hermes/logs/pipeline.log` | Runtime decisions, gate activity |
| Hermes constants | `/root/.hermes/scripts/hermes_constants.py` | SL/TP params, blacklists |
| Volatility gate | `/root/.hermes/scripts/volatility_gate.py` | Regime classification |
| TPSL utils | `/root/.hermes/scripts/tpsl_utils.py` | SL/TP computation |
| Position manager | `/root/.hermes/scripts/position_manager.py` | Trade execution |
| Signal generators | `/root/.hermes/scripts/signals/` | Signal logic |
| Git history | `git log/diff` | Change timeline |

---

## Timeline of Changes

### Aug 5 — Peak Performance (139 trades, 52.5% WR)
- `tl_break_long`: 100% WR (14T), +$1.81
- `tl_break_short`: 80% WR (5T), +$0.22
- `vel-hermes-`: 43.5% WR (46T), +$0.47
- `zscore-rising`: 55-63% WR, positive PnL
- Market was transitioning from trending to flat

### Aug 7 — Best WR Day (56 trades, 62.5% WR)
- `bb_bounce+,range_finder+`: 83% WR (6T)
- `bb_bounce,hzscore+`: 100% WR (2T)
- `ma100-cross,range_finder`: 60% WR
- Momentum signals fading, mean-reversion taking over

### Aug 8 — Flat Day (39 trades, 43.6% WR)
- `bb_bounce+,range_finder+`: 64% WR (14T)
- Signal mix shifting to mean-reversion combos

### Aug 9 — Last Good Day (65 trades, 60.0% WR)
- `bb_bounce+,hzscore+`: 80% WR (5T), +$0.42
- `bb_bounce+,range_finder+`: 58% WR (26T)
- `bb-bounce-short,hzscore-`: 58% WR (12T)
- **Velocity gate added** (commit `33b6670`): blocks LONG when 15m vel < -0.3%

### Aug 10 — The Breaking Point (65 trades, 44.6% WR)
- **SL tightened** (commit `36e4cd0`): 1.2% → 0.5% min, 2.5% → 1.0% max
- **Trailing tightened** (commit `3f2effe`): 0.7% → 0.3%
- `bb_bounce+,hzscore+`: dropped from 80% → 50% WR
- `bb_bounce+,range_finder+`: dropped from 58% → 43% WR
- **64.7% SL hit rate** (was 18.8%)

### Aug 11 — System Frozen
- **SL reverted** (commit `f7a3152`): back to 1.2% min, 2.5% max
- **Trailing reverted**: back to 0.60% (from 0.70% originally)
- **Volatility gate deployed** (commit `f14762b`): regime-based filtering
- **REGIME_SIGNALS updated** (commit `aba2351`): from 30d backtest
- **COSIG-GATE poison-blocked** `bb_bounce+,hzscore+` (commit `9a8d574`)
- **Volatility gate now blocking ALL signals** — 0 entries, system frozen

---

## Market Structure Change

### Regime Shift: Trending → Compressed
- **105/106 tokens are NEUTRAL** (15m regime scanner, Aug 11 14:21)
- Only SOPH shows LONG_BIAS
- Market is compressed/ranging — no trending setups

### Signal Type Evolution
```
Aug 05: vel-hermes-(46), zscore-rising-(31), bb_bounce(18), tl_break_long(14)
        → Momentum signals dominant (trending market)

Aug 07: bb_bounce,range_finder(7), bb_bounce,ma100-cross(7), bb_bounce+,range_finder+(6)
        → Mean-reversion signals emerging

Aug 09: bb_bounce+,range_finder+(26), bb-bounce-short,hzscore-(12), hzscore+,range_finder+(5)
        → Mean-reversion dominant

Aug 10: bb_bounce+,hzscore+(22), bb_bounce+,range_finder+(7), continuation+,hzscore+(4)
        → Pure mean-reversion (flat market)
```

### What This Means
- **Momentum signals** (`tl_break`, `vel-hermes-`) need trending markets → died when market went flat
- **Mean-reversion signals** (`bb_bounce+`) need room to recover → killed by tight SL
- The system correctly adapted signal selection to the regime, but the exit params weren't adapted to match

---

## Root Cause Analysis

### Factor 1: SL Tightening (Primary)
**Commit `36e4cd0` (Aug 10)**
```
ATR_SL_MIN:     1.2% → 0.5%
ATR_SL_MAX:     2.5% → 1.0%
SL_PCT_MIN:     0.5% (was 1.2%)
```
**Impact:** 64.7% SL hit rate (was 18.8%)

Mean-reversion signals enter near the lower Bollinger Band. They **need room to recover** before bouncing. A 0.5% SL gets hit on normal intraday noise — the trade never develops.

**Evidence:**
- `bb_bounce+,hzscore+`: 80% WR at 1.2% SL → 25% WR at 0.5% SL
- Same signal, same tokens, same market — only the SL changed

### Factor 2: Trailing Tightening (Secondary)
**Commit `3f2effe` (Aug 10)**
```
TRAILING_DISTANCE_PCT: 0.7% → 0.3%
```
**Impact:** Winners capped at 0.3% profit before the bounce fully plays out

Risk:reward became unfavorable. Even when the signal was right, the trailing cut the profit before it materialized.

### Factor 3: Velocity Gate (Contributing)
**Commit `33b6670` (Aug 9)**
```
MEAN_REVERSION_VEL_ENABLED = True
Blocks LONG when 15m vel < -0.3%
```
**Impact:** Changed signal distribution. Backtest showed 140→127 signals, 55%→59.1% WR on historical data. But changed behavior in current market regime.

### Factor 4: Volatility Gate (Current Blocker)
**Commits `f14762b` through `aba2351` (Aug 11)**
- Regime-based signal filtering
- `REGIME_SIGNALS` whitelist too narrow
- **Currently blocking ALL signals** — 0 entries
- System is frozen

### Factor 5: COSIG-GATE Poison Block (Wrong Timing)
**Commit `9a8d574` (Aug 11)**
- Poison-blocked `bb_bounce+,hzscore+` based on 23.1% WR
- But that WR was from the 0.5% SL era, not the current 1.2% SL era
- The signal was 80% WR 48h earlier under proper params

---

## Signal Performance Data

### All-Time Top Performers (≥5 trades)
| Signal | Trades | WR | Avg PnL | Net PnL |
|--------|--------|-----|---------|---------|
| bb_bounce,hzscore+ | 5 | 100% | +0.408 | +$0.22 |
| ma100-cross,vortex_break_long | 7 | 71.4% | +0.099 | +$0.09 |
| ma100-cross,return_exhaustion_long | 6 | 66.7% | +0.188 | +$0.13 |
| bb_bounce+,range_finder+ | 53 | 60.4% | +0.135 | +$0.82 |
| bb-bounce-short,hzscore- | 17 | 58.8% | +0.088 | +$0.17 |
| hzscore+,return_exhaustion_long | 12 | 58.3% | +0.121 | +$0.18 |
| continuation+,hzscore+ | 7 | 57.1% | +0.289 | +$0.22 |

### Period Comparison: bb_bounce+,hzscore+
| Period | Trades | WR | Net PnL |
|--------|--------|-----|---------|
| Aug 1-7 | 0 | — | — |
| Aug 8-10 | 29 | 51.7% | +$0.39 |
| Aug 11+ | 4 | 25.0% | -$0.08 |

### Period Comparison: bb_bounce+,range_finder+
| Period | Trades | WR | Net PnL |
|--------|--------|-----|---------|
| Aug 1-7 | 6 | 83.3% | +$0.14 |
| Aug 8-10 | 47 | 57.4% | +$0.68 |

### Daily WR Trend
```
Aug 01: 23.5%  ← trending market, momentum signals dying
Aug 02:  8.7%
Aug 03:  6.3%
Aug 04:  3.1%  ← rock bottom
Aug 05: 52.5%  ← PIVOT: market compressed, signals adapted
Aug 06: 56.1%
Aug 07: 62.5%  ← peak
Aug 08: 43.6%
Aug 09: 60.0%
Aug 10: 44.6%  ← SL tightening day
Aug 11: 40.0%  ← system frozen
```

### Token Performance (Aug 1-11)
**Top Winners:**
| Token | Trades | WR | Net PnL |
|-------|--------|-----|---------|
| LTC | 9 | 88.9% | +$0.25 |
| WLFI | 7 | 85.7% | +$0.15 |
| BSV | 11 | 72.7% | +$0.64 |
| JUP | 15 | 73.3% | +$0.05 |
| W | 13 | 69.2% | +$0.12 |

**Top Losers:**
| Token | Trades | WR | Net PnL |
|-------|--------|-----|---------|
| AAVE | 23 | 26.1% | -$0.88 |
| AVAX | 11 | 18.2% | -$0.60 |
| VINE | 8 | 37.5% | -$0.53 |
| GALA | 10 | 0.0% | -$0.51 |
| KAITO | 15 | 40.0% | -$0.54 |

### Last 12 Hours (Aug 10 18:06 — Aug 11 10:01)
| Metric | Pre-Gate (18:06-03:08) | Post-Gate (03:08-10:01) |
|--------|----------------------|------------------------|
| Trades | 9 | 9 |
| Wins | 2 (22%) | 3 (33%) |
| Net P&L | -$0.24 | -$0.11 |
| Avg P&L/Trade | -$0.027 | -$0.012 |

**By Exit Reason:**
| Exit | Pre-Gate | Post-Gate |
|------|----------|-----------|
| profit-monster-trail | 2/2 wins (+$0.11) | 3/3 wins (+$0.08) |
| atr_sl_hit | 0/7 wins (-$0.35) | 0/6 wins (-$0.19) |

---

## Current System State

### Volatility Gate Status
- **Deployed:** 2026-08-11 03:08 UTC
- **Status:** BLOCKING ALL SIGNALS — 0 entries
- **Reason:** `REGIME_SIGNALS` whitelist too narrow
- **Affected tokens:** W, WLFI, ETH, AVNT, MNT, CC — all blocked

### ATR SL Settings (Current)
```
ATR_SL_MIN:         0.012 (1.2%)  ← reverted from 0.5%
ATR_SL_MAX:         0.025 (2.5%)  ← reverted from 1.0%
TRAILING_DISTANCE:  0.006 (0.6%)  ← from 0.7% originally
SL_PCT_FALLBACK:    0.012 (1.2%)
```

### Blacklists Updated
- MEGA added to both SHORT and LONG blacklists (5T, 0% WR, -$0.23)

### Loss Cooldowns (23 tokens)
ETH (LONG+SHORT), W (LONG+SHORT), ALGO, HBAR, XRP, DYDX, ASTER, LTC, and more

### Open Positions
**ZERO** — system fully idle due to volatility gate blocking everything

---

## Action Plan

### Immediate (Today)
1. **Fix volatility gate whitelist** — expand `REGIME_SIGNALS` so signals can enter
2. **Remove COSIG-GATE poison block** on `bb_bounce+,hzscore+` — the data was from the 0.5% SL era
3. **Verify BTC candle gap** — price collector stopped at May 28, may affect BTC-paired ATR calculations (BTC is blacklisted, low priority)

### Short-Term (This Week)
4. **Monitor `bb_bounce+,hzscore+` at 1.2% SL** — should recover to ~50-60% WR
5. **Evaluate velocity gate impact** — may be filtering good entries
6. **Review trailing distance** — 0.60% vs original 0.70%, find optimal for mean-reversion

### Medium-Term (Next 2 Weeks)
7. **Regime-adaptive SL** — automatically widen SL in flat/compressed markets
8. **Signal-regime matching** — ensure `bb_bounce+` combos only fire in appropriate ATR regimes
9. **Token quality scoring** — pre-filter tokens like MEGA (low-price noise) before signal generation
10. **Backtest `REGIME_SIGNALS`** with current params — validate the whitelist is correct

### Monitoring
11. **Track SL hit rate** — target <30% (currently 64.7% at 0.5%, should be ~18.8% at 1.2%)
12. **Track signal WR by regime** — ensure flat-market signals work in flat regimes
13. **Track volatility gate acceptance rate** — should be >50% of signals entering

---

## Key Metrics to Watch

| Metric | Current | Target | Notes |
|--------|---------|--------|-------|
| SL hit rate | 64.7% | <30% | Was 18.8% at 1.2% SL |
| Signal WR (bb_bounce+,hzscore+) | 25% | >50% | Was 80% at 1.2% SL |
| Volatility gate acceptance | 0% | >50% | Currently frozen |
| Open positions | 0 | 1-3 | System idle |
| Daily trades | 10 | 30-60 | Volume dropped |

---

## Git References

| Commit | Date | Description |
|--------|------|-------------|
| `33b6670` | Aug 9 20:00 | Velocity gate added |
| `3f2effe` | Aug 10 15:14 | Trailing tightened 0.7% → 0.3% |
| `36e4cd0` | Aug 10 18:33 | SL tightened 1.2% → 0.5% |
| `f7a3152` | Aug 11 05:22 | SL reverted to 1.2% |
| `f14762b` | Aug 11 03:08 | Volatility gate deployed |
| `5e433d5` | Aug 11 03:18 | Volatility gate bug fixes |
| `4a4c2f5` | Aug 11 03:29 | Signal-aware regime matching |
| `9860cde` | Aug 11 03:35 | Data-driven regime mappings |
| `aba2351` | Aug 11 04:12 | REGIME_SIGNALS updated from 30d backtest |
| `9a8d574` | Aug 11 13:52 | COSIG-GATE poison block |
