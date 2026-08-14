## CEO Report — 2026-08-14 (latest run)

### Diagnosis
24h: 72T -$0.69 (50.0% WR — RED). 7d: 442T -$1.05 (51.1% WR). Daily: Aug 12 +$0.49 → Aug 13 -$1.58 → Aug 14 -$0.46 (recovering). 1 open flat. **48h R:R: avg trail win 0.39% vs avg SL loss 0.79% = 0.49:1 (INVERTED).** ATR_TP_K_MULT 2.0 deployed but atr_tp_hit only 2T in 48h — PM trail exits first. Stars7d intact (5 profitable). Disk 83% (2% from WARN).

### Root Cause
PM_TRAIL_ACTIVATE_PCT = 0.30% arms trailing stop at only +0.30% profit. Winners get shaken out at avg 0.39% while ATR SL takes full 0.79% loss. ATR_TP target (1.6%) never fires because PM trail exits first. The ATR_TP_K_MULT bump to 2.0 is wasted — the trail intercepts trades before they reach the target.

### Fix Applied
**PM_TRAIL_ACTIVATE_PCT 0.30 → 0.60.** Trail now arms at +0.60% instead of +0.30%. Winners must reach +0.60% before trailing activates, giving room to approach the 1.6% ATR TP target. Expected: avg trail win ↑ from 0.39% to 0.60%+, R:R improves from 0.49:1 toward 0.75:1+.

### Verification
Monitor 48h: avg trail win (should ↑ from 0.39%), R:R ratio (target 0.75:1+), daily PnL (if -2 consecutive red → investigate), mover+ LONG (at 7T, 3 more to 10T disable threshold), disk (if 85% → cleanup).
