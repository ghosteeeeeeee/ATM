# Signal Performance Report
**Generated:** 2026-09-17 05:09 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (24h):** 22 | **System PnL:** -$0.20
- **Total trades (all time):** 5,103

---

## KILLED (executed)

None. No signals meet kill criteria (WR <30% with 5+ trades in 24h).

---

## BOOSTED (executed)

None. No signals meet boost criteria (WR >55%, 5+ trades, PnL >$0.05 in 24h).

---

## LOSERS (watch list)

| Signal | Dir | Trades | WR | PnL | Avg PnL | Status |
|--------|-----|--------|-----|-----|---------|--------|
| pullback-entry- | SHORT | 12 | 33.3% | -$0.16 | -$0.01 | TUNE — historically profitable all regimes, bad 24h streak |
| volume-breakout-long+ | LONG | 3 | 0.0% | -$0.10 | -$0.03 | WATCH — low sample, losses from SNIPER exits |
| rs-s36,volume-breakout-long+ | LONG | 1 | 0.0% | -$0.22 | -$0.22 | WATCH — single trade, insufficient data |

---

## WINNERS

| Signal | Dir | Trades | WR | PnL | Avg PnL | Status |
|--------|-----|--------|-----|-----|---------|--------|
| open-skies+ | LONG | 4 | 50.0% | +$0.14 | +$0.04 | OK — performing within expectations |
| r2-trend-short3 | SHORT | 1 | 100.0% | +$0.06 | +$0.06 | OK — single trade |
| mover- | SHORT | 1 | 100.0% | +$0.08 | +$0.08 | OK — single trade |

---

## REGIME ANALYSIS

### pullback-entry- SHORT (24h)
| Regime | Trades | WR | PnL |
|--------|--------|-----|-----|
| EXTREME | 3 | 100.0% | +$0.60 |
| HIGH | 6 | 16.7% | -$0.39 |
| NORMAL | 3 | 0.0% | -$0.37 |

**All-time (proven profitable):** EXTREME 70% WR (+$1.53), HIGH 54.3% (+$0.82), NORMAL 51.9% (+$0.14)

**Diagnosis:** Signal fires correctly in EXTREME (100% WR, +$0.60). Struggling in HIGH/NORMAL this period — all-time those regimes are profitable. Likely a bad streak, not structural. SNIPER exits cutting some winners (SNIPER-L1-BULLISH, SNIPER-L2-BULLISH).

### open-skies+ LONG (all-time)
| Regime | Trades | WR | PnL |
|--------|--------|-----|-----|
| EXTREME | 6 | 33.3% | -$0.35 |
| HIGH | 4 | 75.0% | +$0.18 |

**Diagnosis:** Wins in HIGH, struggles in EXTREME. No kill needed — 50% WR in 24h, small positive PnL.

### volume-breakout-long+ LONG (all-time)
| Regime | Trades | WR | PnL |
|--------|--------|-----|-----|
| EXTREME | 2 | 0.0% | -$0.04 |
| NORMAL | 1 | 0.0% | -$0.06 |

**Diagnosis:** Very low sample size. All losses from SNIPER-L3-BEARISH exits, not ATR SL. Needs more data before action.

---

## EXIT ANALYSIS (24h)

| Exit Reason | Count | Avg PnL | Notes |
|-------------|-------|---------|-------|
| SNIPER-L3-BEARISH | 5 | -$0.03 | Sniper bearish filter closing LONG trades |
| atr_sl_hit | 8 | +$0.01 | Break-even overall |
| SNIPER-L1-BULLISH | 2 | +$0.04 | Sniper bullish filter closing SHORT trades |
| SNIPER-L2-BULLISH | 1 | -$0.11 | |
| SNIPER-L3-BULLISH | 1 | -$0.07 | |
| HL_CLOSED | 1 | -$0.23 | |
| HARD_SL_FAILED | 1 | -$0.25 | Exchange issue? |
| hard_tp | 1 | +$0.34 | |

**Notable:** 5 SNIPER-L3-BEARISH exits on LONG trades — sniper bearish filter is aggressively closing longs. 2 SNIPER-L1/L2-BULLISH exits on SHORT trades — sniper bullish filter closing shorts. These sniper exits are the dominant source of losses.

---

## SIGNAL INVERSIONS

None detected.

---

## ISSUES

- **pullback-entry- SHORT HIGH/NORMAL underperformance:** All-time profitable (54.3% / 51.9%) but 24h shows 16.7% / 0%. Monitor next cycle — if persists 48h+, consider regime filter.
- **SNIPER exits dominating losses:** 10 of 22 trades (45%) exited by SNIPER filters, contributing most of the negative PnL. Consider reviewing SNIPER sensitivity.
- **volume-breakout-long+ 0% WR:** Only 3 trades, all SNIPER exits. Insufficient sample to act.
- **HARD_SL_FAILED on SEI (-$0.25):** Possible exchange execution issue. Worth logging.

---

## ACTIONS TAKEN

None. No kill/boost criteria met. All signals within acceptable variance.
