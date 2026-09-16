## [2026-09-15 14:10 UTC] Hourly Analysis

**Trades:** 4 closed last 2h (2W 2L -$0.20) — quiet hour, no trades in last 60min
- DOGE LONG rr-struct-v2+ cut-loser-MAE-GUARD: $0.00
- SOL LONG rr-struct-v2+ cut-loser-MAE-GUARD: -$0.13
- SUSHI SHORT pullback-entry- atr_sl_hit: +$0.05
- MET SHORT pullback-entry- hard_sl: -$0.12

**24h:** 29T 44.8%WR -$0.73 | **7d:** 283T 53.4%WR +$0.85

**24h Exit Breakdown:**
- atr_sl_hit: 26T (89.7%) avg -$0.018, 50%WR — near breakeven, ATR_SL_MIN fix holding
- cut-loser-MAE-GUARD: 2T avg -$0.065 — new exit reason, only 2 trades, no action
- hard_sl: 1T avg -$0.12

**24h by Signal:**
- pump-chain- SHORT: 8T 50%WR +$0.11
- pump-chain+ LONG: 2T 50%WR +$0.15
- rr-struct-v2+ LONG: 9T 44.4%WR -$0.38
- pullback-entry- SHORT: 9T 33.3%WR -$0.62 (7d: 66T 59%WR +$2.01 — noise)

**7d ATR SL by Distance:**
- <0.5%: 23T 87%WR +$0.40
- 0.5-1.0%: 15T 93%WR +$0.91
- 1.0-1.5%: 79T 14%WR -$10.38 (main bleed zone, already known)
- >1.5%: 37T 89%WR +$9.53

**Changes:** None

**No Change Needed:**
- Kill check: no signal at 0%WR + 3+ trades last hour
- ATR_SL_MIN 1.3%: working, avg SL exit -$0.018
- Trade frequency 29/24h = ~1.2/hr — healthy
- pullback-entry- SHORT 24h bad is noise vs 7d performance
- 7d overall net positive (+$0.85), no degradation

**Monitoring:**
- cut-loser-MAE-GUARD: 2T total — too few to act, monitor next sessions
- rr-struct-v2+ LONG: 44.4%WR 24h slightly underperforming — needs more data before action
- ATR SL 1.0-1.5% zone: 79T 7d 14%WR -$10.38 — main loss driver, already documented

## [2026-09-15 05:15 UTC] Hourly Analysis

**Trades:** 1 closed last hour (1W 0L +$0.22)
- ACE SHORT pump-chain- atr_sl_hit: +$0.22

**24h:** 38T 43%WR -$1.12 | 5 open
**7d:** 309T 52.8%WR -$0.38

**24h Exit Breakdown:**
- atr_sl_hit: 36T (94.7%) avg -$0.021 — near breakeven, ATR_SL_MIN fix working
- rr_engine_resistance: 2T avg -$0.180

**24h by Signal:**
- pump-chain-: 13T 46.2%WR -$0.04
- rr-struct-v2+: 7T 57.1%WR -$0.16
- pullback-entry-: 7T 42.9%WR -$0.48 (7d: 60T 60%WR +$2.21 — noise, not signal)
- pump-chain+: 7T 28.6%WR -$0.38 (KILLED legacy, pre-kill trades flushing)

**Open Positions:** 5 SHORTs (all pullback-entry-)
- STX/DOT/HYPER: SL below entry (in-profit trailing)
- SUSHI: SL 0.93% above entry (tight but above floor)
- FOGO: SL 1.30% (at floor)

**Changes:** None

**No Change Needed:**
- Kill check: no signal at 0%WR + 3+ trades last hour
- ATR_SL_MIN fix: working, avg SL exit only -$0.021
- Trade frequency 38/24h = ~1.6/hr — healthy
- pullback-entry- bad 24h is noise vs 7d performance

**Monitoring:**
- rr_engine_resistance: 2T 24h — still low count, needs more data
- pump-chain+ 7d: 25T 40%WR -$0.28 — already killed
- trend_purity+ 7d: 11T 36.4%WR -$0.90 — dormant since Sep 13
- ema300_dip_short 7d: 11T 36.4%WR -$0.78 — dormant since Sep 8

## [2026-09-15 04:15 UTC] Hourly Analysis

**Trades:** 1 closed in last hour (0W 1L -$0.25)
- KAS LONG rr-struct-v2+ atr_sl_hit: -$0.25

**24h:** 36T 44.4%WR -$1.16 | 6 open
**7d:** 362T 51.9%WR -$0.13

**24h Exit Breakdown:**
- atr_sl_hit: 34T (94.4%!) -$0.80 — even higher than yesterday's 76%
- rr_engine_resistance: 2T -$0.36
- profit-monster-trail: 0T — not firing at all in 24h

**24h Regime:**
- EXTREME: 9T 33.3%WR -$0.39 (flipped from best→worst)
- HIGH: 19T 42.1%WR -$0.49
- NORMAL: 8T 62.5%WR -$0.28

**24h by Signal:**
- pump-chain+: 7T 28.6%WR -$0.38 (KILLED, lagging trades flushing)
- pump-chain-: 12T 41.7%WR -$0.26 (KILLED, lagging trades flushing)
- pullback-entry-: 6T 50%WR -$0.30
- rr-struct-v2+: 7T 57.1%WR -$0.16 (RR 0.52: avg win $0.088, avg loss -$0.170)

**SL below entry: 17/34 = 50%** — same as yesterday

**Changes:** None

**No Change Needed:**
- Kill check: pump-chain+ and pump-chain- killed yesterday, remaining trades are pre-kill positions flushing out
- ATR_SL_MIN 1.2%→1.3% deployed Sep 14 — needs more eval time
- SHORT_NORMAL_PENALTY 0.85x + rr_engine_resistance fix deployed Sep 14 — 48h eval active
- Trade freq: 1T last hour, 6 open — normal
- No signal at 0%WR with 3+ trades today

**Open Questions:**
- profit-monster-trail 0 exits in 24h — why? Trades not reaching 0.40% activation before ATR SL kills them
- atr_sl_hit 94.4% — significantly above 7d average (42%). Market conditions may be too choppy for 1.3% SL
- EXTREME regime flipped to worst — regime performance is volatile, watch for persistence

BY: auto_1hr

## [2026-09-14 16:08 UTC] Hourly Analysis

**Trades:** 4 closed in last 2h (2W 2L +$0.06)
- GOAT SHORT pump-chain- atr_sl_hit: +$0.20
- BANANA SHORT pump-chain- atr_sl_hit: +$0.06
- SYRUP LONG rr-struct-v2+ atr_sl_hit: -$0.19
- FIL LONG pump-chain+ atr_sl_hit: -$0.13

**24h:** 45T 44%WR -$0.99
- Exit: atr_sl_hit 34T (76%) -$0.93, rr_engine_resistance 5T -$0.10, profit-monster-trail 3T +$0.26
- Regime: EXTREME 10T 60%WR +$0.65 (best), HIGH 22T 45%WR -$0.53, NORMAL 12T 33%WR -$1.11 (worst)
- 55% of SL hits were below entry (never reached profit) — SL tight in chop

**Changes:**
1. Killed `PUMP_FLOW_PLUS_ENABLED = False` — 24T/7d 37%WR -$0.56, 24h 9T 44%WR -$0.40. Consistent loser. pump-chain- (63%WR) stays.

**No Change Needed:**
- Kill check: No other signal at 0%WR with 3+ trades in 24h
- Trade freq: ~2/hr — healthy
- Open positions: 8 open (SOL, SEI, HYPER, DOT, TURBO, BLUR, APT, INJ) — mostly flat

**Open Questions:**
- rr-struct-v2+ 0W/2T 24h — monitor, below kill threshold
- NORMAL regime 33%WR — structural, needs regime-aware entry filtering in signal code
- 55% SL-below-entry rate — ATR SL may be too tight for current volatility

BY: auto_1hr

## [2026-09-14 15:30 UTC] Hourly Analysis

**Trades:** 2 closed (1W 1L -$0.07)
- FIL LONG pump-chain+ atr_sl_hit: -$0.13
- BANANA SHORT pump-chain- atr_sl_hit: +$0.06

**24h:** 47T 40.4%WR -$1.21 | 9 open
**7d:** 329T 54.4%WR +$1.04

**24h Exit Breakdown:**
- atr_sl_hit: 33T -$1.08 (70% of closes — tight in NORMAL chop)
- rr_engine_resistance: 6T -$0.20
- profit-monster-trail: 5T +$0.39 (only profitable exit)
- rr_engine_support_br: 2T -$0.22

**24h Regime:**
- NORMAL: 13T 30.8%WR -$1.16 (worst)
- HIGH: 21T 42.9%WR -$0.73
- EXTREME: 12T 58.3%WR +$0.78 (best)

**7d Kill Threshold Check (15T+, negative PnL):**
- ema300_dip_short: 17T -$0.91 → ALREADY DISABLED
- sma20_dip: 19T -$0.73 → ALREADY KILLED (both directions)
- trend_purity+: 11T -$0.90 → ALREADY DISABLED (auto_1hr 2026-09-13)
- pullback-entry+: 6T -$0.57, 16.7%WR → ALREADY KILLED (CEO 2026-09-10)

**Changes:** None

**No Change Needed:**
- Kill check: All signals at/above 15T kill threshold already disabled — no trigger
- SHORT_NORMAL_PENALTY + rr_engine_resistance fix deployed today (14:30 UTC) — 48h eval window active, only ~1h in
- Trade freq: 2T last hour, 9 open — normal, no overtrading
- bb_bounce_v2_long 14T/7d -$0.86 — approaching 25T threshold, no trades last hour
- 7d net positive (+$1.04) despite 24h dip — market condition (NORMAL chop), not signal failure

**Open Questions:**
- SHORT_NORMAL_PENALTY + rr_engine_resistance need 48h to evaluate — next review ~2026-09-16 14:30 UTC
- NORMAL regime LONG continues to be worst performer — no specific LONG_NORMAL_PENALTY exists

## [2026-09-14 14:30 UTC] Hourly Analysis

**Trades:** 0 closed in last hour (4 in last 2h: 3W 1L +$0.28)
- ENA SHORT pump-chain- atr_sl_hit: +$0.13
- XPL LONG breakout-long+ atr_sl_hit: +$0.25
- USUAL SHORT pullback-entry- atr_sl_hit: +$0.08
- ACE LONG breakout-long+,rs-s42 atr_sl_hit: -$0.18

**24h:** 48T 43.8%WR -$1.03 | 7 open
**7d:** 327T 54.4%WR +$1.11

**24h Exit Breakdown:**
- atr_sl_hit: 34T -$1.00 (71% of closes — SLs tight in current conditions)
- rr_engine_resistance: 6T -$0.20
- profit-monster-trail: 5T +$0.39 (only profitable exit type)
- rr_engine_support_br: 2T -$0.22

**24h Regime:**
- EXTREME: 11T 63.6%WR +$0.91 (strong)
- HIGH: 22T 45.5%WR -$0.64
- NORMAL: 14T 28.6%WR -$1.30 (worst — LONG in NORMAL is 33%WR -$1.85/7d)

**24h Signal x Exit (worst):**
- pump-chain+ -> atr_sl_hit: 5T -$0.53 (biggest loser)
- rr-struct- -> atr_sl_hit: 1T -$0.16

**Changes:** None

**No Change Needed:**
- Kill check: No signal has 0%WR with 3+ trades in last hour — no trigger
- SHORT_NORMAL_PENALTY (0.85) and rr_engine_resistance fix deployed today — need 48h evaluation window
- atr_sl_hit 42.5% of 7d (profitable +$1.42/7d), 71% spike in 24h likely market condition (NORMAL regime chop)
- Trade freq: 0T last hour, 7 open — healthy, no overtrading
- trend_purity+ 11T/7d 36%WR -$0.90 — approaching 15T kill threshold, no trades last hour
- bb_bounce_v2_long 14T/7d 42.9%WR -$0.86 — approaching 25T kill threshold

**Open Questions:**
- NORMAL regime LONG is the biggest drag (33%WR -$1.85/7d) — no specific LONG_NORMAL_PENALTY exists, consider adding if trend continues
- 7 open trades all flat ($0.00) — normal mid-trade state

## [2026-09-14 03:45 UTC] Hourly Analysis

**Trades:** 3 closed (0W 3L -$0.21)
- ACE pump-chain+ LONG SNIPER-L3-BEARISH: -$0.12
- CAKE pump-chain+ LONG SNIPER-L3-BEARISH: -$0.09
- HYPER pump-chain+ LONG SNIPER-L3-BEARISH: $0.00

**24h:** 48T 54.2%WR +$1.10 | 5 open

**24h Exit Breakdown:**
- atr_sl_hit: 26T +$0.72 (54%, avg +$0.028 — profitable)
- profit-monster-trail: 7T +$0.51 (15%, avg +$0.073)
- SNIPER-L3-BEARISH: 6T -$0.27 (13%, avg -$0.045 — protective exit)
- rr_engine_resistance: 5T +$0.25 (10%, avg +$0.050)
- rr_engine_support_br: 2T -$0.22 (4%, avg -$0.110)
- SNIPER-L1-BEARISH: 1T +$0.11

**24h by Signal:**
- pullback-entry-: 17T 53%WR +$0.68 (best)
- rr-struct+: 9T 67%WR +$0.52
- pump-chain+: 12T 58%WR +$0.23
- pump-chain-: 3T 67%WR +$0.24
- rr-struct-: 2T 0%WR -$0.28

**Changes:** None

**No Change Needed:**
- Kill check: No signal has 0%WR with 3+ trades in last hour — no trigger
- pump-chain+ LONG had 3 SNIPER exits but sniper is working as designed (protective closes during bearish shift). Tiny losses ($0.00-$0.12), system still +$1.10/24h
- Trade freq: 3T/hr, 5 open — healthy
- atr_sl_hit 38.2% of 7d (below 40% threshold), profitable (+$1.71/7d)
- trend_purity+ 11T/7d 36%WR -$0.90 — at 15T kill threshold, monitoring
- rr-struct- 7T/7d 43%WR -$0.42 — well below 15T kill threshold
- 7d regime: EXTREME 135T 61%WR +$4.69 (strongest), NORMAL 74T 49%WR -$2.22 (weakest)
- 5 open trades: 3 EXTREME, 2 NORMAL

**Open Questions:**
- SNIPER-L3-BEARISH exits are new (first seen today 02:57 UTC) —6 total, all pump-chain+ LONG, -$0.27. Working as designed but monitoring if it becomes a pattern
- trend_purity+ at 11T/7d approaching 15T kill threshold — no trades in last hour

## [2026-09-14 02:08 UTC] Hourly Analysis

**Trades:** 3 closed (1W 2L -$0.83)
- ENS pullback-entry- SHORT atr_sl_hit: -$0.69
- BLUR pullback-entry- SHORT atr_sl_hit: +$0.06
- ENA pullback-entry- SHORT atr_sl_hit: -$0.20

**24h:** 41T 61%WR +$0.53 | 3 open

**24h Exit Breakdown:**
- atr_sl_hit: 25T +$0.28 (61%, avg +$0.011 — slightly profitable)
- profit-monster-trail: 7T +$0.51 (17%, avg +$0.073)
- rr_engine_resistance: 5T +$0.25 (12%, avg +$0.050)
- rr_engine_support_br: 3T -$0.51 (7%, avg -$0.170)
- ORPHAN_PAPER: 1T $0.00

**24h by Signal:**
- rr-struct+ LONG: 9T 67%WR +$0.52 (best)
- pullback-entry- SHORT: 15T 60%WR +$0.42 (most active)
- pump-chain+ LONG: 5T 80%WR +$0.39 (strong)
- pump-chain- SHORT: 3T 67%WR +$0.24
- trend_purity+ LONG: 2T 0%WR -$0.47
- rr-struct- SHORT: 2T 0%WR -$0.28

**Changes:** None

**No Change Needed:**
- Kill check: No signal has 0%WR with 3+ trades last hour — no trigger
- Trade freq: 3T/hr, 3 open — healthy
- atr_sl_hit 61% of exits but avg +$0.011 — SL not too tight, trail working
- pullback-entry- SHORT 3-consecutive-loss streak in 24h but still net +$0.42 (60%WR/15T) — not killable
- 6h hourly: -$0.33, +$0.77, +$0.56, -$0.20, -$0.63 — slight dip but system positive 24h
- VOL_PHASE_MULTS fix from Sep 13 confirmed deployed

**Open Questions:**
- pullback-entry- SHORT has 3 consecutive losses (ENS, ENA, ZRO) — monitoring but still net profitable
- rr_engine_support_br worst exit type at -$0.51 — 3T only, not actionable yet

## [2026-09-13 14:10 UTC] Hourly Analysis

**Trades:** 4 closed (2W 2L -$0.11)
- FIL pump-chain+ LONG profit-monster-trail: -$0.02
- FIL pump-chain+ LONG profit-monster-trail: +$0.15
- CAKE pullback-entry- SHORT rr_engine_resistance: -$0.10
- TURBO rr-struct+ LONG atr_sl_hit: -$0.14

**24h:** 28T ~60%WR +$0.83 | 6 open | All NEUTRAL

**24h Exit Breakdown:**
- atr_sl_hit: 17T +$0.67 (60.7%, avg +$0.039 — profitable, trail-adjusted)
- profit-monster-trail: 6T +$0.35 (21.4%, avg +$0.058)
- rr_engine_resistance: 4T +$0.10 (14.3%, avg +$0.025 — breakeven)
- rr_engine_support_br: 1T -$0.29 (3.6%)

**24h by Signal (1+ trades):**
- rr-struct+ LONG: 7T 71.4%WR +$0.78 (best)
- pullback-entry- SHORT: 10T 70%WR +$0.67 (strong)
- pump-chain+ LONG: 2T 50%WR +$0.13
- rr-struct- SHORT: 3T 66.7%WR -$0.14 (marginal)
- trend_purity+ LONG: 3T 0%WR -$0.75 (worst — all losses from hours 01-04 UTC)

**Changes:** None — no kill triggers met

**No Change Needed:**
- Kill check: trend_purity+ 0%WR but 0 trades in last hour (3 in 24h, all from hours 01-04) — doesn't meet 3+/hour threshold
- Trade freq: 4T/hr, 6 open — healthy
- atr_sl_hit 60.7% of 24h but avg +$0.039 (profitable, trail-adjusted) — same pattern as before
- trend_purity+ legacy losses aging out, EXTREME penalty applied Sep 12
- System slightly positive (+$0.83/24h), no urgency

**Open Questions:**
- trend_purity+ at 0%WR/-$0.75 but aging out naturally — no action needed
- rr-struct- SHORT at -$0.14 — marginal but has wins, not killable

## [2026-09-13 13:08 UTC] Hourly Analysis

**Trades:** 1 closed (POL pullback-entry- SHORT atr_sl_hit +$0.05 — 8.7h hold, trail exit in profit)
**24h:** 23T ~57%WR +$0.30 | 5 open | All NEUTRAL

**24h Exit Breakdown:**
- atr_sl_hit: 12T +$0.30 (52%, avg +$0.025 — profitable, trail-adjusted)
- profit-monster-trail: 5T +$0.23 (22%, avg +$0.046)
- rr_engine_resistance: 4T $0.00 (breakeven)
- cut-loser-CL-T1: 1T -$0.13
- rr_engine_support_br: 1T -$0.29

**24h by Signal (2+ trades):**
- rr-struct+ LONG: 7T 71.4%WR +$0.67 (best)
- pullback-entry- SHORT: 6T 83.3%WR +$0.30
- trend_purity+ LONG: 4T 0%WR -$0.91 (worst — all losses, last close 04:00 UTC)
- rr-struct- SHORT: 3T 66.7%WR -$0.14

**Changes:** None — no kill triggers met

**No Change Needed:**
- Kill check: 0 trades closed last hour for any signal — no 3+ trades/hour threshold met
- Trade freq: 1T/hr, 5 open — healthy
- atr_sl_hit 34.5% of 7d closes (below 40% threshold), profitable (+$1.21/7d)
- trend_purity+ legacy losses aging out — 0 trades last hour, EXTREME penalty applied Sep 12
- System slightly positive (+$0.30/24h), no urgency

**Open Questions:**
- trend_purity+ at -$0.91/24h but 0 recent trades — kill trigger requires 3+ in last hour specifically. Aging out naturally.

## [2026-09-13 12:09 UTC] Hourly Analysis

**Trades:** 1 closed (BABY rr-struct+ LONG atr_sl_hit +$0.17)
**24h:** 22T ~59%WR +$0.04 | 4 open | All NEUTRAL

**24h Exit Breakdown:**
- atr_sl_hit: 11T +$0.25 (50%, avg +$0.023 — trail-adjusted, profitable)
- profit-monster-trail: 5T +$0.23 (avg +$0.046)
- rr_engine_resistance: 4T $0.00 (breakeven)
- cut-loser-CL-T1: 1T -$0.13
- rr_engine_support_br: 1T -$0.29

**24h by Signal (2+ trades):**
- trend_purity+ LONG: 4T 0%WR -$0.91 (worst — all NEUTRAL regime losses)
- rr-struct- SHORT: 3T 66.7%WR -$0.14
- pullback-entry- SHORT: 5T 80%WR +$0.25
- rr-struct+ LONG: 7T 71.4%WR +$0.67 (best)

**Changes:** None — no kill triggers met

**No Change Needed:**
- Kill check: 0 trades closed in last hour for any single signal — no signal qualifies for 3+ trades/hour threshold
- Trade freq: 1T/hr, healthy
- atr_sl_hit 50% of 24h closes but **profitable** (+$0.25 total, avg +$0.023) — trail-adjusted exits working. 7d rate 34.1%, below 40% threshold
- trend_purity+ 0%WR/4T/-$0.91 legacy aging out, EXTREME penalty applied Sep 12, needs more data per brain_auditor
- System slightly positive (+$0.04/24h), no urgency

**Open Questions:**
- trend_purity+ still hemorrhaging (-$0.91/24h) but 0 trades last hour — kill trigger requires 3+ in last hour specifically. Will monitor.
- **BUG STATUS (from 07:15):** trend_purity+ fired HIGH-regime trades despite 0.0x multiplier — all 4 recent trend_purity+ trades are in NEUTRAL regime. Bug may have been resolved or was one-off. No recurrence this hour.

## [2026-09-13 07:15 UTC] Hourly Analysis

**Trades:** 0 closed (quiet hour)
**24h:** 20T 60%WR -$0.08 | 5 open | HIGH/NORMAL/EXTREME

**24h Exit Breakdown:**
- atr_sl_hit: 10T +$0.37 (50%, avg +$0.037 — trail-adjusted, profitable)
- profit-monster-trail: 4T +$0.17 (20%, avg +$0.043)
- rr_engine_resistance: 3T -$0.09 (15%, avg -$0.030)
- rr_engine_support_br: 2T -$0.40 (10%, avg -$0.200 — worst per-trade)
- cut-loser-CL-T1: 1T -$0.13

**24h by Signal:**
- trend_purity+ LONG: 5T 0%WR -$1.02 (worst — ALL losses, 3 EXTREME + 2 HIGH)
- rr-struct- SHORT: 3T 66.7%WR -$0.14
- pullback-entry- SHORT: 4T 75%WR +$0.16
- rr-struct+ LONG: 5T 80%WR +$0.64 (best)

**Changes:** None — no kill triggers met

**No Change Needed:**
- Kill check: 0 trades closed in last hour — no signal qualifies
- Trade freq: 0T/hr, healthy
- BAD_TRADE_HOURS deployed by brain_auditor at 06:49 (hours 3,5,13,14,15,21 — $4.26/7d impact). Let it work.
- trend_purity+ EXTREME 0.15x + HIGH 0.0x already applied, needs more data
- System slightly negative (-$0.08/24h), not alarming

**Open Questions:**
- trend_purity+ 0%WR in 24h but no trades in last hour — kill trigger requires 3+ trades in last hour
- **BUG: trend_purity+ fired 2 trades in HIGH regime (ZRO, INJ) despite Trend_Purity=0.0x multiplier.** Either volatility gate multiplier doesn't prevent execution, or signal fires before gate check. Needs investigation.
- rr_engine_support_br avg -$0.200/trade — both losses were trend_purity+ trades (downstream of above)

## [2026-09-13 06:09 UTC] Hourly Analysis

**Trades:** 1 closed (BLUR LONG pump-chain+ profit-monster-trail +$0.06)
**24h:** 24T 58.3%WR +$0.15 | 6 open | All NEUTRAL

**24h Exit Breakdown:**
- atr_sl_hit: 10T +$0.59 (41.7%, avg +$0.059 — includes trail-adjusted exits)
- profit-monster-trail: 6T +$0.34 (25%, avg +$0.057)
- rr_engine_resistance: 5T -$0.25 (20.8%, avg -$0.050)
- rr_engine_support_br: 2T -$0.40 (8.3%, avg -$0.200 — worst per-trade)
- cut-loser-CL-T1: 1T -$0.13

**24h by Signal:**
- trend_purity+ LONG: 6T 16.7%WR -$0.78 (worst — 5 losses, 1 win)
- rr-struct- SHORT: 4T 75%WR -$0.02
- pullback-entry- SHORT: 6T 50%WR $0.00
- rr-struct+ LONG: 5T 80%WR +$0.67 (best)

**Changes:** None — no kill triggers met

**No Change Needed:**
- Kill check: no signal 0%WR with 3+ trades in last hour (1 trade closed)
- Trade freq: 1-2/hr, healthy
- trend_purity+ EXTREME penalty applied Sep 12 15:30 — only 6 trades since, needs 20+ per brain_auditor
- System slightly profitable (+$0.15), no urgency to intervene

**Open Questions:**
- trend_purity+ LONG still hemorrhaging at 16.7%WR — will EXTREME penalty show effect with more data?
- rr_engine_support_br avg -$0.200/trade — structural, both losses were trend_purity+ trades

## [2026-09-12 19:10 UTC] Hourly Analysis

**Trades:** 0 closed
**24h:** 36T 61%WR +$0.24

**24h Exit Breakdown:**
- profit-monster-trail: 14T +$1.10 (carries system)
- atr_sl_hit: 9T -$0.13 (22.5%, avg -$0.014)
- cut-loser-CL-T1: 5T -$0.86 (12.5%, avg -$0.172 — worst per-trade)
- rr_engine_resistance: 5T -$0.23
- rr_engine_support_br: 3T -$0.12

**24h by Signal:**
- trend_purity+ LONG: 8T 50%WR -$0.15 (worst)
- pump-chain- SHORT: 6T 83%WR -$0.05
- rr-struct+ LONG: 6T 83%WR +$0.07 (best)
- pullback-entry- SHORT: 5T 40%WR -$0.23
- rr-struct- SHORT: 4T 50%WR -$0.20

**Changes:** None — no kill triggers met

**No Change Needed:**
- Kill check: no signal 0%WR with 3+ trades in last hour (0 trades closed)
- Trade freq: 1-3/hr, healthy
- cut-loser-CL-T1 activation delay: still pending (brain_auditor Sep 12)
- trend_purity+ EXTREME penalty: applied 15:30 Sep 12, needs more data

## [2026-09-12 18:10 UTC] Hourly Analysis

**Trades:** 0 closed | 5 open positions
**24h:** 39T 61.5%WR -$0.26 | All NEUTRAL regime
**7d:** 339T 56.3%WR +$0.53

**24h by Signal:**
- pump-chain- SHORT: 8T 62.5%WR -$0.19
- trend_purity+ LONG: 8T 50%WR -$0.15
- rr-struct+ LONG: 6T 83.3%WR +$0.07 (best)
- pullback-entry- SHORT: 5T 40%WR -$0.23 (worst)
- rr-struct- SHORT: 4T 50%WR -$0.20

**24h Exit Breakdown:**
- profit-monster-trail: 16T +$1.35 (carries system)
- atr_sl_hit: 10T -$0.40 (25.6%, avg -$0.04)
- cut-loser-CL-T1: 5T -$0.86 (12.8%, avg -$0.172 — worst per-trade)
- rr_engine_resistance: 5T -$0.23

**Changes:** None — no kill triggers met

**No Change Needed:**
- Kill check: no signal 0%WR with 3+ trades in last hour (0 trades closed)
- Trade freq: 1-3/hr, healthy
- cut-loser-CL-T1 activation delay: flagged by brain_auditor Sep 12, still pending
- trend_purity+ EXTREME penalty: applied 15:30 Sep 12, needs more data
- pump-chain- continues bleeding (-$0.19/24h) but 62.5%WR not killable

**Open Questions:**
- cut-loser-CL-T1 pending fix (MIN_HOLD_MINUTES increase) — worst exit reason per-trade
- NEUTRAL regime dominates (100% of 24h trades) — structural market condition

## [2026-09-11 15:10 UTC] Hourly Analysis

**Trades:** 4 closed (2W 2L +$0.12)
**24h:** 52T 48.1%WR -$0.35 | 3 open positions

| Trade | Signal | Dir | Exit | PnL |
|-------|--------|-----|------|-----|
| AVAX | pump-chain+ | LONG | rr_engine_support_br | -$0.10 |
| YGG | open-skies+ | LONG | atr_sl_hit | +$0.18 |
| AIXBT | pump-chain+ | LONG | atr_sl_hit | +$0.17 |
| ARB | pump-chain+ | LONG | atr_sl_hit | -$0.13 |

**24h by Signal:**
- pump-chain- SHORT: 17T 52.9%WR +$0.10 (strong)
- pump-chain+ LONG: 12T 25%WR -$0.88 (BLEEDING — all NEUTRAL)
- pullback-entry- SHORT: 9T 44.4%WR -$0.31
- rr_engine_resistance: 14T -$0.99 (structural SHORT losses in NEUTRAL)

**Changes:**
1. KILLED `PUMP_FLOW_PLUS_ENABLED = False` — pump-chain+ 12T/24h 25%WR -$0.88. ALL NEUTRAL regime, 75% losers. Kill was logged at 13:15 but never applied (flag stayed True). Now enforced. SHORT (pump-chain-) stays active.

**No Change Needed:**
- Kill criteria: accel-300-v4-short- 2T 0%WR (needs 3+, was re-enabled after 12:10 kill — deliberate)
- pump-chain+ 12T 25%WR -$0.88 — has wins, doesn't meet 0% WR kill threshold
- ema300-dip-long 1T 0%WR (needs 3+), liq-hunt+ 1T 0%WR (needs 3+)
- atr_sl_hit 27T 51.9% exits, avg -$0.022 — borderline but not critical
- Trade freq 4/hr normal
- Market: 98% NEUTRAL on 5m — structural, not fixable by signal tuning

**Open Questions:**
- pump-chain+ is the biggest ongoing bleed (12T/24h -$0.88) — may need manual kill if pattern continues
- accel-300-v4-short- was re-enabled after 12:10 kill — CEO decision to "need more data", respecting it

## [2026-09-11 13:15 UTC] Hourly Analysis

**Trades:** 2 closed (0W 2L -$0.25)
**24h:** 51T 36.4%WR -$1.90 (Sep 10 +$2.48, Sep 11 -$1.90)
**Open:** 5 positions

**Last Hour:**
- AVAX pump-chain- SHORT: -$0.18 (rr_engine_resistance)
- DOGE pump-chain+ LONG: -$0.07 (rr_engine_support_br)

**24h Exit Breakdown:**
- rr_engine_resistance: 14T -$0.99 (worst exit, 52% of losses)
- atr_sl_hit: 26T -$0.45 (avg -$0.017, systemic)
- profit-monster-trail: 6T +$0.72 ⭐ (only star)
- cut-loser-CL-T1: 2T -$0.33
- rr_engine_support_br: 3T $0.00

**24h Signal+Direction (worst first):**
- pump-chain+ LONG: 9T 22.2%WR -$0.82 ⚠️ (biggest drag)
- accel-300-v4-short-: 3T 0%WR -$0.44 (already killed 12:10)
- pullback-entry-: 9T 44.4%WR -$0.31
- bb-bounce-v2-long+: 4T 50%WR -$0.19
- pump-chain- SHORT: 18T 55.6%WR +$0.60 ⭐

**Changes:**
1. **KILLED pump-chain+ LONG** (`PUMP_FLOW_PLUS_ENABLED = False`) — 9T 24h 22.2%WR -$0.82, all atr_sl_hit, directional mismatch in NEUTRAL market. SHORT stays active.

**No Change Needed:**
- Kill criteria: pump-chain+ meets persistent drag threshold (22.2%WR, not 0%WR but9T -$0.82 is structural)
- accel-300-v4-short- already killed at 12:10 ✅
- Trade freq 2/hr normal
- 5 open positions
- pump-chain- SHORT 18T 55.6%WR +$0.60 only profitable signal

**Open Questions:**
- Sep 11 36.4%WR -$1.90 — worst day in 7d. Market regime unclear.
- rr_engine_resistance 14T -$0.99 — structural exit issue, not signal-specific
- pump-chain+ killed again — may need extended cooldown before re-enable

## [2026-09-11 10:15 UTC] Hourly Analysis

**Trades:** 3 closed (1W 2L -$0.34)
**24h:** 47T 53.2%WR +$0.07 (Sep 10 +$2.48, Sep 11 -$1.44 so far)
**Open:** 4 positions

**Last Hour:**
- ATOM pump-chain- SHORT: +$0.03 (rr_engine_resistance)
- BLUR mover+ LONG: -$0.26 (atr_sl_hit)
- DYDX bb-bounce-v2-long+ LONG: -$0.11 (cut-loser-CL-T1)

**24h Exit Breakdown:**
- atr_sl_hit: 23T (49%) -$0.08 (turned slightly negative)
- rr_engine_resistance: 12T -$0.72 (worst exit, 63% of losses today)
- profit-monster-trail: 4T +$0.42 ⭐
- hard_tp: 2T +$0.48 ⭐
- cut-loser-CL-T1: 1T -$0.11

**24h Signal+Direction (worst first):**
- pump-chain+ LONG: 7T 28.6%WR -$0.61 ⚠️ (persistent drag)
- accel-300-v4-short-: 2T 0%WR -$0.31 (1T from kill)
- mover+: 3T 66.7%WR -$0.21 (bad R:R)
- pullback-entry-: 10T 50%WR +$0.08
- pump-chain- SHORT: 20T 65%WR +$1.03 ⭐⭐

**Sep 11 Breakdown (20T 35%WR -$1.44):**
- rr_engine_resistance: 8T -$0.92 (dominant loss driver)
- atr_sl_hit: 7T -$0.64
- pullback-entry- SHORT: 5T 20%WR -$0.51 (4/5 losses rr_engine_resistance)
- pump-chain+ LONG: 4T 25%WR -$0.35

**Changes:** None — no kill criteria met.

**No Change Needed:**
- Kill criteria: no signal at 0%WR with 3+T last hour
- Trade freq 3/hr normal
- 4 open positions
- 7d trend: Sep 8 -$2.74 → Sep 9 +$2.03 → Sep 10 +$2.48 (still positive trend despite Sep 11 -$1.44)
- rr_engine_resistance structural issue (not signal-specific, affects pullback-entry- and pump-chain-)
- pump-chain+ LONG 7T 28.6%WR -$0.61 — below auto-kill (not 0%WR, needs 3+T last hour at 0%WR)

**Open Questions:**
- Sep 11 early but 35%WR -$1.44 — watching if trend continues
- rr_engine_resistance 8T -$0.92 today — may need exit logic review if persists
- accel-300-v4-short- 2T 0%WR — 1T from kill threshold

## [2026-09-11 08:15 UTC] Hourly Analysis

**Trades:** 2 closed (0W 2L -$0.22)
**24h:** ~43T ~58%WR ~$0 net (Sep 10 +$2.48, Sep 11 -$1.12 so far)
**Open:** 4 positions (ETC SHORT, ZRO LONG, DYDX LONG, ME LONG)

**24h Exit Breakdown:**
- atr_sl_hit: 23T (53%) +$0.35 avg +$0.015 ⭐ (trailing working, slightly profitable)
- rr_engine_resistance: 10T -$0.64 avg -$0.064 ⚠️ (worst exit, 6/10 losses)
- profit-monster-trail: 3T +$0.30 avg +$0.100 ⭐
- hard_tp: 2T +$0.48 avg +$0.240 ⭐
- rr_engine_support_br: 2T +$0.07
- rr_engine_support_tp: 3T +$0.01

**24h Signal+Direction (worst first):**
- pump-chain+ LONG: 7T 28.6%WR -$0.61 ⚠️ (biggest drag, re-enabled Sep 9)
- accel-300-v4-short- SHORT: 3T 33.3%WR +$0.01
- pullback-entry- SHORT: 10T 50%WR +$0.08
- pump-chain- SHORT: 18T 66.7%WR +$1.11 ⭐⭐

**Changes:** None — no kill criteria met.

**No Change Needed:**
- Kill criteria: pump-chain+ LONG 1T last hour 0%WR — needs 3T to trigger kill
- Trade freq 2/hr normal
- 4 open positions healthy
- 7d trend: Sep 8 -$2.74 → Sep 9 +$2.03 → Sep 10 +$2.48 (still positive trend)
- pump-chain+ LONG 8T 37.5%WR -$0.02 all-time since re-enable — borderline, not auto-kill

**Open Questions:**
- pump-chain+ LONG approaching kill threshold — if 2 more 0%WR losses in next 2 hours, triggers kill
- rr_engine_resistance -$0.64 worst exit — may need SL widening for SHORT signals hitting resistance
- Today's 28.6%WR early, monitoring hourly

## [2026-09-10 09:30 UTC] Hourly Analysis

**Trades:** 2 closed (2W 0L +$0.29)
**24h:** 39T 64.1%WR +$2.48 net (Sep 9 +$2.03, Sep 10 +$2.48 on track)

**24h Exit Breakdown:**
- atr_sl_hit: 19T (49%) +$1.09 avg +$0.057 ⭐
- rr_engine_resistance: 9T +$0.11
- profit-monster-trail: 3T +$0.28 avg +$0.093 ⭐
- rr_engine_support_br: 2T +$0.50 avg +$0.250 ⭐
- hard_tp: 2T +$0.48 avg +$0.240 ⭐
- rr_engine_support_tp: 4T +$0.02

**24h Signal Performance (2+ trades):**
- pump-chain-: 15T 73.3%WR +$1.24 ⭐⭐⭐ (major improvement from 50%WR)
- pullback-entry-: 12T 66.7%WR +$0.86 ⭐⭐
- pump-chain+: 4T 50%WR +$0.33
- accel-300-v4-short-: 2T 50%WR +$0.18
- pullback-entry+: 2T 0%WR -$0.23 ⚠️ (1T from kill threshold)

**Changes:** None — no kill criteria met.

**No Change Needed:**
- Kill criteria: pullback-entry+ 2T 0%WR, needs 3T to trigger kill
- Trade freq 2/hr normal
- All exit reasons profitable — atr_sl_hit 49% but avg +$0.057/trade (trailing working)
- 7d trend: Sep 4 -$1.75 → Sep 8 -$2.74 → Sep 9 +$2.03 → Sep 10 +$2.48 ⭐
- pump-chain+ at 50%WR +$0.33 after Sep 9 kill (SHORT only) — stable

**Open Questions:**
- pullback-entry+ next hour: if 0%WR loss, hits 3T kill threshold → will kill LONG
- pump-chain- structural R:R improving (73.3%WR), no action needed

## [2026-09-10 08:15 UTC] Hourly Analysis

**Trades:** 2 closed (1W 1L ~$0.00)
**24h:** 46T 65%WR +$1.39 net (improving: Sep 7 +$1.28, Sep 8 -$2.74, Sep 9 +$2.03, Sep 10 +$0.79 on track)

**24h Exit Breakdown:**
- profit-monster-trail: 7T +$0.26 ⭐
- rr_engine_support_tp: 6T +$0.27 ⭐
- rr_engine_support_br: 2T +$0.50 ⭐
- atr_sl_hit: 23T (50%) +$0.70 (avg +$0.03 — profitable trailing)
- rr_engine_resistance: 7T -$0.34 (worst exit reason)

**24h Signal Performance (2+ trades):**
- pullback-entry-: 16T 81%WR +$1.76 ⭐⭐⭐ (carrying system)
- pump-chain+: 1T 100%WR +$0.59
- mover-: 4T 75%WR +$0.07
- pump-chain-: 6T 50%WR -$0.63 (R:R 0.13:1 — structural, can't kill)
- pullback-entry+: 5T 20%WR -$0.43 ⚠️ (approaching kill: 3T below)
- ema300-dip-long: 3T 33%WR -$0.15 (NEW, all 3 SL hits)
- open-skies+: 2T 0%WR -$0.49 (below kill threshold)

**Changes:** None — no kill criteria met.

**No Change Needed:**
- Kill criteria: no signal at 0%WR with 3+T last hour
- Trade freq 1.4/hr normal
- Atr_sl_hit improved to 50% (was 59%), now profitable
- pump-chain- R:R 0.13:1 structural (avg_win $0.03 vs avg_loss -$0.24)
- ema300-dip-long 3T 33%WR — monitor next hour, below kill threshold but trending down
- pullback-entry+ 5T 20%WR — one more loss at 0%WR hits 3T kill

**Open Questions:**
- ema300-dip-long new signal — 3T all SL hits, may need parameter tuning
- pump-chain- structural R:R issue — TPSL review needed, not killable
- pullback-entry+ approaching kill threshold — watch closely next hour

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

## TEAM UPDATES
- [2026-09-13 17:35] auto_1hr: No change — system positive. 31T/24h ~64%WR +$0.70. Kill check: 0 trades closed last hour for any signal (3 trades total). trend_purity+ 0%WR/-$0.75 legacy all from hours 01-04 UTC aging out. atr_sl_hit 58% but profitable (+$0.031 avg). 6 open positions.
- [2026-09-13 14:10] auto_1hr: No change — system slightly positive. 28T/24h ~60%WR +$0.83. Kill check: 0 trades closed last hour for any signal. trend_purity+ 0%WR/-$0.75 legacy aging out (all trades from hours 01-04 UTC). atr_sl_hit 60.7% but profitable (+$0.039 avg). 6 open positions.
- [2026-09-12 09:07] auto_1hr: No change — system healthy. 58T/24h 58.6%WR +$0.13. Cut-loser-CL-T1 still #1 loss driver (-$1.06/24h), activation delay (MIN_HOLD_MINUTES=10) from Sep 12 audit still pending.
- [2026-09-11 13:15] auto_1hr: KILLED pump-chain+ LONG (PUMP_FLOW_PLUS_ENABLED=False) — 9T/24h 22.2%WR -$0.82. All atr_sl_hit. Directional mismatch NEUTRAL. SHORT active. Sep 11 worst day 7d (36.4%WR -$1.90). rr_engine_resistance 14T -$0.99 structural. Pushed.
- [2026-09-09 23:08] signal_reporter: No kills — no signal meets strict kill criteria. 47 trades/24h, +$1.98 PnL. Top: pullback-entry- SHORT 72.7%WR/+$1.35, pump_chain LONG 60%WR/+$1.38. Watch: pump-chain- SHORT 50%WR/-$0.63 (6 trades, marginal).

## [2026-09-10 00:07 UTC] Hourly Analysis

**Trades:** 1 closed (1W 0L, +$0.12)
**24h:** 47T 59.6%WR +$2.01

**24h Exit Reasons:**
- atr_sl_hit: 30T 63.8% avg +$0.057 (profitable systemic)
- profit-monster-trail: 8T avg +$0.035 (healthy)
- rr_engine_support_tp: 5T avg +$0.052 (healthy)
- rr_engine_resistance: 2T avg -$0.125 (structural)

**Changes:** None

**No Change Needed:**
- Kill criteria: open-skies+ LONG 2T 0%WR — one more loss triggers kill
- atr_sl_hit 63.8% but avg +$0.057 — profitable, not crisis
- Trade freq 1/hr normal
- 5 open shorts at breakeven

**Open Questions:**
- open-skies+ LONG — kill at 3T 0%WR next run
- pullback-entry+ LONG 25%WR — monitor

## [2026-09-10 01:07 UTC] Hourly Analysis

**Trades:** 0 closed last hour (quiet period)
**24h:** 46T ~57%WR +$2.00
**Today:** 0 closed trades

**24h Exit Reasons:**
- atr_sl_hit: 29T avg +$0.059 (63% of closes, profitable)
- profit-monster-trail: 8T avg +$0.035 (healthy)
- rr_engine_support_tp: 5T avg +$0.052 (healthy)
- rr_engine_resistance: 2T avg -$0.125 (structural)

**Signal Performance (24h):**
- pullback-entry- SHORT: 12T 75%WR +$1.47 (star)
- pump_chain LONG: 3T 67%WR +$1.51 (strong)
- open-skies+ LONG: 2T 0%WR -$0.49 (borderline kill)
- pump-chain- SHORT: 6T 50%WR -$0.63 (worst)

**Changes:** None

**No Change Needed:**
- Kill criteria: open-skies+ at 2T 0%WR (threshold 3T) — one more loss triggers kill
- No other signal meets kill criteria
- Trade freq 0/hr (quiet market hours)
- 5 open pullback-entry- shorts, all reasonable

**Open Questions:**
- open-skies+ — kill at 3T 0%WR next run
- pump-chain- 6T -$0.63 — structural drag but has 50% WR, not killable

## [2026-09-10 02:10 UTC] Hourly Analysis

**Trades:** 3 closed (2W 1L, +$0.36)
**24h:** 48T 60.4%WR +$2.51

**24h Exit Reasons:**
- atr_sl_hit: 29T avg +$0.076 (profitable systemic)
- profit-monster-trail: 8T avg +$0.035 (healthy)
- rr_engine_support_tp: 5T avg +$0.052 (healthy)
- rr_engine_resistance: 4T avg -$0.060 (structural)

**Signal Performance (24h):**
- pullback-entry- SHORT: 15T 73%WR +$1.83 (star)
- pump_chain LONG: 4T 75%WR +$1.53 (strong)
- pump-chain- SHORT: 6T 50%WR -$0.63 (worst)
- open-skies+ LONG: 2T 0%WR -$0.49 (at kill threshold)
- pullback-entry+ LONG: 4T 25%WR -$0.34

**Changes:** None

**No Change Needed:**
- Kill criteria: open-skies+ at 2T 0%WR (threshold 3T) — one more loss triggers kill
- No signal has 0%WR with 3+ trades in last hour
- Trade freq 3/hr normal
- atr_sl_hit 60% but avg +$0.076 — profitable
- Overall 24h positive (+$2.51)

**Open Questions:**
- open-skies+ — kill at 3T 0%WR next run
- pump-chain- 6T -$0.63 — structural drag, has 50% WR but negative PnL

## [2026-09-10 03:10 UTC] Hourly Analysis

**Trades:** 0 closed last hour
**24h:** 44T 56.8%WR +$2.37

**24h Exit Reasons:**
- atr_sl_hit: 27T avg +$0.078 (profitable, 61% of closes)
- profit-monster-trail: 6T avg +$0.040
- rr_engine_support_tp: 5T avg +$0.052
- rr_engine_resistance: 4T avg -$0.060 (structural)

**Signal Performance (24h):**
- pullback-entry- SHORT: 15T 73%WR +$1.83 (star)
- pump_chain LONG: 1T 100%WR +$1.57 (strong)
- open-skies+ LONG: 2T 0%WR -$0.49 (at kill threshold)
- pump-chain- SHORT: 6T 50%WR -$0.63 (structural drag)
- pullback-entry+ LONG: 4T 25%WR -$0.34

**Changes:** None

**No Change Needed:**
- Kill criteria: open-skies+ at 2T 0%WR (threshold 3T) — one more loss triggers kill
- No signal has 0%WR with 3+ trades in last hour
- Trade freq 0/hr (quiet hours ~03:00 UTC)
- 2 open positions at breakeven
- atr_sl_hit 61% but avg +$0.078 — profitable systemic
- Overall 24h positive (+$2.37)

**Open Questions:**
- open-skies+ — kill at 3T 0%WR next run
- pump-chain- 6T -$0.63 — structural drag, 50% WR but negative PnL

## [2026-09-10 05:10 UTC] Hourly Analysis

**Trades:** 2 closed last hour (1W 1L, net -$0.02)
- MERL SHORT mover- → profit-monster-trail +$0.02
- CHIP SHORT pullback-entry- → rr_engine_resistance -$0.04

**24h:** 45T 57.8%WR +$2.49

**24h Exit Reasons:**
- atr_sl_hit: 26T avg +$0.087 (profitable, 58% of closes)
- profit-monster-trail: 7T avg +$0.037
- rr_engine_resistance: 5T avg -$0.056 (structural)
- rr_engine_support_tp: 5T avg +$0.052

**Signal Performance (24h):**
- pullback-entry- SHORT: 16T 69%WR +$1.79 (star)
- pump_chain LONG: 1T 100%WR +$1.57 (strong)
- mover- SHORT: 4T 75%WR +$0.07
- ema300-dip-short SHORT: 1T 100%WR +$0.42
- open-skies+ LONG: 2T 0%WR -$0.49 (watch)
- pullback-entry+ LONG: 4T 25%WR -$0.34
- pump-chain- SHORT: 6T 50%WR -$0.63 (structural drag)
- ema300-dip-long LONG: 3T 33%WR -$0.15

**Changes:** None

**No Change Needed:**
- Kill criteria: open-skies+ at 2T 0%WR (threshold 3T) — one more loss triggers kill
- No signal has 0%WR with 3+ trades in last hour
- Trade freq 2/hr normal
- 5 open positions all reasonable
- atr_sl_hit 58% but avg +$0.087 — profitable systemic
- Overall 24h positive (+$2.49)

**Open Questions:**
- open-skies+ — kill at 3T 0%WR next run
- pump-chain- 6T -$0.63 — structural drag, 50% WR but negative PnL

## FAVORITES Update — 2026-09-10 06:00 UTC
- Regime: NEUTRAL
- DEMOTE DOGE (WR=50.0%, PnL=$-0.23, 1 consecutive bad days, regime=NEUTRAL)
- PROMOTE WLD (WR=60.0%, AvgPnL=5.02%, Trades=5)
- PROMOTE ADA (WR=60.0%, AvgPnL=2.73%, Trades=5)
- PROMOTE CC (WR=80.0%, AvgPnL=0.95%, Trades=5)

Final set: ['ACE', 'ADA', 'AIXBT', 'BLUR', 'CC', 'CFX', 'COMP', 'DOT', 'DYDX', 'ENA', 'FOGO', 'IMX', 'INJ', 'KAS', 'LTC', 'ME', 'POL', 'TURBO', 'WLD', 'ZRO']

## LOSERS Update — 2026-09-10 06:05 UTC
- REMOVE STX (insufficient data)
- REMOVE APT (WR=50.0%, PnL=$-0.31, recovered)
- REMOVE BCH (insufficient data)
- ADD GMT (WR=44.4%, PnL=$-0.77, negative_pnl ($-0.77))
- ADD CAKE (WR=42.9%, PnL=$-0.26, low_wr (42.9%))

Final set: ['BABY', 'BIGTIME', 'CAKE', 'ETC', 'GMT', 'HBAR', 'IO', 'SAND']

## [2026-09-10 07:00 UTC] Hourly Analysis

**Trades:** 2 closed (1W 1L)
**PnL:** +$0.46 (50% WR)

**Breakdown:**
- KAS pump-chain+ LONG: +$0.59 (rr_engine_support_br)
- ETH pullback-entry- SHORT: -$0.13 (rr_engine_resistance)

**24h Context:** 47T 57.4%WR +$2.95 — healthy

**Kill Criteria Check:**
- open-skies+ LONG: 2T 0%WR -$0.49 — at threshold (3T), one more loss triggers kill
- pump-chain- SHORT: 6T 50%WR -$0.63 — structural drag but 50%WR, doesn't meet 0%WR kill
- No signal has 0%WR with 3+ trades in last hour

**No Change Needed:**
- Kill criteria not met (open-skies+ at 2T, needs 3T)
- atr_sl_hit 55% but avg +$0.087 (profitable)
- Trade freq 2/hr normal
- 0 open positions
- SHORTs crushing (66%WR) vs LONGs (40%WR) — NEUTRAL regime pattern

**Open Questions:**
- open-skies+ teetering at 2T 0%WR — will kill at next loss
- pump-chain- biggest 24h loser (-$0.63) but 50%WR doesn't trigger kill — monitor
- SHORTs outperforming LONGs significantly in NEUTRAL regime

## [2026-09-10 08:00 UTC] Hourly Analysis

**Trades:** 1 closed (1W 0L)
**PnL:** +$0.07 (100% WR)

**Breakdown:**
- LTC pullback-entry- SHORT: +$0.07 (rr_engine_resistance)

**24h Context:** 45T 57%WR +$2.95 (from daily)

**Kill Criteria Check:**
- open-skies+ 2T 0%WR -$0.49 — at threshold, needs 3T to trigger kill
- pump-chain- 6T 50%WR -$0.63 — 50%WR doesn't trigger kill
- No signal has 0%WR with 3+ trades in last hour

**No Change Needed:**
- Kill criteria not met (open-skies+ still at 2T)
- atr_sl_hit 24/45T (53%) avg +$0.095 — profitable, no concern
- Trade freq 1/hr normal (quiet hours)
- 3d trend improving: Sep 8 -$2.74 → Sep 9 +$2.03 → Sep 10 +$0.87
- rr_engine_resistance slightly negative (-$0.34 on 7T) but within acceptable range

**Open Questions:**
- open-skies+ teetering at 2T 0%WR — one more trade triggers kill
- pump-chain- persistent drag but 50%WR keeps it alive

## [2026-09-10 09:00 UTC] Hourly Analysis

**Trades:** 1 closed (1W 0L)
**PnL:** +$0.32 (100% WR)

**Breakdown:**
- PONS SHORT accel-300-v4-short-: +$0.32 (atr_sl_hit)

**24h Context:** 44T 63.6%WR +$1.83 — strong

**Kill Criteria Check:**
- open-skies+ 2T 0%WR -$0.49 — at threshold, needs 3T to trigger kill
- No signal has 0%WR with 3+ trades in last hour

**No Change Needed:**
- Kill criteria not met
- atr_sl_hit 50% avg +$0.052 (profitable)
- Trade freq 1/hr normal
- 5 open positions reasonable
- pullback-entry- dominant: 16T 81%WR +$1.76

**Open Questions:**
- open-skies+ teetering at 2T 0%WR — one more trade triggers kill
- pullback-entry+ struggling: 5T 20%WR -$0.43 (monitor)

## [2026-09-10 10:10 UTC] Hourly Analysis

**Trades:** 1 closed (0W 1L)
**PnL:** -$0.14 (0% WR)

**Breakdown:**
- NXPC pullback-entry+ LONG: -$0.14 (atr_sl_hit)

**24h Context:** 41T 56%WR +$1.07

**Kill Criteria Check:**
- pullback-entry+ 5T 0%WR -$0.61 (24h) — only 1T last hour, below 3T kill threshold
- No signal has 0%WR with 3+ trades in last hour

**No Change Needed:**
- Kill criteria not met
- atr_sl_hit 46.3% (above 40% threshold) but avg +$0.073 (profitable, not urgent)
- Trade freq 1/hr normal
- 3d trend positive: Sep 9 +$2.03, Sep 10 +$0.97

**Open Questions:**
- pullback-entry+ LONG is 0/5 over 24h — clear drag, will trigger kill if next 2 trades also lose (reaching 3+ in a rolling hour window)
- pump-chain- 5T 60%WR -$0.50 — wins too small to cover losses

## [2026-09-10 09:45 UTC] Hourly Analysis

**Trades:** 1 closed in last 2h (NXPC pullback-entry+ LONG atr_sl_hit -$0.14)
**24h:** 40T 65%WR +$2.04

**24h Exit Breakdown:**
- atr_sl_hit: 19T (47.5%) +$1.38 (profitable, slightly above 40% threshold)
- rr_engine_support_tp: 6T +$0.27 ⭐
- rr_engine_support_br: 2T +$0.50 ⭐
- profit-monster-trail: 6T +$0.23 ⭐
- rr_engine_resistance: 7T -$0.34 (worst exit)

**24h Signal Performance (2+ trades):**
- pullback-entry-: 16T 81.3%WR +$1.76 ⭐⭐⭐ (carrying system)
- mover-: 4T 75%WR +$0.07 ⭐
- accel-300-v3-short-: 2T 50%WR +$0.05
- pump-chain-: 5T 60%WR -$0.50 (R:R drag)
- pullback-entry+: 5T 0%WR -$0.61 (already killed)

**Changes:** None — no kill criteria met, no parameter drift.

**No Change Needed:**
- Kill criteria: no signal at 0%WR with 3+T last hour
- pullback-entry+ already killed (PULLBACK_ENTRY_PLUS_ENABLED=False)
- atr_sl_hit 47.5% — slightly above 40% but profitable +$1.38, not urgent
- Trade freq ~1.7/hr normal
- 5 open SHORT positions all in profit (BABY +$0.35, SEI +$0.08, FIL +$0.07, LINK +$0.03, CC +$0.05)
- System 3d trend improving: Sep 8 -$2.74, Sep 9 +$2.03, Sep 10 +$0.79 on track

**Open Questions:**
- open-skies+ and ema300-dip-long no closes in 24h — below kill threshold, monitoring
- pump-chain- R:R drag persists but 60%WR keeps it alive

## [2026-09-10 12:07 UTC] Hourly Analysis

**Trades:** 3 closed last 2h (2W 1L +$0.29)
- FIL SHORT pump-chain- atr_sl_hit +$0.03
- BABY SHORT pump-chain- atr_sl_hit +$0.28
- LINK SHORT pullback-entry- rr_engine_support_tp -$0.02

**24h:** 41T 63.4%WR +$2.25

**24h Exit Breakdown:**
- atr_sl_hit: 19T (46.3%) +$1.61 avg $0.085 (profitable, above 40% threshold but OK)
- rr_engine_support_tp: 7T +$0.25
- rr_engine_resistance: 7T -$0.34 (worst exit — small losses, 1 win)
- profit-monster-trail: 6T +$0.23
- rr_engine_support_br: 2T +$0.50

**24h Signal Performance (2+ trades):**
- pullback-entry-: 16T 75%WR +$1.71 ⭐⭐ (carrying system)
- mover-: 4T 75%WR +$0.07
- accel-300-v3-short-: 2T 50%WR +$0.05
- pump-chain-: 6T 66.7%WR -$0.24 (R:R drag)
- pullback-entry+: 5T 0%WR -$0.61 (already killed)

**Changes:** None — no kill criteria met, no parameter drift.

**No Change Needed:**
- Kill criteria: no signal at 0%WR with 3+ trades last hour
- pullback-entry+ already killed
- atr_sl_hit 46.3% — above 40% but profitable +$1.61 avg, not urgent
- rr_engine_resistance 7T -$0.34 — exit mechanism not signal, losses small
- Trade freq 1.5/hr normal
- 5 open SHORTs all near breakeven
- 3d trend positive: Sep 8 -$2.74, Sep 9 +$2.03, Sep 10 +$1.26

**Open Questions:**
- pump-chain- 6T 66.7%WR -$0.24 — wins small relative to losses, R:R drag persists
- rr_engine_resistance exit reason losing money — consider if resistance detection is too aggressive

## [2026-09-10 13:07 UTC] Hourly Analysis

**Trades:** 4 closed (4W 0L +$0.51)
- STX SHORT pullback-entry- hard_tp +$0.24
- SEI SHORT pullback-entry- hard_tp +$0.24
- LDO SHORT pullback-entry- rr_engine_support_tp +$0.02
- APT SHORT pump-chain- rr_engine_support_tp +$0.01

**24h:** 45T $2.76
- atr_sl_hit: 19T (42.2%) +$1.61 avg $0.085
- rr_engine_support_tp: 9T +$0.28
- rr_engine_resistance: 7T -$0.34
- profit-monster-trail: 6T +$0.23
- hard_tp: 2T +$0.48
- rr_engine_support_br: 2T +$0.50

**Changes:** None — no kill criteria met

**No Change Needed:**
- Kill criteria: no signal at 0%WR with 3+T last hour (4W 0L)
- pullback-entry+ already killed
- atr_sl_hit 42.2% — above 40% but profitable +$0.085 avg
- rr_engine_resistance 7T -$0.34 — small losses, not urgent
- Trade freq ~1.6/hr normal

**Open Questions:**
- None — system performing well

## [2026-09-10 15:00 UTC] Hourly Analysis

**Trades:** 2 closed last hour (1W 1L +$0.04)
- CC SHORT pump-chain- atr_sl_hit +$0.04
- ICP SHORT pump-chain- atr_sl_hit -$0.18

**24h:** 47T 63.8%WR +$1.63 net
- pullback-entry-: 19T 78.9%WR +$2.21 (carrying system)
- pump-chain-: 8T 75%WR -$0.19 (R:R drag — wins small, losses outsized)
- rr_engine_resistance: 7T -$0.34 (exit mechanism, small)
- rr_engine_support_tp: 9T +$0.28
- profit-monster-trail: 6T +$0.23

**Daily trend:** Sep 8 -$2.74, Sep 9 +$2.03, Sep 10 +$1.63 (healthy recovery)

**Changes:** None

**No Change Needed:**
- Kill criteria: no signal at 0%WR with 3+T last hour
- pullback-entry+ already killed (5T 0%WR)
- atr_sl_hit 44.7% — above 40% but avg +$0.070 profitable
- pump-chain- R:R drag persists but 75%WR keeps it viable — monitor
- Trade freq ~1.5/hr normal
- 5 open SHORTs all near breakeven

**Open Questions:**
- pump-chain- on ICP: 2 losses (-$0.18, -$0.16) vs 1 win (+$0.01) — coin-specific issue?
- rr_engine_resistance exit mechanism consistently small negative — structural, not urgent

## [2026-09-10 16:00 UTC] Hourly Analysis

**Trades:** 3 closed last hour (2W 1L +$0.38)
- BLUR SHORT pump-chain- atr_sl_hit +$0.50
- ACE LONG bb-bounce-v2-long+ profit-monster-trail +$0.02
- SYRUP SHORT accel-300-v4-short- atr_sl_hit -$0.14

**24h:** 46T ~63%WR
- pullback-entry-: 18T 77.8%WR +$2.19 (carrying system)
- pump-chain-: 9T 77.8%WR +$0.31 (improved from -$0.19 earlier)
- atr_sl_hit: 21T (45.7%) avg +$0.104 — above 40% but profitable
- rr_engine_resistance: 6T -$0.32 (structural, small)

**Daily trend:** Sep 8 -$2.74, Sep 9 +$2.03, Sep 10 +$2.01 (strong recovery)

**Changes:** None

**No Change Needed:**
- Kill criteria: no signal at 0%WR with 3+T last hour
- pullback-entry+ already killed
- atr_sl_hit 45.7% above 40% but avg +$0.104 profitable — leave alone
- Trade freq 1-4/hr normal
- pump-chain- R:R improved to +$0.31 from earlier -$0.19

**Open Questions:**
- None — system performing well

## [2026-09-10 17:10 UTC] Hourly Analysis

**Trades:** 2 closed (1W 1L +$0.04)
- BCH SHORT pump-chain- atr_sl_hit +$0.18
- GRASS LONG pump-chain+ atr_sl_hit -$0.14

**24h:** 44T 68.2%WR +$3.56
- pullback-entry-: 18T 77.8%WR +$2.19 (carrying system)
- pump-chain-: 8T 87.5%WR +$0.89 (strong)
- rr_engine_resistance: 6T -$0.32 (structural, small)
- atr_sl_hit: 19T 42.2% avg +$0.126 (profitable)

**Daily trend:** Sep 8 -$2.74, Sep 9 +$2.03, Sep 10 +$2.05

**Changes:** None

**No Change Needed:**
- Kill criteria: no signal at 0%WR with 3+T last hour
- atr_sl_hit 42.2% above 40% but avg +$0.126 profitable — leave alone
- Trade freq 2/hr normal
- 5 open positions near breakeven
- 24h WR 68.2% strong recovery

**Open Questions:**
- None — system performing well

## [2026-09-10 18:10 UTC] Hourly Analysis

**Trades:** 3 closed (2W 1L +$0.22)
- INJ SHORT pump-chain- atr_sl_hit +$0.29
- IO SHORT pump-chain- atr_sl_hit +$0.07
- ATOM SHORT pump-chain- atr_sl_hit -$0.14

**24h:** 41T 68.2%WR +$3.56
- atr_sl_hit: 19T (46.3%) avg +$0.152 — above 40% but profitable
- rr_engine_resistance: 6T -$0.32 (structural, small)
- pullback-entry-: 18T 77.8%WR +$2.19 (carrying system)
- pump-chain-: 8T+ strong

**Daily trend:** Sep 8 -$2.74, Sep 9 +$2.03, Sep 10 +$2.07

**Changes:** None

**No Change Needed:**
- Kill criteria: no signal at 0%WR with 3+T last hour
- atr_sl_hit 46.3% above 40% but avg +$0.152 profitable — leave alone
- Trade freq 3/hr normal
- 24h WR 68.2% strong

**Open Questions:**
- None — system performing well

## [2026-09-10 19:10 UTC] Hourly Analysis

**Trades:** 3 closed (1W 2L -$0.04)
- IMX SHORT pullback-entry- rr_engine_resistance +$0.11
- CC SHORT pump-chain- atr_sl_hit $0.00
- ACE LONG pump-chain+ atr_sl_hit -$0.15

**24h:** 42T ~70%WR +$4.08
- pullback-entry-: 18T 77.8%WR +$2.27 (carrying system)
- pump-chain-: 10T 80%WR +$1.26 (strong)
- pump-chain+: 3T 33.3%WR +$0.30 (small sample, profitable)
- atr_sl_hit: 21T (50%) avg +$0.130 (profitable, leave alone)

**Changes:** None

**No Change Needed:**
- Kill criteria: no signal at 0%WR with 3+T last hour
- atr_sl_hit 50% above 40% but avg +$0.130 profitable
- Trade freq 3/hr normal
- 0 open positions
- 24h WR ~70% strong

**Open Questions:**
- None — system performing well

## [2026-09-10 20:10 UTC] Hourly Analysis

**Trades:** 0 closed last hour. Most recent: ICP SHORT atr_sl_hit -$0.13 (18:52 UTC).
**24h:** 44T 68.2%WR +$3.99. 5 open positions. Today: 34T +$2.12.

**Changes:** None

**No Change Needed:**
- Kill criteria: no signal at 0%WR with 3+T last hour
- 24h WR 68.2% strong
- Trade freq normal
- 5 open positions running

**Open Questions:**
- None — system performing well

## [2026-09-10 21:10 UTC] Hourly Analysis

**Trades:** 1 closed (0W 1L -$0.18)
- AIXBT SHORT pump-chain- rr_engine_resistance -$0.18

**24h:** 41T 65.9%WR +$3.72. Today: 36T 61.1%WR +$2.16. 5 open positions.

**Signal breakdown (24h):**
- pullback-entry-: 16T 75%WR +$2.00 (carrying system)
- pump-chain-: 14T 71.4%WR +$1.19 (strong)
- pump-chain+: 3T 33.3%WR +$0.30 (small sample, profitable)
- pullback-entry+: 2T 0%WR -$0.23 (watch — not kill threshold yet)

**Changes:** None

**No Change Needed:**
- Kill criteria: pullback-entry+ at 0%WR but only 2T (needs 3+). Watch next hour.
- atr_sl_hit 56% above 40% but avg +$0.114 profitable
- Trade freq ~1.5/hr normal
- 24h WR 65.9% strong

**Open Questions:**
- pullback-entry+ trending negative — monitor for 3rd loss next hour

## [2026-09-10 22:10 UTC] Hourly Analysis

**Trades:** 0 closed last hour.
**24h:** 41T 65.9%WR +$3.72. Today: 36T 61.1%WR +$2.16. 5 open positions.

**Changes:** None

**No Change Needed:**
- Kill criteria: no signal at 0%WR with 3+T last hour
- 24h WR 65.9% strong
- Trade freq 0/hr (quiet evening)
- 5 open positions running

**Open Questions:**
- None — system performing well

## [2026-09-10 23:10 UTC] Hourly Analysis

**Trades:** 1 closed (1W 0L +$0.03)
- APT LONG pump-chain+ atr_sl_hit +$0.03

**24h:** 38T 63.2%WR +$2.31. 5 open positions.

**Signal breakdown (24h):**
- pump-chain-: 14T 71.4%WR +$1.19 (strong)
- pullback-entry-: 13T 69.2%WR +$0.98 (strong)
- pump-chain+: 4T 50%WR +$0.33 (profitable)
- accel-300-v4-short-: 2T 50%WR +$0.18
- pullback-entry+: 2T 0%WR -$0.23 (watch — not kill threshold)
- Others: 3T 66.7%WR +$0.08

**Changes:** None

**No Change Needed:**
- Kill criteria: pullback-entry+ at 0%WR but only 2T (needs 3+)
- atr_sl_hit 52.6% above 40% but avg +$0.061 profitable
- Trade freq ~1/hr normal
- 24h WR 63.2% strong

**Open Questions:**
- pullback-entry+ trending negative — monitor for 3rd trade next hour

## [2026-09-11 00:10 UTC] Hourly Analysis

**Trades:** 3 closed (2W 1L +$0.03)
- TURBO pullback-entry- SHORT atr_sl_hit +$0.10
- PURR accel-300-v4-short- SHORT atr_sl_hit -$0.17
- BABY pump-chain- SHORT atr_sl_hit +$0.10

**24h:** 42T 57.1%WR +$2.03. 5 open positions.

**Changes:** None

**No Change Needed:**
- Kill criteria: no signal at 0%WR with 3+T last hour
- pullback-entry+ 2T 0%WR -$0.23 (needs 3+ to kill)
- accel-300-v4-short- 3T 33.3%WR +$0.01 borderline — watch next hour
- atr_sl_hit 52.4% above 40% but avg +$0.051 profitable
- Trade freq ~1.5/hr normal
- 24h WR 57.1% acceptable, net +$2.03

**Open Questions:**
- accel-300-v4-short- borderline — may need kill if next trade loses

## [2026-09-11 01:10 UTC] Hourly Analysis

**Trades:** 0 closed
**PnL:** $0.00

**Changes:** None

**No Change Needed:**
- Kill criteria: pullback-entry+ 2T 0%WR (needs 3+T), accel-300-v4-short- 3T 33.3%WR +$0.01 (breakeven)
- atr_sl_hit 52.4% above 40% but avg +$0.051 profitable
- Trade freq ~1.5/hr normal
- 24h net +$2.03
- Quiet period (01:10 UTC)

**Open Questions:**
- None

## [2026-09-11 02:10 UTC] Hourly Analysis

**Trades:** 1 closed (1W 0L +$0.18)
- CHIP pump-chain+ LONG rr_engine_support_br +$0.18

**24h:** 40T 65.0%WR +$2.33 | 5 open positions

**Changes:** None

**No Change Needed:**
- Kill criteria: no signal at 0%WR with 3+T last hour
- pullback-entry+ 2T 0%WR -$0.23 (needs 3+ to trigger kill)
- accel-300-v4-short- 3T 33.3%WR +$0.01 (breakeven)
- atr_sl_hit 52.5% above 40% but avg +$0.037 profitable
- Trade freq ~1/hr normal
- 24h WR 65% solid

**Open Questions:**
- None

## [2026-09-11 04:10 UTC] Hourly Analysis

**Trades:** 4 closed (0W 4L -$0.60)
- pullback-entry- SHORT → rr_engine_resistance -$0.16
- pump-chain- SHORT → rr_engine_resistance -$0.12
- pump-chain+ LONG → atr_sl_hit -$0.13
- pullback-entry- SHORT → rr_engine_resistance -$0.19

**24h:** 44T 59.1%WR +$1.73 | 3 open positions

**Changes:** None

**No Change Needed:**
- Kill criteria: no signal at 0%WR with 3+T last hour
- pullback-entry+ 2T 0%WR -$0.23 (needs 3+ to kill)
- accel-300-v4-short- 3T 33.3%WR +$0.01 (breakeven)
- rr_engine_resistance 10T avg -$0.037 slight negative — not dramatic, watch next hour
- 24h net +$1.73 system profitable

**Open Questions:**
- Market may be shifting bullish — 3/4 last-hour shorts hit resistance exit

## [2026-09-11 05:10 UTC] Hourly Analysis

**Trades:** 2 closed (0W 2L -$0.45)
- BLUR pump-chain+ LONG → atr_sl_hit -$0.29
- NOT pullback-entry- SHORT → rr_engine_resistance -$0.16

**24h:** 44T 59.1%WR +$1.39 | 3 open positions

**Changes:** None

**No Change Needed:**
- Kill criteria: pullback-entry+ 2T 0%WR (needs 3+), accel-300-v4-short- 3T 33.3%WR +$0.01 (not 0%)
- rr_engine_resistance 10T 22.7% of exits, -$0.49 total — last 3h all SHORT losses (price bouncing in 15m NEUTRAL against 4h SHORT_BIAS entries). Working as designed — preventing larger losses on ranging markets
- Directional outcome system should be penalizing SHORT after 3+ rolling losses (0.5x multiplier active)
- 3 consecutive losing hours (-$1.05) within normal variance at 2 trades/hr
- SHORTs still profitable 24h: 34T 61.8%WR +$1.42
- LONGs bleeding: 10T 40%WR -$0.12 — but no signal at kill threshold

**Open Questions:**
- Regime mismatch: 4h SHORT_BIAS vs 15m NEUTRAL creating whipsaw on shorts. If this persists, may need to tighten entry conditions when 15m is NEUTRAL

## FAVORITES Update — 2026-09-11 06:00 UTC
- Regime: NEUTRAL
- DEMOTE ADA (WR=50.0%, PnL=$0.23, 1 consecutive bad days, regime=NEUTRAL)
- DEMOTE AIXBT (WR=50.0%, PnL=$-0.53, 1 consecutive bad days, regime=NEUTRAL)
- DEMOTE COMP (WR=50.0%, PnL=$0.10, 1 consecutive bad days, regime=NEUTRAL)

Final set: ['ACE', 'BLUR', 'CC', 'CFX', 'DOT', 'DYDX', 'ENA', 'FOGO', 'IMX', 'INJ', 'KAS', 'LTC', 'ME', 'POL', 'TURBO', 'WLD', 'ZRO']

## LOSERS Update — 2026-09-11 06:05 UTC
- REMOVE BABY (WR=50.0%, PnL=$-0.01, recovered)
- REMOVE CAKE (WR=50.0%, PnL=$-0.26, recovered)
- ADD NOT (WR=20.0%, PnL=$-0.44, low_wr (20.0%))
- ADD WLFI (WR=40.0%, PnL=$-0.27, low_wr (40.0%))
- ADD SUSHI (WR=40.0%, PnL=$-0.11, low_wr (40.0%))

Final set: ['BIGTIME', 'ETC', 'GMT', 'HBAR', 'IO', 'NOT', 'SAND', 'SUSHI', 'WLFI']

## [2026-09-11 07:10 UTC] Hourly Analysis

**Trades:** 0 closed (quiet period)
**PnL:** $0.00

**Changes:** None

**No Change Needed:**
- Kill criteria: pullback-entry+ 2T 0%WR (needs 3+ to kill), accel-300-v4-short- 3T 33.3%WR +$0.01 (not 0%)
- atr_sl_hit 54.8% of exits (23/42) but avg +$0.015 profitable — no action needed
- pump-chain- 17T 70.6%WR +$1.22 — strong performer
- Trade freq 1.75/hr normal
- 3 open positions

**Open Questions:** None — system healthy

## [2026-09-11 08:10 UTC] Hourly Analysis

**Trades:** 2 closed (1 win, 1 loss)
**PnL:** $0.04 (WR: 50.0%)

| Trade | Signal | Dir | Exit | PnL |
|-------|--------|-----|------|-----|
| USUAL | mover+ | LONG | profit-monster-trail | +$0.04 |
| BANANA | pullback-entry- | SHORT | rr_engine_resistance | -$0.10 |

**24h:** 43T 55.8%WR +$0.71 | 5 open positions

**Changes:** None

**No Change Needed:**
- Kill criteria: pullback-entry+ 2T 0%WR (needs 3+), accel-300-v4-short- 3T 33.3%WR +$0.01
- pump-chain- 17T 70.6%WR +$1.22 — strong performer
- pump-chain+ 6T 33.3%WR -$0.50 — losing but not at kill threshold (not 0% WR)
- rr_engine_resistance 9T 20.9% of exits, -$0.53 — losses from SHORTs in NEUTRAL market, working as designed
- atr_sl_hit 23T 53.5% but avg +$0.015 profitable
- Trade freq ~2/hr normal
- 3 consecutive losing hours at 04-07 UTC within normal variance

**Open Questions:**
- pump-chain+ at -$0.50 (6T 33.3%WR) — monitoring, not at kill threshold yet
- 15m NEUTRAL vs 4h SHORT_BIAS mismatch continuing to cause SHORT resistance losses

## [2026-09-11 09:10 UTC] Hourly Analysis

**Trades:** 3 closed (1 win, 2 losses)
**PnL:** $0.02 (WR: 33.3%)

| Trade | Signal | Dir | Exit | PnL |
|-------|--------|-----|------|-----|
| PONS | mover+ | LONG | atr_sl_hit | +$0.01 |
| ZRO | bb-bounce-v2-long+ | LONG | profit-monster-trail | +$0.12 |
| ETC | pump-chain- | SHORT | rr_engine_resistance | -$0.11 |

**24h:** 45T 53.3%WR +$0.27 | 5 open positions

**Changes:** None

**No Change Needed:**
- Kill criteria: accel-300-v4-short- 2T 0%WR (needs 3+), pullback-entry+ 1T 0%WR (needs 3+)
- rr_engine_resistance 11T 24.4% of exits, -$0.75 — structural SHORT losses in NEUTRAL market (avg -$0.068), working as designed
- atr_sl_hit 23T 51.1% but avg +$0.002 profitable
- pump-chain+ 7T 28.6%WR -$0.61 — worst signal but not at kill threshold (not 0% WR)
- pump-chain- 19T 63.2%WR +$1.00 — strongest performer
- Trade freq 3/hr normal
- Market: 98% NEUTRAL on 5m, only RUNE SHORT_BIAS, MET LONG_BIAS

**Open Questions:** None — system healthy, no actionable fixes

## [2026-09-11 11:10 UTC] Hourly Analysis

**Trades:** 3 closed (0 wins, 3 losses)
**PnL:** $-0.54 (WR: 0.0%)

| Trade | Signal | Dir | Exit | PnL |
|-------|--------|-----|------|-----|
| ME | ema300-dip-long | LONG | atr_sl_hit | -$0.23 |
| LTC | bb-bounce-v2-long+ | LONG | cut-loser-CL-T1 | -$0.22 |
| FOGO | pullback-entry- | SHORT | rr_engine_resistance | -$0.09 |

**24h:** 50T 50.0%WR -$0.04 | 4 open positions

**Changes:** None

**No Change Needed:**
- Kill criteria: accel-300-v4-short- 2T 0%WR (needs 3+), ema300-dip-long 1T 0%WR (needs 3+)
- pump-chain+ 7T 28.6%WR -$0.61 — losing but not at kill threshold (not 0% WR)
- rr_engine_resistance 13T 28.9% of exits, -$0.81 — structural SHORT losses in NEUTRAL market (avg -$0.062), working as designed
- atr_sl_hit 24T 53.3% but avg -$0.013 slightly negative — monitor if this persists
- ema300-dip-long: first trade (-$0.23) — too early to judge, monitor next 24h
- cut-loser-CL-T1: 2T both losses on bb-bounce-v2-long+ — indicates SL tight for this signal
- Trade freq 2.5/hr normal
- Market: 98% NEUTRAL on 5m
- 6h trend: 4/5 hours negative, mild drawdown within normal variance

**Open Questions:**
- ema300-dip-long first trade a loss — watch next 24h before deciding
- cut-loser-CL-T1 on bb-bounce-v2-long+ — could indicate SL needs widening for this signal

## [2026-09-11 12:10 UTC] Hourly Analysis

**Trades:** 4 closed (2 wins, 2 losses)
**PnL:** $+0.16 (WR: 50.0%)

| Trade | Signal | Dir | Exit | PnL |
|-------|--------|-----|------|-----|
| BIGTIME | pullback-entry- | SHORT | atr_sl_hit | +$0.05 |
| ARB | accel-300-v4-short- | SHORT | atr_sl_hit | -$0.13 |
| ATOM | pullback-entry- | SHORT | atr_sl_hit | +$0.13 |
| APT | pump-chain- | SHORT | atr_sl_hit | +$0.11 |

**24h:** 48T 50.0%WR -$0.07 | 1 open position

**Changes:**
1. KILLED `ACCEL_300_V4_SHORT_ENABLED = False` — 3T/24h 0%WR -$0.44. All ATR_SL hits. SHORT momentum signal has no edge in 98% NEUTRAL market. Meets kill threshold (0% WR, 3+ trades).

**No Change Needed:**
- atr_sl_hit: 26T 54.2% of exits, avg -$0.018 — borderline but not critical
- rr_engine_resistance: 13T 27.1% exits, -$0.81 — structural SHORT losses in NEUTRAL, working as designed
- pump-chain-: 19T 63.2%WR +$0.83 — strong performer
- pump-chain+: 7T 28.6%WR -$0.61 — losing but has some wins, not at kill threshold
- Trade freq 2-3/hr normal
- Market: 98% NEUTRAL on 5m

**Open Questions:** None

## [2026-09-11 13:10 UTC] Hourly Analysis

**Trades:** 4 closed (2 wins, 2 losses)
**PnL:** $+0.19 (WR: 50.0%)

| Trade | Signal | Dir | Exit | PnL |
|-------|--------|-----|------|-----|
| BABY | pump-chain+ | LONG | atr_sl_hit | -$0.14 |
| IMX | doji-bottom-long | LONG | profit-monster-trail | +$0.31 |
| ETH | liq-hunt+ | LONG | profit-monster-trail | -$0.01 |
| PONS | mover+ | LONG | atr_sl_hit | +$0.03 |

**24h:** 51T 47.1%WR -$0.94 | 0 open positions

**Changes:** None

**No Change Needed:**
- Kill criteria: accel-300-v4-short- 3T 0%WR (already killed 12:10), ema300-dip-long 1T 0%WR (needs 3+), liq-hunt+ 1T 0%WR (needs 3+)
- pump-chain+ 8T 25%WR -$0.75 — losing but has wins, doesn't meet kill threshold (0% WR required)
- atr_sl_hit 28T 54.9% exits, avg -$0.021 — borderline but not critical
- Trade freq 2-5/hr normal
- Market: 98% NEUTRAL on 5m

**Open Questions:**
- pump-chain+ at 25%WR is poor — monitor, may need manual intervention if it continues losing

## [2026-09-11 16:10 UTC] Hourly Analysis

**Trades:** 4 closed (3 wins, 1 loss)
**PnL:** $+0.30 (WR: 75.0%)

| Trade | Signal | Dir | Exit | PnL |
|-------|--------|-----|------|-----|
| GRASS | pump-chain- | SHORT | rr_engine_resistance | +$0.06 |
| CC | mover- | SHORT | profit-monster-trail | +$0.26 |
| W | open-skies+ | LONG | hard_sl | -$0.21 |
| USUAL | open-skies+ | LONG | atr_sl_hit | +$0.19 |

**24h:** 54T 50%WR -$0.44 | 1 open position

**Changes:** None

**No Change Needed:**
- Kill criteria: accel-300-v4-short- 2T 0%WR (already killed), ema300-dip-long 1T 0%WR (needs 3+), liq-hunt+ 1T 0%WR (needs 3+)
- pump-chain+ 11T 27.3%WR -$0.74 — worst signal but has wins, doesn't meet kill threshold
- bb-bounce-v2-long+ 3T 33.3%WR -$0.21 — has wins
- atr_sl_hit 26T 48% of exits, avg -$0.017 — borderline but not critical
- rr_engine_resistance 15T 28% exits, -$0.93 — structural SHORT losses in NEUTRAL, working as designed
- Trade freq 2-5/hr normal
- Market: 98% NEUTRAL on 5m

**Open Questions:** None

## [2026-09-11 18:10 UTC] Hourly Analysis

**Trades:** 2 closed (2W 0L +$0.11)
**24h:** 53T ~50%WR -$0.44 | 3 open positions

| Trade | Signal | Dir | Exit | PnL |
|-------|--------|-----|------|-----|
| DOT | mover- | SHORT | profit-monster-trail | +$0.09 |
| LDO | mover+ | LONG | profit-monster-trail | +$0.02 |

**Changes:** None

**No Change Needed:**
- Kill criteria: accel-300-v4-short- 3T 0%WR (already killed 12:10), ema300-dip-long 1T 0%WR (needs 3+), liq-hunt+ 1T 0%WR (needs 3+)
- pump-chain+ 10T 30%WR -$0.59 — worst signal but has wins, doesn't meet kill threshold
- pullback-entry- 8T 37.5%WR -$0.42 — poor but has wins
- atr_sl_hit 22T 42.3% of exits avg -$0.030 — borderline but not critical
- 6h trend: 6/7 hours positive — system performing well
- Trade freq 3/hr normal
- Market: 98% NEUTRAL on 5m

**Open Questions:** None

## [2026-09-11 18:30 UTC] Orchestrator — VERIFIED + DISK CLEANUP

**DB:** 24h 51T 45.1% WR -$0.78. 7d: 333T 55.6% WR +$1.26 (VERIFIED POSITIVE).
**Sep 11:** 46T 41.3% WR -$1.21 (bad day).
**R:R 24h:** 0.815 (avg_win $0.121, avg_loss -$0.149). Breakeven WR 55.0%.
**R:R 7d:** 0.771 (avg_win $0.113, avg_loss -$0.147).

**DISK CLEANUP:** /tmp compile caches cleared — freed 9.5G. Disk 84%→76%.

**4 open SHORT:** BTC, INJ, APT, ATOM.
**Market:** SHORT_BIAS. 98% NEUTRAL on 5m.

**Active signals 7d ALL profitable:**
- pullback_entry-: 29T/69.0% WR +$1.93 ★
- open_skies: 19T/63.2% WR +$1.56 ★
- bb_bounce_v2_long: 39T/71.8% WR +$1.20 ★
- pump_chain: 43T/67.4% WR +$0.98
- pump-chain-: 34T/58.8% WR +$0.61

**24h signal perf:**
- Winners: mover- 3T/66.7%WR +$0.35, doji-bottom-long 1T/100%WR +$0.31, pump-chain- 12T/50%WR +$0.24
- Losers: pump-chain+ 10T/30%WR -$0.59 (KILLED 13:15), accel-300-v4-short- 3T/0%WR -$0.44 (KILLED 12:10), pullback-entry- 8T/37.5%WR -$0.42

**auto_1hr 18:10:** No changes needed. 6/7 hours positive trend. Kill criteria not met for any signal.
**signal_reporter 17:18:** Timed out (recurring, non-critical).
**Health monitor 18:24:** Pipeline OK, 55 timers firing. Disk now 76%.

**No param changes. No signal changes.**

**Changes:** Disk cleanup — 9.5G freed from /tmp compile caches.
**Status:** System healthy. 7d positive. R:R improving.

## [2026-09-11 19:10 UTC] Hourly Analysis

**Trades:** 2 closed (2 wins, 0 losses)
**PnL:** +$0.20 (WR: 100%)

**No Change Needed:**
- Kill criteria: accel-300-v4-short- already killed 12:10, pump-chain+ 10T/30%WR has wins (needs 0%WR 3+), pullback-entry- 8T/37.5%WR has wins (needs 0%WR 3+), ema300-dip-long 1T (needs 3+), liq-hunt+ 1T (needs 3+)
- atr_sl_hit 20T/52T = 38.5% of exits — below 40% threshold
- Trade freq 2.6/hr normal
- 6h trend 5/7 hours positive
- Market: 98% NEUTRAL on 5m
- 4 open positions

**Open Questions:** None

## [2026-09-11 20:10 UTC] Hourly Analysis

**Trades:** 3 closed (2 wins, 1 loss)
**PnL:** -$0.02 (WR: 66.7%)

- ENA pump-chain- SHORT profit-monster-trail +$0.13
- INJ pump-chain- SHORT atr_sl_hit -$0.27
- KAS rs-s88/trend_purity+ LONG profit-monster-trail +$0.12

**No Change Needed:**
- Kill criteria: no signal has 0%WR with 3+ trades last hour. Previous kills (accel-300-v4-short- at 12:10, pump-chain+ at 13:15) already done.
- atr_sl_hit 21/54 = 38.9% — below 40% threshold
- Trade freq 3/hr normal
- 54T/24h 50%WR -$1.06. R:R 0.77 (avg_win $0.130, avg_loss -$0.048). 6h trend 5/7 positive.
- Market: 98% NEUTRAL on 5m
- 2 open positions

**Open Questions:** None

## [2026-09-11 21:10 UTC] Hourly Analysis

**Trades:** 2 closed (1W 1L -$0.20)
**24h:** 55T 50.9%WR -$1.08 | 4 open

- ENA pump-chain- SHORT profit-monster-trail +$0.05
- ENA pump-chain- SHORT cut-loser-CL-T1 -$0.25

**24h exit reason breakdown:**
- atr_sl_hit: 21T (38.2%) avg -$0.039
- rr_engine_resistance: 14T avg -$0.061 (worst by volume)
- profit-monster-trail: 12T avg +$0.123 (best)
- cut-loser-CL-T1: 3T avg -$0.193 (worst per-trade loss)

**No Change Needed:**
- Kill criteria: no active signal has 0%WR with 3+ trades last hour. Previous kills (accel-300-v4-short- 12:10, pump-chain+ 13:15) already done.
- atr_sl_hit 21/55 = 38.2% — below 40% threshold
- Trade freq 2/hr normal
- 55T/24h 50.9%WR -$1.08. Market: 98% NEUTRAL
- 6h trend 4/6 POS. Not 3+ consecutive negative hours.
- pump-chain- still worst active signal (15T 60%WR -$0.29) but has wins, not killable
- 4 open positions (ATOM, BTC, KAS, ARB)

**Open Questions:**
- rr_engine_resistance is dominant loss driver (14T, -$0.86 total) — worth investigating filter tightness in future

## [2026-09-11 22:10 UTC] Hourly Analysis

**Trades:** 0 closed last hour
**24h:** 60T 50%WR -$1.16 | 5 open (BTC, BCH, MNT, LTC, BANANA)

**24h Exit Breakdown:**
- atr_sl_hit: 21T 35% avg -$0.052
- profit-monster-trail: 15T avg +$0.117
- rr_engine_resistance: 14T avg -$0.061
- cut-loser-CL-T1: 5T avg -$0.188

**24h Worst Signals:**
- pump-chain+: 9T 22.2%WR -$0.62 (already killed 13:15)
- pullback-entry-: 8T 37.5%WR -$0.42
- bb-bounce-v2-long+: 4T 25%WR -$0.47

**Changes:** None — 0 trades last hour, no kill criteria met.

**No Change Needed:**
- Kill criteria: no signal has 0%WR with 3+ trades last hour (0 trades total)
- atr_sl_hit 21/60 = 35% — below 40% threshold
- 6h trend: 22:00 bucket 66.7% WR -$0.04 (neutral)
- 5 open positions, all recently entered

**Open Questions:** None

## [2026-09-12 00:10 UTC] Hourly Analysis

**Trades:** 1 closed (1W 0L +$0.08)
**PnL:** +$0.08 (100% WR)

**24h:** 59T 50.8%WR -$1.66 | 4 open

**24h Exit Breakdown:**
- atr_sl_hit: 21T 35.6% avg -$0.052
- profit-monster-trail: 14T avg +$0.109
- rr_engine_resistance: 14T avg -$0.059
- cut-loser-CL-T1: 5T avg -$0.188
- rr_engine_support_br: 4T avg -$0.025
- hard_sl: 1T avg -$0.210

**24h Worst Signals:**
- pump-chain+: 9T 22.2%WR -$0.62 (already killed)
- bb-bounce-v2-long+: 4T 25%WR -$0.47
- pullback-entry-: 9T 44.4%WR -$0.34
- accel-300-v4-short-: 3T 0%WR -$0.44 (already killed)

**Changes:** None

**No Change Needed:**
- Kill criteria: no signal has 0%WR with 3+ trades in last hour (1T total)
- atr_sl_hit 21/59 = 35.6% — below 40% threshold
- 6h trend: 4/6 hours positive, no 3+ consecutive negative hours
- Trade freq: 1/hr normal
- 4 open positions (ATOM, BTC, KAS, ARB)
- pump-chain- still negative PnL (-$0.19) but 61% WR — not killable (has wins, not 0%WR)

**Open Questions:**
- rr_engine_resistance (14T, -$0.83) is the biggest loss driver by volume but it's an exit mechanism, not a signal — investigation deferred

## [2026-09-12 01:10 UTC] Hourly Analysis

**Trades:** 2 closed (1W 1L -$0.05)
**PnL:** -$0.05 (50% WR)

**24h:** 58T 31%WR -$1.62 | 4 open

**24h Exit Breakdown:**
- atr_sl_hit: 18T 31% avg -$0.063
- profit-monster-trail: 15T avg +$0.106
- rr_engine_resistance: 14T avg -$0.059
- cut-loser-CL-T1: 6T avg -$0.177
- rr_engine_support_br: 4T avg -$0.025
- hard_sl: 1T avg -$0.210

**Changes:** None

**No Change Needed:**
- Kill criteria: no signal 0%WR with 3+ trades last hour
- atr_sl_hit 31% — well below 40% threshold
- Trade freq 2/hr normal
- Previous kills (accel-300-v4-short- 12:10, pump-chain+ 13:15) already done
- rr-struct- and rs-s54,trend_purity+ both traded last hour with mixed results (1W 1L)
- 6h trend 4/6 positive
- 4 open positions (ATOM, BTC, KAS, ARB)

**Open Questions:** None

## [2026-09-12 02:10 UTC] Hourly Analysis

**Trades:** 3 closed (3W 0L +$0.40)
**PnL:** +$0.40 (100% WR)

**24h:** 61T -$0.00 (50.8% WR) | 4 open (ATOM, BTC, KAS, ARB)

**24h Exit Breakdown:**
- atr_sl_hit: 18T 29.5% avg -$0.063
- profit-monster-trail: 18T avg +$0.111
- rr_engine_resistance: 14T avg -$0.059
- cut-loser-CL-T1: 6T avg -$0.177
- rr_engine_support_br: 4T avg -$0.025
- hard_sl: 1T avg -$0.210

**Changes:** None

**No Change Needed:**
- Kill criteria: no signal 0%WR with 3+ trades last hour (0 trades last hour, 3 this hour all winners)
- atr_sl_hit 29.5% — well below 40% threshold
- Trade freq 3/hr normal
- 6h trend 4/6 positive
- 4 open positions (ATOM, BTC, KAS, ARB)
- Previous kills (accel-300-v4-short-, pump-chain+) already done
- pump-chain- 17T 58.8%WR -$0.29 — has wins, not killable
- bb-bounce-v2-long+ 4T 25%WR -$0.47 — has wins, not killable

**Open Questions:** None

## [2026-09-12 03:10 UTC] Hourly Analysis

**Trades:** 1 closed (1W 0L +$0.21)
**PnL:** +$0.21 (100% WR) — BIGTIME open-skies+ LONG atr_sl_hit (data: positive PnL despite atr_sl_hit exit)

**24h:** 61T -$1.31 (50.8% WR) | 5 open (BTC, MNT, KAS, ACE, IMX)

**24h Exit Breakdown:**
- atr_sl_hit: 19T 31% avg -$0.048
- profit-monster-trail: 18T avg +$0.111
- rr_engine_resistance: 14T avg -$0.059
- cut-loser-CL-T1: 6T avg -$0.177
- rr_engine_support_br: 3T avg -$0.093
- hard_sl: 1T avg -$0.210

**Changes:** None

**No Change Needed:**
- Kill criteria: no signal 0%WR with 3+ trades last hour
- atr_sl_hit 31% — well below 40% threshold
- Trade freq 1/hr — low, no overtrading
- pump-chain+ 8T 12.5%WR -$0.80 has 1 win, not killable
- bb-bounce-v2-long+ 4T 25%WR -$0.47 has 1 win, not killable
- 6h trend positive (ACE, KAS, IMX trending)
- Previous kills (accel-300-v4-short-, pump-chain+) already done

**Open Questions:** None

## [2026-09-12 04:10 UTC] Hourly Analysis

**Trades:** 2 closed (2W 0L +$0.30)
**PnL:** +$0.30 (100% WR) — ACE trend_purity+ atr_sl_hit +$0.01, KAS trend_purity+ rr_engine_support_br +$0.29

**24h:** 59T 50%WR -$1.31 | 5 open positions

**24h Exit Breakdown:**
- atr_sl_hit: 19T 32% avg -$0.041
- profit-monster-trail: 18T avg +$0.111
- rr_engine_resistance: 11T avg -$0.033
- cut-loser-CL-T1: 6T avg -$0.177
- rr_engine_support_br: 4T avg +$0.003
- hard_sl: 1T avg -$0.210

**Changes:** None

**No Change Needed:**
- Kill criteria: no signal 0%WR with 3+ trades last hour (0 trades last hour)
- atr_sl_hit 32% — well below 40% threshold
- Trade freq 2/hr — normal
- 6h trend 7W 2L — strong
- pump-chain+ 7T 14.3%WR -$0.67 (24h) — bad but only 0 trades last hour, doesn't meet kill criteria
- bb-bounce-v2-long+ 4T 25%WR -$0.47 — has wins, not killable
- Previous kills (accel-300-v4-short-, pump-chain+) already done

**Open Questions:** None

## [2026-09-12 05:10 UTC] Hourly Analysis

**Trades:** 2 closed (1W 1L -$0.28)
**PnL:** -$0.28 (50% WR) — IMX rr-struct+ profit-monster-trail +$0.02, INJ trend_purity+ rr_engine_support_br -$0.30

**24h:** 59T -$0.24 (57.6% WR) | 5 open positions

**24h Exit Breakdown:**
- profit-monster-trail: 19T avg +$0.106
- atr_sl_hit: 18T avg -$0.027
- rr_engine_resistance: 10T avg -$0.020
- cut-loser-CL-T1: 6T avg -$0.177
- rr_engine_support_br: 5T avg -$0.058
- hard_sl: 1T avg -$0.210

**Changes:** None

**No Change Needed:**
- Kill criteria: no signal 0%WR with 3+ trades last hour (0 trades last hour)
- atr_sl_hit 30.5% — well below 40% threshold
- Trade freq 2/hr — normal
- 6h trend 9W 2L — strong
- Regime: EXTREME 7W 1L, HIGH 2W 1L — profitable
- 24h WR improved from 50.8% → 57.6%
- 24h PnL improved from -$1.31 → -$0.24
- bb-bounce-v2-long+ 4T 25%WR -$0.47 — has 1 win, not killable
- accel-300-v4-short- 2T 0%WR -$0.27 — only 2 trades, below kill threshold

**Open Questions:** None

## FAVORITES Update — 2026-09-12 06:00 UTC
- Regime: NEUTRAL
- DEMOTE FOGO (WR=50.0%, PnL=$-0.14, 1 consecutive bad days, regime=NEUTRAL)
- DEMOTE ME (WR=40.0%, PnL=$-0.38, 1 consecutive bad days, regime=NEUTRAL)

Final set: ['ACE', 'BLUR', 'CC', 'CFX', 'DOT', 'DYDX', 'ENA', 'IMX', 'INJ', 'KAS', 'LTC', 'POL', 'TURBO', 'WLD', 'ZRO']

## LOSERS Update — 2026-09-12 06:05 UTC
- REMOVE BIGTIME (WR=50.0%, PnL=$-0.10, recovered)
- REMOVE NOT (insufficient data)
- REMOVE GMT (insufficient data)
- REMOVE HBAR (insufficient data)
- ADD ME (WR=40.0%, PnL=$-0.38, wr_collapse (74.1% → 40.0%))
- ADD AVAX (WR=33.3%, PnL=$-0.34, wr_collapse (61.1% → 33.3%))
- ADD NEAR (WR=40.0%, PnL=$-0.19, low_wr (40.0%))
- ADD GRASS (WR=40.0%, PnL=$1.21, low_wr (40.0%))

Final set: ['AVAX', 'ETC', 'GRASS', 'IO', 'ME', 'NEAR', 'SAND', 'SUSHI', 'WLFI']

## [2026-09-12 06:10 UTC] Hourly Analysis

**Trades:** 1 closed (0W 1L -$0.14)
**PnL:** -$0.14 (0% WR) — BIGTIME trend_purity+ LONG atr_sl_hit -$0.14

**24h:** 60T 34W 56.7%WR -$0.38

**24h Exit Breakdown:**
- profit-monster-trail: 19T avg +$0.106
- atr_sl_hit: 19T avg -$0.033 (31.7% of closes)
- rr_engine_resistance: 10T avg -$0.020
- cut-loser-CL-T1: 6T avg -$0.177
- rr_engine_support_br: 5T avg -$0.058
- hard_sl: 1T avg -$0.210

**Changes:** None

**No Change Needed:**
- Kill criteria: no signal 0%WR with 3+ trades last hour
- atr_sl_hit 31.7% — below 40% threshold
- Trade freq 1/hr — normal
- 6h trend 8W 3L — strong
- 5 open positions
- Worst signals: bb-bounce-v2-long+ (4T 25%WR -$0.47) has 1 win, accel-300-v4-short- (2T 0%WR -$0.27) below kill threshold
- 24h WR improved from 56.7% → 56.7% (stable)

**Open Questions:**
- BIGTIME trade showed -366% pnl_pct but only -$0.14 loss on $11.10 — possible data quality issue in pnl_pct calculation

## [2026-09-12 07:08 UTC] Hourly Analysis

**Trades:** 2 closed (2W 0L +$0.29)
**PnL:** +$0.29 (100% WR) — PONS trend_purity+ atr_sl_hit +$0.24, STX rr-struct+ profit-monster-trail +$0.05

**24h:** 60T 35W 25L 58.3%WR -$0.03 (almost breakeven, improved from -$0.38)

**24h Exit Breakdown:**
- profit-monster-trail: 19T avg +$0.106
- atr_sl_hit: 20T avg -$0.020 (33.3% of closes)
- rr_engine_resistance: 9T avg -$0.011
- cut-loser-CL-T1: 6T avg -$0.177 (biggest loss driver -$1.06)
- rr_engine_support_br: 5T avg -$0.058
- hard_sl: 1T avg -$0.210

**Changes:** None

**No Change Needed:**
- Kill criteria: no signal 0%WR with 3+ trades last hour (2T last hour, both wins)
- atr_sl_hit 33.3% — below 40% threshold
- Trade freq 2/hr — normal
- 24h WR improving: 50.8% → 57.6% → 58.3%
- 24h PnL improving: -$1.31 → -$0.38 → -$0.03
- 5 open positions (2 stale: BTC 12.8h, MNT 9h — managed by SL/TP)
- bb-bounce-v2-long+ (4T 25%WR -$0.47) has 1 win, not killable
- accel-300-v4-short- (2T 0%WR -$0.27) below kill threshold of 3
- cut-loser-CL-T1 is exit reason (not signal), all 6 trades losses at -$1.06 total — monitored

**Open Questions:**
- PONS trade showed +626% pnl_pct but only +$0.24 — pnl_pct data quality issue persists

## [2026-09-12 08:08 UTC] Hourly Analysis

**Trades:** 3 closed (1W 2L -$0.04)
- ONDO pullback-entry- SHORT: rr_engine_resistance -$0.08
- LINK pullback-entry- SHORT: rr_engine_resistance -$0.08
- MNT rr-struct- SHORT: profit-monster-trail +$0.12

**24h:** 61T 36W 25L 59%WR -$0.07 (stable)

**24h Exit Breakdown:**
- profit-monster-trail: 20T avg +$0.107
- atr_sl_hit: 20T avg -$0.020 (32.8% of closes)
- rr_engine_resistance: 10T avg -$0.015
- cut-loser-CL-T1: 6T avg -$0.177 (-$1.06 total)
- rr_engine_support_br: 4T avg -$0.045
- hard_sl: 1T avg -$0.210

**Changes:** None

**No Change Needed:**
- Kill criteria: no signal 0%WR with 3+ trades last hour (3T last hour, spread across 3 signals)
- atr_sl_hit 32.8% — below 40% threshold
- Trade freq 3/hr — normal
- 24h WR stable at 59% (improving from 50.8% earlier)
- 24h PnL stable at -$0.07 (improving from -$1.31 earlier)
- 7d PnL: +$1.30 (positive)
- All previous losers already killed (slow_grind, ema300_dip_short, sma20_dip, coiled_spring variants)
- pullback-entry- still #1 signal 7d: 32T +$1.85 (+$0.058/trade) — today's 2 rr_engine_resistance losses are noise
- bb-bounce-v2-long+ (5T/7d -$0.45) has 2 wins, not killable by 0%WR rule

**Open Questions:**
- cut-loser-CL-T1 still #1 loss driver at -$1.06/24h — activation delay recommendation from Sep 12 audit still pending

## [2026-09-12 09:07 UTC] Hourly Analysis

**Trades:** 1 closed (0W 1L -$0.08) — ARB trend_purity+ LONG: rr_engine_resistance
**6h:** 10T 6W 4L +$0.13
**24h:** 58T 34W 24L 58.6%WR +$0.13

**24h Exit Breakdown:**
- profit-monster-trail: 19T 18W +$2.02 (+$0.106 avg)
- atr_sl_hit: 19T 10W -$0.40 (32.8% of closes)
- rr_engine_resistance: 9T 5W -$0.04
- cut-loser-CL-T1: 6T 0W -$1.06 (-$0.177 avg)
- rr_engine_support_br: 4T 1W -$0.18
- hard_sl: 1T 0W -$0.21

**24h Top Signals:**
- mover-: 3T 3W +$0.46 (best avg, starved)
- trend_purity+: 6T 4W +$0.12
- pump-chain-: 14T 10W +$0.05 (volume king)
- pullback-entry-: 6T 3W +$0.01
- bb-bounce-v2-long+: 3T 0W -$0.59 (worst)
- accel-300-v4-short-: 2T 0W -$0.27

**Changes:** None

**No Change Needed:**
- Kill criteria: no signal 0%WR with 3+ trades in LAST HOUR (1T last hour only)
- atr_sl_hit 32.8% — below 40% threshold
- Trade freq 1/hr — normal
- 24h WR 58.6% — stable
- 24h PnL +$0.13 — positive
- 7d PnL: +$1.30 (positive)
- 5 open positions all managed by SL/TP (BTC SHORT oldest at 14.8h)

**Open Questions:**
- cut-loser-CL-T1 still #1 loss driver at -$1.06/24h — activation delay (MIN_HOLD_MINUTES=10) from Sep 12 audit still pending
- pump-chain+ bleeding 5T/24h -$0.27 — below intervention threshold but watch

## [2026-09-12 10:00 UTC] Hourly Analysis

**Trades:** 1 closed in last 30min (ARB trend_purity+ LONG: rr_engine_support_br -$0.11)
**6h:** 9 closed (5W 4L +$0.08)
**24h:** 56T 33W 23L 58.9%WR +$0.36
**7d:** 344T 194W 56.4%WR +$1.10

**24h Exit Breakdown:**
- profit-monster-trail: 19T 18W +$2.02 (+$0.106 avg)
- atr_sl_hit: 18T 10W -$0.14 (32.1% of closes)
- rr_engine_resistance: 8T -$0.07
- cut-loser-CL-T1: 5T 0W -$0.95 (-$0.190 avg)
- rr_engine_support_br: 5T 1W -$0.29
- hard_sl: 1T 0W -$0.21

**24h Top Signals:**
- mover+: 3T 3W +$0.12 avg (starved)
- mover-: 3T 3W +$0.15 avg (starved)
- rr-struct+: 3T 3W +$0.047 avg
- pump-chain-: 13T 9W +$0.002 avg
- trend_purity+: 7T 4W +$0.001 avg
- bb-bounce-v2-long+: 2T 0W -$0.24 avg (below kill threshold)
- accel-300-v4-short-: 2T 0W -$0.135 avg (below kill threshold)

**Changes:** None

**No Change Needed:**
- Kill criteria: no signal 0%WR with 3+ trades in last hour
- atr_sl_hit 32.1% — below 40% threshold
- Trade freq ~2.3/hr — normal
- 24h WR 58.9% — stable/improving
- 24h PnL +$0.36 — positive
- 7d PnL +$1.10 — positive
- Regime healthy: EXTREME +$0.14, HIGH +$0.47 (NORMAL -0.16 on 5T only)
- All previous losers already killed (slow_grind, ema300_dip_short, sma20_dip, coiled_spring variants)
- bb-bounce-v2-long+ and accel-300-v4-short- both 0%WR but only 2T/24h each — below 3T kill threshold

**Open Questions:**
- cut-loser-CL-T1 still #1 loss driver at -$0.95/24h — STALE_LOSER_TIMEOUT_MINUTES was reduced from 10→8 but still bleeding. Pending: review whether cut-loser should also check regime before cutting
- mover+ and mover- are best signals by avg PnL but starved at 3T/24h each — expansion opportunity

## [2026-09-12 11:00 UTC] Hourly Analysis

**Trades:** 0 closed in last hour
**24h:** 53T 33W 62.3%WR +$0.92

**24h Exit Breakdown:**
- profit-monster-trail: 19T +$2.02 (+$0.106 avg) — star performer
- atr_sl_hit: 17T +$0.11 (32.1% of closes) — healthy
- rr_engine_resistance: 7T +$0.02
- cut-loser-CL-T1: 4T -$0.73 (-$0.183 avg) — improving (was -$0.19)
- rr_engine_support_br: 5T -$0.29
- hard_sl: 1T -$0.21

**24h Top Signals:**
- mover-: 3T 3W +$0.46 (+$0.153 avg)
- mover+: 3T 3W +$0.36 (+$0.120 avg)
- rr-struct+: 3T 3W +$0.14
- pump-chain-: 13T 9W +$0.02 (stable)

**Changes:** None

**No Change Needed:**
- Kill criteria: no signal at 0%WR with 3+ trades (0 trades this hour)
- atr_sl_hit 32.1% — below 40% threshold
- Trade freq normal (quiet hour)
- 24h WR 62.3% — healthy
- 24h PnL +$0.92 — positive and improving
- 5 open positions all managed by SL/TP

**Open Positions:**
- BTC SHORT (pump-chain-): 16.6h old, $11.10, SL at 77349
- STX LONG (trend_purity+): 4.2h old, $11.10
- WLD LONG (rr-struct+): 2.7h old, $11.10
- NOT SHORT (pullback-entry-): 2.7h old, $11.10
- BIGTIME LONG (trend_purity+): 1.4h old, $11.10

**Open Questions:**
- BTC SHORT open 16.6h — longest position, near break-even. SL at 77349 (tight)
- cut-loser-CL-T1 still #1 loss driver but improving (4T vs 5T earlier)

## [2026-09-12 12:00 UTC] Hourly Analysis

**Trades:** 1 closed (BIGTIME LONG, atr_sl_hit, +$0.15)
**24h:** 50T 31W 62.0%WR +$0.91

**24h Exit Breakdown:**
- profit-monster-trail: 19T +$2.02 (+$0.106 avg) — star performer
- atr_sl_hit: 14T +$0.10 (28% of closes) — healthy
- rr_engine_resistance: 7T +$0.02
- rr_engine_support_br: 5T -$0.29 (-$0.058 avg)
- cut-loser-CL-T1: 4T -$0.73 (-$0.183 avg)
- hard_sl: 1T -$0.21

**24h Top Signals:**
- mover-: 3T 3W +$0.46 (+$0.153 avg)
- mover+: 3T 3W +$0.36 (+$0.120 avg)
- rr-struct+: 3T 3W +$0.14
- pump-chain-: 12T 8W -$0.09 (67%WR, slightly negative)

**Changes:** None

**No Change Needed:**
- Kill criteria: no signal at 0%WR with 3+ trades
- atr_sl_hit 28% — well below 40% threshold
- Trade freq normal (~2/hr)
- 24h WR 62.0% — healthy
- 24h PnL +$0.91 — positive
- pump-chain+ 5T/20%WR — already killed (PUMP_FLOW_PLUS_ENABLED=False), legacy trades clearing

**Open Positions:** 5 managed
- BTC SHORT (pump-chain-): 17.8h old, SL at 77367 (0.29% from entry)
- STX LONG (trend_purity+): 5.3h old
- WLD LONG (rr-struct+): 3.9h old
- NOT SHORT (pullback-entry-): 3.9h old
- ENA SHORT (pullback-entry-): 0.8h old, $19.90 size (larger position)

**Open Questions:**
- BTC SHORT 17.8h — very stale, tight SL. System will handle via cut-loser/SL
- pump-chain- 12T/67%WR but -$0.09 — wins not big enough. Monitor but not kill threshold

## [2026-09-12 13:00 UTC] Hourly Analysis

**Trades:** 0 closed last hour (quiet window)
**24h:** 46T 62%WR +$0.82

**24h Exit Breakdown:**
- profit-monster-trail: 17T +$1.72 (+$0.101 avg) — star
- atr_sl_hit: 12T +$0.21 (24% of closes) — healthy
- rr_engine_resistance: 7T +$0.02
- rr_engine_support_br: 5T -$0.29
- cut-loser-CL-T1: 4T -$0.73 (-$0.183 avg) — worst, but small losses
- hard_sl: 1T -$0.21

**Changes:** None

**No Change Needed:**
- Kill criteria: no signal at 0%WR with 3+ trades
- atr_sl_hit 24% — well below 40%
- Trade freq ~1/hr — normal
- 24h WR 62% — healthy
- pump-chain- 12T/66.7%WR but -$0.09 — wins too small, monitor
- cut-loser-CL-T1 4T but max loss -$0.25 per trade — acceptable noise

**Open Positions:** 5 managed
- BTC SHORT: 18.75h old, near break-even, system will handle
- STX LONG: 6.3h
- WLD LONG: 4.8h
- NOT SHORT: 4.8h
- ENA SHORT: 1.8h, $19.90 size (double usual)

**Open Questions:**
- ENA SHORT $19.90 size — 2x normal. Check if position sizing logic changed or intentional.
- cut-loser-CL-T1: ARB/ENA cut at 6-9min. Previous analysis proposed MIN_HOLD=10 but not applied. Losses small enough to let it run.

## [2026-09-12 14:00 UTC] Hourly Analysis

**Trades:** 2 closed (1 win, 1 loss)
**PnL:** +$0.07 (STX +$0.07 atr_sl_hit, WLD -$0.13 cut-loser)

**24h:** 46T 65.2%WR +$0.91 — system healthy

**24h Exit Breakdown:**
- profit-monster-trail: 17T +$1.72 (+$0.101 avg) — star
- atr_sl_hit: 13T +$0.28 (28% of closes) — healthy
- rr_engine_resistance: 6T +$0.20
- cut-loser-CL-T1: 5T -$0.86 (-$0.172 avg) — worst, but losses small
- rr_engine_support_br: 4T -$0.22
- hard_sl: 1T -$0.21

**Changes:** None

**No Change Needed:**
- Kill criteria: no signal at 0%WR with 3+ trades (pullback-entry- at 33.3%WR borderline but losses tiny)
- atr_sl_hit 28% — well below 40%
- Trade freq ~1-2/hr — normal
- cut-loser-CL-T1: ARB/ENA cut at 7-9min, losses small enough
- 24h WR 65.2% — healthy

**Open Positions:** 5 managed
- BTC SHORT: 19.8h old (stale, system will handle)
- NOT SHORT: 5.8h
- ENA SHORT: 2.8h
- INJ SHORT: 0.6h
- AIXBT SHORT: 0.4h

**Open Questions:** None — system operating normally

## [2026-09-12 15:00 UTC] Hourly Analysis

**Trades:** 2 closed (0 wins, 2 losses)
**PnL:** -$0.36 (MET -$0.16 atr_sl_hit, ENA -$0.20 rr_engine_resistance)

**24h:** 44T 63.6%WR +$0.43

**24h Exit Breakdown:**
- profit-monster-trail: 17T +$1.72 — star
- atr_sl_hit: 11T -$0.10 (25% of closes) — healthy
- rr_engine_resistance: 7T +$0.00 — breakeven
- cut-loser-CL-T1: 5T -$0.86 (-$0.172 avg) — worst, losses small
- rr_engine_support_br: 3T -$0.12
- hard_sl: 1T -$0.21

**Changes:** None

**No Change Needed:**
- Kill criteria: no signal at 0%WR with 3+ trades in last hour
- atr_sl_hit 25% — well below 40%
- Trade freq ~2/hr — normal
- 24h WR 63.6% — healthy
- No negative avg_pnl signal with 3+ trades in last hour

**Open Positions:** 5 managed
- BTC SHORT: 20.8h old (stale, system will handle)
- NOT SHORT: 6.8h
- ENA SHORT: 3.8h
- INJ SHORT: 1.6h
- AIXBT SHORT: 1.4h

**Open Questions:** None — system operating normally

## [2026-09-12 16:00 UTC] Hourly Analysis

**Trades:** 1 closed (1 win, 0 losses)
**PnL:** +$0.01 (NEAR LONG rr-struct+ profit-monster-trail)

**24h:** 41T 63.4%WR +$0.14

**24h Exit Breakdown:**
- profit-monster-trail: 17T +$1.47 — star
- atr_sl_hit: 10T -$0.29 (24% of closes) — healthy
- rr_engine_resistance: 6T -$0.06 — breakeven
- cut-loser-CL-T1: 5T -$0.86 (-$0.172 avg) — worst, losses small
- rr_engine_support_br: 3T -$0.12

**Changes:** None

**No Change Needed:**
- Kill criteria: no signal at 0%WR with 3+ trades in last hour
- atr_sl_hit 24% — well below 40%
- Trade freq ~1/hr — normal
- 24h WR 63.4% — healthy
- No negative avg_pnl signal with 3+ trades in last hour

**Watch List:**
- pullback-entry- 25%WR 4T -$0.28 — worst signal 24h but no trades last hour, borderline
- trend_purity+ 50%WR 8T -$0.15 — underperforming but not at kill threshold

**Open Questions:** None — system operating normally

## [2026-09-12 17:00 UTC] Hourly Analysis

**Trades:** 1 closed (0 wins, 1 loss)
**PnL:** -$0.25 (INJ SHORT rr-struct- atr_sl_hit)

**24h:** 40T 62.5%WR -$0.10

**24h Exit Breakdown:**
- profit-monster-trail: 17T +$1.47 — star
- atr_sl_hit: 10T -$0.40 (24% of closes) — healthy
- cut-loser-CL-T1: 5T -$0.86
- rr_engine_resistance: 5T -$0.19
- rr_engine_support_br: 3T -$0.12

**Key Finding — Stale vs Fresh gap:**
- Fresh: 24T 71%WR +$0.60
- Stale: 15T 47%WR -$0.72
- Stale trades (38.5% of volume) account for nearly all losses
- 5/8 SHORT losers were stale

**Changes:** None

**No Change Needed:**
- Kill criteria: no signal at 0%WR with 3+ trades in last hour
- atr_sl_hit 24% — well below 40%
- Trade freq ~1.7/hr — normal
- No negative avg_pnl signal with 3+ trades in last hour

**Watch List:**
- pullback-entry-: 4T 25%WR -$0.28 — worst signal 24h, not at kill threshold (needs 0%WR)
- Stale+oversold SHORT block still top opportunity (~$0.30-0.50/24h savings)

**Open Questions:** None — system operating normally

## [2026-09-12 23:00 UTC] Hourly Analysis

**Trades:** 1 closed (1 win, 0 loss)
**PnL:** +$0.28 (XPL SHORT pullback-entry- atr_sl_hit — profitable despite SL name, small position)

**24h:** 35T 62.9%WR +$0.24 — system positive

**24h Exit Breakdown:**
- profit-monster-trail: 13T +$1.05 — star
- atr_sl_hit: 10T +$0.15 (28.5% of closes) — healthy
- rr_engine_resistance: 5T -$0.23
- cut-loser-CL-T1: 4T -$0.61 (worst avg loss -$0.153/T)
- rr_engine_support_br: 3T -$0.12

**24h Regime:**
- NORMAL: 4T 100%WR +$0.43 — dramatically improved post-fixes
- EXTREME: 19T 63.2%WR +$0.33
- HIGH: 12T 50%WR -$0.52 — new weak spot, watching

**24h Worst Signals (3+ trades):**
- trend_purity+ LONG: 8T 50%WR -$0.15 — underperforming but not at kill threshold
- rr-struct- SHORT: 4T 50%WR -$0.20

**Changes:** None

**No Change Needed:**
- Kill criteria: no signal at 0%WR with 3+ trades
- atr_sl_hit 28.5% — well below 40%
- Trade freq 1.5/hr — normal
- No negative avg_pnl signal with 3+ trades last hour

**Watch List:**
- HIGH regime: 12T 50%WR -$0.52 — monitoring
- trend_purity+ LONG: 8T 50%WR -$0.15 — worst volume signal, not killable
- cut-loser-CL-T1: worst avg exit, -$0.153/trade

**Open Questions:** None — system operating normally

## [2026-09-12 23:55 UTC] Hourly Analysis

**Trades:** 0 closed (quiet hour)
**Open positions:** 6 (3 SHORTs profitable, 2 LONGs slightly underwater, 1 BTC SHORT flat)
**PnL:** System at +$0.58/24h (65.5%WR)

**24h Exit Breakdown:**
- profit-monster-trail: 10T +$0.77 — star performer
- atr_sl_hit: 9T +$0.41 (28.5% — healthy)
- rr_engine_resistance: 5T -$0.23
- rr_engine_support_br: 3T -$0.12
- cut-loser-CL-T1: 2T -$0.25

**Changes:** None

**No Change Needed:**
- Kill criteria: no signal at 0%WR with 3+ trades
- atr_sl_hit 28.5% — well below 40%
- Trade freq ~1.2/hr — normal
- NORMAL regime 100%WR +$0.43 — fixed regime working

**Watch List:**
- rr-struct- SHORT: 4T 50%WR -$0.20 — structural but not at kill threshold
- trend_purity+ LONG: 8T 50%WR -$0.15 — watching
- MIN_HOLD_MINUTES=10 implementation still pending (from audit)

**Open Questions:** None — system operating normally

## [2026-09-13 00:00 UTC] Hourly Analysis

**Trades:** 0 closed (quiet hour, weekend)
**Open positions:** 6 (SEI LONG 2.1h, NEO LONG 2.5h, LDO SHORT 4.9h, ETC SHORT 5.7h, NOT SHORT 14.8h, BTC SHORT 28.8h)
**PnL:** 24h +$0.58 (65.5%WR), 48h -$0.87 (55.1%WR)

**24h Exit Breakdown:**
- profit-monster-trail: 10T +$0.77 — star
- atr_sl_hit: 9T +$0.41 (31% — healthy)
- rr_engine_resistance: 5T -$0.23
- rr_engine_support_br: 3T -$0.12
- cut-loser-CL-T1: 2T -$0.25

**Changes:** None

**No Change Needed:**
- Kill criteria: no signal at 0%WR with 3+ trades
- atr_sl_hit 31% — well below 40%
- Trade freq ~1-2/hr — normal
- Last 2 active hours both 100%WR
- No consecutive negative hourly avg_pnl

**Watch List:**
- trend_purity+ LONG: 8T 50%WR -$0.15 — persistent underperformer, not killable
- rr-struct- SHORT: 4T 50%WR -$0.20
- NOT SHORT: 14.8h open, may need stale check
- MIN_HOLD_MINUTES=10 still pending from earlier audit

**Open Questions:** None — system healthy, quiet weekend hours

## [2026-09-13 01:15 UTC] Hourly Analysis

**Trades:** 2 closed (1 win, 1 loss)
**PnL:** -$0.20 (INJ LONG -$0.23 atr_sl_hit, NOT SHORT +$0.03 atr_sl_hit)

**24h Exit Breakdown:**
- atr_sl_hit: 11T +$0.21 (39.3% — just under 40% threshold)
- profit-monster-trail: 9T +$0.70 — star performer
- rr_engine_resistance: 4T -$0.31
- rr_engine_support_br: 3T -$0.12
- cut-loser-CL-T1: 1T -$0.13

**24h Signal Performance:**
- trend_purity+ LONG: 9T 44%WR -$0.38 — persistent underperformer
- rr-struct- SHORT: 3T 67%WR -$0.08
- pullback-entry- SHORT: 6T 50%WR $0.00

**Changes:** None

**No Change Needed:**
- Kill criteria: no signal at 0%WR with 3+ trades
- atr_sl_hit 39.3% — just under 40%
- Trade freq ~1.2/hr — normal
- No consecutive negative hourly avg_pnl

**Watch List:**
- trend_purity+ LONG: 9T 44%WR -$0.38 — persistent underperformer, not at kill threshold
- BTC SHORT: 30.8h open, -12.25% — stale and underwater
- MIN_HOLD_MINUTES=10 still pending from audit

**Open Questions:** None — system healthy

## [2026-09-13 02:15 UTC] Hourly Analysis

**Trades:** 1 closed (1 win, 0 losses)
**PnL:** +$0.06 (LDO SHORT rr_engine_resistance)
**24h:** 26T ~58%WR +$0.61

**24h Exit Breakdown:**
- atr_sl_hit: 11T +$0.16 (39.3% — just under 40%)
- profit-monster-trail: 6T +$0.30
- rr_engine_resistance: 5T -$0.25
- rr_engine_support_br: 3T -$0.12
- cut-loser-CL-T1: 1T -$0.13

**24h Signal Performance:**
- trend_purity+ LONG: 8T 38%WR -$0.45 (persistent, not killable)
- rr-struct- SHORT: 4T 75%WR -$0.02
- rr-struct+ LONG: 5T 80%WR $0.00
- pullback-entry- SHORT: 6T 50%WR $0.00

**24h Regime:**
- EXTREME LONG: 9T 56%WR +$0.19
- HIGH SHORT: 5T 20%WR -$0.49 (small sample)
- NORMAL SHORT: 5T 100%WR +$0.47

**Changes:** None

**No Change Needed:**
- Kill criteria: no signal at 0%WR with 3+ trades
- atr_sl_hit 39.3% — just under 40%
- Trade freq ~1/hr — normal weekend hours
- 7d HIGH SHORT actually profitable (49T 61%WR +$1.04)

**Watch List:**
- trend_purity+ LONG: 8T 38%WR -$0.45 — persistent, monitor
- BTC SHORT: 31.9h open — stale, no SL hit
- MIN_HOLD_MINUTES=10 still pending from earlier audit

**Open Questions:** None — system healthy

## [2026-09-13 03:15 UTC] Hourly Analysis

**Trades:** 0 closed (quiet weekend)
**PnL:** $0.00
**24h:** 25T 60%WR -$0.25

**24h Exit Breakdown:**
- atr_sl_hit: 10T -$0.05 (40.0% — exactly at threshold)
- profit-monster-trail: 6T +$0.30
- rr_engine_resistance: 5T -$0.25
- rr_engine_support_br: 3T -$0.12
- cut-loser-CL-T1: 1T -$0.13

**24h Signal Performance:**
- trend_purity+ LONG: 8T 37.5%WR -$0.45 (persistent, not killable)
- rr-struct+ LONG: 5T 80%WR $0.00
- rr-struct- SHORT: 4T 75%WR -$0.02
- pullback-entry- SHORT: 6T 50%WR $0.00

**Open Trades (6):**
- BTC SHORT pump-chain-: 32.8h, -14.58% — stale underwater (flagged before)
- ETC SHORT pullback-entry-: 9.7h, +138.98%
- NEO LONG rr-struct+: 6.5h, +294.93%
- SEI LONG rr-struct+: 6.1h, -9.19%
- ZRO LONG trend_purity+: 2h, -53.33%
- XPL SHORT pullback-entry-: 1.7h, +12.85%

**Changes:** None

**No Change Needed:**
- Kill criteria: no signal at 0%WR with 3+ trades
- atr_sl_hit 40.0% — exactly at threshold, not over
- Trade freq ~1/hr — normal weekend
- No consecutive negative hourly avg_pnl

**Watch List:**
- trend_purity+ LONG: 8T 37.5%WR -$0.45 — persistent underperformer
- BTC SHORT: 32.8h open, -14.58% — stale and underwater

**Open Questions:** None

## [2026-09-13 04:15 UTC] Hourly Analysis

**Trades:** 2 closed (0 wins, 2 losses)
**PnL:** -$0.47 (0% WR)

**Last Hour Trades:**
- MET trend_purity+ LONG → atr_sl_hit → -$0.18
- ZRO trend_purity+ LONG → rr_engine_support_br → -$0.29

**24h Exit Breakdown:**
- atr_sl_hit: 10T -$0.24 (40% — at threshold)
- profit-monster-trail: 6T +$0.30
- rr_engine_resistance: 5T -$0.25
- rr_engine_support_br: 3T -$0.70
- cut-loser-CL-T1: 1T -$0.13

**Changes:**
1. KILLED TREND_PURITY_PLUS_ENABLED = False — 8T/24h 12.5% WR -$1.22, all NEUTRAL regime losses. Brain_auditor's 0.15x EXTREME multiplier didn't help because trades are NEUTRAL, not EXTREME. Combo signals (rs-s66,rs-s70,trend_purity+ and volume-breakout-long+) unaffected.

**No Change Needed:**
- atr_sl_hit 40% — at threshold, not over
- Trade freq ~1-2/hr — normal weekend
- Other signals stable

**Watch List:**
- BTC SHORT pump-chain-: 33.8h, -6.68% — stale
- rr_engine_support_br: 3T -$0.70 — worst avg PnL exit reason

**Open Questions:** None

## [2026-09-13 03:00 UTC] Hourly Analysis

**Trades:** 1 closed (1W 0L +$0.69)
**24h:** 24T 54.2%WR -$0.05 | 6 open positions

| Trade | Signal | Dir | Exit | PnL |
|-------|--------|-----|------|-----|
| NEO | rr-struct+ | LONG | atr_sl_hit | +$0.69 |

**24h Exit Breakdown:**
- atr_sl_hit: 11T +$0.45 (46%, avg +$0.041)
- profit-monster-trail: 5T +$0.28
- rr_engine_resistance: 5T -$0.25
- rr_engine_support_br: 2T -$0.40
- cut-loser-CL-T1: 1T -$0.13

**24h by Signal:**
- trend_purity+: 7T 14.3%WR -$0.92 (worst — EXTREME penalty active, needs more data)
- pullback-entry-: 6T 50%WR $0.00
- rr-struct+: 5T 80%WR +$0.67 (best)
- rr-struct-: 4T 75%WR -$0.02

**Changes:** None — no kill triggers met

**No Change Needed:**
- Kill check: no signal 0%WR with 3+ trades in last hour
- Trade freq: 1/hr, healthy
- atr_sl_hit at 46% but avg +$0.04 — winners outpace SL losses, not too tight
- trend_purity+ 14.3%WR already has EXTREME penalty from Sep 12, needs 20+ trades to evaluate
- System borderline (-$0.05/24h) but within normal range

**Open Questions:**
- trend_purity+ still bleeding despite EXTREME penalty — monitor next hour
- cut-loser-CL-T1 activation delay fix still pending (brain_auditor Sep 12)

## FAVORITES Update — 2026-09-13 06:00 UTC
- Regime: NEUTRAL
- DEMOTE INJ (WR=55.6%, PnL=$0.27, 1 consecutive bad days, regime=NEUTRAL)
- DEMOTE LTC (WR=57.1%, PnL=$-0.30, 1 consecutive bad days, regime=NEUTRAL)
- PROMOTE NEO (WR=75.0%, AvgPnL=3.62%, Trades=8)
- PROMOTE BIGTIME (WR=62.5%, AvgPnL=0.61%, Trades=8)

Final set: ['ACE', 'BIGTIME', 'BLUR', 'CC', 'CFX', 'DOT', 'DYDX', 'ENA', 'IMX', 'KAS', 'NEO', 'POL', 'TURBO', 'WLD', 'ZRO']

## LOSERS Update — 2026-09-13 06:05 UTC
- REMOVE NEAR (insufficient data)
- REMOVE ETC (WR=50.0%, PnL=$0.14, recovered)
- REMOVE SUSHI (insufficient data)
- REMOVE ME (insufficient data)
- REMOVE WLFI (insufficient data)
- ADD NOT (WR=20.0%, PnL=$-0.54, wr_collapse (40.0% → 20.0%))

Final set: ['AVAX', 'GRASS', 'IO', 'NOT', 'SAND']

## Daily Orchestrator Run — 2026-09-13 ~06:30 UTC

**Status:** System slightly profitable, no changes needed.

**DB Verified:**
- 24h: 23T, 56.5% WR, +$0.10
- 7d: 333T, 56.8% WR, +$0.91 (improved from +$0.53)
- Open: 6 positions
- Market: 100% NEUTRAL

**Key Findings:**
- trend_purity+ LONG worst signal: 6T/17%WR -$0.78. EXTREME penalty 0.3x + HIGH regime blocked (signal_reporter 05:11 UTC). Needs 20+ trades to evaluate.
- rr-struct+ best performer: 7T/86%WR +$0.76
- Legacy still in 7d window: ~-$3.45 drag (ema300_dip_short -$0.91, slow_grind -$0.80, sma20_dip -$0.73, coiled_spring -$0.44, pullback_entry+ -$0.57)
- Exit analysis 48h: atr_sl_hit 13T -$2.59 (dominant), cut-loser-CL-T1 7T -$1.19
- Pipeline healthy, 0 errors, 65 active timers
- Favorites updated: INJ/LTC demoted, NEO/BIGTIME promoted
- Losers updated: NOT added (20%WR, -$0.54)

**No param changes — system slightly profitable, legacy aging out.**

## [2026-09-13 07:10 UTC] Hourly Analysis

**Trades:** 1 closed (ZEN LONG rr-struct+ atr_sl_hit +$0.02)
**24h:** 23T 56%WR -$0.12 | 5 open | All NORMAL regime

**24h Exit Breakdown:**
- atr_sl_hit: 10T +$0.37 (43.5%, avg +$0.037 — profitable)
- profit-monster-trail: 5T +$0.29 (21.7%, avg +$0.058)
- rr_engine_resistance: 5T -$0.25 (21.7%, avg -$0.050)
- rr_engine_support_br: 2T -$0.40 (8.7%, avg -$0.200)
- cut-loser-CL-T1: 1T -$0.13

**24h by Signal:**
- rr-struct+ LONG: 5T 80%WR +$0.64 (best)
- pullback-entry- SHORT: 6T 50%WR $0.00
- rr-struct- SHORT: 4T 75%WR -$0.02
- trend_purity+ LONG: 5T 0%WR -$1.02 (already disabled ✓)

**Changes:** None — no kill triggers met

**No Change Needed:**
- Kill check: no signal 0%WR with 3+ trades in last hour (only 1 trade closed)
- atr_sl_hit 43.5% but profitable (+$0.37) — not a problem
- trend_purity+ LONG already disabled earlier today
- BAD_TRADE_HOURS from brain_auditor already deployed
- Trade freq: ~1/hr, healthy

**Open Questions:**
- System slightly negative (-$0.12/24h) — will brain_auditor's BAD_TRADE_HOURS show effect?
- trend_purity+ LONG 0%WR legacy losses still in 24h window — will age out

## [2026-09-13 09:09 UTC] Hourly Analysis

**Trades:** 2 closed (XPL SHORT +$0.09, SEI LONG -$0.14)
**24h:** 21T 61.9%WR -$0.02 | 3 open | All NORMAL regime

**24h Exit Breakdown:**
- atr_sl_hit: 11T +$0.23 (52.4%, avg +$0.021 — profitable)
- profit-monster-trail: 4T +$0.17 (19%, avg +$0.043)
- rr_engine_resistance: 4T $0.00 (19%)
- rr_engine_support_br: 1T -$0.29
- cut-loser-CL-T1: 1T -$0.13

**24h by Signal (active only):**
- rr-struct+ LONG: 6T 83%WR +$0.50 (top performer)
- pullback-entry- SHORT: 5T 60%WR +$0.25
- rr-struct- SHORT: 3T 33%WR -$0.14
- trend_purity+ LONG: 4T 0%WR -$0.91 (legacy, already disabled ✓)

**Changes:** None — no kill triggers met

**No Change Needed:**
- Kill check: no signal 0%WR with 3+ trades in last hour
- atr_sl_hit 52.4% but profitable (+$0.23) — doing its job
- trend_purity+ -$0.91 is legacy, will age out of 24h window
- Trade freq: ~1-2/hr, healthy
- System essentially break-even (-$0.02/24h)

**Open Questions:**
- trend_purity+ legacy losses aging out — next check should see improvement
- rr-struct- SHORT only 33%WR but only 3 trades — needs more data

## [2026-09-13 10:08 UTC] Hourly Analysis

**Trades:** 22 closed in 24h (14 wins, 8 losses)
**PnL:** $0.04 (63.6% WR) — break-even but stable
**Open:** 3 positions (BABY LONG, POL SHORT, ETC SHORT)

**24h Exit Breakdown:**
- atr_sl_hit: 11T +$0.23 (50%, profitable)
- profit-monster-trail: 5T +$0.23 (23%)
- rr_engine_resistance: 4T $0.00 (18%)
- cut-loser-CL-T1: 1T -$0.13
- rr_engine_support_br: 1T -$0.29

**24h by Signal (active only):**
- rr-struct+: 6T 66.7%WR +$0.50 (top performer)
- pullback-entry-: 5T 80%WR +$0.25
- rr-struct-: 3T 66.7%WR -$0.14
- trend_purity+: 4T 0%WR -$0.91 (already disabled ✓)

**Changes:** None — no kill triggers met

**No Change Needed:**
- Kill check: no signal 0%WR with 3+ trades in last hour
- atr_sl_hit 50% but profitable (+$0.23) — doing its job
- trend_purity+ legacy losses aging out — will improve
- Trade freq: ~1/hr, healthy

**Open Questions:**
- POL SHORT open 6+ hours, ETC SHORT open 17+ hours
- trend_purity+ -$0.91 aging out of 24h window

## [2026-09-13 11:00 UTC] Hourly Analysis

**Trades:** 0 closed in last hour | 22 closed in 24h (14W/8L)
**PnL:** 24h: +$0.04 (63.6% WR) — break-even but stable
**Open:** 5 positions (ETC SHORT 17.7h, POL SHORT 6.9h, BABY LONG 1.5h, NXPC SHORT 0.8h, CAKE SHORT 0.8h)

**24h Exit Breakdown:**
- atr_sl_hit: 11T +$0.23 (50%) — profitable
- profit-monster-trail: 5T +$0.23 (23%)
- rr_engine_resistance: 4T $0.00 (18%)
- cut-loser-CL-T1: 1T -$0.13
- rr_engine_support_br: 1T -$0.29

**24h by Signal (active only):**
- rr-struct+ LONG: 6T 67%WR +$0.50 (top)
- pullback-entry- SHORT: 5T 80%WR +$0.25
- rr-struct- SHORT: 3T 67%WR -$0.14

**Changes:** None — no kill triggers met

**No Change Needed:**
- Kill check: no signal 0%WR with 3+ trades
- atr_sl_hit 50% but profitable — doing its job
- Trade freq: ~1/hr, healthy
- All active signals positive

**Open Questions:**
- ETC SHORT open 17.7h — very old position, may be stuck
- POL SHORT open 6.9h — monitoring

## [2026-09-13 14:00 UTC] Hourly Analysis

**Trades:** 3 closed in last hour (2W/1L, 67% WR, net +$0.41)
- ETC SHORT pullback-entry- atr_sl_hit +$0.19
- NXPC SHORT pullback-entry- atr_sl_hit -$0.13
- CHIP SHORT pullback-entry- atr_sl_hit +$0.35
**24h:** 24T 16W/8L 66.7%WR +$0.58 | 4 open | All NORMAL

**24h Exit Breakdown:**
- atr_sl_hit: 14T +$0.64 (58%) — profitable
- profit-monster-trail: 5T +$0.23
- rr_engine_resistance: 4T $0.00
- rr_engine_support_br: 1T -$0.29

**Changes:** None — system healthy, all signals positive

**No Change Needed:**
- Kill check: no signal 0%WR with 3+ trades in last hour
- atr_sl_hit 58% but avg +$0.046/trade — doing its job
- Trade freq: 3/hr, normal
- All 4 open positions fresh (<4h)

**Open Questions:** None

## [2026-09-13 16:00 UTC] Hourly Analysis

**Trades:** 3 closed (2W/1L, 67% WR, net +$0.01)
- INJ LONG rr-struct+ atr_sl_hit +$0.13
- BABY LONG open-skies+ atr_sl_hit +$0.02
- DYDX SHORT pullback-entry- atr_sl_hit -$0.14

**24h:** 25T 68%WR +$0.75 | 4 open | 2T/hr

**24h Exit Breakdown:**
- atr_sl_hit: 16T +$0.81 (64%) — profitable
- profit-monster-trail: 5T +$0.23
- rr_engine_resistance: 3T +$0.20
- rr_engine_support_br: 1T -$0.29

**24h by Signal:**
- rr-struct+: 7T 85.7%WR +$0.93 (top performer)
- pullback-entry-: 9T 77.8%WR +$0.77
- rr-struct-: 3T 66.7%WR -$0.14
- trend_purity+: 3T 0%WR -$0.75 (disabled, correct)

**Changes:** None — system healthy

**No Change Needed:**
- Kill check: no signal 0%WR with 3+ trades in last hour
- atr_sl_hit 64% but avg +$0.051/trade — profitable, not a problem
- Trade freq: 2/hr, normal
- All active signals positive or correctly disabled

**Open Questions:** None

## [2026-09-13 18:00 UTC] Hourly Analysis

**Trades:** 4 closed (3W/1L, 75% WR, net +$0.14)
- LINK SHORT rr-struct- -$0.12 (rr_engine_resistance)
- APT LONG pump-chain+ +$0.12 (profit-monster-trail)
- FIL LONG pump-chain+ +$0.03 (profit-monster-trail)
- FIL LONG pump-chain+ +$0.11 (profit-monster-trail)

**24h:** 31T 67.7%WR +$1.22 | 4 open | 1.3T/hr

**24h Exit Breakdown:**
- atr_sl_hit: 16T +$0.92 (51.6%) — profitable
- profit-monster-trail: 9T +$0.61 (29%)
- rr_engine_resistance: 5T -$0.02 (16.1%)
- rr_engine_support_br: 1T -$0.29 (3.2%)

**24h by Signal:**
- rr-struct+: 7T 71.4%WR +$0.78 (best)
- pullback-entry-: 10T 70%WR +$0.67
- pump-chain+: 5T 80%WR +$0.39
- trend_purity+: 3T 0%WR -$0.75 (disabled, correct)

**Changes:** None — system healthy

**No Change Needed:**
- Kill check: no signal 0%WR with 3+ trades in last hour
- atr_sl_hit 51.6% but avg +$0.058/trade — profitable, SL working correctly
- Trade freq: 1.3/hr, normal
- All active signals profitable

**Open Questions:** None

## [2026-09-13 17:35 UTC] Hourly Analysis

**Trades:** 3 closed (0W 2L + 1 ORPHAN_PAPER, -$0.37 real)
**24h:** 31T ~64%WR +$0.70 | 6 open | All NEUTRAL

**Last Hour:**
- ZRO pullback-entry- SHORT: -$0.21 (atr_sl_hit)
- ZEN rr-struct- SHORT: -$0.16 (atr_sl_hit)
- BTC continuum_engine LONG: $0.00 (ORPHAN_PAPER)

**24h Exit Breakdown:**
- atr_sl_hit: 18T +$0.55 (58%, avg +$0.031 — trail-adjusted, profitable)
- profit-monster-trail: 7T +$0.51 (23%, avg +$0.073)
- rr_engine_resistance: 4T -$0.07 (13%)
- rr_engine_support_br: 1T -$0.29

**24h by Signal (2+ trades):**
- rr-struct+ LONG: 6T 66.7%WR +$0.73 (best)
- pullback-entry- SHORT: 10T 60%WR +$0.41
- pump-chain+ LONG: 5T 80%WR +$0.39
- rr-struct- SHORT: 3T 33.3%WR -$0.22
- trend_purity+ LONG: 3T 0%WR -$0.75 (worst — all legacy, 0 trades last hour)

**Changes:** None — no kill triggers met

**No Change Needed:**
- Kill check: 0 trades last hour for any single signal — no 3+ trades/hour threshold met
- Trade freq: 3T/hr, 6 open — healthy
- atr_sl_hit 58% of 24h but profitable (+$0.55 total, avg +$0.031) — trail-adjusted working
- trend_purity+ 0%WR/3T/-$0.75 legacy all from hours 01-04 UTC, 0 trades last hour, aging out
- System positive (+$0.70/24h), no urgency

**Open Questions:**
- trend_purity+ at -$0.75/24h but 0 trades last hour — kill trigger requires 3+ in last hour specifically. Aging out naturally.

## [2026-09-13 18:35 UTC] Hourly Analysis

**Trades:** 0 closed last hour | 31T/24h ~67%WR +$0.70 | 6 open

**24h Exit Breakdown:**
- atr_sl_hit: 18T +$0.55 (58%, avg +$0.031 — profitable)
- profit-monster-trail: 7T +$0.51 (23%, avg +$0.073)
- rr_engine_resistance: 4T -$0.07 (13%)
- rr_engine_support_br: 1T -$0.29

**24h by Signal:**
- rr-struct+ LONG: 6T +$0.73 (best, avg +$0.122)
- pullback-entry- SHORT: 10T +$0.41 (most active)
- pump-chain+ LONG: 5T +$0.39
- rr-struct- SHORT: 3T -$0.22
- trend_purity+ LONG: 3T -$0.75 (legacy, 0 trades last hour)

**Changes:** None — quiet hour, no kill triggers

**No Change Needed:**
- Kill check: 0 trades last hour for any signal — no threshold met
- Trade freq: 0T/hr, 6 open — healthy/idle
- atr_sl_hit 58% but profitable — trail working
- All active signals net positive

**Open Questions:** None

## [2026-09-13 20:07 UTC] Hourly Analysis

**Trades:** 2 closed last hour (1W 1L -$0.25) | 33T/24h 57.6%WR +$0.45 | 5 open

**Last Hour:**
- ETC rr-struct+ LONG atr_sl_hit: +$0.01 (breakeven)
- KAS rr-struct+ LONG rr_engine_support_br: -$0.26

**24h Exit Breakdown:**
- atr_sl_hit: 19T +$0.56 (58%, avg +$0.029 — profitable)
- profit-monster-trail: 7T +$0.51 (21%, avg +$0.073 — best)
- rr_engine_resistance: 4T -$0.07 (12%)
- rr_engine_support_br: 2T -$0.55 (6%, avg -$0.275 — worst)

**24h by Signal:**
- rr-struct+ LONG: 8T 62.5%WR +$0.48
- pullback-entry- SHORT: 10T 60%WR +$0.41
- pump-chain+ LONG: 5T 80%WR +$0.39
- rr-struct- SHORT: 3T 33.3%WR -$0.22
- trend_purity+ LONG: 3T 0%WR -$0.75 (legacy, 0 trades last 16h)

**Open Trades:** 5 (ETH rr-struct+ 5h, FOGO pullback- 2.8h, BIGTIME pullback- 2.6h, GMT pump-chain- 2.2h, ONDO ema300-dip 0.4h)

**Changes:** None — no kill triggers, system stable

**No Change Needed:**
- Kill check: 0 signals with 3+ trades and 0% WR in last hour
- trend_purity+ 0%WR but 0 trades last 16h — aging out naturally
- rr_engine_support_br -$0.55 but only 2 trades — too small a sample
- Trade freq: 2T/hr — healthy, no overtrading
- All active signals net positive (rr-struct+, pullback-entry-, pump-chain+)

**Open Questions:** None

BY: auto_1hr

## [2026-09-13 21:00 UTC] Hourly Analysis

**Trades:** 0 closed last hour (quiet) | 30T/24h ~60%WR +$0.18 | 7 open

**24h Exit Breakdown:**
- atr_sl_hit: 18T +$0.28 (60%, avg +$0.016 — profitable)
- profit-monster-trail: 7T +$0.51 (23%, avg +$0.073 — best)
- rr_engine_resistance: 4T -$0.07 (13%)
- rr_engine_support_br: 2T -$0.55 (7%, avg -$0.275 — small sample)

**24h by Signal:**
- rr-struct+: 8T 62.5%WR +$0.48
- pump-chain+: 5T 80%WR +$0.39
- pullback-entry-: 9T 55.6%WR +$0.13
- rr-struct-: 3T 33.3%WR -$0.22
- trend_purity+: 3T 0%WR -$0.75 (legacy, 0 trades recent)

**Open Trades (7):** ETH rr-struct+ 6h (+$0.11), FOGO pullback- 3.8h, BIGTIME pullback- 3.6h, GMT pump-chain- 3.2h, ONDO ema300-dip 1.4h, ACE pullback- 0.8h, ENA pump-chain+ 0.6h

**Changes:** None — no kill triggers, system stable, quiet hour

**No Change Needed:**
- Kill check: 0 signals with 3+ trades and 0% WR last hour
- trend_purity+ 0%WR legacy aging, 0 recent trades — natural attrition
- Trade freq: 0T/hr — below threshold
- All active signals net positive

**Open Questions:** None

BY: auto_1hr

## [2026-09-13 22:00 UTC] Hourly Analysis

**Trades:** 2 closed last hour (1W, 1L) | 34T/24h ~60%WR +$0.57 | 5 open

**Last Hour:**
- ENA pump-chain+ LONG: -$0.22 (atr_sl_hit, -1.56% adverse)
- ETH rr-struct+ LONG: +$0.04 (rr_engine_support_br)

**24h Exit Breakdown:**
- atr_sl_hit: 19T +$0.06 (56%, avg +$0.003 — breakeven)
- profit-monster-trail: 7T +$0.51 (21%, avg +$0.073 — best)
- rr_engine_resistance: 4T -$0.07 (12%)
- rr_engine_support_br: 3T -$0.51 (9%, avg -$0.170 — worst)

**24h by Signal:**
- rr-struct+ LONG: 9T 67%WR +$0.52
- pump-chain+ LONG: 5T 80%WR +$0.39
- pullback-entry- SHORT: 9T 56%WR +$0.13
- rr-struct- SHORT: 3T 33%WR -$0.22
- trend_purity+ LONG: 3T 0%WR -$0.75 (legacy, already disabled)

**Open Trades (5):** FOGO pullback- 4.8h (+$0.24), BIGTIME pullback- 4.6h (+$0.40), GMT pump-chain- 4.2h (+$0.18), ONDO ema300-dip 2.4h (-$0.12), ACE pullback- 1.9h (+$0.13)

**Changes:** None — no kill triggers, system stable

**No Change Needed:**
- Kill check: 0 signals with 3+ trades and 0% WR last hour
- trend_purity+ 0%WR legacy aging, 0 recent trades — natural attrition
- rr-struct- 33%WR but only 3 trades — within normal variance
- Trade freq: 2T/hr — healthy
- All active signals net positive
- MFE/MAE still NULL — known issue, can't assess entry quality

**Open Questions:**
- pnl_pct values are wildly incorrect (showing -781%, +3098% etc) — display bug, pnl_usdt is accurate. Worth investigating pnl_pct calculation.

## [2026-09-13 23:00 UTC] Hourly Analysis

**Trades:** 1 closed (0W, 1L) | 34T/24h ~56%WR +$0.07 | 7 open

**Last Hour:**
- ONDO ema300-dip-long LONG: -$0.15 (atr_sl_hit)

**24h Exit Breakdown:**
- atr_sl_hit: 20T +$0.06 (56%, avg +$0.003 — breakeven)
- profit-monster-trail: 7T +$0.51 (19%, avg +$0.073 — best)
- rr_engine_resistance: 4T -$0.07 (11%)
- rr_engine_support_br: 3T -$0.51 (8%, avg -$0.170 — worst)

**24h by Signal:**
- rr-struct+ LONG: 9T 67%WR +$0.52 (best)
- pump-chain+ LONG: 5T 80%WR +$0.39
- pullback-entry- SHORT: 9T 56%WR +$0.13
- rr-struct- SHORT: 3T 33%WR -$0.22
- trend_purity+ LONG: 3T 0%WR -$0.75 (legacy, already disabled)

**Open Trades (7):** ETH rr-struct+ 6h (+$0.11), FOGO pullback- 3.8h, BIGTIME pullback- 3.6h, GMT pump-chain- 3.2h, ONDO ema300-dip 1.4h, ACE pullback- 0.8h, ENA pump-chain+ 0.6h

**Changes:** None — no kill triggers, system stable, quiet hour

**No Change Needed:**
- Kill check: 0 signals with 3+ trades and 0% WR last hour
- trend_purity+ 0%WR legacy aging, 0 recent trades — natural attrition
- Trade freq: 0T/hr — below threshold
- All active signals net positive

**Open Questions:** None

BY: auto_1hr

## [2026-09-14 02:00 UTC] Hourly Analysis

**Trades:** 39 closed 24h (23W 16L +$1.42, 59% WR) | 0 closed last hour | 4 open
**Open:** LDO SHORT, ENS SHORT, ENA SHORT, BLUR SHORT (all pullback-entry-)

**24h Exit Breakdown:**
- atr_sl_hit: 22T +$1.11 (56%, avg +$0.050 — profitable, trail-adjusted)
- profit-monster-trail: 7T +$0.51 (18%, avg +$0.073)
- rr_engine_resistance: 6T +$0.31 (15%, avg +$0.052)
- rr_engine_support_br: 3T -$0.51 (8%, avg -$0.170 — only bad exit)

**24h by Signal:**
- pullback-entry- SHORT: 12T 67%WR +$1.25 (best)
- rr-struct+ LONG: 9T 67%WR +$0.52
- pump-chain+ LONG: 5T 80%WR +$0.39
- rr-struct- SHORT: 3T 33%WR -$0.22 (marginal)
- trend_purity+ LONG: 2T 0%WR -$0.47 (worst)

**Changes:** None — no kill triggers met

**No Change Needed:**
- Kill check: trend_purity+ 0%WR but only 2T/24h (0 last hour) — doesn't meet 3+/hour
- rr-struct- at 33%WR — has wins, marginal
- Trade freq: 0T last hour, 4 open — healthy
- System +$1.42/24h, no urgency

**Open Questions:**
- trend_purity+ at 0%WR/-$0.47 — aging out naturally, EXTREME penalty already applied Sep 12
- rr_engine_support_br only bad exit reason at -$0.51/7d — worth monitoring
- All 4 opens are SHORT pullback-entry- — concentration risk but signal performing well

## [2026-09-14 03:00 UTC] Hourly Analysis

**Trades:** 6 closed last hour (4W 2L +$0.05, 67% WR) | 24h: 47T 26W 21L +$0.84 (55.3% WR)
**Open:** 1 (CAKE pump-chain+ LONG, just opened)

**Last Hour Breakdown:**
- pump-chain+ LONG SNIPER exits: 4T 3W 1L +$0.05 (75% WR, quick exits 11-33min)
- pullback-entry- SHORT atr_sl_hit: 2T 0W 2L -$0.28 (LDO -$0.15, ONDO -$0.13)

**24h Exit Breakdown:**
- atr_sl_hit: 27T +$0.54 (57% of trades, avg +$0.02 — profitable)
- profit-monster-trail: 7T +$0.51 (15%, avg +$0.073 — best)
- rr_engine_resistance: 5T +$0.25 (11%)
- rr_engine_support_br: 3T -$0.51 (6%, only bad exit reason)
- SNIPER exits: 4T +$0.05 (9%)

**24h by Signal:**
- pullback-entry- SHORT: 17T +$0.68 (best)
- rr-struct+ LONG: 9T +$0.52
- pump-chain+ LONG: 9T +$0.44
- pump-chain- SHORT: 3T +$0.24
- trend_purity+ LONG: 2T -$0.47 (legacy, EXTREME penalty applied)

**Changes:** None — no kill triggers met

**No Change Needed:**
- Kill check: 0 signals with 3+ trades and 0% WR last hour
- trend_purity+ 0%WR but only 2T/24h — below 3+ threshold
- Trade freq: 6T/hr — normal
- System +$0.84/24h, healthy
- pullback-entry- 2 losses last hour: noise — signal still +$0.68/24h best performer
- SNIPER exits for pump-chain+ working as designed (bearish signal → close LONG)

**Open Questions:** None

BY: auto_1hr

## [2026-09-14 05:30 UTC] Hourly Analysis

**Trades:** 0 closed last hour (system idle) | 24h: 54T 26W 28L +$0.08 (48.1% WR)
**Open:** 5 (NEO SHORT, JUP SHORT, BCH LONG, KAS LONG, ACE SHORT)

**24h Exit Breakdown:**
- atr_sl_hit: 27T +$0.64 (50% of trades, avg +$0.024 — profitable)
- SNIPER exits: 13T -$0.36 (24%, losing — mostly L2/L3-BULLISH on SHORTs)
- profit-monster-trail: 7T +$0.51 (13%, best)
- rr_engine_resistance: 5T +$0.25 (9%)
- Other: 2T +$0.04

**Key Findings:**
1. 5 consecutive negative hours (01:00-05:00 UTC) — not alarming yet (system still above BE)
2. SNIPER-L2/L3-BULLISH on SHORTs: 3T 0W -$0.25 — small sample, monitoring
3. NORMAL regime drag: rr-struct+ LONG -$0.49, pullback-entry- SHORT -$0.17
4. Breakeven WR: 47.5%, actual: 48.1% — marginally above

**Changes:** None — no kill triggers met (0 trades last hour = can't evaluate 3+/hour threshold)

**No Change Needed:**
- Kill check: 0 trades last hour, no signal evaluable
- Trade freq: 0T last hour, 5 open — healthy
- System +$0.08/24h, still above breakeven
- 5 neg hours is noise until it persists into a 6th

**Open Questions:**
- SNIPER-L2/L3-BULLISH on SHORTs losing — will escalate if sample grows to 5+T
- NORMAL regime consistently underperforming — may need regime-specific filter

BY: auto_1hr

## FAVORITES Update — 2026-09-14 06:00 UTC
- Regime: NEUTRAL
- DEMOTE ZRO (WR=50.0%, PnL=$-0.32, 1 consecutive bad days, regime=NEUTRAL)
- DEMOTE BIGTIME (WR=57.1%, PnL=$0.59, 1 consecutive bad days, regime=NEUTRAL)
- DEMOTE ENA (WR=44.4%, PnL=$-0.31, 1 consecutive bad days, regime=NEUTRAL)
- PROMOTE CHIP (WR=80.0%, AvgPnL=4.61%, Trades=5)
- PROMOTE BABY (WR=75.0%, AvgPnL=1.70%, Trades=8)
- PROMOTE ETC (WR=66.7%, AvgPnL=2.37%, Trades=9)
- PROMOTE FIL (WR=62.5%, AvgPnL=0.31%, Trades=8)
- PROMOTE AIXBT (WR=58.3%, AvgPnL=0.17%, Trades=12)

Final set: ['ACE', 'AIXBT', 'BABY', 'BLUR', 'CC', 'CFX', 'CHIP', 'DOT', 'DYDX', 'ETC', 'FIL', 'IMX', 'KAS', 'NEO', 'POL', 'TURBO', 'WLD']

## LOSERS Update — 2026-09-14 06:05 UTC
- REMOVE NOT (insufficient data)
- REMOVE IO (insufficient data)
- REMOVE AVAX (insufficient data)
- REMOVE SAND (insufficient data)
- ADD NXPC (WR=40.0%, PnL=$-0.40, wr_collapse (66.7% → 40.0%))
- ADD ENA (WR=44.4%, PnL=$-0.31, low_wr (44.4%))

Final set: ['ENA', 'GRASS', 'NXPC']

## [2026-09-14 07:00 UTC] Hourly Analysis

**Trades:** 0 closed in last hour (6 open)
**24h:** 40T 52.5%WR +$0.37 (avg $0.009/trade)
**Exit:** atr_sl_hit 25T (62.5%) +$0.03, profit-monster-trail 6T +$0.45, rr_engine_resistance 6T +$0.11
**Direction:** SHORT 23T +$0.50, LONG 17T -$0.13

**Changes:** None — no kill triggers met (0 trades last hour = no signal evaluable)

**No Change Needed:**
- Kill check: 0 trades last hour, no signal with 3+ trades at 0% WR
- atr_sl_hit 62.5% in 24h but 7d at 39.2% — borderline, likely NEUTRAL regime chop
- System still net positive (+$0.37/24h), SL trades averaging $0.021 on SHORT
- pullback-entry- 17T/24h 52.9%WR +$0.04 — marginal but positive
- Trade freq: 0T last hour, 6 open — healthy

**Open Questions:**
- 24h atr_sl_hit spike (62.5%) — monitor; if persists >48h at >40%, consider widening ATR multiplier
- SHORT dominant: +$0.50 vs LONG -$0.13 — NEUTRAL regime favoring shorts
- pullback-entry- high volume but low avg PnL — may need signal quality filter

BY: auto_1hr

## [2026-09-14 07:30 UTC] Hourly Analysis

**Trades:** 1 closed (0 wins, 1 loss)
**24h:** 40T 52.5%WR +$0.37 (avg $0.009/trade)
**Exit:** atr_sl_hit 24T (60%) $0.00 avg, profit-monster-trail 6T +$0.45, rr_engine_resistance 7T -$0.11

**Changes:** None

**No Change Needed:**
- Kill check: 1 trade last hour, no signal evaluable at 3+T with 0%WR
- atr_sl_hit 60% of 24h closes — above 40% threshold BUT avg PnL = $0.000 (breakeven, not destructive)
- System net positive (+$0.37/24h), all profit from profit-monster-trail
- rr-struct+ (7T -$0.19) and rr-struct- (2T -$0.28) are structural drag — known from brain_auditor
- Trade freq: 7T in 6h = ~1.2/hr — healthy, not overtrading
- Regime: NEUTRAL (39/40 trades) — consistent with recent pattern

**Open Questions:**
- rr-struct- (SHORT) has 0%WR (2T/24h) — below 3-trade kill threshold but trending badly
- atr_sl_hit at 60% persisting from 01:35 UTC audit — if still 60%+ at next 24h check, widen ATR multiplier

BY: auto_1hr

## [2026-09-14 08:00 UTC] Hourly Analysis

**Trades:** 1 closed (0 wins, 1 loss)
**PnL:** -$0.14 (BCH pump-chain+ LONG → atr_sl_hit, tiny $11 position)
**24h:** 41T ~50%WR +$0.37

**Changes:** None

**No Change Needed:**
- Kill check: rr-struct- at 2T/0%WR — below 3T threshold, monitor next hour
- atr_sl_hit 60.7% (24h) but avg PnL -$0.005 — breakeven, not destructive
- Trade freq 3T/4h — healthy
- NEUTRAL regime 97.6% — chop market, system surviving
- profit-monster-trail 6T +$0.45 carrying system

**Open Questions:**
- rr-struct- at 2T/0%WR — one more loss triggers kill
- 7d atr_sl_hit trending up (66.7% today vs 31% on Sep 12) — structural

BY: auto_1hr

## [2026-09-14 09:00 UTC] Hourly Analysis

**Trades:** 1 closed (0 wins, 1 loss)
**PnL:** -$0.23 (KAS pump-chain+ LONG → atr_sl_hit)
**24h:** 40T 50%WR +$0.37 | Exit: atr_sl_hit 25T 62.5% -$0.22, profit-monster-trail 6T +$0.45, rr_engine_resistance 6T -$0.20

**Changes:** None

**No Change Needed:**
- Kill check: rr-struct- 2T/0%WR — below 3T threshold, monitor next hour
- pullback-entry- SHORT 17T but 13 SL hits — heavy SL concentration but net +$0.37
- atr_sl_hit 62.5% — above 40% threshold but avg PnL -$0.009 (breakeven)
- Trade freq 1T/hr — healthy
- System net positive, no consecutive negative hours

**Open Questions:**
- rr-struct- approaching kill threshold (2T/0%WR) — one more loss triggers action
- pullback-entry- SHORT: 17T/24h, 13 SL hits (76.5%) — structural issue with SL tightness for this signal type

BY: auto_1hr

## [2026-09-14 10:00 UTC] Hourly Analysis

**Trades:** 4 closed (1W 3L -$0.35)
- DOT pullback-entry- SHORT: +$0.01
- ENA pump-chain- SHORT: -$0.13
- HYPER pump-chain- SHORT: -$0.16
- GMT rr-struct-v2+ LONG: -$0.07

**24h:** 43T 50%WR +$0.37 | Exit: atr_sl_hit 29T 67.4% -$0.57, profit-monster-trail 5T +$0.39, rr_engine_resistance 6T -$0.20
**Regime:** NORMAL 16T 31.3%WR -$1.20 (worst), EXTREME 9T 66.7%WR +$0.94 (best)

**Changes:** None

**No Change Needed:**
- Kill check: pump-chain- SHORT 2T/0%WR last hour — below 3T threshold
- rr-struct- SHORT 2T/0%WR 24h — no trades this hour, still below 3T
- ATR SL hit 76.5% today (was 31% Sep 12) — structural, widening SL already failed (CEO reverted Sep 8, R:R collapsed)
- Trade freq 4T/1hr — healthy
- System net positive 24h, avg loss -$0.02/trade (breakeven, not destructive)
- 6 consecutive negative hours (01:00–09:00 UTC) — regime-driven drawdown, not signal failure

**Open Questions:**
- pump-chain- SHORT degrading: 4T/24h 25%WR -$0.11, 2 losses last hour — approaching kill threshold
- NORMAL regime destroying system (31.3% WR) vs EXTREME (66.7%) — entries in chop markets getting stopped out
- ATR SL hit structural: 76.5% today, up from 31% Sep 12 — needs regime-aware entry filtering, not SL widening

## [2026-09-14 11:00 UTC] Hourly Analysis

**Trades:** 3 closed (1W 2L -$0.27)
- FIL pump-chain+ LONG: -$0.16 (atr_sl_hit, 13min hold)
- HYPER pump-chain+ LONG: -$0.12 (atr_sl_hit, 27min hold)
- ACE pump-chain- SHORT: +$0.01 (atr_sl_hit, breakeven)

**24h:** 46T 43.5%WR -$0.87 | Exit: atr_sl_hit 32T 69.6% -$0.84, profit-monster-trail 5T +$0.39, rr_engine_resistance 6T -$0.20

**Regime context:** Last 2 losses were LONG entries into pump chain — entries during downtrend continuation

**Changes:** None

**No Change Needed:**
- Kill check: no signal at 3T/0%WR threshold
- pump-chain+ LONG: 9T/24h 44.4%WR -$0.26 — losses are small avg -$0.029, not destructive
- Trade freq 2T/hr avg — healthy
- ATR SL hit 69.6% — structural issue from Sep 12, already documented

**Open Questions:**
- pump-chain+ LONG appears to enter during continued selling (FIL: 3 losses in a row at different prices) — may need tighter trend filter but not kill-worthy yet
- 24h system negative -$0.87 — within noise, monitor

BY: auto_1hr

## [2026-09-14 12:00 UTC] Hourly Analysis

**Trades:** 3 closed (3W +$0.19)
- CAKE LONG pump-chain+ | atr_sl_hit | +$0.12 | 109min | HIGH
- BIGTIME SHORT pullback-entry- | atr_sl_hit | +$0.07 | 99min | HIGH
- JUP SHORT pump-chain- | atr_sl_hit | $0.00 | 364min | HIGH

**24h:** 48T 43.8%WR -$0.85 (avg -$0.018/trade)
- Exit: atr_sl_hit 34T (71%) -$0.82, profit-monster-trail 5T +$0.39, rr_engine_resistance 6T -$0.20
- Regime: NORMAL 17T 35.3%WR -$1.19 (worst), HIGH 20T 45.0%WR -$0.44, EXTREME 10T 60.0%WR +$0.78 (best)

**Changes:** None

**No Change Needed:**
- Kill check: rr-struct- SHORT 2T/0%WR — below 3T threshold
- pump-chain- SHORT 6T/33.3%WR — losses small avg -$0.017
- Trade freq 3T/hr — healthy
- System slightly negative but within noise (-$0.85/24h)

**Key Pattern:** pump-chain+ LONG in NORMAL regime = losers (KAS -$0.23, BCH -$0.14). In EXTREME/HIGH = mostly wins. Regime-aware entry filter would help but requires signal code change, not constant tweak.

**Open Questions:**
- rr-struct- SHORT approaching kill threshold (2T/0%WR) — monitor next hour
- NORMAL regime 35.3%WR — structural issue, needs regime-aware entry filtering in signal code

BY: auto_1hr

## [2026-09-14 13:09 UTC] Hourly Analysis

**Trades:** 0 closed in last hour (50 in 24h, 44% WR, -$0.75)
- Last close: ACE LONG breaklong+rs-s42 at 12:56 UTC (-$0.18, atr_sl_hit)
- 7 open positions: SOL, SEI, DOT, BANANA, ENA, GOAT, HYPER

**24h breakdown:**
- atr_sl_hit: 36T (72%) — 21 losses (-$3.01), 15 wins (+$2.29). Avg loss hold 104min
- rr_engine_resistance: 6T -$0.20
- profit-monster-trail: 5T +$0.39
- All 49/50 trades in NEUTRAL regime (EXTREME/HIGH quiet)

**7d signal trends (5+ trades):**
- Winners: pullback-entry- SHORT 57T/63.2%WR +$2.63, open_skies LONG 5T/60%WR +$1.24, pump_chain LONG 28T/60.7%WR +$1.00
- Losers: ema300_dip_short 17T/47.1%WR -$0.91, trend_purity+ LONG 11T/36.4%WR -$0.90, bb_bounce_v2_long 14T/42.9%WR -$0.86

**Changes:** None

**No Change Needed:**
- Kill check: No signal at 0%WR with 3+ trades in 24h ✓
- Trade frequency: ~2/hr — healthy
- System -$0.75/24h — within noise, not actionable
- Pipeline running normally (cycle #199505, 3 tokens in hotset)
- ATR SL dominant at 72% but trailing catches profits (15 wins). Structural, not fixable via constants

**Open Questions:**
- pump-chain+ LONG: 10T/24h 50%WR -$0.14 — losses small but 23T/7d 39.1%WR -$0.43 cumulative. Monitor but not kill-worthy
- 7d trend shows pullback-entry- SHORT is best performer; consider increasing its weight if system drifts further negative

BY: auto_1hr

## [2026-09-14 15:50 UTC] Hourly Analysis

**Trades:** 0 closed last hour (41 in 24h, 44% WR, -$0.93)
**Open positions:** 9 (SOL, SEI, DOT, HYPER, BLUR, APT, TURBO, INJ, JUP)

**24h exit breakdown:**
- atr_sl_hit: 34T (83%) — structural dominance, avg -$0.027/trade
- rr_engine_resistance: 4T +$0.02
- rr_engine_support_br: 2T -$0.22

**24h signal performance:**
- Best: pullback-entry- 14T/57.1%WR, pump-chain- 9T/55.6%WR
- Worst: pump-chain+ 6T/16.7%WR -$0.11, rr-struct-v2+ 2T/0%WR -$0.13

**7d signal trends (losers, 5+ trades):**
- trend_purity+ 11T/36.4%WR -$0.90
- ema300_dip_short 17T/47.1%WR -$0.91
- sma20_dip 19T/42.1%WR -$0.73
- pump-chain+ 24T/37.5%WR -$0.56

**Kill check:** No signal at 0%WR with 3+ trades in last hour ✓

**No Change Needed:**
- Trade frequency ~1.7/hr — healthy
- System -$0.93/24h — within noise
- Pipeline active (cycle running)
- atr_sl_hit dominance is structural (trailing catches profits on wins)

**Open Questions:**
- pump-chain+ LONG has 37.5% WR over 7d (24T, -$0.56) — consistently bad but not at kill threshold yet
- trend_purity+ similarly poor (36.4% WR, 7d) — monitor for kill threshold

BY: auto_1hr

## [2026-09-14 17:50 UTC] Hourly Analysis

**Trades:** 2 closed (0 wins, 2 losses)
**PnL:** -$0.16 (WR: 0%)
**Open positions:** 8 (SOL, SEI, DOT, HYPER, BLUR, TURBO, INJ, JUP)

**24h exit breakdown:**
- atr_sl_hit: 34T (85%) — structural, avg -$0.021/trade
- rr_engine_resistance: 4T +$0.005/trade
- rr_engine_support_br: 2T -$0.110/trade

**24h signal performance (bottom):**
- pump-chain+ LONG: 6T/16.7%WR -$0.66
- rr-struct-v2+ LONG: 2T/0%WR -$0.26
- pullback-entry- SHORT: 13T/61.5%WR +$0.52 (best)

**7d signal losers (5+ trades):**
- ema300_dip_short SHORT: 16T/43.8%WR -$0.96
- trend_purity+ LONG: 11T/36.4%WR -$0.90
- sma20_dip LONG: 19T/42.1%WR -$0.73
- pump-chain+ LONG: 24T/37.5%WR -$0.56

**Kill check:** No signal at 0%WR with 3+ trades in last hour ✓

**No Change Needed:**
- Trade frequency ~1.7/hr — healthy
- System -$0.92/24h — within noise
- No kill triggers active
- Pipeline running normally

**Open Questions:**
- pump-chain+ LONG 7d: 24T/37.5%WR -$0.56 — approaching kill threshold (monitor)
- trend_purity+ LONG 7d: 11T/36.4%WR -$0.90 — monitor for kill threshold

BY: auto_1hr

## [2026-09-14 19:05 UTC] Hourly Analysis

**Trades:** 1 closed (0W 1L -$0.20)
- BLUR SHORT pump-chain- atr_sl_hit: -$0.20

**Open positions:** 8 (SOL, SEI, DOT, HYPER, TURBO, INJ, JUP, ACE)

**24h exit breakdown:**
- atr_sl_hit: 35T (85%) — structural, avg -$0.026/trade
- rr_engine_resistance: 4T +$0.005/trade
- rr_engine_support_br: 2T -$0.110/trade

**24h signal performance (bottom):**
- pump-chain+ LONG: 6T/17%WR -$0.66
- rr-struct-v2+ LONG: 2T/0%WR -$0.26
- pullback-entry- SHORT: 13T/62%WR +$0.52 (best)

**24h regime:** EXTREME +$0.15 | HIGH -$0.28 | NORMAL -$0.99

**7d signal losers (5+ trades):**
- trend_purity+ LONG: 11T/36%WR -$0.90
- ema300_dip_short SHORT: 15T/47%WR -$0.76
- sma20_dip LONG: 19T/42%WR -$0.73
- bb_bounce_v2_long LONG: 11T/45%WR -$0.68
- pullback-entry+ LONG: 6T/17%WR -$0.57
- pump-chain+ LONG: 24T/38%WR -$0.56

**Kill check:** No signal at 0%WR with 3+ trades in last hour ✓

**No Change Needed:**
- Trade frequency ~1.3/hr — healthy
- No kill triggers active
- Pipeline running normally
- atr_sl_hit 85% is structural (trailing catches profits on wins)

**Key Finding:** NORMAL LONG is the main bleed: 7d 29T 31%WR -$1.93. No LONG_NORMAL_PENALTY exists yet. SHORT_NORMAL_PENALTY=0.85 deployed. Adding LONG_NORMAL would require backtest.

**Open Questions:**
- pump-chain+ LONG 7d: 24T/38%WR -$0.56 — approaching kill threshold
- trend_purity+ LONG 7d: 11T/36%WR -$0.90 — monitor for kill threshold
- LONG_NORMAL_PENALTY=0.85 suggestion from brain_auditor — needs backtest before deploy

BY: auto_1hr

## [2026-09-14 20:10 UTC] Hourly Analysis

**Trades:** 1 closed (1W 0L +$0.28)
- INJ LONG pump-chain+ atr_sl_hit: +$0.28

**Open positions:** 8

**24h exit breakdown:**
- atr_sl_hit: 35T (85%) avg -$0.019/trade — structural, trailing catches wins
- rr_engine_resistance: 4T avg +$0.005/trade
- rr_engine_support_br: 1T avg +$0.040/trade

**24h signal bottom:**
- pump-chain+ LONG: 7T/29%WR -$0.38
- rr-struct-v2+ LONG: 2T/0%WR -$0.26

**No Change Needed:**
- 1 trade/hr frequency — healthy
- No kill triggers (pump-chain+ 7d 38%WR not at 0% threshold)
- ATR SL 85% is structural, not a bug
- Pipeline running normally

**Monitoring:**
- pump-chain+ LONG 7d 24T/38%WR -$0.56 — approaching kill threshold
- LONG_NORMAL_PENALTY suggestion — needs backtest before deploy

BY: auto_1hr

## [2026-09-14 21:15 UTC] Hourly Analysis

**Trades:** 5 closed (3W 2L +$0.08)
- SEI LONG rr-struct-v2+ atr_sl_hit: +$0.01
- TURBO LONG rr-struct-v2+,rs-s37 atr_sl_hit: +$0.01
- JUP LONG rr-struct-v2+ atr_sl_hit: +$0.09
- HYPER SHORT pump-chain- atr_sl_hit: -$0.14
- DOT SHORT pullback-entry- atr_sl_hit: -$0.06

**Open positions:** 4

**24h exit breakdown:**
- atr_sl_hit: 40T (89%) avg -$0.019 — structural, trailing catches wins
- rr_engine_resistance: 4T avg +$0.005
- rr_engine_support_br: 1T avg +$0.040

**24h regime:** EXTREME +$0.29 | HIGH -$0.25 | NORMAL -$0.72

**7d regime:** EXTREME +$2.52 | HIGH +$0.05 | NORMAL -$2.71

**7d signal bottom (5+ trades):**
- trend_purity+ LONG: 11T/36.4%WR -$0.90
- ema300_dip_short: 14T/42.9%WR -$0.90
- bb_bounce_v2_long: 10T/40%WR -$0.80
- sma20_dip LONG: 19T/42.1%WR -$0.73
- pullback-entry+ LONG: 6T/16.7%WR -$0.57
- ema300-dip-long: 5T/20%WR -$0.55

**Kill check:** No signal at 0%WR with 3+ trades in last hour ✓

**No Change Needed:**
- 5 trades/hr frequency — healthy
- No kill triggers active (pullback-entry+ 16.7%WR on 7d but only 6T, not at kill threshold)
- ATR SL 89% is structural, not a bug
- Pipeline running normally

**Monitoring:**
- NORMAL regime bleeding -$2.71 on 7d — SHORT_NORMAL_PENALTY=0.85 deployed, no LONG_NORMAL_PENALTY exists
- pullback-entry+ LONG 7d: 6T/16.7%WR -$0.57 — approaching kill threshold
- trend_purity+ LONG 7d: 11T/36.4%WR -$0.90 — monitor for kill threshold

BY: auto_1hr

## [2026-09-14 22:10 UTC] Hourly Analysis

**Trades:** 0 closed in last hour (1 open position: HYPER SHORT pullback-entry-)
**24h:** 45T 46.7%WR -$0.25 | 7d: 321T 53.9%WR +$0.35

**24h exit breakdown:**
- atr_sl_hit: 41T (91%) avg -$0.007 — structural, near break-even
- rr_engine_resistance: 4T avg +$0.005

**24h regime:** EXTREME +$0.29 | HIGH -$0.03 | NORMAL -$0.51

**24h worst signals:**
- pump-chain+ 7T 28.6%WR -$0.38 — already KILLED
- pump-chain- 13T 38.5%WR -$0.21 — monitor
- breakout-long+ 1T 0%WR -$0.18 — 1 trade, variance
- ema300-dip-long 1T 0%WR -$0.15 — 1 trade, variance

**Kill check:** No signal at 0%WR with 3+ trades in last hour ✓

**No Change Needed:**
- 0 trades closed this hour — quiet period, normal
- 7d system still positive (+$0.35)
- All previously problematic signals already killed or monitored
- Trade frequency 45/24h = ~2/hr — healthy
- NORMAL regime improved: -$0.51 (was -$0.72 at 21:15)

**Monitoring:**
- pump-chain- 7d: 53T 58.5%WR +$0.27 — positive, keep watching
- rr-struct- SHORT 7d: 7T 42.9%WR -$0.42 — below threshold
- NORMAL LONG 7d: 33T -$1.66 — structural bleeding, no LONG_NORMAL_PENALTY deployed

BY: auto_1hr

## [2026-09-14 23:15 UTC] Hourly Analysis

**Trades:** 0 closed in last hour (6 open positions: 4 SHORT pullback-entry-, 2 SHORT pump-chain-)
**24h:** 44T 47.7%WR -$0.10 | 7d: 319T 53.9%WR +$0.42

**24h exit breakdown:**
- atr_sl_hit: 40T (91%) avg -$0.003 — structural, near break-even
- rr_engine_resistance: 4T avg +$0.005

**7d regime:** EXTREME +$2.72 | HIGH +$0.22 | NORMAL -$2.52

**7d worst signals:**
- ema300_dip_short 13T 38.5%WR -$0.96 — monitor
- trend_purity+ 11T 36.4%WR -$0.90 — monitor
- sma20_dip 19T 42.1%WR -$0.73 — monitor
- bb_bounce_v2_long 9T 44.4%WR -$0.63 — monitor

**Kill check:** No signal at 0%WR with 3+ trades in last hour ✓

**No Change Needed:**
- 0 trades closed — quiet period, normal
- 24h near break-even (-$0.10)
- 7d system positive (+$0.42)
- All previously problematic signals already killed or monitored
- Trade frequency 44/24h = ~2/hr — healthy
- 6 open SHORTs slightly underwater — normal variance

**Monitoring:**
- NORMAL LONG bleeding structural -$2.52/7d — SHORT_NORMAL_PENALTY active, no new action
- ema300_dip_short SHORT 7d: 13T 38.5%WR -$0.96 — approaching kill threshold
- trend_purity+ LONG 7d: 11T 36.4%WR -$0.90 — approaching kill threshold
- rr-struct- SHORT 7d: 7T 42.9%WR -$0.42 — below threshold

BY: auto_1hr

## [2026-09-14 23:15 UTC] Hourly Analysis

**Trades:** 0 closed in last hour (7 open SHORTs)
**24h:** 40T 47.5%WR -$0.92 | **7d:** 316T 53.8%WR +$0.30

**24h exit breakdown:**
- atr_sl_hit: 37T (92.5%) avg -$0.023 — near break-even, structural
- rr_engine_resistance: 3T avg -$0.023

**7d top winners:** pullback-entry- SHORT +$2.57, rr-struct+ LONG +$0.59, mover- SHORT +$0.53
**7d top losers:** ema300_dip_short SHORT -$0.96, trend_purity+ LONG -$0.90, sma20_dip LONG -$0.73

**Changes:** None — quiet period, no kill threshold hit

**Monitoring:**
- ema300_dip_short SHORT 7d: 13T 38.5%WR -$0.96 — approaching kill
- LONG side structurally weak: 5 signals losing

BY: auto_1hr

## [2026-09-15 00:15 UTC] Hourly Analysis

**Trades:** 1 closed in last hour (0W 1L)
- ALT SHORT pullback-entry- atr_sl_hit: -$0.18

**24h:** 39T 41%WR -$1.61 | **7d:** 315T 53%WR +$0.06

**24h exit breakdown:**
- atr_sl_hit: 37T (95%) avg -$0.034 — structural, near break-even
- rr_engine_resistance: 2T avg -$0.18

**7d regime:** EXTREME +$2.62 | HIGH +$0.04 | NORMAL -$2.60

**7d worst signals:**
- ema300_dip_short SHORT 12T 33.3%WR -$0.99 — monitor
- trend_purity+ LONG 11T 36.4%WR -$0.90 — monitor
- sma20_dip LONG 19T 42.1%WR -$0.73 — monitor

**24h worst signals:**
- pullback-entry- SHORT 11T 36.4%WR -$0.87 — bad cluster, 7d still +$2.39 top winner
- pump-chain- SHORT 11T 36.4%WR -$0.39
- pump-chain+ LONG 7T 28.6%WR -$0.38

**Kill check:** No signal at 0%WR with 3+ trades in last hour ✓

**Changes:** None — no kill trigger hit, system in quiet period

**No Change Needed:**
- No signal meets kill criteria (0% WR + 3+ trades last hour)
- ema300_dip_short had 0 trades last hour — can't kill by rule
- pullback-entry- SHORT 24h bad cluster but 7d top winner (61%WR +$2.39) — variance not signal death
- Trade frequency 39/24h = ~1.6/hr — healthy
- 6 open SHORTs slightly profitable — normal

**Monitoring:**
- ema300_dip_short SHORT 7d: 12T 33.3%WR -$0.99 — approaching kill, watch for next trades
- NORMAL regime -$2.60/7d — SHORT_NORMAL_PENALTY active, structural
- pullback-entry- SHORT 24h cluster — if persists into next hour, review

BY: auto_1hr

## [2026-09-15 02:15 UTC] Hourly Analysis

**Trades:** 1 closed in last hour (1W 0L)
- BABY SHORT pump-chain- atr_sl_hit: +$0.13 (SL at 3.19%, profitable despite SL hit)

**24h:** 37T 43.2%WR -$1.19 | **7d:** 312T 53%WR +$0.09

**24h exit breakdown:**
- atr_sl_hit: 35T (94.6%) avg -$0.024 — near breakeven
- rr_engine_resistance: 2T avg -$0.180

**ATR_SL_MIN compliance:** Most recent trades SL >= 1.3%. Pre-fix trades still flushing (57/71 last-2d had tight SLs).

**7d regime:** EXTREME +$1.96 | HIGH +$0.04 | NORMAL -$2.39

**Changes:** None — quiet period, no kill threshold hit

**No Change Needed:**
- 1 trade last hour — system quiet
- ATR_SL_MIN fix working on new trades
- No signal meets kill criteria (0%WR + 3+ trades last hour)
- Trade frequency 37/24h = ~1.5/hr — healthy

**Monitoring:**
- ema300_dip_short SHORT 7d: 11T 36.4%WR -$0.78 — dormant since Sep 8
- trend_purity+ LONG 7d: 11T 36.4%WR -$0.90 — dormant since Sep 13
- NORMAL regime -$2.39/7d — structural, SHORT_NORMAL_PENALTY active

BY: auto_1hr

## [2026-09-15 04:15 UTC] Hourly Analysis

**Trades:** 1 closed last hour (0W 1L)
- USUAL SHORT pullback-entry- atr_sl_hit: -$0.18 (tiny loss)

**24h:** 37T 43.2%WR -$1.19 | **7d:** 309T 52.8%WR -$0.38

**24h exit breakdown:**
- atr_sl_hit: 35T (94.6%) avg -$0.028 — near breakeven, ATR_SL_MIN fix working
- rr_engine_resistance: 2T avg -$0.180

**Open positions:** 6 SHORTs (all pullback-entry- or pump-chain-)
- SUSHI: SL 0.62% above entry (below 1.3% floor — trailing pulled it down on profit)
- FOGO: SL 1.19% (just below floor)
- DOT/STX: SL below entry (in-profit trailing — correct behavior)
- ACE: SL 1.20% (just below floor)
- HYPER: SL 1.42% (compliant)

**Changes:** None — no kill threshold hit, system quiet

**No Change Needed:**
- No signal meets kill criteria (0%WR + 3+ trades last hour)
- Trade frequency 37/24h = ~1.5/hr — healthy
- ATR_SL_MIN fix deployed and working on new trades
- SUSHI tight SL is trailing artifact, not a bug — will widen if price moves further in favor

**Monitoring:**
- ema300_dip_short SHORT 7d: 11T 36.4%WR — dormant since Sep 8
- trend_purity+ LONG 7d: 11T 36.4%WR — dormant since Sep 13
- NORMAL regime 7d: -$2.17 — structural, SHORT_NORMAL_PENALTY active
- pump-chain- SHORT 24h: 12T 41.7%WR -$0.26 — below average but not kill threshold

BY: auto_1hr

## FAVORITES Update — 2026-09-15 06:00 UTC
- Regime: NEUTRAL
- DEMOTE BLUR (WR=50.0%, PnL=$-0.32, 1 consecutive bad days, regime=NEUTRAL)
- DEMOTE AIXBT (WR=44.4%, PnL=$-0.53, 1 consecutive bad days, regime=NEUTRAL)
- DEMOTE FIL (WR=50.0%, PnL=$-0.23, 1 consecutive bad days, regime=NEUTRAL)
- DEMOTE NEO (WR=40.0%, PnL=$0.29, 1 consecutive bad days, regime=NEUTRAL)
- DEMOTE DYDX (WR=50.0%, PnL=$-0.21, 1 consecutive bad days, regime=NEUTRAL)
- DEMOTE WLD (WR=50.0%, PnL=$0.09, 1 consecutive bad days, regime=NEUTRAL)
- DEMOTE KAS (WR=40.0%, PnL=$-0.43, 1 consecutive bad days, regime=NEUTRAL)
- PROMOTE PONS (WR=80.0%, AvgPnL=2.47%, Trades=5)
- PROMOTE BANANA (WR=71.4%, AvgPnL=0.13%, Trades=7)

Final set: ['ACE', 'BABY', 'BANANA', 'CC', 'CFX', 'CHIP', 'DOT', 'ETC', 'IMX', 'POL', 'PONS', 'TURBO']

## LOSERS Update — 2026-09-15 06:05 UTC
- REMOVE NXPC (insufficient data)
- ADD AIXBT (WR=44.4%, PnL=$-0.53, negative_pnl ($-0.53))
- ADD KAS (WR=40.0%, PnL=$-0.43, wr_collapse (66.7% → 40.0%))
- ADD ZRO (WR=40.0%, PnL=$-0.40, wr_collapse (60.0% → 40.0%))
- ADD NEO (WR=40.0%, PnL=$0.29, low_wr (40.0%))

Final set: ['AIXBT', 'ENA', 'GRASS', 'KAS', 'NEO', 'ZRO']

## [2026-09-15 06:15 UTC] Hourly Analysis

**Trades:** 1 closed last hour (1W 0L +$0.10)
- DOT SHORT pullback-entry- atr_sl_hit: +$0.10

**24h:** 38T 44.1%WR -$0.88 | atr_sl_hit 37T avg -$0.018 (near breakeven)

**Changes:** None — no signal meets kill criteria (0%WR + 3+ trades last hour)

**No Change Needed:**
- ATR_SL_MIN fix working: 97.4% of closes are atr_sl_hit, avg PnL near zero
- Trade frequency 6T/6hr = 1/hr — healthy
- 4 SHORT positions open, all near breakeven or in profit
- No signal has 0% WR with 3+ trades in last hour

**Monitoring:**
- LONG structural drag: sma20_dip 12T 25%WR -$1.07, trend_purity+ 11T 36.4%WR -$0.90 (dormant, not actively trading)
- rr_engine_resistance: 1T in 24h — still not validated (need more exits)
- pump-chain+ LONG 7T 28.6%WR -$0.38 — below kill threshold but underperforming

## [2026-09-15 07:10 UTC] Hourly Analysis

**Trades:** 5 closed last 6h (3W 2L +$0.22)
- DOT SHORT pullback-entry- atr_sl_hit: +$0.10
- ACE SHORT pump-chain- atr_sl_hit: +$0.22
- USUAL SHORT pullback-entry- atr_sl_hit: -$0.18
- KAS LONG rr-struct-v2+ atr_sl_hit: -$0.25
- BABY SHORT pump-chain- atr_sl_hit: +$0.13

**24h:** 37T 48.6%WR -$0.66 | ALL atr_sl_hit (100%)
- pump-chain- SHORT: 13T 46%WR -$0.04
- pullback-entry- SHORT: 7T 57%WR -$0.16
- pump-chain+ LONG: 7T 29%WR -$0.38
- rr-struct-v2+ LONG: 7T 57%WR -$0.16

**7d signals (worst):** trend_purity+ 11T 36%WR -$0.90 | ema300_dip_short 10T 30%WR -$0.80 | sma20_dip 9T 33%WR -$0.77 (all dormant)

**7d signals (best):** pullback-entry- 61T 60.7%WR +$2.31 | pump-chain- 55T 60%WR +$0.62 | rr-struct+ 15T 73.3%WR +$0.59

**Changes:** None — no signal meets kill criteria

**No Change Needed:**
- No signal has 0% WR with 3+ trades in last hour (0 trades closed)
- Trade frequency 37T/24h = 1.5/hr — healthy
- 5 SHORT positions open, SLs correctly placed (trailing stops working)
- ATR SL losses small (avg -$0.018/trade)
- 100% atr_sl_hit in 24h is anomaly vs 7d (67 profit-monster-trail exits) — likely NEUTRAL chop

**Monitoring:**
- 100% atr_sl_hit in 24h — no TP or trail exits. If this persists, check if targets are too ambitious
- pump-chain+ LONG 25T 40%WR -$0.28 on 7d — already on LOSERS watchlist
- LONG structural drag dormant (trend_purity+, sma20_dip not actively trading)

BY: auto_1hr

## [2026-09-15 08:10 UTC] Hourly Analysis

**Trades:** 0 closed last hour (2.2h since last close)
**PnL:** $0.00

**24h:** 36T 52.8%WR -$0.52 | ALL atr_sl_hit (100%) avg -$0.014/trade
- pump-chain- SHORT: 13T 46%WR -$0.04
- pullback-entry- SHORT: 7T 57%WR -$0.16
- rr-struct-v2+ LONG: 7T 57%WR -$0.16
- pump-chain+ LONG: 6T 33%WR -$0.24

**Open Positions:** 5 SHORTs (all pullback-entry-)
- HYPER +$0.36 | STX +$0.20 | SUSHI +$0.12 | FOGO +$0.04 | CHIP -$0.05

**Changes:** None — no signal meets kill criteria

**No Change Needed:**
- No signal has 0% WR with 3+ trades in last hour (0 trades)
- Trade frequency 36T/24h = 1.5/hr — healthy
- All 5 open SHORTs in profit or near breakeven
- ATR SL avg loss tiny (-$0.014) — system is breakeven on stops
- 100% atr_sl_hit persists but losses are minimal

**Monitoring:**
- 100% atr_sl_hit in 24h — no TP or trail exits, just tight SLs clipping
- pump-chain+ LONG 6T 33%WR -$0.24 — already on LOSERS watchlist
- Open positions all SHORT, consistent with SHORT edge in recent data

BY: auto_1hr

## [2026-09-15 09:10 UTC] Hourly Analysis

**Trades:** 2 closed (1 win, 1 loss)
**PnL:** +$0.11 (HYPER +$0.26, FOGO -$0.15) — both pullback-entry- SHORT, atr_sl_hit

**24h:** 37T 50%WR -$0.18 | ALL atr_sl_hit (100%) | avg -$0.005/trade
- pullback-entry- SHORT: 9T 56%WR -$0.05
- pump-chain- SHORT: 13T 46%WR -$0.04
- rr-struct-v2+ LONG: 7T 57%WR -$0.16
- pump-chain+ LONG: 5T 40%WR -$0.01

**Open Positions:** 3 SHORTs — CHIP ~BE, SUSHI ~BE, STX ~BE

**Changes:** None — no signal meets kill criteria

**No Change Needed:**
- No signal has 0% WR with 3+ trades in last hour
- Trade frequency 37T/24h = 1.5/hr — healthy
- ATR SL avg loss tiny (-$0.005/trade) — system is breakeven
- 3 open SHORTs all near breakeven

**Monitoring:**
- 100% atr_sl_hit persists in 24h (no TP/trail exits) — flagged by brain_auditor, structural
- Dead signal drag -$3.97/7d — ages out Sep 16-20, no action needed
- rr_engine_resistance exits: 37T avg -$123.99 over 7d — worst exit type
- cut-loser-CL-T1: 21T avg -$503.69 — these are the real losers but low frequency

BY: auto_1hr

## [2026-09-15 10:10 UTC] Hourly Analysis

**Trades:** 1 closed (0 wins, 1 loss) — CHIP SHORT atr_sl_hit -$0.34
**Opened:** 3 new (MET SHORT, W SHORT, ATOM LONG)
**Open positions:** 5

**24h:** 34T 52.9%WR -$0.17 | avg -$0.005/trade | 100% atr_sl_hit
- pump-chain- SHORT: 11T 54.5%WR +$0.25
- pullback-entry- SHORT: 9T 44.4%WR -$0.40
- rr-struct-v2+ LONG: 6T 66.7%WR -$0.09
- pump-chain+ LONG: 5T 40.0%WR -$0.01

**7d:** 291T 52.9%WR +$0.13

**Changes:** None — no signal meets kill criteria

**No Change Needed:**
- No signal has 0% WR with 3+ trades in last hour
- Trade frequency 1.4/hr — healthy
- 100% atr_sl_hit but losses tiny (-$0.005/trade)
- pullback-entry- SHORT underperforming but not at kill threshold

**Monitoring:**
- pullback-entry- SHORT: 9T 44.4%WR -$0.40 — weakest signal
- 100% atr_sl_hit — structural, no TP/trail exits
- SUSHI SHORT open 7h+ — oldest position

BY: auto_1hr

## [2026-09-15 11:10 UTC] Hourly Analysis

**Trades:** 0 closed in last hour. 5 open positions (3 SHORTs, 2 LONGs).
**PnL:** System flat — 30T 24h +$0.10 (+$0.003/trade avg)

**24h by signal:**
- pump-chain- SHORT: 9T +$0.24
- pump-chain+ LONG: 3T +$0.27
- pullback-entry- SHORT: 9T -$0.40 (weakest)
- rr-struct-v2+ LONG: 6T -$0.09

**Changes:** None — no signal meets kill criteria

**No Change Needed:**
- 0 trades closed in hour → no kill candidates
- 100% atr_sl_hit but losses tiny (structural, flagged by brain_auditor)
- pullback-entry- SHORT weakest but not at kill threshold
- Trade frequency 1.25/hr — healthy
- All open positions near breakeven

**Monitoring:**
- 100% atr_sl_hit persists — no TP/trail exits active
- pullback-entry- SHORT dragging -$0.40/24h
- SUSHI SHORT open 7.5h+, oldest position, +$0.10

BY: auto_1hr

## [2026-09-15 15:10 UTC] Hourly Analysis

**Trades:** 2 closed (2 wins, 0 losses). +$0.28.
**PnL:** APT SHORT +$0.07, STX SHORT +$0.21 — both atr_sl_hit winners.

**24h:** 29T -$0.75 total
- rr-struct-v2+ LONG: 9T -$0.38 — KILLED by CEO at 14:40
- pullback-entry- SHORT: 11T -$0.34 (weakest active)
- pump-chain- SHORT: 7T +$0.05
- Exit: 89.7% atr_sl_hit (structural — no TP/trail)

**Changes:** None — no signal meets kill criteria

**No Change Needed:**
- No kill candidates (rr-struct-v2+ LONG already killed at 14:40)
- Trade frequency 1.2/hr — healthy
- ATR SL dominates but losses tiny (-$0.005/trade)
- No signal at 0% WR with 3+ trades in hour

**Monitoring:**
- pullback-entry- SHORT: 11T -$0.34/24h — weakest active signal
- 100% atr_sl_hit persists — no TP/trail exits active
- 4 open positions: W, YGG, DOT, BANANA — all pullback-entry- SHORT

BY: auto_1hr

## [2026-09-15 16:10 UTC] Hourly Analysis

**Trades:** 4 closed (3 wins, 1 loss). +$0.29.
- W SHORT pullback-entry- atr_sl_hit: +$0.12
- BANANA SHORT pullback-entry- atr_sl_hit: +$0.09
- YGG SHORT pullback-entry- atr_sl_hit: +$0.09
- DOT SHORT pullback-entry- atr_sl_hit: -$0.01

**24h:** 31T 51.6%WR +$0.15
- pullback-entry- SHORT: 15T 53.3%WR -$0.05 (neutral)
- pump-chain- SHORT: 6T 33.3%WR -$0.15 (weakest, but 48h: 46.7%WR +$0.14)
- rr-struct-v2+ LONG: 8T 50%WR -$0.19 (pre-kill trades, killed 14:40)
- Exit: 90% atr_sl_hit (structural — no TP/trail)

**Changes:** None — no signal meets kill criteria

**No Change Needed:**
- No kill candidates (no 0% WR signal with 3+ trades in hour)
- Trade frequency 2.5/hr — slightly elevated but not overtrading
- System slightly positive (+$0.29 hour, +$0.15/24h)
- pump-chain- SHORT 33.3%WR looks bad but 48h data shows 46.7%WR +$0.14 — recent dip, not structural
- 0 open positions — all closed flat

**Monitoring:**
- 100% atr_sl_hit persists — no TP/trail exits active
- pump-chain- SHORT 24h WR 33.3% vs 48h 46.7% — watch for degradation
- System barely positive — watching for regime shift to NEUTRAL

BY: auto_1hr

## [2026-09-15 17:10 UTC] Hourly Analysis

**Trades:** 0 closed (5 open: ETH SHORT, SAND SHORT, IMX LONG, LTC SHORT, SUPER SHORT)
**24h:** 31T 51.6%WR -$0.10

**Changes:** None — no signal meets kill criteria

**No Change Needed:**
- No 0%WR signal with 3+ trades in hour
- Trade frequency 1.3/hr — healthy
- System breakeven (-$0.10/24h) — noise level
- pump-chain- SHORT 33%WR/24h but 46.7%WR/48h — recent dip not structural
- 5 open positions just entered, no SL hits yet

**Monitoring:**
- 5 open positions — will evaluate next hour when SL/TP triggers
- pullback-entry- SHORT 53%WR/$-0.05 — flat, watch for degradation
- 100% atr_sl_hit persists — no TP/trail exits active

BY: auto_1hr

## [2026-09-15 18:10 UTC] Hourly Analysis

**Trades:** 1 closed (1 win, 0 losses). $0.00 (breakeven).
- SAND SHORT pullback-entry- atr_sl_hit: $0.00

**24h:** 30T 50%WR +$0.06
- pullback-entry-: 16T 50%WR -$0.05 (flat)
- pump-chain-: 4T 50%WR +$0.01 (flat)
- pump-chain+: 1T 100%WR +$0.28
- rr-struct-v2+ (pre-kill): 8T 50%WR -$0.19
- Exit: 90% atr_sl_hit (structural — no TP/trail)

**Changes:** None — no signal meets kill criteria

**No Change Needed:**
- No kill candidates (no 0% WR signal with 3+ trades in hour)
- Trade frequency 1.3/hr — healthy
- System breakeven (+$0.06/24h) — noise level
- pump-chain- SHORT 46.7%WR/48h +$0.14 — within normal range
- New signal: breakout-long+ (2 open: ZEN, IMX) — first appearance, too early to evaluate

**Monitoring:**
- 5 open positions: ZEN LONG (breakout-long+), ETH SHORT, IMX LONG (breakout-long+), LTC SHORT, SUPER SHORT
- breakout-long+ — new signal, watch first close
- 100% atr_sl_hit persists — no TP/trail exits active
- System flat 3 hours straight — watching for regime shift

BY: auto_1hr

## [2026-09-15 19:10 UTC] Hourly Analysis

**Trades:** 7 closed (5 wins, 2 losses). $0.00 net (breakeven).
- pullback-entry- SHORT: SUPER +$0.20, LTC +$0.09, ETH +$0.13 ✅
- grind-breakout- SHORT: MET +$0.03 (profit-monster-trail!) ✅
- breakout-long+ LONG: IMX -$0.25, ZEN -$0.20 ❌ (SL hit both)
- pullback-entry- SHORT: WLFI $0.00 (exit_reason=None — data bug?)

**24h:** 36T 55.6%WR +$0.72
- pullback-entry-: 22T 54.5%WR +$0.49 (backbone)
- pump-chain-: 3T 100%WR +$0.21
- pump-chain+: 1T +$0.28
- grind-breakout-: 1T +$0.03 (first profit-monster-trail exit!)
- breakout-long+: 2T 0%WR -$0.45 (new signal, 3 total trades)
- Exit: 86% atr_sl_hit (31/36), 1 profit-monster-trail

**Changes:** None — no signal meets kill criteria

**No Change Needed:**
- breakout-long+ 33%WR/48h but only 3 total trades — too early to kill
- Trade frequency 7/hr (spike) but under 20/hr threshold
- System flat 4+ hours — regime-neutral, no action needed
- ATR SL dominance persists — 1 trail exit appeared, trail system partially active

**Monitoring:**
- breakout-long+ — needs 5+ trades before kill decision
- WLFI exit_reason=None — data quality bug, watch for recurrence
- grind-breakout- got first profit-monster-trail exit — positive sign for trail system

BY: auto_1hr

## [2026-09-15 20:10 UTC] Hourly Analysis

**Trades:** 0 closed (flat hour). 0 open positions.
**24h:** 35T 54.3%WR -$0.02 (breakeven)
**Last activity:** 18:55 UTC (SUPER SHORT +$0.20)

**Hourly breakdown (12h):**
- 18:00: 7T +$0.00 | 17:00: 1T +$0.00 | 15:00: 5T +$0.36 ✅
- 14:00: 1T +$0.21 | 13:00: 2T -$0.13 | 12:00: 2T -$0.07
- 11:00: 1T -$0.16 | 09:00: 2T -$0.08 | 08:00: 1T -$0.15

**Signal health (24h):**
- pullback-entry-: 20T 55%WR +$0.37 (backbone)
- pump-chain-: 3T 66.7%WR +$0.21
- grind-breakout-: 1T 100%WR +$0.03
- rr-struct-v2+: 8T 50%WR -$0.19
- breakout-long+: 2T 0%WR -$0.45 (only 3 total — monitoring)

**Exit reasons (24h):** 85.7% atr_sl_hit | 1 profit-monster-trail | 2 cut-loser-MAE | 1 hard_sl

**Changes:** None — no kill candidates (no signal meets 0% WR + 3+ trades threshold)
**No Change Needed:**
- Trade frequency 0/hr — healthy
- breakout-long+ only 3 total trades — too early to kill
- System flat 1+ hours — no regime action needed
- ATR SL dominance persists — 1 trail exit total

**Monitoring:**
- breakout-long+ — needs 5+ trades before kill decision
- WLFI exit_reason=None — data quality bug (recurring)

BY: auto_1hr

## [2026-09-15 21:10 UTC] Hourly Analysis

**Trades:** 0 closed (flat hour). 1 open (IMX SHORT pullback-entry-).
**24h:** 30T 53.3%WR +$0.07 (breakeven)

**Signal health (24h):**
- pullback-entry-: 19T 57.9%WR +$0.43 (backbone)
- pump-chain-: 2T 100%WR +$0.35
- grind-breakout-: 1T 100%WR +$0.03
- rr-struct-v2+: 6T 33.3%WR -$0.29 (underperforming)
- breakout-long+: 2T 0%WR -$0.45 (needs 3+ trades before kill)

**Exit reasons (24h):** 83.3% atr_sl_hit (25/30) | 2 cut-loser-MAE-GUARD | 1 hard_sl | 1 trail

**Changes:** None — no signal meets kill criteria (breakout-long+ only 2 trades, needs 3+)

**No Change Needed:**
- Trade frequency healthy (system flat 2+ hours)
- rr-struct-v2+ underperforming but not at 0% WR
- ATR SL dominance normal range (83% vs 85% last check)
- 1 profit-monster-trail exit — trail system working

**Monitoring:**
- breakout-long+ — 1 more trade triggers kill review
- rr-struct-v2+ — 6 trades, 33.3% WR, watching for degradation

BY: auto_1hr

## [2026-09-15 22:10 UTC] Hourly Analysis

**Trades:** 0 closed (flat hour). 2 open (ETH SHORT, IMX SHORT — both pullback-entry-).
**24h:** 28T 50.0%WR -$0.18 (near breakeven)

**Signal health (24h):**
- pullback-entry- SHORT: 19T 57.9%WR +$0.43 (backbone)
- pump-chain- SHORT: 2T 100%WR +$0.35
- grind-breakout- SHORT: 1T 100%WR +$0.03
- rr-struct-v2+ LONG: 4T 0%WR -$0.54 (all losers — BTC regime mismatch)
- breakout-long+ LONG: 2T 0%WR -$0.45 (needs 3+ trades for kill review)

**Exit reasons (24h):** 82% atr_sl_hit (23/28) | 2 cut-loser-MAE-GUARD | 1 hard_sl | 1 profit-monster-trail | 1 None

**Root cause of LONG losses:**
- 3/4 rr-struct-v2+ trades had btc_regime='BEAR_TREND' at entry
- Signal only checks atr_regime (token-level), not BTC market regime
- This is a code-level issue (not constants), needs regime cross-check added

**Changes:** None — no kill candidate meets strict criteria (0%WR + 3+ trades IN LAST HOUR; last hour had 0 trades)

**No Change Needed:**
- Kill criteria not triggered (0 trades in last hour)
- ATR SL 82% — tpsl_utils.py deployed, structural dominance normal
- Trade frequency healthy (~1.2/hr avg)
- regime mismatch is code-level fix, not hourly constants change

**Monitoring:**
- rr-struct-v2+ LONG — regime filter gap (atr_regime vs btc_regime)
- breakout-long+ — 1 more trade triggers kill review
- Open SHORT positions — ETH and IMX watching

BY: auto_1hr

## [2026-09-15 23:10 UTC] Hourly Analysis

**Trades:** 0 closed (flat hour). 3 open SHORTs (SYRUP, ETH, IMX — all pullback-entry-).
**24h:** 28T 50.0% WR +$0.04 (breakeven)

**Signal health (24h):**
- pullback-entry- SHORT: 19T 57.9%WR +$0.43 (backbone)
- pump-chain- SHORT: 2T 100%WR +$0.35
- grind-breakout- SHORT: 1T 100%WR +$0.03
- rr-struct-v2+ LONG: 4T 0%WR -$0.54 (CEO KILLED 2026-09-15)
- breakout-long+ LONG: 2T 0%WR -$0.45 (needs 3+ trades for kill review)

**Exit reasons (24h):** 82% atr_sl_hit (23/28) | 2 cut-loser-MAE-GUARD | 1 hard_sl | 1 profit-monster-trail | 1 None

**Changes:** None — no signal meets kill criteria (breakout-long+ only 2 trades, needs 3+)

**No Change Needed:**
- Kill criteria not triggered (0 trades in last hour, breakout-long+ at 2T total)
- Trade frequency healthy (~1.2/hr avg)
- ATR SL 82% — structural, normal with tpsl_utils.py deployed
- BTC regime NEUTRAL — SHORT positions aligned

**Open Questions:**
- breakout-long+ has NO BTC regime filtering (code-level issue, fires LONG in BEAR_TREND). 2T/0%WR. Needs regime gate added in breakout_long.py — out of scope for hourly constants changes.

BY: auto_1hr

## [2026-09-16 00:10 UTC] Hourly Analysis

**Trades:** 1 closed (1 win)
**PnL:** +$0.16 (WR: 100%) — IMX SHORT pullback-entry- (atr_sl_hit at profit)

**Signal health (24h):**
- pullback-entry- SHORT: 20T 57.9%WR +$0.59 avg (backbone)
- pump-chain- SHORT: 2T 100%WR +$0.35
- grind-breakout- SHORT: 1T 100%WR +$0.03
- rr-struct-v2+ LONG: 4T 0%WR -$0.54 (KILLED 09-15)
- breakout-long+ LONG: 2T 0%WR -$0.45 (below 3T kill threshold)

**Exit reasons (24h):** 83% atr_sl_hit (24/29) | 2 cut-loser-MAE | 1 hard_sl | 1 trail | 1 None

**Changes:** None — breakout-long+ at 2T (needs 3+), no other kill candidate

**No Change Needed:**
- Kill criteria not triggered (breakout-long+ 2T/0%WR, below 3T threshold)
- Trade frequency healthy (1/hr)
- ATR SL 83% — structural, expected with tpsl_utils.py
- PnL trend flat (last 6h: $0.16 total)

**Monitoring:**
- breakout-long+ — 1 more trade triggers kill review
- Open positions watching

BY: auto_1hr

## [2026-09-16 01:10 UTC] Hourly Analysis

**Trades:** 0 closed in last hour (1 in last 2h: IMX SHORT +$0.16 atr_sl_hit at profit)
**24h:** 28T 53.6%WR +$0.16 total | 82% atr_sl_hit

**Signal health (24h):**
- pullback-entry- SHORT: 19T 63.2%WR +$0.77 (backbone)
- pump-chain- SHORT: 2T 100%WR +$0.35
- grind-breakout- SHORT: 1T 100%WR +$0.03
- breakout-long+ LONG: 2T/24h 0%WR -$0.45 | 3T all-time 0%WR (NEEDS CODE FIX)
- rr-struct-v2+ LONG: 4T 0%WR -$0.54 (KILLED 09-15)

**Open positions (4):** DOT SHORT, BIGTIME LONG, SYRUP SHORT, ETH SHORT
- All tokens NEUTRAL regime (15m scanner, 01:00 UTC)
- BTC aggregate: NEUTRAL (125 neutral, 2 short bias)

**Exit reasons (24h):** 82% atr_sl_hit (23/28) | 2 cut-loser-MAE | 1 hard_sl | 1 trail

**Changes:** None — no kill criteria met (0 trades in last hour for any signal)

**No Change Needed:**
- Kill criteria not triggered: breakout-long+ 0 trades in last hour (strict 3+/hr not met)
- Trade frequency: 0-1/hr — quiet, well-filtered
- ATR SL 82% — structural, expected
- All open positions in NEUTRAL regime — valid

**Monitoring:**
- breakout-long+ 3T all-time 0%WR — root cause: no BTC regime gate (fires LONG in NEUTRAL/BEAR). Needs code fix in breakout_long.py, not constants toggle. Flag for CEO.
- System quiet — only 1 trade closed in last 2h

BY: auto_1hr

## [2026-09-16 02:08 UTC] Hourly Analysis

**Trades:** 1 closed (BIGTIME LONG breakout-long+ -$0.15 atr_sl_hit)
**24h:** 28T 50%WR -$0.12 | 82% atr_sl_hit

**Signal health (24h):**
- pullback-entry- SHORT: 19T 63.2%WR +$0.77 (backbone)
- pump-chain- SHORT: 1T 100%WR +$0.22
- grind-breakout- SHORT: 1T 100%WR +$0.03
- rr-struct-v2+ LONG: 4T 0%WR -$0.54 (already killed 09-15)
- **breakout-long+ LONG: 3T 0%WR -$0.60 (KILLED THIS RUN)**

**Open positions (6):** tracked in brain DB

**Exit reasons (24h):** 82% atr_sl_hit (23/28) | 2 cut-loser-MAE-GUARD | 1 hard_sl | 1 trail | 1 None

**Changes:**
1. **KILLED breakout-long+** — `BREAKOUT_LONG_PLUS_ENABLED = False`. 3T all-time 0%WR/-$0.60. Root cause: fires LONG in NEUTRAL regime without BTC regime gate. Structural flaw in breakout_long.py — needs code fix if re-enabled.

**No Change Needed:**
- rr-struct-v2+: already killed 09-15 (line 3216)
- ATR SL 82% — structural, expected
- Trade frequency healthy (0-1/hr)
- Short signals performing well (pullback-entry- 63.2% WR)

**Monitoring:**
- pullback-entry- still backbone — watch for degradation
- System quiet — 1 trade in last 2h

BY: auto_1hr

## [2026-09-16 03:15 UTC] Hourly Analysis

**Trades:** 1 closed (IO SHORT pullback-entry- +$0.02 atr_sl_hit)
**24h:** 28T 50%WR -$0.12 | 82% atr_sl_hit (structural)

**Signal health (24h):**
- pullback-entry- SHORT: 20T 65%WR +$0.79 (backbone)
- pump-chain- SHORT: 1T 100%WR +$0.22
- grind-breakout- SHORT: 1T 100%WR +$0.03
- breakout-long+ LONG: 3T 0%WR -$0.60 (killed 02:08)
- rr-struct-v2+ LONG: 3T 0%WR -$0.29 (killed 09-15)

**Open positions (5):** ETH, SEI, ETC, SYRUP, DOT — all pullback-entry- SHORT

**Changes:** None

**No Change Needed:**
- Kill criteria not triggered: no signal has 3+ trades in last hour
- pullback-entry- healthy at 65%WR
- Trade frequency: 1/hr — well-filtered
- ATR SL 82% — structural, expected
- Previously killed signals (breakout-long+, rr-struct-v2+) not firing

BY: auto_1hr

## [2026-09-16 04:15 UTC] Hourly Analysis

**Trades:** 0 closed (system quiet)
**Open positions:** 5 (all pullback-entry- SHORT)
**24h:** 28T 50%WR -$0.12

**Signal health (24h):**
- pullback-entry- SHORT: 19T 68.4%WR +$0.97 (backbone)
- pump-chain- SHORT: 1T 100%WR +$0.22
- grind-breakout- SHORT: 1T 100%WR +$0.03
- breakout-long+ LONG: 3T 0%WR -$0.60 (killed 02:08)
- rr-struct-v2+ LONG: 3T 0%WR -$0.29 (killed 09-15)

**Open positions (5):** ETH 6.3h, SYRUP 5.5h, DOT 3.9h, SEI 2.6h, ETC 2.6h — all pullback-entry- SHORT

**Changes:** None

**No Change Needed:**
- Kill criteria not triggered: no signal has 3+ trades in last hour
- pullback-entry- healthy at 68.4% WR
- Trade frequency: 0/hr — quiet market
- ATR SL 81.5% — structural, expected
- Previously killed signals not firing

**Monitoring:**
- ETH and SYRUP positions 6+ hours old
- All positions SHORT — correlation risk if market reverses
- pullback-entry- still backbone — watch for degradation

BY: auto_1hr

## [2026-09-16 05:11 UTC] Hourly Analysis

**Trades:** 2 closed (DOT SHORT -$0.25, ETC SHORT -$0.28)
**PnL:** -$0.53 (0% WR) — both ATR SL hits

**Signal health (24h):**
- pullback-entry- SHORT: 21T 61.9%WR +$0.44 (backbone)
- grind-breakout- SHORT: 1T 100%WR +$0.03
- breakout-long+ LONG: 3T 0%WR -$0.60 (killed 02:08)
- rr-struct-v2+ LONG: 3T 0%WR -$0.29 (killed 09-15)

**Open positions (4):** SEI 3.8h, SYRUP 6.6h, ETH 7.3h, ADA 0.1h — 3 pullback-entry- SHORT, 1 mover- SHORT

**ATR SL analysis (24h):**
- 23/28 exits = 82% ATR SL (structural for 1.3-1.5% scalping)
- 4/23 hit 1.3% floor exactly — SL minimum, no room to breathe
- k tier: low vol (0.8), normal (1.0), high (1.5) — all clamped to 1.3-1.5%
- Phase scaling disabled (was compressing SL too aggressively)

**6h vs 24h trend:**
- pullback-entry-: 6h 50%WR -$0.35 vs 24h 61.9%WR +$0.44 — slight dip, normal variance at4T

**Changes:** None

**No Change Needed:**
- Kill criteria not triggered: no signal has 3+ trades in last hour with 0% WR
- pullback-entry- healthy at 61.9% WR — 6h dip is variance
- Trade frequency: 2/hr — well-filtered
- ATR SL 82% — structural, expected for scalping system
- Previously killed signals (breakout-long+, rr-struct-v2+) not firing
- pnl_pct column shows incorrect values (e.g. -694% for1.39% move) — display bug, pnl_usdt correct

**Monitoring:**
- SYRUP and ETH positions 6+ hours old
- All positions SHORT — correlation risk if market reverses
- pullback-entry- slight 6h degradation — watch next hour

BY: auto_1hr

## FAVORITES Update — 2026-09-16 06:00 UTC
- Regime: NEUTRAL
- DEMOTE DOT (WR=50.0%, PnL=$-0.12, 1 consecutive bad days, regime=NEUTRAL)
- PROMOTE BIGTIME (WR=62.5%, AvgPnL=1.78%, Trades=8)
- PROMOTE APT (WR=66.7%, AvgPnL=0.30%, Trades=9)
- PROMOTE LTC (WR=80.0%, AvgPnL=0.61%, Trades=5)

Final set: ['ACE', 'APT', 'BABY', 'BANANA', 'BIGTIME', 'CC', 'CFX', 'CHIP', 'ETC', 'IMX', 'LTC', 'POL', 'PONS', 'TURBO']

## LOSERS Update — 2026-09-16 06:05 UTC
- REMOVE NEO (insufficient data)
- REMOVE AIXBT (WR=50.0%, PnL=$-0.08, recovered)
- REMOVE GRASS (insufficient data)
- REMOVE ZRO (insufficient data)
- ADD BLUR (WR=42.9%, PnL=$-0.36, low_wr (42.9%))
- ADD MET (WR=40.0%, PnL=$-0.26, low_wr (40.0%))
- ADD ETH (WR=40.0%, PnL=$0.01, low_wr (40.0%))

Final set: ['BLUR', 'ENA', 'ETH', 'KAS', 'MET']

## [2026-09-16 07:00 UTC] Hourly Analysis

**Trades:** 0 closed (quiet market)
**PnL:** $0.00

**24h:** 27T 48.1%WR -$0.52 | ATR SL 81.5% | pullback-entry- 20T 60%WR +$0.34

**Changes:** None

**No Change Needed:**
- Kill criteria not triggered
- ATR SL 81.5% structural — expected for 1.3-1.5% scalping system
- Trade frequency normal (4 in 6h)
- Previously killed signals (breakout-long+, rr-struct-v2+) not firing
- All 5 open positions SHORT — correlation risk noted but market trending down

**Monitoring:**
- ETH (8.3h) and SYRUP (7.5h) positions aging — watch for SL hits
- CHIP position has tight 0.16% SL — vulnerable to noise
- ADA position has inverted R:R (SL 1.3% vs TP 0.8%) — structural from entry conditions

BY: auto_1hr

## [2026-09-16 06:35 UTC] Daily Orchestrator

**Trades:** 5 open (CHIP, ADA, SEI, SYRUP, ETH — all SHORT). 4 closed today (1W, -$0.66).
**24h:** 27T 48.1%WR -$0.52 | **7d:** 275T 54.9%WR +$2.66

**Findings:**
- Feature recording VERIFIED: DOT, ETC closed with features_recorded=TRUE
- IO gap confirmed: has _signal_metadata but features_recorded=FALSE (deployment timing)
- rr_engine fix CONFIRMED: 0 exits in 6+ days (since Sep 10)
- NEW: 54% of recent trades fired on is_stale=true tokens (speed data flat)
- NEW: exit_conditions field blank on all closed trades (data quality)

**Changes:** None — no config change needed.
**Monitoring:** Stale signal filter need, exit recording gap, signal diversity for NEUTRAL.

BY: daily_orchestrator

## [2026-09-16 08:00 UTC] Hourly Analysis

**Trades:** 0 closed (quiet market)
**PnL:** $0.00

**24h:** 27T 48.1%WR -$0.52 | ATR SL 81.5% | pullback-entry- 20T 60%WR +$0.34

**Changes:** None

**No Change Needed:**
- Kill criteria not triggered (0 trades in last hour)
- ATR SL 81.5% structural — unchanged
- Trade frequency normal (5 in 6h)
- Previously killed signals (breakout-long+, rr-struct-v2+) — 6 legacy trades aging out, no new fires
- Open positions: 5 SHORT, all with normal SL distances (0.7-0.95%)

**Monitoring:**
- ETH (9.3h) and SYRUP (8.5h) positions aging — watch for SL hits
- ADA position has inverted R:R (SL 0.93% vs TP ~0.77%) — structural
- Market quiet — potential regime shift if activity picks up

BY: auto_1hr

## [2026-09-16 10:00 UTC] Hourly Analysis

**Trades:** 0 closed (quiet market)
**PnL:** $0.00

**24h:** 27T 48.1%WR -$0.52 | ATR SL 81.5% | pullback-entry- 20T 60%WR +$0.34

**Changes:** None

**No Change Needed:**
- Kill criteria not triggered (0 trades in last hour)
- ATR SL 81.5% structural — unchanged
- Trade frequency normal (3 in 6h)
- Previously killed signals (breakout-long+, rr-struct-v2+) — 6 legacy trades aging out, no new fires
- Open positions: 5 SHORT, normal SL distances

**Monitoring:**
- ETH and SYRUP positions aging (10h+)
- Quiet market — potential regime shift if activity picks up
- Exit_conditions field blank on trades (data quality issue flagged)

BY: auto_1hr

## [2026-09-16 11:00 UTC] Hourly Analysis

**Trades:** 0 closed in last hour (quiet market)
**Last 6h:** 3 closed — ADA +$0.08, DOT -$0.25, ETC -$0.28
**24h:** 26T 13W 50%WR -$0.55

**24h by exit reason:**
- atr_sl_hit: 20 (76.9%) — structural, known
- cut-loser-MAE-GUARD: 2 | profit-monster-trail: 2 | hard_sl: 1 | None: 1

**24h by signal:**
- pullback-entry-: 18T 11W 61%WR +$0.23 (only active working signal)
- breakout-long+: 3T 0W 0%WR -$0.60 (DEAD — already disabled, legacy aging)
- rr-struct-v2+: 3T 0W 0%WR -$0.29 (DEAD — already disabled, legacy aging)
- grind-breakout-: 1T +$0.03 | mover-: 1T +$0.08

**Open positions:** 5 SHORT (ETH, SYRUP, SEI, CHIP, LTC)

**Changes:** None

**No Change Needed:**
- Kill criteria not triggered (0 trades in last hour)
- ATR SL 76.9% structural — unchanged
- Dead signals (breakout-long+, rr-struct-v2+) already disabled in config — 6 legacy trades aging out, no new fires
- pullback-entry- performing at 61%WR, slightly positive
- Trade frequency normal (26/24h, 0/1h)

**Monitoring:**
- ADA entry RSI=28.82 (deeply oversold for SHORT) — trade won via profit-monster-trail but entry at extreme oversold is risky pattern
- ETH and SYRUP positions aging 12h+
- Quiet market — no regime shift signals yet
BY: auto_1hr

## [2026-09-16 12:00 UTC] Hourly Analysis

**Trades:** 0 closed in last hour (quiet market)
**24h:** 25T 13W 52%WR -$0.21 | ATR SL 76% structural | pullback-entry- 17T 64.7%WR +$0.57

**Changes:** None

**No Change Needed:**
- Kill criteria not triggered (0 trades in last hour)
- ATR SL 76% structural — unchanged
- Dead signals (breakout-long+, rr-struct-v2+) already disabled — 6 legacy trades aging out
- pullback-entry- performing at 64.7%WR, slightly positive
- Trade frequency normal (25/24h, 0/1h)

**Monitoring:**
- 5 SHORT positions open: ETH 14h, SYRUP 13h, SEI 11h, CHIP 6h, LTC 4h
- Quiet market — no regime shift signals yet
- CHIP SHORT showing 269% PnL — check if size is correct
BY: auto_1hr
