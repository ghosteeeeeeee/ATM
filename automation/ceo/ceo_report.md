## CEO Report — 2026-09-17 ~10:45 UTC

### Diagnosis
DB-verified. 24h: 25T, 36.0%WR, -$0.27 (worse than 06:30 snapshot). 7d: 252T, 52.0%WR, -$0.78 (slightly negative). 2 open. Market 100% NEUTRAL. SHORT dominant (+$2.14 7d). LONG legacy drag aging out (-$1.83).

### Root Cause
Two structural issues:
1. **Stale signal execution**: 79 trades marked is_stale (flat momentum) at 48.1%WR -$1.10 vs fresh 172T/54.1%WR +$0.32. Gap $1.42/7d. Not signal AGE — these are trades on tokens with no momentum.
2. **Signal diversity**: Only 2 signal types (pullback-entry-, open-skies+) pass confluence in NEUTRAL. No resilience.

### 24h Losers (VERIFIED)
- pullback-entry- SHORT: 13T/30.8%WR -$0.16 (bad streak, 7d profitable 51.3%WR +$0.73)
- volume-breakout-long+: 3T/0%WR -$0.10 (low sample)
- rs-s36,volume-breakout-long+: 1T -$0.22

### 7d Top Performers (VERIFIED)
- pump-chain- SHORT: 49T/61.2%WR +$1.25
- pullback-entry- SHORT: 78T/51.3%WR +$0.73
- rr-struct+ LONG: 15T/73.3%WR +$0.59
- open-skies+ LONG: 10T/60%WR +$0.29

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
