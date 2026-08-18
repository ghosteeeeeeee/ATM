# Signal Performance Report
**Generated:** 2026-08-18 14:30 UTC | **Period:** Last 6h + 24h + 48h

## Overall Stats
- **All-time:** 3,728 trades | 42.4% WR | -$2.89 PnL
- **24h:** 13 trades | 53.8% WR | -$0.07 PnL

---

## KILLED (executed)

None. No signal meets kill criteria (5+ trades 24h, WR < 30%, PnL < -$0.10).

---

## BOOSTED (executed)

None. Winners already enabled, no tuning needed.

---

## LOSERS — WATCH LIST

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| return_exhaustion_long | LONG | 25% | -$0.23 | 4 (48h) | WATCH — dropped from 60% all-time WR. Already tuning in progress? |
| r2-trend-long3 | LONG | 25% | -$0.09 | 4 (24h) | WATCH — 54.2% all-time. MIN_PRE_MOVE already raised 0.1→0.2 today. |

---

## WINNERS

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| stop_hunt_reversal_long+ | LONG | 100% | $0.07 | 3 (48h) | STRONG |
| r2-trend-long4 | LONG | 80% | $0.12 | 5 (48h) | STRONG |
| bb_bounce+,hl_copy_trader | LONG | 75% | $0.24 | 4 (48h) | STRONG |

---

## SIGNAL INVERSIONS

**No inversions found.** All signals respect their direction labels.

---

## KEY OBSERVATIONS

1. **Very low trade volume** — 13 trades in 24h, well below normal. Market may be in a low-volatility regime.
2. **return_exhaustion_long** has degraded: all-time 60% WR, 10T, +$0.21 but recent 48h is 25% WR, 4T, -$0.23. Needs monitoring — if 24h trade count reaches 5+ with continued poor WR, will kill.
3. **r2-trend-long3** already had MIN_PRE_MOVE raised from 0.1 to 0.2 today to address ATR stop losses hitting before PM_TRAIL activation. Watching effectiveness.
4. **Hot-set is empty** — compaction cycle 13287, no signals in hotset.
5. **All-time PnL is -$2.89** across 3,728 trades — system is nearly breakeven overall, signal quality is adequate but not profitable enough.

---

## RECOMMENDATIONS

1. **Monitor return_exhaustion_long** — if 24h hits 5+ trades with WR < 40%, escalate for disable
2. **No parameter changes needed now** — volume too low to draw conclusions
3. **Consider temporary cooldown on return_exhaustion_long** if next 6h shows continued 0% WR

---

*Report auto-generated. Next report: ~6h from now.*
