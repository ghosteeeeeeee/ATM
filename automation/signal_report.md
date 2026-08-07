# Signal Performance Report — 2026-08-07

## Summary

| Period | Trades | WR | PnL |
|--------|--------|----|-----|
| 6h     | 14     | 28.6% | -3.83% |
| 24h    | 64     | 46.9% | -9.04% |
| 7d     | 358    | 44.1% | -13.74% |

**Active signals in registry:** 8 (bb_bounce, hzscore, ma_100_cross, momentum_leaderboard, range_finder, return_exhaustion, rs, vortex_break)

---

## WINNERS (WR > 55%, PnL > 0)

| Signal | Dir | 6h WR | 6h PnL | 24h WR | 24h PnL | 7d WR | 7d PnL | Status |
|--------|-----|-------|--------|--------|---------|-------|--------|--------|
| ma100-cross,return_exhaustion_long | LONG | — | — | 100.0% | +1.53% | 66.7% | +1.13% | **KEEP** |
| bb_bounce,hzscore+ | LONG | — | — | 100.0% | +0.77% | 100.0% | +2.04% | **KEEP** |
| ma100-cross,range_finder | SHORT | — | — | 60.0% | +0.49% | 60.0% | +0.49% | **KEEP** |
| return_exhaustion-,rs-r30 | SHORT | — | — | 100.0% | +0.53% | — | — | **KEEP** |
| hzscore-,rs-r101..104 | SHORT | — | — | 100.0% | +0.48% | — | — | **KEEP** |
| hzscore-,rs-r66..72 | SHORT | — | — | 100.0% | +0.42% | — | — | **KEEP** |
| return_exhaustion_long,vortex_break_long | LONG | — | — | 100.0% | +0.32% | — | — | **KEEP** |
| range_finder,return_exhaustion_long | LONG | — | — | 100.0% | +0.24% | — | — | **KEEP** |

---

## LOSERS (WR < 30% or PnL < -2%)

| Signal | Dir | 6h WR | 6h PnL | 24h WR | 24h PnL | 7d WR | 7d PnL | Status |
|--------|-----|-------|--------|--------|---------|-------|--------|--------|
| hzscore-,return_exhaustion- | SHORT | — | — | 33.3% | -2.25% | 50.0% | -1.86% | **WATCH** |
| ma100-cross,return_exhaustion- | SHORT | — | — | 40.0% | -2.26% | 42.9% | -2.76% | **WATCH** |
| bb_bounce (standalone) | SHORT | — | — | — | — | 40.0% | -4.61% | **DISABLE** |
| inv-accel-300- | SHORT | — | — | — | — | 38.9% | -2.87% | DEAD (already disabled) |
| decider | SHORT | — | — | — | — | 10.0% | -1.97% | DEAD (already disabled) |
| accel-300-breakout | LONG | — | — | — | — | 0.0% | -1.93% | DEAD (already disabled) |
| pattern_wolf_wave_bear | SHORT | — | — | — | — | 20.0% | -1.64% | DEAD (already disabled) |
| pattern_scanner | SHORT | — | — | — | — | 0.0% | -1.33% | DEAD (already disabled) |

---

## MARGINAL (30-50% WR, need more data)

| Signal | Dir | 6h WR | 6h PnL | 24h WR | 24h PnL | 7d WR | 7d PnL | Status |
|--------|-----|-------|--------|--------|---------|-------|--------|--------|
| bb_bounce,ma100-cross | LONG | 25.0% | -0.80% | 50.0% | +0.26% | 50.0% | +0.26% | **WATCH** |
| bb_bounce,range_finder | LONG | 25.0% | -0.12% | 40.0% | +0.19% | 40.0% | +0.19% | **WATCH** |
| hzscore+,return_exhaustion_long | LONG | — | — | 42.9% | +0.12% | 58.3% | +1.46% | **KEEP** (7d strong) |
| hzscore+,ma100-cross | LONG | — | — | 33.3% | -0.09% | 50.0% | +0.33% | **WATCH** |
| ma100-cross,vortex_break_short | SHORT | — | — | 66.7% | -0.12% | 66.7% | -0.12% | **WATCH** (WR good but PnL negative) |

---

## DISABLED BUT STILL GENERATING OUTCOMES

**Critical finding:** 32 stale signal names still appear in signal_outcomes from the last 7d, despite being disabled. These are producing phantom outcomes from old trade data or hl-sync-guardian writes:

| Stale Signal | Issue |
|-------------|-------|
| vel-hermes-, accel-300-*, inv-accel-300-, zscore-rising-* | CEO killed, still in outcomes |
| pattern_wolf_wave_*, pattern_scanner | CEO killed, still in outcomes |
| tl_break_long, tl_break_short | CEO killed 2026-08-07, still in outcomes |
| decider | 10% WR, still in outcomes |
| hl_copy_trader | Disabled, still in outcomes |
| choch-5 | Via HH_HL_CHOCH, may be legitimate |

**Action needed:** Investigate why disabled signals still write to signal_outcomes. Likely hl-sync-guardian or position_manager recording old trades.

---

## SIGNAL INVERSIONS

**None detected** in last 24h.

---

## RECOMMENDATIONS

### Immediate Actions

1. **[DISABLE] bb_bounce standalone SHORT** — 40% WR, -4.61% PnL over 7d (10 trades). The SHORT variant of standalone bb_bounce is the biggest active loser. Consider requiring confluence with at least one additional signal before firing.

2. **[WATCH] hzscore-,return_exhaustion- SHORT** — 33.3% WR, -2.25% in 24h. Needs more data. If trend continues, disable.

3. **[WATCH] ma100-cross,return_exhaustion- SHORT** — 40% WR, -2.26% in 24h. Same concern as above.

4. **[INVESTIGATE] Stale signal outcomes** — 32 disabled signals still generating outcomes in the database. This corrupts performance tracking. Check hl-sync-guardian.py and position_manager.py for legacy signal_type recording.

### Systemic Issues

5. **[TUNE] 6h under-trading** — Only 14 trades in 6h (28.6% WR). The system is generating too few signals. Consider:
   - Lowering confluence requirements for high-confidence signals
   - Reviewing if regime filter is too aggressive in NEUTRAL state
   - Checking if hotset coverage is sufficient

6. **[PROTECT] bb_bounce,hzscore+ combo** — 100% WR over 7d (5/5 trades, +2.04%). This is the best signal in the system. Ensure the confluence logic stays intact.

7. **[MONITOR] Overall system performance** — 44.1% WR over 7d with -13.74% PnL. The confluence signals are profitable but the system overall is still negative. Focus on:
   - Increasing confluence requirements
   - Reducing standalone signal firing
   - Tightening entry criteria

---

## 7d Top Performers (Context)

| Signal | Dir | Trades | WR | PnL |
|--------|-----|--------|----|-----|
| tl_break_long | LONG | 23 | 65.2% | +11.06% |
| tl_break_long | SHORT | 8 | 62.5% | +5.08% |
| tl_break_short | LONG | 4 | 75.0% | +2.10% |
| bb_bounce,hzscore+ | LONG | 5 | 100.0% | +2.04% |
| hzscore+,return_exhaustion_long | LONG | 12 | 58.3% | +1.46% |
| ma100-cross,return_exhaustion_long | LONG | 6 | 66.7% | +1.13% |
| ma100-cross,vortex_break_long | LONG | 6 | 83.3% | +1.02% |

**Note:** tl_break signals show strong7d performance but CEO killed them on 2026-08-07 due to recent deterioration. The7d data includes profitable historical trades.

---

Generated: 2026-08-07 | Auto-generated by signal performance analysis
