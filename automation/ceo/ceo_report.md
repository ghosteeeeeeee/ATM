⚠️ CRITICAL: SIGNAL STARVATION ⚠️
Aug 12: 100 trades → Aug 13: 53 → Aug 14: 80 → Aug 15: 15. That's an 85% collapse. Zero open positions. 17 signals running, 15 trades closed. The filter stack (SPEED_MIN=45, REGIME_ENABLED, CONTEXT_GATE_ENABLED) strangles signal flow in NEUTRAL. Stop tweaking trailing on zero trades — fix the starvation first. No volume = no data = no improvement = death spiral.

---

## CEO Report — 2026-08-15 (eval check)

### Diagnosis
24h 71T -$0.76 (46.5% WR — RED, 5th+ consecutive red). 48h 127T -$1.42 (49.6% WR). R:R inverted 0.61:1 (avg win 0.42% vs avg loss -0.69%). Daily: Aug 12 +$0.49 → Aug 13 -$1.58 → Aug 14 -$0.56 → Aug 15 -$0.16 (14T). 1 open.

### Root Cause
Eval windows still active — PM_TRAIL disabled, ATR_TP_K_MULT 2.5, trailing activation 0.60% all deployed Aug 15, need 48h. R:R improving slowly (0.61:1 vs 0.48:1 earlier). All bleeding signals already killed (range_breakout_short, wave_catcher, trend_momentum).

### Fix Applied
NO CHANGES. Changing params now invalidates eval results.

### Verification (next run ~Aug 17)
- R:R ratio (should ↑ from 0.61:1 toward 1:1)
- Avg win (should ↑ from 0.42%)
- Daily PnL (if 6th red → deeper investigation)
- Disk (85% → cleanup)

---

## CEO Report — 2026-08-15 (latest)

### Diagnosis
48h 128T -$1.52 (49.2% WR). R:R inverted 0.35:1 — avg PM trail exit 0.27% vs avg ATR_SL -0.78%. PM_TRAIL dominates exits (74T/48h). ATR_SL 49T -$3.87 (main loss driver). ATR_TP only 1T/48h (K_MULT 2.5 barely firing). Stars7d intact. 1 open flat. Disk 71%. NEUTRAL regime.

### Root Cause
PM_TRAIL_DISTANCE_PCT 0.40% too tight. Winners peak at 0.67% → exit at 0.27% (peak-0.40%). 7d PM_TRAIL avg was 0.409% before recent changes, now 0.27% — the 0.40% distance is the bottleneck.

### Fix Applied
WIDENED PM_TRAIL_DISTANCE_PCT 0.40%→0.60%. Trail now gives0.60% room behind peak. Expected: avg exit ↑ from 0.27% toward 0.40%+, R:R ↑ from 0.35:1 toward 0.55:1+.

### Verification (next run ~Aug 16)
- Avg PM trail exit 48h (should ↑ from 0.27%)
- R:R ratio (should ↑ from 0.35:1)
- ATR_SL count (should ↓ as more trades reach trailing)
- Daily PnL (if 6th red day → deeper investigation)

### Stars7d (intact, 5 profitable)
| Signal | Trades | PnL | WR |
|--------|--------|-----|-----|
| bb_bounce+,range_finder+ |44 | +$0.40 | 54.5% |
| bb_bounce+,hzscore+ |34 | +$0.22 | 50.0% |
| bb_bounce+ |21 | +$0.21 | 61.9% |
| hzscore+,mover+ |5 | +$0.17 | 80.0% |
| bb-bounce-short,hzscore- |18 | +$0.14 | 61.1% |

## CEO Report — 2026-08-15

### Diagnosis
24h: 73T, -$0.72, 46.6% WR (RED, 4th consecutive red). Daily: Aug 12 +$0.49 → Aug 13 -$1.58 → Aug 14 -$0.56 → Aug 15 -$0.16 (recovering). 48h R:R inverted 0.35:1 — avg PM trail exit 0.27% vs avg ATR_SL -0.78%. PM_TRAIL 74T/48h dominates exits. ATR_SL 49T -$3.87 (main loss driver). ATR_TP only 1T/48h (K_MULT 2.5 barely firing). Stars7d intact (5 profitable). 1 open flat. Disk 71%. NEUTRAL regime (102/104).

### Root Cause
PM_TRAIL_DISTANCE_PCT 0.40% too tight — winners peak at 0.67% → exit at 0.27% (peak-0.40%). ATR_TP_K_MULT 2.5 barely firing (1T/48h) because PM_TRAIL exits first. Legacy SHORT bleeders aging out (range_breakout_short 11T -$0.47 27.3% WR — already DISABLED).

### Fix Applied
NO CHANGES — eval windows active. PM_TRAIL_DISTANCE_PCT 0.60%, ATR_TP_K_MULT 2.5, TRAILING_ACTIVATION_PCT 0.60% all deployed Aug 15, eval closes ~Aug 17. System correctly idle in NEUTRAL regime.

### Verification
Monitor: avg trail win 48h (should ↑ from 0.27%), R:R ratio (should ↑ from 0.35:1), daily PnL (should continue recovering), mover+ LONG (if 10T no improvement → disable), disk (85% → cleanup).
