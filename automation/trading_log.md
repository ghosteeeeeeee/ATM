# Trading Log — Learnings & Decisions

## [2026-09-03 05:42 UTC] System Status

**Pipeline:** 3 open | 54 closed today | -70% PnL (cumulative daily)
**Weekly:** ~396 closed | 220 wins | 55.6% WR
**Market:** NEUTRAL | Pipeline: OK | Alerts: None

**Open positions:** YGG SHORT, ME SHORT, +1 more
**Context gate:** Blocking ATOM LONG (ema300-dip) — "setup is actively harmful"

### Signal Status (24h)
| Signal | Trades | WR | PnL | Status |
|--------|--------|-----|-----|--------|
| bb-bounce-v2-long+ | 12 | 83.3% | $0.35 | ⭐ Star |
| ema300-dip | 6 | 66.7% | $0.15 | ✅ Good |
| bb-bounce-short | 7 | 85.7% | $0.10 | ✅ Good |
| accel-300-v3-short- | High | — | — | Dominant |

### Recently Killed
| Signal | Reason | Date |
|--------|--------|------|
| r2-trend-long | 5T/24h 20% WR -$0.44, ALL losers | Sep 03 |
| range-reversion-long+ | 6T/24h 16.7% WR -$0.62, NEUTRAL | Sep 02 |
| accel-300-v3-long+ | 20% WR, CEO protected until Sep 04 05:00 | Sep 02 |

### Decisions Needed
1. **Sep 04 05:00 UTC:** accel-300-v3-long+ CEO lock expires — re-enable or kill?
2. Consider boosting allocation to winners (bb-bounce-v2-long+, ema300-dip, bb-bounce-short)

---

## [2026-09-02 04:07 UTC] Hourly Analysis

**Trades:** 3 closed last hour (2W 1L) +$0.05 — all PM trail exits
**24h:** 51T 31W 60.8%WR net ~-$1.48
**Open:** 4 (ICP LONG, GRASS LONG, ME SHORT, YGG SHORT)

**Close reason (24h):**
- profit-monster-trail: 25T (49%) avg +$0.050 — only profitable exit
- atr_sl_hit: 21T (41.2%) avg -$0.100 — down from 68.7%, improving
- cut-loser: 4T (7.8%) avg -$0.155 — normal

**Signal (24h, 3+ trades):**
- bb-bounce-v2-long+: 12T 83.3%WR +$0.35 ⭐
- ema300-dip: 4T 75%WR +$0.14 — new signal, strong
- bb-bounce-short: 7T 85.7%WR +$0.10
- accel-300-v3-long+: 6T 16.7%WR -$0.69 — CEO_PROTECTED until Sep 04 05:00

**No Change Needed:** System improving. PM trail占比提升. Trade freq ~2.1/hr normal.

---

## [2026-09-01 19:10 UTC] Hourly Analysis

**Trades:** 1 closed (1W 0L) +$0.21
**24h:** 57T 30W 52.6%WR -$0.47
**Open:** 0 — flat

**Close reason (24h):** atr_sl_hit 31T (54.4%) avg -$0.050. profit-monster-trail 23T (40.4%) avg +$0.052.

**Signal (24h):**
- bb-bounce-long+: 21T 52%WR -$0.34 — KILLED (NEVER_REENABLED)
- accel-300-v2-long: 15T 33%WR -$0.44 — KILLED (NEVER_REENABLED)
- bb-bounce-short: 5T 80%WR +$0.01 — healthy

**No Change Needed:** Kill thresholds not met for remaining signals.

---

## [2026-09-01 09:05 UTC] Hourly Analysis

**Trades:** 7 closed (1W 6L) -$0.44 — worst hour in 12h
**24h:** 69T 33W 47.8% WR -$0.80
**Open:** 2 LONG (AVAX, LTC)

**Changes:**
1. KILLED BB_BOUNCE_LONG_ENABLED = False — 5T/0%WR/-$0.47 last hour. Added to NEVER_REENABLE_FLAGS.

---

## [2026-08-31 20:06 UTC] Hourly Analysis

**Trades:** 2 closed (1W 1L) +$0.05
**24h:** 42T 19W 45%WR -$0.40

**Changes:**
1. KILLED ACCEL_300_V2_LONG_ENABLED = False — 5T/20%WR/-$0.19. Previous kill at 17:06 never implemented (flag still True). Now properly disabled.

---

## [2026-08-31 17:06 UTC] Hourly Analysis

**Trades:** 8 closed in 2h (3W 5L) -$0.23
**24h:** 45T 19W 42%WR -$0.44

**Changes:**
1. KILLED ACCEL_300_V2_LONG_ENABLED = False — 3T/0%WR/-$0.20. Kill threshold met.

---

## [2026-08-29 20:05 UTC] Hourly Analysis

**Trades:** 1 closed (1W 0L) +$0.07
**24h:** 45T 57%WR -$0.20
**Open:** 5 SHORT (DOT, KAS, DOGE, CRV, ADA)

**No Change Needed:** 5 consecutive positive hours after 15:00 dip.

---

## [2026-08-28 18:28 UTC] Orchestrator Daily

**Pipeline:** 5 open | 91 closed today | +48.48% PnL
**24h:** 90T 60%WR +$0.86 (strong)
**7d:** 419T 52.7%WR +$0.95

**Actions:** Updated CURRENT.md. No implementation tasks.

---

## [2026-08-28 12:05 UTC] Hourly Analysis

**Trades:** 0 closed (8 in last 2h)
**24h:** 81T 42W 51.9% WR -$0.07
**Open:** 3 SHORT (ONDO, ME, BABY)

**No Change Needed:** Kill criteria not triggered. Trade freq 3.5/hr normal.

---

## [2026-08-28 02:15 UTC] Hourly Analysis

**Trades:** 4 closed (4W 0L) +$0.80
**24h:** 69T 43.5% WR -$0.50
**Open:** 5 SHORT (all accel-300-v2-)

**Signal (24h):** accel-300-v2- 16T 44%WR +$0.33. macd-div- 5T 100%WR +$0.29 ⭐.

---

## [2026-08-27 18:35 UTC] Daily Orchestrator

**Pipeline:** 5 open (all SHORT) | 62 closed today | -34.7% PnL
**24h:** 107T 47.7% WR -$0.43
**Market:** 104 NEUTRAL / 1 LONG / 1 SHORT

### Kills Today
1. slow-grind- (CEO 18:20) — flag was still True despite documented kill. Root cause: CEO forgot to edit constants.
2. bb_bounce+ (CEO 18:04) — 48h 9T/11.1%WR/-$0.74 after re-enable.
3. pump-catcher+ (CEO 14:30) — 21T/7d 33.3% WR -$0.39.
4. atr-spike+ (signal_reporter 17:09) — 7T/7d 28.6% WR -$0.15.

### CRITICAL
- System has ZERO backbone signals — all killed. Trade volume low.
- All 5 positions SHORT in NEUTRAL market — structural mismatch.
- Disk at 83% — approaching 85% cleanup.

---

## [2026-08-27 03:05 UTC] Hourly Analysis

**Trades:** 3 closed (1W 2L) -$0.16
**24h:** 65T 28W 43.1% -$0.43

**Changes:**
1. FIXED slow_grind_short lifecycle — Changed from 'lagging' to 'concurrent'. Normal SL instead of tight SL.

---

## [2026-08-26 06:40 UTC] Lifecycle Filters Deployed

**What:** signal_lifecycle_filter.py integrated into SL/TP computation.
**How:** Signals tagged as early/concurrent/lagging. Early gets wider SL (+50%), bigger TP (+100%). Lagging gets tighter SL (-20%).
**Expected:** +3-5% WR from appropriate position sizing.

---

## [2026-08-25 20:10 UTC] Hourly Analysis

**Trades:** 1 closed (0W 1L) -$0.14
**24h:** 38T 15W 39% -$1.70
**Open:** 5 positions (3 SHORT, 2 LONG)

**Changes:**
1. KILLED hl_copy_trader — `HL_COPY_SIGNAL_ENABLED = False`. 12T/25%WR/-$1.13/24h, #1 loser. Copy delay = enters after move over. NEVER_REENABLE.

---

## [2026-08-24 12:05 UTC] Hourly Analysis

**Trades:** 6 closed (2W 4L) -$0.30
**24h:** 73T 42W 57.5% +$0.70
**Open:** 0 — flat

**Signal (24h):** bb_bounce+ 11T/10W 91% +$0.88 ⭐. macd-div- 4T/4W 100% +$0.32.

---

## [2026-08-23 06:30 UTC] Daily Orchestrator

**Pipeline:** 5 open | 39 closed today | -6.05% PnL
**24h:** 35T 17W 48.6% +$0.05
**Market:** NEUTRAL

**Key:** hl_copy_trader 25T/24h 48% +$0.22 (ONLY profitable). MAE-GUARD DISABLED.

---

## [2026-08-20 18:30 UTC] Daily Orchestrator

**Status:** System HEALTHY
**24h:** 23T 56.5% WR -$0.40
**7d:** 271T 50.6% WR -$1.57

---

## [2026-08-20 08:00 UTC] signal_reporter

Killed mover+ (MOMENTUM_LEADERBOARD) — 28.6% WR, -$0.15 (7d). Master + SHORT disabled, added to NEVER_REENABLE.

---

## [2026-08-19 17:00 UTC] signal_reporter

No kills — 7d losers already disabled. 24h quiet (17T -$0.42). Watch: mover+ (28.6% WR 7d). Winners: r2-trend-long6 (100% WR), r2-trend-long2 (64.7% WR).

---

## Blacklist Testing Complete

77 tokens tested (Batches 1-5), 0 KEEP. Blacklist is not the bottleneck — signal generation filters block these tokens. Focus on improving signal quality for active tokens.

## FAVORITES Update — 2026-09-03 06:00 UTC
- Regime: NEUTRAL
- DEMOTE BIGTIME (WR=50.0%, PnL=$-0.14, 1 consecutive bad days, regime=NEUTRAL)
- PROMOTE DOT (WR=100.0%, AvgPnL=3.57%, Trades=6)
- PROMOTE SEI (WR=71.4%, AvgPnL=1.55%, Trades=7)
- PROMOTE BCH (WR=60.0%, AvgPnL=1.28%, Trades=5)
- PROMOTE BANANA (WR=71.4%, AvgPnL=0.23%, Trades=7)
- PROMOTE PUMP (WR=60.0%, AvgPnL=0.17%, Trades=5)

Final set: ['ASTER', 'BABY', 'BANANA', 'BCH', 'DOT', 'DYDX', 'FOGO', 'INJ', 'KAS', 'LTC', 'ME', 'NXPC', 'PUMP', 'SEI', 'STX', 'SYRUP', 'TURBO', 'USUAL']

## LOSERS Update — 2026-09-03 06:05 UTC
- REMOVE MERL (insufficient data)
- REMOVE BCH (WR=60.0%, PnL=$0.13, recovered)
- REMOVE ENS (insufficient data)
- REMOVE ETC (WR=60.0%, PnL=$0.01, recovered)
- REMOVE POL (WR=57.1%, PnL=$-0.05, recovered)
- REMOVE ALT (insufficient data)
- REMOVE ATOM (insufficient data)
- REMOVE IO (insufficient data)
- REMOVE MON (insufficient data)
- REMOVE NEO (insufficient data)
- REMOVE ENA (insufficient data)
- REMOVE CHIP (insufficient data)
- REMOVE NEAR (insufficient data)
- ADD W (WR=20.0%, PnL=$-0.35, wr_collapse (48.1% → 20.0%))
- ADD GRASS (WR=40.0%, PnL=$-0.24, low_wr (40.0%))
- ADD ONDO (WR=40.0%, PnL=$-0.11, low_wr (40.0%))

Final set: ['CC', 'GRASS', 'JUP', 'MET', 'ONDO', 'W', 'XPL', 'ZEN']

## [2026-09-03 06:15 UTC] Hourly Analysis

**Trades:** 6 closed (3W 3L)
**PnL:** $-0.34 (WR: 50.0%)

**Breakdown:**
- ema300-dip: 4T 75%WR +$0.04 (3 PM trail exits, 1 cut-loser)
- bb-bounce-v2-long+: 1T 0%WR -$0.15 (atr_sl_hit ZEN)
- accel-300-v3-long+: 1T 0%WR -$0.23 (atr_sl_hit STX)

**24h Context:** 53T 50.9%WR -$1.75
- profit-monster-trail: 27T avg +$0.049 (carrying system)
- atr_sl_hit: 20T (37.7%) avg -$0.116 (under 40% structural threshold)

**Changes:** None needed.

**No Change Needed:**
- Kill criteria: no signal has 0%WR with 3+T last hour
- atr_sl_hit at 37.7% — under 40% threshold, no SL widen needed
- range-reversion-long+: all 6 trades from before kill date (Sep 2), signal already disabled (RANGE_REVERSION_PLUS_ENABLED=False), no new trades
- accel-300-v3-long+: CEO locked until Sep 4 05:00 UTC, 5T 0%WR -$0.70 — cannot touch
- Trade freq 2.2/hr normal, 2 open positions small ($11-20)
- FOGO -336% pnl_pct is a data quality bug for low-price tokens, not a real issue

**Open Questions:**
- accel-300-v3-long+ 0%WR — will auto-disable after CEO lock expires Sep 4 05:00?
- pnl_pct calculation anomaly for sub-cent tokens (FOGO)
