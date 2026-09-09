## [2026-09-09 22:07 UTC] Hourly Analysis

**Trades:** 0 closed last hour (quiet since 21:00 UTC)
**24h:** 44T 59% atr_sl_hit +$0.38 net (improving from -$3.08 on Sep 8)

**24h Exit Breakdown:**
- profit-monster-trail: 9T +$0.37 ⭐
- rr_engine_support_tp: 5T +$0.26 ⭐
- atr_sl_hit: 26T (59%) -$0.16 (avg loss tiny -$0.006)
- rr_engine_resistance: 2T -$0.25

**24h Signal Performance (2+ trades):**
- pump_chain: 6T 50%WR +$1.06 ⭐
- pullback-entry-: 8T 62.5%WR +$0.33 ⭐
- mover-: 3T 66.7%WR +$0.05 ⭐
- pump-chain-: 6T 50%WR -$0.63 ⚠️ (R:R 0.11:1 structural)
- pullback-entry+: 4T 25%WR -$0.34 ⚠️
- open-skies+: 2T 0%WR -$0.49 ⚠️

**Changes:** None — 0 trades last hour, no kill criteria met.

**No Change Needed:**
- Kill criteria: no signal at 0%WR with 3+T last hour
- Trade freq normal, quiet evening
- pump-chain- R:R 0.11:1 structural — needs TPSL review, not killable
- open-skies+ 0%WR only 2T below threshold

**Open Questions:**
- pump-chain- R:R 0.11:1 worst structural drag
- pullback-entry+ 4T 25%WR approaching kill threshold
- 5 open SHORTs all pullback-entry- — concentrated exposure

## [2026-09-09 21:00 UTC] Hourly Analysis

**Trades:** 6 closed (2W 4L -$0.05)
**24h:** 44T 24W 54.5%WR +$0.22

**24h Exit Breakdown:**
- profit-monster-trail: 9T 88.9%WR +$0.37 ⭐
- rr_engine_support_tp: 5T 80%WR +$0.26 ⭐
- atr_sl_hit: 26T (13 profitable trailing,13 actual stops = 29.5% real stop rate) ✅
- rr_engine_resistance: 2T 0%WR -$0.25

**24h Signal Performance (2+ trades):**
- pump_chain: 6T 50%WR +$1.06 ⭐
- pullback-entry-: 8T 62.5%WR +$0.33 ⭐
- mover-: 3T 66.7%WR +$0.05 ⭐
- accel-300-v3-short-: 2T 50%WR +$0.05
- pump-chain-: 6T 50%WR -$0.63 ⚠️ (avg_win=$0.03 avg_loss=-$0.24, R:R 0.11:1)
- pullback-entry+: 4T 25%WR -$0.34 ⚠️
- open-skies+: 2T 0%WR -$0.49 ⚠️ (below kill threshold)

**Structural Issue:** R:R across system is 0.77:1 (avg_win $0.12 vs avg_loss -$0.15). pump-chain- is worst at 0.11:1. Profit captured by trailing exits is small relative to stop losses.

**Changes:**
None — no kill criteria met (no signal at 0%WR with 3+ trades last hour).

**No Change Needed:**
- Kill criteria: no signal at 0%WR with 3+T last hour
- Real stop rate 29.5% well below 40% threshold ✅
- Trade freq 6/hr normal
- pump-chain+ killed at 03:10 UTC — improvement confirmed (+$0.22 vs -$3.08)
- pump-chain- 50%WR but bad R:R — structural, not a kill signal
- open-skies+ 0%WR but only 2T — below threshold

**Open Questions:**
- pump-chain- R:R 0.11:1 is a structural drag — 50%WR but losses dwarf wins. Needs T review.
- pullback-entry+ 4T 25%WR — monitoring for next kill cycle
- 3-day trend: Sep 7 +$0.01 → Sep 8 -$2.74 → Sep 9 +$0.22 (improving)
- Open positions: 4 SHORT (ONDO, COMP, ENA, ADA)

## [2026-09-09 03:10 UTC] Hourly Analysis

**Trades:** 1 closed (0W 1L -$0.15)
**24h:** 60T 41.7%WR -$3.08

**24h Exit Breakdown:**
- profit-monster-trail: 25T avg +$0.050 ⭐
- cut-loser-CL-T1: 19T avg -$0.139 (all losses by design)
- atr_sl_hit: 14T 21% avg -$0.122 (healthy)
- HL_CLOSED: 1T +$0.02

**24h Worst Signals:**
- pump-chain+: 13T 35.7%WR -$1.28 (worst) — ALL LONG in downtrend
- ema300-dip-short: 11T 36.4%WR -$0.78 (protection expired)
- sma20-dip+: 19T 42.1%WR -$0.73 (legacy, killed yesterday)
- bb-bounce-v2-long+: 8T 37.5%WR -$0.65

**Star:** open-skies+: 3T 67%WR +$1.42

**Changes:**
1. KILL pump-chain+ LONG (`PUMP_FLOW_PLUS_ENABLED = False`) — 13T 35.7%WR -$1.28, all LONG entries in a downtrend. SHORT stays active.

**No Change Needed:**
- Kill criteria: pump-chain+ was above 0%WR threshold but 35.7%WR degraded enough to kill long direction
- atr_sl_hit 21% healthy ✅
- Trade freq 1/hr normal (quiet market 03:10 UTC)
- ema300-dip-short 11T 36.4%WR — protection expired, monitoring for next kill cycle
- bb-bounce-v2-long+ 37.5%WR monitoring

**Open Questions:**
- 3-day trend: Sep 7 +$0.01 → Sep 8 -$2.74 → Sep 9 -$0.14 (just started)
- ema300-dip-short protection expired — next candidate if WR doesn't improve
- Open positions: 5 (BANANA SHORT, ZRO SHORT, GRASS LONG, CC LONG, APT SHORT)

## [2026-09-09 01:10 UTC] Hourly Analysis

**Trades:** 1 closed (1W, net +$0.01)
**24h:** 47T 46.8%WR -$1.81

**Last Hour:**
- ATOM open-skies+: +$0.01 atr_sl_hit (breakeven) ✅

**24h Exit Breakdown:**
- profit-monster-trail: 27T avg +$0.058 ⭐ (carrying system)
- cut-loser-CL-T1: 23T avg -$0.146 (losses contained)
- atr_sl_hit: 14T 18.7% avg -$0.077 (healthy range, slightly negative avg)
- HL_CLOSED: 1T +$0.02

**24h Signal Performance (3+ trades):**
- open-skies+: 3T 66.7%WR +$0.49 ⭐ (best, small sample)
- sma20-dip+: 19T 42.1%WR -$0.73 (persistent drag)
- pump-chain+: 16T 43.8%WR -$0.97 (degraded from 64.3%WR yesterday, -$0.35 in last 2h)
- ema300-dip-short: 12T 33.3%WR -$0.99 (trades from before 16:10 kill)
- bb-bounce-v2-long+: 8T 37.5%WR -$0.65 (underperforming)

**Changes:**
- None needed

**No Change Needed:**
- Kill criteria: No signal at 0%WR with 3+T last hour. Only 1 trade last hour.
- atr_sl_hit 18.7% healthy ✅
- Trade freq 1/hr normal ✅
- 4 open positions (GRASS/CC/IMX LONG pump-chain+, APT SHORT pump-chain-)
- ema300-dip-short confirmed killed — 0 trades post-16:10 ✅

**Open Questions:**
- pump-chain+ WR dropping from 64.3% to 43.8% over 24h. Monitor next hour — if continues negative, may need param tuning.
- sma20-dip+ persistent drag (19T -$0.73) but 42.1%WR not at kill threshold.

## [2026-09-08 17:10 UTC] Hourly Analysis

**Trades:** 2 closed (1W 1L, net -$0.10)
**24h:** 73T 52.1%WR -$0.93

**Last Hour:**
- BLUR pump-chain+: +$0.04 profit-monster-trail ✅
- SUSHI r2-trend-short5: -$0.14 cut-loser-CL-T1 ❌

**24h Exit Breakdown:**
- profit-monster-trail: 35T avg +$0.061 ⭐ (carrying system)
- cut-loser-CL-T1: 24T avg -$0.143 (losses contained)
- atr_sl_hit: 12T 16.4% avg +$0.028 ✅ (healthy)

**24h Signal Performance (3+ trades):**
- pump-chain+: 14T 64.3%WR -$0.019 (best WR)
- sma20-dip+: 19T 42.1%WR -$0.038 (underperforming)
- ema300-dip-short: 17T 47.1%WR -$0.054 (already killed 16:10)
- bb-bounce-v2-long+: 9T 44.4%WR -$0.063 (underperforming)

**Changes:**
- None needed

**No Change Needed:**
- Kill criteria: No signal at0%WR with 3+T last hour. r2-trend-short5 1T 0%WR but only 1 trade (not 3+).
- atr_sl_hit 16.4% healthy ✅
- Trade freq 2/hr normal ✅
- 3 open positions (SOL, BIGTIME, DOGE)
- ema300-dip-short already killed last hour ✅

**Open Questions:**
- r2-trend-short5 has no signal file — ghost signal, trade logged under non-existent module. Not causing harm but worth cleaning up.

## [2026-09-08 16:10 UTC] Hourly Analysis

**Trades:** 7 closed (2W 5L, net -$0.39 excl test)
**24h:** 75T 54.7%WR -$0.45

**Last Hour:**
- WLFI ema300-dip-short: -$0.11 cut-loser-CL-T1 ❌
- CC pump-chain+: +$0.03 profit-monster-trail ✅
- HBAR ema300-dip-short: -$0.17 atr_sl_hit ❌
- DYDX pump-chain+: +$0.02 HL_CLOSED ✅
- GMT ema300-dip-short: -$0.17 atr_sl_hit ❌
- DOGE ema300-dip-short: -$0.16 cut-loser-CL-T1 ❌
- BANANA ema300-dip-short: $0.00 test_cleanup

**24h Exit Breakdown:**
- profit-monster-trail: 38T (51%) avg +$0.066 ⭐
- cut-loser-CL-T1: 23T (31%) avg -$0.143
- atr_sl_hit: 12T (16%) avg +$0.028

**24h Signal Performance:**
- open-skies+: 2T +$1.42 (best, small sample)
- r2-trend-short3: 2T +$0.10
- pump-chain+: 16T -$0.01 (breakeven)
- sma20-dip+: 19T -$0.73 (biggest drag by count)
- ema300-dip-short: 17T -$0.91 (biggest drag by total)
- bb-bounce-v2-long+: 9T -$0.57

**Changes:**
1. KILLED ema300-dip-short — 0%WR last hour (0W4L), 17T/24h -$0.91 net negative. Redesign re-enabled today failed to improve. Kill criteria met (0%WR with 3+T).

**No Change Needed:**
- Kill criteria: ema300-dip-short killed. sma20-dip+ (19T -$0.73) underperforming but 52.6%WR, not at 0%WR threshold.
- atr_sl_hit 16% healthy ✅
- Trade freq 2.3/hr normal ✅
- 0 open positions
- R:R system-wide is 0.74:1 (avg_win +$0.097 vs avg_loss -$0.131) — losses bigger than winners, structural issue from cut-loser timing

**Open Questions:**
- sma20-dip+ is biggest drag by trade count (19T -$0.73). 52.6%WR but losers > winners. Monitor — if next 24h stays negative, consider kill.

## [2026-09-08 02:10 UTC] Hourly Analysis

**Trades:** 5 closed (4W 1L +$0.61, WR 80%)
**24h:** 55T 67%WR +$0.84 (improving)

**Last Hour:**
- KAS pump-chain+: +$0.13 profit-monster-trail ✅
- WLD open-skies+: +$0.48 atr_sl_hit (trailing lock) ✅
- AIXBT pump-chain+: +$0.18 profit-monster-trail ✅
- NXPC ema300-dip-short: -$0.21 cut-loser-CL-T1 ❌
- CAKE pump-chain+: +$0.03 profit-monster-trail ✅

**No Change Needed:**
- Kill criteria: no signal at ≤25%WR with 3+T last hour
- atr_sl_hit 20% healthy ✅
- Trade freq 5/hr normal
- 2 open positions fresh
- ema300-dip-short 6T -$0.13 weakest signal but WR 66.7%, above kill threshold

**Open Questions:**
- None — system performing well

## [2026-09-08 03:10 UTC] Hourly Analysis

**Trades:** 0 closed in last hour. 3 open positions (ICP, IMX, GMT — all fresh)
**24h:** 55T 67.3%WR +$1.51 (improving from +$0.84)

**Last 2h (recent activity):**
- FOGO pump-chain+: -$0.22 cut-loser-CL-T1 ❌
- SUSHI bb-bounce-v2-long+: -$0.12 cut-loser-CL-T1 ❌
- ETC pump-chain+: -$0.15 cut-loser-CL-T1 ❌
- (3 consecutive cut-loser exits, all contained < $0.25)

**24h Exit Breakdown:**
- profit-monster-trail: 31T avg +$0.080 ⭐
- cut-loser-CL-T1: 13T avg -$0.147 (losses contained)
- atr_sl_hit: 10T avg +$0.085 ✅ (SL hits profitable)

**No Change Needed:**
- Kill criteria: No signal at 0%WR with 3+T in last hour
- atr_sl_hit 18% (10/55) — healthy, well under 40%
- ema300-dip-short: 6T -$0.13 weakest but 67%WR above kill threshold
- Trade freq normal
- 3 open positions fresh

**Open Questions:**
- None — system healthy

## [2026-09-08 04:10 UTC] Hourly Analysis

**Trades:** 0 closed in last hour. 4 open positions (USUAL, SAND, IMX, GMT — all fresh)
**24h:** 56T 69.6%WR +$1.69 | 12h: 30T 70%WR +$1.44 | 4h: 11T 63.6%WR +$0.20

**24h Exit Breakdown:**
- profit-monster-trail: 32T avg +$0.079 ⭐
- cut-loser-CL-T1: 12T avg -$0.148 (losses contained)
- atr_sl_hit: 11T avg +$0.078 ✅ (SL hits profitable)
- profit-monster-T1: 1T +$0.08

**No Change Needed:**
- Kill criteria: no signal at ≤25%WR with 3+T last hour
- atr_sl_hit 20% healthy (11/56)
- Trade freq 2.3/hr normal
- 4 open positions fresh
- All signals neutral or positive in 4h window

**Open Questions:**
- None — system healthy and steady

## [2026-09-08 05:10 UTC] Hourly Analysis

**Trades:** 4 closed (2W 2L, +$0.13)
**24h:** 59T 69.5%WR +$1.83
**Exit breakdown:** profit-monster-trail: 36T avg +$0.074 ⭐ | cut-loser-CL-T1: 12T avg -$0.148 | atr_sl_hit: 10T avg +$0.087

**No Change Needed:**
- Kill criteria: no signal at 0%WR with 3+T last hour
- atr_sl_hit 17% healthy
- Trade freq 4/hr normal
- 3 open positions fresh
- All signals neutral/positive in 24h

**Open Questions:**
- None — system healthy

## FAVORITES Update — 2026-09-08 06:00 UTC
- Regime: NEUTRAL
- DEMOTE MNT (WR=50.0%, PnL=$0.24, 1 consecutive bad days, regime=NEUTRAL)
- DEMOTE ATOM (WR=57.1%, PnL=$-0.25, 1 consecutive bad days, regime=NEUTRAL)
- DEMOTE NXPC (WR=62.5%, PnL=$-0.31, 1 consecutive bad days, regime=NEUTRAL)
- PROMOTE ENA (WR=62.5%, AvgPnL=1.66%, Trades=8)
- PROMOTE ACE (WR=60.0%, AvgPnL=0.79%, Trades=5)
- PROMOTE DYDX (WR=80.0%, AvgPnL=0.91%, Trades=5)

Final set: ['ACE', 'AIXBT', 'BLUR', 'CFX', 'DOGE', 'DOT', 'DYDX', 'ENA', 'FOGO', 'GRASS', 'INJ', 'KAS', 'LTC', 'ME', 'POL', 'TURBO', 'ZRO']

## LOSERS Update — 2026-09-08 06:05 UTC
- REMOVE W (insufficient data)
- REMOVE ETC (WR=50.0%, PnL=$0.13, recovered)
- REMOVE ZEN (insufficient data)
- REMOVE JUP (insufficient data)
- REMOVE ARB (insufficient data)
- REMOVE CRV (insufficient data)
- REMOVE NOT (insufficient data)
- ADD SAND (WR=40.0%, PnL=$-0.36, low_wr (40.0%))
- ADD SYRUP (WR=42.9%, PnL=$-0.22, low_wr (42.9%))

Final set: ['BCH', 'BIGTIME', 'CASHCAT', 'FIL', 'LDO', 'SAND', 'STX', 'SYRUP']

## [2026-09-08 07:10 UTC] Hourly Analysis

**Trades:** 3 closed (3W 0L, +$0.23)
**24h:** 58T 69%WR +$1.86
**Exit breakdown:** profit-monster-trail: 35T avg +$0.077 ⭐ | cut-loser-CL-T1: 12T avg -$0.148 | atr_sl_hit: 10T avg +$0.087

**No Change Needed:**
- Kill criteria: no signal at 0%WR with 3+T last hour
- atr_sl_hit 17% healthy
- Trade freq 3/hr normal
- 3 open positions fresh
- All signals neutral/positive in 24h

**Open Questions:**
- None — system healthy and steady

## [2026-09-08 08:10 UTC] Hourly Analysis

**Trades:** 5 closed (0W 5L, -$0.47)
**24h:** 60T 68.3%WR +$1.42
**Exit breakdown:** profit-monster-trail: 34T avg +$0.078 ⭐ | cut-loser-CL-T1: 15T avg -$0.139 | atr_sl_hit: 10T avg +$0.076

**No Change Needed:**
- Kill criteria: no signal at 0%WR with 3+T last hour
- sma20-dip+ 0/3 last hour but 50%WR/24h — one bad cluster, not killable
- atr_sl_hit 16.7% healthy
- Trade freq 5/hr normal
- 5 open positions fresh
- pump-chain+ star (19T 73.7%WR +$0.26), open-skies+ strong (3T 66.7%WR +$1.23)

**Open Questions:**
- None — system steady state, negative hour absorbed by 24h positive

## [2026-09-08 09:10 UTC] Hourly Analysis

**Trades:** 3 closed (1W 2L, -$0.05)
**24h:** 63T 63.5%WR +$1.37
**Exit breakdown:** profit-monster-trail: 36T avg +$0.076 ⭐ | cut-loser-CL-T1: 16T avg -$0.138 | atr_sl_hit: 10T avg +$0.076

**No Change Needed:**
- Kill criteria: no signal at 0%WR with 3+T last hour
- atr_sl_hit 15.9% healthy
- Trade freq 3/hr normal
- 3 open positions fresh
- 24h PnL +$1.37, system steady state

**Open Questions:**
- None — system healthy

## [2026-09-08 10:10 UTC] Hourly Analysis

**Trades:** 3 closed (2W 1L, +$0.07)
**24h:** 63T 65.1%WR +$1.24
**Exit breakdown:** profit-monster-trail: 36T avg +$0.077 ⭐ | cut-loser-CL-T1: 17T avg -$0.144 | atr_sl_hit: 9T avg +$0.082

**No Change Needed:**
- Kill criteria: no signal at 0%WR with 3+T last hour
- atr_sl_hit 14.3% healthy (threshold 40%)
- Trade freq 3/hr normal
- 3 open positions fresh
- All signals neutral/positive in 24h
- sma20-dip+ weakest (13T -0.01 PnL) but 53.8%WR — not killable

**Open Questions:**
- None — system healthy and steady


## [2026-09-08 11:10 UTC] Hourly Analysis

**Trades:** 5 closed (3W 2L, -$0.19)
**24h:** 66T 64.5%WR +$1.05
**Exit breakdown:** profit-monster-trail: 38T avg +$0.074 ⭐ | cut-loser-CL-T1: 18T avg -$0.142 | atr_sl_hit: 9T avg +$0.078

**No Change Needed:**
- Kill criteria: no signal at 0%WR with 3+T last hour
- atr_sl_hit 13.6% healthy (threshold 40%)
- Trade freq 5/hr normal
- 5 open positions fresh
- pump-chain+ star (17T 76.5%WR), open-skies+ strong (3T 66.7%WR +$1.23)
- ema300-dip-short weakest (-$0.45/24h) but 55.6%WR — not killable

**Open Questions:**
- None — system healthy and steady

## [2026-09-08 12:10 UTC] Hourly Analysis

**Trades:** 3 closed (0W 3L, -$0.42)
**24h:** 68T 63.2%WR +$0.63
**Exit breakdown:** profit-monster-trail: 38T avg +$0.074 ⭐ | cut-loser-CL-T1: 20T avg -$0.140 | atr_sl_hit: 9T avg +$0.078

**Changes:**
1. KILLED sma20-dip+ — 0%WR 3T last hour, 47.1%WR all-time, -$0.42 net loser

**No Change Needed:**
- atr_sl_hit 13.2% healthy (threshold 40%)
- Trade freq 3/hr normal
- 3 open positions fresh
- pump-chain+ star (16T 81.2%WR), open-skies+ strong (3T 66.7%WR +$1.23)

**Open Questions:**
- None

## [2026-09-08 13:10 UTC] Hourly Analysis

**Trades:** 3 closed (0W 3L, -$0.24)
**24h:** 70T 62.9%WR +$0.52
**Exit breakdown:** profit-monster-trail: 38T avg +$0.075 ⭐ | cut-loser-CL-T1: 22T avg -$0.141 | atr_sl_hit: 9T avg +$0.078

**No Change Needed:**
- Kill criteria: sma20-dip+ already killed at 12:10 — 2 legacy losses (NOT, LTC) expected
- atr_sl_hit 12.9% healthy (threshold 40%)
- Trade freq 3/hr normal
- 1 open position fresh
- ema300-dip-short won (HYPE +$0.07)
- All other signals neutral/positive in 24h

**Open Questions:**
- None — system healthy, legacy losses expected from pre-kill positions

## [2026-09-08 14:10 UTC] Hourly Analysis

**Trades:** 5 closed (2W 3L, -$0.41)
**24h:** 73T 61.6%WR +$1.65
**Exit breakdown:** profit-monster-trail: 38T avg +$0.065 ⭐ | cut-loser-CL-T1: 24T avg -$0.142 | atr_sl_hit: 11T avg +$0.044

**No Change Needed:**
- Kill criteria: no signal at 0%WR with 3+T last hour
- atr_sl_hit 15.1% healthy (threshold 40%)
- Trade freq 5/hr normal
- 4 open positions fresh
- sma20-dip+ killed at 12:10, 0 trades since kill ✓
- pump-chain+ 68.8%WR positive, ema300-dip-short 66.7%WR (good WR, losing on exits)
- bb-bounce-v2-long+ weakest (41.7%WR -$0.75) but only 1T last hour — no kill trigger

**Open Questions:**
- None — system healthy

## [2026-09-08 15:10 UTC] Hourly Analysis

**Trades:** 2 closed (2W 0L, +$0.17)
**24h:** 75T 61.3%WR +$1.82
**Exit breakdown:** profit-monster-trail: 40T avg +$0.066 ⭐ | cut-loser-CL-T1: 24T avg -$0.142 | atr_sl_hit: 11T avg +$0.044

**No Change Needed:**
- Kill criteria: no signal at 0%WR with 3+T last hour
- atr_sl_hit 14.7% healthy (threshold 40%)
- Trade freq 2/hr normal
- 2 trades last hour both winners (CHIP, LTC via profit-monster-trail)
- pump-chain+ strong (16T), open-skies+ star ($1.23 avg)
- System steady state

**Open Questions:**
- None

## [2026-09-08 17:25 UTC] Hourly Analysis

**Trades:** 1 closed (0W 1L, -$0.12)
**24h:** 73T 64.4%WR +$2.04
**Exit breakdown:** profit-monster-trail: 34T avg +$0.060 ⭐ | cut-loser-CL-T1: 25T avg -$0.142 | atr_sl_hit: 12T avg +$0.028

**No Change Needed:**
- Kill criteria: no signal at 0%WR with 3+T last hour
- atr_sl_hit 16.4% healthy (threshold 40%)
- Trade freq 1/hr normal
- 1 open position fresh
- pump-chain+ negative (-$0.38) but 60%WR — cut-loser exits larger than winners, not signal quality issue
- ema300-dip-short -$0.91 worst performer but 47.1%WR — within range
- bb-bounce-v2-long+ -$0.57, 44.4%WR — borderline but no kill trigger
- System steady state

**Open Questions:**
- None

## [2026-09-08 20:07 UTC] Hourly Analysis

**Trades:** 0 closed (0W 0L, $0.00)
**24h:** 74T 35W 47.3%WR -$1.64
**Today:** 65T 45%WR -$2.48 (worst day in 3d)

**Last 2h (quiet market):**
- SOL rs-s81,volume-breakout-long+: -$0.11 cut-loser-CL-T1 ❌
- ATOM open-skies+: $0.00 atr_sl_hit (breakeven)
- DOGE pump-chain+: -$0.17 atr_sl_hit ❌
- AIXBT bb-bounce-v2-long+: -$0.20 cut-loser-CL-T1 ❌
- GRASS pump-chain+: -$0.14 atr_sl_hit ❌

**24h Exit Breakdown:**
- profit-monster-trail: 32T avg +$0.058 ⭐ (carrying system)
- cut-loser-CL-T1: 26T avg -$0.144 (loss cutting working)
- atr_sl_hit: 14T 18.9% avg +$0.016 (healthy, under 40%)

**24h Signal Performance (3+ trades):**
- open-skies+: 3T 67%WR +$1.42 ⭐ (star)
- pump-chain+: 17T 53%WR -$0.69 (degraded from 83%WR yesterday)
- sma20-dip+: 19T 42%WR -$0.73 (persistent drag)
- ema300-dip-short: 15T 47%WR -$0.76 (killed 16:10, trades from before kill)
- bb-bounce-v2-long+: 9T 33%WR -$0.89 (worst performer)

**Changes:**
- None needed

**No Change Needed:**
- Kill criteria: No signal at 0%WR with 3+T last hour. 0 trades last hour (market quiet).
- atr_sl_hit 18.9% healthy ✅
- Trade freq 0/hr (quiet market, not overtrading)
- 0 open positions
- ema300-dip-short already killed 16:10 ✅
- bb-bounce-v2-long+ 33%WR doesn't meet kill threshold (0%WR), but monitoring

**Open Questions:**
- Today's degradation: bb-bounce-v2-long+ went from 67%WR yesterday to 33%WR today. Market regime shift?
- pump-chain+ degraded from 83%WR to 53%WR. Same pattern.
- 3-day trend: Sep 6 +$0.40, Sep 7 +$0.01, Sep 8 -$2.48. System deteriorating.

## [2026-09-08 21:10 UTC] Hourly Analysis

**Trades:** 1 closed (0W 1L, -$0.03)
**24h:** 73T 48.6%WR -$0.55
**Today:** 66T 43.9%WR -$2.51

**Last hour:**
- ETC pump-chain+ LONG: -$0.03 profit-monster-trail (breakeven exit)

**24h Exit Breakdown:**
- profit-monster-trail: 32T avg +$0.053 ⭐ (carrying system)
- cut-loser-CL-T1: 26T avg -$0.144 (loss cutting)
- atr_sl_hit: 13T 17.6% avg -$0.055 (healthy, under 40%)

**24h Signal Performance (3+ trades):**
- sma20-dip+: 19T 42%WR -$0.73 (killed, legacy trades settling)
- pump-chain+: 18T 50%WR -$0.72 (degraded from 83%WR yesterday)
- ema300-dip-short: 14T 43%WR -$0.90 (killed, legacy trades settling)
- bb-bounce-v2-long+: 9T 33%WR -$0.89 (worst active, monitoring)
- open-skies+: 2T 50%WR +$0.48

**Changes:**
- None needed

**No Change Needed:**
- Kill criteria: No signal at 0%WR with 3+T last hour. Only 1T last hour.
- atr_sl_hit 17.6% healthy ✅
- Trade freq 1/hr normal
- bb-bounce-v2-long+ 33%WR persistent drag but not at kill threshold
- pump-chain+ degraded to 50%WR — 24h aggregate, not last-hour trigger

**Open Questions:**
- 3-day trend: Sep 6 +$0.40, Sep 7 +$0.01, Sep 8 -$2.51. System deteriorating. Market regime shift?
- sma20-dip+ and ema300-dip-short legacy trades still settling (killed earlier today)

## [2026-09-08 22:10 UTC] Hourly Analysis

**Trades:** 0 closed last hour
**24h:** 70T 45.7%WR -$2.51
**Today:** 66T 43.9%WR -$2.51

**24h Exit Breakdown:**
- profit-monster-trail: 31T avg +$0.054 ⭐
- cut-loser-CL-T1: 24T avg -$0.145
- atr_sl_hit: 13T 18.6% avg -$0.055 (healthy)
- HL_CLOSED: 1T +$0.02

**24h Signal Performance (3+ trades):**
- sma20-dip+: 19T 37%WR -$0.73 (killed, legacy settling)
- pump-chain+: 17T 41%WR -$0.75 (degraded)
- ema300-dip-short: 14T 36%WR -$0.90 (killed, legacy settling)
- bb-bounce-v2-long+: 8T 38%WR -$0.72 (worst active)
- open-skies+: 2T 100%WR +$0.48

**Open Positions:** 4 (APT SHORT, AIXBT LONG, IMX LONG, NEO LONG)

**Changes:**
- None needed

**No Change Needed:**
- Kill criteria: No signal at 0%WR with 3+T last hour (0 trades last hour)
- atr_sl_hit 18.6% healthy ✅
- Trade freq 0/hr (quiet market)
- No 3+ trade signals at 0%WR in 24h

**Open Questions:**
- 3-day trend: Sep 6 +$0.40, Sep 7 +$0.01, Sep 8 -$2.51. Market regime shift?
- bb-bounce-v2-long+ 38%WR persistent drag (killed earlier but legacy settling)
- pump-chain+ degraded to 41%WR

## [2026-09-08 23:10 UTC] Hourly Analysis

**Trades:** 1 closed (0W 1L -$0.32)
**24h:** 69T 44.9%WR -$2.76

**24h Exit Breakdown:**
- profit-monster-trail: 30T avg +$0.054 ⭐
- cut-loser-CL-T1: 23T avg -$0.146
- atr_sl_hit: 14T 20.3% avg -$0.074 (healthy)
- HL_CLOSED: 1T +$0.02

**Open Positions:** 5 (CC LONG, ATOM LONG, APT SHORT, IMX LONG, NEO LONG)

**Changes:**
- None needed

**No Change Needed:**
- Kill criteria: No signal at 0%WR with 3+T last hour (1T total)
- atr_sl_hit 20.3% healthy ✅
- Trade freq 1/hr normal
- pump-chain+ 47%WR degraded but not at kill threshold
- bb-bounce-v2-long+ 37.5%WR worst active, monitoring

**Open Questions:**
- 3-day trend: Sep 6 +$0.40 → Sep 7 +$0.01 → Sep 8 -$2.76. Deteriorating fast.
- pump-chain+ entries weak in current regime — 5W/12L in 24h
- bb-bounce-v2-long+ 37.5%WR approaching concern threshold

## [2026-09-09 01:10 UTC] Hourly Analysis

**Trades:** 1 closed (1W 0L +$0.09)
**24h:** 67T 44.8%WR -$2.74

**24h Exit Breakdown:**
- profit-monster-trail: 29T avg +$0.056 ⭐
- cut-loser-CL-T1: 23T avg -$0.146
- atr_sl_hit: 13T 19.4% avg -$0.084 (healthy)
- HL_CLOSED: 1T +$0.02

**Open Positions:** 4

**Changes:**
- None needed

**No Change Needed:**
- Kill criteria: No signal at 0%WR with 3+T last hour (1T total)
- atr_sl_hit 19.4% healthy ✅
- Trade freq 1/hr normal
- pump-chain+ 47%WR degraded but above kill threshold
- bb-bounce-v2-long+ 37.5%WR worst active, monitoring
- sma20-dip+ and ema300-dip-short legacy settling

**Open Questions:**
- 3-day trend: Sep 7 +$0.01 → Sep 8 -$2.74 → Sep 9 (just started)
- pump-chain+ degraded but not at kill threshold (0%WR required)
- Market regime shift? Low trade volume suggests quiet market

## [2026-09-09 02:10 UTC] Hourly Analysis

**Trades:** 0 closed (0W 0L +$0.00)
**24h:** 62T 40.3%WR -$3.42

**24h Exit Breakdown:**
- profit-monster-trail: 25T avg +$0.050 ⭐
- cut-loser-CL-T1: 22T avg -$0.143
- atr_sl_hit: 13T 21% avg -$0.120 (healthy)
- HL_CLOSED: 1T +$0.02

**24h Worst Signals:**
- pump-chain+: 14T 35.7%WR -$1.28 (worst)
- ema300-dip-short: 11T 36.4%WR -$0.78 (legacy, protected until 05:00 UTC)
- sma20-dip+: 19T 42.1%WR -$0.73 (legacy)
- bb-bounce-v2-long+: 8T 37.5%WR -$0.65

**Open Positions:** 5 (GRASS LONG, CC LONG, APT SHORT, IMX LONG, ZRO SHORT)

**Changes:**
- None needed

**No Change Needed:**
- Kill criteria: No signal at 0%WR with 3+T last hour (0T last hour)
- atr_sl_hit 21% healthy ✅
- Trade freq 0/hr (market quiet 02:10 UTC)
- pump-chain+ 35.7%WR degraded but above kill threshold (0%WR required)
- ema300-dip-short protected until 05:00 UTC — will re-evaluate then
- bb-bounce-v2-long+ 37.5%WR monitoring

**Open Questions:**
- 3-day trend: Sep 6 +$0.40 → Sep 7 +$0.01 → Sep 8 -$2.74. Deteriorating.
- ema300-dip-short protection expires 05:00 UTC — 11T 36.4%WR -$0.78, consider killing
- pump-chain+ all LONG in downtrend — directional mismatch
- Market quiet, 0 trades last hour

## [2026-09-09 03:10 UTC] Hourly Analysis

**Trades:** 4 closed (4W 0L +$0.14)
**24h:** 62T 44%WR -$2.62

**24h Exit Breakdown:**
- profit-monster-trail: 26T avg +$0.048 ⭐
- cut-loser-CL-T1: 19T avg -$0.139
- atr_sl_hit: 15T 24% avg -$0.108
- HL_CLOSED: 1T +$0.02
- test_cleanup: 1T $0.00

**Last Hour Trades:**
- APT SHORT pump_chain: +$0.01 (atr_sl_hit)
- BANANA SHORT mover: +$0.03 (profit-monster-trail) ⭐
- ZRO SHORT mover: +$0.01 (profit-monster-trail) ⭐
- CC LONG pump_chain: +$0.09 (atr_sl_hit)

**Changes:**
- None needed

**No Change Needed:**
- Kill criteria: No signal at 0%WR with 3+T last hour
- atr_sl_hit 24% healthy ✅
- Trade freq 4/hr normal
- pump_chain 4T last hour all winners — strong
- mover 2T both trails — strong
- cut-loser-CL-T1 19T -$2.65 worst exit reason — structural issue, not signal-specific

**Open Questions:**
- cut-loser-CL-T1 contributes -$2.65 of -$2.62 total 24h loss (over 100%). Other exits compensate.
- 3-day trend: Sep 7 +$0.01 → Sep 8 -$2.74 → Sep 9 +$0.14 (improving)

## [2026-09-09 04:10 UTC] Hourly Analysis

**Trades:** 1 closed (0W 1L -$0.14)
**24h:** 59T 44%WR -$2.74

**24h Exit Breakdown:**
- profit-monster-trail: 22T avg +$0.051 ⭐
- cut-loser-CL-T1: 19T avg -$0.139 (97% of total loss)
- atr_sl_hit: 16T 27% avg -$0.110
- HL_CLOSED: 1T +$0.02
- test_cleanup: 1T $0.00

**Last Hour Trades:**
- ICP SHORT pump_chain: -$0.14 (atr_sl_hit) — expected, pump_chain LONG-biased

**Changes:**
- None needed

**No Change Needed:**
- Kill criteria: No signal at 0%WR with 3+T last hour (1T only)
- atr_sl_hit 27% healthy ✅
- Trade freq 1/hr normal (market quiet ~04:10 UTC)
- pump-chain+ 47%WR above kill threshold
- cut-loser-CL-T1 structural issue but not signal-specific

**Open Questions:**
- cut-loser-CL-T1 contributes -$2.65 of -$2.74 total 24h loss — consider adjusting CL threshold
- 3-day trend: Sep 7 +$0.01 → Sep 8 -$2.74 → Sep 9 -$0.14 (early day)

## FAVORITES Update — 2026-09-09 06:00 UTC
- Regime: NEUTRAL
- DEMOTE GRASS (WR=57.1%, PnL=$-0.11, 1 consecutive bad days, regime=NEUTRAL)
- PROMOTE COMP (WR=60.0%, AvgPnL=0.30%, Trades=5)
- PROMOTE IMX (WR=60.0%, AvgPnL=0.43%, Trades=5)

Final set: ['ACE', 'AIXBT', 'BLUR', 'CFX', 'COMP', 'DOGE', 'DOT', 'DYDX', 'ENA', 'FOGO', 'IMX', 'INJ', 'KAS', 'LTC', 'ME', 'POL', 'TURBO', 'ZRO']

## LOSERS Update — 2026-09-09 06:05 UTC
- REMOVE CASHCAT (insufficient data)
- REMOVE SYRUP (WR=50.0%, PnL=$-0.12, recovered)
- REMOVE FIL (insufficient data)
- REMOVE LDO (insufficient data)
- ADD BABY (WR=40.0%, PnL=$-0.50, wr_collapse (63.2% → 40.0%))
- ADD APT (WR=42.9%, PnL=$-0.47, low_wr (42.9%))
- ADD HBAR (WR=40.0%, PnL=$-0.47, low_wr (40.0%))
- ADD IO (WR=40.0%, PnL=$-0.40, low_wr (40.0%))
- ADD ETC (WR=44.4%, PnL=$0.10, low_wr (44.4%))

Final set: ['APT', 'BABY', 'BCH', 'BIGTIME', 'ETC', 'HBAR', 'IO', 'SAND', 'STX']

## [2026-09-09 15:10 UTC] Hourly Analysis

**Trades:** 4 closed (0W 4L -$0.36)
**24h:** 40T 40%WR -$0.98

**Last Hour Breakdown:**
- pullback-entry+: 3T 0%WR (NEO -$0.15 atr_sl, AIXBT -$0.21 atr_sl, ETH -$0.02 rr_engine)
- pullback-entry-: 1T 1W (LTC +$0.02 rr_engine_support_tp)

**24h Exit Reasons:**
- atr_sl_hit: 22/40 = **55%** — above 40% threshold → SL too tight
- profit-monster-trail: 7T +$0.20 (good)
- cut-loser-CL-T1: 6T -$0.84 (structural)
- rr_engine: 2T mixed

**24h Signal PnL (worst first):**
- ema300_dip_short: 5T 0%WR -$0.61 — protection expired, chronic loser
- pullback-entry+: 4T 25%WR -$0.34
- open-skies+: 1T 0%WR -$0.26
- pump_chain: 13T 46%WR +$0.69 (best)

**Changes:**
1. **KILLED pullback-entry+** — 0%WR with 3+T last hour (auto kill rule)
   - Disabled PULLBACK_ENTRY_PLUS_ENABLED
   - pullback-entry- remains enabled (1W last hour)

**No Change Needed:**
- ema300_dip_short: protection expired but 0T last hour → doesn't meet kill criteria
- atr_sl_hit 55%: systemic issue, SL params are CEO-locked

**Open Questions:**
- atr_sl_hit at 55% is the dominant close reason — SL may need widening (CEO decision)
- pump_chain+ at 47%WR degraded but still positive PnL — monitor

## [2026-09-09 16:10 UTC] Hourly Analysis

**Trades:** 4 closed (3W 1L +$0.16)
**24h:** 37T 43%WR -$0.18

**Last Hour Breakdown:**
- pump-chain-: 2T 1W 1L -$0.40 (KAS -$0.42, CAKE +$0.02)
- accel-300-v3-short-: 1W +$0.09 (INJ)
- pullback-entry+,rs-s45: 1W +$0.15 (SYRUP) — pre-kill trade, signal disabled since 15:10

**24h Exit Reasons:**
- atr_sl_hit: 24/37 = 65% — above 40% threshold BUT net PnL -$0.18 (nearly flat)
- profit-monster-trail: 6T +$0.17 (good)
- cut-loser-CL-T1: 4T -$0.57 (structural, not signal-specific)
- rr_engine: 2T mixed

**24h Signal PnL (worst first):**
- pump-chain-: 4T 50%WR -$0.48
- pullback-entry+: 4T 25%WR -$0.34 (killed 15:10)
- open-skies+: 1T 0%WR -$0.26
- pump_chain: 11T 36%WR +$0.64 (best earner)

**Changes:** None

**No Change Needed:**
- Kill criteria: no 0%WR signal with 3+T last hour
- atr_sl_hit 65%: trades are flat, not a tuning crisis
- Trade freq 4/hr: healthy
- 3d trend: recovering (Sep 8 -$2.74 → Sep 9 +$0.52)

**Open Questions:**
- pump-chain- at 4T -$0.48 is negative but 50%WR — monitor for next hour
- cut-loser-CL-T1 structural drag (-$0.57/24h) — not addressable via signal tuning

## [2026-09-09 17:07 UTC] Hourly Analysis

**Trades:** 6 closed (3W 3L, -$0.36)
**24h:** 41T 41%WR -$0.22

**Last Hour Breakdown:**
- pump-chain-: 2T 1W 1L -$0.13
- accel-300-v3-short-: 1T 0W 1L -$0.04
- mover+: 1T 1W +$0.12
- pullback-entry-: 1T 1W +$0.03
- r2v2-long3: 1T 0W 1L -$0.14

**24h Exit Reasons:**
- atr_sl_hit: 27/41 = 65.9% — above 40% threshold but avg -$0.017 (flat)
- profit-monster-trail: 6T +$0.25
- cut-loser-CL-T1: 3T -$0.43

**Changes:** None

**No Change Needed:**
- Kill criteria: no 0%WR signal with 3+T last hour
- pump-chain- worst 24h (-$2.20) but has wins — monitor
- atr_sl_hit 65.9% systemic — trades flat, not crisis-level
- Trade freq 6/hr healthy
- 0 open positions

**Open Questions:**
- pump-chain- at -$2.20/24h — if negative next hour, consider kill
- atr_sl_hit 65%+ sustained — structural SL issue, CEO decision if widening needed

## [2026-09-09 18:10 UTC] Hourly Analysis

**Trades:** 2 closed (1W 1L, -$0.18)
**24h:** 42T 41%WR -$0.22

**Last Hour Breakdown:**
- mover-: 1T 1W +$0.05 (JUP SHORT, trail)
- open-skies+: 1T 0W 1L -$0.23 (BLUR LONG, rr_engine_resistance)

**24h Exit Reasons:**
- atr_sl_hit: 27T 64.3% avg -$0.017 (flat, systemic)
- profit-monster-trail: 7T avg +$0.043 (healthy)
- cut-loser-CL-T1: 2T avg -$0.155 (structural)

**24h Signal PnL (worst):**
- pump-chain-: 6T 50%WR -$0.63
- open-skies+: 2T 0%WR -$0.49 (below kill threshold)
- pullback-entry+: 4T 25%WR -$0.34 (killed 15:10)

**Changes:** None

**No Change Needed:**
- Kill criteria: no 0%WR signal with 3+T last hour
- open-skies+ 2T only — monitor next hour
- atr_sl_hit 64.3% systemic but flat — not crisis
- Trade freq 2/hr healthy
- 0 open positions
- 3d trend recovering

**Open Questions:**
- open-skies+ if drops to 0%WR with 3+T next hour → kill
- pump-chain- at -$0.63/24h but 50%WR — structural not signal

## [2026-09-09 19:10 UTC] Hourly Analysis

**Trades:** 2 closed (2W 0L, +$0.14)
**24h:** 39T 54%WR +$0.04
**Open:** 5 positions all green (+$0.96 unrealized)

**24h Exit Reasons:**
- atr_sl_hit: 24T 61.5% avg -$0.006 (flat, systemic)
- profit-monster-trail: 8T avg +$0.043 (healthy)
- rr_engine_support_tp: 4T avg +$0.023 (healthy)
- rr_engine_resistance: 2T avg -$0.125 (structural)

**Changes:** None

**No Change Needed:**
- Kill criteria: no 0%WR signal with 3+T last hour
- atr_sl_hit 61.5% systemic but flat — not crisis
- Trade freq 2/hr healthy
- 3d trend recovering: Sep 8 -$2.74 → Sep 9 +$0.30 (58.3%WR)

**Open Questions:**
- pump-chain- at -$0.63/24h but 50%WR — monitor
- open-skies+ if drops to 3+T 0%WR → kill

## [2026-09-09 20:10 UTC] Hourly Analysis

**Trades:** 4 closed (4W 0L, +$1.44)
**24h:** 47T 53%WR +$2.12

**24h Exit Reasons:**
- atr_sl_hit: 29T 61.7% avg +$0.055 (profitable)
- profit-monster-trail: 9T avg +$0.041 (healthy)
- rr_engine_support_tp: 5T avg +$0.052 (healthy)
- rr_engine_resistance: 2T avg -$0.125 (structural)

**Changes:** None

**No Change Needed:**
- Kill criteria: no 0%WR signal with 3+T last hour
- open-skies+ 2T 0%WR below threshold — monitor next hour
- atr_sl_hit 61.7% but avg +$0.055 — profitable, not crisis
- Trade freq 4/hr normal
- 3d trend: Sep 8 -$2.74 → Sep 9 +$2.12 (recovering)

**Open Questions:**
- pump-chain- -$0.63/24h but 50%WR — structural drag
- open-skies+ if drops to 3+T 0%WR → kill
