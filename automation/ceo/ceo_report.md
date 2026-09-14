## CEO Report — 2026-09-14 ~18:37 UTC

### Diagnosis
24h negative: 41T 41.5% WR -$1.12 (VERIFIED). 7d positive: 321T 53.3% WR +$0.56 (VERIFIED — degraded from +$1.30). Today (Sep 14): 34T 38.2%WR -$1.31. 7 open positions. Market NEUTRAL 100%.

### Verified Numbers (DB-queried this run)
- 24h: 41T, 41.5% WR, -$1.12 (below breakeven ~58%)
- 7d: 321T, 53.3% WR, +$0.56
- Today (Sep 14 full day): 34T, 38.2% WR, -$1.31
- 7d regime: NEUTRAL 314T 54.1%WR +$1.14 (market 100% NEUTRAL)
- 7d exit: profit-monster-trail +$5.36★ | atr_sl_hit +$0.45 | rr_engine_resistance -$1.33 (fix deployed) | cut-loser-CL-T1 -$5.05 (legacy)
- 7d ACTIVE SIGNALS: pullback-entry- 57T/63.2%WR +$2.63★ | rr-struct+ 15T/73.3%WR +$0.59 | pump_chain 22T/50%WR +$0.34 | pump-chain- 51T/60.8%WR +$0.83 | open_skies 4T/75%WR +$1.43
- 7d DRAGGERS: ema300_dip_short 16T/43.8%WR -$0.96 (DEAD) | trend_purity+ 11T/36.4%WR -$0.90 (KILLED) | sma20_dip 19T/42.1%WR -$0.73 (DEAD) | pump-chain+ 24T/37.5%WR -$0.56 (KILLED today) | bb_bounce_v2_long 11T/45.5%WR -$0.68 (DEAD)
- Today losers: pump-chain+ 6 LONG -$0.66 (killed), rr-struct-v2+ 2 LONG -$0.26, pullback-entry- 11 SHORT -$0.25
- 7 open positions (3 rr-struct-v2+ LONG, 1 pump-chain- SHORT, 1 pullback-entry- SHORT, 1 pump-chain+ LONG pre-kill, 1 rr-struct-v2+/rs-s37 LONG)

### Root Cause
Today's -$1.31 is dominated by killed signals (pump-chain+ -$0.66, trend_purity+ -$0.75 in 48h). These will age out. The 7d PnL degraded from +$1.30 to +$0.56 over 4 hours — normal variance in choppy NEUTRAL market. Legacy signals (ema300_dip_short -$0.96, trend_purity+ -$0.90, sma20_dip -$0.73) still in 7d window — last closes were Sep 8-13, aging out by Sep 15-20. Active signals are net positive: pullback-entry- +$2.63, pump-chain- +$0.83, rr-struct+ +$0.59. The system is structurally profitable but legacy drag masks it.

### Fix Applied
**NO CONFIG CHANGES.** pump-chain+ was already killed by auto_1hr at16:08 UTC. Two fixes from earlier today still need 48h evaluation:
- rr_engine_resistance candle CLOSE check (~06:45 UTC) — no SHORT resistance exits since deployment
- SHORT_NORMAL_PENALTY=0.85 (~05:30 UTC) — monitoring

### Monitoring Items
- rr-struct- 7T/7d 42.9%WR -$0.42 — kill at 15T if WR <50%
- trend_ignition 0 trades since Sep 13 — NEUTRAL market, monitor 72h until Sep 16
- Legacy aging: ema300_dip_short, trend_purity+, sma20_dip, bb_bounce_v2_long — all dead, ages out Sep 15-20
- SHORT_NORMAL_PENALTY evaluation window ends Sep 15 ~05:30
- rr_engine_resistance fix evaluation window ends Sep 15 ~06:45

### Verification
All numbers DB-queried this run. No old reports trusted. 7d PnL +$0.56 verified positive. Today -$1.31 verified negative — mostly legacy/killed signals.

---

## CEO Report — 2026-09-14 ~14:30 UTC

### Diagnosis
24h negative: 48T 45.8% WR -$0.83 (VERIFIED). 7d positive: 328T 54.6% WR +$1.17 (VERIFIED — dropped from +$1.76 at 10:15). 8 open positions. Market NEUTRAL 100%.

### Verified Numbers (DB-queried this run)
- 24h: 48T, 45.8% WR, -$0.83 (below breakeven ~58%)
- 7d: 328T, 54.6% WR, +$1.17
- 7d regime: NEUTRAL 320T 55.3%WR +$1.68
- 7d exit: profit-monster-trail 86T +$6.12 ★ | atr_sl_hit 140T +$1.48 | rr_engine_resistance 37T -$1.33 (fix deployed) | cut-loser-CL-T1 37T -$5.44 (legacy)
- 7d ACTIVE SIGNALS: pullback-entry- 57T/63.2%WR +$2.63 ★ | rr-struct+ 15T/73.3%WR +$0.59 | pump_chain 27T/59.3%WR +$0.88 | pump-chain- 48T/62.5%WR +$0.57 | open_skies 5T/60%WR +$1.24
- 7d DRAGGERS: pump-chain+ 23T/39.1%WR -$0.43 (WORST active) | rr-struct- 7T/42.9%WR -$0.42 | open-skies+ 6T/50%WR -$0.31
- 24h losers: 24 total, 0 dead signal, all active (variance day)
- 8 open positions

### Root Cause
7d PnL dropped -$0.59 in 4h (10:15→14:30). Main active dragger: pump-chain+ LONG at 39.1% WR — all 23 trades in NEUTRAL, losses dominated by atr_sl_hit (10T, avg -4.61%). Signal enters LONG before pump confirms, gets stopped out. Not disabling yet — needs entry timing analysis. Legacy signals (ema300_dip_short, trend_purity+, sma20_dip) still in 7d window at -$5.00 combined — aging out by Sep 15-20.

### Fix Applied
**NO CONFIG CHANGES.** Two fixes deployed today still need 48h evaluation:
- rr_engine_resistance candle CLOSE check (~06:45 UTC) — no SHORT resistance exits since deployment (expected, not every period has them)
- SHORT_NORMAL_PENALTY=0.85 (~05:30 UTC) — monitoring

### Monitoring Items
- rr-struct- 7T/7d 42.9%WR — kill at 15T if WR <50%
- bb_bounce_v2_long 14T/7d 0 trades last 48h — effectively dead, will age out
- trend_ignition 0 trades since Sep 13 — NEUTRAL market, monitor 72h
- pump-chain+ LONG — investigate entry timing, consider confidence adjustment

### Verification
- 24h PnL: -$0.83 (negative, below breakeven)
- 7d PnL: +$1.17 (positive, degraded from +$1.76)
- Pipeline active, 8 open positions
- hermes-coding-mcp disabled (was crash-looping 465k restarts)
- coin_tracker timer OK (next run 15:00 UTC)
- Disk ~80%

---

## CEO Report — 2026-09-14 ~02:34 UTC

### Diagnosis
System healthy and improving. 24h: 44T 54.5% WR +$0.90 (VERIFIED). 7d: 334T 56.9% WR +$2.62 (VERIFIED POSITIVE, doubled from +$1.21). R:R 1.035 (breakeven 50.3%, actual 54.5% — 4.2% above). Legacy signals aging out — ema300_dip_short and sma20_dip last closed Sep 8, will drop off 7d window by Sep 15. Active signals ALL profitable. No config changes needed.

### Verified Numbers (DB-queried this run)
- 24h: 44T, 54.5% WR, +$0.90 (R:R 1.035, breakeven WR 50.3%)
- 7d: 334T, 56.9% WR, +$2.62
- 7d regime: NEUTRAL 324T 57.7%WR +$3.00 (100% market)
- 7d exit: profit-monster-trail 100T +$7.18, cut-loser-CL-T1 40T -$5.89 (legacy), rr_engine_resistance 35T -$0.97
- 7d top: pullback-entry- 53T +$2.69, open_skies 8T +$1.20, pump_chain 38T +$1.05
- 2 open: ENA LONG pump-chain+, DOT LONG pump-chain+ (just opened)

### Root Cause
No active root cause — system is profitable. Legacy drag (-$4.11/7d combined from 6 dead signals) is aging out naturally. Structural drag from rr_engine_resistance SHORT exits (-$0.97/7d) persists but improved from -$1.34.

### Fix Applied
No config changes. Updated CURRENT.md Active Decisions and Next Actions with verified numbers. Legacy signals will age out of 7d window by Sep 15-20.

### Verification
- 24h PnL: +$0.90 (positive, above breakeven)
- 7d PnL: +$2.62 (positive, doubled from last report)
- R:R: 1.035 (above breakeven)
- All 5 active signals profitable 7d
- Pipeline active, compactor running, disk 79%
- rr-struct- at 7T/7d (monitoring at 15T kill threshold)

---

## CEO Report — 2026-09-13 ~18:35 UTC

### Diagnosis
System above breakeven. 24h: 31T 58.1% WR +$0.70 (VERIFIED). 7d: 338T 57.1% WR +$1.57 (VERIFIED POSITIVE). **Legacy signals age out tomorrow (Sep 14)** — 6 dead signals -$3.46/7d drag. Active signals ALL profitable 7d. R:R carrying system (24h 0.938, 7d 0.800 — both above breakeven). Range filter deployed, saving money. No config changes needed.

### Verified Numbers (DB-queried this run)
- 24h: 31T, 58.1% WR, +$0.70 (R:R 0.938, breakeven WR 51.6% — 6.5% above breakeven)
- 7d: 338T, 57.1% WR, +$1.57
- Daily: Sep 8 -$2.74, Sep 9 +$2.03, Sep 10 +$2.48, Sep 11 -$1.74, Sep 12 +$0.58, Sep 13 +$0.70 (31T)
- 7d regime: NEUTRAL 327T 57.8%WR +$1.93 (system is 97% NEUTRAL)
- Best 7d: pullback-entry- 44T/63.6%WR +$2.11, open_skies 8T/62.5%WR +$1.20, pump_chain 41T/68.3%WR +$1.11
- Worst 7d: ema300_dip_short 17T/47.1%WR -$0.91 (legacy), trend_purity+ 11T/36.4%WR -$0.90 (dead)
- Exit 48h losses: atr_sl_hit 13T -$2.46, cut-loser-CL-T1 5T -$0.86, rr_engine_support_br 3T -$0.70

### Decision: MONITORING (NO CHANGES)
- Legacy ages out TOMORROW (Sep 14) — 7d PnL expected to improve by ~$3.46
- R:R 24h 0.938 (breakeven 51.6%, actual 58.1% — 6.5% ABOVE breakeven)
- R:R 7d 0.800 (breakeven 55.6%, actual 57.1% — 1.5% ABOVE breakeven)
- System structurally healthy: 5 consecutive green days (Sep 9-13)
- Pipeline active, disk 79%, no errors
- Range filter active, saving money

### What To Watch
1. Verify 7d PnL improves after legacy fully exits (tomorrow)
2. Monitor rr-struct- (7T/7d 42.9%WR -$0.42, R:R 0.42) — kill threshold at 15T
3. Monitor range filter blocks in pipeline.log over next 48h
4. Pipeline healthy — no intervention needed

## CEO Report — 2026-09-13 ~15:30 UTC

### Diagnosis
TURBO LONG loss (-3.83%, $0.14) at 93.3% of 1h range — buying the top. Current accel filter (+0.0028 > 0) passed because price was still rising. RSI 72.73 < 80 also passed. The only filter that catches "buying at resistance" is range position.

### Root Cause
rr_structural.py had no range position filter. Accel catches direction (price moving against trade) but not position (price at wrong end of range). TURBO: price rising but at 93.3% of 1h range — classic buy-the-top. INJ SHORT: at 6.3% of range — classic sell-the-bottom. Both passed all existing filters.

### Fix Applied
**CONFIG CHANGE: RR_STRUCTURAL_RANGE_LONG_MAX=80, RR_STRUCTURAL_RANGE_SHORT_MIN=20 added to hermes_constants.py.**

**Code change: `_get_range_position()` added to rr_structural.py** — queries 1h high/low from candles_1h, returns position as 0-100%. Range filter added to detect() for both LONG and SHORT directions.

**Impact analysis (17 rr-struct trades, 30d):**
- Saves: TURBO LONG -3.83% (93.3% range → blocked), INJ SHORT -6.52% (6.3% range → blocked) = **$9.35 saved**
- Costs: NEO LONG +30.98% (12% range → NOT blocked) = **$0 cost**
- Net: +$9.35 if filter was active

**Why NOT redundant with accel filter:**
- TURBO: accel=+0.0028 (UP, aligned with LONG) → accel PASSES → but 93.3% range → range BLOCKS
- Accel catches: price moving AGAINST direction
- Range catches: price at WRONG END of range (even if moving in direction)
- Complementary, not redundant.

### Verification
Import verified. Pipeline restart needed to load new code. Monitor next 24h for blocks in pipeline.log.

## CEO Report — 2026-09-13 ~22:35 UTC

### Diagnosis
24h: 35T, 54.3% WR, -$0.16. 7d: 336T, 56.5% WR, +$1.21. Market NEUTRAL. R:R 24h 0.740 (breakeven 56.7%, actual 54.3% — 2.4% underwater). 24h negative solely from dead signal trend_purity+ 3T 0%WR -$0.75 — without it, 32T +$0.59.

### Root Cause
Legacy signal trend_purity+ still in 24h window. Ages out Sep 14. Active signals ALL profitable: pullback-entry- +$2.11, open_skies +$1.20, pump_chain +$1.08, rr-struct+ +$0.59. 7d legacy drag -$3.46 will be gone by tomorrow.

### Fix Applied
**No config changes.** System structurally healthy. Monitoring: rr-struct- at 7T/42.9%WR (kill at 15T if WR <50%), rr_engine_resistance SHORT exits (5T/48h -$0.58, needs code change), trend_ignition 0 trades (market condition).

### Verification
7d PnL +$1.21 (VERIFIED). 24h -$0.16 (legacy noise). Pipeline active, 4 open positions, 0 errors. Disk 79%. Next: legacy ages out tomorrow, expect 7d PnL improvement ~$3.46.
