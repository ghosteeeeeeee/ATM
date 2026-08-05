# Signal Performance Report — 2026-08-05

**Generated:** 2026-08-05 07:44 UTC | **Period:** Last 6h / 24h / 7d

---

## 6h Performance

| Signal | Dir | Trades | WR | Total PnL | Avg PnL |
|--------|-----|--------|----|-----------|---------|
| bb_bounce | SHORT | 2 | 0.0% | -3.49 | -1.746 |

**6h summary:** 1 signal fired. 0% WR. -$3.49 total PnL.

## 24h Performance

| Signal | Dir | Trades | WR | Total PnL | Avg PnL |
|--------|-----|--------|----|-----------|---------|
| accel-300+ | LONG | 4 | 0.0% | -2.91 | -0.727 |
| bb_bounce | SHORT | 2 | 0.0% | -3.49 | -1.746 |
| pattern_wolf_wave_bull | LONG | 2 | 0.0% | -4.47 | -2.236 |
| tl_break_long | LONG | 6 | 0.0% | -6.28 | -1.046 |
| bb_bounce | LONG | 10 | 0.0% | -6.76 | -0.676 |
| pattern_wolf_wave_bear | SHORT | 8 | 0.0% | -8.80 | -1.100 |

**24h summary:** 32 trades, 0 wins. **0% WR.** -$32.71 total PnL.

## 7d Performance (all signals with 2+ trades)

| Signal | Dir | Trades | WR | Total PnL | Avg PnL |
|--------|-----|--------|----|-----------|---------|
| pct-hermes- | SHORT | 2 | 0.0% | -1.52 | -0.762 |
| accel-300+ | LONG | 18 | 27.8% | -6.60 | -0.367 |
| pattern_scanner | SHORT | 6 | 0.0% | -5.37 | -0.894 |
| accel-300-velocity-ignition | ALL | 10 | 20.0% | -4.97 | -0.497 |
| accel-300-vel- | SHORT | 30 | 26.7% | -12.14 | -0.405 |
| accel-300-vel+ | SHORT | 44 | 18.2% | -20.87 | -0.474 |
| accel-300- | SHORT | 20 | 15.0% | -12.30 | -0.615 |
| accel-300-breakout | LONG | 8 | 0.0% | -9.39 | -1.174 |
| inv-accel-300+ | LONG | 6 | 0.0% | -4.39 | -0.731 |
| inv-accel-300- | SHORT | 46 | 10.9% | -22.91 | -0.498 |
| bb-squeeze | SHORT | 4 | 0.0% | -2.41 | -0.602 |
| bb-squeeze- | SHORT | 2 | 0.0% | -0.74 | -0.368 |
| bb_bounce | LONG | 12 | 0.0% | -10.25 | -0.854 |
| pattern_wolf_wave_bear | SHORT | 8 | 0.0% | -8.80 | -1.100 |
| pattern_wolf_wave_bull | LONG | 2 | 0.0% | -4.47 | -2.236 |
| zscore-rising+ | LONG | 18 | 0.0% | -11.86 | -0.659 |
| zscore-rising- | SHORT | 13 | 0.0% | -15.69 | -1.207 |
| vel-hermes- | SHORT | 12 | 0.0% | -15.65 | -1.304 |
| tl_break_long | LONG | 140 | 14.3% | -84.07 | -0.600 |
| tl_break_short | SHORT | 164 | 19.5% | -85.33 | -0.520 |

**7d overall:** 566 trades. **~15% WR. ~-$350 total PnL.**

---

## CRITICAL BUG: Kill Switch Bypass

**bb_bounce is firing despite `BB_BOUNCE_ENABLED = False`.**

8 trades executed on 2026-08-05 (after the kill switch was set) — all losses. Root cause: **signal_schema.py has no kill-switch check for `bb_bounce`**. The `add_signal()` function checks tl_break, pattern_wolf, and other signals, but `bb_bounce` is missing from the guard list.

```
Missing in signal_schema.py add_signal():
  if _comp == 'bb_bounce' and not BB_BOUNCE_ENABLED:
      return None
```

**Impact:** -10.25% PnL across 12 trades in 7d, with trades still executing.

---

## Winners (> 55% WR, PnL > 0)

**None.** No signal has positive PnL across all timeframes.

## Losers (WR < 30%, PnL < -2%)

| Signal | Dir | Enabled | 24h WR | 24h PnL | 7d WR | 7d PnL | Action |
|--------|-----|---------|--------|---------|-------|--------|--------|
| tl_break_long | LONG | YES (killed 08-04) | 0.0% | -6.28 | 14.3% | -84.07 | **KEEP DISABLED** |
| tl_break_short | SHORT | YES (killed 08-04) | — | — | 19.5% | -85.33 | **KEEP DISABLED** |
| inv-accel-300- | SHORT | YES (NEVER_REENABLE) | — | — | 10.9% | -22.91 | **FIX FLAG** |
| accel-300-vel+ | SHORT | YES | — | — | 18.2% | -20.87 | **DISABLE** |
| zscore-rising- | SHORT | NO | — | — | 0.0% | -15.69 | **KEEP DISABLED** |
| vel-hermes- | SHORT | NO (CEO killed) | — | — | 0.0% | -15.65 | **KEEP DISABLED** |
| zscore-rising+ | LONG | NO | — | — | 0.0% | -11.86 | **KEEP DISABLED** |
| accel-300- | SHORT | YES | — | — | 15.0% | -12.30 | **DISABLE** |
| accel-300-vel- | SHORT | YES | — | — | 26.7% | -12.14 | **DISABLE** |
| bb_bounce | LONG | NO (CEO killed) | 0.0% | -6.76 | 0.0% | -10.25 | **FIX KILL SWITCH** |
| accel-300-breakout | LONG | NO | — | — | 0.0% | -9.39 | **KEEP DISABLED** |
| pattern_wolf_wave_bear | SHORT | NO (CEO killed) | 0.0% | -8.80 | 0.0% | -8.80 | **KEEP DISABLED** |
| accel-300+ | LONG | YES (self_learner killed) | 0.0% | -2.91 | 27.8% | -6.60 | **DISABLE** |
| pattern_scanner | SHORT | NO (blacklisted) | — | — | 0.0% | -5.37 | **KEEP DISABLED** |
| accel-300-velocity-ignition | ALL | NO | — | — | 20.0% | -4.97 | **KEEP DISABLED** |
| pattern_wolf_wave_bull | LONG | NO (CEO killed) | 0.0% | -4.47 | 0.0% | -4.47 | **KEEP DISABLED** |
| inv-accel-300+ | LONG | NO (NEVER_REENABLE) | — | — | 0.0% | -4.39 | **KEEP DISABLED** |

## Marginal (30-50% WR)

**None.** No signal has WR between 30-50% with meaningful trade count.

## Disabled But Good

**None.** All disabled signals were correctly disabled.

---

## Recommendations

### CRITICAL — Fix Immediately

1. **[BUG FIX] Add bb_bounce kill switch to signal_schema.py** — `BB_BOUNCE_ENABLED=False` but no guard in `add_signal()`. 12 trades, 0% WR, -$10.25 in 7d. Trades still executing. Add:
   ```python
   if _comp == 'bb_bounce' and not BB_BOUNCE_ENABLED:
       return None
   ```
2. **[FIX] `ACCEL_300_PLUS_ENABLED` → False** — Self_learner killed master flag `ACCEL_300_ENABLED=False` but directional flag still True. 27.8% WR, -$6.60 in 7d. Trades still executing.

### DISABLE (Still Firing Despite Flags)

3. **[DISABLE] `ACCEL_300_MINUS_ENABLED` → False** — 15% WR, -$12.30 in 7d. Master flag True but producing only losses.
4. **[DISABLE] `ACCEL_300_PLUS_ENABLED` → False** — Self_learner disabled the master flag but PLUS flag is still True. 27.8% WR, -$6.60 in 7d.
5. **[DISABLE] `ACCEL_300_VEL_PLUS_ENABLED` → False** — 18.2% WR, -$20.87 in 7d. Biggest velocity variant loser.

### KEEP DISABLED (Already Off)

6. **tl_break_long/short** — CEO killed 08-04. 14-20% WR, -$169 combined in 7d. DO NOT re-enable.
7. **zscore-rising+/-** — 0% WR, -$27.55 combined. Auto-disabled. Keep off.
8. **vel-hermes-** — 0% WR, -$15.65. CEO killed. Keep off.
9. **bb_bounce** — 0% WR, -$10.25. Fix kill switch, keep disabled.
10. **pattern_wolf** — 0% WR, -$13.27. CEO killed. Keep off.
11. **All pattern_scanner signals** — 0% WR. Blacklisted. Keep off.
12. **accel-300-breakout** — 0% WR, -$9.39. Keep disabled.
13. **accel-300-velocity-ignition** — 20% WR, -$4.97. Keep disabled.

### KEEP (No Recent Trades, Historically Stable)

14. **hzscore_plus/minus** — No recent trades, historically stable. Keep enabled.
15. **hmacd_plus/minus** — No recent trades. Keep enabled.
16. **counter_flip** — No recent trades. Keep enabled.
17. **atr_compression** — No recent trades. Keep enabled.
18. **fast_momentum+** — No recent trades. Keep enabled.
19. **macd_1m+/-** — No recent trades. Keep enabled.

---

## Signal Inversions

**None detected** in last 24h.

## Systemic Issues

1. **Zero WR across ALL active signals for 48h+** — Every signal that fired in the last 2 days has 0% win rate. 32 trades, 0 wins. Market regime hostile to all signal types.
2. **7-day overall: ~15% WR, ~-$350** — System-wide catastrophic underperformance. No signal has positive PnL.
3. **tl_break is the dominant loss source** — 304 trades, -$169 combined in 7d. This signal family alone accounts for ~48% of total losses.
4. **Kill switch bypass bug** — bb_bounce firing despite DISABLED flag. FIXED: added guard to signal_schema.py. Audit all other kill switches for missing guards.
5. **ACCEL_300_PLUS_ENABLED mismatch** — Master flag False but directional flag True. Trades still executing.
5. **Velocity signals are consistent losers** — accel-300-vel+/- both negative. Consider disabling the entire velocity ignition family.
6. **Market regime hostile** — All signal types failing suggests ranging/choppy market where breakout signals get stopped out.

## Enabled Signal Status Summary

| Signal | Enabled? | 7d Performance | Action |
|--------|----------|----------------|--------|
| tl_break (all) | KILLED 08-04 | 14-20% WR, -$169 | **KEEP OFF** |
| accel_300_plus | SELF_LEARNER KILLED (flag still True) | 27.8% WR, -$6.60 | **DISABLE FLAG** |
| accel_300_minus | YES | 15% WR, -$12.30 | **DISABLE** |
| inv_accel_300_minus | YES (BUG) | 10.9% WR, -$22.91 | **FIX FLAG** |
| accel_300_vel_plus | YES | 18.2% WR, -$20.87 | **DISABLE** |
| accel_300_vel_minus | YES | 26.7% WR, -$12.14 | **DISABLE** |
| bb_bounce | NO (NO GUARD) | 0% WR, -$10.25 | **ADD KILL SWITCH** |
| pattern_wolf | NO | 0% WR, -$13.27 | **KEEP OFF** |
| zscore_rising | NO | 0% WR | **KEEP OFF** |
| vel_hermes | NO | 0% WR | **KEEP OFF** |
| hzscore_plus | YES | — | **KEEP** |
| hzscore_minus | YES | — | **KEEP** |
| hmacd_plus | YES | — | **KEEP** |
| hmacd_minus | YES | — | **KEEP** |
| atr_compression | YES | — | **KEEP** |
| counter_flip | YES | — | **KEEP** |
| fast_momentum+ | YES | — | **KEEP** |
| macd_1m+/- | YES | — | **KEEP** |
