=== Signal Performance Report ===
Generated: 2026-08-08 14:00 UTC

Period: Last 6h | 24h | 7d

---

## KILLED (executed)

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| range_finder- | SHORT | 40.0% | -$0.19 | 5 (7d) | DISABLED — compound ma100-cross-,range_finder- bleeding |
| vortex_break_short | SHORT | 25.0% | -$0.15 | 4 (7d) | DISABLED — compound ma100-cross-,vortex_break_short bleeding |

## ALREADY DISABLED (confirmed dead)

| Signal | Dir | WR | PnL | Trades | Killed |
|--------|-----|-----|-----|--------|--------|
| inv-accel-300- | SHORT | 26.7% | -$0.33 | 15 (7d) | 2026-08-04 (NEVER_REENABLE) |
| zscore-rising- | SHORT | 31.6% | -$0.22 | 38 (7d) | 2026-08-07 |
| hzscore- | SHORT | 15.8% | -$53.50 | 76 (7d) | 2026-08-07 |
| return_exhaustion- | SHORT | 14 trades | -$0.64 | combos | 2026-08-08 |
| ma100-cross- | SHORT | 40.0% | -$0.31 | 24h | 2026-08-08 |
| vel-hermes- | SHORT | 34.6% | -$0.06 | 52 (7d) | signal_decay_detector |
| bb_bounce- | SHORT | 40.0% | -$4.61% | 7d | 2026-08-07 |
| pattern_wolf_wave_bear | SHORT | 20.0% | -$0.16 | 5 (7d) | 2026-08-05 |
| pattern_scanner | SHORT | 0.0% | -$0.14 | 3 (7d) | permanently dead |

## WATCH LIST

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pct-hermes- | SHORT | 33.3% | -$0.03 | 3 (7d) | Borderline — best SHORT in combos (hzscore+,pct-hermes-,vel-hermes-). Monitor. |
| return_exhaustion-,vortex_break_short | SHORT | 66.7% | +$0.01 | 3 (7d) | OK — vortex_break SHORT now disabled, won't fire |

## WINNERS

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb_bounce+,range_finder+ | LONG | 75.0% | +$0.51 | 12 (24h) | HOT — top performer |
| bb_bounce,hzscore+ | LONG | 100.0% | +$0.20 | 5 (7d) | HOT — perfect WR |
| bb_bounce | LONG | 80.0% | +$0.15 | 5 (7d) | Strong |
| hzscore+,return_exhaustion_long | LONG | 58.3% | +$0.13 | 12 (7d) | Solid |
| bb_bounce+,ma100-cross+ | LONG | 66.7% | +$0.06 | 3 (24h) | OK |
| ma100-cross+,vortex_break_long | LONG | 62.5% | +$0.08 | 8 (7d) | OK |
| bb_bounce+,range_finder+ | LONG | 66.7% | +$0.20 | 3 (6h) | Active winner |

## 24h OVERALL

| Metric | Value |
|--------|-------|
| Total trades | 42 |
| Win rate | 61.9% |
| Net PnL | +$0.52 |

## DIRECTION INVERSIONS

None found.

## NOTES

- SHORT side is broadly negative. Most SHORT signals are disabled or bleeding.
- LONG side is carrying the system — bb_bounce+ combinations are consistently profitable.
- The compound signal name format (e.g. `ma100-cross-,range_finder-`) reflects which signals fired together, not a single signal source.
- `pct-hermes-` is borderline (33% WR, -$0.03) but appears in the best-performing SHORT combo (hzscore+,pct-hermes-,vel-hermes-). Leaving enabled for now.
- All kills committed to `scripts/hermes_constants.py`.
