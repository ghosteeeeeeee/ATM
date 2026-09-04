

## [2026-09-04 06:30 UTC] Daily Orchestrator Run

**Pipeline Status:** Running, 5 open | 82 closed today | -24.8% PnL
**24h:** 82T 59.8% WR -$0.73 USDT
**7d:** 407T 54.1% WR -$3.42 USDT
**Market:** 100% NEUTRAL
**Disk:** 84% (1% from threshold)

**Key Findings:**
1. **R:R PROBLEM (CRITICAL):** 59.8% WR losing money — avg loss > avg win. Exit quality is bottleneck, not signal selection. All signals negative today. Signal reporter flagged this at 05:10.
2. **v3-short- killed by auto_1hr:** 3T today (02:07-03:34 UTC, pre-kill). All losers. Added to NEVER_REENABLE.
3. **cascade_flip trade (ENA):** Happened at 04:36 before CASCADE_FLIP_ENABLED was disabled. Not a bug — cascade was still enabled when trade opened.
4. **slow-grind-:** TESTING, 3T/7d 33.3% WR -$0.17. Underperforming.
5. **All signals negative today:** ema300-dip -$0.32, bb-bounce-v2-long+ -$0.04, v3-short- -$0.48, cascade -$0.16, slow-grind -$0.13.
6. **Open positions:** 5 (ema300-dip ETH LONG -$0.01, r2v2-long7 W LONG +$0.01, r2-trend-short4 GMT SHORT +$0.03, accel-300-v3-short- MET SHORT +$0.16, accel-300-v3-short- INJ SHORT +$0.41).

**Health Monitor (06:23 UTC):** Pipeline OK, 41 signals/hr, 22 failed services (one-shot), auto-fixed logs.

**Signal Reporter (05:10 UTC):** All active signals winners (bb-bounce-v2-long+ 75.8% WR +$0.86/48h, ema300-dip 69.0% WR +$0.26/48h). Key finding: R:R problem — system losing despite 59.3% WR.

**Actions Taken:**
1. Updated CURRENT.md with fresh data
2. Added ACCEL_300_V3_SHORT to NEVER_REENABLE_FLAGS
3. Flagged R:R problem for CEO investigation
4. Flagged slow-grind- for potential kill

**Next Steps for CEO:**
1. Investigate R:R problem — ATR_SL k-factors, trailing thresholds, cut_loser timing
2. Decide on slow-grind- kill (3T/7d 33.3% WR -$0.17)
3. Consider expansion of bb-bounce-v2-long+ and ema300-dip (STAR performers)

## [2026-09-03 08:15 UTC] Hourly Analysis

**Trades:** 0 closed last hour (quiet period)
**24h Context:** 48T ~50%WR -$1.62 (improving from -$1.75)

**24h Breakdown:**
- profit-monster-trail: 26T avg +$0.050 (carrying system)
- atr_sl_hit: 17T (34.7%) avg -$0.120 — under 40% threshold, improving
- cut-loser exits: 5T total, avg -$0.14 (normal)

**Signal Leaders:**
- bb-bounce-v2-long+: 13T 76.9%WR +$0.20
- ema300-dip: 9T 66.7%WR +$0.16
- bb-bounce-short: 5T 80%WR +$0.05

**Changes:** None needed.

**No Change Needed:**
- Kill criteria: 0 trades last hour, no signal to evaluate
- atr_sl_hit 34.7% — trending down (was 36.5% at 07:15), under 40%
- accel-300-v3-long+: CEO locked until Sep 4 05:00 UTC, 3T 0%WR -$0.51
- Trade freq 0/hr — quiet period, normal

**Open Questions:**
- accel-300-v3-long+ auto-disable after CEO lock expires tomorrow?



## [2026-09-03 09:06 UTC] Hourly Analysis

**Trades:** 5 closed last hour (5W 0L +$0.13)
**24h Context:** 52T ~50%WR -$1.39

**Last Hour:** All 5 winners via profit-monster-trail (GMT 2x, COMP, DOT, AIXBT). All LONG. Clean exits.

**24h Breakdown:**
- profit-monster-trail: 30T (60%) avg +$0.046 — carrying system
- atr_sl_hit: 17T (34%) avg -$0.120 — under 40%, trending down
- cut-loser exits: 4T total, avg -$0.15 — normal

**Signal Leaders (24h):**
- ema300-dip: 13T 76.9%WR +$0.26
- bb-bounce-v2-long+: 13T 76.9%WR +$0.20
- bb-bounce-short: 4T 75%WR flat

**Signal Losers (24h):**
- accel-300-v3-long+: 4T 25%WR -$0.48 — CEO_PROTECTED until Sep 4 05:00
- range-reversion-long+: 6T 16.7%WR -$0.62 — already killed
- r2-trend-long3: 3T 33.3%WR -$0.23

**Changes:** None needed.

**No Change Needed:**
- Kill criteria: No signal has 0% WR with 3+ trades in last hour (0 trades)
- atr_sl_hit 34% — under 40%, trending down (was 36.5% at 07:15)
- accel-300-v3-long+ CEO locked until Sep 4 05:00 UTC — cannot disable
- Trade freq ~2/hr — normal
- System steady state — profit-monster-trail carrying all PnL

**Open Questions:**
- accel-300-v3-long+ auto-disable after CEO lock expires tomorrow?

## [2026-09-03 10:06 UTC] Hourly Analysis

**Trades:** 0 closed last hour (quiet period — last close 09:03)
**24h Context:** 51T ~54%WR +$-0.08

**24h Breakdown:**
- profit-monster-trail: 30T (59%) avg +$0.046 — carrying system
- atr_sl_hit: 17T (33%) avg -$0.120 — under 40%, trending down (was 38% at 05:15)
- cut-loser-CL-T1: 3T avg -$0.143 — normal
- ORPHAN_PAPER: 1T $0

**Signal Leaders (24h):**
- ema300-dip: 13T 76.9%WR +$0.26
- bb-bounce-v2-long+: 13T 76.9%WR +$0.20
- bb-bounce-short: 4T 75%WR flat

**Signal Losers (24h):**
- accel-300-v3-long+: 4T 25%WR -$0.48 — CEO_PROTECTED until Sep 4 05:00
- range-reversion-long+: 5T 20%WR -$0.41 — already killed
- r2-trend-long3: 3T 33%WR -$0.23

**Open Positions:** 5 ($11-20 each, ~$79 total)

**Changes:** None needed.

**No Change Needed:**
- Kill criteria: No signal has 0% WR with 3+ trades in last hour (0 trades)
- atr_sl_hit 33% — under 40%, trending down steadily (38% → 34.7% → 33%)
- accel-300-v3-long+ CEO locked until Sep 4 05:00 UTC
- Trade freq ~2/hr normal
- System steady state — profit-monster-trail carrying all PnL

**Open Questions:**
- accel-300-v3-long+ auto-disable after CEO lock expires tomorrow?

## [2026-09-03 11:06 UTC] Hourly Analysis

**Trades:** 1 closed last hour (0W 1L -$0.07)
**24h Context:** 49T ~50%WR -$0.70

**24h Breakdown:**
- profit-monster-trail: 30T avg +$0.046 — carrying system
- atr_sl_hit: 14T avg -$0.113 — 28.6% of closes, trending down (33% → 28.6%)
- cut-loser-CL-T1: 4T avg -$0.125 — normal
- ORPHAN_PAPER: 1T $0

**Signal Leaders (24h):**
- bb-bounce-v2-long+: 13T 76.9%WR +$0.20
- ema300-dip: 14T 71.4%WR +$0.19

**Signal Losers (24h):**
- accel-300-v3-long+: 4T 25%WR -$0.48 — CEO_PROTECTED until Sep 4 05:00
- r2-trend-long3: 3T 33.3%WR -$0.23

**Open Positions:** 5 ($78.6) — DOT, SYRUP, AIXBT, ME (SHORT), YGG (SHORT +$0.20)

**Changes:** None needed.

**No Change Needed:**
- Kill criteria: No signal has 0% WR with 3+ trades in last hour (1 trade only)
- atr_sl_hit 28.6% — under 40%, trending down steadily
- accel-300-v3-long+ CEO locked until Sep 4 05:00 UTC
- Trade freq ~1/hr normal
- System steady state — profit-monster-trail carrying all PnL

**Open Questions:**
- accel-300-v3-long+ auto-disable after CEO lock expires tomorrow?

## [2026-09-03 12:06 UTC] Hourly Analysis

**Trades:** 0 closed last hour
**24h Context:** 49T ~50%WR -$0.70

**24h Close Reasons:**
- profit-monster-trail: 30T avg +$0.046 — carrying system
- atr_sl_hit: 14T avg -$0.113 — 28.6% of closes, trending down (38%→28.6%)
- cut-loser-CL-T1: 4T avg -$0.125 — normal
- ORPHAN_PAPER: 1T $0

**Signal Leaders (24h, 3+ trades):**
- bb-bounce-v2-long+: 13T 76.9%WR +$0.20
- ema300-dip: 14T 71.4%WR +$0.19

**Signal Losers (24h, 3+ trades):**
- accel-300-v3-long+: 4T 25%WR -$0.48 — CEO_PROTECTED until Sep 4 05:00
- r2-trend-long3: 3T 33.3%WR -$0.23

**Open Positions:** 5 ($78.60)

**Changes:** None needed.

**No Change Needed:**
- Kill criteria: 0 trades last hour — no signal to evaluate
- atr_sl_hit 28.6% — under 40%, trending down steadily
- accel-300-v3-long+ CEO locked until Sep 4 05:00 UTC
- r2-trend-long3 33%WR -$0.23 (24h) — not kill-worthy on strict criteria (needs 0% WR + 3T last hour)
- Trade freq ~0/hr quiet period
- System steady state — profit-monster-trail carrying all PnL

**Open Questions:**
- accel-300-v3-long+ auto-disable after CEO lock expires tomorrow?
- r2-trend-long3: 9T/48h -$0.46 33%WR — borderline, monitor next hour

## [2026-09-03 13:06 UTC] Hourly Analysis

**Trades:** 3 closed (2 wins, 1 loss)
**PnL:** -$0.05 (WR: 66.7%)

**24h Context:** 50T ~50%WR +$0.76

**Last Hour Breakdown:**
- GRASS bb-bounce-v2-long+ profit-monster-trail +$0.03
- DOT bb-bounce-v2-long+ profit-monster-trail +$0.04
- SYRUP ema300-dip cut-loser-CL-T1 -$0.12

**24h by Close Reason:**
- profit-monster-trail: 31T avg +$0.046 — dominant winner
- atr_sl_hit: 13T (26%) avg -$0.122 — trending down (28.6% → 26%)
- cut-loser-CL-T1: 5T avg -$0.124 — normal
- ORPHAN_PAPER: 1T $0

**Signal Leaders (24h, 3+ trades):**
- bb-bounce-v2-long+: 3W 0L +$0.07 (last hour) — strong
- ema300-dip: 14T 71.4%WR +$0.19 (24h) — slight pullback last hour

**Changes:** None needed.

**No Change Needed:**
- Kill criteria: No signal has 0% WR with 3+ trades last hour
- atr_sl_hit 26% — under 40%, trending down (28.6% → 26%)
- accel-300-v3-long+ CEO_PROTECTED until Sep 4 05:00 UTC
- Trade freq 3/hr normal
- System steady state — profit-monster-trail carrying all PnL

**Open Questions:**
- accel-300-v3-long+ auto-disable after CEO lock expires tomorrow?

## [2026-09-03 14:06 UTC] Hourly Analysis

**Trades:** 0 closed last hour (GRASS/DOT closed at 13:00, just before window)
**PnL:** $0 (quiet period)
**24h Context:** 48T 62.5%WR -$0.67 (improving)

**24h by Close Reason:**
- profit-monster-trail: 31T avg +$0.046 — dominant winner
- atr_sl_hit: 11T (22.9%) avg -$0.135 — under 40% threshold
- cut-loser-CL-T1: 5T avg -$0.124 — normal
- ORPHAN_PAPER: 1T $0

**Signal Leaders (24h):**
- bb-bounce-v2-long+: 15T 80%WR +$0.27 — strong
- ema300-dip: 15T 66.7%WR +$0.07 — slight pullback
- accel-300-v3-long+: 4T 25%WR -$0.48 — CEO_PROTECTED until Sep 4 05:00
- r2-trend-long3: 3T 33%WR -$0.23 — borderline, monitor

**Changes:** None needed.

**No Change Needed:**
- Kill criteria: No 0%WR signal with 3+T last hour
- atr_sl_hit 22.9% — well under 40%
- Trade freq ~0/hr quiet period
- 5 open positions ($64.30)
- System steady state

**Open Questions:**
- accel-300-v3-long+ auto-disable after CEO lock expires tomorrow?
- r2-trend-long3: 3T/24h 33%WR — borderline, next hour determines

## [2026-09-03 15:06 UTC] Hourly Analysis

**Trades:** 8 closed last hour (6W 2L +$0.07)
**24h Context:** 56T 64.3%WR -$0.50

**Last Hour:** 6 winners — bb-bounce-v2-long+ 3W (ETC +$0.18, AIXBT +$0.03, COMP +$0.02), accel-300-v3-long+ 1W (PONS +$0.10), ema300-dip 1W (ONDO +$0.12), slow-grind- 1W (YGG +$0.11). 2 losers — bb-bounce-short 2L (ALT -$0.17, ME -$0.22).

**24h Breakdown:**
- profit-monster-trail: 36T (64.3%) avg +$0.053 — carrying system
- atr_sl_hit: 13T (23.2%) avg -$0.119 — well under 40%, healthy
- cut-loser-CL-T1: 6T avg -$0.140 — normal

**Signal Leaders (24h):**
- bb-bounce-v2-long+: 18T 83.3%WR +$0.50
- ema300-dip: 16T 68.8%WR +$0.19

**Signal Losers (24h):**
- accel-300-v3-long+: 5T 40%WR -$0.38 — CEO_PROTECTED until Sep 4 05:00
- bb-bounce-short: 4T 50%WR -$0.27 — last hour 0%WR 2T (monitor, 1 from kill)
- r2-trend-long3: 3T 33.3%WR -$0.23 — already disabled via R2_TREND_LONG_ENABLED

**Open Positions:** 1 (KAS LONG $19.90)

**Changes:** None needed.

**No Change Needed:**
- Kill criteria: No 0%WR signal with 3+T last hour (bb-bounce-short at 2T)
- atr_sl_hit 23.2% — well under 40%
- accel-300-v3-long+ CEO locked until Sep 4 05:00
- Trade freq 8/hr normal
- System steady state — profit-monster-trail carrying all PnL

**Open Questions:**
- accel-300-v3-long+ auto-disable after CEO lock expires tomorrow?
- bb-bounce-short: 0%WR last hour — if next hour adds 1+ loss, triggers kill

## [2026-09-03 16:15 UTC] Hourly Analysis

**Trades:** 8 closed last hour (4W 4L +$0.13)
**24h Context:** 62T 64.5%WR -$0.02 (near breakeven, improving)

**Last Hour:** 4 winners — ENA +$0.27, ADA +$0.07, KAS +$0.05, ATOM +$0.03 (all profit-monster-trail). 4 losers — CASHCAT -$0.14 (atr_sl_hit), PONS -$0.10, CHIP -$0.03, MNT -$0.02 (cut-loser-MAE-GUARD).

**24h Breakdown:**
- profit-monster-trail: 42T (67.7%) avg +$0.052 — carrying system PnL
- atr_sl_hit: 12T (19.4%) avg -$0.112 — well under 40% threshold
- cut-loser-CL-T1: 6T avg -$0.140 — normal
- cut-loser-MAE-GUARD: 1T avg -$0.020 — new exit type, minimal

**Signal Leaders (24h):**
- bb-bounce-v2-long+: 19T 84.2%WR +$0.55 ✅
- ema300-dip: 18T 66.7%WR +$0.20 ✅

**Signal Losers (24h):**
- accel-300-v3-long+: 9T 44.4%WR -$0.14 — CEO_PROTECTED until Sep 4 05:00
- bb-bounce-short: 4T 50%WR -$0.27 — 0 trades last hour (quiet)
- r2-trend-long3: 3T 33.3%WR -$0.23 — already disabled

**Open Positions:** 2 ($22.20) — ZRO -$0.09, ENS -$0.13 (both accel-300-v3-long+)

**Changes:** None needed.

**No Change Needed:**
- Kill criteria: No 0%WR signal with 3+T last hour
- atr_sl_hit 19.4% — well under 40%
- accel-300-v3-long+ CEO locked until Sep 4 05:00
- Trade freq 8/hr normal
- System steadily improving: -$1.39 → -$0.70 → -$0.02 over 8h
- profit-monster-trail carrying all PnL at avg +$0.052/trade

**Open Questions:**
- accel-300-v3-long+ auto-disable after CEO lock expires tomorrow?
- cut-loser-MAE-GUARD: new exit type, 1T so far — monitor for effectiveness

## [2026-09-03 17:06 UTC] Hourly Analysis

**Trades:** 7 closed last hour (6W 1L +$0.42, 85.7% WR)
**24h Context:** 69T 66.7%WR +$0.40 (positive, improving steadily)
**Today:** 52T 67.3%WR +$0.56

**Last Hour Detail:**
- 6 winners via profit-monster-trail: ACE +$0.19, ZRO +$0.11, DOGE +$0.08, STX +$0.07, GMT +$0.05, POL +$0.04
- 1 loser: ENS -$0.12 (cut-loser-CL-T1, accel-300-v3-long+)

**24h Exit Breakdown:**
- profit-monster-trail: 48T (69.6%) 91.7%WR +$2.72 — carrying entire system PnL
- atr_sl_hit: 12T (17.4%) 16.7%WR -$1.34 — well under 40% threshold
- cut-loser-CL-T1: 7T 0%WR -$0.96 — normal stop exits

**Signal Leaders (today):**
- bb-bounce-v2-long+: 11T 90.9%WR +$0.72 ✅ elite
- ema300-dip: 20T 70.0%WR +$0.29 ✅ workhorse
- accel-300-v3-long+: 13T 53.8%WR $0.00 (breakeven, CEO_PROTECTED)

**Signal Losers:**
- bb-bounce-short: 3T 33.3%WR -$0.35 ⚠️ KILLED
- r2-trend-long3: 1T 0%WR -$0.16 (already disabled)

**Changes:**
1. **KILLED bb-bounce-short** — 3T today, 33.3%WR, -$0.35, 2 consecutive losses (ME cut-loser-CL-T1, ALT atr_sl_hit). Below own 60% KILL_WR threshold. Trending worse.

**No Change Needed:**
- atr_sl_hit 17.4% — well under 40%
- Trade freq max 9/hr — under 20
- profit-monster-trail carrying system at 91.7% WR
- accel-300-v3-long+ CEO_PROTECTED until Sep 4 05:00
- MON open position -48.57% but SL not hit yet (0.026839 vs SL 0.02664636)

**Open Positions:** 5 ($78.60)
- DOT: +32.62% (ema300-dip)
- MNT: +25.61% (ema300-dip)
- ME: +7.90% (ema300-dip)
- BABY: -1.75% (ema300-dip, just opened)
- MON: -48.57% (accel-300-v3-long+, SL tight)

**Open Questions:**
- MON SL at 0.02664636 vs current 0.026839 — 0.7% away. 5x leverage magnifies.
- accel-300-v3-long+ auto-disable after CEO lock expires Sep 4 05:00? Currently breakeven today.

## [2026-09-03 18:06 UTC] Hourly Analysis

**Trades:** 13 closed last hour (10W 3L +$0.31, 76.9% WR)
**24h:** 72T 68.1%WR +$1.62
**Today:** 58T 67.2%WR +$0.45

**24h Exit Breakdown:**
- profit-monster-trail: 50T 91.7%WR +$2.78 (carrying system)
- atr_sl_hit: 11T 16.7%WR -$1.39 (15%, healthy)
- cut-loser-CL-T1: 7T 0%WR -$1.05

**Signal Performance (24h):**
- bb-bounce-v2-long+: 20T 85%WR +$0.74 ✅
- ema300-dip: 23T 73.9%WR +$0.62 ✅
- accel-300-v3-long+: 16T 50%WR -$0.44 ⚠️ CEO_PROTECTED
- r2-trend-long3: 2T 0%WR -$0.28 ⚠️ 1T from kill

**Changes:** None
**No Change Needed:**
- Kill criteria: r2-trend-long3 has 2T (needs 3T), monitoring
- atr_sl_hit 15% well under 40%
- Trade freq ~3/hr normal
- All open positions within SL range

**Open Questions:**
- r2-trend-long3 — if next trade is loss, auto-kill
- accel-300-v3-long+ CEO lock expires Sep 4 05:00

## FAVORITES Update — 2026-09-03 18:28 UTC
- Regime: NEUTRAL
- DEMOTE SYRUP (WR=57.1%, PnL=$0.10, 1 consecutive bad days, regime=NEUTRAL)
- DEMOTE PUMP (WR=50.0%, PnL=$-0.25, 1 consecutive bad days, regime=NEUTRAL)
- PROMOTE MNT (WR=60.0%, AvgPnL=0.93%, Trades=5)
- PROMOTE ETC (WR=66.7%, AvgPnL=1.41%, Trades=6)
- PROMOTE DOGE (WR=75.0%, AvgPnL=0.86%, Trades=8)
- PROMOTE YGG (WR=66.7%, AvgPnL=0.23%, Trades=9)

Final set: ['ASTER', 'BABY', 'BANANA', 'BCH', 'DOGE', 'DOT', 'DYDX', 'ETC', 'FOGO', 'INJ', 'KAS', 'LTC', 'ME', 'MNT', 'NXPC', 'SEI', 'STX', 'TURBO', 'USUAL', 'YGG']

## [2026-09-04 01:06 UTC] Hourly Analysis

**Trades:** 7 closed last hour (2W 5L -$0.27, 28.6% WR)
**24h:** 89T 64%WR +$0.22
**5 Open:** $60.90 (ETC, SAND, ALT, ACE, MET)

**24h Exit Breakdown:**
- profit-monster-trail: 61T 69%WR +$3.39 (carrying system)
- atr_sl_hit: 16T 19%WR -$1.78 (18%, healthy)
- cut-loser-CL-T1: 9T 22%WR -$1.31 (small losses, doing job)

**Signal Performance (24h):**
- bb-bounce-v2-long+: 23T 78%WR +$0.98 ✅
- ema300-dip: 38T 68%WR +$0.24 ✅
- accel-300-v3-long+: 18T 50%WR -$0.47 ⚠️ CEO_PROTECTED

**Changes:** None needed

**No Change Needed:**
- atr_sl_hit 18% well under 40%
- Trade freq 7/hr normal
- No signal has 0%WR with 3+T last hour
- Cut-loser working (small losses, not blowouts)
- accel-300-v3-long+ CEO_LOCK until Sep 4 05:00

**Open Questions:**
- accel-300-v3-long+ runs out of CEO protection in ~4h — review then

## [2026-09-04 02:06 UTC] Hourly Analysis

**Trades:** 0 closed last hour
**24h:** 83T 69%WR +$1.70 (profit-monster-trail carrying)
**5 Open:** $55.50 (SAND, ALT, ACE, MET, ZORA)

**24h Exit Breakdown:**
- profit-monster-trail: 56T 67%WR +$2.96 (carrying system)
- atr_sl_hit: 14T 14%WR -$1.52 (17%, healthy)
- cut-loser-CL-T1: 10T 30%WR -$1.49 (small losses, doing job)

**Signal Performance (24h):**
- bb-bounce-v2-long+: 20T 75%WR +$0.65 ✅
- ema300-dip: 38T 66%WR +$0.03 ✅
- accel-300-v3-long+: 17T 53%WR -$0.36 ⚠️ CEO_PROTECTED

**Changes:** None needed

**No Change Needed:**
- 0 trades last hour — quiet period
- atr_sl_hit 17% well under 40%
- No signal meets kill criteria (0%WR with 3+T last 24h)
- 5 open positions, $55.50 exposure normal
- accel-300-v3-long+ CEO_LOCK expires Sep 4 05:00

**Open Questions:**
- accel-300-v3-long+ runs out of CEO protection in ~3h — review then

## LOSERS Update — 2026-09-04 03:09 UTC
- REMOVE CC (insufficient data)
- REMOVE ONDO (WR=50.0%, PnL=$0.01, recovered)
- REMOVE GRASS (WR=50.0%, PnL=$-0.23, recovered)
- ADD ICP (WR=20.0%, PnL=$-0.46, wr_collapse (46.7% → 20.0%))
- ADD FIL (WR=42.9%, PnL=$-0.32, low_wr (42.9%))
- ADD BIGTIME (WR=40.0%, PnL=$-0.25, low_wr (40.0%))
- ADD NOT (WR=40.0%, PnL=$-0.20, low_wr (40.0%))
- ADD LDO (WR=40.0%, PnL=$-0.11, low_wr (40.0%))
- ADD CHIP (WR=40.0%, PnL=$0.04, low_wr (40.0%))

Final set: ['BIGTIME', 'CHIP', 'FIL', 'ICP', 'JUP', 'LDO', 'MET', 'NOT', 'W', 'XPL', 'ZEN']

## [2026-09-04 04:06 UTC] Hourly Analysis

**Trades:** 5 closed last hour (1W 4L -$0.63)
**24h:** 85T ~50%WR +$0.09

**Last Hour Breakdown:**
- profit-monster-trail: 1T +$0.06 (ALT)
- atr_sl_hit: 3T -$0.45 (SAND, ZORA, ACE)
- hard_sl: 1T -$0.24 (CASHCAT — deepest loss)

**24h Exit Breakdown:**
- profit-monster-trail: 54T 67%WR +$2.97 (carrying system)
- atr_sl_hit: 17T 18%WR -$1.97 (20% of closes, healthy)
- cut-loser-CL-T1: 10T 30%WR -$1.49 (small losses)

**Signal Performance (24h):**
- bb-bounce-v2-long+: 21T 71%WR +$0.51 ✅
- ema300-dip: 37T 68%WR +$0.08 ✅
- accel-300-v3-long+: 17T 53%WR -$0.36 ⚠️ CEO_LOCK expires 05:00 UTC
- accel-300-v3-short-: 2T 0%WR -$0.42 ⚠️ (needs 3+T to kill)
- bb-bounce-short: 2T 0%WR -$0.39 ⚠️ (needs 3+T to kill)

**Changes:** None — accel-300-v3-long+ lock expires at 05:00 UTC, will review then.

**No Change Needed:**
- atr_sl_hit 20% well under 40%
- Trade freq 5/hr normal
- No signal meets kill criteria (0%WR with 3+T last hour)
- Short signals 0%WR but only 2T each — monitor next hour
- Choppy period (5 negative hours since midnight) but 24h still flat

**Open Questions:**
- accel-300-v3-long+ lock expires 05:00 — review signal quality then
- Short signals trending toward kill threshold if no wins next hour

## [2026-09-04 05:06 UTC] Hourly Analysis

**Trades:** 3 closed last hour (0W 3L -$0.18)
- ENA cascade-long: atr_sl_hit -$0.16
- ENA accel-short: cascade_flip -$0.06
- ALT ema300-dip: profit-monster-trail +$0.04

**24h:** 87T 59.8%WR -$0.97

**24h Exit Breakdown:**
- profit-monster-trail: 54T +$3.03 (carrying system)
- atr_sl_hit: 18T -$2.13 (20.7% healthy)
- cut-loser-CL-T1: 10T -$1.49

**24h Signal Performance:**
- bb-bounce-v2-long+: 21T 71%WR +$0.51 ✅
- ema300-dip: 37T 70%WR +$0.14 ✅
- accel-300-v3-long+: 17T 53%WR -$0.36 (CEO killed, NEVER_REENABLE)
- accel-300-v3-short-: 3T 0%WR -$0.48 ❌ KILLED

**Changes:**
1. KILLED ACCEL_300_V3_SHORT_ENABLED = False — 3T/0%WR/-$0.48 24h, 0%WR 7d. Meets kill criteria.

**No Change Needed:**
- atr_sl_hit 20.7% under 40% threshold
- Trade freq 3/hr normal
- 5 open positions ($64.30) all small
- profit-monster-trail carrying system at $3.03

**Open Questions:**
- 24h still negative -$0.97 despite 59.8% WR — SL losses eating profits
- Short signals collectively 0%WR (all killed or below threshold)

## FAVORITES Update — 2026-09-04 06:00 UTC
- Regime: NEUTRAL
- DEMOTE BANANA (WR=50.0%, PnL=$-0.03, 1 consecutive bad days, regime=NEUTRAL)
- DEMOTE ETC (WR=57.1%, PnL=$0.01, 1 consecutive bad days, regime=NEUTRAL)
- DEMOTE STX (WR=57.1%, PnL=$-0.14, 1 consecutive bad days, regime=NEUTRAL)
- DEMOTE BCH (WR=57.1%, PnL=$-0.01, 1 consecutive bad days, regime=NEUTRAL)
- DEMOTE DYDX (WR=57.1%, PnL=$-0.21, 1 consecutive bad days, regime=NEUTRAL)
- PROMOTE POL (WR=75.0%, AvgPnL=0.61%, Trades=8)
- PROMOTE GMT (WR=71.4%, AvgPnL=0.19%, Trades=7)
- PROMOTE ONDO (WR=60.0%, AvgPnL=0.15%, Trades=5)

Final set: ['ASTER', 'BABY', 'DOGE', 'DOT', 'FOGO', 'GMT', 'INJ', 'KAS', 'LTC', 'ME', 'MNT', 'NXPC', 'ONDO', 'POL', 'SEI', 'TURBO', 'USUAL', 'YGG']

## LOSERS Update — 2026-09-04 06:05 UTC
- REMOVE BIGTIME (insufficient data)
- ADD CASHCAT (WR=20.0%, PnL=$-0.50, low_wr (20.0%))
- ADD SAND (WR=40.0%, PnL=$-0.30, low_wr (40.0%))
- ADD APT (WR=40.0%, PnL=$-0.23, wr_collapse (60.0% → 40.0%))
- ADD ARB (WR=44.4%, PnL=$-0.19, low_wr (44.4%))
- ADD ENA (WR=40.0%, PnL=$0.00, low_wr (40.0%))

Final set: ['APT', 'ARB', 'CASHCAT', 'CHIP', 'ENA', 'FIL', 'ICP', 'JUP', 'LDO', 'MET', 'NOT', 'SAND', 'W', 'XPL', 'ZEN']

## [2026-09-04 07:06 UTC] Hourly Analysis

**Trades:** 1 closed last hour (1L)
**PnL:** -$0.11 (0%WR)

**24h:** 84T 59.5%WR
**24h Exit Breakdown:**
- profit-monster-trail: 51T +$2.85 (carrying system)
- atr_sl_hit: 16T -$1.75 (19.5% — healthy)
- cut-loser-CL-T1: 10T -$1.46 (main drag)
- hard_sl: 2T -$0.51

**24h Signal Performance:**
- bb-bounce-v2-long+: 20T 75%WR +$0.66 ✅
- ema300-dip: 34T 67.6%WR -$0.01 (net flat — trailing covers losses)
- accel-300-v3-long+: 16T 56.3%WR -$0.13
- slow-grind-: 2T 50%WR -$0.02
- accel-300-v3-short-: 3T 0%WR -$0.48 (KILLED)

**Changes:** None

**No Change Needed:**
- atr_sl_hit 19.5% under 40% threshold ✅
- No 0%WR signal with 3+T last hour (kill criteria not met)
- Trade freq 1/hr normal (quiet period)
- 5 open positions ($64.30) all small
- profit-monster-trail +$2.85 carrying system
- All previously killed signals remain disabled

**Open Questions:**
- CL-T1 exits 10T -$1.46 in 24h — 7 from ema300-dip. Signal still net positive via trailing but CL exits erode profits. Consider monitoring if CL-T1 share of exits grows above 15%.
- 4 consecutive negative hours (03-07 UTC) — choppy NEUTRAL regime, not alarming

## [2026-09-04 07:07 UTC] Hourly Analysis

**Trades:** 1 closed (1W, 0L)
**PnL:** +$0.07 (100%WR last hour)

**24h:** 83T 60.2%WR -$0.70
**24h Exit Breakdown:**
- profit-monster-trail: 51T +$2.86 (carrying system)
- atr_sl_hit: 16T -$1.75 (19.3% — healthy)
- cut-loser-CL-T1: 10T -$1.46 (main drag)
- hard_sl: 2T -$0.51

**24h Signal Performance:**
- bb-bounce-v2-long+: 20T 75%WR +$0.66 ✅
- ema300-dip: 35T 68.6%WR +$0.03 ✅
- accel-300-v3-long+: 16T 56.3%WR -$0.13 (monitor)
- accel-300-v3-short-: 3T 0%WR -$0.48 (KILLED)
- bb-bounce-short: 2T 0%WR -$0.39 (KILLED)

**Changes:** None

**No Change Needed:**
- atr_sl_hit 19.3% under 40% threshold ✅
- No 0%WR signal with 3+T last hour (kill criteria not met)
- Trade freq 3/hr normal
- 4 open positions ($53.20) all small
- profit-monster-trail +$2.86 carrying system
- All previously killed signals remain disabled
- Hourly trend recovering after choppy 01-05 UTC

**Open Questions:**
- CL-T1 exits 10T -$1.46 in 24h — continues to be main PnL drag. 7 from ema300-dip but signal still net positive via trailing.
- accel-300-v3-long+ at 56.3%WR -$0.13 — borderline. Not kill threshold (needs 0%WR with 3+T last hour). Monitor if WR drops below 50%.
