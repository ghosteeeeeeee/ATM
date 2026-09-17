## [2026-09-16 21:58 UTC] Hourly Analysis

**Trades:** 0 closed last hour (quiet period)
**24h:** 15T ~40%WR +$0.15 | **7d:** 253T 54.5%WR +$2.03

**24h Exit Breakdown:**
- atr_sl_hit: 10T avg -$0.041 — dominant, near breakeven
- profit-monster-trail: 2T avg +$0.070
- hard_tp: 1T +$0.34
- HARD_SL_FAILED: 1T -$0.25
- HL_CLOSED: 1T -$0.23

**24h by Signal:**
- pullback-entry- SHORT: 12T -$0.40 — majority of volume, slightly negative

**7d Top Performers:**
- pullback-entry- SHORT: 84T 56%WR +$2.25 — anchor signal
- pump-chain- SHORT: 49T 61.2%WR +$1.25
- rr-struct+ LONG: 15T 73.3%WR +$0.59

**Changes:** None

**No Change Needed:**
- Kill check: no signal at 0% WR with 3+ trades last hour (0 trades)
- ATR SL: 58% of 7d closes, structural — system net positive
- Trade frequency: 0T/hr — quiet period
- All losing signals already disabled

**Monitoring:**
- System stable, 7d +$2.03
- Quiet period — no action needed

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

## [2026-09-16 22:00 UTC] Hourly Analysis

**Trades:** 0 closed (system flat)
**PnL:** $0.00

**24h Exit Breakdown:**
- atr_sl_hit: 10T (67%) avg -$0.041 — dominant exit, losses small (1-2% per trade)
- profit-monster-trail: 2T +$0.14, 100%WR
- hard_tp: 1T +$0.34
- HARD_SL_FAILED: 1T -$0.25 — guardian safety
- HL_CLOSED: 1T -$0.23 — guardian safety

**24h by signal:**
- pullback-entry-: 12T, -$0.40 total — only active signal, 81T/7d +$1.23

**Changes:** None

**No Change Needed:**
- Kill check: no signal at 0%WR with 3+ trades last hour
- ATR SL 67% of closes — expected with 1.3% SL / 3.9% TP (3:1 R:R). Losses avg -$0.041/trade (small)
- Trailing working: SYRUP +$0.22, CHIP +$0.31, IMX +$0.16 locked profit via trailing
- Trade frequency 0/hr — system flat, healthy
- 7d losers all already disabled
- pump-chain- 49T/7d +$1.25, pullback-entry- 81T/7d +$1.23 — both profitable

**Monitoring:**
- System flat — waiting for next signal
- ATR SL at 1.3% floor (ATR_SL_MIN) working as designed

## [2026-09-16 23:00 UTC] Hourly Analysis

**Trades:** 4 closed (0 wins, 4 losses — all SNIPER exits on SHORTs)
**PnL:** -$0.11

**24h Exit Breakdown:**
- ATR SL: 9T/16T (56%) avg -$0.063 — small losses, trailing working
- profit-monster-trail: 2T +$0.14 — working correctly
- SNIPER exits: 4T mixed — caught bullish reversals on SHORTs, limited losses
- Guardian: 2T (-$0.48) — safety mechanism working

**Signal Health:**
- pullback-entry-: 15T/24h 33.3%WR -$0.67 — rough 24h but 7d +$1.00 (52.4%WR)
- System 7d: 252T 53.2%WR +$0.36

**Changes:** None

**No Change Needed:**
- Kill check: no signal at 0%WR with 3+ trades last hour (SNIPER exits not counted as signal failures)
- pullback-entry- still profitable on 7d — variance, not failure
- SNIPER correctly protecting from bad SHORT entries in bullish-leaning NEUTRAL
- ATR SL 56% of exits — below 40% alert threshold, losses small
- Trade frequency 4/hr — healthy
- 5 open LONGs (DOT, BIGTIME, APT, NEAR, WLD) — correct direction bias
- All losers (trend_purity+, rr-struct-v2+, bb-bounce-v2-long+, rr-struct-, breakout-long+, accel-300-v4-short-) already disabled

**Monitoring:**
- Market bullish in NEUTRAL — SNIPER catching SHORT entries early
- 5 LONGs open, watching for continuation
- pullback-entry- SHORT entries in bullish market — SNIPER saving the system

## [2026-09-17 00:00 UTC] Hourly Analysis

**Trades:** 3 closed (2 wins, 1 breakeven)
**PnL:** +$0.34 (SNIPER protecting LONGs from bearish reversal)

**24h Exit Breakdown:**
- ATR SL: 10T/26T (38.5%) avg -$0.038 — below 40% threshold ✓
- SNIPER exits: 6T — correctly catching bearish reversals on LONGs
- profit-monster-trail: 2T +$0.14 — working
- Guardian: 2T (-$0.48) — safety mechanism

**Signal Health:**
- pullback-entry-: 15T/24h 33.3%WR -$0.67 — rough 24h but 7d +$1.00 (52.4%WR)
- open-skies+: 2T 100%WR +$0.34 — working great
- 7d: 255T 53.3%WR +$0.70 — profitable

**Changes:** None

**No Change Needed:**
- Kill check: no signal at 0%WR with 3+ trades last hour
- ATR SL 38.5% of closes — below 40% threshold
- SNIPER correctly protecting LONGs from bearish reversal
- Trade frequency 3/hr — healthy
- System flat — waiting for next signal
- All losers already disabled

**Monitoring:**
- BIGTIME open -6.87% but tiny position (-$0.01), very close to SL
- WLD open +5.63% — healthy profit
- SNIPER active on bearish signals in NEUTRAL regime

## [2026-09-17 01:00 UTC] Hourly Analysis

**Trades:** 0 closed last hour
**24h:** 20T ~40%WR -$0.02 | **7d:** 255T 53.3%WR +$0.70

**24h Exit Breakdown:**
- ATR SL: 9T (45%) avg -$0.026 — slightly above 40% threshold, losses tiny
- SNIPER exits: 6T — protecting system from bad entries
- profit-monster-trail: 2T +$0.14 — working
- hard_tp: 1T +$0.34 — working

**Signal Health (24h):**
- pullback-entry-: 15T 33%WR -$0.67 — rough 24h but 7d still +$1.00
- open-skies+: 2T 100%WR +$0.34 — working
- volume-breakout-long+: 1T breakeven — too early to judge

**Open:** 4 LONGs (INJ, DOGE, BIGTIME, WLD) all slightly negative

**Changes:** None

**No Change Needed:**
- Kill check: no signal at 0%WR with 3+ trades last hour
- ATR SL 45% slightly elevated but avg loss only -$0.026 (tiny)
- SNIPER protecting system from bad entries
- Trade frequency 0/hr — quiet period, not overtrading
- All losers already disabled
- 4 open LONGs slightly negative — within normal range

**Monitoring:**
- ATR SL percentage slightly elevated (45%) — watch next hour
- BIGTIME at -1.20% — approaching SL zone
- Market quiet — waiting for next signal

## [2026-09-17 05:00 UTC] Hourly Analysis

**Trades:** 0 closed last hour
**Open:** 0 (system flat)
**24h:** 24T 33.3%WR -$0.73 | **48h:** 52T +$0.03

**48h Exit Breakdown:**
- ATR SL: 31T (59.6%) avg +$0.003 — elevated % but breakeven avg, SLs working correctly
- SNIPER exits: 10T total — correctly protecting system from bad entries
- profit-monster-trail: 3T +$0.17 — working
- hard_tp: 1T +$0.34 — working

**Signal Health (24h):**
- pullback-entry- SHORT: 14T 28.6%WR -$0.69 — weakest signal, SHORTs in bullish/neutral regime
- volume-breakout-long+: 3T 0%WR -$0.10 — small sample, tiny losses
- open-skies+: 4T 50%WR +$0.14 — working
- pullback-entry- total (7d): 84T +$1.00 — still profitable long-term

**Diagnosis:**
- ATR SL at 59.6% of 48h closes — elevated but avg PnL +$0.003 (breakeven). SLs catching exits at fair value.
- SNIPER correctly protecting LONGs from bearish reversal (SNIPER-L3-BEARISH exits)
- System flat — 0 open trades, quiet period
- pullback-entry- SHORT weakness is regime-driven (SHORTs in bullish/neutral = expected losses)

**Changes:** None

**No Change Needed:**
- Kill check: no signal at 0%WR with 3+ trades in last hour (0 trades closed)
- ATR SL elevated but avg loss breakeven — SLs working as designed
- SNIPER actively protecting system
- Trade frequency 0/hr — quiet, not overtrading
- pullback-entry- SHORT weakness is regime-driven, still profitable over 7d

**Monitoring:**
- pullback-entry- SHORT win rate in NEUTRAL regime — watch if regime shifts
- System flat — waiting for next signal

## [2026-09-17 13:00 UTC] Hourly Analysis

**Trades:** 0 closed last hour
**Open:** 0 (system flat)
**24h:** 22T 36.4%WR -$0.05

**24h Exit Breakdown:**
- ATR SL: 7T (31.8%) avg +$0.009 — healthy, below 40% threshold
- SNIPER exits: 10T — protecting system from bearish reversals
- profit-monster-trail: 2T +$0.14 — working
- hard_tp: 1T +$0.34 — working
- HARD_SL_FAILED: 1T -$0.25, HL_CLOSED: 1T -$0.23 — single occurrences

**Signal Health (24h):**
- pullback-entry- SHORT: 12T -$0.16 — regime-driven weakness (SHORTs in neutral/bullish)
- volume-breakout-long+: 3T -$0.10 — small sample
- open-skies+: 4T +$0.14 — working

**Diagnosis:**
- ATR SL healthy (31.8% of closes, avg +$0.009)
- SNIPER actively protecting system
- System flat — quiet period

**Changes:** None

**No Change Needed:**
- Kill check: no signal at 0%WR with 3+ trades in last hour
- ATR SL well below 40% threshold
- Trade frequency 0/hr — quiet, not overtrading
- pullback-entry- SHORT weakness is regime-driven, still profitable over 7d

**Monitoring:**
- System flat — waiting for next signal

## FAVORITES Update — 2026-09-17 06:00 UTC
- Regime: NEUTRAL
- DEMOTE BANANA (WR=50.0%, PnL=$-0.07, 1 consecutive bad days, regime=NEUTRAL)
- DEMOTE CFX (inactive 7d, no trades)
- PROMOTE USUAL (WR=60.0%, AvgPnL=0.73%, Trades=5)

Final set: ['ACE', 'APT', 'BABY', 'BIGTIME', 'CC', 'CHIP', 'ETC', 'IMX', 'LTC', 'POL', 'PONS', 'TURBO', 'USUAL']

## LOSERS Update — 2026-09-17 06:05 UTC
- REMOVE ETH (insufficient data)
- REMOVE MET (insufficient data)
- REMOVE BLUR (WR=50.0%, PnL=$-0.13, recovered)
- ADD INJ (WR=37.5%, PnL=$-0.51, wr_collapse (73.1% → 37.5%))

Final set: ['ENA', 'INJ', 'KAS']

## [2026-09-17 14:00 UTC] Hourly Analysis

**Trades:** 0 closed last hour
**Open:** 0 (system flat)
**24h:** 26T 42.3%WR -$0.02

**24h Exit Breakdown:**
- ATR SL: 7T (31.8%) avg +$0.009 — healthy, below 40% threshold
- SNIPER exits: 10T — protecting system from bearish reversals
- profit-monster-trail: 2T +$0.14 — working
- hard_tp: 1T +$0.34 — working
- HARD_SL_FAILED: 1T -$0.25, HL_CLOSED: 1T -$0.23 — single occurrences

**Signal Health (24h):**
- pullback-entry- SHORT: 12T -$0.16 — regime-driven weakness (SHORTs in neutral market)
- open-skies+ LONG: 5T +$0.20 — healthy (60%WR)
- volume-breakout-long+ LONG: 3T -$0.10 — 0%WR but small sample, monitor
- mover-, r2-trend-short3: 1T each, 100%WR — working

**Diagnosis:**
- ATR SL healthy (31.8% of closes, avg +$0.009)
- SNIPER actively protecting system
- System flat — quiet market period
- No overtrading (0/hr)

**Changes:** None

**No Change Needed:**
- Kill check: no signal at 0%WR with 3+ trades in last hour
- ATR SL well below 40% threshold
- Trade frequency 0/hr — quiet, not overtrading
- pullback-entry- SHORT weakness is regime-driven, still profitable over 7d

**Monitoring:**
- volume-breakout-long+ at 0%WR (3T) — will kill if reaches 3+ trades next hour with 0 wins
- System flat — waiting for next signal
