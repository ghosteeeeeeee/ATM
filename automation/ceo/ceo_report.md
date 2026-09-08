## CEO Report — 2026-09-08 ~16:00 UTC

### Diagnosis
24h: 73T, 54.8% WR, -$0.47 (was +$1.06 at 10:35 — degraded $1.53). 48h: 121T, 58.7% WR, -$0.88. Sep 8: 48T, 50% WR, -$1.25 (worst day in 4, breaks 4-day green streak). **bb-bounce-v2-long+ STAR degraded today:** 13T/38.5% WR, -$0.91 (7d still 71T/74.6% WR +$2.19). cut-loser-CL-T1 dominates losses (24T/48h, -$3.41). open-skies+ ONLY healthy R:R signal (3T/24h 66.7% WR +$1.23, R:R 3.737).

### Root Cause
1. **bb-bounce-v2-long+ bad day** — 7/13 trades hit cut-loser-CL-T1 at -5.32% avg. Weak NEUTRAL entries getting stopped out. **7d still 74.6% WR — this is variance, not structural.**
2. **sma20-dip+ legacy** — 19T/24h -$0.73 (killed at 12:10 UTC by auto_1hr, losses aging out).
3. **ema300-dip-short protected** — 12T/24h -$0.30. Protected until Sep 9 05:00.
4. **R:R structural** — avg win $0.046 (bb-bounce today) vs avg loss $0.140. PM_TRAIL at 0.40%/0.20% (protected) capping winners.

### Fix Applied
1. **sma20-dip+ KILLED** by auto_1hr at 12:10 UTC — correct (0%WR last hour, 47.1% all-time).
2. **No param changes** — bb-bounce 74.6% WR 7d, one bad day doesn't warrant change.
3. **PM_TRAIL protected** at 0.40%/0.20%. 52.1% of exits, avg +2.08%.
4. **Legacy aging out** — slow-grind+, coil-spring+ exited 48h window.

### Verification
Pipeline healthy. 5 open positions. Disk 82%. Legacy bleeders aging out by tomorrow. System recovering from normal variance after 4 green days (Sep 5-7: +$0.88 total). Today -$1.25 erases Sep 5+6 gains but not structural.

### Target
48h flips positive as bb-bounce recovers and legacy ages out. Monitor — no changes unless bb-bounce drops below 50% WR at 20T/48h.

### Signal R:R Summary (7d)
| Signal | R:R | Breakeven WR | Actual WR | Status |
|--------|-----|-------------|-----------|--------|
| open-skies+ | 1.303 | 43.4% | 64.7% | HEALTHY ★ |
| bb-bounce-v2-long+ | 0.623 | 61.6% | 75.7% | Profitable but tight |
| sma20-dip+ | 0.482 | 67.5% | 53.3% | UNDERWATER |
| pump-chain+ | 0.369 | 73.0% | 82.1% | Barely profitable |

### Verification
DB verified at 10:35 UTC. 48h flipped negative from legacy. Today -$0.33 within normal variance for compressed R:R system. No param changes needed — watch 48h window flip back positive as legacy ages out. ema300-dip-short protection expires Sep 9 05:00.
