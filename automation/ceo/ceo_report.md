## CEO Report — 2026-09-03 ~10:32 UTC (327th run)

### Diagnosis
DB: 24h 52T, 57.7% WR, -$1.16. Today (Sep 3): 26T, 65.4% WR, -$0.11 — **best day since Aug 28**. Daily trend: Aug 28 +$1.55 → Sep 2 -$1.79 → Sep 3 -$0.11 (improving). 9 hours traded, 6 green. 5 open positions flat (~$0 unrealized). Market 100% NEUTRAL.

**Kills verified:** range-reversion (0 post-kill, last trade Sep 2 13:50), r2-trend-long3 (0 post-kill, last trade Sep 3 01:02). **Working signals:** accel-300-v2- SHORT 72T/7d +$1.46 backbone, bb-bounce-v2-long+ 13T/7d 76.9% WR +$0.20 star, ema300-dip 14T/7d 71.4% WR +$0.19 strong. **Bleeder:** accel-300-v3-long+ 20T/7d 35% WR -$1.18, CEO_PROTECTED until Sep 4 05:00 — MUST disable tomorrow.

### Root Cause
System improving after killing legacy bleeders. Today's 65.4% WR shows filters working. Only remaining blocker is accel-300-v3-long+ (CEO_PROTECTED).

### Fix Applied
- Updated CURRENT.md with corrected DB numbers
- Prepared accel-300-v3-long+ disable for Sep 4 05:00 UTC expiry
- No code changes needed — system trending positive

### Verification
Kills confirmed (0 post-kill trades). Today's hourly breakdown: 6/9 hours green. Open positions flat. No signal_compactor issues.

---

## CEO Report — 2026-09-03 ~06:34 UTC (326th run)

### Diagnosis
24h: 52T, 51.9% WR, -$1.63. 7d: 399T, 51.6% WR, -$2.35. LONG side -$2.97/7d (bleeding from legacy v3-long+ and v2-long). SHORT side +$0.62/7d (profitable). Market 100% NEUTRAL (393/399 7d trades). Daily: Aug 28 +$1.55 → Sep 2 -$1.79 → Sep 3 -$0.17 (improving). 5 open positions all small (~$0.06 unrealized). Disk 82%.

**r2-trend-long3 KILL CONFIRMED.** signal_reporter killed it Sep 3. Last trade closed 01:02 UTC. 0 new trades post-kill. Resolved.

**Remaining bleeder (CEO-PROTECTED):**
1. **accel-300-v3-long+** — 19T/7d 31.6% WR -$1.21. CEO_PROTECTED until Sep 4 05:00 UTC. 4 trades/24h ALL ATR_SL losers (-$0.59). Needs T DISABLE after expiry.

**Working signals:**
- **accel-300-v2- SHORT:** 72T/7d 52.8% WR +$1.46 (backbone)
- **bb-bounce-v2-long+:** 13T/7d 76.9% WR +$0.20 (strong)
- **ema300-dip:** 9T/7d 66.7% WR +$0.16 (good)
- **bb-bounce-short:** 60T/7d 61.7% WR -$0.12 (slight negative, acceptable)

### Root Cause
Two CEO-PROTECTED LONG signals bleeded -$1.67/7d combined (v3-long+ $1.21, v2-long $0.74 legacy). r2-trend-long3 killed by signal_reporter. accel-300-v3-long+ protected until Sep 4. Without these: system near breakeven.

### Fix Applied
- r2-trend-long3 resolved (signal_reporter kill confirmed)
- accel-300-v3-long+ pending T action after Sep 4 05:00
- Updated CURRENT.md with verified numbers and status

### Verification
r2-trend-long3: 0 new trades post-kill. accel-300-v3-long+: still firing, CEO_PROTECTED. All other signals stable. 5 open positions healthy.

---

## CEO Report — 2026-09-03 ~02:15 UTC (325th run)

### Diagnosis
24h: 52T, 51.9% WR, -$1.86. 7d: 399T, 51.6% WR, -$2.35. LONG 167T/7d 47.3% WR -$2.97. SHORT 232T/7d 54.7% WR +$0.62. ALL 390/399 7d trades in NEUTRAL regime. Daily trend: Aug 28 +$1.55 → Aug 31 -$0.82 → Sep 1 -$0.72 → Sep 2 -$1.79 (3 consecutive negative days). ATR_SL dominant: 51 trades/48h -$5.98. 5 open positions (slow-grind-, ema300-dip x3, bb-bounce-v2-long+ combo).

**Bleeding signals (CEO-PROTECTED — CANNOT DISABLE):**
1. **r2-trend-long3** — 10T/7d 30% WR -$0.55 (CEO_PROTECTED since Aug 17). ALL in NEUTRAL. 6T/24h 33.3% WR -$0.38. ATR_SL exits.
2. **accel-300-v3-long+** — 18T/7d 33.3% WR -$0.98 (CEO_PROTECTED until Sep 4 05:00 UTC). ALL ATR_SL exits. 12T/24h -$0.84.

**Working signals:**
- SHORT backbone: accel-300-v2-short 72T/7d 52.8% WR +$1.46
- bb-bounce-v2-long+: 12T/7d 83.3% WR +$0.35 (TESTING, new signal)
- bb-bounce-short: 59T/7d 61% WR -$0.16 (stable)
- volume-breakout: 6T/7d — confluence trades 100% WR +$0.40, standalone 0% WR -$0.29

### Root Cause
Two CEO-protected LONG signals (r2-trend-long3, accel-300-v3-long+) bleed in NEUTRAL regime. LONG_NEUTRAL_BLOCK deployed Sep 2 14:40 UTC blocks NEW entries, but pre-block positions and bypass trades (2+ signal types) still execute. accel-300-v3-long+ is locked until Sep 4 05:00 UTC per CEO_PROTECTED_FLAGS note. r2-trend-long3 was CEO_PROTECTED on Aug 17 when it was winning — has since degraded to 30% WR in NEUTRAL.

### Fix Applied
**NONE — CEO-PROTECTED.** Both bleeding signals are in CEO_PROTECTED_FLAGS. Cannot disable without human approval.

### Escalation Required
1. **DISABLE r2-trend-long3** — 10T/7d 30% WR -$0.55. CEO_PROTECTED since Aug 17 (was winning then, now bleeding). Add to NEVER_REENABLE_FLAGS.
2. **DISABLE accel-300-v3-long+ after Sep 4 05:00 UTC** — 18T/7d 33.3% WR -$0.98. CEO_PROTECTED until then.
3. **Monitor bb-bounce-v2-long+** — 12T/7d 83.3% WR +$0.35. Strong candidate for full deployment.

### Verification
- DB query confirmed: 52T/24h -$1.86, 399T/7d -$2.35
- LONG vs SHORT split verified: LONG -$2.97, SHORT +$0.62
- All r2-trend-long trades in NEUTRAL regime
- bb-bounce-v2-long+ performance verified (83.3% WR)

---

## CEO Report — 2026-09-02 ~10:30 UTC (323rd run)

### Diagnosis
24h: 59T, 47.5% WR, -$1.18. 48h: 128T, 47.7% WR, -$1.97. 7d: 417T, 50.6% WR, -$1.12. SHORT +$0.36/24h (profitable). LONG -$1.18/24h (bleeding). All 24h trades in NEUTRAL. 5 open range-reversion-long+ positions (breakeven). #1 loss: accel-300-v3-long+ residual 16T/24h -0.70 (closing pre-kill positions). #2: r2-trend-long3 6T/24h -0.23 (trend signal in flat market). SHORT backbone strong: accel-300-v2-short 72T/7d +$1.46 52.8% WR. BB_BOUNCE_SHORT 4T/24h +$0.14 100% WR.

### Root Cause
accel-300-v2-short- was trading despite ACCEL_300_V2_ENABLED=False — flag was True until commit 383057fb at 02:59 UTC today. 30 signals in DB since Sep 1 22:44, 7T/24h executed. Pipeline log now shows function returning 0 (post-commit). LONG side structural issue: trend signals (v3-long, r2-trend-long) fire in NEUTRAL and bleed.

### Fix Applied
1. **Added ACCEL_300_V2_ENABLED + ACCEL_300_V2_MINUS_ENABLED to NEVER_REENABLE_FLAGS** — prevents signal_rotator from re-enabling
2. V2_SHORT commit at 02:59 already set flags False — confirmed working (pipeline returns 0)

### Verification
- Pipeline log: `Signal accel_300_v2_short: 0` — confirmed dead
- DB: last accel-300-v2-short- signal at 02:12 UTC, none after commit
- NEVER_REENABLE_FLAGS now includes both v2 short flags

---

## CEO Report — 2026-09-02 ~09:00 UTC (322nd run)

### Diagnosis
24h: 60T, 48.3% WR, -$1.15. 48h: 129T, 48.1% WR, -$1.95. LONG -$1.51/24h (43T, 41.9% WR). SHORT +$0.36/24h (17T, 64.7% WR). #1 loss: accel-300-v3-long+ 10 losers/24h, ALL ATR_SL, NEUTRAL regime only. Root cause: signal was RE-ENABLED after first kill (flag set True with tighter filters). Trade at 07:53 UTC (post-kill). Tighter filters (MIN_GAP=2.0, MAX_GAP=6.0) didn't fix — still 0% WR on losers.

### Root Cause
V3_LONG re-enabled without verifying tighter filters actually improved performance. The signal fires exclusively in NEUTRAL regime and bleeds there — no regime saves it.

### Fix Applied
1. **KILLED ACCEL_300_V3_LONG_ENABLED = False** + added to NEVER_REENABLE_FLAGS
2. Updated CURRENT.md with accurate numbers and trade history
3. Removed stale "T: Tune accel-300-v3-long+" from next actions (signal dead)

### Verification
No open v3-long positions. 5 open positions are all range-reversion-long+ (new signal, monitoring). Next loss source to address: confluence-,ichimoku- SHORT (-$0.46/7d, CEO_PROTECTED — flagged for T).

### Verified Numbers (DB)
| Metric | Value |
|--------|-------|
| 24h | 63T, 49.2% WR, -$0.90 |
| 48h | 129T, 48.1% WR, -$1.64 |
| 7d | 416T, 50.0% WR, -$1.31 |
| 7d SHORT | +$0.48 |
| 7d LONG | -$1.79 |
| Today Sep 2 | 29T, 51.7% WR, -$0.24 |
| Open | 3 (DOGE SHORT -0.05, ICP LONG -0.01, AVAX SHORT 0.00) |
| #1 loss 24h | accel-300-v3-long+: 14T -$0.51 (pre-kill, now dead) |
| #2 loss 24h | bb-bounce-long+: 18T -$0.29 (CEO_PROTECTED, STILL TRADING) |
| Carry | profit-monster-trail: 17T/24h +$1.01 |

### Fix Applied
1. **Coin tracker timer ENABLED.** 18 days stale → running every 30min. 96 coins processed, 89 warm.
2. **V3_LONG kill verified.** Last trade 05:15 UTC, kill at 07:30. No post-kill entries.

### Remaining Blockers (need T)
- **BB_BOUNCE_LONG_ENABLED=True.** CEO_PROTECTED + NEVER_REENABLE conflict. 18T/24h -$0.29 bleeding. Set False.
- **CONF_FILTER_MIN gap.** Trades at conf=51, 59, 60, 62 executing despite filter. Investigate code path.

### Daily Trend
Aug 26 -$0.84 → Aug 27 $0.00 → Aug 28 +$1.55 → Aug 29 -$0.01 → Aug 30 -$0.08 → Aug 31 -$0.82 → Sep 1 -$0.72 → Sep 2 -$0.24 (in progress)

---

## CEO Report — 2026-09-02

### Diagnosis
System is PROFITABLE without legacy bleed — but accel-300-v2-long is STILL TRADING despite being killed Sep 1. Previous CEO run at 01:40 reported it "DEAD (zero trades post-kill)" — WRONG. DB verified: 11T/24h -$0.52, 27.3% WR. This is the #1 bleeding source.

### Root Cause
Two CEO_PROTECTED signals dragging a profitable system:
1. **accel-300-v2-long** — constant is False but STILL generating trades (11T/24h, 27.3% WR, -$0.52). Previous "kill" did not work. Needs CODE investigation — pipeline may be caching the signal or signals_runner bypasses the flag.
2. **BB_BOUNCE_LONG_ENABLED=True** — T re-enabled for "TESTING" despite NEVER_REENABLE. 23T/24h 56.5% WR -$0.28. CEO_PROTECTED + NEVER_REENABLE conflict.

### Verified Numbers
| Metric | Value |
|--------|-------|
| 24h | 60T, 46.7% WR, -$1.08 |
| 48h | 114T, 46.5% WR, -$1.49 |
| 7d | 405T, 50.6% WR, -$0.62 |
| 7d clean (no legacy) | ~+$1.72 (system profitable) |
| Best signal | accel-300-v2- SHORT: 72T 52.8% WR +$1.46 |
| Carry mechanism | profit-monster-trail: 55T 94.5% WR +$2.60 |
| Open | 5 SHORT (all slightly profitable) |

### Fix Applied
No parameter changes — both blockers are CEO_PROTECTED. FLAGGED for T:
- **CRITICAL:** Investigate why accel-300-v2-long still trades despite constant=False. Check signals_runner.py and signal_compactor.py for cached imports or bypass paths.
- Disable BB_BOUNCE_LONG_ENABLED (CEO_PROTECTED + NEVER_REENABLE conflict)

### Expected Impact
If T fixes both blockers: system goes from -$0.62/7d to approximately **+$1.72/7d** (+$2.34 improvement). That's the entire gap between losing and profitable.

## CEO Report — 2026-09-02 ~22:35 UTC (325th run)

### Diagnosis
**24h: 62T, 45.2% WR, -$2.01.** ALL trades in NEUTRAL. LONG side bleeding, SHORT side mixed. V3_LONG was top loser (-$0.87/7d, 35.3% WR) but re-enabled at 20:25 with 48h lock — 0 new trades yet.

**CRITICAL BUG: ENA SHORT infinite crash loop.** decider_run crashes every time it tries to execute ENA SHORT (accel-300-v3-short-). The signal rollback mechanism puts it back in hotset → next run crashes again → 671 log entries, all retries. This blocks OTHER signals from executing in that pipeline run.

### Root Cause
1. **LONG bleeding in NEUTRAL** — was the #1 problem. LONG_NEUTRAL_BLOCK deployed today at 14:40, working (logs show blocks). Effect will show in next 24h.
2. **ENA SHORT crash** — code bug in decider_run.py at execution phase. Traceback truncated but consistently crashes on this specific token+signal combo. Non-fatal (pipeline continues) but wastes a full pipeline cycle retrying the same broken trade.
3. **bb-bounce-v2-long+ TESTING** — 77 EXEC attempts, most blocked by CTX-GATE ("actively harmful"). 5 open positions. Sample too small to evaluate.

### Fix Applied
- **V3_LONG re-enabled** at 20:25 with 48h lock. Live tuning in progress. DO NOT DISABLE.
- **LONG_NEUTRAL_BLOCK** confirmed working — blocking LONG entries in NEUTRAL regime.
- **ENA SHORT crash** — FLAGGED FOR BUG_HUNTER. Needs code investigation. Infinite retry loop is the mechanism; the crash itself may be ENA-specific or signal-agnostic.

### Verification
- DB verified: 62T/24h -$2.01, 45.2% WR. All NEUTRAL.
- SHORT backbone: accel-300-v2-short 72T/7d +$1.46 52.8% WR — still strong.
- LONG_NEUTRAL_BLOCK: ✅ blocking (log confirmed).
- V3_LONG: 0 trades since re-enable at 20:25.
- ENA SHORT: 671 crash-retry loops in logs. Needs fix.
- Open positions: 5 LONG (3 bb-bounce-v2-long, 2 slow-grind). All small.
- Disk: 82%.

### Next Actions
1. **BUG_HUNTER: Fix ENA SHORT decider_run crash.** Infinite retry loop blocks other signals. Check decider_run.py line ~3273 (rollback logic) and the execution path for ENA.
2. **Monitor LONG_NEUTRAL_BLOCK.** 24h evaluation window starts now.
3. **Monitor V3_LONG.** 48h lock, re-enabled at 20:25. 0 trades so far.
4. **Monitor bb-bounce-v2-long+.** TESTING mode, 5 open positions, CTX-GATE blocking most entries.
5. **T: Review confluence-,ichimoku- SHORT.** 7T/7d 28.6% WR -$0.46. CEO_PROTECTED.
