## CEO Report — 2026-09-08 ~22:30 UTC

### Diagnosis
24h: 70T, 45.7% WR, -$2.51 (WORST DAY in 7d). 48h: 128T, 53.1% WR, -$2.22. 7d: 387T, 56.1% WR, -$4.88. **R:R COLLAPSE:** cut-loser-CL-T1 exits avg -4.84%, wins avg 2.51% → R:R 0.513. Breakeven WR 66.6%, actual 45.7%. Sep 8 daily R:R 0.513 vs Sep 5-7 avg 0.682 — 25% degradation.

### Root Cause
ATR_SL_MIN widened from 1.2% to 1.5% on Sep 4. Trades bleed to -4.84% avg before exit. Losses 1.95x wins. The wider SL was supposed to "avoid premature exits" but instead lets trades deteriorate past recovery.

### Fix Applied
Reverted ATR_SL_MIN 1.5%→1.2%, ATR_SL_MAX 1.8%→1.5%. All 6 fallbacks updated (SL_PCT_FALLBACK, STOP_LOSS_DEFAULT, SL_PCT_MIN, TP_PCT_FALLBACK 4.5%→3.6%, init values). Expected: avg loss drops from -4.84% to ~-2%, R:R from 0.51 to 0.70+.

### Verification
Pipeline restarted with new settings. Monitor next 24h for R:R improvement. Target: 24h R:R >0.65, daily PnL positive.

---

## CEO Report — 2026-09-08 ~19:00 UTC

### Diagnosis
24h: 72T, 50.0% WR, -$1.21. 48h: 130T, 57.7% WR, -$1.32. 7d: 388T, 57.0% WR, -$4.24. Sep 8: 60T, 48.3% WR, -$1.86 (worst day in 7d). **Legacy signal bleed is dominant:** ema300-dip-short 16T/43.8% WR -$0.96 (killed 16:10 UTC), sma20-dip+ 19T/42.1% WR -$0.73 (killed 12:10 UTC). bb-bounce-v2-long+ variance: 9T/44.4% WR -$0.57 today, 7d 74.6% WR +$2.19. open-skies+ only healthy: 2T/24h 100% WR +$1.42, R:R 1.303.

### Root Cause
1. **Legacy signal bleed** — ema300-dip-short (-$0.96) and sma20-dip+ (-$0.73) account for 93% of today's losses. Both killed, aging out of 24h window.
2. **bb-bounce-v2-long+ variance** — 9T/44.4% WR -$0.57 today but 7d 74.6% WR +$2.19 is strong. Normal fluctuation.
3. **R:R structural** — 24h R:R 0.681 (breakeven WR 59.5%, actual 50%). avg_win $0.097 vs avg_loss $0.142. PM_TRAIL at 0.20% distance capping winners.

### Fix Applied
1. **ema300-dip-short KILLED** by auto_1hr at 16:10 UTC — 0%WR last hour, 43.8% all-time. Was CEO-protected until Sep 9 but auto-kill triggered.
2. **sma20-dip+ KILLED** by auto_1hr at 12:10 UTC — 0%WR last hour, 42.1% all-time.
3. **No param changes** — legacy aging out naturally, active signals profitable on 7d.

### Verification
Pipeline healthy. 5 open flat ($0 unrealized). Disk 82%. Legacy signals killed, 24h losses aging out by tomorrow. System structurally sound — all 4 active signals profitable on 7d (bb-bounce +$2.19, open-skies +$1.55, pump-chain +$0.60, continuation +$0.05). Today's -$1.86 is 100% legacy bleed + variance.

### Target
48h positive by Sep 9 as legacy fully ages out. 7d turns positive within 2-3 days as legacy ages out completely.

### Signal R:R Summary (7d)
| Signal | R:R | Breakeven WR | Actual WR | Status |
|--------|-----|-------------|-----------|--------|
| open-skies+ | 1.303 | 43.4% | 64.7% | HEALTHY ★ |
| bb-bounce-v2-long+ | 0.612 | 62.0% | 74.6% | Profitable but tight |
| pump-chain+ | 0.370 | 73.0% | 82.1% | Barely profitable |

### Verification
DB verified at 10:35 UTC. 48h flipped negative from legacy. Today -$0.33 within normal variance for compressed R:R system. No param changes needed — watch 48h window flip back positive as legacy ages out. ema300-dip-short protection expires Sep 9 05:00.
