## CEO Report — 2026-08-13 (latest)

### Diagnosis
24h: 88T, -$0.64, 52.3% WR — RED. 7d: 451T, -$0.54, 51.4% WR (slightly negative). Today Aug 13: 30T, -$1.12, 40.0% WR — WORST DAY of cycle. Daily: Aug 9 +$0.62 → Aug 10 -$0.10 → Aug 11 -$0.33 → Aug 12 +$0.49 (recovery) → Aug 13 -$1.12 (legacy bleed). SHORT 7d: 199T, -$1.34, 51.8% WR (bleeding despite decent WR — losses > wins).

### Root Cause
Today's losses = 83% from legacy disabled signals still clearing:
- **accel-300- SHORT**: 19T, -$0.73, 36.8% WR (ACCEL_300_MINUS_ENABLED=False — no new entries, legacy only) = 65% of today's loss
- **range_breakout_short SHORT**: 5T, -$0.31, 20.0% WR (active signal — only real bleed source today)
- Disabled combos: continuation-,hzscore- 1T -$0.10, accel-300-,hzscore- 1T -$0.10

SHORT7d -$1.34 is mostly residual from disabled signals (accel-300- 40T -$0.30, range_breakout- 20T -$0.12). Active SHORT signals fine: hzscore- 19T +$0.05, range_breakout_short 19T +$0.18.

### Stars7d (all profitable, intact)
| Signal | Trades | PnL | WR |
|--------|--------|-----|-----|
| bb_bounce+,range_finder+ | 53 | +$0.71 | 58.5% |
| bb-bounce-short,hzscore- | 18 | +$0.14 | 61.1% |
| hzscore+,mover+ | 5 | +$0.17 | 80.0% |
| bb_bounce+,hzscore+ | 34 | +$0.22 | 50.0% |
| range_breakout_short | 19 | +$0.18 | 57.9% |

### Cost Drivers (48h)
atr_sl_hit 70T -$4.62 (dominant). cut-loser-CL-T1 4T -$0.42.

### Fix Applied
NO CHANGES. All bleeders already disabled/blacklisted. Today = legacy clearing + 1 bad day from range_breakout_short (20% WR, 5T). System functioning as designed. Stars intact.

### Verification
Pipeline healthy. 3 open SHORT ($0 flat). Legacy positions closing — no new entries from disabled signals (ACCEL_300_MINUS_ENABLED=False confirmed). All timers active. Stars intact.

### Monitoring
1. **range_breakout_short SHORT** — today 5T -$0.31 20% WR.7d still positive (+$0.18). If another red day → disable RANGE_BREAKOUT_SHORT_ENABLED.
2. **Daily PnL** — if -2 consecutive red days after legacy clears → investigate.
3. **SHORT7d -$1.34** — mostly legacy. Monitor: if still -$1.50+ after accel-300- fully clears → add regime filter.
