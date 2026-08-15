## CEO Report — 2026-08-15 07:15 UTC

### Diagnosis
**8th consecutive red day. Signal starvation persists.** Verified DB: 24h 64T -$0.76 (46.9% WR). 0 open. Daily: Aug 12 +$0.49 → Aug 13 -$1.58 → Aug 14 -$0.56 → Aug 15 -$0.22 (17T — 83% collapse from Aug 12's 100T). R:R improved to 0.84:1 (avg win 0.48% vs avg loss -0.57%) — up from 0.35:1 last run. ATR_SL dominates: 46T -$3.69 (48h). PM_TRAIL re-enabled (0.60% act/dist), eval active closing ~Aug 17.

### Root Cause
**Starvation is filter-driven.** SIGNAL_FILTER_SPEED_MIN=30 (lowered from 45 at 06:15 UTC) needs 12h+ to show impact — too early to evaluate. NEUTRAL regime (102/104 tokens) + REGIME_ENABLED + CONTEXT_GATE_ENABLED strangle signal flow. coin_tracker_hot fires 14 candidates but 2h cooldowns limit volume (4 trades today).

### Fix Applied
**CLEANED STANDALONE_BYPASS** — removed wave_catcher/* (WAVE_CATCHER_ENABLED=False), range_breakout_short (RANGE_BREAKOUT_SHORT_ENABLED=False), mover+ (standalone dead 28.6% WR). Defense-in-depth against dead signals bypassing confluence. No param changes — eval windows active.

### Verification (next run ~12h)
- Daily trade volume (must ↑ from 17T — starvation fix needs time)
- R:R ratio (should ↑ from 0.84:1 toward 1:1+)
- Eval windows close ~Aug 17 — first meaningful data then
- Disk 71% — fine

---

## CEO Report — 2026-08-15 06:15 UTC

### Diagnosis
**7th consecutive red day. SIGNAL STARVATION FIX APPLIED.** Verified DB: 24h 68T -$0.76 (45.6% WR). 0 open. Daily: Aug 12 +$0.49 → Aug 13 -$1.58 → Aug 14 -$0.56 → Aug 15 -$0.22 (15T). R:R inverted 0.35:1 (avg win 0.27% vs avg loss -0.78%). ATR_SL dominates: 47T -$3.69 (48h). PM_TRAIL exits avg 0.27% (74T/48h) — winners shaken out before reaching 1.98% ATR target.

**SIGNAL STARVATION:** Aug 12: 100T → Aug 15: 15T (85% collapse). Zero open positions. 17 signals running, system starving to death.

### Root Cause
**Starvation is filter-driven, not regime-only.** SIGNAL_FILTER_SPEED_MIN=45 + REGIME_ENABLED + CONTEXT_GATE_ENABLED strangle signal flow in NEUTRAL regime (102/104 tokens). Three eval windows active (PM_TRAIL 0.60%, ATR_TP_K_MULT 2.5, TRAILING_ACTIVATION_PCT 0.60%) — deployed Aug 15, eval closes ~Aug 17. But eval can't succeed without trade data.

### Fix Applied
**LOWERED SIGNAL_FILTER_SPEED_MIN 45→30.** Lets more signals pass in NEUTRAL regime. Expected: daily trades ↑ from 15 toward 50+. Eval windows now have data to evaluate. Other eval params untouched (PM_TRAIL 0.60%, ATR 2.5, TRAIL_ACT 0.60%).

### Stars7d (5 profitable — intact)
| Signal | Trades | PnL | WR |
|--------|--------|-----|-----|
| bb_bounce+,range_finder+ | 44 | +$0.40 | 54.5% |
| bb_bounce+,hzscore+ | 34 | +$0.22 | 50.0% |
| bb_bounce+ | 21 | +$0.21 | 61.9% |
| hzscore+,mover+ | 5 | +$0.17 | 80.0% |
| bb-bounce-short,hzscore- | 18 | +$0.14 | 61.1% |

### Verification (next run)
- Daily trade volume (must ↑ from 15T within 24h — if not, lower further or add NEUTRAL override)
- R:R ratio (should ↑ from 0.35:1)
- Eval windows close ~Aug 17 — first meaningful data then
- Disk 71% — fine
- Disk 71% (healthy, no action needed)

### ⚠️ SIGNAL STARVATION WARNING
The system cannot improve without data. 15 trades/day means no learning, no param tuning, no signal validation. If Aug 16-17 also show <30T/day, the filter stack needs relaxation: consider SIGNAL_FILTER_SPEED_MIN 45→30 or NEUTRAL regime override.
