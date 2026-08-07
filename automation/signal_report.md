# Signal Performance Report — 2026-08-07

## Summary

| Window | Trades | Wins | WR% | Total PnL |
|--------|--------|------|-----|-----------|
| 6h     | 17     | 13   | 76.5% | +2.65%  |
| 24h    | 58     | 34   | 58.6% | +0.45%  |

No signal inversions detected.

---

## WINNERS (WR > 55%, PnL > 0, 24h)

| Signal | Dir | 6h | 24h | 7d | Status |
|--------|-----|----|-----|----|--------|
| hzscore+,return_exhaustion_long | LONG | — | 5/5 60%, +0.59 | 7/12 58%, +1.46 | KEEP |
| bb_bounce,hzscore+ | LONG | — | 2/2 100%, +0.77 | 5/5 100%, +2.04 | KEEP |
| ma100-cross,return_exhaustion_long | LONG | — | 1/1 100%, +0.39 | 4/6 67%, +1.13 | KEEP |
| ma100-cross,vortex_break_long | LONG | — | 1/2 50%, -0.13 | 5/7 71%, +0.69 | KEEP |
| ma100-cross,range_finder | SHORT | — | 2/4 50%, +0.06 | 3/5 60%, +0.49 | KEEP |

## MARGINAL (30-50% WR or mixed)

| Signal | Dir | 6h | 24h | 7d | Status |
|--------|-----|----|-----|----|--------|
| bb_bounce,range_finder | LONG | 1/2 50%, -0.19 | 3/7 43%, -0.0 | 3/7 43%, -0.0 | WATCH |
| bb_bounce+,range_finder+ | LONG | 3/4 75%, -0.08 | 3/4 75%, -0.08 | — | WATCH |
| bb_bounce,ma100-cross | LONG | — | 3/7 43%, -1.33 | 3/7 43%, -1.33 | WATCH |
| ma100-cross,return_exhaustion- | SHORT | — | 2/3 67%, -0.45 | 3/7 43%, -2.76 | WATCH |
| hzscore-,return_exhaustion- | SHORT | — | 0/2 0%, -1.23 | 5/10 50%, -1.86 | WATCH |

## LOSERS (7d, WR < 30%, PnL < 0)

| Signal | Dir | 7d WR | 7d PnL | Status |
|--------|-----|-------|--------|--------|
| inv-accel-300- | SHORT | 18.8% (6/32) | -19.85 | DISABLED ✅ |
| zscore-rising+ | LONG | 26.9% (7/26) | -9.70 | DISABLED ✅ |
| zscore-rising- | SHORT | 38.6% (17/44) | -12.99 | DISABLED ✅ |
| vel-hermes- | SHORT | 34.5% (20/58) | -10.65 | DISABLED ✅ |
| accel-300+ | LONG | 0% (0/7) | -4.44 | DISABLED ✅ |
| accel-300-breakout | LONG | 0% (0/6) | -6.56 | DISABLED ✅ |
| pattern_wolf_wave_bear | SHORT | 11.1% (1/9) | -7.85 | DISABLED ✅ |
| pattern_scanner | SHORT | 0% (0/5) | -4.38 | DISABLED ✅ |

All worst performers already disabled via NEVER_REENABLE_FLAGS or kill switches.

## Worst Tokens (24h)

| Token | Trades | WR | PnL | Notes |
|-------|--------|----|-----|-------|
| TNSR | 3 | 33.3% | -2.52% | Multiple losing signals |
| VINE | 2 | 0% | -1.49% | Both trades lost |
| AAVE | 4 | 50% | -1.43% | Win size < loss size |

## Best Tokens (24h)

| Token | Trades | WR | PnL |
|-------|--------|----|-----|
| AVNT | 2 | 100% | +2.11% |
| MNT | 2 | 50% | +1.02% |
| ME | 3 | 100% | +0.96% |
| LTC | 3 | 100% | +0.84% |
| ENS | 4 | 75% | +0.83% |

---

## Recommendations

1. **KEEP** — `hzscore+,return_exhaustion_long` — best 24h signal (+0.59% PnL, 60% WR). Enabled and performing.
2. **KEEP** — `bb_bounce,hzscore+` — 100% WR confluence combo. Enabled.
3. **KEEP** — `ma100-cross` family — all variants profitable. Enabled.
4. **KEEP** — `vortex_break` family — mixed but net positive. Enabled.
5. **WATCH** — `bb_bounce,ma100-cross` LONG — 43% WR, -1.33% PnL over 24h. If this continues, consider disabling `bb_bounce` LONG variant when combined with ma100-cross.
6. **WATCH** — `hzscore-,return_exhaustion-` SHORT — 0% WR in 24h (2 trades). Small sample, but -1.23% PnL. Monitor.
7. **NO ACTION NEEDED** — All historically bad signals already disabled (inv-accel-300, zscore-rising, vel-hermes, accel-300, pattern_scanner, pattern_wolf).

---

*Generated: 2026-08-07 | Next report: ~6h*
