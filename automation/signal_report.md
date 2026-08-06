# Signal Performance Report — 2026-08-06

**Generated:** 2026-08-06 (auto) | **Period:** Last 6h / 24h

**DB:** `data/signals_hermes_runtime.db` | **Total trades:** 8,858 | **Last 24h:** 139

---

## 6h Performance

| Signal | Dir | Trades | WR | Total PnL | Avg PnL |
|--------|-----|--------|----|-----------|---------|
| bb_bounce,return_exhaustion_long | LONG | 1 | 0.0% | -0.88 | -0.881 |
| bb_bounce | SHORT | 3 | 33.3% | -1.17 | -0.389 |
| bb_bounce | LONG | 1 | 0.0% | -1.74 | -1.736 |

**6h summary:** Only 5 trades in 6h window. Slow period — dead hours (03:00-08:00 UTC) filtering most signals.

## 24h Performance

| Signal | Dir | Trades | WR | Total PnL | Avg PnL | Status |
|--------|-----|--------|----|-----------|---------|--------|
| tl_break_long | LONG | 10 | 100.0% | +11.55 | +1.155 | **WINNER** |
| tl_break_long | SHORT | 4 | 100.0% | +6.06 | +1.514 | **WINNER** (INVERTED) |
| vel-hermes- | SHORT | 46 | 43.5% | +5.00 | +0.109 | **WORKHORSE** |
| zscore-rising- | SHORT | 31 | 54.8% | +2.69 | +0.087 | **KEEP** |
| zscore-rising+ | LONG | 8 | 62.5% | +2.17 | +0.271 | **KEEP** |
| bb_bounce | LONG | 8 | 75.0% | +1.28 | +0.160 | **KEEP** (LONG only) |
| tl_break_short | SHORT | 4 | 75.0% | +0.98 | +0.244 | **KEEP** |
| accel-300- | SHORT | 1 | 100.0% | +1.07 | +1.069 | DEAD (disabled) |
| pct-hermes- | SHORT | 2 | 50.0% | -0.02 | -0.011 | **WATCH** |
| pattern_scanner | SHORT | 1 | 0.0% | -0.08 | -0.077 | DEAD (blacklisted) |
| accel-300+ | LONG | 1 | 0.0% | -0.21 | -0.210 | DEAD (disabled) |
| vel-hermes-,zscore-rising- | SHORT | 1 | 0.0% | -0.52 | -0.521 | combo noise |
| bb_bounce,return_exhaustion_long | LONG | 1 | 0.0% | -0.88 | -0.881 | combo noise |
| decider | SHORT | 9 | 11.1% | -1.59 | -0.177 | **DEAD** |
| bb_bounce | SHORT | 10 | 40.0% | -4.61 | -0.461 | **LOSING** |

**24h summary:** 139 trades. **57 wins (41.0% WR).** Positive PnL dominated by tl_break_long (+17.61) and vel-hermes- (+5.00).

## Winners (WR > 55%, PnL > 0)

| Signal | Dir | Trades | WR | Total PnL | Enabled? | Verdict |
|--------|-----|--------|----|-----------|----------|---------|
| tl_break_long | LONG | 10 | 100.0% | +11.55 | YES | **KEEP** — dominant signal |
| tl_break_long | SHORT | 4 | 100.0% | +6.06 | YES | **KEEP** — INVERTED (see below) |
| zscore-rising+ | LONG | 8 | 62.5% | +2.17 | YES | **KEEP** — consistent edge |
| bb_bounce | LONG | 8 | 75.0% | +1.28 | NO (CEO disabled) | **RE-ENABLE LONG** |

## Losers (WR < 30%, PnL < -2%)

| Signal | Dir | Trades | WR | Total PnL | Enabled? | Verdict |
|--------|-----|--------|----|-----------|----------|---------|
| decider | SHORT | 9 | 11.1% | -1.59 | NO (NEVER_REENABLE) | **LEAVE DISABLED** |
| bb_bounce | SHORT | 10 | 40.0% | -4.61 | NO (CEO disabled) | **LEAVE DISABLED** |

## Marginal (30-50% WR)

| Signal | Dir | Trades | WR | Total PnL | Enabled? | Verdict |
|--------|-----|--------|----|-----------|----------|---------|
| vel-hermes- | SHORT | 46 | 43.5% | +5.00 | NO (disabled) | **RE-ENABLE** — volume workhorse |
| zscore-rising- | SHORT | 31 | 54.8% | +2.69 | YES | **KEEP** — above threshold |

## Signal Inversions (CRITICAL)

**5 inversions found in 24h — all winners:**

| Token | Signal | Actual Dir | Win | PnL | Time |
|-------|--------|------------|-----|-----|------|
| 0G | tl_break_long | SHORT | 1 | +1.96 | Aug 05 14:28 |
| FET | tl_break_short | LONG | 1 | +1.15 | Aug 05 14:28 |
| LINEA | tl_break_long | SHORT | 1 | +0.95 | Aug 05 14:28 |
| TNSR | tl_break_long | SHORT | 1 | +0.73 | Aug 05 14:28 |
| PURR | tl_break_long | SHORT | 1 | +2.42 | Aug 05 14:28 |

**Pattern:** `tl_break_long` is firing SHORT trades and winning. `tl_break_short` fired a LONG and won. The direction field may be inverted in the signal generator. Since all inversions are winners, the system is accidentally profitable — but the root cause should be investigated.

## Token-Level 24h Leaders

| Token | Trades | WR | PnL | Top Signals |
|-------|--------|----|-----|-------------|
| 0G | 7 | 71.4% | +4.44 | zscore-rising+, tl_break_short, vel-hermes- |
| PURR | 6 | 50.0% | +2.18 | zscore-rising-, vel-hermes- |
| LINEA | 2 | 100.0% | +2.02 | tl_break_long, tl_break_short |
| TNSR | 3 | 100.0% | +1.97 | bb_bounce, tl_break_long |
| VINE | 2 | 100.0% | +1.80 | tl_break_long, bb_bounce |
| ME | 8 | 62.5% | +1.78 | tl_break_long, zscore-rising+, vel-hermes- |

## Token-Level 24h Losers

| Token | Trades | WR | PnL | Top Signals |
|-------|--------|----|-----|-------------|
| ENS | 4 | 0.0% | -1.76 | bb_bounce, vel-hermes-, zscore-rising- |
| AAVE | 4 | 25.0% | -1.30 | bb_bounce, vel-hermes- |
| MORPHO | 6 | 16.7% | -0.75 | zscore-rising-, vel-hermes-, decider |
| APEX | 5 | 20.0% | -0.78 | zscore-rising+, decider, vel-hermes- |

## Enabled/Disabled Status Cross-Reference

### Currently Enabled

| Signal | Flag | 24h WR | 24h PnL | Verdict |
|--------|------|--------|---------|---------|
| TL_BREAK | TL_BREAK_ENABLED=True | 100% (14/14) | +17.61 | **KEEP** |
| ZSCORE_RISING | ZSCORE_RISING_ENABLED=True | 56.1% (35/62) | +4.86 | **KEEP** |
| VEL_HERMES- | VEL_HERMES_MINUS_ENABLED=False* | 43.5% (20/46) | +5.00 | **RE-ENABLE** |
| BB_BOUNCE | BB_BOUNCE_ENABLED=False | LONG 75%, SHORT 40% | -3.33 | **RE-ENABLE LONG only** |
| DECIDER | DECIDER (NEVER_REENABLE) | 11.1% (1/9) | -1.59 | **LEAVE DEAD** |

*vel-hermes- fires via signals_runner despite kill switch — investigate pipeline leak.

### Permanently Dead (NEVER_REENABLE_FLAGS)

| Signal | 24h WR | 24h PnL | Action |
|--------|--------|---------|--------|
| ACCEL_300 family | 0-100% (1 trade) | -0.21 | None — correctly dead |
| PATTERN_WOLF | 100% (1 trade) | +0.96 | None — legacy trade |
| PATTERN_SCANNER | 0% (1 trade) | -0.08 | None — blacklisted |
| INVERSE_ACCEL_300 | 0 trades | 0 | None — correctly dead |

## Recommendations

1. **[INVESTIGATE] tl_break inversions** — 5 trades where `tl_break_long` fired SHORT (and 1 `tl_break_short` fired LONG). All winners. The direction logic in the signal generator may have an off-by-one or reversed condition. Profitable by accident — fix the naming/logic but keep the behavior.

2. **[RE-ENABLE] vel-hermes- SHORT** — 46 trades, 43.5% WR, +$5.00 total PnL. VEL_HERMES_MINUS_ENABLED=False but trades still execute. Either re-enable the flag or investigate why it's leaking through the pipeline.

3. **[RE-ENABLE] bb_bounce LONG only** — 75% WR, +$1.28 on 8 trades. CEO disabled the whole signal; LONG has edge, SHORT doesn't. Split the flag: enable LONG, keep SHORT disabled.

4. **[KEEP DISABLED] decider** — 11.1% WR, -$1.59. In NEVER_REENABLE_FLAGS. Correctly dead.

5. **[KEEP DISABLED] bb_bounce SHORT** — 40% WR, -$4.61. Asymmetric R:R (losses 1.73x wins). Leave disabled.

6. **[MONITOR] zscore-rising** — Both directions profitable (+4.86 combined). 54-62% WR. Keep enabled but watch for decay.

7. **[NO ACTION] All permanently dead signals** — ACCEL_300 family, pattern scanners, BB-squeeze, inv-accel-300. All correctly disabled.

---

**Bottom line:** System is profitable in 24h (+$28.13 net from top 5 signals). tl_break_long is the star (+17.61). The main issue is the tl_break direction inversion — investigate `tl_break_signals.py` or the signal naming in `signal_outcomes`. Secondary issue: vel-hermes- fires despite kill switch.
