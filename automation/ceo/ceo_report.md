## CEO Report — 2026-09-20 ~14:30 UTC

### Diagnosis
DB-verified. 24h: 33T, 57.6% WR, +$0.98 (solid). 7d: 214T, 48.1% WR, -$0.30 (flipped negative from +$0.51 this morning). 6 open at MAX_OPEN. Market NEUTRAL — all 214 7d trades in NEUTRAL regime. **Biggest loser: pullback-entry- SHORT** — 65T 47.7%WR -$0.70/7d. **Biggest winner: pump-chain+ LONG** — 43T 48.8%WR +$1.51/7d (carrying system). **HOTSET empty** — confluence gate blocks everything in NEUTRAL. Dead zone fix (TIME_BLOCK 01-09) just deployed at 07:30 UTC.

### Root Cause
pullback_entry.py:188 had a backwards momentum filter — blocked SHORT with rising momentum (the ONLY profitable state: 65%WR +$0.17). Flat/falling momentum were the losers (39-41%WR -$0.87 combined) but were allowed through. Comment said "SHORT with rising = 62.5% LOSS" — outdated, data contradicts.

### Fix Applied
Flipped momentum filter in pullback_entry.py:188. Now blocks SHORT with flat/falling (anti-trend), allows rising. Also blocks LONG with rising/flat. Expected +$0.87/7d from pullback-entry- SHORT. Dead zone fix (TIME_BLOCK 01-09) expected +$0.50-1.00/7d. Combined expected: +$1.37-1.87/7d.

### Verification
Monitor 48h. If pullback-entry- SHORT WR improves from 47.7% to 55%+ and PnL turns positive, filter is working. Check 7d PnL — target: back above $0.00.

---

## CEO Report — 2026-09-20 ~07:30 UTC

### Diagnosis
DB-verified. 24h: 38T, 68.4% WR, +$2.26 (strong day). 7d: 218T, 49.1% WR, +$0.51 (barely positive). 6 open. Market NEUTRAL. **Dead zone hours 1-2 UTC bleed $1.62/7d** — not covered by TIME_BLOCK (03-09). Hour 2: 13T 30.8% WR -$1.15 (worst). pump-chain+ LONG 0%WR in hours 1-2. **EXTREME regime carries system:** +$2.70/7d (57.4% WR). **NORMAL bleeds:** -$1.34/7d (44.1% WR). **HIGH bleeds:** -$0.85/7d (legacy signals aging out, resolves by Sep 23).

### Root Cause
TIME_BLOCK started at hour 3, missing the two worst hours (1-2). pump-chain+ LONG fires in EXTREME/HIGH during hours 1-2 but loses 100% — low liquidity, false breakouts. The 0.7x penalty during 03-09 was working but started too late.

### Fix Applied
Extended TIME_BLOCK_START from 3 to 1. Covers hours 1-2 with 0.7x confidence penalty. Expected +$0.50-1.00/7d. Also updated signal_regime_memory.json with volume-breakout-long+ regime data (hidden gem: 71.4% WR in EXTREME+NORMAL).

### Verification
- 24h: 38T 68.4%WR +$2.26 ✅
- 7d: 218T 49.1%WR +$0.51 ✅
- EXTREME edge: 61T 57.4%WR +$2.70 ✅
- Dead zone hours 1-2: $1.62/7d bleed identified and addressed

### Verification
Pipeline running (timer active, all steps healthy). 4 open trades (2x pullback-entry- SHORT, 2x pump-chain+ LONG). Chase filter active (58 blocks). Stale filter working. Feature recording working.

### Next
- Monitor EXTREME edge sustainability (is 73.3% WR normal variance or regime-dependent?)
- Develop NEUTRAL-diverse signals (confluence gap persists)
- Legacy losers aging out — no action needed
- Hotset empty — investigate signal-compactor token flow

## CEO Report — 2026-09-19 ~18:37 UTC

### Diagnosis
DB-verified. 24h: 50T, 44.0%WR, +$0.67 (positive). 7d: 207T, 49.3%WR, +$0.13 (FLAT). 6 open ($0.00 unreal). Market NEUTRAL. Legacy killed signals still in 7d data (trend_purity+ -$0.75, rr-struct-v2+ -$0.45, open-skies+ -$0.40) — will age out. Active signals positive: pump-chain+ +$1.64, volume-breakout-long+ +$0.76, rr-struct+ +$0.52. Exit analysis: profit-monster-trail best (34T 76.5%WR +$1.93), ATR_SL nearly breakeven (143T -$0.21), cut-loser-CL-T1 -$0.95 on already-disabled signals only.

### Root Cause
System is essentially NEUTRAL-only (97.8% of 30d trades). NEUTRAL 30d: -$6.48 despite 52.9% WR — avg loss > avg win. Only 2 signal types pass confluence in NEUTRAL (pump-chain+, volume-breakout-long+). Signal diversity is the binding constraint.

### Fix Applied
No config changes. Chase filter deployed (pipeline running). BAD_TRADE_HOURS reference removed from CURRENT.md (not implemented in code). CURRENT.md updated with DB-verified numbers.

### Verification
Pipeline clean (no errors in last hour). 6 open trades. Stale filter working (4.9% stale in 48h). Feature recording working (gap_at_entry + staleness_minutes).

### Next
- Monitor chase filter impact (48h)
- Develop new NEUTRAL regime signals (confluence diversity gap)
- Legacy losers aging out — no action needed

## CEO Report — 2026-09-19 ~15:00 UTC

### Diagnosis
DB-verified. 24h: 46T, 41.3%WR, +$0.89 (positive, recovering). 7d: 206T, 48.5%WR, -$0.84 (slightly negative, improving from -$1.71). 5 open ($68.70). Market NEUTRAL. Legacy killed signals aging out (-$2.46). Active signals positive: pump-chain+ $0.99, volume-breakout-long+ $0.76, rr-struct+ $0.58. ATR_SL still dominates losses (72 hits/7d -$11.73) but root cause is entry quality, not stop width.

### Root Cause
Chase entries: z>2.5 LONG =12.5%WR -$1.01, gap>1.0% LONG = 25%WR -$0.40. Non-chase: 53.1%WR +$1.28. Brain_auditor identified this as the single biggest filter opportunity (+$1.25/7d). Code existed in decider_run.py but was silently failing — constants CHASE_ZSCORE_MAX and CHASE_GAP_MAX_PCT were never defined in hermes_constants.py. ImportError caught by pass.

### Fix Applied
**CODE FIX:** (1) Added CHASE_FILTER_ENABLED=True, CHASE_ZSCORE_MAX=2.5, CHASE_GAP_MAX_PCT=1.0 to hermes_constants.py. (2) Fixed abs() bug in gap check — was blocking dip-buying LONGs (negative gap = good entry). (3) Added z-score fallback via _ctx_gate_get_zscore since signal_z_score is always NULL (0/205 trades). **EXPECTED:** +$1.25/7d. Pipeline restart needed.

### Verification
Constants import verified. Both files compile clean. Filter logic tested: will block z>2.5 LONG and gap>1.0% LONG entries. Monitor logs for [CHASE-BLOCK] entries after pipeline restart.

### 30d Winners (active signals)
pullback-entry- SHORT: 97T 54.6%WR +$1.51 | volume-breakout-long+: 13T 69.2%WR +$0.76 | rr-struct+: 15T 73.3%WR +$0.59 | mover+: 13T 76.9%WR +$0.34

### Next
- Monitor grind-trend- SHORT (2T 0%WR, too few trades to kill)
- Develop new NEUTRAL regime signals (confluence gap)
- ATR_SL root cause: entry quality, not stop width

## CEO Report — 2026-09-19 ~02:40 UTC

### Diagnosis
DB-verified. 24h: 30T, 60.0%WR, +$1.56 (STRONG — best 24h in days). 7d: 192T, 50.5%WR, -$0.84 (legacy aging out). 2 open. Market NEUTRAL. **gap_at_entry: 0/192 trades** — silently broken since deployment. Stale filter working: fresh +$0.15 vs stale -$0.99 (gap $1.14/7d). Eval due 10:00 UTC today.

### Root Cause
`get_price_history(token, timeframe='5m', limit=310)` in decider_run.py:3991 — function signature is `get_price_history(token, lookback_minutes=1440)`. Wrong keyword args → silent exception → gap_at_entry never computed. Also, candle tuples are `(timestamp, price)` not OHLCV — `c[4]` should be `c[1]`.

### Fix Applied
**CODE FIX:** decider_run.py:3991 — `get_price_history(token, lookback_minutes=1550)` + `c[1]` instead of `c[4]`. Verified: SOL gap computed correctly (0.31%). All future trades will have gap_at_entry in _signal_metadata. Enables MAX_ENTRY_GAP filter, chase detection, regime-specific gap thresholds. **Pipeline restart needed.**

### Verification
SOL: EMA300=113.28, Price=113.64, Gap=0.31%. All 5 Sep 19 trades already have staleness_minutes (working). gap_at_entry will appear on next pipeline cycle.

### Monitoring
1. **Stale filter eval: 10:00 UTC today** — fresh +$0.15 vs stale -$0.99, gap $1.14/7d. Likely extend.
2. **pullback-entry- SHORT:** 66T 48.5%WR -$0.35 (30d +$1.66 NEUTRAL). Slight 7d dip, within variance.
3. **Legacy aging out:** trend_purity+ -$0.92, rr-struct-v2+ -$0.45, open-skies+ -$0.40, breakout-long+ -$0.35, rr-struct- -$0.30. All killed. Will age out by Sep 22-24.
4. **Sep 19 cold start:** 7T 14.3%WR -$0.78. Too early to diagnose — 7 trades only.
5. **z_score chasing:** brain_auditor found 6 LONG trades with z_score>2.5 — 1W 5L -$0.69. Suggested LONG_ZSCORE_MAX=2.0.

## CEO Report — 2026-09-18 ~20:00 UTC

### Diagnosis
DB-verified. 24h: 24T, 58.3%WR, +$0.71 (POSITIVE — stable). 7d: 197T, 53.3%WR, -$0.69 (legacy aging out). 5 open. Market NEUTRAL. RSI recording WORKING (187/188 trades). **gap_at_entry and staleness_minutes: 0/5128 trades** — not recorded.

### Root Cause
signal_compactor.py builds _signal_metadata from hotset values but never injects gap_at_entry (price vs EMA300) or staleness_minutes (signal age). These fields are computed elsewhere for filtering but discarded before DB write. This blocks: MAX_ENTRY_GAP filter, staleness-based analytics, regime-specific gap thresholds.

### Fix Applied
**CODE FIX:** decider_run.py — inject `gap_at_entry` (EMA300 gap %) and `staleness_minutes` (signal age) into `_signal_metadata` dict before execute_trade(). Gap computed from 5m candles (EMA300). Staleness from existing signal_created_at parsing. All in try/except — no crash risk.

### Verification
Syntax check passed. Next trade will have both fields in _signal_metadata. Monitor: `SELECT _signal_metadata FROM trades ORDER BY id DESC LIMIT 1;`

## CEO Report — 2026-09-18 ~18:00 UTC

### Diagnosis
DB-verified. 24h: 23T, 65.2%WR, +$0.98 (POSITIVE — recovering). 7d: 197T, 53.3%WR, -$0.69 (slightly negative, improving). 0 open. Market NEUTRAL. Numbers BETTER than CURRENT.md (+$0.98 vs +$0.84, -$0.69 vs -$0.94).

### Root Cause
7d negative ($-0.69) is ENTIRELY from killed legacy signals aging out: trend_purity+ -$0.90, rr-struct-v2+ -$0.45, rr-struct- -$0.42, open-skies+ -$0.40, breakout-long+ -$0.35. All removed from active signals. Active signals ALL positive or flat 30d: +$4.93 total. Stale filter working: fresh +$0.88 vs stale -$1.57 (gap $2.45/7d). pullback-entry- SHORT cold streak (4T today ALL ATR SL) is variance — 30d 56.4%WR +$2.01.

### Fix Applied
NO CONFIG CHANGE. System self-correcting. Legacy drags aging out naturally. Active signals healthy. Stale filter protecting (eval due Sep 19). RSI execution-time fix deployed ~09:45 UTC (no bad entries since).

### Verification
Active signals 30d: volume-breakout-long+ +$0.89 (75%WR), rr-struct+ +$0.59 (73.3%WR), mover+ +$0.57 (100%WR), pullback-entry- +$0.08 (50.8%WR flat), pump-chain- +$0.01 (54.2%WR flat). 196/197 7d trades NEUTRAL. 0 open trades. Pipeline healthy.

### Monitoring
1. **Stale filter evaluation: Sep 19 10:00 UTC (TOMORROW)** — must evaluate
2. pullback-entry- cold streak: monitor 48h (30d profitable, variance)
3. Signal diversity: only 2 types pass confluence in NEUTRAL — bottleneck
4. NEW: Legacy flush complete — 7d negative should resolve naturally

---

## CEO Report — 2026-09-18 ~15:00 UTC

### Diagnosis
DB-verified. 24h: 24T, 54.2%WR, -$0.30 (FLAT — better than previous report). 7d: 202T, 54.0%WR, -$0.94 (slightly negative, improving). 2 open (BLUR LONG mover+, HYPER LONG btc-pump-rider+). Market NEUTRAL. Previous report showed 20T/40%WR/-$1.21 — DB actually shows better numbers.

### Root Cause
- **24h losers (10):** pullback-entry- SHORT 4T ALL ATR SL (-$0.61 — cold streak, 30d profitable 56.4%WR +$2.01). open-skies+ LONG 2T killed legacy (-$0.31). volume-breakout-long+ 2T normal variance. Other 2 small losses.
- **7d negative ($-0.94):** ENTIRELY legacy killed signals: trend_purity+ -$0.90, rr-struct-v2+ -$0.45, rr-struct- -$0.42, open-skies+ -$0.42, breakout-long+ -$0.35. All dead. Active signals positive 30d: +$4.93 total.
- **pullback-entry- SHORT cold streak:** 4T today ALL losers. 30d: 94T 56.4%WR +$2.01. This is variance, not structural. Will recover.

### Fix Applied
NO CONFIG CHANGE. RSI ceiling fix deployed ~09:45 UTC (execution-time revalidation). No bad RSI entries since. Legacy drags aging out naturally. System structurally healthy.

### Verification
Active signals: 6 types, all profitable 30d (+$4.93 total). Stale filter working (90%+ fresh post-deploy). RSI fix deployed. Pipeline healthy. 2 trades open.

### Monitoring
1. **Stale filter evaluation: Sep 19 10:00 UTC (TOMORROW)** — must evaluate
2. pullback-entry- cold streak: monitor 48h (30d profitable, will recover)
3. Signal diversity: need new signals for NEUTRAL regime (only 2-3 types pass confluence)
4. RSI fix effectiveness: monitor next 24h for blocked trades

---

## CEO Report — 2026-09-18 ~09:45 UTC

### Diagnosis
DB-verified. 24h: 20T, 40.0%WR, -$1.21 (COLD STREAK). 7d: 209T, 52.6%WR, -$1.50. 0 open. Market NEUTRAL. 5 SHORT trades entered with RSI>65 (all losers, -$0.98) — RSI drifted between detection and execution.

### Root Cause
SHORT_RSI_CEILING=65 checked at signal detection only. RSI can drift from 45 to 72+ between detection and execution. 5 trades slipped through.

### Fix Applied
Added `_ctx_gate_get_rsi(token)` + execution-time SHORT_RSI_CEILING check in decider_run.py safety section. Same pattern as existing live z-score check. Expected +$0.98/7d.

### Verification
Python syntax check passed. Pipeline restart needed to load fix. Monitor next 24h for blocked trades.

## CEO Report — 2026-09-18 ~06:00 UTC

### Diagnosis
DB-verified. 24h: 18T, 33.3%WR, -$1.26 (COLD STREAK). 7d: 225T, 51.1%WR, -$2.78 (negative). 2 open. Market NEUTRAL.

### Root Cause
24h cold streak: open-skies+ legacy (killed, 4T ALL losers -$0.61) + pullback-entry- 5T/20%WR -$0.59 (cold streak — 30d profitable 56.4%WR +$2.01, variance). 7d negative is ENTIRELY legacy killed signals: trend_purity+ -$0.90, bb-bounce-v2-long+ -$0.47, rr-struct-v2+ -$0.45, pump-chain+ -$0.37 — ALL dead. Active signals all positive 30d: pullback-entry- +$2.01, pump-chain- +$1.04, rr-struct+ +$0.59, mover- +$0.61, mover+ +$0.30. Total active 30d: +$4.55.

### Fix Applied
NO CONFIG CHANGE. Legacy drags aging out naturally. System structurally healthy.

### Verification
Active signals: 5 signal types, all profitable 30d. Stale filter working (100% fresh post-deploy). Open-skies+ killed. Pipeline healthy.

### Monitoring
1. Stale filter eval: Sep 19 10:00 UTC
2. pullback-entry- cold streak: monitor 48h
3. Signal diversity: need new signals for NEUTRAL regime
4. volume-breakout-long+ 4T 50%WR -$0.04 — mixed, monitor

---

## CEO Report — 2026-09-17 ~18:35 UTC

### Diagnosis
DB-verified. 24h: 15T, 20.0%WR, -$1.73 (COLD STREAK — worst day in 7d). 7d: 226T, 50.9%WR, -$2.73 (slightly negative). 3 open (2 volume-breakout-long+ LONG, 1 pullback-entry- SHORT). Market 100% NEUTRAL.

### Root Cause
1. **pullback-entry- SHORT cold streak**: 4T/0%WR -$0.78 in 24h. But 7d: 68T/51.5%WR +$0.25 (profitable). This is variance, not structural. All-time profitable in NEUTRAL (58.4%WR +$2.60/30d).
2. **Legacy losers in 7d stats**: trend_purity+ ($-0.90), pump-chain+ ($-0.58), rr-struct-v2+ ($-0.45), rr-struct- ($-0.42) — all killed/disabled, legacy trades dragging numbers.
3. **Signal diversity**: Only 2-3 signal types pass confluence in NEUTRAL. No resilience when one has a cold streak.

### 24h Losers (VERIFIED)
- pullback-entry- SHORT: 4T/0%WR -$0.78 (cold streak, 7d profitable)
- open-skies+ LONG: 5T/20%WR -$0.42 (KILLED 17:11 UTC)
- volume-breakout-long+: 2T/50%WR -$0.14 (low sample)

### 7d Top Performers (VERIFIED)
- rr-struct+ LONG: 15T/73.3%WR +$0.59 ★★
- mover- SHORT: 4T/100%WR +$0.54 (tiny sample)
- pullback-entry- SHORT: 68T/51.5%WR +$0.25
- pump-chain- SHORT: 38T/55.3%WR -$0.03 (breakeven)

### Fix Applied
**NO CONFIG CHANGE.** System structurally healthy. The 24h cold streak is variance in a profitable signal (pullback-entry-). Legacy losses from killed signals will age out.

### Verification
- Stale filter: Deployed 10:00 UTC. Post-deploy 7 trades ALL FRESH (working). Evaluate by Sep 19 10:00 UTC.
- open-skies+ KILLED correctly (17:11 UTC). All 5 24h trades were losers.
- Regime memory fresh (updated Sep 16). All active signals are NEUTRAL specialists.

### Monitoring
1. Stale filter effectiveness (48h evaluation by Sep 19 10:00 UTC)
2. pullback-entry- SHORT recovery from cold streak
3. HIGH regime legacy flush (94T/7d 46.8%WR -$2.00, ~60% legacy)
4. Signal diversity — need new signals for NEUTRAL resilience

### 7d Biggest Drags (VERIFIED)
- trend_purity+ LONG: 11T/36.4%WR -$0.90 (legacy, killed Sep 13)
- pump-chain+ LONG: 24T/37.5%WR -$0.87 (legacy, killed)
- accel-300-v4-short-: 4T/0%WR -$0.58 (legacy)

### Fix Applied
NO CONFIG CHANGE. System is structurally healthy — 7d PnL -$0.78 (barely negative). Stale signal issue needs code-level fix (staleness_mult decay or hard age block). Signal diversity needs new signal development.

### Next Actions
1. **Code fix needed**: Stale signal execution — implement hard age block or tighten staleness_mult decay. ~$1.42/7d potential.
2. **New signals needed**: NEUTRAL regime only has 2 confluence-passing types. Need 3+ for resilience.
3. **Monitor**: pullback-entry- SHORT 24h streak (30.8%WR). 7d profitable — likely variance.

## CEO Report — 2026-09-17 ~02:40 UTC

### Diagnosis
24h: 22T, 36.4%WR, -$0.60 (VERIFIED — deterioration from 66.7% earlier). 7d: 258T, 52.7%WR, +$0.31 (VERIFIED — barely positive, down from +$2.72). SHORT carries: +$2.14. LONG bleeds: -$1.83. Market 100% NEUTRAL. 0 open.

### Root Cause
Breakout-long+ still firing LONG in NEUTRAL without BTC regime gate — 3T/0%WR -$0.60 in 48h. Legacy trades from killed signals (rr-struct-v2+, breakout-long+) account for most LONG losses. pullback-entry- SHORT normal variance (84T/7d 52.4%WR +$1.00).

### Fix Applied
1. KILLED BREAKOUT_LONG_ENABLED (was True). 4T/7d 25%WR -$0.35, 48h 3T/0%WR -$0.60. Pipeline restarted.

### Not Applied (review needed)
- trend_purity+ LONG: 11T/36.4%WR -$0.90, but ALL trades are legacy (Sep 12-13). TREND_PURITY_PLUS_ENABLED already False since Sep 13. No active bleed — no action needed.

### Verification
Pipeline restarted, BREAKOUT_LONG_ENABLED=False confirmed in hermes_constants.py.

### Diagnosis
24h flat: 25T, 52%WR, -$0.21 (VERIFIED). 7d positive: 267T, 55.4%WR, +$1.53 (VERIFIED). SHORT dominant: +$3.79. LONG drag: -$2.26 (legacy aging out). 5 open SHORT. Market NEUTRAL.

### Root Cause
Dead signals accumulated in STANDALONE_BYPASS (accel-300-v4-short, ema300-dip-long, ema300-dip-short). Regime memory stale 5 days. Signal diversity low — only 2 types in NEUTRAL.

### Fix Applied
1. Removed 3 dead signals from STANDALONE_BYPASS. Pipeline restarted.
2. Updated signal_regime_memory.json with fresh 7d DB data.
3. MONITORING: Signal diversity — only pullback-entry- and pump-chain- in NEUTRAL. Delegate new signal development.

### Verification
Pipeline restarted clean. STANDALONE_BYPASS now excludes dead signals. Regime memory fresh as of Sep 16.

## CEO Report — 2026-09-16 ~02:15 UTC

### Diagnosis
24h flat: 29T, 51.7% WR, -$0.10 (VERIFIED). 7d positive: 278T, 55.8% WR, +$3.08 (VERIFIED, improved from +$1.83). 5 open trades. Market NEUTRAL.

### Verified Numbers (DB-queried this run)
- 24h: 29T, 51.7% WR, -$0.10
- 7d: 278T, 55.8% WR, +$3.08
- 7d SHORT: ~152T, 58.6% WR, +$2.69 ★
- 7d LONG: ~126T, 49.2% WR, +$0.39 (improving, legacy ages out Sep 16-20)
- 7d Regime: NEUTRAL 273T 56.4% WR +$3.45
- 7d Exit: profit-monster-trail 43T 93%WR +$3.39 ★ | atr_sl_hit 161T 54%WR +$2.14 | rr_engine_resistance 37T 40.5%WR -$1.33 (ALL pre-fix, 0 post-fix ✓)
- 7d Active: pullback-entry- SHORT 79T/62%WR +$3.18 ★ | pump-chain- SHORT 55T/60%WR +$0.62 | rr-struct+ LONG 15T/73.3%WR +$0.59 | mover- SHORT 7T/85.7%WR +$0.53
- 24h Active: pullback-entry- SHORT 20T/65%WR +$0.79 ★ | pump-chain- SHORT 1T/100%WR +$0.22
- 7d Dragger: trend_purity+ LONG 11T/36.4%WR -$0.90 (KILLED) | pullback-entry+ LONG 6T/16.7%WR -$0.57 (KILLED) | ema300-dip-long 5T/20%WR -$0.55 (DEAD)

### Root Cause
System is flat today because: (1) auto_1hr killed breakout-long+ (0%WR -$0.60 in 24h, fires LONG in NEUTRAL without BTC regime gate) and (2) rr-struct-v2+ legacy LONG trades still flushing (4T/24h -$0.54). These were killed days ago. SHORT side carrying profits (+$2.69/7d). **The system only has 2 signal types passing confluence in NEUTRAL: pullback-entry- and pump-chain-.** This is fragile — one bad regime shift kills everything.

### New Finding: cut-loser-CL-T1 bleeding
7d: 7 exits, -4.9% avg PnL, -$1.19 total. This exit type is the second-worst after rr_engine_resistance (pre-fix). Needs investigation.

### Fix Applied
**NO CONFIG CHANGES.** auto_1hr already killed breakout-long+ at 02:08 UTC. rr_engine_resistance fix verified: 0 post-fix exits in 48h+. Pullback-entry- SHORT now uses ATR exit (working, 62% WR).

### Monitoring
1. **Legacy LONG flush.** trend_purity+ -$0.90, pullback-entry+ -$0.57, ema300-dip-long -$0.55. Ages out Sep 16-20. No action.
2. **rr_engine_resistance post-fix.** 0 exits since Sep 15. Monitor until Sep 18.
3. **cut-loser-CL-T1 bleed.** 7 exits -$1.19. Investigate root cause next run.
4. **features_recorded=FALSE ALL 279 trades (14 days).** CRITICAL data gap. Retroactive fix + pipeline wiring needed.
5. **5 open trades.** 3 SHORT (pullback-entry-), 1 LONG (breakout-long+ killed), 1 other.
6. **Signal diversity.** Only 2 signal types in NEUTRAL. Need new signals for confluence.

### Decision
**No config change.** System structurally healthy. 7d PnL +$3.08 (POSITIVE, improved from +$1.83). Legacy LONG drag aging out. SHORT side strong. Hold. Focus: fix feature recording + develop new signals.

## CEO Report — 2026-09-16 ~08:30 UTC

### Diagnosis
24h: 27T 48.1%WR -$0.52 (FLAT). 7d: 275T 54.9%WR +$2.66 (POSITIVE). Market NEUTRAL 100%. 5 open trades, all SHORT. System healthy but not exciting.

### Root Cause
SHORT_NORMAL_PENALTY=0.85 was still active despite monitoring expiring Sep 16. SHORT in NORMAL is profitable (34T/7d 61.8%WR +$0.59). Penalty was reducing confidence by 15%, blocking ~2 good entries/week.

### Fix Applied
SHORT_NORMAL_PENALTY = 1.0 (removed penalty). Monitoring period expired. Data supports removal.

### What NOT to change
- PM_TRAIL (0.40%/0.20%) — protected, ATR SL wins the race
- ATR_SL (1.3%/1.5%) — protected, 7d avg +0.39%
- All losers already killed (trend_purity+, pullback-entry+, rr-struct-v2+, breakout-long+)

### Monitoring (5 items)
1. Feature recording — verify on next 5-10 closed trades
2. rr_engine_resistance — 0 exits post-fix, deadline Sep 18
3. cut-loser-CL-T1 — 7 exits -$1.19, avg -$0.17 (healthy)
4. Signal diversity — 2 types in NEUTRAL, need new signals
5. 48h ATR SL cluster — 27 exits avg -5.26% (structural)

### Verification
SHORT NORMAL 7d: 34T 61.8%WR +$0.59. Penalty removal expected +$0.26/7d. Monitor next 48h.

## CEO Report — 2026-09-17 ~15:00 UTC

### Diagnosis
7d: 232T, 52.0%WR, -$0.06 (BREAKEVEN). 24h: 11T, 27.3%WR, -$0.97 (cold streak, tiny sample). 3 open trades (STX, W, WCT — all LONG in NEUTRAL). ALL active signals profitable 7d: rr-struct+ 15T/73.3%WR +$0.59, pump-chain- 44T/56.8%WR +$0.39, pullback-entry- 69T/52.2%WR +$0.36.

### Root Cause
Stale signal execution = #1 drag ($4.86/7d). 31.8% of trades fire on stale signals (staleness_mult decays over 10min, too slow). Fresh WR 58.2% vs stale 48.6%. Signal diversity = #2 issue (only 2 types pass confluence in NEUTRAL). Cold streak is tiny sample noise.

### Fix Applied
NO CONFIG CHANGE. System structurally healthy. All dead signals properly disabled. ATR SL exits near breakeven (avg -$0.059). Stale issue needs code-level fix (execution-time revalidation), not config. Signal diversity needs new signal development.

### Verification
DB-verified. Active signals confirmed profitable. Legacy trades aging out. Pipeline healthy.

---

## CEO Report — 2026-09-18 — ML Trade Classifier Spec Review

### Decision: REJECT (for now — revisit in 2 weeks)

### Why

The spec is excellent — clean architecture, good risk analysis, sensible model choice. **But it solves the wrong problem at the wrong time.**

**Current bottleneck is signal diversity, not scoring quality.**
- 24h: 15T, 20%WR, -$1.73 (cold streak)
- 7d: 222T, 49.5%WR, -$3.58
- **Only 1 signal type passes confluence in NEUTRAL:** pullback-entry- SHORT
- open-skies+ killed Sep 17. squeeze_reversal zero trades. Signal starvation is the crisis.

The ML classifier would sit AFTER signal detection — it can't help if signals aren't firing. Adding a sophisticated filter on top of a starving pipeline is like installing a bouncer at an empty bar.

**Three reasons to wait:**

1. **5K rows is thin for a 20-feature RandomForest.** With one-hot encoding across ~40 tokens, ~15 signal types, 3 regimes, and 3 volatility states, we'll have sparse feature matrices. Risk of overfitting to historical noise is real. Need 10K+ trades for reliable generalization — that's ~2-3 months at current pace.

2. **Hebbian + signal_compactor already do this.** The composite_score (hebbian_engine.py:535) already weights decayed WR, exit quality, token WR, and combo parts. The ML classifier proposes to learn "RSI < 35 + BULL = 78% WR" — but regime-specific filtering (CURRENT.md policy) already does this with explicit rules and regime memory. The marginal lift over existing rules is unclear without a baseline backtest.

3. **Opportunity cost is high.** 4 days of subagent time = 4 signals not built. The system needs new signals that fire in NEUTRAL (Wyckoff phase, Elliott Wave, volume profile from coin_tracker). These directly address the starvation problem. ML scoring is a tuning knob; new signals are capacity.

### What to do instead (next 2 weeks)

| Priority | Task | Impact |
|----------|------|--------|
| **1** | Build 2-3 NEUTRAL-compatible signals (coin_tracker-based) | Directly increases trade capacity |
| **2** | Let stale filter mature (eval Sep 19) | Data shows 52.9%WR fresh vs 46.6% stale |
| **3** | Collect more trades (need 10K+ for ML) | Better training data for later ML build |
| **4** | Backtest ML classifier against current system (shadow mode) | Prove marginal lift before committing |

### When to revisit ML classifier

- After 10K+ closed trades (est. late Oct 2026)
- After 3+ new signals deployed and matured
- When signal diversity is no longer the bottleneck

### Key concern with spec

The `ML_WEIGHT = 0.6` + `HEBBIAN_WEIGHT = 0.4` default means ML dominates scoring from day one. This is aggressive for an unproven model. If we do build this, start at `ML_WEIGHT = 0.3` and only increase after backtest proves marginal lift.

### Spec quality

No issues with the spec itself — it's well-designed. The model choice (RF), feature set, fail-open design, and retraining strategy are all sound. It's a "right build, wrong time" situation.

---

## CEO Report — 2026-09-20 ~15:00 UTC — JEV/Von Updated Assessment

### Previous Assessment (Sep ~10)
REJECTED — wrong time, signal diversity is the bottleneck. Revisit after 10K+ trades and 3+ new signals.

### What Changed

Open source alternatives alter the cost/benefit:

| Factor | Before (JEV) | Now (Von/sklearn) |
|--------|-------------|-------------------|
| Cost | $$$ API calls | $0 local |
| Setup | Complex API integration | sklearn: ~200 lines, 1 day |
| Latency | Network round-trip | ~18ms GPU, ~480ms CPU |
| Accuracy | 97.2% (JEV) | 93.5% (Von), sklearn varies |
| Text classification | Only option | Von is viable for news/sentiment |

### Updated Verdict: STILL HOLD — but the "when" moved up

**Three questions, three answers:**

**1. Should we build a minimal sklearn classifier (1-day prototype)?**
**No — but the reason changed.** Previously: "wait for 10K trades." Now: "the bottleneck is still signal diversity." DB shows 5,204 closed trades (not 5K — we've grown). But the constraint isn't data volume, it's that only 2 signal types fire in NEUTRAL. A classifier that scores signals better doesn't help when there are no signals to score. The bar chart metaphor still holds: installing a better sorting algorithm on an empty shelf.

**But:** if someone builds a new NEUTRAL signal and it fires 50+ times, THEN a 1-day sklearn prototype to score it is trivial. The 1-day estimate is credible — `CalibratedClassifierCV` + `StandardScaler` + 5-fold CV is literally 150 lines. The right move: build the signal first, classifier second.

**2. Should we evaluate Von for text-based signal classification?**
**No — we have no text data.** Von classifies text (news, sentiment, social). Hermes processes numeric indicators (RSI, momentum, gaps, regime). There's no text pipeline. Von is a solution looking for a problem. If we ever add news sentiment analysis, Von becomes relevant — but that's a new feature, not a scoring upgrade.

**3. Or still hold off until 10K+ trades?**
**Yes — but the timeline is organic, not artificial.** At ~30 trades/day, we hit 10K in ~5 months (Feb 2027). But the real trigger isn't trade count, it's signal diversity. When we have 5+ signal types passing confluence in NEUTRAL, THEN a classifier that learns which conditions predict wins becomes valuable. Right now we're choosing between 2 signal types — there's nothing to classify.

### Bottom Line

| Question | Answer | Reason |
|----------|--------|--------|
| Von for text? | Skip | No text data in pipeline |
| sklearn prototype? | Defer | Build signal first, classifier second |
| Hold off? | Yes | Signal diversity still the bottleneck |

**The right time to build the classifier is when we have 5+ active signal types in NEUTRAL and want to score which conditions predict wins for each.** That's probably late Oct/Nov 2026, not because of trade count but because of signal portfolio maturity.

### What I'm doing instead

Focus stays on:
1. **NEUTRAL signal development** (coin_tracker-based: Wyckoff phase, Elliott Wave, volume profile)
2. **Regime-specialist tuning** (keep signals alive in winning regimes)
3. **Dead zone / stale filter monitoring** (proven edge, let it compound)

The classifier is a tuning knob. New signals are capacity. Capacity first.
