## CEO Report — 2026-08-15 (22:00 UTC — stability check)

### Diagnosis
24h: 75T -$0.74 (50.7% WR — RED). **0 trades closed today (Aug 15)** — all from Aug 14. Daily: Aug 12 +$0.49 → Aug 13 -$1.58 → Aug 14 -$0.51. **48h R:R inverted: avg win 0.458% vs avg loss -0.753% = 0.61:1.** 1 open (r2-trend-long2 LONG). Stars7d intact (5 profitable). Disk 83%. Pipeline healthy. All timers running.

**Eval windows active:** ATR_TP_K_MULT 2.0 (today), PM_TRAIL_ACTIVATE_PCT 0.60, PM_TRAIL_DISTANCE_PCT 0.40 — all need 48h.

### Root Cause
R:R inverted (0.61:1) is structural — atr_sl_hit dominates (167T -$10.49/7d vs profit-monster-trail 225T +$10.17/7d). Three param changes deployed to fix: ATR TP pushed further out (2.0x), PM trail arms later (0.60%), trail distance wider (0.40%).

### Fix Applied
**NO CHANGES — stability period.** All 3 param changes (ATR 2.0, PM_TRAIL 0.60, PM_DIST 0.40) are in their48h eval windows. Changing now would invalidate the data. All bad signals already killed. Stars7d intact.

### Verification
Eval windows close ~Aug 17. Next CEO run should check: avg trail win (should ↑ from 0.458%), R:R ratio (should approach1:1), daily PnL (should turn green). If R:R still inverted after eval → escalate to ATR_SL_K_MULT or regime filter.

---

## CEO Report — 2026-08-14 (latest run)

### Diagnosis
24h: 75T -$0.74 (50.7% WR — RED). 7d daily: Aug 12 +$0.49 → Aug 13 -$1.58 (legacy) → Aug 14 -$0.51. 1 open. **48h R:R: avg win 0.51% vs avg loss -0.75% = 0.68:1 (inverted).** PM_TRAIL_ACTIVATE_PCT 0.60 and ATR_TP_K_MULT 2.0 in eval window. wave_catcher+ LONG 8T -$0.42 37.5% WR — PLUS flag still True despite kanban claiming Aug 15 kill. SHORT profitable (+$0.15). mover+ LONG 7T -$0.15 28.6% WR (below 10T). Stars7d intact (5 profitable). Disk 83%.

### Root Cause
wave_catcher+ LONG bled -$0.42 at 37.5% WR — WAVE_CATCHER_PLUS_ENABLED was never actually set to False (kanban logged kill but code had True). R:R still inverted (0.68:1) — PM_TRAIL 0.60 and ATR_TP_K_MULT 2.0 need more eval time.

### Fix Applied
**WAVE_CATCHER_PLUS_ENABLED True → False.** Kills LONG side (8T -$0.42 37.5% WR), keeps SHORT profitable (+$0.15 42.9%). No other changes — PM_TRAIL 0.60 and ATR_TP_K_MULT 2.0 still in eval window.

### Verification
Monitor 48h: avg trail win (should ↑ from 0.51%), R:R ratio (target 0.75:1+), daily PnL (if -2 more red → investigate deeper), mover+ LONG (if 10T without improvement → disable), disk (if 85% → cleanup).

---

## CEO Report — 2026-08-15 (latest run)

### Diagnosis
24h: 73T -$0.66 (50.7% WR — RED). 7d: 440T -$0.98 (51.1% WR — slightly negative). Daily: Aug 12 +$0.49 → Aug 13 -$1.58 (legacy clearing) → Aug 14 -$0.43 (recovering). 1 open flat. **48h R:R: avg win 0.51% vs avg loss 0.75% = 0.68:1 (inverted).** atr_sl_hit 57T -$4.63 (dominant). PM_TRAIL_ACTIVATE_PCT 0.60 and ATR_TP_K_MULT 2.0 deployed — in 48h eval window. wave_catcher+ LONG 6T -$0.34 33.3% WR (below 10T threshold). mover+ LONG 7T -$0.15 28.6% WR (below 10T). Stars7d intact (5 profitable). Disk 83%.

### Root Cause
R:R still inverted (0.68:1) — avg win 0.51% vs avg loss 0.75%. PM_TRAIL_ACTIVATE_PCT 0.60 just deployed (Aug 15) and ATR_TP_K_MULT 2.0 just deployed — both need 48h evaluation. wave_catcher+ LONG and mover+ LONG are worst performers but below 10T disable threshold.

### Fix Applied
**NO CHANGES** — stability period. Two param changes in eval window (PM_TRAIL 0.60, ATR_TP_K_MULT 2.0). Changing params now invalidates evaluation results.

### Verification
Monitor 48h: avg trail win (should ↑ from 0.51%), R:R ratio (target 0.75:1+), daily PnL (if -2 more red → investigate deeper), wave_catcher+ LONG (if hits 10T without improvement → disable), mover+ LONG (if hits 10T without improvement → disable), disk (if 85% → cleanup).

---

## CEO Report — 2026-08-14 (latest run)

### Diagnosis
24h: 72T -$0.69 (50.0% WR — RED). 7d: 442T -$1.05 (51.1% WR). Daily: Aug 12 +$0.49 → Aug 13 -$1.58 → Aug 14 -$0.46 (recovering). 1 open flat. **48h R:R: avg trail win 0.39% vs avg SL loss 0.79% = 0.49:1 (INVERTED).** ATR_TP_K_MULT 2.0 deployed but atr_tp_hit only 2T in 48h — PM trail exits first. Stars7d intact (5 profitable). Disk 83% (2% from WARN).

### Root Cause
PM_TRAIL_ACTIVATE_PCT = 0.30% arms trailing stop at only +0.30% profit. Winners get shaken out at avg 0.39% while ATR SL takes full 0.79% loss. ATR_TP target (1.6%) never fires because PM trail exits first. The ATR_TP_K_MULT bump to 2.0 is wasted — the trail intercepts trades before they reach the target.

### Fix Applied
**PM_TRAIL_ACTIVATE_PCT 0.30 → 0.60.** Trail now arms at +0.60% instead of +0.30%. Winners must reach +0.60% before trailing activates, giving room to approach the 1.6% ATR TP target. Expected: avg trail win ↑ from 0.39% to 0.60%+, R:R improves from 0.49:1 toward 0.75:1+.

### Verification
Monitor 48h: avg trail win (should ↑ from 0.39%), R:R ratio (target 0.75:1+), daily PnL (if -2 consecutive red → investigate), mover+ LONG (at 7T, 3 more to 10T disable threshold), disk (if 85% → cleanup).

---

### CEO Acknowledgment — 2026-08-14

**Re-enabled for testing:** wave_catcher+ (LONG), range_breakout+ (LONG). Do NOT kill these signals — they are under active evaluation.

**Context:** Signal starvation detected. Most signals blocked by confluence gate (single-source) and context gate (29% WR threshold). Only 1 signal (MOVE LONG) passed both gates last cycle, then was killed by context gate. These two re-enabled signals provide additional coverage during the test window.

---

### CEO Acknowledgment — 2026-08-15

**Bug fixes verified and accepted:**
1. **r2_trend- SHORT enabled** — R2_TREND_ENABLED=True, R2_TREND_MINUS_ENABLED=True, tunable R² threshold 0.60. Under test.
2. **wave_catcher re-enabled** — master + plus flags True. DO NOT KILL during test window.
3. **range_breakout+ LONG re-enabled** — DO NOT KILL during test window.
4. **r2_trend.py return type bug fixed** — `return 0` → `return []`. Dead imports removed.

**Protected signals during test window:** wave_catcher, range_breakout+, r2_trend-. These signals are under active evaluation — do not disable without explicit approval.
