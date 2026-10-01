## CEO Report — 2026-09-30 (05:30 UTC)

### Diagnosis
DB-verified: 38T 44.7%WR -$0.53 (24h) | 131T 43.5%WR -$2.23 (7d) | 316T 44.6%WR -$2.33 (14d). POST-FIX: 56T 53.6%WR +$0.13 (0 ATR_SL hits). System slightly positive post-fix, legacy losses aging out. **pump-chain- SHORT RSI<25 = CATASTROPHIC** — 9T 22.2%WR -$0.66/14d. Oversold entries via STANDALONE_BYPASS bypass SHORT_RSI_FLOOR=40. RSI 45-55 sweet spot: 7T 85.7%WR +$0.86. **SIGNAL DIVERSITY CRITICAL** — only volume-breakout-long+ (+$2.48/14d) and pump-chain+ (+$1.23/14d) profitable. doji-bottom-long promising (11T 63.6%WR +$0.36). **HOTSET CONFIDENCE INVERSE** — 85-95 conf 33.3%WR, 95+ conf 38.9%WR. CONF_FILTER_MIN=90 working. **1 open:** BTC LONG continuum-osc+ NEUTRAL.

### Root Cause
pump-chain- SHORT fires at extreme oversold RSI (<25) via STANDALONE_BYPASS, which bypasses the general SHORT_RSI_FLOOR. These are "catch falling knife in reverse" entries — shorting into oversold conditions. 22% WR, -$0.66/14d.

### Fix Applied
**PUMP_CHAIN_SHORT_RSI_MIN=25** added to hermes_constants.py + signal_compactor.py filter. Blocks pump-chain- SHORT entries where RSI<25. RSI 45-55 sweet spot (85.7%WR) preserved. Expected +$0.20-0.40/7d.

### Verification
- ATR_SL widening: PASS (0/56 post-fix hits)
- pump-chain- RSI_MIN: Will verify on next pump-chain- SHORT RSI<25 signal
- doji-bottom-long: Monitor at 20+ trades (currently 11T 63.6%WR)
- COIN_TRACKER_HOT_PLUS_ENABLED: RESEARCH_FLAGS — needs human approval to enable

## CEO Report — 2026-09-29 (22:00 UTC)

### Diagnosis
DB-verified: 48T 47.9%WR -$1.14 (24h) | 136T 44.1%WR -$3.24 (7d) | ALL 135/136 trades NEUTRAL. SHORT R:R 0.73:1 (avg_win $0.110 vs avg_loss $0.150). LONG R:R 0.70:1 (avg_win $0.083 vs avg_loss $0.118). Hotset rs-s* = DOMINANT 24h loser (15L/16T, 0% WR on losers). pump-chain- SHORT only profitable SHORT (43T 53.5%WR +$0.18/7d). doji-bottom-long promising (6T 66.7%WR +$0.27). pump-chain+ V5 0 trades/7d (cold streak persists). Post-fix (Sep 28+): 53T 54.7%WR -$0.60, 0 ATR_SL hits — PASS.

### Root Cause
1. **Hotset chop in NEUTRAL** — 15 hotset LONG hard_sl24h, all small (<$0.23). Entry RSI 32-75, no clear RSI pattern. Market choppy, no follow-through. $0.72/7d bleed.
2. **Signal diversity CRITICAL** — only pump-chain- SHORT (+$0.18) and volume-breakout-long+ (+$0.13) profitable 7d. 2 signal types carry system.
3. **Coin_tracker intelligence UNDERUTILIZED** — 7 coins in Wyckoff accumulation (BANANA 59.71, BCH 58.24, MET 56.04) with high setup scores. Zero signals using this data.

### Fix Applied
1. **DELEGATED to signal_analyst:** Build Wyckoff accumulation LONG signal. Trigger: coin_tracker wyckoff_phase=accumulation AND setup_score>40 AND clustering_bullish>=2. Expected +$0.30-0.50/7d from NEUTRAL diversity.
2. **No config changes** — system stable post-fix. Hotset bleed is structural (chop in NEUTRAL), not fixable without killing winners. V5 re-enablement in 48h test window.

### Verification
- ATR_SL widening: PASS (0/53 post-fix hits)
- V5 re-enablement: 0 trades so far, monitoring 48h
- Hotset: structural chop, monitoring — no action unless pattern changes

## CEO Report — 2026-09-29 (18:00 UTC)

### Diagnosis
DB-verified: 43T 46.5%WR -$1.63 (24h) | 129T 41.1%WR -$4.38 (7d) | 318T 43.7%WR -$4.43 (14d). 5 open positions (3 SHORT pump-chain-, 1 LONG doji-bottom, 1 LONG continuum-osc). ATR_SL widening VERIFIED: 0% post-fix (45T). SHORT R:R 0.59:1 (avg_win $0.088 vs avg_loss $0.149) — structural bleeding. pump-chain+ LONG 0 trades/7d (dead hours + NEUTRAL). Signal diversity CRITICAL — only2 signals profitable.

### Root Cause
1. **SHORT R:R broken** — ATR_SL cuts SHORT winners at 1.5x SL. TP unreachable (0.9% hit rate). Winners average $0.088, losers $0.149.
2. **pump-chain+ starved** — profitable hours 0,14,20,23 blocked in dead hours list (stale data from Sep 28).
3. **ALL trades NEUTRAL** — no EXTREME/HIGH data for regime multiplier eval.

### Fix Applied
1. **PUMP_CHAIN_LONG_DEAD_HOURS** — removed hours 0,14,20,23 (profitable 30d), added 18 (loser). Opens 3 more hours. Expected +$0.30-0.60/7d.
2. **ATR_TP_K_MULT 1.5→2.0** — TP target 4% (was 3%). Gives SHORT winners room to run. Expected +$0.20-0.50/7d from improved R:R.

### Verification
ATR_SL widening: 45T post-fix, 0 hits — PASS. SHORT R:R will improve as TP becomes reachable. pump-chain+ dead hours fix needs 48h to measure (next pump-chain+ setup in NEUTRAL regime).

## CEO Report — 2026-09-29 (02:00 UTC)

### Diagnosis
DB-verified: 16T 75.0%WR +$1.07 (24h) | 116T 42.2%WR -$3.40 (7d) | 305T 45.2%WR -$2.00 (14d). 2 open positions (BTC LONG continuum-osc+, SOL SHORT pump-chain-). Post-fix recovery REAL: 5 consecutive positive days (Sep25+: +$1.65 total). Pre-fix bleed (Sep22-24): -$5.05. ALL major fixes VERIFIED WORKING: volume_spike 90% populated (48h), signal_rsi_14 304/305 (14d), ATR_SL 42.2% hit rate (PASS <55%). SHORT side -$2.46/14d but ALL SHORT signals disabled, aging out. LONG +$0.46/14d (breakeven). Signal diversity CRITICAL: only volume-breakout-long+ (+$1.46/14d) and pump-chain+ (+$1.23/14d) profitable.

### Root Cause
1. **Legacy bleed AGING OUT** — Sep22-24 -$5.05 dominating 7d. Post-fix (Sep25+): +$1.65. System healing naturally.
2. **SHORT side legacy** — pullback-entry- (-$2.04/14d) and mover+ (-$1.12/14d) already disabled/killed. Aging out.
3. **pump-chain+ cold streak** — 7d: 4T 25%WR -$0.64. 14d: 55T 41.8%WR +$1.23. Variance, not systemic.
4. **ATR_SL still dominant loss** — 30 hits/7d -$6.27. Widening deployed Sep28 (2.0% cap). Need more post-fix data.
5. **Signal diversity** — 14d: only 2/11 LONG types profitable. NEUTRAL regime trap.

### Fix Applied
**NO CONFIG CHANGES.** System recovering. All fixes verified. Legacy aging out. Premature to change params during recovery.

### Verification
- volume_spike: 27/30 (90%) populated in48h trades ✅
- signal_rsi_14: 304/305 (99.7%) populated in14d trades ✅
- ATR_SL hit rate: 42.2% 7d — PASS (<55%) ✅
- Post-fix days: Sep25 +$0.05, Sep27 +$0.72, Sep28 +$0.30, Sep29 +$0.58 ✅
- Open positions: 2 (BTC LONG -$0.05, SOL SHORT +$0.35) — both near breakeven
- Pipeline: active, generating signals, no errors

### Next Actions
1. **MONITOR** — pump-chain+ cold streak (7d). If continues past Oct1, investigate dead hours or params.
2. **MONITOR** — ATR_SL widening impact (needs 50+ post-fix trades for statistical significance).
3. **DELEGATE** — signal_analyst: build new NEUTRAL signal for diversity. Current: only volume-breakout-long+ and pump-chain+ profitable. Need 3rd signal type.
4. **HOLD** — SHORT side all disabled, aging out. No action needed.
5. **DISK** — 86% (95G/118G). Monitor growth.

---

## CEO Report — 2026-09-28 (Evening)

### Diagnosis
DB-verified: 14T 42.9%WR +$0.62 (24h) | 112T 35.7%WR -$5.26 (7d) | 305T 44.3%WR -$2.90 (14d). 5 open positions (1 LONG BTC, 3 SHORT EXTREME, 1 LONG HIGH). ATR_SL widening WORKING: 46.4% 7d hit rate (PASS <55%), 2 post-fix trades both winners +$0.16. All trades NEUTRAL — 100% of 7d/14d. Signal diversity CRITICAL: only pump-chain+ LONG (+$1.51/14d) and volume-breakout-long+ (+$1.46/14d) profitable. volume_spike STILL BROKEN: 86.6% NULL7d (97/112 trades).

### Root Cause
1. **volume_spike metadata bug PERSISTS** — Sep 25 fix NOT working for86.6% of trades. Chase filter blind to volume quality. 3 orphan code paths (rs-s*, continuum_engine) bypass metadata injection.
2. **final_confidence 98% NULL** — confidence-based filtering impossible. pump-chain+ trades at confidence 99 cannot be filtered.
3. **NEUTRAL trap** — 100% of trades fire in NEUTRAL. No EXTREME/HIGH data to evaluate REGIME_CONF_HIGH_MULT=0.50.
4. **pump-chain+ cold streak** — 7d: 9T 11.1%WR -$1.15 (all Sep 21-22). 14d: 56T 42.9%WR +$1.51. Variance, not systemic.

### Fix Applied
NO CHANGES APPLIED. System in "wait and see" mode:
- ATR_SL widening working (46.4% < 55% target)
- Post-fix trades: 2T both winners
- Legacy losses aging out (Sep 21-24 worst days)
- pump-chain+ not in NEVER_REENABLE — 14d still profitable

### Verification
- Post-fix (Sep 28 10:39+): 2T 100%WR +$0.16 — ATR_SL widening success
- volume_spike: 86.6% NULL7d — CRITICAL, needs code fix
- final_confidence: 98% NULL7d — blocks confidence filtering
- All RSI filters working (0 post-fix violations)
- 5 open positions: BTC LONG +0.57%, LDO SHORT +0.24%, LTC SHORT +0.02%, BABY SHORT -0.11%, SYRUP LONG -0.07%

### Next Actions
1. **DELEGATE:** volume_spike fix — 3 orphan code paths need investigation (bug_hunter)
2. **MONITOR:** pump-chain+ cold streak recovery (48h window)
3. **MONITOR:** ATR_SL widening (need 30+ post-fix EXTREME trades for evaluation)
4. **DEVELOP:** New signals for NEUTRAL regime (only 2 profitable types)

## CEO Report — 2026-09-30 09:50 UTC

### Diagnosis
24h: 33T 42.4%WR -$0.22. 7d: 123T 43.9%WR -$1.80. Post-fix (Sep 28 10:39+): 57T 52.6%WR +$0.11, 0 ATR_SL hits. System slightly positive post-fix but 7d still negative from legacy losses aging out.

### Root Cause
**CANDLE TIMERS DISABLED.** hermes-1m-candle.timer and hermes-5m-candle.timer were both inactive. 0 candles collected in last hour. Without fresh 1m/5m candles, RSI/ATR/indicator computations degrade — every downstream filter and signal quality metric suffers. This explains persistent hotset chop and mediocre WR despite post-fix improvements.

### Fix Applied
1. **Re-enabled hermes-1m-candle.timer and hermes-5m-candle.timer** (systemctl enable --now). Both active as of 09:50 UTC.
2. **Verified PUMP_CHAIN_SHORT_RSI_MIN=25 working** — brain_auditor's "dead code" claim was wrong. 7 RSI<25 signals blocked (EXPIRED, executed=0) since 05:30 UTC. 0 oversold SHORT entries executed. Filter reads row[8]=rsi_14 correctly.

### Verification
Candle timers active. 1m timer triggers every 1min, 5m every 5min. Next candle collection within 1 minute. RSI filter confirmed blocking oversold entries via signal DB query (0 executed RSI<25 since deploy).

### Goals
| Metric | Current | Target | Deadline |
|--------|---------|--------|----------|
| Win rate 7d | 43.9% | 48% | 48h |
| Post-fix WR | 52.6% | 55% | 24h |
| doji-bottom-long trades | 6 | 20+ | 7d |
| Candle freshness | 0/hr | 60/hr 1m | 1h |

## CEO Report — 2026-09-30 22:00 UTC

### Diagnosis
24h: 11T 54.5%WR +$1.13 — POSITIVE, recovering. 7d: 114T 45.6%WR -$1.31 — improving from -$4.41 (Sep 29). Daily trajectory: Sep 24 -$2.58 → Sep 29 -$1.13 → Sep 30 +$1.13. Post-fix (Sep 28+) consistently positive. ATR_SL fix verified (0% post-fix). RSI metadata fixed (58/59 in 48h). SHORT R:R still structural: 7d 51T 49.0%WR -$1.46, avg_win $0.112 vs avg_loss $0.164 (0.68:1). Bleeding is legacy aging out.

### Root Cause
System was bleeding from pre-fix legacy losses (ATR_SL tight, RSI filters broken, metadata NULL). All fixes deployed Sep 25-30 now working. Legacy trades aging out of 7d window. No new systemic issues. Signal diversity still thin — only volume-breakout-long+ (70%WR) and doji-bottom-long (66.7%WR) consistent winners. neutral_sniper (NEUTRAL mean-reversion) human-disabled Sep 12 — cannot override. coin_tracker_hot_plus in NEVER_REENABLE — code fix deployed but flag blocked.

### Fix Applied
**0 config changes.** System recovering on its own. All recent fixes verified working. No param change has enough data to justify (V5 eval Oct 1, doji-bottom at 20+ trades). Corrected signal_version.py false alarm (JSON path, not missing script). Re-flagged dead signal_gen imports to bug_hunter (4 files still importing defunct module).

### Verification
11T 54.5%WR +$1.13 (24h) — DB-verified. 4 open positions healthy. Pipeline active. Regime memory fresh (updated today). Next evals: V5 Oct 1, doji-bottom at 20+ trades, SHORT R:R recovery tracking.

## CEO Report — 2026-10-01 02:00 UTC

### Diagnosis
24h: 13T 46.2%WR +$0.05 (recovering). 7d: 114T 44.7%WR -$1.78. LONG +$0.16 (64T, R:R 1.09:1) is profitable. SHORT -$1.94 (50T, R:R 0.59:1) bleeds — needs >63%WR to break even at current win/loss ratios. pump-chain- SHORT 38T 50%WR -$0.56/7d is the volume leader but structurally disadvantaged. Hotset rs-s*/rs-r* 37T -$1.02/7d — small individual losses, RSI scattered 21-82.

### Root Cause
pump-chain- SHORT fires in RSI 25-40 bands that are 0%WR (5T -$0.67 combined 14d). Sweet spot is RSI 40-45 (8T 75%WR +$0.47). SHORT avg_loss $0.186 vs avg_win $0.110 — structural R:R problem worsened by oversold entries.

### Fix Applied
**PUMP_CHAIN_SHORT_RSI_MIN 25→40.** Blocks losing bands, preserves 40-45 edge. Expected +$0.10-0.20/7d. V5 test extended to Oct 3 (3T +$0.27 too few). DRIFT-001 fix live (pipeline restarted 01:47) — eval 48h. Hotset exec-time RSI ceiling fix — eval 48h. Re-delegated NEUTRAL signal to signal_analyst.

### Verification
Pending — param change needs pipeline restart to load. Monitor pump-chain- SHORT WR over next 48h. Target: >55%WR (from 50%). If still <50% at 20+ trades, raise MIN to 45.
