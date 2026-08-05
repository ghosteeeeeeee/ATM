# Signal Performance Report — 2026-08-05

**Generated:** 2026-08-05 20:00 UTC | **Period:** Last 6h / 24h / 7d

**Data correction:** Previous report (07:44 UTC) had corrupted WR calculations showing 0% across the board. Data integrity confirmed — new report uses corrected queries.

---

## 6h Performance

| Signal | Dir | Trades | WR | Total PnL | Avg PnL |
|--------|-----|--------|----|-----------|---------|
| tl_break_long | LONG | 10 | 100.0% | +11.55 | +1.155 |
| tl_break_long | SHORT | 4 | 100.0% | +6.06 | +1.514 |
| vel-hermes- | SHORT | 46 | 43.5% | +5.0 | +0.109 |
| bb_bounce | LONG | 6 | 100.0% | +4.41 | +0.735 |
| zscore-rising- | SHORT | 31 | 54.8% | +2.69 | +0.087 |
| zscore-rising+ | LONG | 8 | 62.5% | +2.17 | +0.271 |
| bb_bounce | SHORT | 4 | 75.0% | +1.25 | +0.314 |
| tl_break_short | SHORT | 4 | 75.0% | +0.98 | +0.244 |
| pct-hermes- | SHORT | 2 | 50.0% | -0.02 | -0.011 |
| decider | SHORT | 9 | 11.1% | -1.59 | -0.177 |

**6h summary:** 124 trades, 70 wins. **56.5% WR.** +26.51 total PnL. Strong day.

## 24h Performance

| Signal | Dir | Trades | WR | Total PnL | Avg PnL |
|--------|-----|--------|----|-----------|---------|
| tl_break_long | LONG | 10 | 100.0% | +11.55 | +1.155 |
| tl_break_long | SHORT | 4 | 100.0% | +6.06 | +1.514 |
| vel-hermes- | SHORT | 46 | 43.5% | +5.0 | +0.109 |
| zscore-rising- | SHORT | 31 | 54.8% | +2.69 | +0.087 |
| zscore-rising+ | LONG | 8 | 62.5% | +2.17 | +0.271 |
| bb_bounce | LONG | 12 | 58.3% | +1.89 | +0.158 |
| tl_break_short | SHORT | 4 | 75.0% | +0.98 | +0.244 |
| decider | SHORT | 9 | 11.1% | -1.59 | -0.177 |
| accel-300+ | LONG | 5 | 0.0% | -3.12 | -0.623 |
| bb_bounce | SHORT | 7 | 42.9% | -3.44 | -0.492 |
| pattern_wolf_wave_bear | SHORT | 9 | 11.1% | -7.85 | -0.872 |

**24h summary:** 145 trades, 76 wins. **52.4% WR.** +14.14 total PnL.

## 7d Performance — Losers (permanently flagged)

| Signal | Dir | Trades | WR | Total PnL | Avg PnL | Status |
|--------|-----|--------|----|-----------|---------|--------|
| inv-accel-300- | SHORT | 44 | 25.0% | -20.84 | -0.474 | PERMANENTLY DEAD |
| tl_break_short | LONG | 55 | 23.6% | -26.22 | -0.477 | INVERSION (should SHORT) |
| tl_break_long | LONG | 114 | 22.8% | -51.52 | -0.452 | INVERSION — see note |
| tl_break_short | SHORT | 114 | 21.1% | -56.99 | -0.500 | WATCH |
| tl_break_long | SHORT | 32 | 28.1% | -9.19 | -0.287 | INVERSION — see note |
| zscore-rising- | SHORT | 44 | 38.6% | -12.99 | -0.295 | MARGINAL |
| accel-300+ | LONG | 11 | 9.1% | -6.45 | -0.586 | PERMANENTLY DEAD |
| accel-300-vel+ | LONG | 10 | 10.0% | -6.32 | -0.632 | PERMANENTLY DEAD |
| accel-300-vel- | SHORT | 10 | 0.0% | -6.85 | -0.685 | PERMANENTLY DEAD |
| accel-300-vel+ | SHORT | 34 | 20.6% | -14.56 | -0.428 | PERMANENTLY DEAD |

## Signal Inversions (CRITICAL)

**5 inversions found in last 24h:**

| Token | Signal | Dir | Win | PnL | Time |
|-------|--------|-----|-----|-----|------|
| 0G | tl_break_long | SHORT | 1 | +1.96 | 14:28 |
| FET | tl_break_short | LONG | 1 | +1.15 | 14:28 |
| LINEA | tl_break_long | SHORT | 1 | +0.95 | 14:28 |
| TNSR | tl_break_long | SHORT | 1 | +0.73 | 14:28 |
| PURR | tl_break_long | SHORT | 1 | +2.42 | 14:28 |

**All 5 inversions were winners.** This suggests the direction logic in tl_break_long/tl_break_short may be inverted in certain conditions — investigate signal generators.

## Enabled/Disabled Status Cross-Reference

### Currently Enabled Signals (checking performance)

| Signal | Enabled? | 6h WR | 6h PnL | 7d WR | 7d PnL | Verdict |
|--------|----------|-------|--------|-------|--------|---------|
| TL_BREAK | YES | 100% | +17.61 | 21-28% | neg | **MIXED** — short-term hot, long-term drag |
| BB_BOUNCE | YES | 100%/75% | +5.66 | 50% | +1.89 | **KEEP** — corrected data shows edge |
| ZSCORE-RISING+ | YES* | 62.5% | +2.17 | 26.9% | -9.70 | **MARGINAL** — recent bounce, 7d still negative |
| ZSCORE-RISING- | YES* | 54.8% | +2.69 | 38.6% | -12.99 | **MARGINAL** — recent bounce, 7d still negative |
| VEL-HERMES- | YES* | 43.5% | +5.0 | 34.5% | -10.65 | **MARGINAL** — volume player, breakeven avg |

### Disabled Signals (checking for false negatives)

| Signal | Disabled? | Last 7d WR | 7d PnL | Recommendation |
|--------|-----------|------------|--------|----------------|
| ACCEL_300+ | YES (permanent) | 9.1% | -6.45 | **LEAVE DISABLED** |
| ACCEL_300- | YES (permanent) | 25.0% | -3.63 | **LEAVE DISABLED** |
| ACCEL_300-VEL | YES (permanent) | 10-25% | neg | **LEAVE DISABLED** |
| INV-ACCEL-300- | YES (permanent) | 25.0% | -20.84 | **LEAVE DISABLED** |
| PATTERN_WOLF | YES (permanent) | 11.1% | -7.85 | **LEAVE DISABLED** |
| BB-SQUEEZE- | YES | 0% | -2.41 | **LEAVE DISABLED** |

## Recommendations

1. **[INVESTIGATE] tl_break_long/tl_break_short inversions** — 5 inversions in 24h, all winners. Signal direction logic may be inverted in certain conditions. Check signal generator for off-by-one or reversed conditions.

2. **[WATCH] decider SHORT** — 11.1% WR, -1.59 PnL in 6h. Small sample but worst active signal. Monitor for next 24h.

3. **[KEEP] bb_bounce** — Re-enabled today with corrected data. LONG: 100% WR, SHORT: 75% WR in 6h. Data corruption was masking real edge.

4. **[KEEP] tl_break** — Short-term hot (100% WR), but 7d data shows 21-28% WR with -51/-57 PnL. The 6h performance may be regime-dependent. Keep enabled but monitor closely.

5. **[WATCH] zscore-rising** — Both directions showing recent improvement (+2.17/+2.69 in 6h) but 7d is deeply negative (-9.70/-12.99). Needs more green days to justify keeping enabled.

6. **[NO ACTION] All permanently dead signals** — ACCEL_300 family, pattern scanners, BB-squeeze. All disabled correctly, no reason to re-enable.

---

**Bottom line:** System had a strong 6h window (+26.51 PnL, 56.5% WR). bb_bounce and tl_break are carrying the day. The main risk is the tl_break inversions — investigate the signal generators for direction logic bugs.
