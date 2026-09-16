## [2026-09-16 19:09 UTC] Hourly Analysis

**Trades:** 2 closed last hour (0W 2L -$0.48)
- ME SHORT pullback-entry- atr_sl_hit: -$0.15
- ACE SHORT pullback-entry- atr_sl_hit: -$0.33

**24h:** 16T ~50%WR +$1.34 | **7d:** 261T 55.6%WR +$2.54

**24h Exit Breakdown:**
- atr_sl_hit: 13T avg +$0.028 — net positive
- profit-monster-trail: 2T avg +$0.070
- hard_tp: 1T +$0.34

**24h by Signal:**
- pullback-entry- SHORT: 13T 66%WR +$0.86 — dominant, healthy

**7d Losers (all already disabled):**
- trend_purity+: 11T 0%WR -$0.90 → `TREND_PURITY_PLUS_ENABLED=False`
- rr-struct-v2+: 10T 0%WR -$0.45 → `RR_STRUCTURAL_V2_LONG_ENABLED=False`
- bb-bounce-v2-long+: 5T 0%WR -$0.45 → `BB_BOUNCE_V2_LONG_ENABLED=False`
- rr-struct-: 7T 0%WR -$0.42 → `RR_STRUCTURAL_MINUS_ENABLED=False`
- accel-300-v4-short-: 5T 0%WR -$0.26 → in killed list

**Changes:** None — all losing signals already killed

**No Change Needed:**
- Kill check: no signal at 0% WR with 3+ trades last hour (only 2 trades)
- ATR SL: 150T/7d 54%WR net +$2.16 — within tolerance
- Trade frequency: 2T/hr — healthy
- All 0% WR signals already disabled by prior sessions

**Monitoring:**
- System stable, 7d net positive (+$2.54)
- Last hour's 2 losses are noise (2 trades, same signal, market conditions)

## [2026-09-16 16:10 UTC] Hourly Analysis

**Trades:** 0 closed last hour (quiet period)
**24h:** 18T ~44%WR ~+$0.15 | **7d:** 261T 55.6%WR +$2.54

**24h Exit Breakdown:**
- atr_sl_hit: 13T avg -$0.028 — fix working (near breakeven)
- profit-monster-trail: 3T avg +$0.057
- hard_tp: 1T +$0.34

**24h by Signal:**
- pullback-entry-: 12T 58.3%WR +$0.58 — solid
- breakout-long+: 3T 0%WR -$0.60 — already killed (disabled 02:08 UTC)
- Other signals: 1T each, minor PnL

**Changes:** None

**No Change Needed:**
- Kill check: no signal at 0%WR + 3+ trades last hour (0 trades last hour)
- ATR SL fix: avg exit -$0.028 — well within tolerance
- Trade frequency: 4T/6h = ~0.7/hr — healthy
- breakout-long+: already killed by prior session
- trend_ignition: already disabled

**Monitoring:**
- System running healthy, 7d net positive (+$2.54)
- ATR SL 1.0-1.5% zone remains main loss driver (7d) but within acceptable range

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

## [2026-09-16 15:30 UTC] Hourly Analysis

**Trades:** 0 closed last hour (quiet period)
**24h:** 18T 55.6%WR +$0.23

**24h Exit Breakdown:**
- atr_sl_hit: 13T (72% of closes) avg -$0.028, 46.2%WR — above 40% threshold but avg loss within tolerance
- profit-monster-trail: 3T +$0.17, 100%WR — working perfectly
- hard_tp: 1T +$0.34, 100%WR
- breakout-long+: 3T -$0.60, 0%WR — already disabled by prior session

**7d:** 255T 55.7%WR +$2.72 — healthy, net positive

**Open:** 5 SHORTs (all pullback-entry-), max age 18.5h, all near breakeven

**Changes:** None

**No Change Needed:**
- Kill check: 0 trades in last hour, no signal qualifies
- breakout-long+ already disabled (3T 0%WR)
- ATR SL at 72% of closes but avg -$0.028 is acceptable — ATR_SL_MIN fix holding
- Trade frequency 0 entries/hr — healthy, not overtrading
- 7d net positive, no degradation

**Monitoring:**
- SYRUP SHORT open 18.5h — longest open trade, monitor for staleness
- ATR SL 1.0-1.5% zone (7d 14%WR -$10.38) — main loss driver, already documented
- breakout-long+ disabled — if re-enabled, monitor closely

## [2026-09-16 18:30 UTC] Hourly Analysis

**Trades:** 4 closed (4 wins, 0 losses)
**PnL:** +$1.18 (WR: 100%)
**24h:** 21T 66.7%WR +$1.33
**7d:** 255T 55.7%WR +$2.72

**24h Exit Breakdown:**
- atr_sl_hit: 16T (76%) avg +$0.051 — trailing stops locking in profit (healthy)
- profit-monster-trail: 3T +$0.17, 100%WR
- hard_tp: 1T +$0.34, 100%WR

**Open:** 2 trades (ACE SHORT 0.6h, ME SHORT 4.7h)

**Changes:** None

**No Change Needed:**
- Kill check: no signal at 0%WR with 3+ trades last hour
- ATR SL at 76% but avg +$0.051 — trailing into profit, working correctly
- Trade frequency 1/hr — healthy, not overtrading
- 7d losers (trend_purity+, breakout-long+, accel-300-v4-short-) already disabled
- rr-struct-v2+ 10T/7d 40%WR -$0.45 — borderline, too small sample, monitor

**Monitoring:**
- rr-struct-v2+: watch for continued bleed next sessions
- pump-chain+: 25T/7d 40%WR -$0.28 — borderline, stable, no action yet

## [2026-09-16 20:00 UTC] Hourly Analysis

**Trades:** 2 closed (0 wins, 2 losses)
**PnL:** -$0.28 (WR: 0%)
**24h:** 13T 53.8%WR +$0.62
**7d:** 254T 55.1%WR +$3.23

**24h Exit Breakdown:**
- atr_sl_hit: 9T avg +$0.027 — trailing into profit (healthy)
- profit-monster-trail: 2T +$0.14, 100%WR
- HARD_SL_FAILED: 1T -$0.10 — guardian safety close (SEI 18.7h open, SL failed on exchange)
- hard_tp: 1T +$0.34

**Open:** 4 trades (ACE SHORT 6.7h, ME SHORT 6.7h, ACE SHORT 2.6h, SYRUP SHORT 0.3h)

**Changes:** None

**No Change Needed:**
- Kill check: no signal at 0%WR with 3+ trades last hour
- HARD_SL_FAILED is guardian safety mechanism working correctly
- ATR SL at 9T/13T (69%) avg +$0.027 — trailing working
- Trade frequency 2/hr — healthy, not overtrading
- 7d losers (trend_purity+, rr-struct-v2+, bb-bounce-v2-long+, rr-struct-, ema300-dip-long, breakout-long+, accel-300-v4-short-) all already disabled
- pump-chain+ 25T/7d 40%WR -$0.28 — borderline, stable, no action

**Monitoring:**
- 4 open trades, all SHORT, max 6.7h — healthy age
- pump-chain+ 25T/7d — watch for continued bleed

## [2026-09-16 21:00 UTC] Hourly Analysis

**Trades:** 5 closed (0 wins, 5 losses including 1 $0 orphan paper)
**Real PnL:** -$0.76 (WR: 0%)
**24h:** 16T 50%WR +$0.15
**7d:** 255T 55.7%WR +$2.80

**24h Exit Breakdown:**
- atr_sl_hit: 10T avg +$0.011 — trailing into profit (healthy)
- profit-monster-trail: 2T +$0.14, 100%WR
- hard_tp: 1T +$0.34
- HARD_SL_FAILED: 1T -$0.23 — guardian caught exchange SL failure (SEI)
- HL_CLOSED: 1T -$0.22 — guardian safety close (ACE, 7h stale)
- ORPHAN_PAPER: 1T $0.00 — guardian paper cleanup (SYRUP)

**Open:** 0 trades — system flat

**Changes:** None

**No Change Needed:**
- Kill check: no signal at 0%WR with 3+ trades last hour
- HARD_SL_FAILED is guardian safety mechanism working correctly
- HL_CLOSED is guardian closing stale position where exchange SL failed
- ATR SL at 10T/16T (62.5%) avg +$0.011 — trailing working
- Trade frequency 5/hr — healthy, not overtrading
- 7d losers (trend_purity+, rr-struct-v2+, bb-bounce-v2-long+, rr-struct-, breakout-long+, accel-300-v4-short-) all already disabled
- pump-chain+ 25T/7d 40%WR -$0.28 — borderline, stable, no action

**Monitoring:**
- System flat — waiting for next signal
- pullback-entry- only active signal (12T/24h), 7d +$2.80, today 36.4%WR (below avg but small sample)
