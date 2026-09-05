

## [2026-09-04 15:06 UTC] Hourly Analysis

**Trades:** 0 closed last hour (system flat since 12:47 UTC)
**24h Context:** 84T 59.5%WR -$1.10 | atr_sl_hit 25% (under 40%)

**24h Exit Breakdown:**
- profit-monster-trail: 49T (58%) avg +$0.056 — carrying system
- atr_sl_hit: 21T (25%) avg -$0.118 — under 40% threshold, acceptable
- cut-loser-CL-T1: 7T avg -$0.150 — normal
- hard_sl: 4T avg -$0.205 — rare, acceptable

**Signal Leaders (24h):**
- bb-bounce-v2-long+: 16T 68.8%WR +$0.38 ⭐
- continuation+: 4T 100%WR +$0.30 ⭐
- ema300-dip: 38T 60.5%WR -$1.03 (biggest drag but 60.5% WR)
- accel-300-v3-long+: 14T 50%WR -$0.26 (killed, draining legacy)

**Hourly Pattern (12h):**
- 12:00 UTC was bad: 7T 14.3%WR -$1.17 (ema300-dip disaster)
- 08:00-11:00 UTC: All green hours (100-75% WR)
- 13:00-15:00 UTC: Dead period, no trades

**Kill Criteria Check:**
- No 0%WR signal with 3+T in last hour → none to kill
- atr_sl_hit 25% → well under 40% threshold
- accel-300-v3-long+: already killed, draining legacy trades
- accel-300-v3-short-: already killed

**Changes:** None needed.

**No Change Needed:**
- Kill criteria not met: no signal at 0%WR with 3+T last hour
- System flat — no positions, no new entries since 12:47
- atr_sl_hit 25% — healthy, well under 40%
- ema300-dip: 60.5%WR 24h but -$1.03 PnL (R:R issue, not kill candidate — WR too high)
- Trade freq 0/hr — quiet market, normal for UTC afternoon

**Open Questions:**
- ema300-dip R:R problem persists: 60.5%WR but -$1.03. Winning exits avg +$0.057, losing exits avg -$0.149. Not a kill (WR too high) but worth monitoring.
- 12:00 UTC ema300-dip cluster: 7 entries in one hour, 6 losses. Signal may need cooldown adjustment if this pattern repeats.

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

## [2026-09-04 08:06 UTC] Hourly Analysis

**Trades:** 1 closed (1W, 0L)
**PnL:** +$0.03 (100%WR last hour)

**24h:** 83T 60.2%WR -$0.70
**24h Exit Breakdown:**
- profit-monster-trail: 52T +$2.89 (carrying system)
- atr_sl_hit: 16T -$1.75 (19.3% — healthy)
- cut-loser-CL-T1: 10T -$1.46 (main drag)
- hard_sl: 2T -$0.51

**24h Signal Performance:**
- bb-bounce-v2-long+: 20T 75%WR +$0.66 ✅
- ema300-dip: 35T 68.6%WR +$0.03 ✅
- accel-300-v3-long+: 16T 56.3%WR -$0.13 (monitor)
- accel-300-v3-short-: 3T 0%WR -$0.48 (KILLED)
- bb-bounce-short: 2T 0%WR -$0.39 (KILLED)

**Open:** 4 positions ($53.20): GMT SHORT, ETH LONG, INJ SHORT, MET SHORT

**Changes:** None

**No Change Needed:**
- atr_sl_hit 19.3% under 40% threshold ✅
- No 0%WR signal with 3+T last hour (kill criteria not met)
- Trade freq 1/hr — quiet period, no overtrading
- 4 open positions ($53.20) all small
- profit-monster-trail +$2.89 carrying system
- All previously killed signals remain disabled

**Open Questions:**
- CL-T1 exits 10T -$1.46 in 24h — continues to be main PnL drag. 7 from ema300-dip but signal still net positive via trailing.
- accel-300-v3-long+ at 56.3%WR -$0.13 — borderline. Not kill threshold (needs 0%WR with 3+T last hour). Monitor if WR drops below 50%.

## [2026-09-04 10:06 UTC] Hourly Analysis

**Trades:** 1 closed (1W, 0L)
**PnL:** +$0.02 (100%WR last hour)

**24h:** 84T 60.7%WR -$0.66 (improving from -$0.70)
**24h Exit Breakdown:**
- profit-monster-trail: 52T +$3.07 (carrying system)
- atr_sl_hit: 19T -$1.64 (19.3% — healthy)
- cut-loser-CL-T1: 9T -$1.39 (improved from 10T)
- hard_sl: 2T -$0.51

**24h Signal Performance:**
- bb-bounce-v2-long+: 21T 76.2%WR +$0.68 ✅
- continuation+: 2T 100%WR +$0.18 ✅
- ema300-dip: 32T 68.8%WR +$0.11 ✅
- accel-300-v3-long+: 15T 53.3%WR -$0.16 (borderline, monitor)
- accel-300-v3-short-: 4T 25%WR -$0.26 (killed, still has stragglers)

**Open:** 4 positions ($53.20): GMT SHORT, ETH LONG, INJ SHORT, MET SHORT

**6h Trend:** All green hours 05-10 UTC. 08:00 best hour (3T +$0.33). Recovery after choppy midnight period.

**Changes:** None

**No Change Needed:**
- atr_sl_hit 19.3% under 40% threshold ✅
- No 0%WR signal with 3+T last hour (kill criteria not met)
- Trade freq 1/hr — quiet period, no overtrading
- 4 open positions ($53.20) all small
- profit-monster-trail +$3.07 24h carrying system
- 6h trend all green, system recovering

**Open Questions:**
- accel-300-v3-long+ at 53.3%WR -$0.16 — borderline. Not kill threshold. Monitor if WR drops below 50%.
- CL-T1 exits down to 9T -$1.39 — improving. 7 from ema300-dip but signal still net positive.

## [2026-09-04 11:06 UTC] Hourly Analysis

**Trades:** 3 closed (3W, 0L)
**PnL:** +$0.15 (100%WR last hour)

**24h:** ~88T, profit-monster-trail +$3.22 carrying system
**24h Exit Breakdown:**
- profit-monster-trail: 55T +$3.22 (AVG +$0.059) ✅
- atr_sl_hit: 19T -$1.64 (21.6% — under 40% threshold) ✅
- cut-loser-CL-T1: 9T -$1.39
- hard_sl: 2T -$0.51

**24h Signal Performance:**
- bb-bounce-v2-long+: 21T 76.2%WR +$0.68 ✅
- continuation+: 4T 100%WR +$0.30 ✅
- ema300-dip: 33T 69.7%WR +$0.14 ✅
- accel-300-v3-long+: 15T 53.3%WR -$0.16 (borderline, monitor)
- accel-300-v3-short-: 4T 25%WR -$0.26 (killed)
- bb-bounce-short: 2T 0%WR -$0.39 (killed)

**Open:** 5 ema300-dip LONGs ($84.10): NXPC, SEI, YGG, GMT, ALT

**Changes:** None

**No Change Needed:**
- atr_sl_hit 21.6% under 40% threshold ✅
- No 0%WR signal with 3+T last hour (kill criteria not met)
- Trade freq 3/hr normal
- 5 open positions ($84.10) reasonable exposure
- profit-monster-trail +$3.22 24h carrying system

**Open Questions:**
- accel-300-v3-long+ at 53.3%WR -$0.16 — borderline. Not kill threshold. Monitor if WR drops below 50%.

## [2026-09-04 14:06 UTC] Hourly Analysis

**Trades:** 0 closed last hour (quiet period)
**24h:** 92T, ~60% WR, -$0.51
**Last 2h:** 7T (1W 6L, -$1.13) — ema300-dip cluster stopped out

**24h Exit Breakdown:**
- profit-monster-trail: 54T +$3.19 ✅
- atr_sl_hit: 23T -$2.54 (25% — under 40%)
- cut-loser-CL-T1: 8T -$1.27
- hard_sl: 4T -$0.82

**24h Signal Performance:**
- ema300-dip: 39T 61.5%WR -$0.91 (R:R 0.39:1 — losses 2.5x wins)
- bb-bounce-v2-long+: 19T 73.7%WR +$0.61 ✅
- continuation+: 4T 100%WR +$0.30 ✅
- accel-300-v3-long+: 15T 53.3%WR -$0.16 (borderline)

**Changes:**
1. Tightened ema300-dip trend filters: MIN_TREND_STRENGTH 75→85, MIN_EMA_SLOPE -0.4→0.0 — signal had 0.39:1 R:R, entering during choppy markets where EMA300 support fails. Require positive EMA slope and stronger trend confirmation.

**No Change Needed:**
- atr_sl_hit 25% under 40% threshold ✅
- No 0%WR signal with 3+T last hour (kill criteria not met)
- Trade freq 0/hr quiet period
- 0 open positions (clean slate)
- profit-monster-trail +$3.19 24h carrying system

**Open Questions:**
- accel-300-v3-long+ at 53.3%WR -$0.16 — borderline. Monitor if WR drops below 50%.
- ema300-dip now requires positive slope — will reduce trade frequency but should improve R:R.

## [2026-09-04 15:06 UTC] Hourly Analysis

**Trades:** 0 closed last hour (quiet period)
**24h:** 76T, 60.5%WR, -$0.71
**Open:** 0 positions (clean slate)

**24h Exit Breakdown:**
- profit-monster-trail: 43T +$2.45 ✅ (carrying system)
- atr_sl_hit: 20T -$2.34 (26.3% — under 40%)
- cut-loser-CL-T1: 7T -$1.05
- hard_sl: 4T -$0.82

**24h Signal Performance:**
- profit-monster-trail: 43T +$2.45 (system backbone)
- bb-bounce-v2-long+: 15T 66.7%WR +$0.33 ✅
- continuation+: 4T 100%WR +$0.30 ✅
- ema300-dip: 36T 61.1%WR -$1.04 (R:R still poor, fix deployed this hour)
- accel-300-v3-long+: 9T 55.6%WR -$0.33 (borderline)

**Changes:** None

**No Change Needed:**
- atr_sl_hit 26.3% under 40% threshold ✅
- No 0%WR signal with 3+T last hour (kill criteria not met)
- Trade freq 0/hr quiet period
- 0 open positions (clean slate)
- ema300-dip fix deployed last hour (MIN_TREND_STRENGTH 85, MIN_EMA_SLOPE 0.0) — need more data to evaluate
- profit-monster-trail +$2.45 24h carrying system

**Open Questions:**
- accel-300-v3-long+ at 55.6%WR -$0.33 — borderline but not kill threshold. Monitor.
- ema300-dip R:R still 0.39:1 in 24h — tight filters need more time to show effect.

## [2026-09-04 18:00 UTC] Hourly Analysis

**Trades:** 0 closed last hour (system flat since 17:05)
**PnL:** $0.00 (0 trades)
**24h:** 70T 55.7% WR -$1.96

**24h Exit Breakdown:**
- profit-monster-trail: 38T (54%) avg +$0.052 — carrying system
- atr_sl_hit: 20T (29%) avg -$0.117 — under 40% threshold ✓
- cut-loser-CL-T1: 6T avg -$0.155 — normal
- hard_sl: 4T avg -$0.205 — rare

**Signal Leaders (24h):**
- continuation+: 4T 100%WR +$0.30 ⭐
- bb-bounce-v2-long+: 14T 64.3%WR +$0.14 ⭐
- ema300-dip: 34T 58.8%WR -$1.13 (R:R drag, not kill — WR too high)
- accel-300-v3-long+: 6T 50%WR -$0.40 (killed, draining legacy)
- accel-300-v3-short-: 4T 25%WR -$0.26 (killed, draining legacy)

**Kill Criteria Check:**
- No 0%WR signal with 3+T in last hour → none to kill
- atr_sl_hit 29% → well under 40% threshold
- accel-300-v3-long+ and short-: already killed, draining legacy trades

**Changes:** None needed.

**No Change Needed:**
- Kill criteria not met: no signal at 0%WR with 3+T last hour
- System flat — no positions, no new entries since 17:05
- atr_sl_hit 29% — healthy, well under 40%
- ema300-dip 58.8%WR -$1.13: R:R problem (winners avg +$0.057, losers avg -$0.149). Not a kill (WR too high)
- Trade freq 0/hr — quiet market

**Open Positions:**
- ME LONG via ema300-dip: $19.90 size, $0.00 PnL
- HBAR SHORT via ema300-dip-short: $11.10 size, $0.00 PnL

**Open Questions:**
- ema300-dip R:R problem persists across multiple days. Winning exits are small (+$0.057 avg) while losing exits are 2.6x larger (-$0.149 avg). Worth tuning TP/SL ratio if this pattern continues.
- System flat for 1+ hours — quiet afternoon period, normal.

## [2026-09-04 19:00 UTC] Hourly Analysis

**Trades:** 1 closed last hour (1W +$0.03)
**24h:** 64T 56.3%WR +$1.80 gross → -$1.89 net

**24h Exit Breakdown:**
- profit-monster-trail: 35T (58%) avg +$0.051 — carrying system
- atr_sl_hit: 20T (33%) avg -$0.117 — under 40% ✓
- cut-loser-CL-T1: 5T avg -$0.148
- hard_sl: 3T avg -$0.183

**Signal Leaders (24h):**
- continuation+: 4T 100%WR +$0.30 ⭐
- bb-bounce-v2-long+: 14T 64.3%WR +$0.14 ⭐
- ema300-dip: 31T 54.8%WR -$1.46 (R:R drag)
- accel-300-v3-short-: 4T 25%WR -$0.26 (draining legacy)

**Changes:** None needed.

**No Change Needed:**
- Kill criteria not met (no 0%WR signal with 3+T last hour)
- atr_sl_hit 33% — healthy, under 40%
- ema300-dip tightened yesterday (MIN_TREND_STRENGTH 85, MIN_EMA_SLOPE 0.0) — need more data
- Trade freq 1/hr — quiet market
- 1 open position ($19.90)

**Open Questions:**
- ema300-dip R:R still problematic (avg_loss 2.5x avg_win). If tightened filters don't show improvement by tomorrow, consider reducing TP target or widening SL.

## [2026-09-04 20:00 UTC] Hourly Analysis

**Trades:** 0 closed last hour
**24h:** 60T 53.3%WR -$1.99 net

**24h Exit Breakdown:**
- profit-monster-trail: 31T (52%) avg +$0.055 — carrying system
- atr_sl_hit: 20T (33%) avg -$0.117 — under 40% ✓
- cut-loser-CL-T1: 5T avg -$0.148
- hard_sl: 3T avg -$0.183

**Signal Leaders (24h):**
- continuation+: 4T 100%WR +$0.30 ⭐
- bb-bounce-v2-long+: 14T 64.3%WR +$0.14 ⭐
- ema300-dip: 29T 51.7%WR -$1.59 (R:R drag)

**Changes:** None needed.

**No Change Needed:**
- Kill criteria not met (no 0%WR signal with 3+T last hour)
- atr_sl_hit 33% — healthy, under 40%
- Trade freq 0/hr — quiet market
- 3 open positions ($42.10)

**Open Positions:**
- ME LONG via ema300-dip: $19.90 size
- ETC SHORT via ema300-dip-short: $11.10 size
- STX SHORT via ema300-dip-short: $11.10 size

## [2026-09-04 21:00 UTC] Hourly Analysis

**Trades:** 0 closed last hour
**24h:** 55T 52.7%WR -$1.39 net

**24h Exit Breakdown:**
- profit-monster-trail: 27T (49%) avg +$0.054 — carrying system ⭐
- atr_sl_hit: 19T (34.5%) avg -$0.116 — under 40% ✓
- cut-loser-CL-T1: 5T avg -$0.148
- hard_sl: 3T avg -$0.183

**Signal Leaders (24h):**
- continuation+: 4T 100%WR +$0.30 ⭐
- bb-bounce-v2-long+: 12T 58.3%WR -$0.05 (breakeven)
- ema300-dip: 28T 50%WR -$1.63 (R:R drag — tightened at 14:06, no post-tightening data yet)
- accel-300-v3-short-: 4T 25%WR -$0.26 (not kill threshold)

**Changes:** None needed.

**No Change Needed:**
- Kill criteria not met (0T last hour, no 0%WR signal with 3+T)
- atr_sl_hit 34.5% — healthy, under 40%
- ema300-dip tightened at 14:06 UTC — only 7h post-change, no data to evaluate yet
- Trade freq 0/hr — quiet market
- 4 open positions ($53.20) all slightly negative, normal
- profit-monster-trail still carrying system PnL

**Open Positions:**
- ME LONG via ema300-dip: $19.90 size
- STX SHORT via ema300-dip-short combo: $11.10
- ETC SHORT via ema300-dip-short: $11.10
- NOT SHORT via ema300-dip-short: $11.10

**Open Questions:**
- ema300-dip tightening (MIN_TREND_STRENGTH 85, MIN_EMA_SLOPE 0.0) needs more trades to evaluate. Recheck tomorrow.
- accel-300-v3-short- consistently low WR (25%) but trade count too low to auto-kill. If it fires 3+ times next hour with losses, will kill.

## [2026-09-04 22:00 UTC] Hourly Analysis

**Trades:** 0 closed last hour
**24h:** 52T 48%WR -$2.07

**24h Exit Breakdown:**
- profit-monster-trail: 25T (48%) avg +$0.055 — carrying system ⭐
- atr_sl_hit: 18T (34.6%) avg -$0.116 — under 40% ✓
- cut-loser-CL-T1: 5T avg -$0.148
- hard_sl: 3T avg -$0.183
- cascade_flip_-0.46%: 1T avg -$0.060

**Signal Leaders (24h, 3+T):**
- continuation+: 4T 100%WR +$0.30 ⭐
- bb-bounce-v2-long+: 11T 54.5%WR -$0.07 (breakeven)
- ema300-dip: 26T 50%WR -$1.60 (tightened at 14:06 UTC, 8h post-change)
- accel-300-v3-short-: 4T 25%WR -$0.26 (not kill threshold)

**Changes:** None needed.

**No Change Needed:**
- Kill criteria not met (no 0%WR signal with 3+T last hour)
- atr_sl_hit 34.6% — healthy, under 40%
- ema300-dip tightened at 14:06 UTC — 8h post-change, needs overnight data
- Trade freq 0/hr — quiet market, ~2/hr average
- 5 open positions ($73.10)
- profit-monster-trail carrying system PnL

**Open Positions:**
- NXPC LONG via bb-bounce-v2-long+: $19.90 (opened 20:36 UTC)
- NOT SHORT via ema300-dip-short: $11.10 (opened 19:32 UTC)
- ETC SHORT via ema300-dip-short: $11.10 (opened 18:37 UTC)
- STX SHORT via ema300-dip-short: $11.10 (opened 18:31 UTC)
- ME LONG via ema300-dip: $19.90 (opened 17:05 UTC)

**Open Questions:**
- accel-300-v3-short- at 25%WR with 4T — borderline. If it fires next hour with losses, will kill.
- ema300-dip needs more post-tightening trades to evaluate.

## [2026-09-04 23:06 UTC] Hourly Analysis

**Trades:** 0 closed last hour
**24h:** 47T ~48%WR -$2.07

**24h Exit Breakdown:**
- profit-monster-trail: 20T (43%) avg +$0.060 — carrying system
- atr_sl_hit: 18T (38%) avg -$0.116 — under 40% ✓
- cut-loser-CL-T1: 5T avg -$0.148
- hard_sl: 3T avg -$0.183

**Changes:** None needed.

**No Change Needed:**
- Kill criteria not met (no 0%WR signal with 3+T last hour)
- atr_sl_hit 38% — under 40% ✓
- ema300-dip tightened at 14:06 UTC (10h post-change, overnight data pending)
- accel-300-v3-short- 4T 25%WR below kill threshold
- Trade freq 0/hr quiet
- 5 open positions ($73.10)

**Open Questions:**
- accel-300-v3-short- borderline (25%WR, 4T)
- ema300-dip needs post-tightening evaluation

## [2026-09-04 00:06 UTC] Hourly Analysis

**Trades:** 1 closed last hour (1W +$0.13)
**24h:** 44T ~48%WR -$1.89

**24h Exit Breakdown:**
- profit-monster-trail: 20T (45%) avg +$0.066 — carrying system
- atr_sl_hit: 15T (34%) avg -$0.108 — healthy, under 40% ✓
- cut-loser-CL-T1: 4T avg -$0.140
- hard_sl: 3T avg -$0.183
- cascade_flip: 1T avg -$0.060

**Changes:** None needed.

**No Change Needed:**
- Kill criteria not met (no 0%WR signal with 3+T last hour)
- atr_sl_hit 34% — under 40% ✓
- ema300-dip tightened at 14:06 UTC — post-tightening: 2T 100%WR +$0.16 (tiny sample but positive early signal)
- accel-300-v3-short- 4T 25%WR below kill threshold
- Trade freq 1/hr — quiet market
- 4 open positions ($62.00)
- 6h trend: only 2 trades total — very quiet

**Open Positions:**
- NXPC LONG via bb-bounce-v2-long+: $19.90 (opened 20:36 UTC)
- ETC SHORT via ema300-dip-short: $11.10 (opened 18:37 UTC)
- STX SHORT via ema300-dip-short,rs-r37: $11.10 (opened 18:31 UTC)
- ME LONG via ema300-dip: $19.90 (opened 17:05 UTC)

**Open Questions:**
- accel-300-v3-short- borderline (25%WR, 4T) — if next trades are losses, will kill
- ema300-dip post-tightening needs more data (2T sample too small)
- Quiet market overnight — system in steady state

## [2026-09-05 01:06 UTC] Hourly Analysis

**Trades:** 1 closed last hour (0W 1L -$0.11)
**24h:** 41T ~46%WR -$1.25

**24h Exit Breakdown:**
- profit-monster-trail: 19T (46%) avg +$0.062 — carrying system
- atr_sl_hit: 13T (32%) avg -$0.127 — under 40% ✓
- cut-loser-CL-T1: 5T avg -$0.134
- hard_sl: 3T avg -$0.183
- cascade_flip: 1T avg -$0.060

**24h Signal Breakdown:**
- ema300-dip: 18T 44.4%WR -$1.35 (R:R drag)
- bb-bounce-v2-long+: 6T 50%WR -$0.02 (neutral)
- accel-300-v3-short-: 4T 25%WR -$0.26 (borderline)
- continuation+: 4T 100%WR +$0.30 (star)

**Changes:** None needed.

**No Change Needed:**
- Kill criteria not met (no 0%WR signal with 3+T last hour)
- atr_sl_hit 32% — under 40% ✓
- ema300-dip post-tightening: 3T 66.7%WR +$0.05 (positive trend)
- accel-300-v3-short- borderline (25%WR, 4T) — monitoring
- Trade freq 1/hr — quiet overnight
- 5 open positions ($81.90)

**Open Questions:**
- accel-300-v3-short- borderline — if next trades are losses, will kill
- ema300-dip post-tightening needs continued monitoring
- Quiet overnight — system in steady state

## [2026-09-05 02:07 UTC] Hourly Analysis

**Trades:** 3 closed last hour (2W 1L, net +$0.26)
**24h:** 37T ~54%WR net ~+$0.28

**24h Exit Breakdown:**
- profit-monster-trail: 17T (46%) avg +$0.075 — carrying system
- atr_sl_hit: 11T (30%) avg -$0.127 — under 40% ✓
- cut-loser-CL-T1: 4T avg -$0.130
- hard_sl: 3T avg -$0.183
- profit-monster-T1: 1T avg +$0.040

**24h Signal Breakdown:**
- ema300-dip: 16T 50%WR -$1.08 (R:R drag, tightened yesterday, post-tighten trending positive)
- accel-300-v3-short-: 4T 25%WR -$0.26 (borderline, not kill threshold)
- continuation+: 4T 100%WR +$0.30 (star)
- bb-bounce-v2-long+: 3T 66.7%WR -$0.08 (neutral)
- open-skies+: 1T 100%WR +$0.34

**Changes:** None needed.

**No Change Needed:**
- Kill criteria not met (no 0%WR signal with 3+T last hour)
- atr_sl_hit 30% — under 40% ✓
- ema300-dip post-tightening: positive early trend, needs continued monitoring
- accel-300-v3-short- borderline — monitoring
- Trade freq 1/hr — quiet overnight
- 3 open positions ($50.90)

**Open Questions:**
- accel-300-v3-short- borderline — will kill if next trades are losses
- ema300-dip post-tightening performance overnight

## [2026-09-05 03:07 UTC] Hourly Analysis

**Trades:** 3 closed (2W 1L, net +$0.21)
**24h:** 37T 54.1%WR -$1.27

**24h Exit Breakdown:**
- profit-monster-trail: 17T (46%) +$1.24 — carrying system
- atr_sl_hit: 11T (30%) -$1.40 — under 40% ✓
- cut-loser-CL-T1: 4T -$0.54
- hard_sl: 3T -$0.55

**24h Signal Breakdown:**
- open-skies+: 2T 100%WR +$0.41 (star)
- continuation+: 4T 100%WR +$0.30 (star)
- ema300-dip: 14T 50%WR -$1.00 (R:R drag, post-tightening improving)
- accel-300-v3-short-: 4T 25%WR -$0.26 (borderline, monitoring)

**Changes:** None needed.

**No Change Needed:**
- Kill criteria not met (no 0%WR signal with 3+T last hour)
- atr_sl_hit 30% — under 40% ✓
- Trade freq 3/hr — normal overnight
- 3 open positions ($42.10) — light exposure
- open-skies+ and continuation+ both 100%WR stars

**Open Questions:**
- accel-300-v3-short- borderline — will kill if next trades are losses
- ema300-dip post-tightening continuing positive trend

## [2026-09-05 04:06 UTC] Hourly Analysis

**Trades:** 1 closed (1W +$0.14)
**24h:** 38T 50%WR -$0.86

**24h Exit Breakdown:**
- profit-monster-trail: 18T (47%) +$1.38 — carrying system
- atr_sl_hit: 11T (29%) -$1.40 — under 40% ✓
- cut-loser-CL-T1: 4T -$0.54
- hard_sl: 3T -$0.55

**24h Signal Breakdown:**
- ema300-dip: 14T 50%WR -$1.00 (R:R drag, post-tightening improving)
- accel-300-v3-short-: 4T 25%WR -$0.26 (borderline)
- continuation+: 4T 100%WR +$0.30 (star)
- open-skies+: 3T 100%WR +$0.55 (star)
- bb-bounce-v2-long+: 3T 66.7%WR -$0.08

**Changes:** None needed.

**No Change Needed:**
- Kill criteria not met (no 0%WR signal with 3+T last hour)
- atr_sl_hit 29% — under 40% ✓
- Trade freq 1/hr — quiet overnight
- 4 open positions ($53.20) — light exposure
- open-skies+ and continuation+ both 100%WR stars
- ema300-dip post-tightening 66.7%WR — improving trend

**Open Questions:**
- accel-300-v3-short- borderline — will kill if next trades are losses
- ema300-dip post-tightening continued improvement overnight

## [2026-09-05 05:06 UTC] Hourly Analysis

**Trades:** 0T last hour (quiet overnight). 34T/24h 61.8%WR -$0.38

**24h Exit Breakdown:**
- profit-monster-trail: 17T (50%) +$1.32 — carrying system
- atr_sl_hit: 8T (23.5%) -$0.95 — under 40% ✓
- cut-loser-CL-T1: 4T -$0.54
- hard_sl: 2T -$0.31

**24h Signal Breakdown:**
- ema300-dip: 14T 50%WR -$0.94 (R:R drag, post-tightening improving)
- continuation+: 4T 100%WR +$0.30 (star)
- open-skies+: 3T 100%WR +$0.55 (star)
- accel-300-v3-short-: 2T 50%WR +$0.16 (improved from 25%WR)
- bb-bounce-v2-long+: 2T 100%WR +$0.06

**Changes:** None needed.

**No Change Needed:**
- Kill criteria not met (no 0%WR signal with 3+T last hour)
- atr_sl_hit 23.5% — under 40% ✓
- Trade freq 0/hr — quiet overnight
- 5 open positions ($73.10) — light exposure
- open-skies+ and continuation+ both 100%WR stars
- ema300-dip post-tightening 50%WR — improving trend
- accel-300-v3-short- improved to 50%WR — no longer borderline

**Open Questions:**
- ema300-dip still biggest drag but trending positive post-tightening
- System essentially breakeven over 24h — waiting for stars to compound

## [2026-09-05 05:07 UTC] Hourly Analysis

**Trades:** 1T last hour (1W +$0.03 FOGO bb-bounce-v2-long+). 32T/24h 53.1%WR -$1.47

**24h Exit Breakdown:**
- profit-monster-trail: 17T (53%) +$1.31 — carrying system
- atr_sl_hit: 7T (21.9%) -$0.79 — under 40% ✓
- cut-loser-CL-T1: 4T -$0.54
- hard_sl: 2T -$0.31
- profit-monster-T1: 2T +$0.16

**24h Signal Breakdown:**
- ema300-dip: 13T 46.2%WR -$0.98 (biggest drag, avg -$0.075/trade)
- continuation+: 4T 100%WR +$0.30 (star)
- open-skies+: 3T 100%WR +$0.55 (star)
- bb-bounce-v2-long+: 3T 100%WR +$0.09 (star)
- ema300-dip-short: 4T 50%WR -$0.15 (marginal)
- accel-300-v3-short-: 1T 100%WR +$0.22 (improved)

**Changes:** None needed.

**No Change Needed:**
- Kill criteria not met (no 0%WR signal with 3+T last hour)
- atr_sl_hit 21.9% — under 40% ✓
- Trade freq 1/hr — quiet overnight
- 5 open positions ($64.30) — light exposure
- open-skies+, continuation+, bb-bounce-v2-long+ all 100%WR stars
- ema300-dip only underperformer (46.2%WR, -$0.98) — not killable

**Open Questions:**
- ema300-dip still biggest drag at -$0.98/24h but not killable (46.2%WR)
- System essentially breakeven — stars carrying, drag limiting upside

## FAVORITES Update — 2026-09-05 06:00 UTC
- Regime: NEUTRAL
- DEMOTE ONDO (WR=33.3%, PnL=$-0.06, 1 consecutive bad days, regime=NEUTRAL)
- DEMOTE ASTER (WR=57.1%, PnL=$-0.06, 1 consecutive bad days, regime=NEUTRAL)
- DEMOTE GMT (WR=55.6%, PnL=$-0.35, 1 consecutive bad days, regime=NEUTRAL)
- PROMOTE AIXBT (WR=100.0%, AvgPnL=1.00%, Trades=6)

Final set: ['AIXBT', 'BABY', 'DOGE', 'DOT', 'FOGO', 'INJ', 'KAS', 'LTC', 'ME', 'MNT', 'NXPC', 'POL', 'SEI', 'TURBO', 'USUAL', 'YGG']

## LOSERS Update — 2026-09-05 06:02 UTC
- REMOVE LDO (insufficient data)
- REMOVE ICP (insufficient data)
- REMOVE NOT (WR=50.0%, PnL=$-0.07, recovered)
- REMOVE ZEN (insufficient data)
- REMOVE XPL (insufficient data)
- REMOVE MET (WR=57.1%, PnL=$-0.20, recovered)
- REMOVE SAND (insufficient data)
- ADD BCH (WR=33.3%, PnL=$-0.43, low_wr (33.3%))
- ADD NEAR (WR=40.0%, PnL=$-0.08, wr_collapse (63.6% → 40.0%))
- ADD CRV (WR=46.2%, PnL=$0.16, low_wr (46.2%))

Final set: ['APT', 'ARB', 'BCH', 'CASHCAT', 'CHIP', 'CRV', 'ENA', 'FIL', 'JUP', 'NEAR', 'W']

## 2026-09-05 07:07 UTC — Hourly Analysis

**Trades:** 0 closed last hour (quiet overnight)
**24h:** 31T 54.8%WR ~$0.06 breakeven

**24h Top Signals:**
- open-skies+: 3T 100%WR +$0.55 ⭐
- continuation+: 4T 100%WR +$0.30 ⭐
- bb-bounce-v2-long+: 3T 100%WR +$0.09 ⭐
- ema300-dip: 12T 50%WR -$0.87 (drag)

**24h Close Reasons:**
- profit-monster-trail: 17T +$1.31 (carrying system)
- atr_sl_hit: 7T -$0.79 (21.9% — under 40% ✓)

**Changes:** None needed

**No Change Needed:**
- Kill criteria not met
- atr_sl_hit 21.9% under 40%
- Trade freq 0/hr quiet
- Stars carrying, ema300-dip drag not killable

**Open Questions:**
- ema300-dip at -$0.87/24h still biggest drag — watch for further deterioration

## Daily Orchestrator Report — 2026-09-05 06:30 UTC

**Pipeline Status:**
- Trades (24h): 31T, 64.5% WR, -$0.24
- Trades (7d): 368T, 54.9% WR, -$4.34
- Open: 4 positions
- Market: 3 LONG_BIAS / 105 NEUTRAL / 0 SHORT

**R:R Fix Effect (11 trades post-fix):**
- profit-monster-trail: 5T avg +$0.142 (2.7x old $0.053)
- cut-loser-CL-T1: 4T avg -$0.142
- profit-monster-T1: 2T avg +$0.080
- Net: +$0.30 (profitable!)
- R:R ratio: 0.69→1.26 (83% improvement)
- Need 20+ trades to confirm

**Top Signals (7d):**
- bb-bounce-v2-long+: 36T 78%WR +$0.95 ★ STAR
- open-skies+: 3T 100%WR +$0.55
- continuation+: 4T 100%WR +$0.30

**Implemented Today:**
1. Disk cleanup — freed 3G (coin_tracker 2.2G→752MB, hl_copy 1.9G→324MB)
2. Updated CURRENT.md with verified DB data

**Critical Issues:**
- Signal starvation — system on 1 profitable backbone (bb-bounce-v2-long+)
- NEUTRAL signal build pending since Sep 1 — never delivered
- ema300-dip-short borderline (5T/40%WR -$0.29)

**Next Steps:**
1. Monitor R:R fix — need 20+ trades to confirm
2. Build NEUTRAL regime signal (delegated, pending)
3. Monitor ema300-dip-short for potential kill
4. Monitor bb-bounce-v2-long+ performance

**Quality Metrics:**
- Tasks completed: 2/2 (disk cleanup, CURRENT.md update)
- First-attempt success: 100%
- System health: OK (1 compactor timeout recovered)

## [2026-09-05 08:07 UTC] Hourly Analysis

**Trades:** 0T last hour. 32T/24h, 20W 12L, 62.5% WR
**PnL:** -$0.37 (24h). Stars carrying: open-skies+ +$0.55, continuation+ +$0.30, bb-bounce-v2-long+ +$0.09.
**Open:** 3 positions ($42.10) — BLUR LONG, WLFI SHORT, ME LONG

**Close reasons (24h):** profit-monster-trail 16T +$1.27 dominant. atr_sl_hit 7T 21.9% under 40%. cut-loser-CL-T1 5T -$0.70.

**Signal health (24h):**
- Stars: continuation+ 4T 100%WR, open-skies+ 3T 100%WR, bb-bounce-v2-long+ 3T 100%WR
- Drag: ema300-dip 11T 45%WR -$0.91 (improving from -$0.98), ema300-dip-short 6T 33%WR -$0.42
- No kill criteria met (need 0%WR + 3+T last hour; 0T last hour)

**Changes:**
None — kill criteria not met, atr_sl_hit under 40%, trade freq 0/hr quiet. System steady state.

**No Change Needed:**
- Kill criteria: 0 trades last hour, no signal qualifies
- atr_sl_hit: 21.9% well under 40%
- Trade freq: 0/hr quiet overnight

**Open Questions:**
- ema300-dip at -$0.91/24h still biggest drag — watch for further deterioration
- 3 open positions small ($42.10) — low exposure
- Overnight quiet — expect activity in US session

**Next:** Re-run at 09:07 UTC

## [2026-09-05 09:07 UTC] Hourly Analysis

**Trades:** 2T last hour (2W +$0.23). 33T/24h, 21W 12L, 63.6% WR
**PnL:** -$0.17 (24h). Stars dominating: open-skies+ 4T 100%WR +$0.58, continuation+ 4T 100%WR +$0.30, bb-bounce-v2-long+ 4T 100%WR +$0.29.
**Open:** 2 positions — both winners last hour (BLUR LONG +$0.20, LTC LONG +$0.03)

**Close reasons (24h):** profit-monster-trail 17T +$1.47 dominant. atr_sl_hit 7T 21.2% under 40%. cut-loser-CL-T1 5T -$0.70.

**Signal health (24h):**
- Stars: open-skies+ 4T 100%WR +$0.58, continuation+ 4T 100%WR +$0.30, bb-bounce-v2-long+ 4T 100%WR +$0.29
- Drag: ema300-dip 11T 45.5%WR -$0.91, ema300-dip-short 6T 33.3%WR -$0.42
- No kill criteria met (need 0%WR + 3+T last hour; 2T last hour both wins)

**Changes:**
None — system healthy, WR climbing, stars dominant.

**No Change Needed:**
- Kill criteria: 2T last hour both wins, no signal qualifies
- atr_sl_hit: 21.2% well under 40%
- Trade freq: 2/hr normal
- WR trending up: 54.8% → 62.5% → 63.6%

**Open Questions:**
- ema300-dip still biggest drag (-$0.91/24h) but not killable (45.5% WR)
- System on strong backbone of 3 star signals

**Next:** Re-run at 10:07 UTC
