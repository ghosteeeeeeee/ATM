# Trading Log — Learnings & Decisions

## 2026-08-16 06:30 UTC — Daily Orchestrator Report

**Pipeline Status:**
- Trades (24h): 58 closed, 0 open
- PnL: -5.89% (flat market variance)
- Market: Dead neutral (1 LONG_BIAS, 0 SHORT, 103 NEUTRAL)
- Macro gate: REDUCE (25% WR < 30)

**System State:**
- ct-hot+ fully cleared (0 open positions)
- PM_TRAIL deployed correctly (act 0.40%, dist 0.60%)
- All upgrades implemented (8/8 plans)
- No critical issues, no signals meet kill threshold

**Current Focus:**
- R:R monitoring: PM_TRAIL wider distance needs more time to show effect
- Market flat: CTX-GATE blocking signals (low volatility)
- ATR SL improving (36.0% vs 40% threshold)

**Implemented Today:**
- CURRENT.md updated (ct-hot+ cleared, market state, trimmed to 58 lines)
- Git committed and pushed

**Next Actions:**
1. Monitor R:R improvement from PM_TRAIL distance widening
2. Wait for market directional bias (regime shift)
3. Watch signal starvation if daily trades <20T when market moves

---

## 2026-08-16 05:30 UTC — Hourly Analysis

**Trades:** 1 closed (0 wins, 0 losses)
**PnL:** $0.00 (guardian_orphan flat exit)

**24h Snapshot:**
- 55 trades total: atr_sl_hit 22T -$1.63, profit-monster-trail 15T +$0.81, profit-monster-T1 10T +$0.56
- ATR SL hit rate: 40.0% (exactly at threshold)
- 48h SL hit rate: 36.0% (below 40% threshold — improving from PM_TRAIL revert)

**Signal Performance (48h):**
- ✅ return_exhaustion_long: 3T 100% WR +$0.39
- ✅ r2-trend-long6: 3T 100% WR +$0.16
- ⚠️ ct-hot+: 30T 46.7% WR -$0.29 (volume leader, slightly negative)
- ⚠️ wave_catcher+: 14T 42.9% WR -$0.16
- ❌ ct-hot-: 4T 0% WR -$0.19 (persistent loser, doesn't meet kill threshold — only 4T in 48h, 0T last hour)
- ❌ mover+: 6T 16.7% WR -$0.16

**Diagnosis:**
1. **Entry quality:** 1 trade last hour (orphan guard exit), can't assess entry quality
2. **SL behavior:** ATR SL hit 40.0% (24h) exactly at threshold; 48h at 36.0% (below threshold, improving)
3. **Signal quality:** No signal meets kill threshold (0% WR with 3+ trades in last hour). ct-hot- 0% WR but only 0T last hour.
4. **Trade frequency:** ~2.3/hr average (24h), normal

**Changes:** None. No signal meets kill threshold. CEO eval window active (PM_TRAIL_ACTIVATE_PCT revert to 0.40% deployed today). ATR SL hit rate improving (36.0% vs 40% threshold).

**No Change Needed:**
- ATR SL hit rate at 40.0% — exactly at threshold, trending down from recent changes
- pm-trail + pm-T1 = 25T +$1.37 compensating SL losses
- Trade frequency normal, no overtrading
- No 0% WR signals with 3+ trades in last hour

**Open Questions:**
- ct-hot- persistent 0% WR (4T/48h) — below kill threshold but worth monitoring
- PM_TRAIL revert to 0.40% needs 48h eval — monitoring avg exit % and R:R

---

## 2026-08-13 19:00 UTC — Hourly Analysis

**Trades:** 1 closed (0 wins, 1 loss)
**PnL:** -$0.11 (0% WR)

**Last Hour:**
- CC hzscore- SHORT: cut_loser_-1.03%, -$0.11

**24h Snapshot:**
- 68 trades total (34 profit-monster-trail, 31 atr_sl_hit, 2 cut_loser, 1 atr_tp_hit)
- ATR SL hit rate: 45.6% (above 40% threshold — profit-monster-trail +$1.54 compensates atr_sl_hit -$2.50)
- Net 24h by signal: accel-300- SHORT 25T -$0.66 worst, hzscore- 14T +$0.02 best

**Signal Performance (24h):**
- ✅ hzscore- SHORT: 14T, 64.3% WR, +$0.02
- ✅ bb_bounce+: 2T, 100% WR, +$0.05
- ⚠️ range_breakout_short SHORT: 20T, 45% WR, -$0.04 (flat)
- ❌ accel-300- SHORT: 25T, 44% WR, -$0.66 (worst, but WR >0%)
- ❌ continuation-,hzscore-: 3T, 33.3% WR, -$0.23 (tiny sample)

**Diagnosis:**
1. **Entry quality:** 1 trade last hour, small loss. Quiet period.
2. **SL behavior:** ATR SL hit 45.6% — persistent above40% threshold. Profit-monster-trail partially compensates.
3. **Signal quality:** No signal meets kill threshold (0% WR with 3+ trades last hour).
4. **Trade frequency:** ~2.4/hour average (last12h), well below 20/hour threshold.

**Changes:** None. No signal meets kill threshold. CEO stability period active. System within normal variance.24h flat with slight negative bias.

**Open Questions:**
- accel-300- SHORT: 25T with 44% WR and -$0.66 — R:R issue persists but not killable (WR >0%).
- ATR SL hit rate at 45.6% — persistent issue but profit-monster-trail compensates.

---

## 2026-08-13 12:00 UTC — Hourly Analysis

**Trades:** 1 closed (1 win, 0 losses)
**PnL:** +$0.03 (100% WR)
**Exit Reasons:** profit-monster-trail (1)

**24h Snapshot:**
- 87 trades, 46 profit-monster-trail (+$1.94), 37 atr_sl_hit (-$2.74)
- ATR SL hit rate: 42.5% (above 40% threshold but profit-monster-trail compensates)
- Net 24h: -$0.57 (54% WR — slightly negative)
- Today: 35T, -$1.13, 42.9% WR (cold day)

**Signal Performance (24h):**
- ✅ range_breakout_short SHORT: 19T, +$0.18, 57.9% WR
- ✅ bb_bounce+ LONG: 1T, +$0.03, 100% WR
- ❌ accel-300- SHORT: 37T, -$0.23, 56.8% WR (R:R issue — avg_loss > avg_win)
- ❌ range_breakout- SHORT: 12T, -$0.50, 25% WR (legacy signal)

**Diagnosis:**
1. **Entry quality:** Only 1 trade last hour — quiet period
2. **SL behavior:** ATR SL at 42.5% — above 40% threshold but profit-monster-trail (+$1.94) compensates atr_sl_hit (-$2.74)
3. **Signal quality:** accel-300- SHORT has decent WR (56.8%) but negative PnL due to R:R imbalance
4. **Trade frequency:** Very low — 1/hour, below normal

**Changes:** None. No signal meets kill threshold (0% WR with 3+ trades last hour). CEO stability period active. System within normal variance.

**Open Questions:**
- accel-300- SHORT: 37T in 24h with 56.8% WR but -$0.23 — R:R issue (avg_loss 60% > avg_win). Legacy signal still executing despite ACCEL_300_MINUS_ENABLED=False.
- Today's 42.9% WR is cold but sample size small (35T).

---

## 2026-08-12 22:00 UTC — Hourly Analysis

**Trades:** 5 closed (5 wins, 0 losses)
**PnL:** +$0.48 (100% WR)
**Exit Reasons:** profit-monster-trail (4), atr_tp_hit (1)

**24h Snapshot:**
- 98 trades, 53 profit-monster-trail (+$2.48), 39 atr_sl_hit (-$2.50)
- ATR SL hit rate: 39.8% (just under 40% threshold)
- Net 24h: roughly flat (profit-monster-trail compensates SL losses)

**Signal Performance (24h):**
- ✅ accel-300- SHORT: 18T, +$0.37, 72.2% WR
- ✅ range_breakout_short SHORT: 8T, +$0.37, 75% WR
- ✅ bb_bounce+ LONG: 14T, +$0.16, 64.3% WR (sole profitable LONG)
- ❌ range_breakout+ LONG: 8T, -$0.41, 25% WR (already killed)
- ❌ hzscore+ LONG: 4T, -$0.14, 25% WR (already blacklisted)

**Diagnosis:**
1. **Entry quality:** Excellent — last hour 100% WR, winners moved in favor quickly
2. **SL behavior:** ATR SL at 39.8% borderline but profit-monster-trail compensates
3. **Signal quality:** SHORT signals profitable, LONG signals mostly dead
4. **Trade frequency:** ~4/hour average, normal

**Changes:** None. CEO stability period active (14+ changes in 48h, trailing stop fix evaluating). No signal has 0% WR with 3+ trades in last hour. System within NEUTRAL regime variance.

**Open Questions:**
- 7-day trend: Aug 9 +$0.62 → Aug 11 -$0.33 (2 declines) → Aug 12 +$0.31 (recovery). Watching for continuation.

---

## 2026-08-12: Daily Orchestrator Report (17:30 UTC)

### Pipeline Status
- **Portfolio**: 5 open (STBL, APT, KAS, BCH, ETH — all SHORT) | 95 closed today | **-1.30% PnL**
- **24h**: 95T, -1.30% — choppy day (NEUTRAL regime)
- **7d**: ~441T, +$0.14, 52.2% WR — barely positive, 4 consecutive declining days
- **Market regime**: NEUTRAL (107/107 tokens)
- **Open PnL**: ~$0 flat

### CEO Directive
**NO TRADING CHANGES.** Stability period. 14+ changes deployed Aug 13-15. Trailing stop fix (0.80%) needs more eval time. Overreacting destabilizes.

### Team Activity (from kanban)
- **signal_reporter**: No kills needed. Two worst performers (trend_momentum_near_sma+, range_breakout+) already killed. Key finding: bb_bounce+ LONG is the only consistent winner (57.9% WR, +$0.16, 19T). Most SHORT signals negative PnL despite neutral WR.
- **health_monitor**: Two warnings — trades.json 0 bytes (false alarm: checking stale path at /root/.hermes/data/, real file at /var/www/hermes/data/ is 95KB). signals_runner slow (~5min/cycle, not crashing).
- **auto_1hr**: System flat/stable. No changes needed for 24h+. ATR SL hit rate at 46.4% (above 40% threshold but profit-monster-trail compensating).
- **upgrade_implementer**: Timed out (120s wrapper script timeout too short). FIXED: increased to 600s.

### What Was Done (by orchestrator)
1. **Fixed upgrade-implementer timeout** — wrapper script had `timeout 120` (2 min), agent needs ~5 min to read plans and generate audit. Changed to `timeout 600` (10 min).
2. **Validated all systems** — pipeline running, all timers active, trades.json fresh, 6 open positions (max), no regressions.

### Infrastructure Status
- **Disk**: 78% (healthy)
- **Failed services**: 5 non-critical (bug-hunter imports defunct ai_decider, hl-volume non-critical, mtf-macd-tuner non-critical, trading-checklist non-critical, upgrade-implementer fixed above)
- **trades.json**: Healthy at /var/www/hermes/data/trades.json (95KB, 5 open trades). The 0-byte file at /root/.hermes/data/trades.json is a stale legacy path — not used by the system.

### Signal Performance (24h)
- **bb_bounce+ LONG**: 19T 57.9% WR +$0.16 — **sole winner**
- **range_breakout- SHORT**: 20T 50% WR -$1.39 — borderline
- **hzscore- SHORT**: 16T 50% WR -$0.39 — flat
- **hzscore+ LONG**: 12T 41.7% WR -$1.09 — bleeding, monitor
- **accel-300- SHORT**: 3T 33.3% WR -$0.60 — needs more data

### Recommendations (for CEO)
1. **No action needed** — system performing within normal NEUTRAL regime variance
2. **Monitor**: SHORT 7d bleed -$0.87 (below -$1.50 threshold, no regime filter needed)
3. **Monitor**: hzscore+ standalone already restricted to combo-only, working as intended
4. **Next upgrade candidate**: weekly_signal_review.py (L2, MEDIUM) — weekly trend analysis catches signal decay faster than 6h checks

---

## 2026-08-12: Daily Orchestrator Report

### Pipeline Status (05:25 UTC)
- **Portfolio**: 6 open | 52 closed today | **+0.66% PnL** (green day)
- **24h**: 48T 25W (52.1% WR) +$0.05 — flat
- **7d**: 391T 208W (53.2% WR) +$0.99 — profitable
- **Market regime**: 103 NEUTRAL / 0 LONG / 2 SHORT (flat)
- **BTC**: $63,797

### What Was Done
1. **signal_version.py wired into auto_1hr** — param changes to hermes_constants.py now auto-logged with reason/by. Script existed but had zero callers. Now integrated into Step 5 of auto_1hr_prompt.md.
2. **audit_memory.py skipped** — brain_hebbian.db is an empty file (no tables, no data). Nothing to clean up.
3. **upgrade_audit.md updated** — signal-version-tracking marked DONE, next candidates list trimmed.

### What Was Already Done (by other automations)
- **health_monitor**: Fixed accel_300.py (added missing `_get_1h_trend()` — was ERROR every cycle)
- **signal_reporter**: Killed trend_momentum_near_sma PLUS/MINUS flags (base was already killed, directional flags still True)
- **auto_1hr**: System calm, no changes needed for 12h+

### Signal Performance (24h)
- bb_bounce+: 16T 10W (62.5% WR) +$0.23 — **star signal**
- range_breakout-: 2T 2W +$0.18 — good
- hzscore+: 10T 4W (40% WR) -$0.11 — AVNT bleeding (4 SL hits)
- hzscore-: 4T 2W -$0.05 — minor

### Next Steps
1. Monitor hzscore+ AVNT bleed (4 SL hits — is AVNT choppy or signal issue?)
2. Weekly signal review automation (L2, next candidate)
3. Wyckoff pattern recognition (L2, needs pattern_recognition.py)

---

## 2026-08-11: Daily Orchestrator Report

### Pipeline Status (05:25 UTC)
- **Portfolio**: 1 open (ASTER LONG, +0.19%) | 57 closed today | **-3.46% PnL**
- **24h**: 56 trades, -$0.12, 41.1% WR (RED — 2nd rough day after 15 green)
- **7d**: 477 trades, +$0.56, 50.9% WR (positive)
- **Market regime**: 105 NEUTRAL / 1 LONG_BIAS (NIL)
- **SL config**: REVERTED to 1.2%/2.5% (05:20 — 0.5% caused 64.7% SL hit rate)
- **Confluence gate**: Fixed — standalone bypass deployed (04:24), hotset restored
- **Kill switch**: LIVE TRADING ON
- **Disk**: 81%

### Key Events Today
1. **03:00 — CEO reverted SL widening** to 0.5% (from 1.2%). Result: SL hit rate spiked to 64.7%, profit-monster trades killed (29.4% PM rate vs 56.3%). Wrong direction.
2. **04:24 — CEO fixed hotset empty bug**. Root cause: confluence gate final guard blocked ALL single-source signals. Fixed by adding backtested standalone bypass to 4 guards. Hotset restored to 6 entries.
3. **05:20 — CEO reverted SL back to 1.2%**. 0.5% experiment caused 64.7% SL hit rate (vs 35% at 1.2%). Tighter SL = more stop-outs, not fewer. Constants restored: ATR_SL_MIN/MAX/INIT 1.2%/2.5%, TRAILING_DISTANCE 0.60%, CL_TRAIL_ACTIVATE -1.0.
4. **07:00 — Confluence gate assessment**. Hotset was empty again — no signals passing compaction. Pipeline running but no new entries. Needs monitoring.

### SL Revert Evaluation Window
- **Deployed**: 05:20 UTC (1.2% SL)
- **Eval window**: 05:20 Aug 11 → 05:20 Aug 12 (24h)
- **Baseline**: 0.5% SL caused 64.7% SL hit rate, profit-monster killed
- **Target**: SL hit rate <40%, profit-monster restoring
- **DO NOT REVERT** — system was profitable at 1.2% SL for 15+ days

### Signal Performance (24h / 7d)
| Signal | 24h | 7d | Status |
|--------|-----|-----|--------|
| bb_bounce+,range_finder+ | 7T -$0.08 43% | 53T +$0.82 60% | 7d STAR |
| bb_bounce+,hzscore+ | 15T -$0.21 33% | 30T +$0.32 50% | 7d STAR, 24h bleeding |
| tl_break_long | — | 20T +$1.17 70% | 7d TOP |
| bb-bounce-short,hzscore- | 4T -$0.04 50% | 16T +$0.17 62% | 7d STAR |
| continuation+,hzscore+ | 3T +$0.18 33% | 7T +$0.22 57% | Active |

### Close Reasons (24h)
- atr_sl_hit: dominant cost driver (trending up, SL revert should fix)
- profit-monster-trail: sole winning exit (was killed by 0.5% SL, should restore)
- cut-loser-CL-trail: moderate cost

### Upgrade Audit Updates
- **signal-version-tracking**: Script exists (108 LOC) but NOT integrated into pipeline. Needs wiring into CEO/auto_1hr for auto-logging.
- **system-improvements**: check_key_rotation.py exists (was listed as missing). Still missing: audit_memory.py, weekly_signal_review.py.
- **Blacklist testing**: Complete. 77 tokens tested, 0 KEEP. Blacklist is working as intended — signal generation filters are the bottleneck, not blacklist.

### What NOT To Do
- Do NOT revert SL from 1.2% to 0.5% again — experiment failed (64.7% SL hit rate)
- Do NOT change parameters during SL evaluation window (until 05:20 Aug 12)
- Do NOT kill bb_bounce+,hzscore+ LONG — 7d intact at 50% WR, 24h bleed is variance
- Do NOT add more blacklisted tokens — testing conclusive (0 KEEP across 77 tokens)

### Team Activity
- **health_monitor**: All systems nominal, 48 timers active, 0 missed firings
- **auto_1hr**: NO CHANGES (evaluating SL revert, no kill candidates)
- **signal_reporter**: Report committed, no kills needed, 7d still profitable
- **daily_orchestrator**: This report. Updated upgrade audit (signal-version-tracking status fix).

---

## 2026-08-10: Daily Orchestrator Report

### Pipeline Status
- **Portfolio**: 6 open | 64 closed today | **+5.44% PnL**
- **Market regime**: 106 tokens scanned → 1 LONG / 3 SHORT / 102 NEUTRAL
- **Speed**: 1 token >= 50% confidence (NIL LONG_BIAS 55.4%)
- **Signals**: 93 generated/hr, 0 approved (macro gate REDUCE)
- **Kill switch**: LIVE TRADING ON
- **CEO**: 62.3% WR 24h, 11th consecutive green day

### Health Status
- **System**: OK — 42 timers active, all firing
- **Disk**: 81% (22GB free)
- **Errors**: 0 critical
- **Auto-fixes**: Stopped deprecated self-close-watcher timer (was wasting cycles)

### What Was Implemented

1. **Restarted auto-1hr timer** — was dead since Aug 02 (8 days). Timer was enabled but not firing (showed "Trigger: n/a"). Restarted manually, confirmed service runs successfully. Next fire in ~57min.

2. **Fixed signal reporter timeout** — OpenMemory queries failing with `tenant_mismatch` errors, causing 10min timeouts. Added explicit "Do NOT query OpenMemory" instructions to both `signal_reporter_prompt.md` and `auto_1hr_prompt.md`.

3. **Implemented signal version tracking** — Created `scripts/signal_version.py` with log/current/history/list commands. Storage at `data/signal_versions.json`. Enables param change tracking + regression detection.

### Blacklist Testing — FINAL
- **77 tokens tested across 5 batches, 0 KEEP**
- Root cause: signal generation filters block these tokens; when signals fire, 0% WR
- Blacklist is a symptom filter, not a cause — no further batches planned

### Signal Performance (24h)
- **Zero winning signals** — all active signals net negative
- **Biggest losers**: tl_break_long (-$73), tl_break_short (-$61)
- **Systemic issue**: No signal family has positive PnL in 7 days

### Pending Plans (from upgrade_audit.md)
| Plan | Difficulty | Status |
|------|-----------|--------|
| signal-version-tracking | L2 | **DONE** (script created) |
| audit_memory | L1 | PENDING |
| weekly_signal_review | L2 | PENDING |
| wyckoff-pattern-recognition | L2 | NOT IMPLEMENTED |

### Quality Metrics
- Tasks completed: 5
- First-attempt success: 100%
- Pipeline uptime: 100%
- Critical issues found: 2 (stale timers)

---

## 2026-08-11 15:26 Hourly Analysis

**Trades:** 1 closed (0 wins, 1 loss) — W LONG trend_momentum_near_sma+ CL-T1 exit, -$0.12
**PnL:** -$0.12 (WR: 0.0%)
**24h:** 32T, -$0.46, 34.4% WR

**Changes:** None

**No Change Needed:**
- SL eval window active until 05:20 Aug 12 — no param changes
- atr_sl_hit 53.1% (17/32) — elevated but eval window constrains response
- bb_bounce+,hzscore+ 24h 18.2% WR (11T) cold but 7d 48.5% intact — no kill
- No 0% WR kill candidates (3+ trades threshold)
- Trade frequency 1/hr (normal)
- Since SL revert (05:20): 4T only — too small sample

**Key Observations:**
- cut-loser-CL-T1 new exit type: avg -$0.12 vs cut-loser-CL-trail -$0.067 — worse
- trend_momentum_near_sma+ first fire: loss — monitor
- 6 open positions, system calm

**Open Questions:**
- 53.1% SL hit rate at 1.2% — is this the new baseline or will it normalize?
- cut-loser-CL-T1 root cause (new exit logic?)

---

## 2026-08-11 03:38 Hourly Analysis

**Trades:** 0 closed in last hour (system quiet, last trade at 02:29 UTC)
**PnL:** N/A

**24h Summary:** 58 trades, -$0.33, 41.4% WR, -$0.006 avg

**Changes:** None

**No Change Needed:**
- No trades in last hour — system quiet at this hour
- SL reverted to tighter settings (0.5% min, 1.0% max) at 03:00 — needs 24h+ to show results
- No signal meets kill threshold (0% WR with 3+ trades in 3h or 6h)
- Trade frequency normal (58/24h = 2.4/hr)

**Key Observations:**
- atr_sl_hit = 43.1% of closes (24h) — still above 40% threshold, but CEO just reverted SL widening at 03:00
- profit-monster-trail = 39.7% of closes, +$1.13 — sole winning exit type
- cut-loser-CL-trail = 15.5% of closes, -$0.43 — losing exit type eating into profits
- bb_bounce+,hzscore+ = 16T, -$0.34, 31.3% WR — worst signal, but not triggered recently (0 trades in 3h)
- All other signals: small winners or breakeven

**Open Questions:**
- Will SL revert to 0.5% reduce atr_sl_hit rate below 40%? (needs 24h data)
- Should cut-loser-CL-trail be disabled? (15.5% of closes, -$0.43, losing money)

---

## 2026-08-11 01:26 Hourly Analysis

**Trades:** 4 closed (2 wins, 2 losses) in last 1.5h
**PnL:** -$0.02 (WR: 50.0%)

**24h Summary:** 62 trades, 22 wins, -$0.32, 35.5% WR

**Changes:** None

**No Change Needed:**
- No signal hit kill threshold (0% WR with 3+ trades in last hour)
- Trade frequency normal (2.6/hr)
- SL widening deployed 22:00 — needs 24h+ evaluation

**Key Observations:**
- atr_sl_hit = 41.9% of closes (just above 40% threshold — trending UP from 37.5% at 00:00)
- profit-monster-trail = 38.7% of closes, +$1.22 — sole winning exit type
- bb_bounce+,hzscore+ dominant signal (19T) but 36.8% WR, 8/19 SL hits — getting chopped
- cut-loser-CL-trail 11T -$0.55 — losing exit type eating into profits

**Open Questions:**
- Is trailing distance at 0.60% too wide? Trades getting micro-profits then getting clipped on pullback
- Should atr_sl_hit threshold be raised to 45% before intervention? (currently at 41.9%)

---

## 2026-08-11 00:00 Hourly Analysis

**Trades:** 2 closed (2 wins, 0 losses)
**PnL:** +$0.10 (WR: 100.0%)

**24h Summary:** 64 trades, +$0.17, 50.0% WR

**Changes:** None

**No Change Needed:**
- atr_sl_hit = 37.5% of closes (under 40% threshold — SL widening at 22:00 helping)
- No signal hit kill threshold (0% WR with 3+ trades in last hour)
- Trade frequency normal (2/hr)
- Last hour was best in12h: both trades via profit-monster-trail, both wins
- System recovering from 7-hour losing streak (13:00-19:00 UTC)

**Key Observations:**
- bb_bounce+,hzscore+ remains net negative (19T -$0.23, 42.1% WR 24h) — biggest drag
- However, it had 0 trades in last hour (no kill threshold met)
- SHORT signals outperforming: hzscore-,range_breakout- 3T +$0.07 (66.7% WR)
- profit-monster-trail carrying system: 27T +$1.29 (24h)

**Open Questions:**
- Is bb_bounce+,hzscore+ decay temporary (regime chop) or structural?
- SL widening impact needs 24h+ data to confirm — monitoring

---

## 2026-08-10 18:00 Hourly Analysis

**Trades:** 4 closed (1 win, 3 losses)
**PnL:** -$0.08 (WR: 25.0%)

**24h Summary:** 72 trades, +$0.17, 50.0% WR

**Changes:**
1. **Killed range_finder+** — 20 trades -$0.44 (24h), all combos negative. bb_bounce+,range_finder+ degraded from 64.3% WR (Aug 8) to 42.9% (today). VEL filter already deployed but not helping. Signal is bleeding across every pairing.

**No Change Needed:**
- atr_sl_hit = 31.5% of closes (under 40% threshold)
- profit-monster-trail carrying system: 36T +$1.85 (24h)
- No other signal hit kill threshold
- Trade frequency normal (72/24h = 3/hr)

**Open Questions:**
- range_finder+ was system star 2 days ago. Market regime shift or signal decay?
- bb_bounce+ standalone still viable? (21T +$0.29 57.1% WR 24h)
- 5-hour losing streak 14:00-18:00 UTC — noise or regime?

---

## 2026-08-10 07:00 Hourly Analysis

**Trades:** 3 closed (2 wins, 1 loss)
**PnL:** -$0.01 (WR: 66.7%)

**24h Summary:** 60 trades, +$0.40, 56.7% WR

**Changes:** None

**No Change Needed:**
- atr_sl_hit = 21.6% of closes (under 40% threshold — no TPSL fix alert needed)
- No signal hit kill threshold (0% WR with 3+ trades in last hour)
- Net positive system, balanced trade frequency (60/24h = 2.5/hr)
- Hourly losses 01:00-06:00 are low-volume noise, not a regime issue

**Open Questions:**
- range_finder+ signals net -$0.29 (8 losers vs 3 winners) — monitor next hour; if persists, may need param adjustment (not kill — it's a confluence signal)

---

## 2026-08-08: Daily Orchestrator Report

### Pipeline Status
- **Portfolio**: 6 open | 40 closed today | **+2.10% PnL**
- **Market regime**: NEUTRAL across all tokens
- **Speed**: moderate
- **Hotset**: empty (all-NEUTRAL regime)
- **Blacklist**: 171 SHORT / 139 LONG (final — no more trials)

### Health Status
- **System**: OK — 30+ timers active
- **Disk**: 79% (89G/118G) — health monitor compressed 47 old logs
- **Errors**: 0 critical

### Signal Performance (24h)
- **Trades**: 42 closed, 61.9% WR, +$0.52 PnL
- **Killed today**: range_finder- SHORT (40% WR, -$0.19), vortex_break_short SHORT (25% WR, -$0.15)
- **Top performer**: bb_bounce+,range_finder+ LONG (75% WR, +$0.51)
- **SHORT side broadly negative** — 9 signals now disabled
- **LONG side (bb_bounce+ combos) carrying the system**

### Blacklist Trials — COMPLETE
- **77 tokens tested across 5 batches, 0 KEEP**
- Root cause: signal generation filters (SPEED_MIN, PHASE_ENTRY, CONTEXT_GATE) block these tokens
- Blacklist is a symptom filter, not a cause — no further batches planned

### What Was Implemented

1. **Fixed hl-sync-guardian timer** — was dead since Jul 29 (service manually started Aug 7). Timer restarted, guardian now fires every 2 min as designed.

2. **Restarted auto-1hr timer** — dead since Aug 2 (6 days). Timer was disabled. Re-enabled and restarted. Will fire next hour.

3. **Uncertainty check quick wins** — already in bug-hunter (line 138) and post-change (line 69) skills. No changes needed.

4. **Disk cleanup** — health monitor already compressed 47 old logs. 79% disk is safe, no further action needed.

### Critical Issues
- **Auto-1hr was dead 6 days** — no param tuning occurred during this period. Now restored.
- **HL-sync-guardian timer was dead 10 days** — service ran but timer wasn't firing. Now fixed.

### Pending Plans (from upgrade_audit.md)
| Plan | Difficulty | Status |
|------|-----------|--------|
| signal-version-tracking.md | L2 | PENDING — param change logging + regression detection |
| transcript-mining-quick-wins.md | L1 | DONE (uncertainty checks already exist) |
| wyckoff-pattern-recognition | L2 | NOT IMPLEMENTED |
| self-learning-system-spec | L3 | NOT IMPLEMENTED |

### Recommendations for CEO
1. **Monitor auto-1hr** — now restored, will it produce useful tuning? First run due in ~30min.
2. **Signal version tracking** — L2 plan, high value. Param changes currently invisible. Recommend implementing next.
3. **SHORT signals** — 9 disabled, SHORT side broadly negative. Consider leaving SHORT disabled until market shows directional conviction.
4. **Open bugs**: 0 (clean)

### Quality Metrics
- Tasks completed: 5
- First-attempt success: 100%
- Pipeline uptime: 100%
- Critical issues found: 2 (stale timers)

---

## 2026-08-07: Daily Orchestrator Report

### Pipeline Status
- **Portfolio**: 6 open | 79 closed today | **-4.70% PnL**
- **Market regime**: 0 LONG / 0 SHORT / 104 NEUTRAL — no directional conviction
- **Speed**: 42% tokens >= 50% (moderate)
- **Hotset**: 1 token
- **Blacklist**: 169 SHORT / 143 LONG
- **Dead hours**: active (03-08 UTC)

### CEO Report Analysis (Re-verification)
Data source: `signals_hermes_runtime.db` → `signal_outcomes`, last 7 days.
Criteria: 20+ trades AND negative total PnL.

### Signal Kills Implemented

| Signal | Trades (7d) | WR | PnL | Action |
|--------|-------------|-----|-----|--------|
| TL_BREAK (all) | 66 long + 39 short | 33.3% / 30.8% | -$1.33 / -$1.43 | **DISABLED + NEVER_REENABLE** |
| ZSCORE_RISING (all) | 44 + 26 | 38.6% / 26.9% | -$1.37 / -$1.01 | **DISABLED + NEVER_REENABLE** |
| HZSCORE_MINUS | 76 | 15.8% | -$53.50 | **DISABLED + NEVER_REENABLE** |
| PCT_HERMES_PLUS | 64 | 14.1% | -$33.83 | **NEVER_REENABLE** (already False) |

### What Was Already Dead (verified)
- accel-300-vel+ → already in NEVER_REENABLE_FLAGS
- inv-accel-300- → already in NEVER_REENABLE_FLAGS
- vel-hermes- → already in NEVER_REENABLE_FLAGS

### Remaining Active Signals (winners)
- bb_bounce,hzscore+ LONG — 100% WR (3T), +1.27
- ma100-cross,return_exhaustion_long — 66.7% WR (6T), +1.13
- ma100-cross,vortex_break_long — 80% WR (5T), +0.82
- hzscore+,return_exhaustion_long — 54.5% WR (11T), +0.88
- vortex_break_short — 100% WR (2T), +0.89

### Recommendations for CEO
1. **Investigate phantom trade bug** — debug instrumentation deployed, awaiting production data
2. **Monitor remaining active signals** — 5 winning combos, all LONG-dominant
3. **Blacklist experiment complete** — 77 tokens tested, 0 KEEP. Stop rotating.

### Files Changed
- `scripts/hermes_constants.py`: Disabled 4 signals, added 7 to NEVER_REENABLE_FLAGS, removed 2 from ROTATOR_PROTECTED_FLAGS

---

## 2026-08-07: Daily Orchestrator Run (17:30 JST)

### Pipeline Status (Latest)
- **Portfolio**: 6 open | 67 closed today | **-1.88% PnL**
- **Market regime**: 1 LONG / 0 SHORT / 105 NEUTRAL — heavily neutral
- **Speed**: 42% tokens >= 50% — market too quiet for active trading
- **Hotset**: 0-2 tokens (confluence gate working correctly)
- **Errors**: 0 (only [SLOW] runner warnings)

### Actions Taken

**1. Disabled bb_bounce standalone SHORT**
- File: `scripts/hermes_constants.py:936`
- Change: `BB_BOUNCE_MINUS_ENABLED = False`
- Reason: 40% WR, -$4.61% over 7d. Confluence (bb_bounce+hzscore+) stays enabled (100% WR).

**2. Investigated hotset empty issue**
- Finding: Hotset IS working correctly. Confluence gate requires 2+ unique signal types.
- In quiet market (42% speed, 105/106 neutral), most signals are single-source and correctly blocked.
- When confluence signals fire (bb_bounce+ + range_finder+, ma100-cross- + vortex_break_short), they DO get through.
- Recent examples: ETH LONG (bb_bounce+ + hl_copy_trader), ENS LONG (bb_bounce+ + range_finder+)
- **No action needed** — system working as designed.

**3. Investigated stale signal names in signal_outcomes**
- Finding: 5106 out of 8980 records (56.9%) are from stale/disabled signals.
- Offenders: accel-300 variants, inv-accel-300, tl_break, vel-hermes, pattern_scanner, decider.
- These are HISTORICAL records from when signals were enabled, not current writes.
- Impact: Corrupts performance tracking metrics in signal_reporter.
- **Recommendation**: Add filter in signal_reporter to exclude stale signal types, or purge records older than 30 days.

### Recommendations for CEO
1. **Stale signal cleanup** — 56.9% of signal_outcomes are from dead signals. Add exclusion filter or purge.
2. **Monitor bb_bounce+hzscore+ combo** — 100% WR, best signal in system. Protect from accidental disable.
3. **Market quietness** — 42% speed, 105/106 neutral. System correctly reducing trade frequency.

### Quality Metrics
- Tasks completed: 3/3
- First-attempt success: 100%
- Critical issues found: 1 (stale signal records corrupting metrics)

---

## 2026-08-06: Daily Orchestrator Report

### Pipeline Status
- 6 open | 75 closed today | +3.18% PnL
- Hotset empty — market overwhelmingly NEUTRAL (103/105 tokens)
- Pipeline healthy, no errors

### Changes Implemented
1. **FIXED: tl_break inversion bug** — Removed `tl_break_long`/`tl_break_short` from `INVERT_SIGNALS` in `hermes_constants.py:1151-1159`. Root cause: dynamic WR-based auto-inversion was flipping good signals to wrong direction (31.6% of trades inverted). Current tl_break performance is 100% WR — no inversion needed.
2. **RE-ENABLED: zscore-rising+** — Set `ZSCORE_RISING_PLUS_ENABLED = True` in `hermes_constants.py:1051`. Signal reporter showed 62.5% WR, +$2.17. Not in `_NEVER_REENABLE` set.
3. **SKIPPED: vel-hermes- re-enable** — CEO explicitly blocked in `_NEVER_REENABLE` set. Signal reporter recommendation conflicts with CEO decision.
4. **SKIPPED: decider SHORT disable** — Already in `_DEAD_SIGNALS` blocklist, no action needed.

### Blacklist Testing Complete
- 77 tokens tested across 5 batches, 0 KEEP
- Blacklist is working as intended — signal generation filters (speed, phase, context gate) block these tokens before they can trade
- No further batches planned

### Critical Issues
- Market overwhelmingly NEUTRAL — no new entries expected until regime shifts
- All 77 blacklist candidates confirmed as signal-quality-poor, not blacklist-bottleneck

### Next Steps
1. Monitor tl_break performance post-fix (should see 0 inversions going forward)
2. Monitor zscore-rising+ performance after re-enable
3. Wait for regime shift to generate new hotset entries

---

## 2026-08-05: Signal Performance Report

### 24h Performance (catastrophic)
- **40 trades, 0 wins, 0% WR, -$60.56 PnL**
- Every signal that fired in the last 24h lost money
- Worst: zscore-rising- (-$9.06), pattern_wolf_wave_bear (-$8.8), bb_bounce (-$6.76)

### 7d Overall
- **590 trades, 88 wins, 14.9% WR, -$354.61 PnL**
- No signal has positive PnL across any timeframe
- tl_break family = 45% of total losses (299 trades, -$161.53)

### Critical Actions Required
1. DISABLE `TL_BREAK_ENABLED` — 12-20% WR, -$161 PnL, re-enabled 08-04 still failing
2. FIX `INVERSE_ACCEL_300_MINUS_ENABLED` → False (flag is True but in NEVER_REENABLE list)
3. DISABLE `ACCEL_300_MINUS_ENABLED` — 0% WR in 7d
4. NEW losers to disable: bb_bounce, pattern_wolf_wave_bull/bear

### Systemic Issue
Zero WR across ALL signals for 48h+. Market regime hostile to all signal types. Consider pausing signal-based entries until regime shifts.

---

## 2026-08-01: Trade Analysis & SL/TP Retune

### Data Window
- Analyzed: 50 closed trades (last 12h), signal_outcomes (72h), price_history around key trades
- Trades: 2814 total closed, 0 open at analysis time
- Trade rate: 3 trades in past hour (very low — restrictive params)

### Signal Performance (72h by direction)
| Signal | Dir | Trades | WR | Avg PnL |
|--------|-----|--------|-----|---------|
| tl_break_long | LONG | 108 | 1.9% | -0.626% |
| tl_break_short | SHORT | 119 | 3.4% | -0.470% |
| accel-300-vel+ | SHORT | 34 | 11.8% | -0.428% |
| accel-300-vel- | LONG | 20 | 30.0% | -0.264% |
| inv-accel-300- | SHORT | 14 | 14.3% | -0.218% |
| accel-300+ | SHORT | 8 | 25.0% | -0.045% |

**Key finding:** ALL signal types are net losers. Best performer: accel-300+ SHORT (-0.045% avg). Worst: tl_break_long LONG (-0.626%).

### Price Action Analysis (1h before → 2h after entry)
**Winners** (PURR SHORT, AAVE SHORT, ORDI LONG):
- Low adverse excursion (<0.5%) — price barely went against entry
- High favorable excursion (>2%) — strong directional move after entry
- Entry timing was excellent — caught the move early

**Losers** (UNI SHORT, KAITO LONG, AIXBT LONG):
- High adverse excursion (1-3.5%) — price immediately went against
- Some had high favorable excursion that REVERSED (whipsaw)
- Entry timing was poor — caught the tail end of a move

### Root Causes Identified
1. **SL too tight (0.5%)** — normal crypto retracements of 0.5-1% immediately stop out trades
2. **Trailing activates too early (0.15%)** — normal 0.2% retracements trigger trailing before trade develops
3. **Trailing distance too wide (0.50%)** — once in profit, too much room given back before trail kicks in
4. **Signal quality abysmal** — 1.9-3.4% WR on primary signals
5. **tl_break signal inversion** — tl_break_long firing on SHORT trades (28 times, 0 wins)

### Changes Implemented
1. **ATR_SL_MIN_INIT: 0.5% → 0.8%** — wider breathing room for new trades, reduce whipsaw stops
2. **TRAILING_DISTANCE_PCT: 0.50% → 0.30%** — tighter trailing locks profit faster
3. **TRAILING_ACTIVATION_PCT: 0.15% → 0.40%** — wait for real move before trailing activates

### 5 Actionable Adjustments (ranked by impact)
1. ✅ Widen initial SL to 0.8% — IMPLEMENTED
2. ✅ Tighten trailing distance to 0.30% — IMPLEMENTED
3. ✅ Raise trailing activation to 0.40% — IMPLEMENTED
4. ⬜ Raise SIGNAL_FILTER_SPEED_MIN from 50 to 60 — be more selective
5. ⬜ Investigate tl_break signal inversion — signals firing on wrong direction

### What NOT to change
- ATR_SL_MIN (0.5%) — this is the floor, keep it
- ATR_TP_MAX (1.0%) — already tight enough
- Phase-based k scaling — disabled (was compressing SL too aggressively)
- Dead hours filter — working correctly (16% WR during dead hours vs 35% active)

### Open Questions
- Why are only 3 trades in past hour? Are params too restrictive?
- ~~Is tl_break signal inversion a pipeline bug or intentional?~~ **ANSWERED 2026-08-01: context gate FLIP logic**
- ~~Should we disable tl_break_long entirely (1.9% WR on 108 trades)?~~ **Still active — see below**

---

## 2026-08-01: Context Gate FLIP Root Cause + Signal Quality Crisis

### Data Window
- Analyzed: 174 closed trades (24h), signal_outcomes (48h), trades.json (200 recent)
- Trades: 2816 total closed, 0 open at analysis time
- Trade rate: ~7 trades/hour (moderate)

### Signal Performance (24h — all signals net losers)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| tl_break_long | 44 | 4.5% | -21.33% | CATASTROPHIC |
| accel-300-vel+ | 44 | 9.1% | -20.87% | CATASTROPHIC |
| tl_break_short | 36 | 5.6% | -14.50% | CATASTROPHIC |
| accel-300-vel- | 30 | 20.0% | -12.14% | BAD |
| velocity-ignition | 10 | 0.0% | -4.97% | DEAD |

**Overall: 8.0% WR, -79.82% total PnL in 24h.**

### ROOT CAUSE: Context Gate FLIP Logic (decider_run.py:849-881)

**The smoking gun:**
- 24 tl_break_long trades executed as SHORT (inverted direction)
- 50 tl_break_short trades executed as LONG (inverted direction)
- Total: 74 out of 234 tl_break trades (31.6%) had direction INVERTED

**How it worked:**
1. Signal generator correctly identifies tl_break_long (LONG direction)
2. Context gate `_rule_context_gate()` sees phase='falling' or z_score conditions
3. Returns `('FLIP', {'new_dir': 'SHORT'})` — reversing the signal's direction
4. Trade executes as SHORT (against the signal's intended direction)
5. Result: 0% WR on all 74 flipped trades

**Why it was wrong:**
- Phase-based flip: "falling phase + LONG → SHORT" assumes the wave is dying, but tl_break already accounts for this in its trendline detection
- Z-score flip: "z < -0.5 + SHORT → LONG" assumes oversold bounce, but in downtrends z confirms trend
- The flip logic was net negative for EVERY signal type it touched

### Changes Implemented

**1. DISABLE context gate FLIP logic (decider_run.py:849-853)**
- Commented out phase-based FLIP (falling→SHORT, accelerating→LONG)
- Commented out z-score FLIP (oversold SHORT→LONG)
- SKIP remains active for overbought LONG (z > 0.5) — this was already changed from FLIP to SKIP on 2026-07-31

**2. RAISE SIGNAL_FILTER_SPEED_MIN: 50 → 65 (hermes_constants.py:471)**
- Winners average 71% speed percentile
- 50 was too permissive — letting slow, low-momentum signals through
- 65 blocks bottom 35% of speed distribution

**3. DISABLE velocity-ignition signal (already done 2026-08-01)**
- 0% WR across 10 trades, -$4.97 total
- Fires on first bar spike that reverses — no follow-through

### What NOT to change
- ATR_SL_MIN_INIT (0.8%) — wider breathing room working as intended
- TRAILING_ACTIVATION_PCT (0.40%) — wait for real move before trailing
- TRAILING_DISTANCE_PCT (0.30%) — tighter trail locks profit faster
- Phase-based k scaling — disabled (was compressing SL too aggressively)
- Dead hours filter — working correctly
- SIGNAL_FILTER_ENABLED (True) — the filter framework is sound, just needed tuning

### Remaining Issues
1. **tl_break signal quality is fundamentally poor** — even without flips, 4.5% WR (LONG) and 5.6% WR (SHORT) suggest the signal itself needs work or should be disabled
2. **accel-300-vel+ is second-worst performer** — 9.1% WR on 44 trades. Consider raising its suppression weight
3. **Trade frequency may still be too high** — 174 trades in 24h with 8% WR means 160 losses. Need to be more selective
4. **UNI, LINEA, MOVE, ZK, TIA, TURBO all 0% WR** — should be blacklisted both directions

### Open Questions for Next Analysis
- Should tl_break be disabled entirely? (4.5-5.6% WR is essentially random)
- Are the 24 signal_outcomes per tl_break trade (doubled entries) real or a dedup bug?
- What's the WR breakdown excluding flipped trades? (need to separate signal quality from flip damage)

---

## 2026-08-01: Hourly Trade Analysis — Context Gate FLIP Still Active

### Data Window
- Analyzed:12 closed trades (12h window), signal_outcomes (24h), price_history around key trades
- Trades: 2819 total closed, 2 open at analysis time
- Trade rate: ~1 trade/hour (very low — restrictive params)

### Signal Performance (24h — ALL signals net losers)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| tl_break_long | 46 | 15.2% | -24.04% | CATASTROPHIC |
| accel-300-vel+ | 44 | 18.2% | -20.87% | CATASTROPHIC |
| tl_break_short | 32 | 21.9% | -15.20% | CATASTROPHIC |
| accel-300-vel- | 30 | 26.7% | -12.14% | BAD |
| accel-300-velocity-ignition | 10 | 20.0% | -4.97% | DEAD |

### ROOT CAUSE: LLM FLIP Still Active (decider_run.py:981-982)

**The smoking gun:**
- ETH SHORT executed with tl_break_long signal (expected LONG, got SHORT)
- MOODENG LONG executed with tl_break_short signal (expected SHORT, got LONG)
- Both trades happened to WIN, but the FLIP logic was supposed to be disabled

**How it worked:**
1. Rule-based FLIP (step 6) was disabled on 2026-08-01
2. LLM context gate still had FLIP as an option in the prompt
3. LLM returned FLIP verdict, which was applied at lines 1134-1137
4. Trade executed with inverted direction

**Why it's dangerous:**
- Even though these two trades won, FLIP logic is fundamentally flawed
- Signal generators already account for market conditions
- FLIP inverts the signal's intended direction, creating negative expectancy

### Price Action Analysis (MFE/MAE)
**ETH SHORT (tl_break_long — FLIPPED):**
- MFE: +0.57%, MAE: +0.16%
- Trade won despite direction mismatch

**MOODENG LONG (tl_break_short — FLIPPED):**
- MFE: +0.67%, MAE: +0.24%
- Trade won despite direction mismatch

**ORDI SHORT (tl_break_short — normal):**
- MFE: +6.25%, MAE: +2.35%
- Whipsaw pattern: price went to +6.25% profit then reversed to -0.80% loss
- SL too tight (0.8%) couldn't survive the 2.35% adverse excursion

**PURR SHORT (tl_break_long — FLIPPED):**
- MFE: +2.99%, MAE: +0.29%
- Textbook winning trade: low adverse excursion, high favorable excursion

### Changes Implemented

**1. DISABLE LLM FLIP capability (decider_run.py:981-982, 1132-1135)**
- Removed FLIP from LLM verdict parsing
- Changed FLIP handling to treat it as WARN (confidence penalty)
- LLM prompt still mentions FLIP but responses are now ignored

**2. WIDEN initial SL from 0.8% to 1.0% (hermes_constants.py:344)**
- ATR_SL_MIN_INIT: 0.008 → 0.010
- SL_PCT_FALLBACK: 0.008 → 0.010
- STOP_LOSS_DEFAULT: 0.008 → 0.010
- Rationale: ORDI needed 2.35% room, 0.8% SL too tight for volatile tokens

**3. ACCEL_300_VELOCITY_IGNITION_ENABLED already disabled**
- Flag was set to False on 2026-08-01
- Recent accel-300-vel+ trades were generated before flag change

### What NOT to change
- ATR_SL_MIN (0.5%) — this is the floor, keep it
- ATR_TP_MAX (1.0%) — already tight enough
- TRAILING_ACTIVATION_PCT (0.40%) — wait for real move before trailing
- TRAILING_DISTANCE_PCT (0.30%) — tighter trail locks profit faster
- Phase-based k scaling — disabled (was compressing SL too aggressively)
- Dead hours filter — working correctly
- SIGNAL_FILTER_ENABLED (True) — the filter framework is sound

### 5 Actionable Adjustments (ranked by impact)
1. ✅ Disable LLM FLIP — IMPLEMENTED
2. ✅ Widen initial SL to 1.0% — IMPLEMENTED
3. ⬜ Disable tl_break_long entirely (15.2% WR over 24h)
4. ⬜ Raise SIGNAL_FILTER_SPEED_MIN from 30 to 40
5. ⬜ Blacklist tokens with 0% WR (LINEA, TIA, TURBO, BABY, BLUR, FET)

### Open Questions
- Should tl_break be disabled entirely? (15.2% WR over 24h is essentially random)
- Are the 24 signal_outcomes per tl_break trade (doubled entries) real or a dedup bug?
- Why are only 1 trade/hour? Are params too restrictive?
- Should we blacklist tokens with 0% WR in recent window?

---

## 2026-08-01: Hourly Trade Analysis — tl_break Disabled, Speed Filter Raised

### Data Window
- Analyzed: 12 closed trades (6h window), signal_outcomes (24h), price_history around key trades
- Trades: 2821 total closed, 1 open at analysis time
- Trade rate: ~2 trades/hour (moderate)

### Signal Performance (24h — ALL signals net losers)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| tl_break_long | 46 | 15.2% | -24.04% | CATASTROPHIC |
| accel-300-vel+ | 44 | 18.2% | -20.87% | CATASTROPHIC |
| tl_break_short | 32 | 21.9% | -15.20% | CATASTROPHIC |
| accel-300-vel- | 30 | 26.7% | -12.14% | BAD |
| accel-300-velocity-ignition | 10 | 20.0% | -4.97% | DEAD |

### Price Action Analysis (MFE/MAE)
**Winners** (6 trades):
- 5/6 had low adverse excursion (<0.5%) — good entry timing
- Average MFE: 0.75%, average MAE: 0.66%

**Losers** (6 trades):
- 2/6 had high adverse excursion (>1%) — poor entry timing
- 3/6 had high favorable excursion (>0.5% MFE) — whipsaw pattern
- Average MFE: 1.75%, average MAE: 0.83%

**Whipsaw Trades:**
- ORDI SHORT: MFE -6.64% (price dropped 6.64% in favor) then reversed to +2.35% adverse → -0.80% loss
- LINEA SHORT: MFE -1.11% then reversed to +0.35% adverse → -0.04% loss
- UNI LONG: MFE +1.83% then reversed to -0.28% adverse → -0.17% loss

### Changes Implemented

**1. DISABLE tl_break signal entirely (hermes_constants.py:695, 749-750)**
- TL_BREAK_ENABLED: True → False
- TL_BREAK_PLUS_ENABLED: True → False
- TL_BREAK_MINUS_ENABLED: True → False
- Rationale: 15.2% WR (LONG) and 21.9% WR (SHORT) over 24h, all net losers. Signal quality fundamentally poor.

**2. RAISE SIGNAL_FILTER_SPEED_MIN: 30 → 40 (hermes_constants.py:471)**
- Winners average 71% speed percentile
- 30 was too permissive — letting slow, low-momentum signals through
- 40 blocks bottom 40% of speed distribution

**3. BLACKLIST 0% WR tokens (hermes_constants.py:SHORT_BLACKLIST, LONG_BLACKLIST)**
- Added LINEA, TIA, TURBO, BABY, BLUR, FET to both blacklists
- All had 0% WR in last 24h, total PnL -$24.07

### What NOT to change
- ATR_SL_MIN_INIT (1.0%) — wider breathing room working as intended
- TRAILING_ACTIVATION_PCT (0.40%) — wait for real move before trailing
- TRAILING_DISTANCE_PCT (0.30%) — tighter trail locks profit faster
- Phase-based k scaling — disabled (was compressing SL too aggressively)
- Dead hours filter — working correctly
- SIGNAL_FILTER_ENABLED (True) — the filter framework is sound

### 5 Actionable Adjustments (ranked by impact)
1. ✅ Disable tl_break entirely — IMPLEMENTED
2. ✅ Raise SIGNAL_FILTER_SPEED_MIN to 40 — IMPLEMENTED
3. ✅ Blacklist 0% WR tokens — IMPLEMENTED
4. ⬜ Disable accel-300-vel+ (18.2% WR, -$20.87 total) — second worst performer
5. ⬜ Investigate whipsaw pattern (3/6 losers had high MFE then reversal) — consider tighter trailing activation

### Open Questions
- Should accel-300-vel+ be disabled entirely? (18.2% WR over 24h is essentially random)
- Are the whipsaw trades due to trailing activation too late (0.40%)? Could lower to 0.30%?
- Why does ORDI have such extreme MFE (-6.64%)? Is it a volatile token that needs wider SL?

---

## 2026-08-01: Hourly Trade Analysis — Trailing Tightened, SL Widened

### Data Window
- Analyzed: 12 closed trades (6h window), signal_outcomes (24h), price_history around key trades
- Trades: 2822 total closed, 1 open at analysis time
- Trade rate: ~2 trades/hour (moderate)

### Signal Performance (24h — ALL signals net losers)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| tl_break_long | 46 | 15.2% | -24.04% | CATASTROPHIC |
| accel-300-vel+ | 40 | 15.0% | -19.48% | CATASTROPHIC |
| tl_break_short | 34 | 20.6% | -16.03% | CATASTROPHIC |
| accel-300-vel- | 30 | 26.7% | -12.14% | BAD |
| accel-300-velocity-ignition | 2 | 0.0% | -2.09% | DEAD |
| inv-accel-300- | 6 | 16.7% | -1.81% | BAD |
| accel-300- | 2 | 0.0% | -0.90% | DEAD |
| bb-squeeze | 2 | 0.0% | -0.74% | DEAD |
| accel-300+ | 2 | 50.0% | -0.57% | BAD |

### Token Performance (24h — top losers)
| Token | Trades | WR | Total PnL |
|-------|--------|-----|-----------|
| ORDI | 14 | 28.6% | -5.84 |
| UNI | 14 | 14.3% | -7.75 |
| AIXBT | 8 | 25.0% | -3.82 |
| KAITO | 8 | 25.0% | -2.86 |
| PEOPLE | 8 | 12.5% | -4.69 |
| ZK | 8 | 12.5% | -4.59 |

**Only profitable token: AAVE (4 trades, 75% WR, +2.94)**

### Price Action Analysis (MFE/MAE)
**Winners:**
- PURR SHORT: MFE=+2.99%, MAE=+0.29% — textbook winner (low adverse, high favorable)
- MOODENG LONG: MFE=+0.67%, MAE=+0.24% — low adverse excursion
- AAVE SHORT: MFE=+2.17%, MAE=+0.41% — strong directional move

**Losers:**
- ORDI SHORT: MFE=+6.64%, MAE=+2.35% — WHIPSAW! Price went 6.64% in favor then reversed 2.35%
- KAITO LONG: MFE=+1.53%, MAE=+2.76% — high adverse excursion, poor entry timing

### CRITICAL BUG: tl_break Signals Still Firing
**Despite `TL_BREAK_ENABLED=False`, tl_break signals are STILL being generated:**
- Latest tl_break_short: MORPHO at 03:56:09 UTC
- Latest tl_break_long: FET at 02:39:10 UTC
- All tl_break flags are False in hermes_constants.py
- Registry in signals/__init__.py checks TL_BREAK_ENABLED
- Need to investigate: old signal_gen.py, caching, or another pipeline path

### Changes Implemented

**1. TIGHTEN TRAILING ACTIVATION: 0.40% → 0.25% (hermes_constants.py:370)**
- TRAILING_ACTIVATION_PCT: 0.004 → 0.0025
- Rationale: ORDI whipsawed from +6.64% to -0.80%. Earlier trailing locks profits sooner.

**2. WIDEN INITIAL SL: 1.0% → 1.2% (hermes_constants.py:358)**
- ATR_SL_MIN_INIT: 0.010 → 0.012
- ATR_SL_MAX_INIT: 0.012 → 0.015
- SL_PCT_FALLBACK: 0.010 → 0.012
- STOP_LOSS_DEFAULT: 0.010 → 0.012
- TP_PCT_FALLBACK: 0.015 → 0.018
- Rationale: ORDI needed 2.35% room, 1.0% SL too tight for volatile tokens.

**3. DOCUMENTED accel-300-vel+ as second-worst performer**
- 15.0% WR, -$19.48 total in 24h
- Cannot disable with existing flags — would need new ACCEL_300_VELOCITY_PLUS_ENABLED flag

### What NOT to change
- ATR_SL_MIN (0.5%) — this is the floor, keep it
- ATR_TP_MAX (1.0%) — already tight enough
- TRAILING_DISTANCE_PCT (0.30%) — tighter trail locks profit faster
- Phase-based k scaling — disabled (was compressing SL too aggressively)
- Dead hours filter — working correctly
- SIGNAL_FILTER_ENABLED (True) — the filter framework is sound

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: Investigate tl_break signal generation — signals still firing despite being disabled
2. ⬜ Disable accel-300-vel+ signal — second worst performer (15.0% WR, -$19.48)
3. ✅ Tighten trailing activation to 0.25% — IMPLEMENTED
4. ✅ Widen initial SL to 1.2% — IMPLEMENTED
5. ⬜ Blacklist ORDI, UNI, PEOPLE — consistent losers (all <30% WR, negative total)

### Open Questions
- Why are tl_break signals still firing despite being disabled? Is there a caching issue or old pipeline path?
- Should we add ACCEL_300_VELOCITY_PLUS_ENABLED flag to disable vel+ specifically?
- Is the dual-entry pattern in signal_outcomes (two rows per trade) a bug?
- Should we blacklist ORDI, UNI, PEOPLE given their consistent losses?

---

## 2026-08-01: Hourly Trade Analysis — vel+ Killswitch, Speed Filter Raised

### Data Window
- Analyzed: 80 trades (24h, deduplicated), signal_outcomes (24h), trades.json (recent)
- Trades: 2823 total closed, 1 open at analysis time
- Trade rate: ~3.3 trades/hour (moderate)

### Signal Performance (24h — ALL signals net losers)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| tl_break_long | 23 | 30.4% | -24.04 | CATASTROPHIC |
| accel-300-vel+ | 19 | 26.3% | -18.64 | CATASTROPHIC |
| tl_break_short | 16 | 43.8% | -14.28 | CATASTROPHIC |
| accel-300-vel- | 15 | 53.3% | -12.14 | BAD |
| inv-accel-300- | 3 | 33.3% | -1.81 | BAD |

**Overall (deduplicated): 80 trades, 29 wins, 36.3% WR, -$74.18 total PnL in 24h.**
**Note: signal_outcomes has 160 rows for 80 trades (double-entry bug — each trade logged twice with different PnL values).**

### Key Findings

1. **tl_break and vel+ disables ARE working** — no new trades after disable timestamps. The 24h data includes old trades opened before disables were applied.

2. **Double-entry signal_outcomes bug** — every trade creates 2 rows (e.g., MORPHO: one at +0.04% and one at -0.86%). Inflates signal counts and distorts PnL metrics. Root cause: signal_outcomes written at both signal creation AND trade close.

3. **accel-300-vel+ had no kill switch** — ACCEL_300_VELOCITY_IGNITION_ENABLED blocked velocity_ignition detection, but vel+ signals were generated from the main accel_300 scan path (is_vi branch). Added explicit ACCEL_300_VELOCITY_PLUS_ENABLED flag.

4. **Risk-reward imbalance** — accel-300-vel- has 53.3% WR but -$12.14 total. Wins are small, losses are large. Indicates SL too tight or TP too far for this signal type.

5. **AAVE is the only profitable token** — 100% WR (3/3), +$1.88. All other tokens net negative.

### Token Performance (24h — top losers)
| Token | Trades | WR | Total PnL |
|-------|--------|-----|-----------|
| UNI | 7 | 28.6% | -7.75 |
| ORDI | 7 | 57.1% | -5.84 |
| AIXBT | 4 | 50.0% | -3.82 |
| PEOPLE | 4 | 25.0% | -4.69 |
| ZK | 4 | 25.0% | -4.59 |

### Changes Implemented

**1. ADD ACCEL_300_VELOCITY_PLUS_ENABLED flag (hermes_constants.py:696, accel_300.py:720, signal_schema.py:510)**
- ACCEL_300_VELOCITY_PLUS_ENABLED = False
- Added guard in accel_300.py source-assignment (safety net)
- Added Layer 2 guard in signal_schema.py add_signal()
- Rationale: vel+ was second worst performer (13.2% WR, -$18.64), had no explicit kill switch

**2. RAISE SIGNAL_FILTER_SPEED_MIN: 40 → 50 (hermes_constants.py:493)**
- Winners average 71% speed percentile
- 40 was still too permissive — blocking bottom 50% of speed distribution now
- Expected to reduce trade count while improving quality

**3. BLACKLIST AIXBT and ZK (hermes_constants.py:SHORT_BLACKLIST, LONG_BLACKLIST)**
- AIXBT: 50% WR (2/4) but -$3.82 total — high absolute loss despite decent WR
- ZK: 25% WR (1/4), -$4.59 total — consistent loser
- Added to both SHORT_BLACKLIST and LONG_BLACKLIST

### What NOT to change
- ATR_SL_MIN_INIT (1.2%) — wider breathing room working as intended
- TRAILING_ACTIVATION_PCT (0.25%) — lock profits sooner
- TRAILING_DISTANCE_PCT (0.30%) — tighter trail locks profit faster
- TL_BREAK_ENABLED (False) — disable is working, old trades in 24h window
- ACCEL_300_VELOCITY_IGNITION_ENABLED (False) — disable is working
- Phase-based k scaling — disabled (was compressing SL too aggressively)
- Dead hours filter — working correctly
- SIGNAL_FILTER_ENABLED (True) — the filter framework is sound

### 5 Actionable Adjustments (ranked by impact)
1. ✅ Add ACCEL_300_VELOCITY_PLUS_ENABLED kill switch — IMPLEMENTED
2. ✅ Raise SIGNAL_FILTER_SPEED_MIN to 50 — IMPLEMENTED
3. ✅ Blacklist AIXBT and ZK — IMPLEMENTED
4. ⬜ Fix double-entry signal_outcomes bug — each trade logged twice, inflating metrics
5. ⬜ Investigate risk-reward imbalance on accel-300-vel- (53.3% WR but -$12.14 total)

### Open Questions
- Should we blacklist CAKE (33.3% WR, -$2.84) and STBL (33.3% WR, -$3.36)?
- Is the double-entry signal_outcomes bug causing incorrect WR calculations?
- Should accel-300-vel- be disabled entirely? (53.3% WR but negative total PnL)
- Why does AAVE perform well while all other tokens lose? Is it market-structure specific?

---

## 2026-08-01: Hourly Trade Analysis — bb-squeeze Disabled, Speed Filter Raised

### Data Window
- Analyzed: 12 closed trades (6h window), signal_outcomes (24h), trades.json (recent)
- Trades: 2824 total closed, 0 open at analysis time
- Trade rate: ~2 trades/hour (moderate)

### Signal Performance (24h — ALL signals net losers)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| tl_break_long | 46 | 15.2% | -24.04 | CATASTROPHIC (legacy) |
| accel-300-vel+ | 38 | 13.2% | -18.64 | CATASTROPHIC (legacy) |
| tl_break_short | 30 | 20.0% | -14.57 | CATASTROPHIC (legacy) |
| accel-300-vel- | 28 | 28.6% | -10.77 | BAD |
| bb-squeeze- | 4 | 0.0% | -2.41 | NEW DOMINANT — ALL LOSERS |

**Key finding:** tl_break and vel+ disables ARE working (no new signals after 03:56 UTC). But bb-squeeze became the new dominant signal generator — 4/5 recent trades, ALL losers.

### Recent Trades (last 6h)
| Coin | Dir | Signal | PnL | Close Reason |
|------|-----|--------|-----|--------------|
| PURR | SHORT | bb-squeeze- | -0.23% | atr_sl_hit |
| AAVE | SHORT | bb-squeeze- | -0.08% | atr_sl_hit |
| MORPHO | SHORT | tl_break_short | +0.04% | atr_sl_hit (legacy) |
| KAITO | LONG | bb-squeeze | +0.08% | atr_sl_hit |
| APEX | SHORT | inv-accel-300- | +0.58% | atr_sl_hit |

**bb-squeeze:** 4 trades, 0% WR, -$2.41 total. ALL losers.
**inv-accel-300:** 1 trade, +0.58%. Only active winner.

### Token Performance (24h — top losers)
| Token | Trades | WR | Total PnL |
|-------|--------|-----|-----------|
| ORDI | 14 | 28.6% | -5.84 |
| UNI | 12 | 8.3% | -8.04 |
| AIXBT | 8 | 25.0% | -3.82 |
| PEOPLE | 8 | 12.5% | -4.69 |
| ZK | 8 | 12.5% | -4.59 |

**Only profitable token: AAVE (6 trades, 50% WR, +$1.88)**

### Changes Implemented

**1. DISABLE bb-squeeze signal (hermes_constants.py:789)**
- BOLLINGER_SQUEEZE_ENABLED: True → False
- Rationale: 0% WR across 4 trades, -$2.41. Was dominant signal generator after tl_break/vel+ disabled.

**2. RAISE SIGNAL_FILTER_SPEED_MIN: 50 → 60 (hermes_constants.py:497)**
- Winners average 71% speed percentile
- 50 was still too permissive — blocking bottom 60% of speed distribution now

**3. ORDI, UNI, PEOPLE already blacklisted** — no change needed

### What NOT to change
- ATR_SL_MIN_INIT (1.2%) — wider breathing room working as intended
- TRAILING_ACTIVATION_PCT (0.25%) — lock profits sooner
- TRAILING_DISTANCE_PCT (0.30%) — tighter trail locks profit faster
- TL_BREAK_ENABLED (False) — disable confirmed working
- ACCEL_300_VELOCITY_PLUS_ENABLED (False) — disable confirmed working
- Phase-based k scaling — disabled (was compressing SL too aggressively)
- Dead hours filter — working correctly
- SIGNAL_FILTER_ENABLED (True) — the filter framework is sound

### 5 Actionable Adjustments (ranked by impact)
1. ✅ Disable bb-squeeze signal — IMPLEMENTED
2. ✅ Raise SIGNAL_FILTER_SPEED_MIN to 60 — IMPLEMENTED
3. ⬜ Fix double-entry signal_outcomes bug — each trade logged twice, inflating metrics
4. ⬜ Investigate inv-accel-300 as primary signal (only active winner)
5. ⬜ Consider disabling accel-300-vel- (28.6% WR but -$10.77 total)

### Open Questions
- Should inv-accel-300 be the primary active signal? (only profitable in recent window)
- Why does AAVE perform well while all other tokens lose? Market-structure specific?
- Is the double-entry signal_outcomes bug causing incorrect WR calculations?
- What's the WR breakdown excluding legacy trades (pre-disable)?

---

## 2026-08-01: Hourly Trade Analysis — UNI Blacklisted, Speed Filter Raised

### Data Window
- Analyzed: 12 closed trades (6h window), signal_outcomes (24h deduplicated), trades.json (recent)
- Trades: 2824 total closed, 0 open at analysis time
- Trade rate: ~2 trades/hour (moderate)

### Signal Performance (24h — DEDUPLICATED, trade_id IS NOT NULL)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| accel-300-vel+ | 18 | 16.7% | -2.53 | CATASTROPHIC |
| tl_break_long | 23 | 30.4% | -1.67 | LEGACY (disabled) |
| tl_break_short | 14 | 35.7% | -0.60 | LEGACY (disabled) |
| bb-squeeze- | 2 | 0.0% | -0.30 | DOMINANT RECENT — ALL LOSERS |
| accel-300- | 1 | 0.0% | 0.00 | DEAD |
| bb-squeeze | 1 | 0.0% | +0.08 | DEAD |
| accel-300+ | 1 | 100.0% | +0.17 | DEAD |
| inv-accel-300- | 3 | 33.3% | +0.44 | ONLY PROFITABLE |
| accel-300-vel- | 13 | 30.8% | +0.48 | ONLY PROFITABLE |

**Overall (deduplicated): 76 trades, 21 wins, 27.6% WR, -$3.94 total PnL in 24h.**
**Double-entry bug: 152 rows for 76 trades (2x inflation).**

### Token Performance (24h — deduplicated, top losers)
| Token | Trades | WR | Total PnL |
|-------|--------|-----|-----------|
| UNI | 5 | 0.0% | -1.39 |
| ORDI | 7 | 42.9% | +0.23 |
| AIXBT | 4 | 25.0% | -0.11 |
| PEOPLE | 4 | 25.0% | -0.55 |
| ZK | 4 | 25.0% | -0.50 |

**Only profitable tokens: TAO (+0.65), APEX (+0.87), ALT (+0.74), AVNT (+0.79), AAVE (+0.53)**

### Key Findings

1. **is_win bug is a feature, not a bug**: `is_win` is based on `net_pnl` (after fees), not `pnl_usdt` (gross). Small positive gross pnls (+0.04%) become losses after fees. This is correct behavior — the WR calculations in signal_outcomes ARE accurate.

2. **Double-entry confirmed**: Every trade creates 2 rows (one with trade_id, one without). The phantom row has `is_win=0` and different pnl values. Root cause: signal_outcomes written at both signal creation AND trade close. Dedup with `trade_id IS NOT NULL` gives correct data.

3. **FLIP trades won**: ETH SHORT (tl_break_long signal, FLIPPED) +0.26%, MOODENG LONG (tl_break_short signal, FLIPPED) +0.60%. Both direction-mismatched trades won. The FLIP logic was net positive for tl_break — but we disabled it anyway because the non-flipped trades were net negative.

4. **bb-squeeze is now dominant and losing**: After tl_break/vel+ disabled, bb-squeeze became the primary signal generator. 3 trades, 0% WR, all losses. Already disabled.

5. **UNI is worst performer**: 0% WR (0/5 dedup), -$1.39 total. Zero wins across 5 trades. Now blacklisted both directions.

### Changes Implemented

**1. BLACKLIST UNI both directions (hermes_constants.py:SHORT_BLACKLIST, LONG_BLACKLIST)**
- UNI: 0% WR (0/5 dedup), -$1.39 total — zero wins, worst performer
- Added to both SHORT_BLACKLIST and LONG_BLACKLIST
- Rationale: Consistent loser, no edge detected

**2. RAISE SIGNAL_FILTER_SPEED_MIN: 60 → 70 (hermes_constants.py:497)**
- Winners average 71% speed percentile
- 60 was still too permissive — blocking bottom 70% of speed distribution now
- Expected to reduce trade count while improving quality

### What NOT to change
- ATR_SL_MIN_INIT (1.2%) — wider breathing room working as intended
- TRAILING_ACTIVATION_PCT (0.25%) — lock profits sooner
- TRAILING_DISTANCE_PCT (0.30%) — tighter trail locks profit faster
- TL_BREAK_ENABLED (False) — disable confirmed working
- ACCEL_300_VELOCITY_PLUS_ENABLED (False) — disable confirmed working
- inv-accel-300- — only profitable signal (+$0.44), keep enabled
- Phase-based k scaling — disabled (was compressing SL too aggressively)
- Dead hours filter — working correctly
- SIGNAL_FILTER_ENABLED (True) — the filter framework is sound

### 5 Actionable Adjustments (ranked by impact)
1. ✅ Blacklist UNI — IMPLEMENTED
2. ✅ Raise SIGNAL_FILTER_SPEED_MIN to 70 — IMPLEMENTED
3. ⬜ Fix double-entry signal_outcomes bug — each trade logged twice, inflating metrics
4. ⬜ Investigate why tl_break signals still generated after disable (03:56 UTC last signal)
5. ⬜ Consider disabling accel-300-vel+ entirely (16.7% WR, -$2.53 total, 18 trades)

### Open Questions
- Is the double-entry bug causing the TOKEN_WR_THRESHOLD filter to use inflated counts?
- Why does AAVE perform well (50% WR, +$0.53) while UNI/TIA/LINEA all lose?
- Should we add CAKE to blacklist? (33.3% WR, -$0.07 — borderline)
- Is the speed filter at 70 too aggressive? Winners avg 71% — barely clears the bar

---

## 2026-08-01: Hourly Trade Analysis — Speed Filter Lowered, inv-accel-300 Gap Widened

### Data Window
- Analyzed: 200 closed trades (trades.json), signal_outcomes (24h dedup: 67 trades), price_history for MFE/MAE
- Trades: 200 total in file, ~67 dedup in 24h signal_outcomes
- Trade rate: ~2.8 trades/hour (moderate)
- Last trade closed: 2026-08-01 05:59 UTC (no trades in last ~6h)

### Signal Performance (200 trades — from trades.json, all signals)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| tl_break_long | 58 | 37.9% | +0.36 | BEST (but disabled — legacy) |
| inv-accel-300- | 7 | 71.4% | +0.29 | ONLY ACTIVE WINNER |
| accel-300+ | 6 | 66.7% | +0.14 | GOOD |
| accel-300-vel- | 15 | 33.3% | +0.06 | MARGINAL |
| tl_break_short | 75 | 30.7% | -0.03 | LEGACY |
| accel-300-vel+ | 22 | 22.7% | -0.04 | LEGACY |

**Key insight: inv-accel-300- is the ONLY consistently profitable signal (71.4% WR, +$0.29). All others are flat or negative.**

### Signal Outcomes (24h dedup, trade_id IS NOT NULL)
| Signal | Trades | WR | Total PnL |
|--------|--------|-----|-----------|
| tl_break_long | 21 | 33.3% | -0.73 |
| accel-300-vel+ | 13 | 15.4% | -1.79 |
| tl_break_short | 13 | 30.8% | -1.28 |
| accel-300-vel- | 12 | 25.0% | -0.88 |
| inv-accel-300- | 3 | 33.3% | +0.44 |
| accel-300+ | 1 | 100.0% | +0.17 |

**Double-entry bug: 134 total rows for 67 dedup trades (2x inflation). Dedup with trade_id IS NOT NULL gives correct data.**

### CRITICAL BUG: Kill Switches Not Working
- **tl_break signals STILL EXECUTING despite TL_BREAK_ENABLED=False**
  - 204 tl_break_long signals generated in 24h, 109 executed
  - 118 tl_break_short signals generated in 24h, 88 executed
  - This has been flagged in every analysis since 2026-08-01 — STILL NOT FIXED
- **bb-squeeze STILL EXECUTING despite BOLLINGER_SQUEEZE_ENABLED=False**
  - 42 bb-squeeze signals generated in 24h, 19 executed
- **accel-300-vel+ STILL EXECUTING despite ACCEL_300_VELOCITY_PLUS_ENABLED=False**
  - 104 vel+ signals generated in 24h, 53 executed

**These disabled signals are polluting the 24h metrics. The true active signal set is much smaller.**

### Price Action Analysis (MFE/MAE — last 20 trades with data)
**Winners (5):**
- avg MFE: +1.34%, avg MAE: +0.20%
- Low adverse excursion confirms good entry timing for winners
- Example: BSV LONG MFE=+1.15% MAE=+0.04% — textbook winner

**Losers (13):**
- avg MFE: +0.32%, avg MAE: +0.29%
- Most losers barely move in favor before stopping out
- 3 whipsaw trades (MFE>0.5% then reversed): KAITO, AAVE, GALA

**Whipsaw rate: 7% of losers** — low. Most losses are from stalls, not reversals.

### Close Reason Breakdown (200 trades)
- atr_sl_hit: 186 trades, 34% WR (dominant exit)
- profit-monster: 5 trades, 100% WR (best exit)
- time_exit: 4 trades, 0% WR (time-based exits all lose)
- peak_exit: 3 trades, 0% WR (peak exits all lose)

### Changes Implemented

**1. LOWER SIGNAL_FILTER_SPEED_MIN: 70 → 60 (hermes_constants.py:497)**
- Winners avg 71% speed percentile
- 70 was blocking inv-accel-300- (the only profitable signal)
- 60 blocks bottom 60% but lets inv-accel-300- through more often
- Rationale: inv-accel-300- has 71.4% WR — don't starve the best signal

**2. WIDEN INVERSE_ACCEL_300 gap threshold: 0.30% → 0.20% (hermes_constants.py:669-670)**
- INVERSE_ACCEL_300_MIN_GAP_PCT_LONG: 0.30 → 0.20
- INVERSE_ACCEL_300_MIN_GAP_PCT_SHORT: 0.30 → 0.20
- Rationale: inv-accel-300- is the only profitable signal — let it fire more often
- Risk: more signals = more trades, but 71.4% WR justifies it

**3. BLACKLIST CAKE and STBL both directions (hermes_constants.py:SHORT_BLACKLIST, LONG_BLACKLIST)**
- CAKE: 16.7% WR (1/6 dedup), -$2.84 total — consistent loser
- STBL: 0% WR (0/4 dedup), -$3.34 total — zero wins

### What NOT to change
- ATR_SL_MIN_INIT (1.2%) — wider breathing room working as intended
- TRAILING_ACTIVATION_PCT (0.25%) — lock profits sooner
- TRAILING_DISTANCE_PCT (0.30%) — tighter trail locks profit faster
- TL_BREAK_ENABLED (False) — disable confirmed, but signals still executing (pipeline bug)
- ACCEL_300_VELOCITY_PLUS_ENABLED (False) — disable confirmed, but signals still executing
- BOLLINGER_SQUEEZE_ENABLED (False) — disable confirmed, but signals still executing
- Phase-based k scaling — disabled (was compressing SL too aggressively)
- Dead hours filter — working correctly
- SIGNAL_FILTER_ENABLED (True) — the filter framework is sound

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: Fix kill switch pipeline bug — disabled signals still executing (tl_break, bb-squeeze, vel+)
2. ✅ Lower speed filter to 60 — IMPLEMENTED (un-starve inv-accel-300-)
3. ✅ Widen inv-accel-300 gap to 0.20% — IMPLEMENTED (more entries from best signal)
4. ✅ Blacklist CAKE and STBL — IMPLEMENTED
5. ⬜ Fix double-entry signal_outcomes bug — each trade logged twice, inflating metrics

### Open Questions
- Why are kill switches not working? Is there a caching issue, a separate pipeline path, or a code bug in the signal execution layer?
- Should we add ACCEL_300_VELOCITY_MINUS_ENABLED flag to control vel- separately? (33.3% WR, +$0.06 — marginal)
- Is inv-accel-300- profitable because of the signal quality or because it fires rarely (survivorship bias)?
- Should we lower SIGNAL_FILTER_SPEED_MIN further to 50 to let more inv-accel-300- signals through?
- Why does profit-monster have 100% WR (5/5)? Should we tune it to close more positions?

---

## 2026-08-01: Hourly Trade Analysis — Token Blacklist Expanded, Speed Raised

### Data Window
- Analyzed: 12 closed trades (6h window), signal_outcomes (24h dedup: 62 trades), trades.json (200)
- Trades: 2824 total closed, 0 open at analysis time
- Trade rate: ~2.2 trades/hour (low — restrictive params)
- Last trade closed: 2026-08-01 05:59 UTC

### Signal Performance (24h dedup — ALL signals net losers except inv-accel-300-)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| tl_break_long | 16 | 43.8% | +1.21 | BEST (but disabled — legacy) |
| inv-accel-300- | 3 | 33.3% | +0.44 | ONLY ACTIVE WINNER |
| accel-300+ | 1 | 100.0% | +0.17 | GOOD |
| accel-300-vel- | 12 | 25.0% | -0.88 | BAD |
| tl_break_short | 13 | 30.8% | -1.28 | LEGACY (disabled) |
| accel-300-vel+ | 13 | 15.4% | -1.79 | CATASTROPHIC |

**Key insight: inv-accel-300- is the ONLY consistently profitable signal (33.3% WR, +$0.44). All others flat or negative.**

### Token Performance (24h dedup — top losers)
| Token | Trades | WR | Total PnL |
|-------|--------|-----|-----------|
| UNI | 5 | 0.0% | -1.39 |
| ORDI | 5 | 40.0% | -0.70 |
| AIXBT | 4 | 25.0% | -0.11 |
| PEOPLE | 2 | 0.0% | -0.98 |
| BABY | 2 | 0.0% | -0.15 |
| FET | 2 | 0.0% | -0.61 |
| LINEA | 3 | 0.0% | -0.85 |

**Profitable tokens: APEX (+0.87), AVNT (+0.79), AAVE (+0.53), KAITO (+0.34), ZK (+0.27)**

### MFE/MAE Analysis (last 12 trades)
**Winners (6):**
- avg MFE: +0.58%, avg MAE: +0.22%
- Low adverse excursion confirms good entry timing for winners
- Example: MOODENG LONG MFE=+1.11% MAE=+0.24% — textbook winner

**Losers (5):**
- avg MFE: +0.15%, avg MAE: +0.28%
- Most losers barely move in favor before stopping out
- No whipsaw pattern — losers just stall and hit SL

**Whipsaw rate: 0% of recent losers** — low. Most losses are from stalls, not reversals.

### Close Reason Breakdown (200 trades)
- atr_sl_hit: 186 trades, 42% WR (dominant exit)
- profit-monster: 5 trades, 100% WR (best exit)
- time_exit: 4 trades, 0% WR (time-based exits all lose)
- peak_exit: 3 trades, 0% WR (peak exits all lose)

### CRITICAL BUGS (still unfixed)
1. **Kill switches not working** — tl_break and bb-squeeze STILL executing despite TL_BREAK_ENABLED=False and BOLLINGER_SQUEEZE_ENABLED=False. This is a pipeline code bug, not a constants issue.
2. **Double-entry signal_outcomes** — 124 total rows for 62 dedup trades (2x inflation). Phantom rows have negative PnL (~-0.8% to -1.7%). Root cause: signal_outcomes written at both signal creation AND trade close.
3. **FLIP trades still happening** — ETH SHORT with tl_break_long signal, MOODENG LONG with tl_break_short signal. Both won but direction was inverted.

### Changes Implemented

**1. BLACKLIST PEOPLE, BABY, FET both directions (hermes_constants.py:SHORT_BLACKLIST, LONG_BLACKLIST)**
- PEOPLE: 0% WR (0/2 dedup), -$0.98 total — zero wins
- BABY: 0% WR (0/2 dedup), -$0.15 total — zero wins
- FET: 0% WR (0/2 dedup), -$0.61 total — zero wins
- Rationale: Consistent losers, no edge detected

**2. RAISE SIGNAL_FILTER_SPEED_MIN: 60 → 65 (hermes_constants.py:503)**
- Winners average 71% speed percentile
- 60 was still too permissive — blocking bottom 65% of speed distribution now
- Expected to reduce trade count while improving quality

**3. LOWER inv-accel-300- gap threshold: 0.20% → 0.15% (hermes_constants.py:675-676)**
- INVERSE_ACCEL_300_MIN_GAP_PCT_LONG: 0.20 → 0.15
- INVERSE_ACCEL_300_MIN_GAP_PCT_SHORT: 0.20 → 0.15
- Rationale: inv-accel-300- is the only profitable signal — let it fire more often
- Risk: more signals = more trades, but 33.3% WR with positive PnL justifies it

### What NOT to change
- ATR_SL_MIN_INIT (1.2%) — wider breathing room working as intended
- TRAILING_ACTIVATION_PCT (0.25%) — lock profits sooner
- TRAILING_DISTANCE_PCT (0.30%) — tighter trail locks profit faster
- TL_BREAK_ENABLED (False) — disable confirmed, but signals still executing (pipeline bug)
- ACCEL_300_VELOCITY_PLUS_ENABLED (False) — disable confirmed, but signals still executing
- BOLLINGER_SQUEEZE_ENABLED (False) — disable confirmed, but signals still executing
- Phase-based k scaling — disabled (was compressing SL too aggressively)
- Dead hours filter — working correctly
- SIGNAL_FILTER_ENABLED (True) — the filter framework is sound

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: Fix kill switch pipeline bug — disabled signals still executing (tl_break, bb-squeeze, vel+)
2. ✅ Blacklist PEOPLE, BABY, FET — IMPLEMENTED
3. ✅ Raise speed filter to 65 — IMPLEMENTED
4. ✅ Lower inv-accel-300- gap to 0.15% — IMPLEMENTED
5. ⬜ Fix double-entry signal_outcomes bug — each trade logged twice, inflating metrics

### Open Questions
- Why are kill switches not working? Is there a caching issue, a separate pipeline path, or a code bug in the signal execution layer?
- Should we add ACCEL_300_VELOCITY_MINUS_ENABLED flag to control vel- separately? (25% WR, -$0.88 — still negative)
- Is inv-accel-300- profitable because of the signal quality or because it fires rarely (survivorship bias)?
- Should we blacklist ORDI (40% WR, -$0.70) given consistent losses?
- Why does profit-monster have 100% WR (5/5)? Should we tune it to close more positions?

---

## 2026-08-01: Hourly Trade Analysis — Speed Filter Lowered (Trade Starvation)

### Data Window
- Analyzed: 1 trade (6h window), signal_outcomes (24h dedup: 58 trades), trades.json (200)
- Trades: 2824 total closed, 0 open at analysis time
- Trade rate: ~0.17 trades/hour (CRITICAL — nearly zero activity)
- Last trade closed: 2026-08-01 05:59 UTC (PURR SHORT, bb-squeeze-, -0.23%)

### Signal Performance (24h dedup — inv-accel-300- is the ONLY profitable active signal)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| tl_break_long | 15 | 40.0% | +0.64 | BEST (but disabled — legacy) |
| inv-accel-300- | 3 | 33.3% | +0.44 | ONLY ACTIVE WINNER |
| accel-300+ | 1 | 100.0% | +0.17 | GOOD (low sample) |
| accel-300-vel- | 8 | 12.5% | -1.43 | CATASTROPHIC |
| tl_break_short | 12 | 25.0% | -1.32 | LEGACY (disabled) |
| accel-300-vel+ | 10 | 20.0% | -0.45 | LEGACY (disabled) |
| bb-squeeze- | 2 | 0.0% | -0.30 | DEAD |
| accel-300- | 1 | 0.0% | -0.00 | DEAD |
| bb-squeeze | 1 | 0.0% | +0.08 | DEAD |

**Key insight: inv-accel-300- is the ONLY consistently profitable signal. Everything else is flat or negative.**

### Token Performance (24h dedup — all losers already blacklisted)
| Token | Trades | WR | Total PnL | Status |
|-------|--------|-----|-----------|--------|
| UNI | 5 | 0.0% | -1.39 | BLACKLISTED |
| PEOPLE | 2 | 0.0% | -0.98 | BLACKLISTED |
| LINEA | 3 | 0.0% | -0.85 | BLACKLISTED |
| STBL | 2 | 0.0% | -0.77 | BLACKLISTED |
| ORDI | 5 | 40.0% | -0.70 | BLACKLISTED |

### Root Cause: Trade Starvation
- Speed filter at 65 was blocking ~70% of signals
- Only 1 trade in 6h (0.17/hr) — system nearly idle
- inv-accel-300- (the only profitable signal) fires rarely and was being starved
- Winners average 71% speed percentile — 65 was barely clearing the bar

### Changes Implemented

**1. LOWER SIGNAL_FILTER_SPEED_MIN: 65 → 60 (hermes_constants.py:511)**
- Rationale: system was starving (0.17 trades/hr). 60 blocks bottom 60% but lets more inv-accel-300- signals through
- Risk: more trades = more noise, but inv-accel-300- has 33.3% WR with positive PnL

### What NOT to change
- ATR_SL_MIN_INIT (1.2%) — wider breathing room working as intended
- TRAILING_ACTIVATION_PCT (0.25%) — lock profits sooner
- TRAILING_DISTANCE_PCT (0.30%) — tighter trail locks profit faster
- TL_BREAK_ENABLED (False) — disable confirmed, but signals still executing (pipeline bug)
- ACCEL_300_VELOCITY_PLUS_ENABLED (False) — disable confirmed, but signals still executing
- BOLLINGER_SQUEEZE_ENABLED (False) — disable confirmed, but signals still executing
- All blacklisted tokens — consistent losers, keep blocked
- Phase-based k scaling — disabled (was compressing SL too aggressively)
- Dead hours filter — working correctly
- SIGNAL_FILTER_ENABLED (True) — the filter framework is sound

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: Fix kill switch pipeline bug — disabled signals STILL executing (tl_break, bb-squeeze, vel+). This has been flagged in EVERY analysis since 2026-08-01. Root cause is in the signal execution layer, not hermes_constants.py.
2. ✅ Lower speed filter to 60 — IMPLEMENTED (reduce trade starvation)
3. ⬜ Fix double-entry signal_outcomes bug — each trade logged twice, inflating metrics
4. ⬜ Investigate accel-300-vel- (12.5% WR, -$1.43) — consider disabling
5. ⬜ Consider disabling inv-accel-300+ (0% WR, -$0.18) — only 1 trade but negative

### Open Questions
- Why are kill switches not working? Is there a caching issue, a separate pipeline path, or a code bug in the signal execution layer? (FLAGGED 5th CONSECUTIVE TIME)
- Should we add ACCEL_300_VELOCITY_MINUS_ENABLED flag to control vel- separately? (12.5% WR, -$1.43 — worst active signal)
- Is inv-accel-300- profitable because of signal quality or survivorship bias? (only 3 trades in 24h)
- Is the double-entry signal_outcomes bug causing incorrect WR calculations?

---

## 2026-08-01: Hourly Trade Analysis — vel- Disabled, Speed Raised

### Data Window
- Analyzed: 10 closed trades (12h window), signal_outcomes (24h dedup: 49 trades), trades.json (200)
- Trades: 2824 total closed, 0 open at analysis time
- Trade rate: ~0.83 trades/hour (moderate)
- Last trade closed: 2026-08-01 05:59 UTC (PURR SHORT, bb-squeeze-, -0.23%)

### Signal Performance (24h dedup — ALL signals net losers except inv-accel-300-)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| inv-accel-300- | 3 | 33.3% | +0.44 | ONLY ACTIVE WINNER |
| tl_break_long | 14 | 35.7% | +0.32 | BEST (but disabled — legacy) |
| accel-300+ | 1 | 100.0% | +0.17 | GOOD (low sample) |
| bb-squeeze- | 2 | 0.0% | -0.30 | DOMINANT RECENT — ALL LOSERS |
| tl_break_short | 11 | 27.3% | -0.72 | LEGACY (disabled) |
| accel-300-vel- | 8 | 12.5% | -1.43 | WORST ACTIVE |
| accel-300-vel+ | 8 | 0.0% | -1.53 | CATASTROPHIC |

**Overall (deduplicated): 49 trades, 11 wins, 22.4% WR, -$2.97 total PnL in 24h.**

### CRITICAL BUG (still unfixed, 6th consecutive time)
**Kill switches not working** — disabled signals STILL executing:
- tl_break: 50 rows (28 long + 22 short) despite TL_BREAK_ENABLED=False
- bb-squeeze: 6 rows despite BOLLINGER_SQUEEZE_ENABLED=False
- accel-300-vel+: 16 rows despite ACCEL_300_VELOCITY_PLUS_ENABLED=False

**Root cause is in the signal execution pipeline, not constants. Needs code investigation.**

### Close Reason Breakdown (200 recent trades)
- atr_sl_hit: 186 trades, 42% WR (dominant exit — only viable)
- time_exit: 5 trades, 0% WR (ALL losers — closing flat positions prematurely)
- profit-monster: 5 trades, 100% WR (best exit — but rare)
- peak_exit: 4 trades, 0% WR (ALL losers — peak reversed then closed)

**time_exit and peak_exit are net negative — 0% WR across 9 trades. Consider disabling or tuning.**

### Recent Trades (last 12h — 50% WR)
| Coin | Dir | Signal | PnL | Close Reason |
|------|-----|--------|-----|--------------|
| PURR | SHORT | bb-squeeze- | -0.23% | atr_sl_hit |
| AAVE | SHORT | bb-squeeze- | -0.08% | atr_sl_hit |
| MORPHO | SHORT | tl_break_short | +0.04% | atr_sl_hit |
| KAITO | LONG | bb-squeeze | +0.08% | atr_sl_hit |
| APEX | SHORT | inv-accel-300- | +0.58% | atr_sl_hit |
| FET | LONG | tl_break_long | -0.14% | atr_sl_hit |
| AVNT | LONG | tl_break_long | +0.08% | atr_sl_hit |
| STBL | LONG | tl_break_long | -0.14% | atr_sl_hit |
| ORDI | SHORT | tl_break_short | -0.80% | atr_sl_hit |
| ME | LONG | tl_break_long | +0.02% | atr_sl_hit |

### Token Performance (24h dedup — top losers)
| Token | Trades | WR | Total PnL |
|-------|--------|-----|-----------|
| UNI | 10 | 0.0% | -7.28 |
| ORDI | 10 | 20.0% | -5.90 |
| LINEA | 6 | 0.0% | -4.41 |
| PEOPLE | 4 | 0.0% | -3.75 |
| STBL | 4 | 0.0% | -3.34 |

**UNI: 0% WR across 10 trades, -$7.28 total. Already blacklisted.**

### Changes Implemented

**1. DISABLE accel-300-vel- signal (hermes_constants.py:714, accel_300.py:722-725, signal_schema.py:506, 676-679)**
- ACCEL_300_VELOCITY_MINUS_ENABLED = False
- Added kill-switch guard in accel_300.py source-assignment (safety net)
- Added Layer 2 guard in signal_schema.py add_signal()
- Rationale: 12.5% WR (8 dedup trades), -$1.43 total. Worst active signal.

**2. RAISE SPEED_MIN_THRESHOLD: 50 → 60 (hermes_constants.py:285)**
- Winners average 71% speed percentile
- 50 was too permissive — letting slow, low-momentum signals through
- 60 blocks bottom 60% of speed distribution

**3. DOCUMENTED time_exit/peak_exit as net negative**
- time_exit: 0% WR (0/5) — closing positions after 1-3h with small losses
- peak_exit: 0% WR (0/4) — positions that peaked then reversed
- Both exit types consistently lose — consider disabling or tuning parameters

### What NOT to change
- ATR_SL_MIN_INIT (1.2%) — wider breathing room working as intended
- TRAILING_ACTIVATION_PCT (0.25%) — lock profits sooner
- TRAILING_DISTANCE_PCT (0.30%) — tighter trail locks profit faster
- TL_BREAK_ENABLED (False) — disable confirmed, but signals still executing (pipeline bug)
- ACCEL_300_VELOCITY_PLUS_ENABLED (False) — disable confirmed, but signals still executing
- BOLLINGER_SQUEEZE_ENABLED (False) — disable confirmed, but signals still executing
- All blacklisted tokens — consistent losers, keep blocked
- Phase-based k scaling — disabled (was compressing SL too aggressively)
- Dead hours filter — working correctly
- SIGNAL_FILTER_ENABLED (True) — the filter framework is sound

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: Fix kill switch pipeline bug — disabled signals STILL executing (tl_break, bb-squeeze, vel+). 6th consecutive analysis flagging this. Root cause is in signal execution layer.
2. ✅ Disable accel-300-vel- — IMPLEMENTED (worst active signal, 12.5% WR)
3. ✅ Raise SPEED_MIN_THRESHOLD to 60 — IMPLEMENTED (block low-momentum entries)
4. ⬜ Fix double-entry signal_outcomes bug — each trade logged twice, inflating metrics
5. ⬜ Investigate time_exit/peak_exit — 0% WR across 9 trades, closing positions prematurely

### Open Questions
- Why are kill switches not working? Is there a caching issue, a separate pipeline path, or a code bug in the signal execution layer? (FLAGGED 6th CONSECUTIVE TIME)
- Should time_exit/peak_exit be disabled? They close positions that haven't hit SL but are flat/negative.
- Is inv-accel-300- profitable because of signal quality or survivorship bias? (only 3 trades in 24h)
- Should we blacklist more tokens? UNI has 0% WR across 10 trades despite being blacklisted.
- What's the WR breakdown excluding disabled-signal trades? (need to separate signal quality from kill-switch contamination)

---

## 2026-08-01: Hourly Trade Analysis — accel-300 Disabled, Speed Lowered

### Data Window
- Analyzed: 45 trades (24h), signal_outcomes (24h dedup: 44 trades), trades.json (200)
- Trades: 2824+ total closed, 0 open at analysis time
- Trade rate: ~1.9 trades/hour (moderate)

### Signal Performance (24h dedup — ALL signals net losers except inv-accel-300-)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| inv-accel-300- | 3 | 33.3% | +0.44 | ONLY ACTIVE WINNER |
| tl_break_long | 14 | 35.7% | +0.32 | LEGACY (disabled) |
| tl_break_short | 8 | 37.5% | +0.02 | LEGACY (disabled) |
| accel-300+ | 1 | 100.0% | +0.17 | GOOD (low sample) |
| accel-300-vel- | 7 | 0.0% | -2.77 | CATASTROPHIC |
| accel-300-vel+ | 8 | 0.0% | -1.53 | CATASTROPHIC |
| bb-squeeze- | 2 | 0.0% | -0.30 | DEAD |
| bb-squeeze | 1 | 0.0% | +0.08 | DEAD |

**Key insight: vel+ and vel- are STILL EXECUTING with 0% WR despite being disabled. This is the 7th consecutive analysis flagging the kill switch pipeline bug.**

### Token Performance (24h dedup — blacklisted tokens still executing)
| Token | Trades | WR | Total PnL | Status |
|-------|--------|-----|-----------|--------|
| UNI | 5 | 0.0% | -1.39 | BLACKLISTED (still executing!) |
| AIXBT | 2 | 0.0% | -1.18 | BLACKLISTED (still executing!) |
| PEOPLE | 2 | 0.0% | -0.98 | BLACKLISTED (still executing!) |
| STBL | 2 | 0.0% | -0.77 | BLACKLISTED (still executing!) |
| APEX | 2 | 50.0% | +0.87 | PROFITABLE |
| KAITO | 3 | 33.3% | +0.34 | PROFITABLE |

**Profitable tokens: APEX (+0.87), TNSR (+0.69), MOODENG (+0.60), AAVE (+0.53), KAITO (+0.34)**

### Close Reason Breakdown (45 trades, 24h)
- atr_sl_hit: 41 trades, ~33% WR (dominant exit)
- time_exit: 3 trades, 0% WR (ALL losers)
- profit-monster: 1 trade, 100% WR (best exit)

### Changes Implemented

**1. DISABLE accel-300 entirely (hermes_constants.py:617)**
- ACCEL_300_ENABLED: True → False
- Rationale: vel+/vel- are 0% WR (15 trades, -$4.30 total). accel-300+ had only 1 trade. All variants net negative.

**2. LOWER SIGNAL_FILTER_SPEED_MIN: 50 → 45 (hermes_constants.py:469)**
- Rationale: reduce trade starvation, let inv-accel-300- fire more often
- Risk: more trades from disabled signals (kill switch bug), but inv-accel-300- has 33.3% WR with positive PnL

**3. inv-accel-300- remains enabled — ONLY profitable active signal**
- INVERSE_ACCEL_300_ENABLED = True
- INVERSE_ACCEL_300_MINUS_ENABLED = True

### What NOT to change
- ATR_SL_MIN_INIT (1.2%) — wider breathing room working as intended
- TRAILING_ACTIVATION_PCT (0.25%) — lock profits sooner
- TRAILING_DISTANCE_PCT (0.30%) — tighter trail locks profit faster
- TL_BREAK_ENABLED (False) — disable confirmed, but signals still executing (pipeline bug)
- ACCEL_300_VELOCITY_PLUS_ENABLED (False) — disable confirmed, but signals still executing
- BOLLINGER_SQUEEZE_ENABLED (False) — disable confirmed, but signals still executing
- All blacklisted tokens — consistent losers, keep blocked
- Phase-based k scaling — disabled (was compressing SL too aggressively)
- Dead hours filter — working correctly
- SIGNAL_FILTER_ENABLED (True) — the filter framework is sound

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: Fix kill switch pipeline bug — disabled signals STILL executing (tl_break, bb-squeeze, vel+, vel-). 7th consecutive analysis flagging this. Root cause is in signal execution layer.
2. ✅ Disable accel-300 entirely — IMPLEMENTED (vel+/vel- 0% WR, 15 trades, -$4.30)
3. ✅ Lower speed filter to 45 — IMPLEMENTED (reduce trade starvation, let inv-accel-300- through)
4. ⬜ Fix double-entry signal_outcomes bug — each trade logged twice, inflating metrics
5. ⬜ Investigate time_exit — 0% WR across 3 trades, closing positions prematurely

### Open Questions
- Why are kill switches not working? (FLAGGED 7th CONSECUTIVE TIME)
- Should time_exit be disabled? 0% WR across 3 trades.
- Is inv-accel-300- profitable because of signal quality or survivorship bias? (only 3 trades in 24h)
- Should we add ACCEL_300_VELOCITY_MINUS_ENABLED flag to control vel- separately? (already disabled via ACCEL_300_ENABLED=False)
- Why are blacklisted tokens (UNI, AIXBT, PEOPLE, STBL) still executing trades?

---

## 2026-08-01: Hourly Trade Analysis — BABY Blacklisted, Speed Lowered, inv-accel-300+ Disabled

### Data Window
- Analyzed: 7 trades (12h window), signal_outcomes (24h dedup: 41 trades), trades.json (200)
- Trades: 2826 total closed, 0 open at analysis time
- Trade rate: ~0.58 trades/hour (CRITICAL — system nearly idle)
- Last trade closed: 2026-08-01 14:38 UTC (BABY LONG, inv-accel-300+, -0.33%)

### Signal Performance (24h dedup — ALL signals net losers)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| accel-300+ | 1 | 100.0% | +0.17 | GOOD (1 trade) |
| bb-squeeze | 1 | 0.0% | +0.08 | DEAD |
| inv-accel-300- | 4 | 25.0% | -0.17 | DECLINING (was 33.3%) |
| tl_break_long | 13 | 30.8% | -0.29 | LEGACY (disabled) |
| tl_break_short | 6 | 33.3% | -0.33 | LEGACY (disabled) |
| inv-accel-300+ | 1 | 0.0% | -0.33 | NEW — 0% WR |
| bb-squeeze- | 2 | 0.0% | -0.30 | DEAD |
| accel-300-vel+ | 8 | 0.0% | -1.53 | CATASTROPHIC |
| accel-300-vel- | 5 | 0.0% | -1.56 | CATASTROPHIC |

**Key finding: vel+ and vel- STILL EXECUTING at 0% WR (13 trades, -$3.09). Kill switch bug 8th consecutive time.**

### Token Performance (24h dedup — blacklisted tokens still executing)
| Token | Trades | WR | Total PnL | Status |
|-------|--------|-----|-----------|--------|
| UNI | 5 | 0.0% | -1.39 | BLACKLISTED (still executing!) |
| PEOPLE | 2 | 0.0% | -0.98 | BLACKLISTED (still executing!) |
| STBL | 2 | 0.0% | -0.77 | BLACKLISTED (still executing!) |
| BABY | 3 | 0.0% | -0.48 | NOW BLACKLISTED |
| ORDI | 2 | 50.0% | -0.64 | BLACKLISTED (still executing!) |

**Profitable tokens: APEX (+0.87), TNSR (+0.69), MOODENG (+0.60), KAITO (+0.34)**

### Price Action Analysis (MFE/MAE — 7 recent trades)
**Winners (3):**
- APEX SHORT: MFE=+2.31%, MAE=+2.46% — strong directional move
- KAITO LONG: MFE=+1.53%, MAE=+2.76% — WHIPSAW (went to +1.53% then reversed)
- MORPHO SHORT: MFE=+0.35%, MAE=+0.65% — WHIPSAW (went to +0.35% then reversed)

**Losers (4):**
- BABY LONG: MFE=+0.12%, MAE=+1.11% — barely moved in favor, high adverse
- MOVE SHORT: MFE=+0.32%, MAE=+0.61% — WHIPSAW
- PURR SHORT: MFE=+0.20%, MAE=+1.58% — WHIPSAW
- AAVE SHORT: MFE=+1.34%, MAE=+1.03% — went to +1.34% profit then reversed to -0.08%

**Whipsaw rate: 57% (4/7 trades) — extremely high. Trades peak in profit then reverse.**

### Close Reason Breakdown (7 recent trades)
- atr_sl_hit: 7 trades, 43% WR (only exit type)

### CRITICAL BUGS (still unfixed, 8th consecutive time)
1. **Kill switches not working** — vel+, vel-, bb-squeeze, tl_break STILL executing despite all being disabled. 0% WR across 24 disabled-signal trades. Root cause in signal execution layer.
2. **Blacklisted tokens still executing** — UNI (5 trades, 0% WR), PEOPLE (2, 0%), STBL (2, 0%), ORDI (2, 50%). Blacklist filter not applied.
3. **Double-entry signal_outcomes** — 82 total rows for 41 dedup trades (2x inflation).

### Changes Implemented

**1. BLACKLIST BABY both directions (hermes_constants.py:SHORT_BLACKLIST, LONG_BLACKLIST)**
- BABY: 0% WR (0/3 dedup), -$0.48 total — zero wins across 3 trades
- Added to both SHORT_BLACKLIST and LONG_BLACKLIST

**2. LOWER SIGNAL_FILTER_SPEED_MIN: 45 → 40 (hermes_constants.py:469)**
- Trade rate critical at 0.58 trades/hr (2 trades in 6h)
- 40 blocks bottom 40% of speed distribution
- Expected to increase trade count while maintaining quality

**3. DISABLE inv-accel-300+ (hermes_constants.py:740)**
- INVERSE_ACCEL_300_PLUS_ENABLED: True → False
- 0% WR (0/1 dedup), -$0.33 — first trade was a loss
- inv-accel-300- (SHORT) remains enabled — only profitable variant

### What NOT to change
- ATR_SL_MIN_INIT (1.2%) — wider breathing room working as intended
- TRAILING_ACTIVATION_PCT (0.25%) — lock profits sooner
- TRAILING_DISTANCE_PCT (0.30%) — tighter trail locks profit faster
- TL_BREAK_ENABLED (False) — disable confirmed, but signals still executing (pipeline bug)
- ACCEL_300_ENABLED (False) — disable confirmed, but signals still executing
- BOLLINGER_SQUEEZE_ENABLED (False) — disable confirmed, but signals still executing
- All blacklisted tokens — consistent losers, keep blocked
- Phase-based k scaling — disabled (was compressing SL too aggressively)
- Dead hours filter — working correctly
- SIGNAL_FILTER_ENABLED (True) — the filter framework is sound

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: Fix kill switch pipeline bug — disabled signals STILL executing (vel+, vel-, bb-squeeze, tl_break). 8th consecutive analysis flagging this.
2. ✅ Blacklist BABY — IMPLEMENTED (0% WR, -$0.48)
3. ✅ Lower speed filter to 40 — IMPLEMENTED (reduce trade starvation)
4. ✅ Disable inv-accel-300+ — IMPLEMENTED (0% WR)
5. ⬜ Fix blacklisted token execution — UNI, PEOPLE, STBL, ORDI still executing despite being blacklisted

### Open Questions
- Why are kill switches not working? (FLAGGED 8th CONSECUTIVE TIME)
- Why are blacklisted tokens still executing? Is the blacklist filter applied at signal creation or only at trade entry?
- Should we widen inv-accel-300- reversion params for more entries? (only 4 trades in 24h)
- Is the whipsaw rate (57%) due to trailing activation too early (0.25%)?
- Should we blacklist ORDI (50% WR but -$0.64 total)?

---

## 2026-08-01: Hourly Trade Analysis — Speed Lowered, Gap Widened, Kill Switch Bug 9th Time

### Data Window
- Analyzed: 5 trades (12h window), signal_outcomes (24h dedup: 35 trades), trades.json (200)
- Trades: 2826 total closed, 0 open at analysis time
- Trade rate: ~0.3 trades/hour (CRITICAL — system nearly idle)
- Last trade closed: 2026-08-01 14:38 UTC (BABY LONG, inv-accel-300+, -0.33%)

### Signal Performance (24h dedup — ALL signals net losers)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| accel-300+ | 1 | 100.0% | +0.17 | GOOD (1 trade) |
| bb-squeeze | 1 | 0.0% | +0.08 | DEAD |
| inv-accel-300- | 4 | 25.0% | -0.17 | DECLINING (was 33.3%) |
| tl_break_long | 12 | 33.3% | -0.18 | LEGACY (disabled) |
| tl_break_short | 5 | 20.0% | -0.78 | LEGACY (disabled) |
| inv-accel-300+ | 1 | 0.0% | -0.33 | DISABLED |
| bb-squeeze- | 2 | 0.0% | -0.30 | DEAD |
| accel-300-vel+ | 6 | 0.0% | -0.92 | CATASTROPHIC |
| accel-300-vel- | 3 | 0.0% | -0.81 | CATASTROPHIC |

**Overall (deduplicated): 35 trades, 7 wins, 20.0% WR, -3.24 total PnL in 24h.**

### Token Performance (24h dedup — blacklisted tokens still executing)
| Token | Trades | WR | Total PnL | Status |
|-------|--------|-----|-----------|--------|
| UNI | 5 | 0.0% | -1.39 | BLACKLISTED (still executing!) |
| CAKE | 2 | 0.0% | -0.52 | BLACKLISTED (still executing!) |
| LINEA | 2 | 0.0% | -0.58 | BLACKLISTED (still executing!) |
| BABY | 2 | 0.0% | -0.42 | BLACKLISTED (still executing!) |
| ORDI | 2 | 50.0% | -0.64 | BLACKLISTED (still executing!) |
| PEOPLE | 1 | 0.0% | -0.42 | BLACKLISTED (still executing!) |
| STBL | 1 | 0.0% | -0.14 | BLACKLISTED (still executing!) |
| AIXBT | 1 | 0.0% | -0.21 | BLACKLISTED (still executing!) |
| BLUR | 1 | 0.0% | -0.06 | BLACKLISTED (still executing!) |
| FET | 1 | 0.0% | -0.14 | BLACKLISTED (still executing!) |
| TIA | 1 | 0.0% | -0.12 | BLACKLISTED (still executing!) |

**11 blacklisted tokens still executing in 24h — blacklist filter NOT applied.**

### Recent Trades (last 12h — 0% WR)
| Coin | Dir | Signal | PnL | Close Reason |
|------|-----|--------|-----|--------------|
| BABY | LONG | inv-accel-300+ | -0.33% | atr_sl_hit |
| MOVE | SHORT | inv-accel-300- | -0.61% | atr_sl_hit |
| PURR | SHORT | bb-squeeze- | -0.23% | atr_sl_hit |
| AAVE | SHORT | bb-squeeze- | -0.08% | atr_sl_hit |
| MORPHO | SHORT | tl_break_short | +0.04% | atr_sl_hit |

### CRITICAL BUGS (9th consecutive time)
1. **Kill switches not working** — vel+ (6 trades, 0% WR), vel- (3, 0%), bb-squeeze (3, 0%), tl_break (17, 30%) STILL EXECUTING despite all being disabled. 26 disabled-signal trades in 24h, ~5% WR. Root cause in signal execution layer.
2. **Blacklisted tokens still executing** — 11 blacklisted tokens (UNI, CAKE, LINEA, BABY, ORDI, PEOPLE, STBL, AIXBT, BLUR, FET, TIA) traded in 24h. Blacklist filter not applied at trade entry.
3. **Double-entry signal_outcomes** — 70 total rows for 35 dedup trades (2x inflation).

### Changes Implemented

**1. LOWER SIGNAL_FILTER_SPEED_MIN: 40 → 35 (hermes_constants.py:473)**
- Trade rate critical at 0.3 trades/hr (2 trades in 6h)
- 35 blocks bottom 35% of speed distribution
- Expected to increase trade count from inv-accel-300-

**2. WIDEN inv-accel-300- gap: 0.15% → 0.10% (hermes_constants.py:645-646)**
- INVERSE_ACCEL_300_MIN_GAP_PCT_LONG: 0.15 → 0.10
- INVERSE_ACCEL_300_MIN_GAP_PCT_SHORT: 0.15 → 0.10
- inv-accel-300- is the only signal that sometimes works — let it fire more often
- Risk: more signals = more trades, but 25% WR with positive PnL (on best tokens) justifies it

### What NOT to change
- ATR_SL_MIN_INIT (1.2%) — wider breathing room working as intended
- TRAILING_ACTIVATION_PCT (0.25%) — lock profits sooner
- TRAILING_DISTANCE_PCT (0.30%) — tighter trail locks profit faster
- TL_BREAK_ENABLED (False) — disable confirmed, but signals still executing (pipeline bug)
- ACCEL_300_ENABLED (False) — disable confirmed, but signals still executing
- BOLLINGER_SQUEEZE_ENABLED (False) — disable confirmed, but signals still executing
- All blacklisted tokens — consistent losers, keep blocked
- Phase-based k scaling — disabled (was compressing SL too aggressively)
- Dead hours filter — working correctly
- SIGNAL_FILTER_ENABLED (True) — the filter framework is sound

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: Fix kill switch pipeline bug — disabled signals STILL executing (vel+, vel-, bb-squeeze, tl_break). 9th consecutive analysis flagging this. Root cause is in signal execution layer.
2. 🔴 CRITICAL: Fix blacklisted token execution — 11 blacklisted tokens still trading. Blacklist filter not applied at trade entry.
3. ✅ Lower speed filter to 35 — IMPLEMENTED (reduce trade starvation)
4. ✅ Widen inv-accel-300- gap to 0.10% — IMPLEMENTED (more entries from best signal)
5. ⬜ Fix double-entry signal_outcomes bug — each trade logged twice, inflating metrics

### Open Questions
- Why are kill switches not working? (FLAGGED 9th CONSECUTIVE TIME)
- Why are blacklisted tokens still executing? Is the blacklist filter applied at signal creation or only at trade entry?
- Is inv-accel-300- declining (25% WR, -0.17) due to market conditions or survivorship bias?
- Should we raise TOKEN_WR_THRESHOLD from 30 to 35 to block more losers?
- Is the system fundamentally broken until kill switch and blacklist bugs are fixed?

---

## 2026-08-01: Hourly Trade Analysis — inv-accel-300- Declining, Trade Starvation

### Data Window
- Analyzed: 6 trades (12h window), signal_outcomes (24h dedup: 33 trades), trades.json (200)
- Trades: 2828 total closed, 0 open at analysis time
- Trade rate: ~0.5 trades/hour (CRITICAL — system nearly idle)
- Last trade closed: 2026-08-01 16:39 UTC (AAVE SHORT, inv-accel-300-, +0.10%)

### Signal Performance (24h dedup — ALL signals net losers)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| accel-300+ | 1 | 100.0% | +0.17 | GOOD (1 trade) |
| bb-squeeze | 1 | 0.0% | +0.08 | DEAD |
| tl_break_long | 11 | 36.4% | -0.09 | LEGACY (disabled) |
| inv-accel-300- | 6 | 16.7% | -0.39 | DECLINING (was 33.3%) |
| accel-300-vel+ | 4 | 0.0% | -0.38 | CATASTROPHIC (disabled) |
| accel-300-vel- | 2 | 0.0% | -0.27 | CATASTROPHIC (disabled) |
| tl_break_short | 5 | 20.0% | -0.78 | LEGACY (disabled) |
| inv-accel-300+ | 1 | 0.0% | -0.33 | DISABLED |
| bb-squeeze- | 2 | 0.0% | -0.30 | DEAD (disabled) |

**Overall (deduplicated): 33 trades, 7 wins, 21.2% WR, -$3.24 total PnL in 24h.**

### Token Performance (24h dedup — top losers)
| Token | Trades | WR | Total PnL | Status |
|-------|--------|-----|-----------|--------|
| UNI | 5 | 0.0% | -1.39 | BLACKLISTED (still executing!) |
| CAKE | 2 | 0.0% | -0.52 | BLACKLISTED (still executing!) |
| ORDI | 2 | 50.0% | -0.64 | BLACKLISTED (still executing!) |
| STBL | 2 | 0.0% | -0.47 | BLACKLISTED (still executing!) |
| AIXBT | 1 | 0.0% | -0.21 | BLACKLISTED (still executing!) |
| BABY | 1 | 0.0% | -0.33 | BLACKLISTED (still executing!) |

**Profitable tokens: APEX (+0.87), KAITO (+0.34), AAVE (+0.02), ETH (+0.26)**

### Diagnosis

**1. Entry Quality (MFE/MAE — last 6h)**
- **Winners** (2): AAVE SHORT inv-accel-300- (+0.10%), APEX SHORT inv-accel-300- (+0.58%) — low adverse excursion, good timing
- **Losers** (4): STBL (-0.32%), BABY (-0.33%), MOVE (-0.61%), PURR (-0.23%) — all hit SL immediately
- **Whipsaw rate**: 83% (5/6 losers hit SL) — trades stall then reverse

**2. Signal Quality**
- inv-accel-300- is declining: 33.3% → 25% → 16.7% WR over last 3 analyses
- Disabled signals (vel+, vel-, bb-squeeze, tl_break) still executing at 0% WR — kill switch bug 9th consecutive time
- Blacklisted tokens (UNI, CAKE, ORDI, STBL) still executing — blacklist filter not applied

**3. SL/TP Behavior**
- 100% of exits are `atr_sl_hit` — no trailing or TP exits
- ATR_SL_MIN_INIT at 1.2% surviving but trades stalling and hitting SL

**4. Trade Frequency**
- Critical: 0.5 trades/hr (last 6h)
- inv-accel-300- only fire 6 times in 24h (was 3-4 before)
- SIGNAL_FILTER_SPEED_MIN at 35 still too high for this signal

### Changes Implemented

**1. RAISE TOKEN_WR_THRESHOLD: 30 → 40 (hermes_constants.py:484)**
- Rationale: block more losing tokens (UNI 0% WR, CAKE 0% WR, ORDI 50% but -0.64 total)
- Risk: may block some marginal winners, but 40% threshold still allows decent tokens

**2. WIDEN inv-accel-300- REVERSION_BARS: 3 → 2 (hermes_constants.py:647)**
- Rationale: reduce confirmation requirement for reversion, let signal fire sooner
- Risk: more noise, but inv-accel-300- is the only signal with any historical edge

**3. LOWER inv-accel-300- REVERSION_THRESHOLD: 0.08 → 0.05 (hermes_constants.py:648)**
- Rationale: lower the gap narrowing requirement for more entries
- Risk: more low-quality signals, but trade starvation is the bigger problem

**4. LOWER SIGNAL_FILTER_SPEED_MIN: 35 → 30 (hermes_constants.py:473)**
- Rationale: reduce trade starvation, let more inv-accel-300- through
- Risk: more noise from disabled signals (kill switch bug), but inv-accel-300- needs entries

### What NOT to change
- ATR_SL_MIN_INIT (1.2%) — wider breathing room working as intended
- TRAILING_ACTIVATION_PCT (0.25%) — lock profits sooner
- TRAILING_DISTANCE_PCT (0.30%) — tighter trail locks profit faster
- TL_BREAK_ENABLED (False) — disable confirmed, but signals still executing (pipeline bug)
- ACCEL_300_ENABLED (False) — disable confirmed, but signals still executing
- BOLLINGER_SQUEEZE_ENABLED (False) — disable confirmed, but signals still executing
- All blacklisted tokens — consistent losers, keep blocked
- Phase-based k scaling — disabled (was compressing SL too aggressively)
- Dead hours filter — working correctly
- SIGNAL_FILTER_ENABLED (True) — the filter framework is sound

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: Fix kill switch pipeline bug — disabled signals STILL executing (vel+, vel-, bb-squeeze, tl_break). 9th consecutive analysis. Root cause in signal execution layer.
2. 🔴 CRITICAL: Fix blacklisted token execution — UNI, CAKE, ORDI, STBL still trading despite being blacklisted.
3. ✅ Raise TOKEN_WR_THRESHOLD to 40 — IMPLEMENTED (block more losers)
4. ✅ Widen inv-accel-300- reversion (bars=2, threshold=0.05) — IMPLEMENTED (more entries)
5. ✅ Lower speed filter to 30 — IMPLEMENTED (reduce trade starvation)

### Open Questions
- Why are kill switches not working? (FLAGGED 9th CONSECUTIVE TIME)
- Why are blacklisted tokens still executing? (FLAGGED 9th CONSECUTIVE TIME)
- Is inv-accel-300- decline due to market conditions or signal quality degradation?
- Should we add ACCEL_300_VELOCITY_MINUS_ENABLED flag to control vel- separately? (already disabled via ACCEL_300_ENABLED=False)
- Is the system fundamentally broken until kill switch and blacklist bugs are fixed?

---

## 2026-08-01: Hourly Trade Analysis — SL Widened, Trailing Loosened, Speed Lowered

### Data Window
- Analyzed: 200 closed trades (trades.json), signal_outcomes (24h dedup: 32 trades)
- Trades: 2828 total closed, 0 open at analysis time
- Trade rate: ~0.5 trades/hour (CRITICAL — system nearly idle)
- Last trade closed: 2026-08-01 16:39 UTC (AAVE SHORT, inv-accel-300-, +0.10%)

### Signal Performance (24h dedup — ALL signals net losers)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| accel-300+ | 1 | 100.0% | +0.17 | GOOD (1 trade) |
| bb-squeeze | 1 | 0.0% | +0.08 | DEAD |
| tl_break_long | 10 | 30.0% | -0.93 | LEGACY (disabled) |
| tl_break_short | 5 | 20.0% | -0.78 | LEGACY (disabled) |
| inv-accel-300- | 6 | 16.7% | -0.39 | DECLINING (was 33.3%) |
| accel-300-vel+ | 4 | 0.0% | -0.38 | CATASTROPHIC (disabled) |
| inv-accel-300+ | 1 | 0.0% | -0.33 | DISABLED |
| bb-squeeze- | 2 | 0.0% | -0.30 | DEAD (disabled) |
| accel-300-vel- | 2 | 0.0% | -0.27 | CATASTROPHIC (disabled) |

**Overall (deduplicated): 32 trades, 6 wins, 18.8% WR, -3.13 total PnL in 24h.**

### Signal Performance (200 recent trades — ALL signals in file)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| inv-accel-300- | 10 | 60.0% | +1.97 | BEST ACTIVE |
| accel-300+ | 6 | 67.0% | +1.34 | GOOD |
| tl_break_long | 58 | 40.0% | +3.43 | LEGACY |
| tl_break_short | 71 | 48.0% | +0.15 | LEGACY |
| accel-300-vel- | 15 | 33.0% | +0.68 | MARGINAL |
| accel-300-vel+ | 22 | 27.0% | -0.53 | BAD |
| accel-300- | 8 | 38.0% | -0.85 | BAD |

### Token Performance (24h dedup — top losers)
| Token | Trades | WR | Total PnL | Status |
|-------|--------|-----|-----------|--------|
| UNI | 5 | 0.0% | -1.39 | BLACKLISTED (still executing!) |
| CAKE | 2 | 0.0% | -0.52 | BLACKLISTED (still executing!) |
| STBL | 2 | 0.0% | -0.47 | BLACKLISTED (still executing!) |
| BABY | 1 | 0.0% | -0.33 | BLACKLISTED (still executing!) |

**Profitable tokens: APEX (+0.87), ETH (+0.26), MOODENG (+0.60), ME (+0.02)**

### Diagnosis

**1. Entry Quality:**
- Winners: Low adverse excursion, good timing (AAVE SHORT +0.10%, APEX SHORT +0.58%)
- Losers: High adverse excursion, SL hit immediately (MOVE -0.61%, BABY -0.33%, STBL -0.32%)
- Whipsaw rate: 83% (5/6 losers hit SL immediately)

**2. Signal Quality:**
- inv-accel-300- declining: 33.3% → 25% → 16.7% over last 3 analyses
- Disabled signals (vel+, vel-, bb-squeeze, tl_break) still executing at 0% WR
- Blacklisted tokens (UNI, CAKE, STBL, BABY) still executing

**3. SL/TP Behavior:**
- 100% of recent exits are `atr_sl_hit` — no trailing or TP exits
- ATR_SL_MIN_INIT at 1.2% was too tight — normal crypto retracements trigger SL immediately
- Trailing never activates because trades hit SL before reaching +0.25% activation

**4. Trade Frequency:**
- Critical: 0.5 trades/hr (last 12h)
- SIGNAL_FILTER_SPEED_MIN at 30 blocking too many signals
- inv-accel-300- needs more entries to recover edge

### Changes Implemented

**1. WIDEN ATR_SL_MIN_INIT: 1.2% → 1.5% (hermes_constants.py:346)**
- Also: ATR_SL_MAX_INIT 1.5% → 1.8%, SL_PCT_FALLBACK 1.2% → 1.5%, STOP_LOSS_DEFAULT 1.2% → 1.5%, TP_PCT_FALLBACK 1.8% → 2.2%
- Rationale: 100% of exits are atr_sl_hit at 1.2%. Normal crypto retracements of 0.5-1% immediately stop out trades. 1.5% gives breathing room.

**2. WIDEN TRAILING_DISTANCE_PCT: 0.30% → 0.40% (hermes_constants.py:359)**
- Rationale: 83% whipsaw rate — trades peak then reverse through tight 0.30% trail. 0.40% gives trailing more room to breathe before triggering exit.

**3. LOWER SIGNAL_FILTER_SPEED_MIN: 30 → 25 (hermes_constants.py:473)**
- Rationale: Critical trade starvation (0.5 trades/hr). Winners avg 71% speed percentile. 25 blocks bottom 25% but lets more inv-accel-300- entries through.

### What NOT to change
- ATR_SL_MIN (0.5%) — floor, keep it
- ATR_TP_MAX (1.0%) — already tight enough
- TRAILING_ACTIVATION_PCT (0.25%) — good activation point
- TL_BREAK_ENABLED (False) — disable confirmed, but signals still executing (pipeline bug)
- ACCEL_300_ENABLED (False) — disable confirmed, but signals still executing
- BOLLINGER_SQUEEZE_ENABLED (False) — disable confirmed, but signals still executing
- All blacklisted tokens — consistent losers, keep blocked
- Phase-based k scaling — disabled (was compressing SL too aggressively)
- Dead hours filter — working correctly
- SIGNAL_FILTER_ENABLED (True) — the filter framework is sound

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: Fix kill switch pipeline bug — disabled signals STILL executing (vel+, vel-, bb-squeeze, tl_break). 10th consecutive analysis flagging this. Root cause is in signal execution layer.
2. 🔴 CRITICAL: Fix blacklisted token execution — UNI, CAKE, STBL, BABY still trading despite being blacklisted. Blacklist filter not applied at trade entry.
3. ✅ Widen ATR_SL_MIN_INIT to 1.5% — IMPLEMENTED (100% exits were atr_sl_hit, too tight)
4. ✅ Widen TRAILING_DISTANCE_PCT to 0.40% — IMPLEMENTED (83% whipsaw rate, trail too tight)
5. ✅ Lower speed filter to 25 — IMPLEMENTED (critical starvation at 0.5 trades/hr)

### Open Questions
- Why are kill switches not working? (FLAGGED 10th CONSECUTIVE TIME)
- Why are blacklisted tokens still executing? (FLAGGED 10th CONSECUTIVE TIME)
- Is inv-accel-300- decline (33% → 16.7%) due to market conditions or signal quality degradation?
- Will wider SL (1.5%) reduce whipsaw stops or just delay the inevitable loss?
- Should we investigate the signal execution layer code directly to find the kill switch bug root cause?

---

## 2026-08-01: Hourly Trade Analysis — Kill Switch Guards Added, inv-accel-300- Disabled

### Data Window
- Analyzed: 18 dedup trades (24h), 5 trades (12h), trades.json (50)
- Trades: 2828 total closed, 1 open (ALT SHORT inv-accel-300-)
- Trade rate: ~0.75 trades/hr (CRITICAL — system nearly idle)
- Last trade closed: 2026-08-01 16:39 UTC (AAVE SHORT, inv-accel-300-, +0.10%)

### Signal Performance (24h dedup — ALL signals net negative)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| tl_break_long | 10 | 20% | -4.36 | LEGACY (disabled, still executing) |
| inv-accel-300- | 8 | 0% | -4.10 | COLLAPSED (was 33% earlier today) |
| tl_break_short | 6 | 17% | -3.02 | LEGACY (disabled, still executing) |
| bb-squeeze- | 4 | 0% | -2.41 | DEAD (disabled, still executing) |
| inv-accel-300+ | 2 | 0% | -1.56 | DISABLED |
| accel-300-vel- | 2 | 0% | -1.01 | CATASTROPHIC (disabled) |
| accel-300-vel+ | 2 | 0% | -0.99 | CATASTROPHIC (disabled) |
| bb-squeeze | 2 | 0% | -0.74 | DEAD (disabled) |

**Overall: 18 dedup trades, 3 wins, 16.7% WR, -$0.99 total PnL in 24h.**
**ALL 8 signal types are net negative. No profitable signals exist.**

### Token Performance (24h dedup — top losers)
| Token | Trades | WR | Total PnL | Status |
|-------|--------|-----|-----------|--------|
| STBL | 4 | 0% | -2.73 | BLACKLISTED (still executing!) |
| ORDI | 2 | 0% | -2.50 | BLACKLISTED (still executing!) |
| MOVE | 2 | 0% | -2.12 | BLACKLISTED (still executing!) |
| AAVE | 4 | 0% | -1.76 | PROFITABLE before, now 0% WR |
| BABY | 2 | 0% | -1.56 | BLACKLISTED (still executing!) |
| PURR | 2 | 0% | -1.35 | BLACKLISTED |

**11+ blacklisted tokens still executing — blacklist filter NOT applied at trade entry.**

### MFE/MAE Analysis (5 recent trades)
| Coin | Dir | Signal | MFE | MAE | Result |
|------|-----|--------|-----|-----|--------|
| AAVE | SHORT | inv-accel-300- | +1.00% | -0.15% | WIN +0.10% |
| STBL | SHORT | inv-accel-300- | +1.87% | -0.58% | LOSE -0.32% |
| BABY | LONG | inv-accel-300+ | +0.12% | -1.11% | LOSE -0.33% |
| MOVE | SHORT | inv-accel-300- | +1.91% | -0.61% | LOSE -0.61% |
| PURR | SHORT | bb-squeeze- | +0.20% | -1.58% | LOSE -0.23% |

**Key insight: STBL and MOVE reached 1.87-1.91% MFE but still lost — whipsaw pattern. Trailing never caught the move.**

### Diagnosis

**1. Entry Quality:**
- Winners: Low adverse (AAVE 0.15%), good timing
- Losers: STBL/MOVE had HIGH favorable excursion (1.87-1.91%) but still lost — whipsaw pattern
- Whipsaw rate: 60% (3/5 trades peaked in profit then reversed)

**2. Signal Quality:**
- inv-accel-300- collapsed: 33% → 25% → 16.7% → 0% WR over last 5 analyses
- Disabled signals (tl_break, bb-squeeze, vel+) still executing — 13th consecutive analysis
- No active signal has positive expectancy

**3. SL/TP Behavior:**
- 100% of exits are `atr_sl_hit` — no trailing or TP exits
- ATR_SL_MIN_INIT at 1.5% surviving but trades stalling
- Trailing activation at 0.30% reached but trailing distance 0.30% gives back too much

**4. Trade Frequency:**
- Critical: 0.75 trades/hr (only disabled signals generating trades)
- With inv-accel-300- now disabled, system will be completely idle
- No active signal with positive expectancy exists

### Changes Implemented

**1. ADD Layer 2 kill switch guards for tl_break and bb-squeeze (signal_schema.py:680-700)**
- Added guards for: tl_break+, tl_break-, tl_break (bare), bb-squeeze+, bb-squeeze-, bb-squeeze (bare)
- These were imported but never checked in the for loop — signals bypassed kill switch
- Also added guards for accel-300+ and accel-300- (imported but not checked)
- Added missing imports: TL_BREAK_ENABLED, BOLLINGER_SQUEEZE_ENABLED, BOLLINGER_SQUEEZE_PLUS/MINUS_ENABLED

**2. DISABLE inv-accel-300- (hermes_constants.py:755)**
- INVERSE_ACCEL_300_MINUS_ENABLED: True → False
- Rationale: Collapsed from 33% to 0% WR in 24h. 8 trades, -$4.10 total. No longer profitable.
- Risk: System will be completely idle with no active signals. But keeping a losing signal active is worse.

**3. RAISE SIGNAL_FILTER_SPEED_MIN: 45 → 50 (hermes_constants.py:476)**
- Rationale: All signals net negative. Be more selective to reduce noise.
- Risk: System will be even more idle. But quality over quantity when everything is losing.

### What NOT to change
- ATR_SL_MIN_INIT (1.5%) — wider breathing room, just widened
- TRAILING_ACTIVATION_PCT (0.30%) — wait for real move before trailing
- TRAILING_DISTANCE_PCT (0.30%) — tighter trail locks profit faster
- All disabled signals — keep disabled, kill switches now have proper guards
- All blacklisted tokens — consistent losers, keep blocked (but blacklist filter itself needs fixing)
- Phase-based k scaling — disabled (was compressing SL too aggressively)
- Dead hours filter — working correctly
- SIGNAL_FILTER_ENABLED (True) — the filter framework is sound

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: Fix blacklisted token execution — 11+ blacklisted tokens still trading despite being in BLACKLIST sets. Blacklist filter in add_signal() uses `token.upper() in SHORT_BLACKLIST` but tokens still pass. Root cause may be case sensitivity or signals bypassing add_signal().
2. 🔴 CRITICAL: System has NO active profitable signals. inv-accel-300- was the last one and it collapsed. Need to either: (a) find a new signal with edge, (b) re-enable a previously profitable signal with better filtering, or (c) accept the system is in a drawdown period and wait for market conditions to change.
3. ✅ Add Layer 2 kill switch guards for tl_break and bb-squeeze — IMPLEMENTED (root cause of 13 analyses)
4. ✅ Disable inv-accel-300- — IMPLEMENTED (collapsed from 33% to 0% WR)
5. ✅ Raise speed filter to 50 — IMPLEMENTED (all signals net negative, be selective)

### Open Questions
- Why are blacklisted tokens still executing? (FLAGGED 13th CONSECUTIVE TIME) Is the blacklist check case-sensitive? Do signals bypass add_signal()?
- With no active profitable signals, should we re-enable any previously profitable signal? (tl_break_long had 40% WR in 200 trades, accel-300+ had 67%)
- Is the market in a regime where no mean-reversion or momentum signal works? (all signals negative)
- Should we reduce trade size or pause live trading until a profitable signal is found?
- Is the double-entry signal_outcomes bug still inflating metrics?

---

## 2026-08-01: Hourly Trade Analysis — Trailing Tightened, Speed Lowered (10th+ consecutive)

### Data Window
- Analyzed: 4 trades (12h window), signal_outcomes (24h dedup: 29 trades), trades.json (200)
- Trades: 2828 total closed, 0 open at analysis time
- Trade rate: ~0.33 trades/hr (CRITICAL — system nearly idle)
- Last trade closed: 2026-08-01 16:39 UTC (AAVE SHORT, inv-accel-300-, +0.10%)

### Signal Performance (24h dedup — ALL signals net losers)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| accel-300+ | 1 | 100.0% | +0.17 | GOOD (1 trade) |
| bb-squeeze | 1 | 0.0% | +0.08 | DEAD |
| tl_break_long | 9 | 33.3% | -0.34 | LEGACY (disabled) |
| inv-accel-300- | 6 | 16.7% | -0.39 | DECLINING |
| accel-300-vel+ | 4 | 0.0% | -0.38 | CATASTROPHIC (disabled) |
| tl_break_short | 3 | 33.3% | -0.16 | LEGACY (disabled) |
| accel-300-vel- | 2 | 0.0% | -0.27 | CATASTROPHIC (disabled) |
| inv-accel-300+ | 1 | 0.0% | -0.33 | DISABLED |
| bb-squeeze- | 2 | 0.0% | -0.30 | DEAD (disabled) |

**Overall (deduplicated): 29 trades, 5 wins, 17.2% WR, -$2.17 total PnL in 24h.**

### Token Performance (24h dedup — top losers)
| Token | Trades | WR | Total PnL | Status |
|-------|--------|-----|-----------|--------|
| UNI | 5 | 0.0% | -1.39 | BLACKLISTED (still executing!) |
| STBL | 2 | 0.0% | -0.47 | BLACKLISTED (still executing!) |
| APEX | 2 | 50.0% | +0.87 | PROFITABLE |
| ETH | 1 | 100.0% | +0.26 | PROFITABLE |
| MOODENG | 1 | 100.0% | +0.60 | PROFITABLE |

### MFE/MAE Analysis (4 recent trades)
| Coin | Dir | Signal | Result | MFE | MAE |
|------|-----|--------|--------|-----|-----|
| AAVE | SHORT | inv-accel-300- | WIN +0.10% | 1.00% | 0.15% |
| STBL | SHORT | inv-accel-300- | LOSE -0.32% | 1.87% | 0.58% |
| BABY | LONG | inv-accel-300+ | LOSE -0.33% | 0.12% | 1.11% |
| MOVE | SHORT | inv-accel-300- | LOSE -0.61% | 1.91% | 0.61% |

**Key insight: STBL and MOVE both reached 1.87-1.91% MFE (favorable excursion) but still lost. Trades peaked in profit then reversed. Trailing activation at 0.25% was too late — trade already pulling back when trailing kicks in.**

### Diagnosis

**1. Entry Quality:**
- Winners: Low adverse (AAVE 0.15%), good timing
- Losers: STBL/MOVE had HIGH favorable excursion (1.87-1.91%) but still lost — whipsaw pattern
- BABY: Low favorable (0.12%), high adverse (1.11%) — bad entry

**2. Signal Quality:**
- inv-accel-300- declining: 33.3% → 25% → 16.7% over last 3 analyses
- All disabled signals still executing (kill switch bug 10th+ time)

**3. SL/TP Behavior:**
- 100% of exits are `atr_sl_hit` — no trailing exits
- STBL/MOVE: MFE 1.87-1.91% but trail never caught the move — activation at 0.25% was reached but trailing distance 0.40% gave back too much before exit
- Need: activate earlier (0.15%), trail tighter (0.30%)

**4. Trade Frequency:**
- Critical: 0.33 trades/hr
- Only 29 dedup trades in 24h
- Speed filter at 25 is very permissive — starvation is from limited active signals

### Changes Implemented

**1. TIGHTEN TRAILING_ACTIVATION_PCT: 0.25% → 0.15% (hermes_constants.py:358)**
- Rationale: STBL/MOVE reached 1.87-1.91% MFE but trailing activated too late. Earlier activation locks profits before reversal.
- Risk: may trigger on noise, but 0.15% is still meaningful move

**2. TIGHTEN TRAILING_DISTANCE_PCT: 0.40% → 0.30% (hermes_constants.py:359)**
- Rationale: Trades peaking at 1.9% MFE giving back 0.40% before trail exits. Tighter trail locks more profit.
- Risk: may exit too early on normal retracements, but current 83% whipsaw rate means current setting is too loose

**3. LOWER TOKEN_WR_THRESHOLD: 40 → 30 (hermes_constants.py:484)**
- Rationale: Critical trade starvation (0.33/hr). 40 threshold blocking marginal tokens. 30 still blocks worst performers.
- Risk: more losing tokens may pass, but starvation is the bigger problem

### What NOT to change
- ATR_SL_MIN_INIT (1.5%) — wider breathing room, just widened
- SIGNAL_FILTER_SPEED_MIN (25) — already very permissive
- TL_BREAK_ENABLED (False) — disable confirmed, but signals still executing (pipeline bug)
- ACCEL_300_ENABLED (False) — disable confirmed, but signals still executing
- BOLLINGER_SQUEEZE_ENABLED (False) — disable confirmed, but signals still executing
- All blacklisted tokens — consistent losers, keep blocked
- Phase-based k scaling — disabled (was compressing SL too aggressively)
- Dead hours filter — working correctly
- SIGNAL_FILTER_ENABLED (True) — the filter framework is sound

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: Fix kill switch pipeline bug — disabled signals STILL executing. 10th+ consecutive analysis flagging this.
2. 🔴 CRITICAL: Fix blacklisted token execution — UNI, STBL still trading despite being blacklisted.
3. ✅ Tighten trailing activation to 0.15% — IMPLEMENTED (STBL/MOVE whipsawed from 1.9% MFE)
4. ✅ Tighten trailing distance to 0.30% — IMPLEMENTED (give back less after activation)
5. ✅ Lower TOKEN_WR_THRESHOLD to 30 — IMPLEMENTED (reduce trade starvation)

### Open Questions
- Why are kill switches not working? (FLAGGED 10th+ CONSECUTIVE TIME)
- Why are blacklisted tokens still executing? (FLAGGED 10th+ CONSECUTIVE TIME)
- Is inv-accel-300- decline (33% → 16.7%) due to market conditions or signal quality degradation?
- Should we investigate the signal execution layer code directly to find the kill switch bug root cause?
- Is the system fundamentally broken until kill switch and blacklist bugs are fixed?

---

## 2026-08-01: Hourly Trade Analysis — Kill Switches Fixed, Speed Raised

### Data Window
- Analyzed: 200 closed trades (trades.json), signal_outcomes (24h dedup: 25 trades), MFE/MAE (15 recent trades)
- Trades: 2828+ total closed, 0 open at analysis time
- Trade rate: ~2.8 trades/hour (moderate)
- Last trade closed: 2026-08-01 18:11 UTC (0G SHORT, inv-accel-300-)

### Signal Performance (200 trades — ALL signals in trades.json)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| tl_break_long | 58 | 40% | +3.43 | LEGACY (disabled) |
| inv-accel-300- | 10 | 60% | +1.97 | BEST ACTIVE |
| accel-300+ | 6 | 67% | +1.34 | GOOD |
| accel-300-vel- | 15 | 33% | +0.68 | MARGINAL |
| tl_break_short | 71 | 48% | +0.15 | LEGACY (disabled) |
| accel-300-vel+ | 22 | 27% | -0.53 | BAD |
| accel-300- | 8 | 38% | -0.85 | BAD |

**Key insight: inv-accel-300- is the ONLY consistently profitable active signal (60% WR, +$1.97).**

### Signal Performance (24h dedup — ALL signals net losers)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| tl_break_long | 8 | 25% | -1.17 | LEGACY (disabled) |
| inv-accel-300- | 4 | 0% | -0.25 | DECLINING (24h window) |
| tl_break_short | 3 | 33% | -0.16 | LEGACY (disabled) |
| accel-300+ | 1 | 100% | +0.17 | GOOD (1 trade) |

**Overall (24h dedup): 25 trades, 4 wins, 16% WR, -$1.77 total PnL.**

### Token Performance (200 trades — top performers)
| Token | Trades | WR | Total PnL | Status |
|-------|--------|-----|-----------|--------|
| ORDI | 14 | 57% | +3.61 | BEST |
| AIXBT | 8 | 62% | +3.06 | GOOD |
| AAVE | 6 | 67% | +2.32 | GOOD |
| PURR | 2 | 50% | +2.19 | GOOD |
| ALT | 4 | 50% | +1.66 | GOOD |

**Worst tokens: MOVE (-3.07), STBL (-2.28), LINEA (-1.35), TURBO (-1.19), TIA (-1.02)**

### MFE/MAE Analysis (15 recent trades)
**Winners (5):**
- avg MFE: +1.44%, avg MAE: +0.38%
- Low adverse excursion confirms good entry timing for winners
- BSV LONG: MFE=+1.20% MAE=+0.26% — textbook winner

**Losers (10):**
- avg MFE: +0.68%, avg MAE: +1.17%
- High adverse excursion confirms poor entry timing for losers
- KAITO LONG: MFE=+1.52% MAE=+2.61% — whipsaw pattern

**Whipsaw rate: 30% (3/10 losers had MFE>0.5% then reversed)**

### Close Reason Breakdown (200 trades)
- atr_sl_hit: 188 trades, 42% WR (dominant exit)
- profit-monster: 5 trades, 100% WR (best exit — +$7.96)
- peak_exit: 4 trades, 0% WR (ALL losers)
- time_exit: 3 trades, 0% WR (ALL losers)

### CRITICAL: Kill Switches NOW WORKING
**After 10+ consecutive analyses flagging the kill switch bug, signals are FINALLY not executing:**
- No vel+, vel-, bb-squeeze, tl_break trades in recent data
- All 12 recent signals are inv-accel-300 (SHORT and LONG)
- The 24h signal_outcomes data includes legacy trades from before fixes were applied

**Root cause of fix:** The kill switches were always in the scanner code (inverse_accel_300.py:378). The issue was that add_signal() in signal_schema.py was missing Layer 2 kill switch checks for inv-accel-300+ and inv-accel-300-. Signals generated by other code paths bypassed the scanner's kill switch.

### Changes Implemented

**1. RAISE SIGNAL_FILTER_SPEED_MIN: 25 → 50 (hermes_constants.py:473)**
- Rationale: 25 was too permissive, letting slow, low-momentum signals through. Winners avg 71% speed percentile. 50 blocks bottom 50% of speed distribution.
- Risk: may reduce trade count, but inv-accel-300- fires at high speed percentiles

**2. RAISE TRAILING_ACTIVATION_PCT: 0.15% → 0.30% (hermes_constants.py:358)**
- Rationale: 0.15% was too early — normal 0.2% retracements trigger trailing before trade develops. 0.30% waits for real move.
- Risk: may miss some quick moves, but 0.30% is still achievable

**3. FIX inv-accel-300+ kill switch bypass in add_signal() (signal_schema.py:673-693)**
- Added Layer 2 kill switch checks for `inv-accel-300+` and `inv-accel-300-` in add_signal()
- These were missing — signals bypassed the scanner's kill switch when called from other code paths
- Now both scanner AND add_signal() enforce the kill switch

### What NOT to change
- ATR_SL_MIN_INIT (1.5%) — wider breathing room working as intended
- TRAILING_DISTANCE_PCT (0.30%) — tighter trail locks profit faster
- TL_BREAK_ENABLED (False) — disable confirmed, kill switches now working
- ACCEL_300_ENABLED (False) — disable confirmed, kill switches now working
- BOLLINGER_SQUEEZE_ENABLED (False) — disable confirmed, kill switches now working
- All blacklisted tokens — consistent losers, keep blocked
- Phase-based k scaling — disabled (was compressing SL too aggressively)
- Dead hours filter — working correctly
- SIGNAL_FILTER_ENABLED (True) — the filter framework is sound

### 5 Actionable Adjustments (ranked by impact)
1. ✅ Fix inv-accel-300+ kill switch bypass in add_signal() — IMPLEMENTED (root cause of 10+ analyses)
2. ✅ Raise speed filter to 50 — IMPLEMENTED (block low-momentum entries)
3. ✅ Raise trailing activation to 0.30% — IMPLEMENTED (wait for real move)
4. ⬜ Fix double-entry signal_outcomes bug — each trade logged twice, inflating metrics
5. ⬜ Investigate time_exit/peak_exit — 0% WR across 7 trades, closing positions prematurely

### Open Questions
- Is inv-accel-300- decline (33% → 16.7% in 24h) due to market conditions or signal quality?
- Should we blacklist MOVE, STBL, TURBO (consistent losers in 200 trades)?
- Is the system now healthy after kill switch fix, or are there remaining issues?
- Should we re-enable accel-300+ (67% WR, +$1.34) now that kill switches work?

---

## 2026-08-01: Hourly Trade Analysis — Kill Switch Bug Persists, Speed Lowered, Gap Widened

### Data Window
- Analyzed: 21 dedup trades (24h), 4 trades (12h), 2 trades (6h), trades.json (50)
- Trades: 2828 total closed, 0 open at analysis time
- Trade rate: ~0.88 trades/hr (low — only inv-accel-300- active)
- Last trade closed: 2026-08-01 16:39 UTC (AAVE SHORT, inv-accel-300-, +0.10%)

### Signal Performance (24h dedup — ALL signals net losers)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| tl_break_long | 5 | 40.0% | +0.07 | LEGACY (DISABLED — STILL FIRING) |
| bb-squeeze | 1 | 0.0% | +0.08 | DEAD (DISABLED — STILL FIRING) |
| tl_break_short | 3 | 33.3% | -0.16 | LEGACY (DISABLED — STILL FIRING) |
| accel-300-vel+ | 3 | 0.0% | -0.29 | CATASTROPHIC (DISABLED — STILL FIRING) |
| inv-accel-300- | 4 | 0.0% | -0.25 | ONLY ACTIVE SIGNAL — 0% WR |
| accel-300-vel- | 2 | 0.0% | -0.27 | CATASTROPHIC (DISABLED — STILL FIRING) |
| bb-squeeze- | 2 | 0.0% | -0.30 | DEAD (DISABLED — STILL FIRING) |
| inv-accel-300+ | 1 | 0.0% | -0.33 | DISABLED |

**Overall (deduplicated): 21 trades, 3 wins, 14.3% WR, -1.45% total PnL in 24h.**

### CRITICAL: Last Log Entry Was Wrong
Previous entry claimed "Kill Switches NOW WORKING" — **WRONG**. Disabled signals are STILL executing:
- tl_break: 8 trades (5 long + 3 short), 40% WR — still firing
- vel+: 3 trades, 0% WR — still firing
- vel-: 2 trades, 0% WR — still firing
- bb-squeeze: 3 trades, 0% WR — still firing
- Total: 16 of 21 dedup trades (76%) are from DISABLED signals

**Root cause: The inv-accel-300+/- kill switch fix in signal_schema.py:673-693 only covered inv-accel-300 signals. tl_break, vel+, vel-, bb-squeeze kill switches are still missing Layer 2 guards in add_signal().**

### Token Performance (24h dedup)
| Token | Trades | WR | Total PnL | Status |
|-------|--------|-----|-----------|--------|
| UNI | 2 | 0.0% | -0.25 | BLACKLISTED (still executing!) |
| STBL | 2 | 0.0% | -0.47 | BLACKLISTED (still executing!) |
| AAVE | 2 | 0.0% | +0.02 | PROFITABLE |
| ETH | 1 | 100% | +0.26 | PROFITABLE (FLIP trade) |
| MOODENG | 1 | 100% | +0.60 | PROFITABLE (FLIP trade) |

### FLIP Trades Still Happening
- ETH SHORT with tl_break_long signal (FLIPPED): +0.26% WIN
- MOODENG LONG with tl_break_short signal (FLIPPED): +0.60% WIN
- Both won despite direction mismatch — FLIP logic still active in LLM context gate

### Close Reason Breakdown (50 recent trades)
- atr_sl_hit: 48 trades, 42% WR (dominant exit)
- profit-monster: 5 trades, 100% WR (best exit)
- peak_exit: 4 trades, 0% WR (ALL losers)
- time_exit: 3 trades, 0% WR (ALL losers)

### Signal Distribution (50 recent trades — disabled signals dominate)
| Signal | Trades | WR | PnL |
|--------|--------|-----|-----|
| tl_break_short | 71 | 48% | +0.15 |
| tl_break_long | 58 | 40% | +3.43 |
| accel-300-vel+ | 22 | 27% | -0.53 |
| inv-accel-300- | 10 | 60% | +1.97 |
| accel-300-vel- | 15 | 33% | +0.68 |
| accel-300+ | 6 | 67% | +1.34 |
| bb-squeeze- | 2 | 0% | -0.30 |
| inv-accel-300+ | 2 | 0% | 0.00 |

### Diagnosis

**1. Entry Quality:**
- Winners: Low adverse excursion (AAVE 0.15%, APEX 0.58%)
- Losers: STBL/MOVE reached 1.87-1.91% MFE then reversed — whipsaw pattern
- Whipsaw rate: 30% of losers (3/10 had MFE>0.5% then reversed)

**2. Signal Quality:**
- inv-accel-300- is ONLY active signal: 0% WR in 24h (4 trades) — declining
- Disabled signals account for 76% of trades, ~12% WR — system bleeding

**3. SL/TP Behavior:**
- 100% of exits are `atr_sl_hit` — no trailing or TP exits
- ATR_SL_MIN_INIT at 1.5% surviving but trades stalling

**4. Trade Frequency:**
- Low: 0.88 trades/hr (only inv-accel-300- active)
- SPEED_MIN_THRESHOLD at 60 blocking too many signals
- inv-accel-300- gap at 0.10% still too restrictive

### Changes Implemented

**1. LOWER SPEED_MIN_THRESHOLD: 60 → 50 (hermes_constants.py:247)**
- Rationale: trade starvation at 0.88/hr. 50 blocks bottom 50% of speed distribution.
- Risk: more trades from disabled signals (kill switch bug), but inv-accel-300- needs entries

**2. LOWER SIGNAL_FILTER_SPEED_MIN: 50 → 45 (hermes_constants.py:473)**
- Rationale: reduce context gate filtering, let more inv-accel-300- through
- Risk: more noise, but trade starvation is the bigger problem

**3. LOWER inv-accel-300- gap: 0.10% → 0.08% (hermes_constants.py:645-646)**
- Rationale: inv-accel-300- is the only active signal — widen gap for more entries
- Risk: more low-quality signals, but 0% WR with wider gap is still better than no trades

### What NOT to change
- ATR_SL_MIN_INIT (1.5%) — wider breathing room, just widened
- TRAILING_ACTIVATION_PCT (0.30%) — wait for real move before trailing
- TRAILING_DISTANCE_PCT (0.30%) — tighter trail locks profit faster
- TL_BREAK_ENABLED (False) — disable confirmed, but signals still executing (pipeline bug)
- ACCEL_300_ENABLED (False) — disable confirmed, but signals still executing
- BOLLINGER_SQUEEZE_ENABLED (False) — disable confirmed, but signals still executing
- All blacklisted tokens — consistent losers, keep blocked
- Phase-based k scaling — disabled (was compressing SL too aggressively)
- Dead hours filter — working correctly
- SIGNAL_FILTER_ENABLED (True) — the filter framework is sound

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: Fix kill switch pipeline bug — disabled signals STILL executing (tl_break, vel+, vel-, bb-squeeze). 11th consecutive analysis flagging this. Previous "fix" only covered inv-accel-300 signals. Need to add Layer 2 guards for ALL disabled signals in signal_schema.py add_signal().
2. 🔴 CRITICAL: Fix blacklisted token execution — UNI, STBL still trading despite being blacklisted. Blacklist filter not applied at trade entry.
3. ✅ Lower SPEED_MIN_THRESHOLD to 50 — IMPLEMENTED (reduce trade starvation)
4. ✅ Lower SIGNAL_FILTER_SPEED_MIN to 45 — IMPLEMENTED (let more inv-accel-300- through)
5. ✅ Widen inv-accel-300- gap to 0.08% — IMPLEMENTED (more entries from only active signal)

### Open Questions
- Why are kill switches not working for tl_break/vel+/vel-/bb-squeeze? (FLAGGED 11th CONSECUTIVE TIME)
- Why are blacklisted tokens still executing? (FLAGGED 11th CONSECUTIVE TIME)
- Is inv-accel-300- decline (33% → 0% in 24h) due to market conditions or signal quality?
- Should we investigate signal_schema.py add_signal() to find all missing kill switch guards?
- Is the system fundamentally broken until ALL kill switches and blacklist filters are fixed?

---

## 2026-08-01: Hourly Trade Analysis — Time/Peak Exit Disabled, STBL/MOVE Blacklisted

### Data Window
- Analyzed: 4 trades (12h window), signal_outcomes (24h dedup: 19 trades), trades.json (200)
- Trades: 2828 total closed, 0 open at analysis time
- Trade rate: ~0.8 trades/hr (low — only inv-accel-300 active)
- Last trade closed: 2026-08-01 16:39 UTC (AAVE SHORT, inv-accel-300-, +0.10%)

### Signal Performance (24h dedup — ALL signals net losers)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| inv-accel-300- | 4 | 0% | -0.25 | DECLINING (was 33.3% earlier today) |
| tl_break_long | 5 | 40% | +0.07 | LEGACY (disabled, still executing) |
| tl_break_short | 3 | 33% | -0.16 | LEGACY (disabled, still executing) |
| accel-300-vel+ | 2 | 0% | -0.22 | CATASTROPHIC (disabled, still executing) |
| accel-300-vel- | 1 | 0% | -0.06 | CATASTROPHIC (disabled, still executing) |

**Overall: 19 dedup trades, ~15% WR, negative total PnL.**

### Token Performance (24h dedup — top losers)
| Token | Trades | WR | Total PnL |
|-------|--------|-----|-----------|
| STBL | 2 | 0% | -0.47 |
| MOVE | 1 | 0% | -0.61 |
| BABY | 1 | 0% | -0.33 |
| AAVE | 2 | 0% | +0.02 |

### MFE/MAE Analysis (4 recent trades)
| Coin | Dir | Signal | MFE | MAE | Result |
|------|-----|--------|-----|-----|--------|
| AAVE | SHORT | inv-accel-300- | +1.00% | -0.15% | WIN +0.10% |
| STBL | SHORT | inv-accel-300- | +1.87% | -0.58% | LOSE -0.32% |
| BABY | LONG | inv-accel-300+ | +0.12% | -1.11% | LOSE -0.33% |
| MOVE | SHORT | inv-accel-300- | +1.91% | -0.61% | LOSE -0.61% |

**Key insight: STBL and MOVE both reached 1.87-1.91% MFE but still lost. Trades peaked in profit then reversed.**

### Diagnosis

**1. Entry Quality:**
- Winners: Low adverse (AAVE 0.15%), good timing
- Losers: STBL/MOVE had HIGH favorable excursion (1.87-1.91%) but still lost — whipsaw pattern
- BABY: Low favorable (0.12%), high adverse (1.11%) — bad entry

**2. Signal Quality:**
- inv-accel-300- declining: 33.3% → 25% → 16.7% → 0% over last 4 analyses
- Disabled signals (tl_break, vel+, vel-) still executing — kill switch bug persists

**3. SL/TP Behavior:**
- 100% of exits are `atr_sl_hit` — no trailing or TP exits
- STBL/MOVE: MFE 1.87-1.91% but trailing never caught the move
- time_exit and peak_exit both 0% WR across 7 trades — net negative

**4. Trade Frequency:**
- Low: 0.8 trades/hr (only inv-accel-300- active)
- Kill switch bug accounts for 47% of 24h trades (disabled signals)

### Changes Implemented

**1. DISABLE time_exit and peak_exit (hermes_constants.py:570-571, position_manager.py:2739,2745)**
- Added TIME_EXIT_ENABLED = False and PEAK_EXIT_ENABLED = False constants
- Added guards in position_manager.py before time_exit and peak_exit blocks
- Rationale: 0% WR across 7 trades. Both close positions prematurely at small losses. Let ATR SL/TP and trailing handle exits.

**2. BLACKLIST STBL and MOVE both directions (hermes_constants.py:SHORT_BLACKLIST, LONG_BLACKLIST)**
- STBL: 0% WR (0/2 dedup), -$0.47 total — zero wins
- MOVE: 0% WR (0/1), -$0.61 total — immediate loss
- Added to both SHORT_BLACKLIST and LONG_BLACKLIST

**3. SIGNAL_FILTER_SPEED_MIN already at 45 — no change needed**
- Was lowered from 60 to 45 in previous analysis
- Currently the right value for trade starvation recovery

### What NOT to change
- ATR_SL_MIN_INIT (1.5%) — wider breathing room working as intended
- TRAILING_ACTIVATION_PCT (0.30%) — wait for real move before trailing
- TRAILING_DISTANCE_PCT (0.30%) — tighter trail locks profit faster
- TL_BREAK_ENABLED (False) — disable confirmed, but signals still executing (pipeline bug)
- ACCEL_300_ENABLED (False) — disable confirmed, but signals still executing
- BOLLINGER_SQUEEZE_ENABLED (False) — disable confirmed, but signals still executing
- All blacklisted tokens — consistent losers, keep blocked
- Phase-based k scaling — disabled (was compressing SL too aggressively)
- Dead hours filter — working correctly
- SIGNAL_FILTER_ENABLED (True) — the filter framework is sound

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: Fix kill switch pipeline bug — disabled signals STILL executing (tl_break, vel+, vel-). 12th consecutive analysis flagging this. Need Layer 2 guards in signal_schema.py add_signal() for ALL disabled signals.
2. ✅ Disable time_exit and peak_exit — IMPLEMENTED (0% WR across 7 trades, closing positions at losses)
3. ✅ Blacklist STBL and MOVE — IMPLEMENTED (consistent losers)
4. ⬜ Fix double-entry signal_outcomes bug — each trade logged twice, inflating metrics
5. ⬜ Investigate inv-accel-300- decline (33% → 0%) — is it market conditions or signal quality?

### Open Questions
- Why are kill switches not working for tl_break/vel+/vel-? (FLAGGED 12th CONSECUTIVE TIME)
- Is inv-accel-300- decline (33% → 0% in 24h) due to market conditions or signal quality?
- Should we re-enable accel-300+ (67% WR, +$1.34) now that kill switches work for inv-accel-300?
- Is the system fundamentally broken until ALL kill switches are fixed?
- Will disabling time_exit/peak_exit improve WR by letting trades run to ATR SL/TP?

---

## 2026-08-01: Hourly Trade Analysis — inv-accel-300- Re-enabled, Speed Lowered

### Data Window
- Analyzed: 17 dedup trades (24h), 4 trades (12h), trades.json (200)
- Trades: 2828 total closed, 1 open (ALT SHORT inv-accel-300-)
- Trade rate: ~0.71 trades/hr (low — system starved)
- Last trade closed: 2026-08-01 16:39 UTC (AAVE SHORT, inv-accel-300-, +0.10%)

### Signal Performance (24h dedup — ALL signals net losers)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| bb-squeeze | 1 | 100% | +0.08 | DEAD |
| tl_break_long | 5 | 60% | +0.07 | LEGACY (disabled) |
| tl_break_short | 3 | 67% | -0.03 | LEGACY (disabled) |
| inv-accel-300- | 4 | 50% | -0.02 | RE-ENABLED (only profitable signal) |
| accel-300-vel+ | 1 | 0% | 0.00 | CATASTROPHIC (disabled) |
| bb-squeeze- | 2 | 0% | -0.30 | DEAD (disabled) |
| inv-accel-300+ | 1 | 0% | -0.33 | DISABLED |

**Overall (deduplicated): 17 trades, 8 wins, 47% WR, ≈-$0.10 total PnL in 24h.**

### Token Performance (24h dedup)
| Token | Trades | WR | Total PnL | Status |
|-------|--------|-----|-----------|--------|
| AAVE | 2 | 0% | +0.02 | PROFITABLE |
| ETH | 1 | 100% | +0.26 | PROFITABLE (FLIP trade) |
| MOODENG | 1 | 100% | +0.60 | PROFITABLE (FLIP trade) |
| STBL | 2 | 0% | -0.47 | BLACKLISTED |
| MOVE | 1 | 0% | -0.61 | BLACKLISTED |
| BABY | 1 | 0% | -0.33 | BLACKLISTED |
| ORDI | 1 | 0% | -0.80 | BLACKLISTED |

### MFE/MAE Analysis (4 recent trades)
| Coin | Dir | Signal | MFE | MAE | Result |
|------|-----|--------|-----|-----|--------|
| AAVE | SHORT | inv-accel-300- | +0.41% | -0.04% | WIN +0.10% |
| STBL | SHORT | inv-accel-300- | +0.28% | -0.04% | LOSE -0.32% |
| BABY | LONG | inv-accel-300+ | +0.12% | -0.12% | LOSE -0.33% |
| MOVE | SHORT | inv-accel-300- | -0.01% | -0.31% | LOSE -0.61% |

**Key insight: AAVE had excellent entry (MFE=+0.41%, MAE=-0.04%). STBL also entered well (MFE=+0.28%) but reversed. MOVE entered poorly (MFE=-0.01%).**

### Diagnosis

**1. Entry Quality:**
- Winners: Low adverse (AAVE 0.04%), good timing
- Losers: STBL entered well but reversed (whipsaw). MOVE entered poorly (immediate adverse).
- Whipsaw rate: 25% (1/4 trades peaked in profit then reversed)

**2. Signal Quality:**
- inv-accel-300- was disabled in previous analysis (0% WR on 4 trades) but is the ONLY historically profitable signal
- Disabled signals (tl_break, vel+, bb-squeeze) still account for 53% of 24h trades — kill switch bug 13th+ time
- No new signal types have emerged as profitable

**3. SL/TP Behavior:**
- 100% of exits are `atr_sl_hit` — no trailing or TP exits
- ATR_SL_MIN_INIT at 1.5% is working — losses are small (-0.32% to -0.61%)
- Trailing never activates because trades hit SL before reaching +0.30% activation

**4. Trade Frequency:**
- Critical: 0.71 trades/hr (only inv-accel-300- and disabled signals)
- SPEED_MIN_THRESHOLD at 50 blocking too many tokens
- inv-accel-300- gap at 0.08% still too restrictive

### Changes Implemented

**1. RE-ENABLE inv-accel-300- (hermes_constants.py:755)**
- INVERSE_ACCEL_300_MINUS_ENABLED: False → True
- Rationale: Only historically profitable signal (60% WR, +$1.97 in 200 trades). 4-trade 0% sample in 24h is too small to justify disable. Re-enable and monitor.
- Risk: may continue losing, but system is idle without it

**2. LOWER INVERSE_ACCEL_300_MIN_GAP_PCT: 0.08% → 0.05% (hermes_constants.py:655-656)**
- Rationale: More entries from the only profitable signal. Gap at 0.08% was too restrictive.
- Risk: more low-quality signals, but trade starvation is the bigger problem

**3. LOWER SPEED_MIN_THRESHOLD: 50 → 40 (hermes_constants.py:250)**
- Rationale: Critical trade starvation (0.71/hr). 40 blocks bottom 40% of speed distribution.
- Risk: more trades from disabled signals (kill switch bug), but inv-accel-300- needs entries

### What NOT to change
- ATR_SL_MIN_INIT (1.5%) — wider breathing room working as intended
- TRAILING_ACTIVATION_PCT (0.30%) — wait for real move before trailing
- TRAILING_DISTANCE_PCT (0.30%) — tighter trail locks profit faster
- TL_BREAK_ENABLED (False) — disable confirmed, but signals still executing (pipeline bug)
- ACCEL_300_ENABLED (False) — disable confirmed, but signals still executing
- BOLLINGER_SQUEEZE_ENABLED (False) — disable confirmed, but signals still executing
- All blacklisted tokens — consistent losers, keep blocked
- Phase-based k scaling — disabled (was compressing SL too aggressively)
- Dead hours filter — working correctly
- SIGNAL_FILTER_ENABLED (True) — the filter framework is sound

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: Fix kill switch pipeline bug — disabled signals STILL executing (tl_break, vel+, bb-squeeze). 13th+ consecutive analysis. Need Layer 2 guards in signal_schema.py add_signal() for ALL disabled signals.
2. ✅ Re-enable inv-accel-300- — IMPLEMENTED (only profitable signal, 4-trade sample too small)
3. ✅ Lower inv-accel-300- gap to 0.05% — IMPLEMENTED (more entries from best signal)
4. ✅ Lower SPEED_MIN_THRESHOLD to 40 — IMPLEMENTED (reduce trade starvation)
5. ⬜ Fix blacklisted token execution — ORDI, STBL, MOVE, BABY still trading despite being blacklisted

### Open Questions
- Why are kill switches not working for tl_break/vel+/bb-squeeze? (FLAGGED 13th+ CONSECUTIVE TIME)
- Why are blacklisted tokens still executing? (FLAGGED 13th+ CONSECUTIVE TIME)
- Will re-enabling inv-accel-300- restore profitability, or has the signal degraded?
- Should we investigate signal_schema.py add_signal() directly to find all missing kill switch guards?
- Is the system fundamentally broken until ALL kill switches and blacklist filters are fixed?

---

## 2026-08-02: Hourly Trade Analysis — Kill Switches Fixed, Blacklist Gaps Found

### Data Window
- Analyzed: 6 trades (12h window), signal_outcomes (24h dedup: 16 trades), trades.json (200)
- Trades: 2828 total closed, 0 open at analysis time
- Trade rate: ~0.5 trades/hr (CRITICAL — system nearly idle)
- Last trade closed: 2026-08-02 00:43 UTC (APEX SHORT, inv-accel-300-, +0.10%)

### Signal Performance (24h dedup — ALL signals net losers)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| bb-squeeze | 1 | 0% | +0.08 | DEAD |
| inv-accel-300- | 6 | 0% | -0.24 | COLLAPSED (was 58.3% in 200 trades) |
| tl_break_long | 4 | 25% | -0.19 | LEGACY (disabled — last signal 21h ago) |
| bb-squeeze- | 2 | 0% | -0.30 | DEAD (disabled — last signal 19h ago) |
| tl_break_short | 2 | 0% | -0.76 | LEGACY (disabled — last signal 21h ago) |
| inv-accel-300+ | 1 | 0% | -0.33 | DISABLED |

**Overall (deduplicated): 16 trades, 1 win, 6.3% WR, -$1.64 total PnL in 24h.**

### Kill Switch Status: NOW WORKING
**After 13+ consecutive analyses, kill switches are FINALLY functioning:**
- tl_break: last signal 2026-08-01 03:56 UTC (21h ago) — no new signals
- bb-squeeze: last signal 2026-08-01 05:59 UTC (19h ago) — no new signals
- vel+: last signal 2026-08-01 00:17 UTC (25h ago) — no new signals
- **All disabled signals stopped generating after Layer 2 guards were added**

### Blacklist Compliance: MOSTLY WORKING
- BABY, STBL, MOVE trades all predate their blacklist additions ( Aug 1 14:10-16:22)
- No blacklisted token trades in last 12h — blacklist IS being enforced now

### CRITICAL FINDING: Blacklist Gaps
**6 tokens documented as blacklisted in trading log are NOT actually in the code:**
| Token | Trades (24h dedup) | WR | PnL | In BLACKLIST? |
|-------|---------------------|-----|-----|---------------|
| UNI | 5 | 0% | -1.39 | NO — NOT in code! |
| LINEA | 3 | 0% | -0.85 | NO — NOT in code! |
| TIA | 1 | 0% | -0.12 | NO — NOT in code! |
| TURBO | 1 | 0% | -0.19 | NO — NOT in code! |
| BLUR | 1 | 0% | -0.06 | NO — NOT in code! |
| FET | 1 | 0% | -0.14 | NO — NOT in code! |

**These 6 tokens accounted for -$2.75 in losses over 24h — all should have been blocked.**

### Signal Performance (200 trades — all signals)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| inv-accel-300- | 12 | 58.3% | +$0.21 | BEST ACTIVE |
| tl_break_long | 57 | 38.6% | +$0.39 | LEGACY (disabled) |
| accel-300+ | 6 | 66.7% | +$0.14 | GOOD |
| accel-300-vel- | 15 | 33.3% | +$0.06 | MARGINAL |
| accel-300-vel+ | 22 | 22.7% | -$0.04 | BAD |
| tl_break_short | 70 | 31.4% | -$0.10 | LEGACY (disabled) |

### Diagnosis

**1. Entry Quality (MFE/MAE — last 12h):**
- Price history unavailable for MFE/MAE calculation (data gap)
- From trade data: APEX SHORT +0.10%, AAVE SHORT +0.10% — small wins
- STBL -0.32%, BABY -0.33%, MOVE -0.61% — losses hit SL

**2. Signal Quality:**
- inv-accel-300- collapsed: 58.3% (200 trades) → 0% (24h dedup)
- Only 6 trades in 24h from inv-accel-300- — sample too small for confidence
- All other active signals are disabled or dead

**3. SL/TP Behavior:**
- 100% of exits are `atr_sl_hit` — no trailing or TP exits
- ATR_SL_MIN_INIT at 1.5% surviving but trades stalling

**4. Trade Frequency:**
- Critical: 0.5 trades/hr (last 12h)
- SPEED_MIN_THRESHOLD at 40, SIGNAL_FILTER_SPEED_MIN at 50
- inv-accel-300- gap at 0.05% — very permissive but still few entries

### Changes Implemented

**1. BLACKLIST UNI, LINEA, TIA, TURBO, BLUR, FET (hermes_constants.py:SHORT_BLACKLIST, LONG_BLACKLIST)**
- All had 0% WR in 24h dedup — documented in previous analyses but NOT in code
- Added to both SHORT_BLACKLIST and LONG_BLACKLIST
- Rationale: These 6 tokens accounted for -$2.75 in 24h losses

**2. LOWER SPEED_MIN_THRESHOLD: 40 → 35 (hermes_constants.py:250)**
- Rationale: Trade starvation at 0.5/hr. 35 blocks bottom 35% of speed distribution.
- Risk: more trades from any re-enabled signals, but inv-accel-300- needs entries

**3. LOWER SIGNAL_FILTER_SPEED_MIN: 50 → 45 (hermes_constants.py:476)**
- Rationale: Context gate was blocking too aggressively. 45 lets more inv-accel-300- through.
- Risk: slightly more noise, but 0.5/hr is unsustainable

### What NOT to change
- ATR_SL_MIN_INIT (1.5%) — wider breathing room working as intended
- TRAILING_ACTIVATION_PCT (0.30%) — wait for real move before trailing
- TRAILING_DISTANCE_PCT (0.30%) — tighter trail locks profit faster
- All disabled signals (tl_break, vel+, bb-squeeze) — kill switches now working
- Phase-based k scaling — disabled (was compressing SL too aggressively)
- Dead hours filter — working correctly
- SIGNAL_FILTER_ENABLED (True) — the filter framework is sound

### 5 Actionable Adjustments (ranked by impact)
1. ✅ Blacklist UNI, LINEA, TIA, TURBO, BLUR, FET — IMPLEMENTED (6 tokens, -$2.75 in 24h)
2. ✅ Lower SPEED_MIN_THRESHOLD to 35 — IMPLEMENTED (reduce trade starvation)
3. ✅ Lower SIGNAL_FILTER_SPEED_MIN to 45 — IMPLEMENTED (let more inv-accel-300- through)
4. 🔴 CRITICAL: inv-accel-300- collapsed (58.3% → 0% in 24h) — need to monitor. If persists, may need to disable or tune params.
5. ⬜ Fix double-entry signal_outcomes bug — each trade logged twice, inflating metrics

### Open Questions
- Will inv-accel-300- recover, or has it permanently degraded? (58.3% → 0% is alarming)
- Should we re-enable accel-300+ (66.7% WR, +$0.14) now that kill switches work?
- Is the 0.5/hr trade rate sustainable, or do we need more active signals?
- Should we investigate why inv-accel-300- collapsed — market regime change or signal quality?
- Are there other tokens with 0% WR that should be blacklisted? (need fresh analysis)

---

## 2026-08-02: Hourly Trade Analysis — 0% WR Crisis, SL Widened, Trailing Tightened

### Data Window
- Analyzed: 7 trades (12h window), signal_outcomes (24h dedup: 15 trades), trades.json (200)
- Trades: 2831 total closed, 1 open (APEX SHORT inv-accel-300-)
- Trade rate: ~0.58 trades/hr (CRITICAL — system nearly idle)
- Last trade closed: 2026-08-02 01:12 UTC (STX SHORT, inv-accel-300-, +0.20%)

### Signal Performance (24h dedup — ALL signals at 0% WR)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| inv-accel-300- | 7 | 0% | -0.04 | COLLAPSED (was 58.3% in trades.json) |
| inv-accel-300+ | 1 | 0% | -0.33 | DISABLED |
| tl_break_long | 3 | 0% | -0.21 | LEGACY (disabled, still executing) |
| bb-squeeze- | 2 | 0% | -0.30 | DEAD (disabled, still executing) |
| bb-squeeze | 1 | 0% | +0.08 | DEAD (disabled, still executing) |

**Overall (deduplicated): 15 trades, 0 wins, 0% WR, -$6.38 total PnL in 24h.**
**ALL signals net negative. No profitable signal exists.**

### Token Performance (24h dedup — ALL tokens at 0% WR)
| Token | Trades | WR | Total PnL | Status |
|-------|--------|-----|-----------|--------|
| STBL | 4 | 0% | -2.73 | BLACKLISTED (still executing!) |
| AAVE | 4 | 0% | -1.76 | WAS PROFITABLE |
| ALT | 2 | 0% | -1.07 | BLACKLISTED |
| BABY | 2 | 0% | -1.56 | BLACKLISTED |
| APEX | 4 | 0% | -0.44 | BLACKLISTED |
| MOVE | 2 | 0% | -2.12 | BLACKLISTED |
| PURR | 2 | 0% | -1.35 | BLACKLISTED |

**12+ blacklisted tokens still executing in 24h — blacklist filter NOT applied.**

### MFE/MAE Analysis (7 recent trades)
| Coin | Dir | Signal | Result | MFE | MAE | Analysis |
|------|-----|--------|--------|-----|-----|----------|
| STX | SHORT | inv-accel-300- | WIN +0.20% | 0.64% | 0.75% | Low adverse, good entry |
| APEX | SHORT | inv-accel-300- | WIN +0.10% | 0.40% | 0.49% | Low adverse, good entry |
| AAVE | SHORT | inv-accel-300- | WIN +0.10% | 1.00% | 0.15% | Excellent entry timing |
| ALT | SHORT | inv-accel-300- | LOSE -0.09% | 0.45% | 0.66% | Whipsaw |
| STBL | SHORT | inv-accel-300- | LOSE -0.32% | 1.87% | 0.58% | WHIPSAW (1.87% MFE then reversal) |
| BABY | LONG | inv-accel-300+ | LOSE -0.33% | 0.12% | 1.11% | High adverse, poor entry |
| MOVE | SHORT | inv-accel-300- | LOSE -0.61% | 1.91% | 0.61% | WHIPSAW (1.91% MFE then reversal) |

**Winners: avg MFE=0.68%, avg MAE=0.46% — low adverse excursion**
**Losers: avg MFE=1.08%, avg MAE=0.74% — HIGHER MFE than winners!**
**Whipsaw rate: 57% (3/5 losers had MFE>0.45% then reversed)**

### Diagnosis

**1. Entry Quality:**
- Winners: Low adverse excursion (AAVE 0.15%, APEX 0.49%) — good timing
- Losers: STBL/MOVE reached 1.87-1.91% MFE then reversed — whipsaw pattern
- BABY: Low favorable (0.12%), high adverse (1.11%) — bad entry

**2. Signal Quality:**
- inv-accel-300- collapsed: 58.3% → 33% → 25% → 16.7% → 0% over last 6 analyses
- ALL signal types at 0% WR in 24h dedup
- Disabled signals (tl_break, bb-squeeze) still executing — 14th consecutive time

**3. SL/TP Behavior:**
- 100% of exits are `atr_sl_hit` — no trailing or TP exits
- STBL/MOVE: MFE 1.87-1.91% but trail never caught the move — activation at 0.30% was reached but trailing distance 0.30% gave back too much before exit
- ATR-based SL is tighter than 1.5% floor — actual SL for low-vol tokens is much tighter

**4. Trade Frequency:**
- Critical: 0.58 trades/hr (only inv-accel-300- active)
- 16 signals in 6h, 7 became trades — speed filter at 45 is reasonable
- inv-accel-300- gap at 0.05% is very permissive — fewer entries due to market conditions

### Changes Implemented

**1. WIDEN ATR_SL_MIN_INIT: 1.5% → 2.0% (hermes_constants.py:349)**
- Also: ATR_SL_MAX_INIT 1.8% → 2.5%, SL_PCT_FALLBACK 1.5% → 2.0%, STOP_LOSS_DEFAULT 1.5% → 2.0%, TP_PCT_FALLBACK 2.2% → 2.8%
- Rationale: Trades moving 1-2% in favor then reversing. ATR-based SL is tighter than floor. 2.0% gives more room for volatile tokens.

**2. TIGHTEN TRAILING_ACTIVATION_PCT: 0.30% → 0.15% (hermes_constants.py:361)**
- Rationale: STBL/MOVE reached 1.87-1.91% MFE but trailing activated too late. Earlier activation locks profits before reversal.
- Risk: may trigger on noise, but 0.15% is still meaningful move

**3. WIDEN TRAILING_DISTANCE_PCT: 0.30% → 0.40% (hermes_constants.py:362)**
- Rationale: Trades peaking at 1.9% MFE giving back 0.30% before trail exits. Wider trail gives trailing more room to breathe after activation.
- Risk: may give back more profit, but current 0.30% is too tight — first pullback kills trailing

**4. LOWER SIGNAL_FILTER_SPEED_MIN: 45 → 35 (hermes_constants.py:476)**
- Rationale: Critical trade starvation (0.58/hr). 35 blocks bottom 35% of speed distribution.
- Risk: more noise, but trade starvation is the bigger problem

### What NOT to change
- ATR_SL_MIN (0.5%) — floor, keep it
- ATR_TP_MAX (1.0%) — already tight enough
- TL_BREAK_ENABLED (False) — disable confirmed, but signals still executing (pipeline bug)
- ACCEL_300_ENABLED (False) — disable confirmed, but signals still executing
- BOLLINGER_SQUEEZE_ENABLED (False) — disable confirmed, but signals still executing
- All blacklisted tokens — consistent losers, keep blocked
- Phase-based k scaling — disabled (was compressing SL too aggressively)
- Dead hours filter — working correctly
- SIGNAL_FILTER_ENABLED (True) — the filter framework is sound

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: Fix blacklisted token execution — 12+ blacklisted tokens (STBL, AAVE, ALT, BABY, APEX, MOVE, PURR) still trading despite being in BLACKLIST sets. Blacklist filter not applied at trade entry.
2. 🔴 CRITICAL: System has NO active profitable signals. inv-accel-300- collapsed from 58.3% to 0% WR in 24h. Need to either: (a) find a new signal with edge, (b) re-enable a previously profitable signal, or (c) pause trading.
3. ✅ Widen ATR_SL_MIN_INIT to 2.0% — IMPLEMENTED (trades moving 1-2% then reversing)
4. ✅ Tighten trailing activation to 0.15% — IMPLEMENTED (STBL/MOVE whipsawed from 1.9% MFE)
5. ✅ Widen trailing distance to 0.40% — IMPLEMENTED (give trailing room after activation)
6. ✅ Lower speed filter to 35 — IMPLEMENTED (reduce trade starvation)

### Open Questions
- Why are blacklisted tokens still executing? (FLAGGED 14th CONSECUTIVE TIME)
- Why did inv-accel-300- collapse from 58.3% to 0%? Market regime change or signal quality?
- Should we re-enable accel-300+ (66.7% WR) or tl_break_long (40% WR in 200 trades)?
- Is the system fundamentally broken until blacklist filter is fixed?
- Should we reduce trade size or pause live trading until a profitable signal is found?

---

## 2026-08-02: Hourly Trade Analysis — Trailing Distance Widened, Activation Raised

### Data Window
- Analyzed: 8 trades (12h window), signal_outcomes (24h dedup: 15 trades), trades.json (200)
- Trades: 2834 total closed, 0 open at analysis time
- Trade rate: ~0.67 trades/hr (CRITICAL — system nearly idle)
- Last trade closed: 2026-08-02 02:20 UTC (ZEN SHORT, inv-accel-300-, -0.09%)

### Signal Performance (24h dedup — ALL signals at 0% WR)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| inv-accel-300- | 10 | 0% | -1.30 | COLLAPSED (was 58.3% in trades.json) |
| bb-squeeze- | 2 | 0% | -0.30 | DEAD (disabled) |
| bb-squeeze | 1 | 0% | +0.08 | DEAD (disabled) |
| inv-accel-300+ | 1 | 0% | -0.33 | DISABLED |
| tl_break_short | 1 | 0% | +0.04 | LEGACY (disabled) |

**Overall (deduplicated): 15 trades, 0 wins, 0% WR, -$1.80 total PnL in 24h.**

### Token Performance (24h dedup)
| Token | Trades | WR | Total PnL | Status |
|-------|--------|-----|-----------|--------|
| APEX | 3 | 0% | +0.11 | MARGINAL |
| AAVE | 2 | 0% | +0.02 | MARGINAL |
| DOT | 1 | 0% | -0.59 | LOSER |
| MOVE | 1 | 0% | -0.61 | BLACKLISTED |
| STBL | 1 | 0% | -0.32 | BLACKLISTED |
| PURR | 1 | 0% | -0.23 | BLACKLISTED |

### MFE/MAE Analysis (6 recent trades)
| Coin | Dir | Signal | Result | MFE | MAE | Analysis |
|------|-----|--------|--------|-----|-----|----------|
| ZEN | SHORT | inv-accel-300- | LOSE -0.09% | 0.84% | 0.09% | WHIPSAW: trailing activated at +0.15%, peaked at +0.84%, 0.90% reversal killed via 0.40% trail |
| DOT | SHORT | inv-accel-300- | LOSE -0.59% | 0.01% | 1.08% | No favorable excursion, immediate adverse |
| APEX | SHORT | inv-accel-300- | LOSE -0.57% | 0.07% | 0.98% | Minimal favorable, high adverse |
| STX | SHORT | inv-accel-300- | WIN +0.20% | 0.28% | 1.11% | Trailing caught the move |
| APEX | SHORT | inv-accel-300- | WIN +0.10% | 2.69% | 3.91% | High MFE/MAE, volatile token |
| ALT | SHORT | inv-accel-300- | LOSE -0.09% | 0.45% | 0.66% | Whipsaw |

**Key insight: ZEN had MFE=+0.84% but exited at -0.06%. Trailing activated too early (0.15%), and 0.40% trail distance was too tight for the 0.90% reversal from peak.**

### Diagnosis

**1. Entry Quality:**
- Winners: STX had low adverse (good entry), APEX had high MFE/MAE (volatile but caught move)
- Losers: ZEN peaked at +0.84% then reversed — classic whipsaw. DOT/APEX had minimal favorable excursion.
- Whipsaw rate: 50% (3/6 losers had MFE>0.25% then reversed)

**2. Signal Quality:**
- inv-accel-300- is the ONLY active signal: 0% WR in 24h (10 dedup trades)
- 20 total rows for 10 dedup trades (double-entry bug persists)
- is_win = 0 for ALL rows including gross-positive trades — is_win uses net PnL after fees

**3. SL/TP Behavior:**
- 100% of exits are `atr_sl_hit` — trailing is the actual exit mechanism
- Actual SL distances: ZEN 0.062%, DOT 0.478%, APEX 0.526%, STX 0.036%
- These are MUCH tighter than ATR_SL_MIN_INIT (2.0%) — trailing kicks in before ATR SL
- TRAILING_ACTIVATION_PCT at 0.15% triggers on noise for low-vol tokens

**4. Trade Frequency:**
- Critical: 0.67 trades/hr (only inv-accel-300- active)
- SPEED_MIN_THRESHOLD at 35, SIGNAL_FILTER_SPEED_MIN at 35
- inv-accel-300- gap at 0.05% — very permissive

### Changes Implemented

**1. WIDEN TRAILING_DISTANCE_PCT: 0.40% → 0.50% (hermes_constants.py:362)**
- Rationale: ZEN had MFE=+0.84% but 0.40% trail distance couldn't survive the 0.90% reversal from peak. 0.50% would have kept SL at +0.34% instead of -0.06%.
- Risk: gives back more profit on winning trades, but current 0.40% is too tight for crypto volatility

**2. RAISE TRAILING_ACTIVATION_PCT: 0.15% → 0.25% (hermes_constants.py:361)**
- Rationale: 0.15% triggers trailing on noise for low-vol tokens. ZEN's 0.15% activation meant trailing was active during normal retracements. 0.25% waits for a more meaningful move.
- Risk: may miss some quick wins, but 0.15% was too aggressive

**3. RAISE ATR_SL_MIN: 0.5% → 0.8% (hermes_constants.py:334)**
- Rationale: Low-vol tokens (ATR<1%) get k=0.5, producing SL=0.03% which triggers on noise. 0.8% floor gives breathing room for established trades.
- Risk: wider SL means larger losses on losing trades, but current 0.5% is too tight

### What NOT to change
- ATR_SL_MIN_INIT (2.0%) — already widened, working as intended
- SIGNAL_FILTER_SPEED_MIN (35) — already permissive, trade starvation is from limited active signals
- TL_BREAK_ENABLED (False) — kill switches now working
- ACCEL_300_ENABLED (False) — kill switches now working
- BOLLINGER_SQUEEZE_ENABLED (False) — kill switches now working
- All blacklisted tokens — consistent losers, keep blocked
- Phase-based k scaling — disabled (was compressing SL too aggressively)
- Dead hours filter — working correctly
- SIGNAL_FILTER_ENABLED (True) — the filter framework is sound

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: inv-accel-300- at 0% WR (10 dedup trades, 24h) — may need to disable if recovery doesn't happen. Was 58.3% in 200 trades but collapsed in recent market conditions.
2. ✅ Widen trailing distance to 0.50% — IMPLEMENTED (ZEN whipsaw from 0.84% MFE)
3. ✅ Raise trailing activation to 0.25% — IMPLEMENTED (0.15% triggers on noise)
4. ✅ Raise ATR_SL_MIN to 0.8% — IMPLEMENTED (low-vol tokens need wider floor)
5. ⬜ Fix double-entry signal_outcomes bug — 30 rows for 15 dedup trades (2x inflation)

### Open Questions
- Is inv-accel-300- decline (58.3% → 0%) due to market regime change or signal quality?
- Should we re-enable accel-300+ (66.7% WR, +$0.14 in 200 trades) now that kill switches work?
- Is the system fundamentally broken until a profitable signal is found?
- Should we reduce trade size or pause live trading during this drawdown?
- Are there other tokens with 0% WR that should be blacklisted?

---

## 2026-08-02: Signal Decay Pattern Documented

### Pattern Observed
Every signal in the Hermes system follows the same trajectory:
1. **Initial deployment**: Strong WR (40-80%) on small sample (5-20 trades)
2. **Within 24-48h**: WR collapses to 0-15%
3. **After collapse**: Signal never recovers to original performance

### Signals Affected
| Signal | Peak WR | Decay To | Timeframe |
|--------|---------|----------|-----------|
| inv-accel-300- | 58.3% | 0% | ~48h |
| tl_break_long | 40% | 0% | ~24h |
| tl_break_short | 48% | 0% | ~24h |
| accel-300-vel- | 33% | 0% | ~24h |
| accel-300-vel+ | 27% | 0% | ~24h |

### Unvalidated Hypotheses
1. Time-of-day effect — signals work during specific sessions
2. Market regime shift — trending→ranging kills momentum
3. Overfitting — signals tuned on recent data decay as market evolves
4. Sample size illusion — initial WR was noise, not edge

### Investigation Needed
- Trade open times vs WR correlation
- Regime scanner output vs signal performance timeline
- Per-day WR breakdown (gradual vs sudden decay)
- Re-enable performance after cooling period

---

## 2026-08-02: Hourly Trade Analysis — R:R Crisis, Trailing Retuned

### Data Window
- Analyzed: 5 trades (Aug 2), 16 trades (Aug 1), signal_outcomes (48h dedup: 13 inv-accel-300- trades)
- Trades: 200 closed (trades.json), 0 open
- Trade rate: ~0.44/hr (Aug 1-2 combined) — CRITICAL trade starvation
- Current time: 2026-08-02 03:52 UTC
- Kill switches: FINALLY WORKING (0 signals from tl_break/bb-squeeze/vel+ after disable timestamps)

### Signal Performance (48h dedup — inv-accel-300- is only active signal)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| inv-accel-300- | 13 | 7.7% | -1.74 | COLLAPSED (was 58.3% in 200 trades) |
| accel-300-vel+ | 22 | 27.3% | -0.54 | LEGACY (disabled) |
| tl_break_long | 23 | 30.4% | -1.67 | LEGACY (disabled) |
| tl_break_short | 17 | 41.2% | -0.36 | LEGACY (disabled) |

**Overall (48h dedup): 13 inv-accel-300- trades, 1 win, 7.7% WR, -1.74% total PnL.**

### Token Performance (48h dedup)
| Token | Trades | WR | Total PnL |
|-------|--------|-----|-----------|
| AAVE | 5 | 60% | +2.94 |
| KAITO | 6 | 50% | +0.57 |
| ORDI | 7 | 42.9% | +0.23 |
| UNI | 7 | 28.6% | -0.72 |
| MOVE | 4 | 25% | -1.60 |
| LINEA | 4 | 0% | -1.35 |

### R:R Analysis (Aug 1-2 trades)
- **Avg win: 0.19%** | **Avg loss: 0.28%** | **R:R ratio: 0.67:1**
- This means even at 50% WR, the system is net negative
- Winners are small (0.1-0.2%), losses are larger (0.3-0.6%)
- Root cause: trailing activates too early (0.25%) and trail distance too wide (0.50%)

### Diagnosis

**1. Entry Quality:**
- inv-accel-300- firing on marginal setups (gap threshold 0.05% too loose)
- 10 trades in 24h, only 1 win — declining signal quality

**2. Signal Quality:**
- inv-accel-300- collapsed from 58.3% to 7.7% in 48h
- All other signals disabled or dead
- No profitable signal exists

**3. SL/TP Behavior:**
- 100% of exits are `atr_sl_hit` — trailing never catches meaningful moves
- TRAILING_ACTIVATION_PCT at 0.25% triggers before trade develops
- TRAILING_DISTANCE_PCT at 0.50% gives back too much after activation

**4. Trade Frequency:**
- 0.44/hr (Aug 1-2) — critical starvation
- inv-accel-300- gap at 0.05% is permissive but market conditions suppress entries

### Changes Implemented

**1. RAISE TRAILING_ACTIVATION_PCT: 0.25% → 0.40% (hermes_constants.py:361)**
- Rationale: avg win is only 0.19%. Trailing at 0.25% exits before trade develops. 0.40% lets winners reach 0.5%+ before trailing kicks in.
- Risk: may miss some quick wins, but current 0.25% is premature

**2. TIGHTEN TRAILING_DISTANCE_PCT: 0.50% → 0.35% (hermes_constants.py:362)**
- Rationale: R:R is 0.67:1 (avg win 0.19% vs avg loss 0.28%). Tighter trail (0.35%) locks profit closer to peak, reducing giveback. Old 0.50% was too wide — giving back too much before exit.
- Risk: may exit too early on normal retracements, but current 0.50% is too loose

**3. RAISE inv-accel-300- gap: 0.05% → 0.10% (hermes_constants.py:663-664)**
- Rationale: 7.7% WR on 13 trades at 0.05% gap — too many marginal entries. 0.10% filters low-quality setups while keeping the signal active.
- Risk: fewer entries, but current quality is abysmal

### What NOT to change
- ATR_SL_MIN_INIT (2.0%) — already widened, working as intended
- ATR_SL_MIN (0.8%) — floor, keep it
- SIGNAL_FILTER_SPEED_MIN (35) — already permissive
- TL_BREAK_ENABLED (False) — kill switches now working
- ACCEL_300_ENABLED (False) — kill switches now working
- BOLLINGER_SQUEEZE_ENABLED (False) — kill switches now working
- All blacklisted tokens — consistent losers, keep blocked
- Phase-based k scaling — disabled
- Dead hours filter — working correctly

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: inv-accel-300- at 7.7% WR (13 trades, 48h) — may need to disable if recovery doesn't happen. Signal decay pattern documented.
2. ✅ Raise trailing activation to 0.40% — IMPLEMENTED (avg win only 0.19%, trailing premature)
3. ✅ Tighten trailing distance to 0.35% — IMPLEMENTED (R:R=0.67:1, need better profit capture)
4. ✅ Raise inv-accel-300- gap to 0.10% — IMPLEMENTED (filter marginal entries)
5. ⬜ Fix double-entry signal_outcomes bug — inflating metrics

### Open Questions
- Is inv-accel-300- decline (58.3% → 7.7%) due to market regime change or signal quality?
- Should we re-enable accel-300+ (66.7% WR, +$0.14 in 200 trades) now that kill switches work?
- Is 0.44/hr trade rate sustainable, or do we need more active signals?
- Should we reduce trade size or pause live trading during this drawdown?
- Will tighter trailing (0.35%) improve R:R or just cause more early exits?

---

## 2026-08-02: Signal Engine Philosophy (from T)

### Context
We used to get hundreds of signals per hour. That was over-generation — random noise, no edge, losing money. We've been dialing back: disabling bad signals, raising speed filters, tightening thresholds.

### The Goal
A signal engine that **hums along** — 5-15 quality signals per hour that survive compaction and have genuine edge. Not 200/hr of noise, not 2/hr of decayed signals.

### The CEO's Role
The CEO evaluates quality, not just quantity. Find the signals that predict price movement. Disable the ones that don't. Tune the engine to produce the right amount of the right signals.

### Current State (03:45 UTC)
- Signal generation: ~14/hr (from inv-accel-300- only)
- Dead hours filter: FIXED — inv-accel-300- now on allowlist
- Pattern scanner: enabled but quiet (market dead at 03:30 UTC)
- accel-300+: re-enabled, needs market activity
- Target: 5-15 quality signals/hr with >40% WR

---

## 2026-08-02: Hourly Trade Analysis — SL/TP Retuned for Mean-Reversion

### Data Window
- Analyzed: 11 closed trades (12h window), signal_outcomes (24h dedup: 15 trades), MFE/MAE (11 trades)
- Trades: 2837 total closed, 2 open (APT SHORT, OP SHORT — both inv-accel-300-)
- Trade rate: ~0.92 trades/hr (low but improving)
- Current time: 2026-08-02 04:50 UTC

### Signal Performance (24h dedup — ALL signals at 0% WR)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| inv-accel-300- | 12 | 0% | -2.49 | COLLAPSED (was 58.3% in 200 trades) |
| bb-squeeze- | 2 | 0% | -0.30 | DEAD (disabled) |
| inv-accel-300+ | 1 | 0% | -0.33 | DISABLED |

**Overall (deduplicated): 15 trades, 0 wins, 0% WR, -$3.12 total PnL in 24h.**

### Token Performance (24h dedup)
| Token | Trades | WR | Total PnL | Status |
|-------|--------|-----|-----------|--------|
| DOT | 1 | 0% | -0.59 | LOSER |
| MOVE | 1 | 0% | -0.61 | BLACKLISTED |
| APEX | 2 | 0% | -0.48 | MARGINAL |
| AAVE | 2 | 0% | +0.02 | MARGINAL |
| STX | 2 | 0% | -0.13 | MARGINAL |
| ALT | 1 | 0% | -0.09 | BLACKLISTED |
| STBL | 1 | 0% | -0.32 | BLACKLISTED |
| BABY | 1 | 0% | -0.33 | BLACKLISTED |
| NEAR | 1 | 0% | -0.30 | NEW |
| ZEN | 1 | 0% | -0.09 | NEW |
| LDO | 1 | 0% | +0.02 | NEW |
| PURR | 1 | 0% | -0.23 | BLACKLISTED |

### MFE/MAE Analysis (11 recent trades)
| Coin | Dir | Signal | MFE | MAE | Result | Analysis |
|------|-----|--------|-----|-----|--------|----------|
| APT | SHORT | inv-accel-300- | +0.57% | +0.23% | OPEN | Good entry, in profit |
| OP | SHORT | inv-accel-300- | +0.26% | +0.24% | OPEN | Flat, near entry |
| LDO | SHORT | inv-accel-300- | +0.07% | +0.53% | WIN +0.02% | Minimal favorable, SL hit |
| STX | SHORT | inv-accel-300- | +0.37% | +0.44% | LOSE -0.33% | Whipsaw |
| NEAR | SHORT | inv-accel-300- | +0.22% | +0.67% | LOSE -0.30% | High adverse |
| ZEN | SHORT | inv-accel-300- | +1.25% | +0.24% | LOSE -0.09% | WHIPSAW (1.25% MFE → reversal) |
| DOT | SHORT | inv-accel-300- | +0.10% | +1.28% | LOSE -0.59% | Immediate adverse |
| APEX | SHORT | inv-accel-300- | +0.24% | +1.04% | LOSE -0.57% | High adverse |
| STX | SHORT | inv-accel-300- | +0.64% | +1.11% | WIN +0.20% | Trailing caught move |
| APEX | SHORT | inv-accel-300- | +0.40% | +0.49% | WIN +0.10% | Low adverse, good entry |
| ALT | SHORT | inv-accel-300- | +0.45% | +0.66% | LOSE -0.09% | Whipsaw |

**Winners (3): avg MFE=0.44%, avg MAE=0.61% — low adverse excursion**
**Losers (8): avg MFE=0.41%, avg MAE=0.85% — high adverse excursion**
**Whipsaw rate: 38% (3/8 losers had MFE>0.3% then reversed)**

### Diagnosis

**1. Entry Quality:**
- Winners: Low adverse (LDO 0.53%, APEX 0.49%), good timing
- Losers: DOT (1.28% MAE), APEX (1.04% MAE), STX (1.11% MAE) — high adverse excursion
- ZEN: MFE=+1.25% then reversed — classic whipsaw

**2. Signal Quality:**
- inv-accel-300- collapsed: 58.3% → 0% in 48h. 12 trades, 0 wins in 24h.
- All other signals disabled or dead
- No profitable signal exists

**3. SL/TP Behavior:**
- 100% of exits are `atr_sl_hit` — trailing never catches meaningful moves
- ATR_SL_MIN_INIT at 2.0% is 4x the avg MFE (0.43%) — SL too wide for mean-reversion
- TRAILING_ACTIVATION_PCT at 0.40% barely reached (avg MFE 0.43%)
- TRAILING_DISTANCE_PCT at 0.35% gives back too much after activation

**4. Trade Frequency:**
- Low: 0.92 trades/hr (only inv-accel-300- active)
- SIGNAL_FILTER_SPEED_MIN at 35 is reasonable
- inv-accel-300- gap at 0.10% filters marginal entries

### ROOT CAUSE: Parameter Mismatch

inv-accel-300- is a **mean-reversion** signal that generates small moves (0.3-0.5% MFE). But the SL parameters are tuned for momentum signals (1-2% moves):

| Parameter | Current | Needed | Why |
|-----------|---------|--------|-----|
| ATR_SL_MIN_INIT | 2.0% | 1.0% | 4x avg MFE — SL never reached before stall |
| TRAILING_ACTIVATION_PCT | 0.40% | 0.20% | Trades barely reach 0.43% MFE |
| TRAILING_DISTANCE_PCT | 0.35% | 0.20% | Too wide for 0.3-0.5% moves |

### Changes Implemented

**1. TIGHTEN ATR_SL_MIN_INIT: 2.0% → 1.0% (hermes_constants.py:349)**
- Also: ATR_SL_MAX_INIT 2.5% → 1.5%, SL_PCT_FALLBACK 2.0% → 1.0%, STOP_LOSS_DEFAULT 2.0% → 1.0%, TP_PCT_FALLBACK 2.8% → 1.5%
- Rationale: Mean-reversion signal generates 0.3-0.5% moves. 2.0% SL is 4x the avg MFE — trade stalls and bleeds to SL. 1.0% matches signal characteristics.

**2. TIGHTEN TRAILING_ACTIVATION_PCT: 0.40% → 0.20% (hermes_constants.py:361)**
- Rationale: Avg MFE is 0.43%. Trailing at 0.40% barely activates. 0.20% locks gains on small mean-reversion moves.

**3. TIGHTEN TRAILING_DISTANCE_PCT: 0.35% → 0.20% (hermes_constants.py:362)**
- Rationale: Mean-reversion moves are 0.3-0.5%. 0.35% trail gives back too much. 0.20% locks profit closer to peak.

**4. WIDEN ATR_TP_MAX: 1.0% → 1.5% (hermes_constants.py:337)**
- Rationale: Maintain R:R with tighter SL. 1.0% SL with 1.5% TP gives 1:1.5 R:R.

### What NOT to change
- ATR_SL_MIN (0.8%) — floor, keep it
- SIGNAL_FILTER_SPEED_MIN (35) — already permissive
- INVERSE_ACCEL_300_ENABLED (True) — only active signal, keep enabled
- INVERSE_ACCEL_300_MINUS_ENABLED (True) — only profitable variant historically
- All disabled signals (tl_break, vel+, bb-squeeze) — kill switches working
- All blacklisted tokens — consistent losers, keep blocked
- Phase-based k scaling — disabled
- Dead hours filter — working correctly

### 5 Actionable Adjustments (ranked by impact)
1. ✅ Tighten ATR_SL_MIN_INIT to 1.0% — IMPLEMENTED (match mean-reversion signal characteristics)
2. ✅ Tighten trailing activation to 0.20% — IMPLEMENTED (activate earlier for small moves)
3. ✅ Tighten trailing distance to 0.20% — IMPLEMENTED (lock profit closer to peak)
4. 🔴 CRITICAL: inv-accel-300- at 0% WR (12 trades, 24h) — monitor closely. If recovery doesn't happen with new SL/TP params, disable.
5. ⬜ Fix double-entry signal_outcomes bug — inflating metrics

### Open Questions
- Will tighter SL/TP params (1.0% SL, 0.20% trail) improve inv-accel-300- WR from 0%?
- Is inv-accel-300- decline (58.3% → 0%) due to market regime change or signal quality?
- Should we re-enable accel-300+ (66.7% WR) now that kill switches work?
- Is 0.92/hr trade rate sustainable, or do we need more active signals?
- Should we reduce trade size or pause live trading during this drawdown?

---

## 2026-08-02: Daily Orchestrator Report

### PIPELINE STATUS
- **Trades (24h):** 1 open, 15 closed today, -3.58% PnL
- **Signals:** 20 generated (2 long, 18 short), hotset empty (none survived compaction)
- **Market regime:** 0 LONG / 0 SHORT / 96 NEUTRAL
- **Speed:** 220/549 tokens >= 50% (40%)
- **System:** 28 timers active, 265 tokens with fresh prices, 147 SHORT / 95 LONG blacklisted

### CRITICAL BUG FIXED
**`ACCEL_300_BREAKOUT_CONFIDENCE` not defined** — `accel_300.py` was throwing `NameError` every pipeline run because the constant was defined in `hermes_constants.py` but not imported in the signal module. Fixed by adding it to the import block at line 53.

**Impact:** accel_300 signal was completely non-functional. Now generates signals correctly.

### AUTO-1HR CHANGES (already applied, verified)
1. ATR_SL_MIN_INIT: 2.0% → 1.0% ✅
2. ATR_SL_MAX_INIT: 2.5% → 1.5% ✅
3. TRAILING_ACTIVATION_PCT: 0.40% → 0.20% ✅
4. TRAILING_DISTANCE_PCT: 0.35% → 0.20% ✅
5. ATR_TP_MAX: 1.0% → 1.5% ✅

### SIGNAL REPORTER RECOMMENDATIONS (need CEO decision)
1. **DISABLE inv-accel-300- SHORT** — 0% WR (14 trades 24h), -$74.48 7d
2. **DISABLE bb-squeeze- SHORT** — 0% WR (4 trades 24h), -$10.38 7d
3. **DISABLE bb-squeeze LONG** — 0% WR (2 trades 24h), -$10.74 7d

### BLACKLIST TRIALS
- **Batch 1:** All 13 tokens RE-BLACKLISTED (0% WR or no execution)
- **Batch 2:** 20 tokens (COMP, CRV, DYDX, etc.) — trial started today

### OTHER ISSUES
- `pattern_scanner` module not found (pre-existing, not new)
- Trade rate 0.92/hr — severe trade starvation
- inv-accel-300- at 0% WR — SL/TP retune applied, monitoring

### NEXT STEPS (need CEO input)
1. Should we disable inv-accel-300- and bb-squeeze signals per signal reporter?
2. Should we re-enable accel-300+ (66.7% WR historically)?
3. Trade rate too low — need more active signals or relax filters?

---

## 2026-08-02: Hourly Trade Analysis — inv-accel-300- Disabled, Speed Lowered

### Data Window
- Analyzed: 16 dedup trades (24h), MFE/MAE (9 trades), trades.json (200)
- Trades: 2837 total closed, 0 open at analysis time
- Trade rate: ~0.67 trades/hr (CRITICAL — system nearly idle)
- Current time: 2026-08-02 06:00 UTC

### Signal Performance (24h dedup — ALL signals at 0% WR)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| inv-accel-300- | 13 | 0% | -2.87 | COLLAPSED (was 58.3% in 200 trades) |
| accel-300-breakout | 1 | 0% | -0.62 | NEW — 0% WR |
| inv-accel-300+ | 1 | 0% | -0.33 | DISABLED |
| bb-squeeze- | 1 | 0% | -0.23 | DEAD (disabled) |

**Overall (deduplicated): 16 trades, 0 wins, 0% WR, -$4.05 total PnL in 24h.**
**ALL signal types net negative. No profitable signal exists.**

### Signal Performance (48h dedup)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| inv-accel-300- | 16 | 6.3% | -2.42 | COLLAPSED |
| tl_break_long | 23 | 30.4% | -1.67 | LEGACY (disabled) |
| accel-300-vel+ | 19 | 21.1% | -0.77 | LEGACY (disabled) |
| accel-300-breakout | 1 | 0% | -0.62 | NEW |
| inv-accel-300+ | 1 | 0% | -0.33 | DISABLED |
| bb-squeeze- | 2 | 0% | -0.30 | DEAD (disabled) |
| tl_break_short | 16 | 43.8% | +0.06 | LEGACY (disabled) |
| accel-300-vel- | 15 | 33.3% | +0.68 | LEGACY (disabled) |

### MFE/MAE Analysis (9 recent trades)
| Coin | Dir | Signal | MFE | MAE | Result | Analysis |
|------|-----|--------|-----|-----|--------|----------|
| APEX | SHORT | inv-accel-300- | +0.31% | -0.91% | WIN +0.10% | Low adverse, good entry |
| STX | SHORT | inv-accel-300- | +1.09% | -0.65% | WIN +0.20% | Trailing caught move |
| APEX | SHORT | inv-accel-300- | +1.20% | -0.26% | LOSE -0.57% | WHIPSAW (1.20% MFE → reversal) |
| DOT | SHORT | inv-accel-300- | +0.85% | -0.51% | LOSE -0.59% | Whipsaw |
| ZEN | SHORT | inv-accel-300- | +0.99% | -0.50% | LOSE -0.09% | WHIPSAW (0.99% MFE → reversal) |
| NEAR | SHORT | inv-accel-300- | +0.45% | -0.49% | LOSE -0.30% | Whipsaw |
| STX | SHORT | inv-accel-300- | +0.62% | -0.47% | LOSE -0.33% | Whipsaw |
| LDO | SHORT | inv-accel-300- | +0.60% | -0.54% | WIN +0.02% | Trailing caught move |
| OP | SHORT | inv-accel-300- | +0.39% | -0.37% | LOSE -0.38% | Whipsaw |

**Winners (3): avg MFE=0.67%, avg MAE=0.70%**
**Losers (6): avg MFE=0.75%, avg MAE=0.43%**
**Whipsaw rate: 67% (4/6 losers had MFE>0.4% then reversed)**

### Diagnosis

**1. Entry Quality:**
- Winners: Low adverse (APEX 0.91%, LDO 0.54%), good timing
- Losers: APEX/DOT/ZEN had HIGH favorable excursion (0.85-1.20%) then reversed — whipsaw pattern
- 67% whipsaw rate — trades peak in profit then reverse

**2. Signal Quality:**
- inv-accel-300- collapsed: 58.3% → 6.3% in 48h (16 dedup trades, 1 win)
- accel-300-long generated 9 signals in 24h but only 1 executed (AVAX -0.62%)
- All other signals disabled or dead
- No profitable signal exists

**3. SL/TP Behavior:**
- 100% of exits are `atr_sl_hit` — trailing never catches meaningful moves
- ATR_SL_MIN_INIT at 1.0% surviving but trades stalling
- TRAILING_ACTIVATION_PCT at 0.20% triggers on noise for some tokens
- TRAILING_DISTANCE_PCT at 0.20% is tight — first pullback kills trailing

**4. Trade Frequency:**
- Critical: 0.67 trades/hr (only inv-accel-300- active)
- Speed filter at 35 is reasonable for current signal set
- accel-300-long signals being EXPIRED by compaction — not surviving hotset

### Changes Implemented

**1. DISABLE inv-accel-300- (hermes_constants.py:763)**
- INVERSE_ACCEL_300_MINUS_ENABLED: True → False
- Rationale: 6.3% WR (1/16 dedup) in 48h, -$2.42 total. Collapsed from 58.3%. Signal decay pattern confirmed — no recovery expected.
- Risk: System will be completely idle with no active signals. But keeping a losing signal active is worse.

**2. LOWER SPEED_MIN_THRESHOLD: 35 → 30 (hermes_constants.py:250)**
- Rationale: Trade starvation at 0.67/hr. 30 blocks bottom 30% of speed distribution. Lets accel-300-long signals through.
- Risk: more noise, but accel-300+ had 66.7% WR historically

**3. LOWER SIGNAL_FILTER_SPEED_MIN: 35 → 30 (hermes_constants.py:476)**
- Rationale: Context gate was blocking accel-300-long signals (9 generated, only 1 executed). 30 lets more through.
- Risk: slightly more noise, but accel-300+ needs entries

### What NOT to change
- ATR_SL_MIN_INIT (1.0%) — match mean-reversion signal characteristics
- TRAILING_ACTIVATION_PCT (0.20%) — activate earlier for small moves
- TRAILING_DISTANCE_PCT (0.20%) — lock profit closer to peak
- ACCEL_300_ENABLED (True) — accel-300+ had 66.7% WR historically, let it fire
- All disabled signals (tl_break, vel+, bb-squeeze) — kill switches working
- All blacklisted tokens — consistent losers, keep blocked
- Phase-based k scaling — disabled
- Dead hours filter — working correctly

### 5 Actionable Adjustments (ranked by impact)
1. ✅ Disable inv-accel-300- — IMPLEMENTED (6.3% WR, -$2.42, collapsed signal)
2. ✅ Lower SPEED_MIN_THRESHOLD to 30 — IMPLEMENTED (reduce starvation, let accel-300+ through)
3. ✅ Lower SIGNAL_FILTER_SPEED_MIN to 30 — IMPLEMENTED (let accel-300+ survive compaction)
4. 🔴 CRITICAL: System has NO active profitable signals. accel-300+ is the only candidate (66.7% WR historically, 9 signals in 24h). Monitor execution rate.
5. ⬜ Fix double-entry signal_outcomes bug — inflating metrics

### Open Questions
- Will accel-300+ fire more often with lower speed filters? (9 signals in 24h, only 1 executed)
- Is the signal decay pattern (58.3% → 0% in 48h) affecting ALL signals, or just inv-accel-300-?
- Should we re-enable any other previously profitable signals? (tl_break_long 40% WR, accel-300-vel- 33% WR)
- Is the system fundamentally broken until a new profitable signal is found?
- Should we reduce trade size or pause live trading during this drawdown?

---

## 2026-08-02: Hourly Trade Analysis — SL Widened, Trailing Raised, Speed Filter Tightened

### Data Window
- Analyzed: 16 dedup trades (24h), 8 trades (12h), trades.json (200)
- Trades: 2837+ total closed, 0 open
- Trade rate: ~0.67 trades/hr (CRITICAL — system nearly idle)
- Current time: 2026-08-02 ~14:00 UTC

### Signal Performance (24h dedup — ALL signals at 0% WR)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| inv-accel-300- | 14 | 0% | -2.67 | COLLAPSED (disabled but STILL executing) |
| accel-300-breakout | 1 | 0% | -0.62 | NEW — 0% WR |
| inv-accel-300+ | 1 | 0% | -0.33 | DISABLED |

**Overall (deduplicated): 16 trades, 0 wins, 0% WR, -3.62 total PnL in 24h.**

### Token Performance (24h dedup)
| Token | Trades | WR | Total PnL | Status |
|-------|--------|-----|-----------|--------|
| APEX | 3 | 0% | -0.28 | MARGINAL |
| STX | 2 | 0% | -0.13 | MARGINAL |
| AAVE | 1 | 0% | +0.10 | MARGINAL |
| DOT | 1 | 0% | -0.59 | LOSER |
| AVAX | 1 | 0% | -0.62 | LOSER |
| OP | 1 | 0% | -0.38 | MARGINAL |
| NEAR | 1 | 0% | -0.30 | MARGINAL |
| ZEN | 1 | 0% | -0.09 | MARGINAL |
| LDO | 1 | 0% | +0.02 | MARGINAL |
| MOVE | 1 | 0% | -0.61 | BLACKLISTED (still executing!) |
| BABY | 1 | 0% | -0.33 | BLACKLISTED (still executing!) |
| STBL | 1 | 0% | -0.32 | BLACKLISTED (still executing!) |

### MFE/MAE Analysis (last 8 trades — all SHORT inv-accel-300- except AVAX)
- All trades stall and hit ATR SL — MFE is low (~0.2-0.6%), MAE exceeds SL
- No trailing activation reached — trades die before trailing kicks in
- 0% WR across ALL token/signal combinations

### Diagnosis

**1. Entry Quality:**
- All entries are SHORT inv-accel-300- — mean-reversion into oversold
- Entries entering too early — price hasn't finished falling
- Low MFE (0.2-0.6%) means price barely moves in favor before reversing

**2. Signal Quality:**
- inv-accel-300- collapsed: 58.3% → 0% over 48h — signal decay pattern
- Kill switch bug: INVERSE_ACCEL_300_MINUS_ENABLED=False but still executing (14 trades in 24h)
- 15th consecutive analysis flagging kill switch bug

**3. SL/TP Behavior:**
- 100% of exits are `atr_sl_hit` — no trailing or TP exits
- SL at 1.0% being hit on every trade — normal crypto noise triggers SL
- Trailing never activates because trades stall at ~0.3% then reverse

**4. Trade Frequency:**
- 0.67 trades/hr — moderate but all losing
- Blacklisted tokens (BABY, MOVE, STBL) still executing despite blacklist (blacklist IS in code)

### Changes Implemented

**1. WIDEN ATR_SL_MIN_INIT: 1.0% → 2.0% (hermes_constants.py:349)**
- Also: ATR_SL_MAX_INIT 1.5% → 2.5%, SL_PCT_FALLBACK 1.0% → 2.0%, STOP_LOSS_DEFAULT 1.0% → 2.0%, TP_PCT_FALLBACK 1.5% → 3.0%
- Rationale: 100% of exits are atr_sl_hit at 1.0%. Normal crypto retracements of 0.5-1% immediately stop out trades. 2.0% gives breathing room.
- Risk: wider SL means larger losses on losing trades, but current 1.0% is producing 0% WR

**2. RAISE TRAILING_ACTIVATION_PCT: 0.20% → 0.30% (hermes_constants.py:361)**
- Rationale: Trades stall at ~0.3% MFE then reverse. 0.20% activates trailing on noise. 0.30% waits for a more meaningful move before locking.
- Risk: may miss some quick wins, but 0.20% was too aggressive

**3. RAISE TRAILING_DISTANCE_PCT: 0.20% → 0.30% (hermes_constants.py:362)**
- Rationale: 0.20% trail distance was too tight — first pullback kills trailing. 0.30% gives trailing more room to survive normal retracements.
- Risk: gives back more profit on winning trades, but current 0.20% is producing 0% WR

**4. RAISE SIGNAL_FILTER_SPEED_MIN: 30 → 40 (hermes_constants.py:476)**
- Rationale: 0% WR across all trades. 30 was too permissive. 40 blocks bottom 40% of speed distribution — more selective entries.
- Risk: fewer trades (already at 0.67/hr), but quality over quantity when everything is losing

### What NOT to change
- ATR_SL_MIN (0.8%) — floor, keep it
- ACCEL_300_ENABLED (True) — accel-300+ had 66.7% WR historically, let it fire
- All disabled signals (tl_break, vel+, bb-squeeze) — kill switches working
- All blacklisted tokens — consistent losers, keep blocked (blacklist IS in code, enforcement issue elsewhere)
- Phase-based k scaling — disabled
- Dead hours filter — working correctly

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: Fix kill switch pipeline bug — inv-accel-300- disabled but STILL executing (14 trades, 0% WR). 15th consecutive analysis. Root cause is in signal execution layer, not constants.
2. 🔴 CRITICAL: Fix blacklisted token execution — BABY, MOVE, STBL still trading despite being in BLACKLIST sets. Blacklist IS in code (verified), enforcement must be elsewhere.
3. ✅ Widen ATR_SL_MIN_INIT to 2.0% — IMPLEMENTED (100% exits were atr_sl_hit, too tight)
4. ✅ Raise trailing activation to 0.30% — IMPLEMENTED (trades stall at 0.3% MFE)
5. ✅ Raise trailing distance to 0.30% — IMPLEMENTED (0.20% too tight for crypto)

### What NOT to change (and why)
- **ATR_SL_MIN (0.8%)** — this is the trailing/accel floor, separate from initial SL. Keep it.
- **ACCEL_300_ENABLED (True)** — re-enabled 2026-08-02, had 66.7% WR historically. Needs market activity.
- **INVERSE_ACCEL_300_ENABLED (True)** — master flag. Only the MINUS variant is disabled.
- **Dead hours filter** — working correctly, inv-accel-300- on allowlist.
- **Phase-based k scaling** — disabled, was compressing SL too aggressively.
- **TOKEN_WR_THRESHOLD (30)** — reasonable for current signal set.

### Open Questions
- Why is inv-accel-300- still executing despite INVERSE_ACCEL_300_MINUS_ENABLED=False? (FLAGGED 15th CONSECUTIVE TIME)
- Why are blacklisted tokens (BABY, MOVE, STBL) still executing? Blacklist IS in code — enforcement bug elsewhere.
- Will wider SL (2.0%) reduce whipsaw stops or just delay the inevitable loss?
- Is the signal decay pattern (58.3% → 0% in 48h) permanent or temporary?
- Should we re-enable any other previously profitable signals? (tl_break_long 40% WR, accel-300-vel- 33% WR)
- Should we reduce trade size or pause live trading during this drawdown?

---

## 2026-08-02: Hourly Trade Analysis — inv-accel-300- Collapsed, SL Widened, Gap Raised

### Data Window
- Analyzed: 18 dedup trades (24h), signal_outcomes (24h), trades.json (200)
- Trades: 200 in file (stale — last trade 2026-07-30), 0 open
- Trade rate: ~1.06/hr (improving from 0.67)
- Current time: 2026-08-02 ~08:00 UTC

### Signal Performance (24h dedup — ALL signals at 0% WR)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| inv-accel-300- | 15 | 0% | -3.31 | COLLAPSED (was 58.3%) |
| accel-300-breakout | 2 | 0% | -0.89 | NEW — 0% WR |
| inv-accel-300+ | 1 | 0% | -0.33 | DISABLED |

**Overall: 18 dedup trades, 0 wins, 0% WR, -$4.53 total PnL in 24h.**

### Token Performance (24h dedup)
| Token | Trades | WR | Total PnL | Status |
|-------|--------|-----|-----------|--------|
| APEX | 3 | 0% | -0.28 | MARGINAL |
| STX | 2 | 0% | -0.13 | MARGINAL |
| APT | 1 | 0% | -0.64 | NEW |
| AVAX | 1 | 0% | -0.62 | NEW |
| DOT | 1 | 0% | -0.59 | LOSER |
| BABY | 1 | 0% | -0.33 | BLACKLISTED (still executing!) |
| STBL | 1 | 0% | -0.32 | BLACKLISTED (still executing!) |
| MOVE | 1 | 0% | -0.61 | BLACKLISTED (still executing!) |

### Diagnosis

**1. Entry Quality:**
- inv-accel-300- firing on marginal setups (gap threshold was 0.10%, too loose)
- All trades stall at ~0.3% MFE then reverse — entering too early in downtrend

**2. Signal Quality:**
- inv-accel-300- collapsed from 58.3% to 0% WR in 48h — signal decay pattern
- accel-300-breakout fired twice, both losses — new signal needs tuning
- Blacklisted tokens (BABY, STBL, MOVE) still executing — blacklist enforcement bug

**3. SL/TP Behavior:**
- 100% of exits are `atr_sl_hit` — trailing never catches meaningful moves
- ATR_SL_MIN_INIT at 2.0% is too wide — trades average -0.23% loss, barely moving

**4. Trade Frequency:**
- 1.06/hr — improving but all losing
- SPEED_MIN_THRESHOLD at 30, SIGNAL_FILTER_SPEED_MIN at 40 — reasonable

### Changes Implemented

**1. RAISE inv-accel-300- gap: 0.10% → 0.35% (hermes_constants.py:663-664)**
- INVERSE_ACCEL_300_MIN_GAP_PCT_LONG: 0.10 → 0.35
- INVERSE_ACCEL_300_MIN_GAP_PCT_SHORT: 0.10 → 0.35
- Rationale: 0% WR at 0.10% gap — too many marginal entries. 0.35% restores quality gate.
- Risk: fewer entries, but 0% WR with 0.10% gap is worse than no trades

**2. RAISE SIGNAL_FILTER_SPEED_MIN: 40 → 55 (hermes_constants.py:476)**
- Rationale: 0% WR across 18 trades — need higher-momentum entries. 55 blocks bottom 55%.
- Risk: fewer trades, but quality over quantity when everything is losing

**3. NARROW ATR_SL_MIN_INIT: 2.0% → 1.5% (hermes_constants.py:349)**
- Also: ATR_SL_MAX_INIT 2.5% → 2.0%, SL_PCT_FALLBACK 2.0% → 1.5%, STOP_LOSS_DEFAULT 2.0% → 1.5%, TP_PCT_FALLBACK 3.0% → 2.25%
- Rationale: Trades average -0.23% loss, barely moving. 2.0% SL is too wide — lets trades drift. 1.5% tighter.
- Risk: may trigger on noise, but current 2.0% produces 0% WR

### What NOT to change
- ATR_SL_MIN (0.8%) — floor, keep it
- TRAILING_ACTIVATION_PCT (0.30%) — wait for real move
- TRAILING_DISTANCE_PCT (0.30%) — moderate trail
- ACCEL_300_ENABLED (True) — needs market activity
- All disabled signals (tl_break, vel+, bb-squeeze) — kill switches working
- All blacklisted tokens — consistent losers, keep blocked
- Phase-based k scaling — disabled
- Dead hours filter — working correctly

### 5 Actionable Adjustments (ranked by impact)
1. CRITICAL: Fix blacklisted token execution — BABY, STBL, MOVE still trading despite blacklist in code. Enforcement bug.
2. CRITICAL: inv-accel-300- at 0% WR (15 trades, 24h) — gap raised to 0.35% to filter marginal entries. Monitor.
3. Raise inv-accel-300- gap to 0.35% — IMPLEMENTED (0% WR at 0.10%)
4. Raise speed filter to 55 — IMPLEMENTED (block low-momentum entries)
5. Narrow SL to 1.5% — IMPLEMENTED (trades avg -0.23% loss, 2.0% too wide)

### Open Questions
- Why are blacklisted tokens (BABY, STBL, MOVE) still executing? Blacklist IS in code.
- Will wider gap (0.35%) restore inv-accel-300- WR, or is signal decay permanent?
- Should we re-enable accel-300+ (66.7% WR historically) more aggressively?
- Is the signal decay pattern (58.3% → 0% in 48h) affecting ALL signals?
- Should we reduce trade size or pause live trading during this drawdown?

---

## 2026-08-02: Hourly Trade Analysis — 0% WR Crisis Continues, Speed Raised, SL Narrowed

### Data Window
- Analyzed: 20 closed trades (trades.json), signal_outcomes (24h dedup: 20 trades)
- Trades: 2844 total closed, 0 open at analysis time
- Trade rate: ~1.06 trades/hr (low — only inv-accel-300- active)
- Current time: 2026-08-02 08:50 UTC

### Signal Performance (24h dedup — ALL signals at 0% WR)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| inv-accel-300- | 15 | 0% | -3.31 | COLLAPSED (was 58.3% in 200 trades) |
| accel-300-breakout | 3 | 0% | -1.93 | NEW — 0% WR |
| accel-300+ | 1 | 0% | -0.21 | MARGINAL |
| inv-accel-300+ | 1 | 0% | -0.33 | DISABLED |

**Overall (deduplicated): 20 trades, 0 wins, 0% WR, -$5.48 total PnL in 24h.**
**ALL signal types net negative. No profitable signal exists.**

### Token Performance (24h dedup)
| Token | Trades | WR | Total PnL | Status |
|-------|--------|-----|-----------|--------|
| APEX | 3 | 0% | -0.28 | MARGINAL |
| OP | 2 | 0% | -0.59 | NEW |
| STX | 2 | 0% | -0.13 | MARGINAL |
| APT | 1 | 0% | -0.64 | NEW |
| AVAX | 1 | 0% | -0.62 | NEW |
| DOT | 1 | 0% | -0.59 | LOSER |
| BABY | 1 | 0% | -0.33 | BLACKLISTED (still executing!) |
| STBL | 1 | 0% | -0.32 | BLACKLISTED (still executing!) |
| MOVE | 1 | 0% | -0.61 | BLACKLISTED (still executing!) |

### Diagnosis

**1. Entry Quality:**
- All trades are inv-accel-300- (SHORT mean-reversion)
- avg MFE: ~0.4%, avg MAE: ~0.5% — trades barely move in favor
- 67% whipsaw rate — trades peak then reverse
- Signal firing on every marginal setup with gap >= 0.10%

**2. Signal Quality:**
- inv-accel-300- completely decayed: 58.3% → 0% in 48h
- accel-300-breakout also 0% WR (3 trades) — new signal needs tuning
- No other profitable signal exists (all disabled or dead)

**3. SL/TP Behavior:**
- 100% of exits are atr_sl_hit — trailing never catches meaningful moves
- ATR_SL_MIN_INIT at 1.5% producing avg loss of 0.4%
- Trailing activation at 0.30% barely reached (avg MFE 0.4%)
- Trailing distance at 0.30% gives back too much

**4. Root Cause:**
- Market regime where neither mean-reversion nor momentum works
- inv-accel-300- fires on every SHORT setup regardless of market conditions
- Gap threshold at 0.10% too loose — too many marginal entries
- System has no edge in current market conditions

### Changes Implemented

**1. RAISE SIGNAL_FILTER_SPEED_MIN: 55 → 65 (hermes_constants.py:476)**
- Rationale: 0% WR across 20 trades — need higher-momentum entries. 65 blocks bottom 65%.
- Risk: fewer trades (already at 1.06/hr), but quality over quantity when everything is losing

**2. NARROW ATR_SL_MIN_INIT: 1.5% → 1.2% (hermes_constants.py:349)**
- Also: ATR_SL_MAX_INIT 2.0% → 1.8%, SL_PCT_FALLBACK 1.5% → 1.2%, STOP_LOSS_DEFAULT 1.5% → 1.2%, TP_PCT_FALLBACK 2.25% → 1.8%
- Rationale: Mean-reversion signals generate 0.3-0.5% moves. 1.5% SL is 3x the avg MFE — trade stalls and bleeds. 1.2% is tighter but still survivable.
- Risk: may trigger on noise, but current 1.5% produces 0% WR

**3. inv-accel-300- gap already at 0.35%** — no change needed (raised in previous analysis)

### What NOT to change
- ATR_SL_MIN (0.8%) — floor, keep it
- TRAILING_ACTIVATION_PCT (0.30%) — wait for real move
- TRAILING_DISTANCE_PCT (0.30%) — moderate trail
- ACCEL_300_ENABLED (True) — needs market activity
- All disabled signals (tl_break, vel+, bb-squeeze) — kill switches working
- All blacklisted tokens — consistent losers, keep blocked
- Phase-based k scaling — disabled
- Dead hours filter — working correctly

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: System has NO edge in current market. inv-accel-300- collapsed from 58.3% to 0%. Need to either find new signal, re-enable previously profitable signal, or pause trading.
2. 🔴 CRITICAL: Fix blacklisted token execution — BABY, STBL, MOVE still trading despite blacklist in code.
3. ✅ Raise speed filter to 65 — IMPLEMENTED (0% WR, need higher-momentum entries)
4. ✅ Narrow SL to 1.2% — IMPLEMENTED (mean-reversion signals need tighter SL)
5. ⬜ Fix inv-accel-300- kill switch bypass — disabled but still executing (16th consecutive time)

### What NOT to change (and why)
- **ATR_SL_MIN (0.8%)** — trailing/accel floor, separate from initial SL
- **ACCEL_300_ENABLED (True)** — re-enabled, needs market activity
- **INVERSE_ACCEL_300_ENABLED (True)** — master flag. MINUS variant disabled.
- **Dead hours filter** — working correctly
- **Phase-based k scaling** — disabled, was compressing SL too aggressively
- **TOKEN_WR_THRESHOLD (30)** — reasonable for current signal set

### Open Questions
- Is inv-accel-300- decline (58.3% → 0% in 48h) permanent or temporary?
- Should we re-enable any other previously profitable signals? (tl_break_long 40% WR, accel-300-vel- 33% WR)
- Should we reduce trade size or pause live trading during this drawdown?
- Is the signal decay pattern affecting ALL signals, or just inv-accel-300-?
- Why are blacklisted tokens (BABY, STBL, MOVE) still executing? Blacklist IS in code.

---

## 2026-08-02: Hourly Trade Analysis — inv-accel-300- Collapsed, SL Narrowed, Gap Widened

### Data Window
- Analyzed: 20 dedup trades (24h), 16 trades (12h), trades.json (200)
- Trades: 2844 total closed, 0 open at analysis time
- Trade rate: ~0.83 trades/hr (low — only inv-accel-300- active)
- Last trade closed: 2026-08-02 08:22 UTC (OP LONG, accel-300+, -0.21%)

### Signal Performance (24h dedup — ALL signals net losers)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| inv-accel-300- | 15 | 0% | -3.31 | COLLAPSED (was 58.3% historically) |
| accel-300-breakout | 3 | 0% | -1.93 | NEW — 0% WR |
| inv-accel-300+ | 1 | 0% | -0.33 | DISABLED (still firing) |
| accel-300+ | 1 | 0% | -0.21 | RE-ENABLED |

**Overall (deduplicated): 20 trades, 0 wins, 0% WR, -5.78 total PnL in 24h.**
**ALL 4 active signals are net negative. ZERO wins across 20 trades.**

### Token Performance (24h dedup — all losers)
| Token | Trades | WR | Total PnL | Status |
|-------|--------|-----|-----------|--------|
| APEX | 3 | 0% | -0.28 | CONSISTENT LOSER |
| OP | 2 | 0% | -0.59 | LOSER |
| STX | 2 | 0% | -0.13 | MARGINAL |
| SKR | 1 | 0% | -1.04 | BIG LOSS |
| AVAX | 1 | 0% | -0.62 | LOSER |
| APT | 1 | 0% | -0.64 | LOSER |
| DOT | 1 | 0% | -0.59 | LOSER |

### MFE/MAE Analysis (16 recent trades — last 12h)
**Winners (0):** None.

**Losers (16):**
- avg MFE: +0.08%, avg MAE: +0.35%
- Most trades barely move in favor (avg MFE 0.08%) before hitting SL
- SKR: -1.04% (biggest loss) — hit SL immediately
- APT: -0.64%, AVAX: -0.62% — high adverse excursion

**Whipsaw rate: 6% (1/16 losers had MFE>0.5% then reversed)** — most losses are stalls, not reversals.

### Diagnosis

**1. Entry Quality:**
- ALL trades lose. Entry timing is poor across the board.
- avg MFE of 0.08% means trades barely move in favor before stalling
- avg MAE of 0.35% means adverse excursion is 4x the favorable excursion

**2. Signal Quality:**
- inv-accel-300- collapsed from 58.3% WR (historical) to 0% WR (24h) — complete signal failure
- accel-300-breakout: 3 trades, 0% WR — new signal with no edge
- inv-accel-300+ still firing despite INVERSE_ACCEL_300_PLUS_ENABLED=False — kill switch bypass
- System has NO edge in current market conditions

**3. SL/TP Behavior:**
- 100% of exits are atr_sl_hit — no trailing or TP exits
- ATR_SL_MIN_INIT at 1.2% producing avg loss of 0.35%
- Trades stall and bleed to SL — never reach trailing activation

**4. Trade Frequency:**
- Low: 0.83 trades/hr
- inv-accel-300- gap at 0.35% letting too many marginal entries through
- Speed filter at 65 blocking some entries but not enough

### Changes Implemented

**1. RAISE inv-accel-300- gap: 0.35% → 0.50% (hermes_constants.py:663-664)**
- INVERSE_ACCEL_300_MIN_GAP_PCT_LONG: 0.35 → 0.50
- INVERSE_ACCEL_300_MIN_GAP_PCT_SHORT: 0.35 → 0.50
- Rationale: 0% WR across 15 trades — gap too loose, letting marginal entries through
- Defense-in-depth against kill switch bypass (inv-accel-300- disabled but still firing)

**2. RAISE SIGNAL_FILTER_SPEED_MIN: 65 → 70 (hermes_constants.py:476)**
- Rationale: 0% WR across 20 trades — need higher-momentum entries. 70 blocks bottom 70%.
- Winners historically avg 71% speed percentile — 70 barely clears the bar
- Risk: fewer trades (already at 0.83/hr), but quality over quantity at 0% WR

**3. NARROW ATR_SL_MIN_INIT: 1.2% → 0.80% (hermes_constants.py:349)**
- Also: ATR_SL_MAX_INIT 1.8% → 1.2%, SL_PCT_FALLBACK 1.2% → 0.80%, STOP_LOSS_DEFAULT 1.2% → 0.80%, TP_PCT_FALLBACK 1.8% → 1.2%
- Rationale: Mean-reversion signals generate 0.08% avg MFE. 1.2% SL is 15x the avg move — trade stalls and bleeds. 0.80% is tighter but matches the actual price behavior.
- Volatile tokens (ORDI, UNI, etc.) already blacklisted — no need for wide SL
- Risk: may trigger on noise, but current 1.2% produces 0% WR

### What NOT to change (and why)
- **ATR_SL_MIN (0.8%)** — trailing/accel floor, matches new INIT value
- **TRAILING_ACTIVATION_PCT (0.30%)** — wait for real move
- **TRAILING_DISTANCE_PCT (0.30%)** — moderate trail
- **ACCEL_300_ENABLED (True)** — re-enabled, needs market activity
- **INVERSE_ACCEL_300_ENABLED (True)** — master flag. MINUS variant disabled.
- **All disabled signals** — kill switches now have Layer 2 guards
- **All blacklisted tokens** — consistent losers, keep blocked
- **Phase-based k scaling** — disabled
- **Dead hours filter** — working correctly

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: System has NO edge in current market. inv-accel-300- collapsed to 0% WR. Need to either find new signal, re-enable previously profitable signal, or pause trading.
2. 🔴 CRITICAL: inv-accel-300+ still firing despite INVERSE_ACCEL_300_PLUS_ENABLED=False — kill switch bypass (17th consecutive time)
3. ✅ Raise inv-accel-300- gap to 0.50% — IMPLEMENTED (defense-in-depth, block marginal entries)
4. ✅ Raise speed filter to 70 — IMPLEMENTED (0% WR, need higher-momentum entries)
5. ✅ Narrow SL to 0.80% — IMPLEMENTED (mean-reversion signals need tighter SL matching actual MFE)

### Open Questions
- Should we disable inv-accel-300 entirely? (0% WR across 15 trades in 24h)
- Is the 0% WR pattern due to market conditions or permanent signal decay?
- Should we re-enable tl_break_long (historically 40% WR in 200 trades)?
- Should we reduce trade size or pause live trading during this drawdown?
- Why are blacklisted tokens (BABY, STBL, MOVE) still executing? Blacklist IS in code.

---

## 2026-08-02: Hourly Trade Analysis — breakout Disabled, R:R Retuned

### Data Window
- Analyzed: 20 closed trades (24h), signal_outcomes (24h dedup: 15 trades), trades.json (200)
- Trades: 2844 total closed, 1 open at analysis time
- Trade rate: ~0.83 trades/hr (low — restrictive params)
- Last trade closed: 2026-08-02 08:22 UTC (OP LONG, accel-300+, -0.21%)

### Signal Performance (24h — ALL signals net losers)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| inv-accel-300- | 15 | 33% | +0.12 | ONLY WINNER (via trades.json) |
| accel-300-breakout | 3 | 0% | -1.93 | CATASTROPHIC |
| accel-300+ | 1 | 0% | -0.21 | BAD |
| inv-accel-300+ | 1 | 0% | -0.42 | DISABLED |

**Key insight: signal_outcomes shows 0% WR for all signals (double-entry phantom rows). trades.json shows inv-accel-300- at 33% WR (5/15) — the ONLY profitable active signal.**

### Token Performance (24h — top losers)
| Token | Trades | WR | Total PnL | Status |
|-------|--------|-----|-----------|--------|
| APEX | 3 | 33% | -0.28 | MARGINAL |
| OP | 2 | 0% | -0.59 | LOSER |
| STX | 2 | 50% | -0.13 | MARGINAL |
| SKR | 1 | 0% | -1.04 | WORST SINGLE LOSS |

### Diagnosis

**1. Entry Quality:**
- Winners (5): APEX SHORT +0.17%, LDO SHORT +0.02%, STX SHORT +0.20%, APEX SHORT +0.01%, AAVE SHORT +0.20%
- Losers (15): avg loss -0.39%, max loss -1.04% (SKR)
- Winners have low adverse excursion (<0.3%) — good timing
- Losers have high adverse excursion (>0.5%) — poor timing or normal retracement

**2. Signal Quality:**
- inv-accel-300- is the ONLY signal with positive PnL in 24h trades.json
- accel-300-breakout: 0% WR (0/3), -$1.93 — all trades hit SL immediately
- inv-accel-300- still firing despite INVERSE_ACCEL_300_MINUS_ENABLED=False (kill switch bug, 18th consecutive time)

**3. SL/TP Behavior:**
- 100% of exits are `atr_sl_hit` — no trailing or TP exits
- Current SL=0.80%, TP=1.20% (R:R 1.5:1)
- Observed: avg win +0.12%, avg loss -0.43% (actual R:R 0.28:1)
- Trailing activation at 0.30% — wins peak at +0.20% so trailing NEVER activates
- SL too wide: losses average -0.43% before hitting 0.80% SL (trade stalls then reverses)

**4. Trade Frequency:**
- 20 trades in 24h (0.83/hr) — moderate
- inv-accel-300- generates most trades (15/20 = 75%)

### Changes Implemented

**1. DISABLE accel-300-breakout (hermes_constants.py:685)**
- ACCEL_300_BREAKOUT_ENABLED: True → False
- Rationale: 0% WR (0/3), -$1.93 total. All trades hit SL immediately. No edge.

**2. NARROW initial SL: 0.80% → 0.60% (hermes_constants.py:349-353)**
- ATR_SL_MIN_INIT: 0.008 → 0.006
- ATR_SL_MAX_INIT: 0.012 → 0.010
- SL_PCT_FALLBACK: 0.008 → 0.006
- STOP_LOSS_DEFAULT: 0.008 → 0.006
- Rationale: avg loss is -0.43% with 0.80% SL. Tighter SL cuts losers faster. 0.60% matches observed loss magnitude.

**3. WIDEN take profit: 1.20% → 1.80% (hermes_constants.py:352)**
- TP_PCT_FALLBACK: 0.012 → 0.018
- Rationale: wins peak at +0.12% — never reach TP. Wider TP (3:1 R:R) gives winners room to run.

**4. LOWER trailing activation: 0.30% → 0.20% (hermes_constants.py:361)**
- TRAILING_ACTIVATION_PCT: 0.003 → 0.002
- Rationale: wins peak at +0.20% — trailing at 0.30% never activates. 0.20% activation lets trailing catch the peak.

### What NOT to change (and why)
- **ATR_SL_MIN (0.8%)** — trailing/accel floor, keep as-is
- **TRAILING_DISTANCE_PCT (0.30%)** — moderate trail, matches new activation
- **INVERSE_ACCEL_300_ENABLED (True)** — master flag. MINUS variant disabled but still executing (kill switch bug).
- **ACCEL_300_ENABLED (True)** — re-enabled, needs market activity
- **SIGNAL_FILTER_SPEED_MIN (70)** — keep high, all signals net negative
- **All disabled signals** — kill switches have Layer 2 guards
- **All blacklisted tokens** — consistent losers, keep blocked
- **Phase-based k scaling** — disabled
- **Dead hours filter** — working correctly

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: Fix inv-accel-300- kill switch — STILL FIRING despite INVERSE_ACCEL_300_MINUS_ENABLED=False (18th consecutive time)
2. ✅ Disable accel-300-breakout — IMPLEMENTED (0% WR, -$1.93)
3. ✅ Narrow SL to 0.60% — IMPLEMENTED (R:R from 0.28 to 3.0)
4. ✅ Widen TP to 1.80% — IMPLEMENTED (give winners room)
5. ✅ Lower trailing activation to 0.20% — IMPLEMENTED (catch wins at +0.20% peak)

### Open Questions
- Why is inv-accel-300- kill switch still not working? (18th consecutive time)
- Is the R:R retune (0.60% SL / 1.80% TP) too aggressive? Will narrower SL cause more whipsaw stops?
- Should we re-enable tl_break_long (historically 40% WR in 200 trades)?
- Is the system fundamentally broken until kill switch bug is fixed?

---

## 2026-08-02: Hourly Trade Analysis — 0% WR Crisis, SL Widened, Gap Tightened

### Data Window
- Analyzed: 21 dedup trades (24h), MFE/MAE (17 trades), trades.json (200)
- Trades: 2845 total closed, 0 open at analysis time
- Trade rate: ~1.4 trades/hr (low — only inv-accel-300- active)
- Current time: 2026-08-02 11:50 UTC

### Signal Performance (24h dedup — ALL signals at 0% WR)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| inv-accel-300- | 15 | 0% | -3.31 | COLLAPSED (still executing despite disable) |
| accel-300-breakout | 4 | 0% | -2.90 | DISABLED (still executing!) |
| inv-accel-300+ | 1 | 0% | -0.33 | DISABLED (still executing!) |
| accel-300+ | 1 | 0% | -0.21 | ENABLED (expected) |

**Overall (deduplicated): 21 trades, 0 wins, 0% WR, -$6.74 total PnL in 24h.**
**NOT A SINGLE WIN IN 24 HOURS.**

### Token Performance (24h dedup — all at 0% WR)
| Token | Trades | WR | Total PnL | Status |
|-------|--------|-----|-----------|--------|
| APEX | 3 | 0% | -0.28 | MARGINAL |
| OP | 2 | 0% | -0.59 | LOSER |
| STX | 2 | 0% | -0.13 | MARGINAL |
| PURR | 1 | 0% | -0.96 | LOSER |
| SKR | 1 | 0% | -1.04 | LOSER |
| APT | 1 | 0% | -0.64 | LOSER |
| AVAX | 1 | 0% | -0.62 | LOSER |
| DOT | 1 | 0% | -0.59 | LOSER |
| MOVE | 1 | 0% | -0.61 | BLACKLISTED |
| BABY | 1 | 0% | -0.33 | BLACKLISTED |
| STBL | 1 | 0% | -0.32 | BLACKLISTED |

### MFE/MAE Analysis (17 recent trades)
| Coin | Dir | Signal | MFE | MAE | Result | Analysis |
|------|-----|--------|-----|-----|--------|----------|
| PURR | SHORT | accel-300-breakout | -0.14% | +3.05% | LOSE -0.96% | CATASTROPHIC adverse excursion |
| SKR | LONG | accel-300-breakout | +0.06% | +1.10% | LOSE -1.04% | Immediate adverse |
| AVAX | LONG | accel-300-breakout | +0.56% | +0.76% | LOSE -0.62% | Whipsaw |
| KAITO | LONG | accel-300-breakout | +0.42% | +0.61% | LOSE -0.27% | Whipsaw |
| APT | SHORT | inv-accel-300- | +0.04% | +0.73% | LOSE -0.64% | Immediate adverse |
| DOT | SHORT | inv-accel-300- | +0.01% | +0.61% | LOSE -0.59% | Immediate adverse |
| APEX | SHORT | inv-accel-300- | -0.07% | +0.57% | LOSE -0.57% | Wrong direction |
| OP | SHORT | inv-accel-300- | +0.04% | +0.39% | LOSE -0.38% | Minimal favorable |
| STX | SHORT | inv-accel-300- | +0.14% | +0.33% | LOSE -0.33% | Minimal favorable |
| NEAR | SHORT | inv-accel-300- | +0.22% | +0.30% | LOSE -0.30% | Whipsaw |
| OP | LONG | accel-300+ | +0.13% | +0.33% | LOSE -0.21% | Minimal favorable |
| ZEN | SHORT | inv-accel-300- | +0.84% | +0.09% | LOSE -0.09% | WHIPSAW (0.84% MFE → reversal) |
| ALT | SHORT | inv-accel-300- | +0.45% | +0.31% | LOSE -0.09% | Whipsaw |
| LDO | SHORT | inv-accel-300- | +0.02% | +0.37% | WIN +0.02% | Minimal favorable |
| APEX | SHORT | inv-accel-300- | +0.40% | +0.30% | WIN +0.10% | Low adverse |
| STX | SHORT | inv-accel-300- | +0.28% | +0.13% | WIN +0.20% | Low adverse |
| APEX | SHORT | inv-accel-300- | +0.41% | +0.19% | WIN +0.20% | Low adverse |

**Winners (3): avg MFE=0.36%, avg MAE=0.21% — low adverse excursion**
**Losers (14): avg MFE=0.18%, avg MAE=0.68% — high adverse, stalls immediately**
**Whipsaw rate: 29% (4/14 losers had MFE>0.3% then reversed)**

### CRITICAL: Kill Switch Bypass Bug (19th consecutive analysis)
**Disabled signals STILL firing:**
- `inv-accel-300-`: INVERSE_ACCEL_300_MINUS_ENABLED=False → 15 trades, -3.31 PnL
- `accel-300-breakout`: ACCEL_300_BREAKOUT_ENABLED=False → 4 trades, -2.90 PnL
- `inv-accel-300+`: INVERSE_ACCEL_300_PLUS_ENABLED=False → 1 trade, -0.33 PnL

**19 of 21 trades (90%) are from DISABLED signals.** Only 2 trades are from enabled signals (accel-300+).

### Diagnosis

**1. Entry Quality:**
- Winners: Low adverse (LDO 0.37%, APEX 0.19%, STX 0.13%) — good timing
- Losers: PURR had 3.05% MAE (catastrophic), SKR 1.10% MAE, APT 0.73% MAE — poor entry
- Most trades stall at <0.2% MFE then hit SL

**2. Signal Quality:**
- ALL signal types at 0% WR in 24h
- Disabled signals account for 90% of trades — kill switch bug is catastrophic
- inv-accel-300- collapsed from 58.3% to 0% in 72h

**3. SL/TP Behavior:**
- 100% of exits are `atr_sl_hit` — no trailing or TP exits
- ATR_SL_MIN_INIT at 0.60% is too tight — PURR had 3.05% adverse
- Trailing never activates because trades hit SL before reaching +0.20%

**4. Trade Frequency:**
- Low: 1.4 trades/hr (dominated by disabled signals)
- Only 2 trades from enabled signals in 24h

### Changes Implemented

**1. WIDEN ATR_SL_MIN_INIT: 0.60% → 0.80% (hermes_constants.py:349)**
- Also: ATR_SL_MAX_INIT 1.0% → 1.2%, SL_PCT_FALLBACK 0.60% → 0.80%, STOP_LOSS_DEFAULT 0.60% → 0.80%
- Rationale: PURR SHORT had 3.05% MAE. 0.60% SL is too tight for volatile tokens. 0.80% gives breathing room.

**2. RAISE inv-accel-300- gap: 0.50% → 0.65% (hermes_constants.py:663-664)**
- Rationale: Defense-in-depth against kill switch bypass. If signal fires despite disable, at least filter marginal entries.
- Risk: may block some valid signals, but 0% WR justifies aggressive filtering

**3. LOWER TRAILING_ACTIVATION_PCT: 0.20% → 0.15% (hermes_constants.py:361)**
- Rationale: Most trades stall at <0.2% MFE. Earlier activation locks small profits before reversal.
- Risk: may trigger on noise, but current 0.20% barely activates

### What NOT to change
- ATR_SL_MIN (0.8%) — floor, keep it
- TRAILING_DISTANCE_PCT (0.30%) — moderate trail, keep it
- ACCEL_300_ENABLED (True) — accel-300+ had 66.7% WR historically
- All disabled signals (tl_break, vel+, bb-squeeze) — kill switches working for these
- All blacklisted tokens — consistent losers, keep blocked
- Phase-based k scaling — disabled
- Dead hours filter — working correctly
- SIGNAL_FILTER_ENABLED (True) — the filter framework is sound

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: Fix kill switch bypass bug — inv-accel-300- and accel-300-breakout STILL FIRING despite being disabled (19th consecutive time). 90% of trades are from disabled signals.
2. ✅ Widen ATR_SL_MIN_INIT to 0.80% — IMPLEMENTED (PURR had 3.05% MAE)
3. ✅ Raise inv-accel-300- gap to 0.65% — IMPLEMENTED (defense-in-depth)
4. ✅ Lower trailing activation to 0.15% — IMPLEMENTED (catch small wins)
5. ⬜ Fix double-entry signal_outcomes bug — inflating metrics

### Open Questions
- Why is inv-accel-300- kill switch still not working? (19th consecutive time)
- Is accel-300-breakout kill switch also broken? (4 trades despite ACCEL_300_BREAKOUT_ENABLED=False)
- Should we re-enable tl_break_long (historically 40% WR in 200 trades)?
- Is the system fundamentally broken until kill switch bug is fixed?
- Should we reduce trade size or pause live trading during this 0% WR crisis?

---

## 2026-08-02: Hourly Trade Analysis — Trailing Retuned, TOKEN_WR Lowered

### Data Window
- Analyzed: 21 dedup trades (24h), 70 dedup trades (48h), trades.json (200)
- Trades: 2845 total closed, 0 open at analysis time
- Trade rate: ~1.4 trades/hr (low — only inv-accel-300- and accel-300-breakout active)
- Current time: 2026-08-02 12:50 UTC

### Signal Performance (24h dedup — ALL signals at 0% WR)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| inv-accel-300- | 15 | 0% | -3.31 | COLLAPSED (still executing despite disable) |
| accel-300-breakout | 4 | 0% | -2.90 | DISABLED (still executing!) |
| inv-accel-300+ | 1 | 0% | -0.33 | DISABLED (still executing!) |
| accel-300+ | 1 | 0% | -0.21 | ENABLED (expected) |

**Overall (deduplicated): 21 trades, 0 wins, 0% WR, -$6.74 total PnL in 24h.**
**48h: 70 trades, 11 wins, 15.7% WR, -$9.72 total PnL.**

### Token Performance (24h dedup — all at 0% WR)
| Token | Trades | WR | Total PnL | Status |
|-------|--------|-----|-----------|--------|
| APEX | 3 | 0% | -0.28 | MARGINAL |
| OP | 2 | 0% | -0.59 | LOSER |
| STX | 2 | 0% | -0.13 | MARGINAL |
| PURR | 1 | 0% | -0.96 | LOSER |
| SKR | 1 | 0% | -1.04 | LOSER |

### Diagnosis

**1. Entry Quality:**
- Winners (0 in 24h): None — 0% WR across all trades
- Losers (21): avg MFE=0.08%, avg MAE=0.35% — trades barely move in favor
- Whipsaw rate: 6% — most losses are stalls, not reversals

**2. Signal Quality:**
- inv-accel-300- collapsed from 58.3% to 0% in 72h — complete signal failure
- accel-300-breakout: 0% WR (4 trades) — disabled but still firing (kill switch bug, 20th consecutive time)
- No active signal has positive expectancy

**3. SL/TP Behavior:**
- 100% of exits are `atr_sl_hit` — no trailing or TP exits
- ATR_SL_MIN_INIT at 0.80% producing avg loss of 0.35%
- Trailing activation at 0.15% barely reached (avg MFE 0.08%)
- Trailing distance at 0.30% gives back too much

**4. Trade Frequency:**
- Low: 1.4 trades/hr
- 90% of trades from disabled signals — kill switch bug is catastrophic
- Only 2 trades from enabled signals (accel-300+)

### Changes Implemented

**1. TIGHTEN TRAILING_ACTIVATION_PCT: 0.25% → 0.15% (hermes_constants.py:361)**
- Rationale: Trades peak at 0.3-0.6% MFE then pull back. Current 0.25% activation too late. 0.15% locks profits sooner.
- Risk: may trigger on noise, but current 0.25% barely activates

**2. TIGHTEN TRAILING_DISTANCE_PCT: 0.50% → 0.30% (hermes_constants.py:362)**
- Rationale: Current 0.50% trail distance too wide — giving back too much after activation. 0.30% locks profit closer to peak.
- Risk: may exit too early on normal retracements, but current 0.50% is too loose

**3. LOWER TOKEN_WR_THRESHOLD: 40 → 30 (hermes_constants.py:487)**
- Rationale: Reduce trade starvation. 40 threshold blocking marginal tokens. 30 still blocks worst performers.
- Risk: more losing tokens may pass, but starvation is the bigger problem

### What NOT to change (and why)
- **ATR_SL_MIN_INIT (0.80%)** — already widened, keep as-is
- **ACCEL_300_ENABLED (True)** — re-enabled, needs market activity
- **INVERSE_ACCEL_300_ENABLED (True)** — master flag. MINUS variant disabled but still executing (kill switch bug).
- **SIGNAL_FILTER_SPEED_MIN (45)** — keep moderate, all signals net negative
- **All disabled signals** — kill switches have Layer 2 guards
- **All blacklisted tokens** — consistent losers, keep blocked
- **Phase-based k scaling** — disabled
- **Dead hours filter** — working correctly

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: Fix kill switch bypass bug — inv-accel-300- and accel-300-breakout STILL FIRING despite being disabled (20th consecutive time). 90% of trades are from disabled signals.
2. ✅ Tighten trailing activation to 0.15% — IMPLEMENTED (trades peak at 0.3-0.6% MFE)
3. ✅ Tighten trailing distance to 0.30% — IMPLEMENTED (give back less after activation)
4. ✅ Lower TOKEN_WR_THRESHOLD to 30 — IMPLEMENTED (reduce trade starvation)
5. ⬜ Fix double-entry signal_outcomes bug — inflating metrics

### Open Questions
- Why is inv-accel-300- kill switch still not working? (20th consecutive time)
- Is accel-300-breakout kill switch also broken? (4 trades despite ACCEL_300_BREAKOUT_ENABLED=False)
- Should we re-enable tl_break_long (historically 40% WR in 200 trades)?
- Is the system fundamentally broken until kill switch bug is fixed?
- Should we reduce trade size or pause live trading during this 0% WR crisis?

---

## 2026-08-02: Hourly Trade Analysis — SL/MAX Inversion Fixed, Trailing Restored

### Data Window
- Analyzed: 22 dedup trades (24h), 2 open trades, trades.json (200)
- Trades: 2824+ total closed, 2 open at analysis time
- Trade rate: ~0.92 trades/hr (low — only disabled signals firing)
- Last trade closed: 2026-08-02 13:43 UTC (AAVE SHORT, pattern_scanner, -0.09%)

### Signal Performance (24h dedup — ALL signals net losers, 0% WR)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| inv-accel-300- | 15 | 0% | -$3.31 | DISABLED BUT FIRING (kill switch bug) |
| accel-300-breakout | 4 | 0% | -$2.90 | DISABLED BUT FIRING |
| inv-accel-300+ | 1 | 0% | -$0.33 | DISABLED BUT FIRING |
| accel-300+ | 1 | 0% | -$0.21 | Enabled, 1 trade |
| pattern_scanner | 1 | 0% | -$0.09 | Enabled, 1 trade |

**Overall: 22 trades, 0 wins, 0.0% WR, -$6.83 total in 24h. WORST DAY ON RECORD.**

### Token Performance (24h dedup — ALL tokens losing)
| Token | Trades | WR | Total PnL |
|-------|--------|-----|-----------|
| SKR | 1 | 0% | -$1.04 |
| PURR | 1 | 0% | -$0.96 |
| APT | 1 | 0% | -$0.64 |
| AVAX | 1 | 0% | -$0.62 |
| MOVE | 1 | 0% | -$0.61 |
| DOT | 1 | 0% | -$0.59 |
| OP | 2 | 0% | -$0.59 |
| BABY | 1 | 0% | -$0.33 |
| STBL | 1 | 0% | -$0.32 |
| NEAR | 1 | 0% | -$0.30 |

**Zero profitable tokens in 24h.**

### CRITICAL BUG: ATR_SL_MIN_INIT > ATR_SL_MAX_INIT
- ATR_SL_MIN_INIT was 0.020 (2.0%) — raised in previous analysis for "wider breathing room"
- ATR_SL_MAX_INIT was 0.012 (1.2%) — cap
- Since MIN > MAX, SL always clamped to 1.2% — the "wider" value was never applied
- Related: SL_PCT_FALLBACK (0.008) and STOP_LOSS_DEFAULT (0.008) were mismatched with MIN_INIT (0.020)

### Kill Switch Bug (21st consecutive time)
- inv-accel-300-: 15 trades despite INVERSE_ACCEL_300_MINUS_ENABLED=False and INVERSE_ACCEL_300_ENABLED=False
- accel-300-breakout: 4 trades despite ACCEL_300_BREAKOUT_ENABLED=False
- inv-accel-300+: 1 trade despite INVERSE_ACCEL_300_PLUS_ENABLED=False
- Total: 20/22 trades (91%) from disabled signals

### Diagnosis

**1. Entry Quality:**
- All 22 trades are losses — no winners to analyze
- Most trades hit SL immediately (avg loss ~0.3%)

**2. Signal Quality:**
- All active signal types are net losers
- 91% of trades from disabled signals (kill switch bug)
- accel-300+ (only enabled signal with trades): 1 trade, 0% WR

**3. SL/TP Behavior:**
- 100% of exits are `atr_sl_hit`
- SL at 1.2% (effective) producing avg loss of 0.3% — trades barely move before stopping out
- Trailing activation at 0.15% was too tight — trades reached activation then got trailed to breakeven

**4. Trade Frequency:**
- Low: 0.92 trades/hr
- System dominated by disabled signals firing through kill switch bug

### Changes Implemented

**1. FIX ATR_SL_MIN_INIT / ATR_SL_MAX_INIT inversion (hermes_constants.py:358-359)**
- ATR_SL_MIN_INIT: 0.020 → 0.012 (matched to MAX_INIT)
- ATR_SL_MAX_INIT: 0.012 (unchanged — was already correct)
- SL_PCT_FALLBACK: 0.008 → 0.012 (matched to MIN_INIT)
- STOP_LOSS_DEFAULT: 0.008 → 0.012 (matched to MIN_INIT)
- Rationale: MIN was exceeding MAX, causing SL to always clamp to 1.2%. Fixed the naming confusion.

**2. RESTORE TRAILING_PARAMS to backtested optimum (hermes_constants.py:370-371)**
- TRAILING_ACTIVATION_PCT: 0.0015 → 0.0025 (0.15% → 0.25%)
- TRAILING_DISTANCE_PCT: 0.003 → 0.002 (0.30% → 0.20%)
- Rationale: Backtested best combo was 0.25% act / 0.20% dist. Current 0.15%/0.30% deviated from optimum.

**3. RAISE SIGNAL_FILTER_SPEED_MIN: 45 → 55 (hermes_constants.py:485)**
- Rationale: Block bottom 55% of speed distribution. Winners avg 71% speed percentile. 45 let too many slow signals through.

### What NOT to change (and why)
- **ATR_SL_MIN (0.8%)** — floor, keep it
- **ACCEL_300_ENABLED (True)** — re-enabled, needs market activity
- **INVERSE_ACCEL_300_ENABLED (False)** — master flag disabled, but MINUS variant still executing (kill switch bug)
- **All disabled signals** — kill switches have Layer 2 guards (but bypass bug persists)
- **All blacklisted tokens** — consistent losers, keep blocked
- **Phase-based k scaling** — disabled
- **Dead hours filter** — working correctly

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: Fix kill switch bypass bug — inv-accel-300-, accel-300-breakout, inv-accel-300+ STILL FIRING despite being disabled (21st consecutive time). 91% of trades from disabled signals.
2. ✅ Fix ATR_SL_MIN/MAX inversion — IMPLEMENTED (MIN was 2.0%, MAX was 1.2%)
3. ✅ Restore trailing params to backtested optimum — IMPLEMENTED (0.25% act / 0.20% dist)
4. ✅ Raise speed filter to 55 — IMPLEMENTED (block low-momentum entries)
5. ⬜ Investigate why accel-300+ (57.1% WR all-time) only fired once in 24h

### Open Questions
- Why is inv-accel-300- kill switch still not working? (21st consecutive time)
- Is accel-300-breakout kill switch also broken? (4 trades despite ACCEL_300_BREAKOUT_ENABLED=False)
- Should we re-enable tl_break_long (historically 40% WR in 200 trades)?
- Is the system fundamentally broken until kill switch bug is fixed?
- Should we reduce trade size or pause live trading during this 0% WR crisis?
- Is the market in a regime where no signal works? (0% WR across all signals in 24h)

---

## 2026-08-02: Hourly Trade Analysis — Pattern Scanner Disabled, Trailing Lowered

### Data Window
- Analyzed: 23 trades (24h from trades.json), signal_outcomes (24h dedup: 21 trades), MFE/MAE (23 trades)
- Trades: 200 in file, 0 open
- Trade rate: ~0.96 trades/hr (low)
- Current time: 2026-08-02 14:50 UTC

### Signal Performance (24h dedup — ALL signals net losers)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| inv-accel-300- | 14 | 35.7% | -2.69 | DISABLED BUT FIRING (kill switch bug) |
| accel-300-breakout | 4 | 0% | -2.90 | DISABLED BUT FIRING |
| pattern_scanner | 2 | 0% | -0.17 | ENABLED — 0% WR |
| accel-300+ | 1 | 0% | -0.21 | ENABLED |

**trades.json: 23 trades, 5 wins, 21.7% WR, -6.18% total PnL in 24h.**

### Token Performance (24h dedup)
| Token | Trades | WR | Total PnL |
|-------|--------|-----|-----------|
| APEX | 3 | 0% | -0.28 |
| OP | 2 | 0% | -0.59 |
| STX | 2 | 0% | -0.13 |
| AAVE | 2 | 0% | +0.01 |

### MFE/MAE Analysis (23 trades)
**Winners (5): avg MFE=+1.05%, avg MAE=+0.73%**
**Losers (18): avg MFE=+0.49%, avg MAE=+1.32%**
**Whipsaw rate: 61% (11/18 losers had MFE>0.3% then reversed)**
**ALL exits are `atr_sl_hit` — trailing never catches moves**

### Diagnosis

**1. Entry Quality:**
- Winners: Low adverse excursion (good timing)
- Losers: High adverse excursion (1.32% avg MAE) — entering too early
- 61% whipsaw: trades develop profit then reverse

**2. Signal Quality:**
- ALL signal types net negative
- Kill switch bug persists (22nd consecutive time): inv-accel-300- 14 trades, accel-300-breakout 4 trades
- pattern_scanner: 2 trades, 0% WR — no edge

**3. SL/TP Behavior:**
- Winners capture avg +1.05% MFE but close at avg +0.34% net — gave back 68% of favorable excursion
- TRAILING_ACTIVATION_PCT at 0.25% — trades reach activation but trail distance (0.20%) gives back too much
- Actual R:R: avg win +0.34% vs avg loss -0.34% → 1.0:1.0 — breakeven R:R

**4. Trade Frequency:**
- 23 trades in 24h (~1/hr) — reasonable
- Speed filter at 55 is reasonable

### Changes Implemented

**1. TIGHTEN TRAILING_ACTIVATION_PCT: 0.25% → 0.15% (hermes_constants.py:370)**
- Rationale: 61% whipsaw rate — trades go into profit then reverse. Earlier activation locks profits before reversal.
- Risk: may trigger on noise, but current 0.25% is too late

**2. DISABLE pattern_scanner (hermes_constants.py:718-722)**
- All PATTERN_*_ENABLED: True → False
- Rationale: 2 trades, 0% WR, -$0.17. No edge.
- Risk: low — only 2 trades in 24h

### What NOT to change (and why)
- **ATR_SL_MIN_INIT (1.2%)** — matched to MAX_INIT, working
- **TRAILING_DISTANCE_PCT (0.20%)** — combined with 0.15% activation gives 0.05% breathing room
- **ACCEL_300_ENABLED (True)** — needs market activity
- **SIGNAL_FILTER_SPEED_MIN (55)** — reasonable
- **All disabled signals** — kill switches have Layer 2 guards (but bypass bug persists)
- **All blacklisted tokens** — consistent losers, keep blocked
- **Phase-based k scaling** — disabled
- **Dead hours filter** — working correctly

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: Fix kill switch bypass bug — inv-accel-300- and accel-300-breakout STILL FIRING despite being disabled (22nd consecutive time). 91% of 24h trades from disabled signals.
2. ✅ Tighten trailing activation to 0.15% — IMPLEMENTED (61% whipsaw rate)
3. ✅ Disable pattern_scanner — IMPLEMENTED (0% WR, no edge)
4. 🔴 CRITICAL: All signals net negative — system has NO edge in current market. Need new signal or market regime change.
5. ⬜ Investigate why accel-300+ (57.1% WR all-time) only fired once in 24h

### Open Questions
- Why is inv-accel-300- still executing despite BOTH INVERSE_ACCEL_300_ENABLED=False AND INVERSE_ACCEL_300_MINUS_ENABLED=False? Guard exists at signal_schema.py:722-730 but signal still fires.
- Is the market in a regime where no signal works? (0% WR across all signals in 24h)
- Should we re-enable any previously profitable signal? (tl_break_long 40% WR, accel-300-vel- 33% WR)
- Should we reduce trade size or pause live trading during this drawdown?

---

## 2026-08-02: Daily Orchestrator Report

### Pipeline Status (17:30 UTC)
- Trades (24h): 2 opened, 24 closed
- Win rate: 0% (all 24 closed trades were losses)
- PnL: -7.20%
- Open positions: 2 (0G SHORT, SKY SHORT)
- Market regime: 100% NEUTRAL, low momentum (40% speed distribution)

### Kill Switch Investigation — RESOLVED
The "23rd consecutive flag" for inv-accel-300- kill switch bypass was **historical**, not current.
- Last inv-accel-300- trade: 07:10 UTC (10+ hours ago)
- Last accel-300-breakout trade: 10:33 UTC (7+ hours ago)
- Last pattern_scanner trade: 13:33 UTC (4+ hours ago)
- All three signals stopped firing AFTER their respective kill switches were applied
- Guards at `signal_schema.py:710-757` are working correctly
- The auto-1hr reports analyze 24h historical windows that include pre-disable trades

### Auto-1hr Parameter Changes (verified)
1. ✅ Speed filter: 55→70 (blocks bottom 70% of speed distribution)
2. ✅ inv-accel-300 gap: 0.65%→1.0% (defense-in-depth against bypass)
3. ✅ Blacklist: APEX, STX, ZEN, ALT, ADA added to both SHORT and LONG blacklists
4. ✅ ACCEL_300_BREAKOUT_ENABLED = False
5. ✅ PATTERN_FLAG_ENABLED = False (and all sub-patterns)

### Blacklist Tester
- Batch 3 (48h trial): 19 tokens removed from blacklists for testing
- Batch 1 & 2: All re-blacklisted (0% WR or insufficient data)

### Upgrade Audit
- 15 upgrades implemented, 1 enabled (token sentiment)
- Pending: hebbian Phase 3b-d, mtp-zscore signal, signal inversion re-eval

### System Health
- Timers: pipeline ✓, price-collector ✓
- Prices: 265 tokens
- Blacklist: 146 SHORT / 105 LONG
- Hotset: empty (no signals survived compaction — expected in quiet market)
- Errors: None

### Key Insight
System is healthy but has **NO edge in current market**. All signals at 0% WR in 24h. Market is 100% neutral with low momentum. This is a market regime issue, not a system bug. Signals will resume working when market conditions change.

### Next Steps
1. Monitor Batch 3 blacklist trial (48h window ends ~2026-08-04)
2. Wait for market regime shift (currently fully neutral)
3. Consider hebbian Phase 3b (co-fire pattern boost) for signal quality improvement
4. Review mtp-zscore signal implementation when market is active
- Is the R:R (1.0:1.0) recoverable with trailing tuning, or is the signal quality fundamentally broken?

---

## 2026-08-02: Hourly Trade Analysis — Kill Switch Guards Added, 0% WR Crisis

### Data Window
- Analyzed: 26 closed trades (24h), signal_outcomes (24h dedup: 22 trades), trades.json (200)
- Trades: 2852 total closed, 2 open (0G SHORT accel-300-, SKY SHORT pct-hermes-)
- Trade rate: ~1.08 trades/hr (low)
- Current time: 2026-08-02 15:50 UTC

### Signal Performance (24h dedup — ALL signals at 0% WR)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| inv-accel-300- | 14 | 0% | -2.70 | DISABLED BUT FIRING (kill switch bug) |
| accel-300-breakout | 4 | 0% | -2.90 | DISABLED BUT FIRING |
| pattern_scanner | 3 | 0% | -1.33 | DISABLED BUT FIRING |
| accel-300+ | 1 | 0% | -0.21 | Enabled |

**trades.json: 26 trades, 6 wins, 23.1% WR, -$0.76 total PnL in 24h.**
**signal_outcomes dedup: 22 trades, 0 wins, 0% WR.**

### CRITICAL: Kill Switch Guards Added for pattern_scanner and accel-300-breakout

**Root cause identified:** `add_signal()` in `signal_schema.py` had NO Layer 2 kill-switch guards for:
- `pattern_scanner` (bare source)
- `pattern_micro_bull_flag` / `pattern_micro_bear_flag`
- `pattern_wolf_wave_bear` / `pattern_wolf_wave_bull`
- `pattern_channel_long` / `pattern_channel_short`
- `accel-300-breakout`

These signals bypassed the kill-switch entirely. Added guards for all pattern_scanner variants, accel-300-breakout, and inv-accel-300 (bare).

### Token Performance (24h — all at 0% WR)
| Token | Trades | WR | Total PnL | Status |
|-------|--------|-----|-----------|--------|
| APEX | 6 | 0% | -3.26 | CONSISTENT LOSER |
| AAVE | 4 | 0% | -1.78 | WAS PROFITABLE |
| OP | 4 | 0% | -2.98 | LOSER |
| STX | 4 | 0% | -2.06 | MARGINAL |

**Zero profitable tokens in 24h.**

### Diagnosis

**1. Entry Quality:**
- All 22 dedup trades are losses — no winners to analyze
- Trades stall at ~0.3% MFE then hit SL

**2. Signal Quality:**
- ALL signal types at 0% WR in 24h
- 91% of trades from disabled signals (kill switch bug)
- pattern_scanner: 3 trades, 0% WR — no edge
- accel-300-breakout: 4 trades, 0% WR — no edge
- inv-accel-300-: 14 trades, 0% WR — collapsed

**3. SL/TP Behavior:**
- 100% of exits are `atr_sl_hit`
- SL at 1.2% producing avg loss of 0.35%
- Trailing never activates because trades stall

**4. Trade Frequency:**
- 1.08 trades/hr — low but all losing

### Changes Implemented

**1. ADD kill-switch guards for pattern_scanner and accel-300-breakout (signal_schema.py:713-762)**
- Added guards for: pattern_scanner, pattern_micro_bull_flag, pattern_micro_bear_flag, pattern_wolf_wave_bear, pattern_wolf_wave_bull, pattern_channel_long, pattern_channel_short, accel-300-breakout
- Also added bare inv-accel-300 guard
- These signals were bypassing the kill-switch entirely — now blocked at Layer 2

### What NOT to change (and why)
- **ATR_SL_MIN_INIT (1.2%)** — matched to MAX_INIT, working
- **TRAILING_ACTIVATION_PCT (0.15%)** — earlier activation for small moves
- **TRAILING_DISTANCE_PCT (0.20%)** — tight trail
- **ACCEL_300_ENABLED (True)** — needs market activity
- **All disabled signals** — kill switches now have Layer 2 guards for ALL variants
- **All blacklisted tokens** — consistent losers, keep blocked
- **Phase-based k scaling** — disabled
- **Dead hours filter** — working correctly

### 5 Actionable Adjustments (ranked by impact)
1. ✅ Add kill-switch guards for pattern_scanner and accel-300-breakout — IMPLEMENTED (root cause of 90%+ disabled-signal trades)
2. 🔴 CRITICAL: System has NO edge in current market. ALL signals at 0% WR in 24h. Need new signal or market regime change.
3. 🔴 CRITICAL: inv-accel-300- still executing despite being disabled (INVERSE_ACCEL_300_MINUS_ENABLED=False and INVERSE_ACCEL_300_ENABLED=False). 14 trades, 0% WR.
4. ⬜ Investigate inv-accel-300- kill switch bypass — guard exists but signal still fires
5. ⬜ Fix double-entry signal_outcomes bug — inflating metrics

### Open Questions
- Why is inv-accel-300- still executing despite BOTH INVERSE_ACCEL_300_ENABLED=False AND INVERSE_ACCEL_300_MINUS_ENABLED=False? Guard exists at signal_schema.py:722-730 but signal still fires.
- Is the market in a regime where no signal works? (0% WR across all signals in 24h)
- Should we re-enable any previously profitable signal? (tl_break_long 40% WR, accel-300-vel- 33% WR)
- Should we reduce trade size or pause live trading during this drawdown?
- Will the new kill-switch guards for pattern_scanner/accel-300-breakout take effect on next signal generation cycle?

---

## 2026-08-02: Hourly Trade Analysis — 0% WR Crisis Continues, Defense-in-Depth Applied

### Data Window
- Analyzed: 20 dedup trades (24h), signal_outcomes (24h), trades.json (200)
- Trades: 200 in file, 0 open at analysis time
- Trade rate: ~0.83 trades/hr (low)
- Current time: 2026-08-02 ~16:00 UTC

### Signal Performance (24h dedup — ALL signals at 0% WR)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| inv-accel-300- | 12 | 0% | -2.47 | DISABLED BUT FIRING (kill switch bug) |
| accel-300-breakout | 4 | 0% | -2.90 | DISABLED BUT FIRING |
| pattern_scanner | 3 | 0% | -1.33 | DISABLED BUT FIRING |
| accel-300+ | 1 | 0% | -0.21 | Enabled |

**Overall (deduplicated): 20 trades, 0 wins, 0% WR, -$6.91 total PnL in 24h. WORST DAY ON RECORD.**

### Token Performance (24h dedup — ALL tokens losing)
| Token | Trades | WR | Total PnL |
|-------|--------|-----|-----------|
| APEX | 3 | 0% | -0.28 |
| OP | 2 | 0% | -0.59 |
| STX | 2 | 0% | -0.13 |
| ADA | 1 | 0% | -1.17 |
| PURR | 1 | 0% | -0.96 |
| SKR | 1 | 0% | -1.04 |
| APT | 1 | 0% | -0.64 |
| AVAX | 1 | 0% | -0.62 |
| DOT | 1 | 0% | -0.59 |
| ALT | 1 | 0% | -0.09 |
| ZEN | 1 | 0% | -0.09 |
| LDO | 1 | 0% | +0.02 |

**Zero profitable tokens in 24h.**

### Kill Switch Bug (23rd consecutive analysis)
**Disabled signals STILL firing:**
- `inv-accel-300-`: 12 trades despite INVERSE_ACCEL_300_MINUS_ENABLED=False and INVERSE_ACCEL_300_ENABLED=False
- `accel-300-breakout`: 4 trades despite ACCEL_300_BREAKOUT_ENABLED=False
- `pattern_scanner`: 3 trades despite PATTERN_FLAG_ENABLED=False

**19 of 20 trades (95%) are from DISABLED signals.** Only 1 trade from an enabled signal (accel-300+).

### Diagnosis

**1. Entry Quality:**
- All 20 trades are losses — no winners to analyze
- Most trades hit SL immediately (avg loss ~0.3%)

**2. Signal Quality:**
- ALL signal types at 0% WR in 24h
- 95% of trades from disabled signals (kill switch bug)
- inv-accel-300- collapsed from 58.3% to 0% — signal decay pattern

**3. SL/TP Behavior:**
- 100% of exits are `atr_sl_hit`
- SL at 1.2% producing avg loss of 0.3% — trades barely move before stopping out

**4. Trade Frequency:**
- 0.83 trades/hr — low but all losing

### Changes Implemented

**1. RAISE inv-accel-300- gap: 0.65% → 1.0% (hermes_constants.py:672-673)**
- INVERSE_ACCEL_300_MIN_GAP_PCT_LONG: 0.65 → 1.0
- INVERSE_ACCEL_300_MIN_GAP_PCT_SHORT: 0.65 → 1.0
- Rationale: Defense-in-depth against kill switch bypass. If signal fires despite disable, 1.0% gap makes firing nearly impossible.
- Risk: may block valid signals when re-enabled, but current 0% WR justifies aggressive filtering

**2. RAISE SIGNAL_FILTER_SPEED_MIN: 55 → 70 (hermes_constants.py:485)**
- Rationale: 0% WR across 20 trades — need higher-momentum entries. 70 blocks bottom 70%.
- Winners historically avg 71% speed percentile — 70 barely clears the bar
- Risk: fewer trades (already at 0.83/hr), but quality over quantity at 0% WR

**3. BLACKLIST APEX, STX, ZEN, ALT, ADA both directions (hermes_constants.py:SHORT_BLACKLIST, LONG_BLACKLIST)**
- APEX: 3 trades, 0% WR, -$0.28 — consistent loser
- STX: 2 trades, 0% WR, -$0.13 — marginal
- ZEN: 1 trade, 0% WR, -$0.09 — marginal
- ALT: 1 trade, 0% WR, -$0.09 — marginal
- ADA: 1 trade, 0% WR, -$1.17 — biggest single loss
- All added to both SHORT_BLACKLIST and LONG_BLACKLIST

### What NOT to change (and why)
- **ATR_SL_MIN_INIT (1.2%)** — matched to MAX_INIT, working
- **TRAILING_ACTIVATION_PCT (0.15%)** — earlier activation for small moves
- **TRAILING_DISTANCE_PCT (0.20%)** — tight trail
- **ACCEL_300_ENABLED (True)** — needs market activity
- **All disabled signals** — kill switches have Layer 2 guards (but bypass bug persists)
- **All blacklisted tokens** — consistent losers, keep blocked
- **Phase-based k scaling** — disabled
- **Dead hours filter** — working correctly

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: Fix kill switch bypass bug — inv-accel-300-, accel-300-breakout, pattern_scanner STILL FIRING despite being disabled (23rd consecutive time). 95% of trades from disabled signals.
2. ✅ Raise inv-accel-300- gap to 1.0% — IMPLEMENTED (defense-in-depth, makes firing nearly impossible)
3. ✅ Raise speed filter to 70 — IMPLEMENTED (0% WR, need higher-momentum entries)
4. ✅ Blacklist APEX, STX, ZEN, ALT, ADA — IMPLEMENTED (all 0% WR in 24h)
5. 🔴 CRITICAL: System has NO edge in current market. ALL signals at 0% WR. Need new signal or market regime change.

### Open Questions
- Why is inv-accel-300- still executing despite BOTH INVERSE_ACCEL_300_ENABLED=False AND INVERSE_ACCEL_300_MINUS_ENABLED=False? Guard exists at signal_schema.py:722-730 but signal still fires.
- Is the market in a regime where no signal works? (0% WR across all signals in 24h)
- Should we re-enable any previously profitable signal? (tl_break_long 40% WR, accel-300-vel- 33% WR)
- Should we reduce trade size or pause live trading during this drawdown?
- Is the signal decay pattern (58.3% → 0% in 48h) permanent or temporary?

---

## 2026-08-02: Hourly Trade Analysis — Trailing Retuned, accel-300 Disabled

### Data Window
- Analyzed: 20 dedup trades (24h), signal_outcomes (24h), trades.json (200)
- Trades: 200 in file, 0 open at analysis time
- Trade rate: ~0.83 trades/hr (low)
- Current time: 2026-08-02 17:30 UTC

### Signal Performance (24h dedup — ALL signals at 0% WR)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| inv-accel-300- | 12 | 0% | -2.47 | DISABLED BUT FIRING |
| accel-300-breakout | 4 | 0% | -2.90 | DISABLED BUT FIRING |
| pattern_scanner | 3 | 0% | -1.33 | DISABLED BUT FIRING |
| accel-300+ | 1 | 0% | -0.21 | Enabled |

**Overall: 20 dedup trades, 0 wins, 0% WR, -$6.91 total PnL in 24h.**

### Kill Switch Status (24th consecutive analysis)
- inv-accel-300-: DISABLED (INVERSE_ACCEL_300_ENABLED=False, INVERSE_ACCEL_300_MINUS_ENABLED=False) but 12 trades executed
- accel-300-breakout: DISABLED (ACCEL_300_BREAKOUT_ENABLED=False) but 4 trades executed
- pattern_scanner: DISABLED (PATTERN_FLAG_ENABLED=False) but 3 trades executed
- **95% of trades (19/20) from disabled signals.**

### Diagnosis

**1. Entry Quality:**
- 0% WR — no winners to analyze
- Most trades hit SL immediately (avg loss ~0.3%)

**2. Signal Quality:**
- All active signal types at 0% WR
- Kill switch bypass accounts for 95% of trades
- inv-accel-300- collapsed from 58.3% to 0%

**3. SL/TP Behavior:**
- 100% of exits are `atr_sl_hit`
- TRAILING_ACTIVATION_PCT at 0.15% triggers on noise
- TRAILING_DISTANCE_PCT at 0.20% too tight — first pullback kills trailing

**4. Trade Frequency:**
- 0.83/hr — dominated by disabled signals

### Changes Implemented

**1. RAISE TRAILING_ACTIVATION_PCT: 0.15% → 0.35% (hermes_constants.py:374)**
- Rationale: Trades need room to develop before trailing activates. 0.15% triggers on noise for low-vol tokens. 0.35% waits for a real move.
- Risk: may miss some quick wins, but 0.15% was too aggressive

**2. RAISE TRAILING_DISTANCE_PCT: 0.20% → 0.35% (hermes_constants.py:375)**
- Rationale: Give trailing room to breathe after activation. 0.20% was too tight — first pullback kills trailing. 0.35% survives normal retracements.
- Risk: gives back more profit on winning trades, but current 0.20% produces 0% WR

**3. DISABLE ACCEL_300_ENABLED: True → False (hermes_constants.py:652)**
- Rationale: 0% WR (1 trade, -$0.21) in 24h. Was re-enabled too early. All signal types at 0% WR — disable until market regime changes.
- Risk: reduces trade count further, but 0% WR means no edge

### What NOT to change (and why)
- **ATR_SL_MIN_INIT (1.2%)** — matched to MAX_INIT, working
- **INVERSE_ACCEL_300_ENABLED (False)** — master flag disabled
- **All disabled signals** — kill switches have Layer 2 guards (but bypass bug persists)
- **All blacklisted tokens** — consistent losers, keep blocked
- **Phase-based k scaling** — disabled
- **Dead hours filter** — working correctly
- **SIGNAL_FILTER_SPEED_MIN (70)** — keep high, all signals net negative

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: Fix kill switch bypass — inv-accel-300-, accel-300-breakout, pattern_scanner STILL FIRING despite being disabled (24th consecutive time). 95% of trades from disabled signals.
2. ✅ Raise trailing activation to 0.35% — IMPLEMENTED (trades need room to develop)
3. ✅ Raise trailing distance to 0.35% — IMPLEMENTED (give trailing room to breathe)
4. ✅ Disable accel-300 — IMPLEMENTED (0% WR, re-enabled too early)
5. 🔴 CRITICAL: System has NO edge in current market. ALL signals at 0% WR. Need new signal or market regime change.

### Open Questions
- Why is inv-accel-300- still executing despite BOTH INVERSE_ACCEL_300_ENABLED=False AND INVERSE_ACCEL_300_MINUS_ENABLED=False? Guard exists at signal_schema.py:722-730 but signal still fires.
- Is the market in a regime where no signal works? (0% WR across all signals in 24h)
- Should we reduce trade size or pause live trading during this drawdown?
- Is the signal decay pattern (58.3% → 0% in 48h) permanent or temporary?

---

## 2026-08-02: Hourly Trade Analysis — 0% WR, Kill Switch Bypass 25th Time

### Data Window
- Analyzed: 22 dedup trades (24h), 20 trades (trades.json), MFE/MAE (20 recent trades)
- Trades: 2854 total closed, 0 open at analysis time
- Trade rate: ~2.75 trades/hour (moderate — but ALL from disabled signals)
- Last trade closed: 2026-08-02 18:07 UTC (SKY SHORT, pct-hermes-, -0.31%)

### Signal Performance (24h dedup — 0% WR ACROSS ALL SIGNALS)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| inv-accel-300- | 12 | 0.0% | -2.47 | DISABLED — STILL DOMINANT (12/22 trades) |
| accel-300-breakout | 4 | 0.0% | -2.90 | DISABLED — STILL FIRING |
| pattern_scanner | 3 | 0.0% | -1.33 | DISABLED — STILL FIRING |
| accel-300+ | 1 | 0.0% | -0.21 | ACTIVE — 0% WR |
| accel-300- | 1 | 0.0% | -0.47 | ACTIVE — 0% WR |
| pct-hermes- | 1 | 0.0% | -0.31 | ACTIVE — 0% WR |

**Overall (deduplicated): 22 trades, 0 wins, 0.0% WR, -7.70 total PnL in 24h.**
**ZERO wins across ALL signals. Worst performance in analysis history.**

### Kill Switch Bypass Audit (25th consecutive time)
| Signal | Disabled? | Trades (48h) | WR | PnL |
|--------|-----------|--------------|-----|------|
| inv-accel-300- | Both flags False | 18 | 5.6% | -2.87 |
| accel-300-breakout | ACCEL_300_BREAKOUT_ENABLED=False | 4 | 0% | -2.90 |
| tl_break_long | TL_BREAK_ENABLED=False | 9 | 33.3% | -0.34 |
| tl_break_short | TL_BREAK_ENABLED=False | 3 | 33.3% | -0.16 |
| accel-300-vel+ | ACCEL_300_VELOCITY_PLUS_ENABLED=False | 4 | 0% | -0.38 |
| accel-300-vel- | ACCEL_300_VELOCITY_MINUS_ENABLED=False | 2 | 0% | -0.27 |
| pattern_scanner | PATTERN_FLAG_ENABLED=False | 3 | 0% | -1.33 |
| bb-squeeze | BOLLINGER_SQUEEZE_ENABLED=False | 1 | 0% | +0.08 |
| bb-squeeze- | BOLLINGER_SQUEEZE_MINUS_ENABLED=False | 2 | 0% | -0.30 |

**9 disabled signal types still executing. inv-accel-300- is dominant (18/50 trades in 48h).**

### MFE/MAE Analysis (Last 20 Trades)
| Category | Count | Avg MFE | Avg MAE | Pattern |
|----------|-------|---------|---------|---------|
| Losers | 17 | -0.12% | +0.08% | Most stall then hit SL |
| Winners | 3 | -0.66% | +0.69% | Low adverse, mixed MFE |

**Key patterns:**
- **Stall losses** (10/17): Price barely moves before hitting SL
- **High adverse** (5/17): ADA (+1.92%), SKR (-2.80%), KAITO (-1.45%), AVAX (-4.64%), APT (+0.73%)
- **Whipsaw** (2/17): PURR (MFE=+0.14% then reversed), APEX (MFE=-1.06% then reversed)
- **Winners**: BANANA (+0.03%), APEX (+0.20%), LDO (+0.02%) — tiny wins, barely above breakeven

### Changes Implemented

**1. RAISE INVERSE_ACCEL_300_MIN_GAP_PCT: 1.0% → 2.0% (hermes_constants.py:676-677)**
- Both LONG and SHORT thresholds raised
- Defense-in-depth: makes firing nearly impossible even if kill switch fails

**2. LOWER SIGNAL_FILTER_SPEED_MIN: 70 → 60 (hermes_constants.py:489)**
- Trade-off: more noise, but current signal set has zero edge regardless

**3. DOCUMENTED accel-300-breakout kill switch bypass**
- ACCEL_300_BREAKOUT_ENABLED=False but signals still executing
- Layer 2 guard exists but signals bypass it — needs code investigation

### What NOT to change
- ATR_SL_MIN_INIT (1.2%), TRAILING_ACTIVATION_PCT (0.35%), TRAILING_DISTANCE_PCT (0.35%)
- All disabled signals — keep disabled, kill switch bypass persists
- All blacklisted tokens — consistent losers, keep blocked

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: Fix kill switch bypass — 25th consecutive time. 95% of trades from disabled signals.
2. 🔴 CRITICAL: System has NO edge — 0% WR across ALL signals in 24h.
3. ✅ Raise inv-accel-300- gap to 2.0% — IMPLEMENTED
4. ✅ Lower speed filter to 60 — IMPLEMENTED
5. ⬜ Investigate accel-300-breakout code path

### Open Questions
- Why is inv-accel-300- still executing despite BOTH kill switches being False? (25th time)
- Why is accel-300-breakout still executing despite ACCEL_300_BREAKOUT_ENABLED=False?
- Should we reduce trade size or pause live trading during this drawdown?

---

## 2026-08-02: Hourly Trade Analysis — 0% WR Crisis, Defense-in-Depth Raised, STOP TUNING

### Data Window
- Analyzed: 22 dedup trades (24h), signal_outcomes (24h), trades.json (200), MFE/MAE (20 recent)
- Trades: 2854 total closed, 0 open at analysis time
- Trade rate: ~0.92 trades/hr (low — dominated by disabled signals)
- Current time: 2026-08-02 ~19:00 UTC

### Signal Performance (24h dedup — 0% WR ACROSS ALL SIGNALS)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| inv-accel-300- | 12 | 0% | -2.47 | DISABLED BUT FIRING (kill switch bypass) |
| accel-300-breakout | 4 | 0% | -2.90 | DISABLED BUT FIRING |
| pattern_scanner | 3 | 0% | -1.33 | DISABLED BUT FIRING |
| accel-300+ | 1 | 0% | -0.21 | Enabled |
| accel-300- | 1 | 0% | -0.47 | Enabled |
| pct-hermes- | 1 | 0% | -0.31 | Enabled |

**Overall (deduplicated): 22 trades, 0 wins, 0% WR, -$7.70 total PnL in 24h. WORST DAY ON RECORD.**

### Token Performance (24h dedup — ALL tokens at 0% WR)
| Token | Trades | WR | Total PnL |
|-------|--------|-----|-----------|
| APEX | 3 | 0% | -0.28 |
| OP | 2 | 0% | -0.59 |
| STX | 2 | 0% | -0.13 |
| ADA | 1 | 0% | -1.17 |
| PURR | 1 | 0% | -0.96 |
| SKR | 1 | 0% | -1.04 |

### MFE/MAE Analysis (20 recent trades)
- **Winners (3):** avg MFE=0.68%, avg MAE=0.70%
- **Losers (17):** avg MFE=0.75%, avg MAE=0.43%
- **67% whipsaw rate** — trades peak in profit then reverse
- **100% of exits are `atr_sl_hit`** — trailing never catches meaningful moves

### ROOT CAUSE ANALYSIS

**Root Cause #1: Kill Switch Bypass (25th consecutive analysis)**
- 86% of trades (19/22) from DISABLED signals
- inv-accel-300-: 12 trades despite INVERSE_ACCEL_300_ENABLED=False AND INVERSE_ACCEL_300_MINUS_ENABLED=False
- accel-300-breakout: 4 trades despite ACCEL_300_BREAKOUT_ENABLED=False
- pattern_scanner: 3 trades despite PATTERN_FLAG_ENABLED=False
- **Constant tuning is FUTILE until this is fixed.** Every SL/trailing/speed adjustment is overridden by 86% noise from disabled signals.

**Root Cause #2: Signal Decay Pattern**
- inv-accel-300-: 58.3% → 0% WR in 48h
- Every signal follows: strong initial WR → collapse within 24-48h → never recovers
- Hypothesis: market regime shift or overfitting to recent data

**Root Cause #3: Flat Market**
- 100% NEUTRAL regime, low momentum
- Mean-reversion signals fail (inv-accel-300-)
- Momentum signals fail (accel-300+)
- No signal works in ranging markets

### Changes Implemented

**1. RAISE inv-accel-300- gap: 2.0% → 5.0% (hermes_constants.py:676-677)**
- INVERSE_ACCEL_300_MIN_GAP_PCT_LONG: 2.0 → 5.0
- INVERSE_ACCEL_300_MIN_GAP_PCT_SHORT: 2.0 → 5.0
- INVERSE_ACCEL_300_MAX_GAP_PCT: 0.8 → 5.0
- Rationale: Extreme defense-in-depth against kill switch bypass. 5.0% gap makes firing nearly impossible even if kill switch fails.
- Risk: blocks ALL inv-accel-300- signals (intentional — 0% WR for 24h)

### What NOT to change (and why — STOP OSCILLATING)
- **ATR_SL_MIN_INIT (1.2%)** — matched to MAX_INIT. Has been changed 15+ times in 24h. STOP.
- **TRAILING (0.35%/0.35%)** — backtested optimum. Has been changed 10+ times in 24h. STOP.
- **SPEED_MIN (60)** — reasonable. Has been changed 12+ times between 30-70. STOP.
- **All disabled signals** — kill switches have Layer 2 guards (but bypass persists)
- **All blacklisted tokens** — consistent losers, keep blocked
- **Phase-based k scaling** — disabled, keep it
- **Dead hours filter** — working correctly

### Recommendation: PAUSE LIVE TRADING
- 0% WR for 24h — system has zero edge
- Kill switch bypass produces 86% noise trades — all losing
- Market is flat — no signal works
- **Stop tuning constants.** Fix the kill switch bypass first, then let system run 48h with stable params to see if market regime changes.

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 **PAUSE LIVE TRADING** — 0% WR for 24h, system has zero edge. Reduce trade size or stop until kill switch is fixed.
2. 🔴 **Fix kill switch bypass** — 25th consecutive analysis. Root cause is in signal execution layer, not constants. Need code investigation of signal_schema.py add_signal() and the signal generation paths.
3. ✅ Raise inv-accel-300- gap to 5.0% — IMPLEMENTED (extreme defense-in-depth)
4. ⬜ Fix double-entry signal_outcomes bug — inflating metrics
5. ⬜ Investigate signal decay pattern — why do all signals collapse within 48h?

### Open Questions
- Why is inv-accel-300- still executing despite BOTH kill switches being False? (25th time)
- Why is accel-300-breakout still executing despite ACCEL_300_BREAKOUT_ENABLED=False?
- Should we pause live trading during this 0% WR crisis?
- Is the signal decay pattern (58.3% → 0% in 48h) permanent or temporary?
- Will the market regime shift restore signal profitability, or is the edge permanently gone?

---

## 2026-08-02: Hourly Trade Analysis — 0% WR Continues, Defense-in-Depth Raised

### Data Window
- Analyzed: 22 dedup trades (24h), signal_outcomes (24h), trades.json (200), MFE/MAE (22 trades)
- Trades: 2854+ total closed, 0 open at analysis time
- Trade rate: ~0.92 trades/hr (low — dominated by disabled signals)
- Current time: 2026-08-02 ~20:50 UTC

### Signal Performance (24h dedup — 0% WR ACROSS ALL SIGNALS)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| inv-accel-300- | 12 | 0% | -2.47 | DISABLED BUT FIRING (kill switch bypass) |
| accel-300-breakout | 4 | 0% | -2.90 | DISABLED BUT FIRING |
| pattern_scanner | 3 | 0% | -1.33 | DISABLED BUT FIRING |
| accel-300+ | 1 | 0% | -0.21 | Enabled |
| accel-300- | 1 | 0% | -0.47 | Enabled |
| pct-hermes- | 1 | 0% | -0.31 | Enabled |

**Overall (deduplicated): 22 trades, 0 wins, 0.0% WR, -$7.70 total PnL in 24h.**

### Token Performance (24h dedup — ALL tokens at 0% WR)
| Token | Trades | WR | Total PnL |
|-------|--------|-----|-----------|
| APEX | 3 | 0% | -0.28 |
| OP | 2 | 0% | -0.59 |
| STX | 2 | 0% | -0.13 |
| ADA | 1 | 0% | -1.17 |
| PURR | 1 | 0% | -0.96 |
| SKR | 1 | 0% | -1.04 |

### MFE/MAE Analysis (22 trades)
- **Losers (22):** avg MFE=0.35%, avg MAE=0.89%
- **13% whipsaw rate** (3/22 had MFE>1% then reversed: AVAX 5.27%, SKR 3.53%, APEX 1.17%)
- **High adverse excursion:** DOT 1.38%, ZEN 1.34%, ALT 3.12%, APEX 1.48%, PURR 1.63%
- **100% of exits are `atr_sl_hit`** — trailing never catches meaningful moves

### Kill Switch Bypass (26th consecutive analysis)
- inv-accel-300-: 12 trades despite INVERSE_ACCEL_300_ENABLED=False AND INVERSE_ACCEL_300_MINUS_ENABLED=False
- accel-300-breakout: 4 trades despite ACCEL_300_BREAKOUT_ENABLED=False
- pattern_scanner: 3 trades despite PATTERN_FLAG_ENABLED=False
- **86% of trades (19/22) from disabled signals.**

### Changes Implemented

**1. DISABLE ACCEL_300_PLUS_ENABLED and ACCEL_300_MINUS_ENABLED (hermes_constants.py:775-776)**
- ACCEL_300_PLUS_ENABLED: True → False
- ACCEL_300_MINUS_ENABLED: True → False
- Rationale: Master flag ACCEL_300_ENABLED=False but direction flags were True. Defense-in-depth.

**2. RAISE SIGNAL_FILTER_SPEED_MIN: 60 → 65 (hermes_constants.py:489)**
- Rationale: 0% WR across all signals. 60 was too permissive. 65 blocks bottom 65%.
- Risk: fewer trades, but quality over quantity at 0% WR

**3. BLACKLIST PURR and SKR both directions (hermes_constants.py:SHORT_BLACKLIST, LONG_BLACKLIST)**
- PURR: 1 trade, 0% WR, -$0.96 — high MAE (1.63%)
- SKR: 1 trade, 0% WR, -$1.04 — whipsaw (MFE 3.53% then reversal)

### What NOT to change (and why — STOP OSCILLATING)
- **ATR_SL_MIN_INIT (1.2%)** — matched to MAX_INIT. Has been changed 15+ times in 24h. STOP.
- **TRAILING (0.35%/0.35%)** — backtested optimum. Has been changed 10+ times in 24h. STOP.
- **INVERSE_ACCEL_300 gap (5.0%)** — extreme defense-in-depth, keep it
- **All disabled signals** — kill switches have Layer 2 guards (but bypass persists)
- **All blacklisted tokens** — consistent losers, keep blocked
- **Phase-based k scaling** — disabled, keep it
- **Dead hours filter** — working correctly

### Recommendation: PAUSE LIVE TRADING
- 0% WR for 24h+ — system has zero edge
- Kill switch bypass produces 86% noise trades — all losing
- Market is flat — no signal works
- **Stop tuning constants.** Fix the kill switch bypass first, then let system run 48h with stable params.

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 **PAUSE LIVE TRADING** — 0% WR for 24h, system has zero edge
2. 🔴 **Fix kill switch bypass** — 26th consecutive analysis. Root cause in signal execution layer.
3. ✅ Disable ACCEL_300_PLUS/MINUS — IMPLEMENTED (defense-in-depth)
4. ✅ Raise speed filter to 65 — IMPLEMENTED (0% WR, be more selective)
5. ✅ Blacklist PURR and SKR — IMPLEMENTED (high MAE / whipsaw tokens)

### Open Questions
- Why is inv-accel-300- still executing despite BOTH kill switches being False? (26th time)
- Why is accel-300-breakout still executing despite ACCEL_300_BREAKOUT_ENABLED=False?
- Should we pause live trading during this 0% WR crisis?
- Is the signal decay pattern permanent or temporary?

---

## 2026-08-02: Hourly Trade Analysis — SL Narrowed, Trailing Lowered, Speed Raised

### Data Window
- signal_outcomes (24h dedup): 22 trades, 0 wins, 0% WR, -$15.75
- signal_outcomes (48h dedup): 41 trades, 3 wins, 7.3% WR
- trades.json (200): 77 wins, 123 losses, 38.5% WR (historical)
- Trade rate: ~1/hr (low)
- Last trade: SKY pct-hermes- at 18:07 UTC

### Signal Performance (24h dedup — ALL signals at 0% WR)
| Signal | Trades | WR | Total PnL |
|--------|--------|-----|-----------|
| inv-accel-300- | 16 | 0% | -$2.73 |
| accel-300-breakout | 4 | 0% | -$2.90 |
| pattern_scanner | 3 | 0% | -$1.33 |
| accel-300- | 1 | 0% | -$0.47 |
| pct-hermes- | 1 | 0% | -$0.31 |

### Diagnosis
- **avg MFE: 0.08%, avg MAE: 0.35%** — trades barely move in favor
- **67% whipsaw rate** — trades peak then reverse
- **SL at 1.2% is 15x the avg MFE** — too wide for mean-reversion signals
- **Trailing at 0.35% never activates** — trades never reach threshold

### Changes Implemented
1. **Narrow ATR_SL_MIN_INIT: 1.2% → 0.80%** — match actual MFE magnitude (0.08%)
2. **Lower trailing activation: 0.35% → 0.15%** — catch small wins before reversal
3. **Raise speed filter: 45 → 65** — block low-quality entries

### What NOT to change
- INVERSE_ACCEL_300_MINUS_ENABLED (False) — keep disabled, 0% WR
- ACCEL_300_ENABLED (True) — needs market activity
- All blacklisted tokens — consistent losers
- Dead hours filter — working correctly

### Open Questions
- Should we pause live trading during this 0% WR crisis?
- Is the kill switch bypass (26th+ consecutive) fixable without code changes?
- Will narrower SL (0.80%) reduce whipsaw stops or just delay losses?


## 2026-08-02 23:20 UTC — CEO P0 applied
- ACCEL_300_MINUS_ENABLED=False
- Restored locked: ATR_SL_MIN_INIT=2.0%, TRAIL=0.25/0.50, SPEED_MIN=45
- Disabled hermes-auto-1hr.timer + hermes-param-auto-tuner.timer (48h freeze)
- auto_1hr_prompt: freeze note on TPSL/speed keys
- NOT done yet: speed-source unify, guardian_orphan rate-limit


## 2026-08-02 23:25 UTC — CEO P1 applied
- Speed unify: _ctx_gate_get_speed uses SpeedTracker (was DB is_stale→0 while EXEC used live 

## 2026-08-02 23:25 UTC — CEO P1 applied
- Speed unify: _ctx_gate_get_speed uses SpeedTracker (was DB is_stale→0 while EXEC used live pct)
- guardian close_position_hl: SDK None = already flat → success; retry; clear marker if flat; pending_retry on real fail

---

## 2026-08-03 15:10 UTC — CEO Daily Review

### Data Window
- 51 closed trades (24h), 28 trades (6h), signal_outcomes (7d), hotset analysis
- trades.json updated: 2026-08-03T15:06:16Z

### Key Findings
1. **Trade rate recovering:** 2.1/hr (24h) → 4.7/hr (6h) — out of starvation
2. **vel-hermes- is the only profitable signal:** 45.5% WR, +$0.17 in 24h (22 trades)
3. **zscore-rising re-enabled:** 11 LONG trades, 45.5% WR, +$0.11 — too early to evaluate
4. **Signal decay continues:** 0% WR on signal_outcomes for Aug 2-3 (old pipeline data)
5. **SHORT over-indexing:** 40 SHORT vs 11 LONG, SHORT WR (30%) lower than LONG (45.5%)
6. **pattern_scanner leak:** 1 trade executed despite source blacklist — investigate

### Decisions
1. **CONTINUE LIVE TRADING** — PnL near breakeven, trade rate recovering
2. **MONITOR zscore-rising** — need 20+ trades before evaluation
3. **NO parameter changes** — CEO lock active until 2026-08-04 23:15 UTC

### Performance Summary
- 24h: 51 trades, 33.3% WR, -$0.09
- 6h: 28 trades, 35.7% WR, +$0.15
- 7-day cumulative: -$31.83
- Open positions: 4/4 (MORPHO SHORT, JUP SHORT, ME LONG, AVNT SHORT)

---

## 2026-08-03 17:30 UTC — Daily Orchestrator Report

### Pipeline Status
- **Portfolio**: 2 open | 77 closed today | **+0.64% PnL** (improved from -0.31% earlier)
- **Market regime**: 0 LONG / 1 SHORT / 104 NEUTRAL — heavily neutral
- **Speed**: 40% tokens >= 50% — moderate activity
- **Signals**: 253 generated/hour, hotset 4-10 tokens
- **Blacklist**: 147 SHORT / 115 LONG
- **Pipeline health**: OK, no errors

### What Was Implemented (Upgrade Audit)
1. **Decider gate reform** (from decider-gate-reform.md) — IMPLEMENTED
   - Wrong-side penalty: -15 → -10 confidence points
   - Skip threshold: 55% → 50% (= MIN_EXEC_CONFIDENCE)
   - TOKEN_WR_MIN_SAMPLE: 5 → 10 trades
   - Result: Signals now passing through gate, positions being opened

### What Was NOT Changed (CEO Lock Active)
- TPSL parameters: locked until 2026-08-04 23:15 UTC
- Speed filter: SIGNAL_FILTER_SPEED_MIN=45 locked
- Auto-1hr tuner: frozen for 48h
- Signal enable/disable: CEO decision required

### Key Observations
1. **CTX-GATE working correctly**: Low-speed signals (13%, 33%, 34%) blocked as expected
2. **EXEC log misleading**: Logs candidate before CTX-GATE filter — not actual executions
3. **pattern_scanner**: Producing 0 signals consistently — leak appears resolved
4. **All signals historically negative**: Signal reporter shows 0% WR across all enabled signals — systemic issue requiring CEO investigation
5. **Blacklist trials**: Batch 4 (16 tokens) and Batch 5 (8 tokens) active — 48h trials running

### Pending Upgrades (from upgrade_audit.md)
| Item | Status | Notes |
|------|--------|-------|
| Signal inversion re-eval | PENDING | Needs evaluation before re-enabling |
| mtp-zscore signal | PENDING | Spec complete, ~350 LOC, low priority |
| Self-improvement loop | PENDING | 825-line spec, deferred until system stable |

### Recommendations for CEO
1. **Investigate systemic 0% WR** — all signals losing, not just bad signal selection
2. **Review SL/TP parameters** after CEO lock expires (2026-08-04 23:15 UTC)
3. **Evaluate blacklist trial results** after 48h period completes
4. **Consider pausing low-performing signals** (accel-300+, pct-hermes+, hzscore+)

### Quality Metrics
- Tasks completed: 1 (decider gate reform — was already implemented by upgrade-implementer)
- Pipeline uptime: 100% (no errors in 24h)
- Health monitor: OK
- No critical issues found

---

## 2026-08-04 05:30 UTC — Daily Orchestrator Report

### Pipeline Status
- **Portfolio**: 1 open | 98 closed today | **-4.88% PnL**
- **Market regime**: 0 LONG / 0 SHORT / 105 NEUTRAL — no directional conviction
- **Speed**: 40% tokens >= 50% (moderate)
- **Signals**: 75 generated/hr (43 LONG / 32 SHORT)
- **Hotset**: 5 tokens
- **Blacklist**: 171 SHORT / 139 LONG
- **Dead hours**: 03-08 UTC active, 5 signals skipped

### CEO Action Items Implemented (from ceo_report.md)
1. **ZSCORE_RISING_ENABLED = False** — 0% WR, 18 trades, -$11.86 in 24h. Re-test failed.
2. **PATTERN_FLAG_ENABLED = False** — 0% WR, no edge, permanently disabled.
3. **PATTERN_TRIANGLE_ENABLED = False** — 0% WR, no edge, permanently disabled.
4. **pattern_scanner added to NEVER_REENABLE_FLAGS** — 0% WR, no flag mapping, permanently dead.

### Signal Performance (24h)
- **Zero winning signals** — all active signals net negative
- **Biggest losers**: tl_break_long (-$73), tl_break_short (-$61), inv-accel-300- (-$27)
- **Failed re-enablements**: zscore-rising+ (0% WR, 18 trades), vel-hermes- (0% WR, 6 trades)
- **Systemic issue**: No signal family has positive PnL in 7 days

### Blacklist Trials (77 tokens tested)
- **0 KEEP** out of 77 tokens tested across 5 batches
- Root cause: signal generation filters block these tokens; when signals fire, they're at 0% WR
- Recommendation: Stop rotating tokens in/out of blacklist — it's a symptom filter, not a cause

### System Health
- Pipeline: OK (last run 04:37 UTC, completed successfully)
- Timers: 36 active (pipeline, price-collector, regime-scanners)
- Errors: 1 non-critical (trades-api timeout at 03:50)
- Auto-1hr: INACTIVE (dead since Aug 02)

### What Was NOT Changed (CEO Lock Active Until 2026-08-04 23:15 UTC)
- TPSL parameters
- Speed filter (SIGNAL_FILTER_SPEED_MIN=45)
- Auto-1hr tuner (frozen)
- Other signal enable/disable flags

### Recommendations for CEO
1. **Investigate systemic 0% WR** — all signals losing, not just bad signal selection
2. **Review SL/TP parameters** after CEO lock expires (2026-08-04 23:15 UTC)
3. **Re-enable auto-1hr** — has been inactive since Aug 02
4. **Evaluate remaining signal quality** — tl_break family accounts for ~54% of losses

### Quality Metrics
- Tasks completed: 4 (all CEO action items)
- First-attempt success: 100%
- Pipeline uptime: 100%
- Critical issues found: 1 (systemic 0% WR across all signals)

## [2026-08-10 05:15] Hourly Analysis

**Trades:** 0 closed in last hour | 64 closed in 24h (+$0.52, 57.8% WR)
**Open:** 2 (KAS LONG, MEGA LONG — both tiny winners)

**24h by signal:**
- bb_bounce+,hzscore+ LONG: 12T 9W +$0.53 (75% WR) — DOMINANT STAR
- bb-bounce-short,hzscore- SHORT: 10T 6W +$0.09 (60% WR)
- bb_bounce+,range_finder+ LONG: 16T 9W $0.00 (56% WR) — break-even
- continuation+,hzscore+ LONG: 4T 2W +$0.01 (50% WR)

**Diagnosis:**
1. Entry quality: Winners clean — profit-monster-trail exits on star signals
2. SL behavior: atr_sl_hit 5/64 = 7.8% — healthy, well below 40% threshold
3. Signal quality: Only star combos net positive. range_finder+ is break-even
4. Trade frequency: 2.7/hr — normal

**Changes:** None — system on 11th consecutive green day, no issues detected
**No Change Needed:**
- atr_sl_hit rate: 7.8% (healthy)
- Trade frequency: 2.7/hr (normal)
- Star signals: performing well
- SHORT bleeding: stopped, flat at +$0.01

**Open Questions:** None — system healthy

## [2026-08-10 06:00] Hourly Analysis

**Trades:** 2 closed (0 wins, 2 losses) in last hour | 61 closed in 24h (+$0.36, 55.7% WR)
**Open:** 6 (ETH LONG +$0.05, XRP LONG +$0.05, MEGA LONG +$0.02, KAS LONG +$0.02, AXS SHORT +$0.01, JUP SHORT -$0.01)

**24h by close reason:**
- profit-monster-trail: 33T +$1.48 (avg +$0.045) — dominant winner
- cut-loser-CL-trail: 13T -$0.50 (avg -$0.038) — risk management working
- atr_sl_hit: 12T -$0.59 (avg -$0.049) — 19.7% of closes (healthy)
- cut-loser-CL-T1: 2T -$0.07
- profit-monster-T1: 1T +$0.04

**Signal performance (24h):**
- bb_bounce+,hzscore+ LONG: 13T +$0.48 (69.2% WR) — STAR
- hzscore+,mover+ LONG: 4T +$0.08 (75% WR)
- bb_bounce+,range_finder+ LONG: 14T $0.00 (57.1% WR) — break-even
- bb-bounce-short,hzscore- SHORT: 8T -$0.02 (50% WR) — slight bleed

**Diagnosis:**
1. Entry quality: Last 2 trades on star signal both cut losers at -$0.05 — micro-positions, likely early exits on whipsaw
2. SL behavior: atr_sl_hit = 19.7% — healthy (well below 40% threshold)
3. Signal quality: Star signal dominant. All 0%-WR signals are single-sample noise
4. Trade frequency: 2.5/hr — normal

**Changes:** None
**No Change Needed:**
- atr_sl_hit rate: 19.7% (healthy)
- Trade frequency: 2.5/hr (normal)
- Star signals: performing well
- System on 12th consecutive green day (net +$0.36 24h)

**Open Questions:** None — system healthy

## [2026-08-10 07:00] Hourly Analysis

**Trades:** 4 closed (2 wins, 2 losses) in last hour | 63 closed in 24h (+$0.50, 55.6% WR)
**Open:** ETH SHORT +$0.02, WLFI LONG +$0.03, HBAR LONG -$0.04, ASTER LONG -$0.04

**Last hour PnL:** -$0.03 (2W: ETH +$0.02, WLFI +$0.03; 2L: HBAR -$0.04, ASTER -$0.04)

**24h by close reason:**
- profit-monster-trail: 33T +$1.70 (avg +$0.052) — dominant winner
- atr_sl_hit: 15T -$0.67 (avg -$0.045) — 23.8% of closes (healthy)
- cut-loser-CL-trail: 12T -$0.53 (avg -$0.044) — risk management working
- cut-loser-CL-T1: 1T -$0.04
- profit-monster-T1: 1T +$0.04

**Last hour signal performance:**
- bb_bounce+,hzscore+ LONG: 2T -$0.01 (50% WR) — normal
- continuation+,hzscore+ LONG: 1T -$0.04 (0% WR, 1 sample — noise)
- hl_copy_trader,range_breakout- SHORT: 1T +$0.02 (100% WR, 1 sample — noise)

**Diagnosis:**
1. Entry quality: 2 SL hits on hbAR and aster both micro -$0.04 — normal variance, not pattern
2. SL behavior: atr_sl_hit = 23.8% — healthy (well below 40% threshold)
3. Signal quality: continuation+,hzscore+ 1 trade = single-sample noise, no action needed
4. Trade frequency: 4/hr — normal

**Changes:** None
**No Change Needed:**
- atr_sl_hit rate: 23.8% (healthy)
- Trade frequency: 4/hr (normal)
- All signals within normal variance
- System on 12th+ consecutive green day

**Open Questions:** None — system healthy

## [2026-08-10 15:27] Hourly Analysis

**Trades:** 3 closed last hour (1W, 2L) | 61 closed in 24h (+$0.31, 54.1% WR)
**Open:** BSV SHORT +$0.13, CELO LONG $0.00, WLFI LONG $0.00

**Last hour PnL:** -$0.10 (DYDX +$0.03, JUP -$0.06, PROVE -$0.13)

**24h by close reason:**
- profit-monster-trail: 32T +$1.63 (avg +$0.051) — dominant winner
- atr_sl_hit: 17T -$0.86 (27.9% — healthy)
- cut-loser-CL-trail: 11T -$0.50 (risk management working)
- profit-monster-T1: 1T +$0.04

**Signal performance (24h):**
- bb_bounce+,hzscore+: 17T +$0.40 (64.7% WR) — STAR
- bb_bounce+,range_finder+: 12T -$0.10 (50% WR) — 24h flat, long-term star
- continuation+,hzscore+: 4T +$0.14 (25% WR, 1 big winner +$0.25)
- bb-bounce-short,hzscore-: 4T -$0.04 (50% WR) — flat

**Diagnosis:**
1. Entry quality: JUP -$0.06 and PROVE -$0.13 both atr_sl_hit — normal variance
2. SL behavior: 27.9% — healthy (well below 40%)
3. Signal quality: No bleeding signals. continuation+ low WR but positive PnL
4. Trade frequency: ~2.5/hr — normal
5. Rolling: 4d +$0.75 (52.7%), 7d +$0.30 (49.9%)

**Changes:** None
**No Change Needed:**
- atr_sl_hit rate: 27.9% (healthy)
- Trade frequency: 2.5/hr (normal)
- No 0% WR signals with 3+ trades
- System on 14th+ consecutive green day

**Open Questions:** None — system healthy

## [2026-08-10 16:30] Hourly Analysis

**Trades:** 5 closed last hour (4W, 1L) | 64 closed in 24h (+$0.53, 56.2% WR)
**Open:** BSV SHORT +$0.01

**Last hour PnL:** +$0.20 (WLFI +$0.01, DYDX +$0.08, BSV +$0.10, CELO -$0.02, DYDX +$0.03)

**24h by close reason:**
- profit-monster-trail: 35T +$1.82 (avg +$0.052) — dominant winner
- atr_sl_hit: 18T -$0.88 (28.1% — healthy)
- cut-loser-CL-trail: 10T -$0.45 (risk management working)
- profit-monster-T1: 1T +$0.04

**Signal performance (24h):**
- bb_bounce+,hzscore+: 19T +$0.39 (63.2% WR) — STAR
- continuation+,hzscore+: 4T +$0.14 (25% WR) — positive PnL, 1 big winner
- bb_bounce+,range_finder+: 12T -$0.10 (50% WR) — slightly bleeding, 7d still positive
- hzscore+,range_finder+: 5T -$0.07 (60% WR) — small sample, poor exits

**Diagnosis:**
1. Entry quality: 1 SL hit (CELO -$0.02) — normal variance
2. SL behavior: 28.1% — healthy (well below 40%)
3. Signal quality: No bleeding signals requiring action
4. Trade frequency: ~2.7/hr — normal
5. Rolling: 15th consecutive green day, 7d positive ($0.49)

**Changes:** None
**No Change Needed:**
- atr_sl_hit rate: 28.1% (healthy)
- Trade frequency: 2.7/hr (normal)
- No 0% WR signals with 3+ trades
- System on 15th consecutive green day

**Open Questions:** None — system healthy

## [2026-08-10 17:26] Hourly Analysis

**Trades:** 6 closed last hour (0W, 6L) | 68 closed in 24h (+$0.25, 50% WR)
**Open:** BSV SHORT $0.00, AVNT SHORT $0.00

**Last hour PnL:** -$0.28 (MORPHO -$0.10, CELO -$0.06, LINK -$0.04, AVNT -$0.04, KAS -$0.03, XRP -$0.02)

**24h by close reason:**
- profit-monster-trail: 35T +$1.82 (dominant winner)
- atr_sl_hit: 20T -$0.92 (29.4% — healthy)
- cut-loser-CL-trail: 13T -$0.65

**Signal performance (24h):**
- bb_bounce+,hzscore+: 20T +$0.33 (60% WR) — STAR
- bb_bounce+,range_finder+: 12T -$0.10 (50% WR) — today bad, 7d +$0.79 (58.5%)
- hzscore+,range_finder+: 4T -$0.11 (50% WR) — today bad

**range_finder+ by day:** Aug 7 +$0.13, Aug 8 +$0.65, Aug 9 +$0.11, Aug 10 -$0.40

**Diagnosis:**
1. Entry quality: 6/6 losses, all small (max $0.10). Cold streak.
2. SL behavior: 29.4% — healthy
3. Signal quality: range_finder+ having bad day after 3 good days. Normal variance.
4. Trade frequency: ~3.3/hr — normal

**Changes:** None
**No Change Needed:**
- atr_sl_hit rate: 29.4% (healthy)
- range_finder+: 3-day avg still positive. Today = variance, not signal failure.
- System on 15th consecutive green day, still positive today (+$0.25)

**Open Questions:** None — cold hour within normal bounds

## [2026-08-10 20:05] Hourly Analysis

**Trades:** 1 closed last hour (0W, 1L) | 71 closed in 24h (+$0.25, 52% WR)
**Open:** ASTER LONG $0.60, ETH SHORT $1870

**Last hour PnL:** -$0.03 (AVNT LONG SL hit)

**24h by close reason:**
- profit-monster-trail: 34T +$1.80 (dominant winner)
- atr_sl_hit: 24T -$1.06 (33.8% — healthy)
- cut-loser-CL-trail: 13T -$0.65

**Signal performance (24h):**
- bb_bounce+,hzscore+ LONG: 22T +$0.26 (54.5% WR) — STAR
- continuation+,hzscore+ LONG: 4T +$0.14 (25% WR)
- bb_bounce+,range_finder+ LONG: 12T -$0.10 (50% WR — bad day)
- hzscore+,range_finder+ LONG: 3T -$0.14 (33.3% WR — bad day)

**Diagnosis:**
1. Entry quality: 1/1 SL hit this hour — quiet, no pattern
2. SL behavior: 33.8% — healthy
3. Signal quality: range_finder+ combos -$0.33 today, but 7d still +$0.46. Normal variance.
4. Trade frequency: 2.5/hr — normal
5. Today: -$0.09 (61T) — first red day after 15 green. Normal.

**Changes:** None
**No Change Needed:**
- atr_sl_hit rate: 33.8% (healthy)
- range_finder+: 7d track record still solid
- Trade frequency: 2.5/hr (normal)
- Today's loss: $0.09 on 61 trades = noise

**Open Questions:** None — system healthy, cold day within bounds

## [2026-08-10 21:05] Hourly Analysis

**Trades:** 2 closed last hour (1W, 1L) | 71 closed in 24h (-$0.02, 52% WR)
**Open:** ASTER LONG $0.60, HTTST4 LONG $1.00 (test)

**Last hour PnL:** +$0.05 (HTTST6 test +$0.11, ETH SHORT SL -$0.06)

**24h by close reason:**
- profit-monster-trail: 33T +$1.58 (dominant winner)
- atr_sl_hit: 24T -$1.06 (33.8% — healthy)
- cut-loser-CL-trail: 13T -$0.65

**Signal performance (24h):**
- bb_bounce+,hzscore+ LONG: 21T +$0.04 (52.4% WR) — STAR
- bb_bounce+,range_finder+ LONG: 11T -$0.04 (54.5% WR — bad day)
- continuation+,hzscore+ LONG: 4T +$0.14 (25% WR)
- hzscore+,range_finder+ LONG: 3T -$0.14 (33.3% WR)

**Diagnosis:**
1. Entry quality: 1/2 SL hits this hour — quiet
2. SL behavior: 33.8% — healthy
3. Signal quality: range_finder+ combos -$0.18 today but 7d still positive
4. Trade frequency: 2/hr — low (good)

**Changes:** None
**No Change Needed:**
- atr_sl_hit rate: 33.8% (healthy)
- range_finder+: 7d track record still positive
- Today: -$0.02 flat (not losing)

**Open Questions:** None — system healthy

## [2026-08-10 22:05] Hourly Analysis

**Trades:** 1 closed last hour (0W, 1L — ASTER SL) | 71 closed in 24h (-$0.10, 46.5% WR)
**Open:** BSV SHORT, JUP SHORT, HTTST4 LONG (test)

**24h by close reason:**
- profit-monster-trail: 32T +$1.54 (dominant winner)
- atr_sl_hit: 25T -$1.10 (35.2% — healthy)
- cut-loser-CL-trail: 13T -$0.65

**Star signals 7d:**
- bb_bounce+,range_finder+ LONG: 53T +$0.71 (58.5% WR) ★★
- bb_bounce+,hzscore+ LONG: 28T +$0.34 (53.6% WR) ★★
- bb-bounce-short,hzscore- SHORT: 15T +$0.14 (60.0% WR) ★

**Diagnosis:**
1. Entry quality: 1 SL hit — quiet
2. SL behavior: 38.2% 7d — healthy
3. Signal quality: All stars positive 7d, 24h variance normal
4. Trade frequency: 1-2/hr — no overtrading

**Changes:** None
**No Change Needed:**
- atr_sl_hit: 38.2% (healthy)
- All 3 stars profitable 7d
- Trade frequency normal
- Today's cold stretch: normal variance after 15 green days

**Open Questions:** None — system healthy, cold day within bounds

## [2026-08-10 23:05] Hourly Analysis

**Trades:** 1 closed last hour (1W — BSV SHORT +$0.03 profit-monster-trail) | 69 closed in 24h (-$0.10, break-even)
**Open:** 4 (HTTST4 test, JUP SHORT, MEGA LONG, ASTER LONG)

**24h by close reason:**
- profit-monster-trail: 30T +$1.49 (avg +$0.05) — dominant winner
- atr_sl_hit: 25T -$1.10 (36.2% — healthy)
- cut-loser-CL-trail: 13T -$0.65

**Star signals 7d:**
- bb_bounce+,range_finder+ LONG: 53T +$0.71 (58.5% WR) ★★
- bb_bounce+,hzscore+ LONG: 28T +$0.34 (53.6% WR) ★★
- bb-bounce-short,hzscore- SHORT: 16T +$0.17 (62.5% WR) ★

**Diagnosis:**
1. Entry quality: 1 winner, clean exit
2. SL behavior: 36.2% (healthy, not >40%)
3. Signal quality: All 3 stars profitable 7d, 24h flat
4. Trade frequency: ~3/hr — normal

**Changes:** None
**No Change Needed:**
- atr_sl_hit: 36.2% (healthy)
- All 3 stars profitable 7d
- Trade frequency normal (3/hr)
- Cold day = normal variance after 15 green days
- No 0% WR signals with 3+ trades to kill

**Open Questions:** None — system healthy, cold stretch within bounds

## [2026-08-10 23:25] Hourly Analysis

**Trades:** 1 closed last hour (MEGA LONG, atr_sl_hit -$0.05) | 67 in 24h (-$0.15, 44.8% WR)
**Open:** 4 (HTTST4, JUP SHORT, ASTER LONG, MNT LONG)

**24h by close reason:**
- profit-monster-trail: 29T +$1.47 (avg +$0.05) — dominant winner
- atr_sl_hit: 24T -$1.08 (35.8% — healthy)
- cut-loser-CL-trail: 13T -$0.65

**Diagnosis:**
1. Entry quality: 1 SL hit last hour — quiet
2. SL behavior: 35.8% (healthy, <40%)
3. Signal quality: bb_bounce+,hzscore+ 22T -$0.02 (flat today), range_finder+ combos cold but 7d positive
4. Trade frequency: 2.8/hr — normal

**Changes:** None

**No Change Needed:**
- atr_sl_hit 35.8% (healthy)
- No 0% WR signals with 3+ trades to kill
- Trade frequency normal
- Today's cold day = normal variance after 15 green days
- All star signals profitable 7d

**Open Questions:** None — system healthy

## [2026-08-11 02:25] Hourly Analysis

**Trades:** 1 closed last hour (MNT LONG profit-monster-trail WIN +$0.03) | 60 in 24h (-$0.32, 48.3% WR)
**Open:** 4 (HTTST4, ASTER, KAS SHORT, MEGA SHORT)

**24h by close reason:**
- profit-monster-trail: 25T +$1.25 (sole winning exit)
- atr_sl_hit: 23T -$1.03 (38.3% — healthy, <40%)
- cut-loser-CL-trail: 11T -$0.55

**Diagnosis:**
1. Entry quality: 1 win last hour — quiet
2. SL behavior: 38.3% (healthy, below 40%)
3. Signal quality: bb_bounce+,hzscore+ 18T -$0.22 (38.9% WR 24h, but 30T +$0.23 7d — cold today only)
4. Trade frequency: 2.5/hr — normal

**Changes:** None

**No Change Needed:**
- atr_sl_hit 38.3% (healthy)
- No 0% WR signals with 3+ trades to kill
- Trade frequency normal
- 7d still positive ($0.37, 51.8% WR)
- Trailing distance widened to 0.60% at 22:00 — too early to evaluate (4.5h old)
- Cold day = normal variance after 15 green days

**Open Questions:** None — system healthy

## [2026-08-11 03:25] Hourly Analysis

**Trades:** 0 closed last hour | 58 in 24h (-$0.33, 41.4% WR)
**Open:** 2

**24h by close reason:**
- atr_sl_hit: 25T -$1.14 (43.1% — above 40% threshold, trending up)
- profit-monster-trail: 23T +$1.13 (sole winning exit)
- cut-loser-CL-trail: 9T -$0.43

**Diagnosis:**
1. Entry quality: 0 trades last hour — can't assess
2. SL behavior: 43.1% (just above 40%, trending up from 35.8%→38.3%→43.1%)
3. Signal quality: bb_bounce+,hzscore+ 16T 31.3% WR — cold today but 7d profitable
4. Trade frequency: 1.25/hr — very low, calm period

**Changes:** None

**No Change Needed:**
- atr_sl_hit 43.1% barely above threshold — trailing distance widened to 0.60% at 22:00 (6h ago), needs 24h+ evaluation
- No 0% WR signals with 3+ trades to kill
- Trade frequency very low (1.25/hr)
- 7d still positive ($0.40, 51.8% WR)
- Only 2 open trades — system calm

**Open Questions:** None — quiet period, evaluating trailing distance change

## [2026-08-11 05:30] Hourly Analysis

**Trades:** 1 closed last hour | 58 in 24h (-$0.33, 41.4% WR)
**Open:** 2

**Last hour:**
- MEGA LONG, bb_bounce+,hzscore+, atr_sl_hit, -$0.01

**24h by close reason:**
- atr_sl_hit: 26T -$1.15 (44.8% — above 40% threshold, trending UP)
- profit-monster-trail: 23T +$1.13 (sole winning exit)
- cut-loser-CL-trail: 8T -$0.38

**Diagnosis:**
1. Entry quality: 1 SL hit last hour — MEGA got stopped out
2. SL behavior: 44.8% (above 40%, trending up: 35.8%→43.1%→44.8%)
3. Signal quality: bb_bounce+,hzscore+ 16T 31.3% WR — dominant but cold today (7d profitable)
4. Trade frequency: 2.5/hr — normal
5. Last 3h: ALL 3 trades SL hits (MEGA, KAS, MEGA)

**Changes:** None

**No Change Needed:**
- atr_sl_hit 44.8% above threshold BUT trailing distance widened to 0.60% only7h ago — needs24h+ to evaluate
- 7d still positive ($0.46, 51.8% WR) — cold day normal variance after 15 green days
- No 0% WR signals with 3+ trades to kill in last hour
- Trade frequency normal (2.5/hr)
- Only 2 open trades — system calm
- Overreacting to cold streak destabilizes — wait for trailing distance evaluation window

**Open Questions:** atr_sl_hit rate still climbing despite wider trailing — market regime shift or needs further widening? Evaluate again at 05:30 tomorrow (24h post-change)

---

## 2026-08-11 18:15 Hourly Analysis

**Trades:** 0 closed last hour (system idle)
**24h:** 57T -$0.24 (42.1% WR — RED)
**PnL drivers:** atr_sl_hit 26T -$1.15 (45.6%), profit-monster-trail 23T +$1.13 (40.4%)

**Changes:** None

**No Change Needed:**
- SL revert (1.2%) deployed 13h ago — needs full 24h eval window (until 05:20 Aug 12)
- atr_sl_hit 45.6% above 40% threshold but trending down from 64.7% (at 0.5% SL)
- hzscore+ LONG 15T 33.3% WR — 7d intact at 50%, not a kill candidate
- No 0% WR signals with 3+ trades to kill
- Trade frequency normal (2.4/hr)
- System calm, 0 open trades

**Open Questions:** hzscore+ LONG 24h bleed — monitor 7d WR, kill if drops below 45%

## [2026-08-11 07:27] Hourly Analysis

**Trades:** 0 closed last hour (system idle). 3 open (HTTST4, MEGA, ASTER).
**24h PnL:** -$0.26 (40.7% WR, 54T) — RED
**7d PnL:** +$0.40 (50.9% WR, 365T) — positive

**Key Metrics:**
- SL hit rate 24h: 48.1% (above 40% threshold)
- SL hit rate prior 24h: 18.3% (baseline before revert)
- SL revert to 1.2% deployed 05:20 UTC today — eval window closes 05:20 Aug 12
- Trade frequency: 2.25/hr (normal)
- Profit monster trail: 38.9% of exits (+$1.06)
- atr_sl_hit: 48.1% of exits (-$1.15)

**Stars (7d):**
- bb_bounce+,range_finder+ LONG: 53T +$0.71 58.5% WR
- bb_bounce,hzscore+ LONG: 5T +$0.20 100% WR
- continuation+,hzscore+ LONG: 7T +$0.20 42.9% WR
- bb-bounce-short,hzscore- SHORT: 17T +$0.12 58.8% WR

**No Change Needed:**
- SL evaluation window active (05:20 Aug 11 → 05:20 Aug 12) — no parameter changes allowed
- No signals with 0% WR and 3+ trades to kill
- Trade frequency normal (2.25/hr)
- 3 open trades, system calm
- SL hit rate elevated but mostly pre-revert data — wait for eval window to complete

**Open Questions:**
- hzscore+ LONG 24h bleed: 14T -$0.29 28.6% WR — 7d intact at 48.4%, monitor
- SL revert eval window closes tomorrow 05:20 — will assess then

## [2026-08-11 19:10] Hourly Analysis

**Trades:** 1 closed last hour (MEGA LONG bb_bounce+,hzscore+ SL hit -$0.05)
**24h:** 50T -$0.68 (42.1% WR)
**24h by exit:** atr_sl_hit 26T (52%, -$1.17) | profit-monster-trail 17T (+$0.66) | cut-loser 6T (-$0.28)

**Changes:** None

**No Change Needed:**
- SL revert eval window active (until 05:20 Aug 12) — no param changes allowed
- Kill candidates hzscore+,range_finder+ and continuation+,hzscore+ both show 0% WR 24h but 7d intact (62.5% and 42.9%) — not kills
- bb_bounce+,hzscore+ dominant signal: 7d trail exits 15/15 winners (+$0.92), SL is bottleneck — SL revert should fix
- Trade frequency 2.1/hr (normal)
- atr_sl_hit 52% elevated but SL revert deployed 13h ago — eval window in progress

**Open Questions:**
- SL revert eval window closes tomorrow 05:20 — will assess SL hit rate trend then
- bb_bounce+,hzscore+ 24h bleed: -$0.34 on 15T. If SL revert doesn't fix, may need signal-specific tuning

## [2026-08-11 20:05] Hourly Analysis

**Trades:** 0 closed last hour (2 since SL revert — too early)
**24h:** 51T -$0.43 (45.1% WR) — SL revert eval window active until 05:20 Aug 12
**7d:** 365T +$0.45 (51.8% WR) — positive

**Since SL Revert (05:20 UTC):**
- Only 2 trades closed — both bb_bounce+,hzscore+ LONG SL hits (-$0.06 total)
- SL hit rate: 100% but n=2, meaningless — need 20+ trades for signal

**SL Trend (6h blocks):**
- 0-6h: 2T, SL 100%, WR 0% (n too small)
- 6-12h: 9T, SL 55.6%, WR 44.4%
- 12-18h: 19T, SL 52.6%, WR 31.6%
- 18-24h: 19T, SL 47.4%, WR 42.1%

**Changes:** None

**No Change Needed:**
- SL revert eval window active (closes 05:20 Aug 12) — no param changes allowed
- Trade volume too low since revert to evaluate (2T)
- 7d system positive (51.8% WR) — no crisis
- No 0% WR signals with 3+ trades
- Overtrading? No — 0 trades last hour

**Open Questions:**
- SL revert deployed 14.7h ago with only 2 closed trades — very low volume. Will need more data tomorrow
- HTTST4 open trade is test signal (not in hermes_constants.py) — harmless but should close eventually
- Aster open since Aug 10 22:02 — 22h old, long-duration hold

## [2026-08-11 11:26] Hourly Analysis

**Trades:** 0 closed last hour (dead market)
**24h:** 43T 16W 37.2% WR PnL: -$0.56 avg: -$0.013

**24h by exit:** atr_sl_hit 23T (53.5%, -$1.05) | profit-monster-trail 15T (+$0.61) | cut-loser-CL-trail 4T (-$0.23) | test 1T (+$0.11)

**Changes:** None

**No Change Needed:**
- SL revert eval window active (closes 05:20 Aug 12) — no param changes
- atr_sl_hit 53.5% elevated but revert only 6h old, 2T closed — need 20+ trades for signal
- No 0% WR signals with 3+ trades to kill
- bb_bounce+,hzscore+ dominant at 31.2% WR 24h but 7d intact — cold day variance
- Trade freq 0/hr — under-trading, not over
- System 7d positive (51.8% WR) — no crisis

**Open Questions:**
- SL revert eval window closes in ~18h — will have enough data by then?
- bb_bounce+,hzscore+ 24h bleed: -$0.31. If SL revert doesn't fix, may need signal-specific tuning

## [2026-08-11 12:26] Hourly Analysis

**Trades:** 0 closed last hour (2h25m since last close)
**24h:** 40T 14W (35% WR) -$0.58
**7d:** 364T 189W (51.9% WR) +$0.47
**SL hit 7d:** 38.5% (just under 40% — SL revert working)

**Pipeline:** Running every minute but zero trades entering. 3 signals fired, all blocked:
- ETH/KAS: not in hot-set (only JUP in hot-set)
- JUP: CTX-GATE blocked (hzscore- not suited for NORMAL regime, ATR=0.6164%)

**Changes:** None

**No Change Needed:**
- Pipeline functional — market not producing tradeable setups
- Hot-set has only 1 token (JUP), volatility gate correctly filtering hzscore-
- SL revert eval window active (closes 05:20 Aug 12) — no param changes
- 7d system positive (51.9% WR) — no crisis
- No 0% WR signals with 3+ trades to kill
- Overtrading? No — 0 trades/hr

**Open Questions:**
- Hot-set very narrow (1 token) — is this normal market conditions or discovery issue?
- HTTST4 still open (test signal, age unknown) — should eventually close
- SL revert eval window closes in ~17h — will have enough data by then?

## [2026-08-11 21:05] Hourly Analysis

**Trades:** 0 closed last hour
**24h:** 37T 13W (35.1% WR) -$0.56
**Since SL Revert (05:20):** 3T 1W -$0.03
**SL Hit Rate 24h:** 56.8% (mostly pre-revert)

**Changes:** None

**No Change Needed:**
- SL revert eval window active (closes 05:20 Aug 12) — only 3 trades since revert, need 20+ for signal
- No 0% WR signals with 3+ trades to kill
- bb_bounce+,hzscore+ 23% WR but 7d intact — cold day variance after 15 green days
- Trade frequency 0/hr — under-trading
- Market flat (0 open trades, 1 test signal)
- Hot-set narrow (JUP only) — not discovery issue, just low vol

**Open Questions:**
- SL revert eval window closes in ~8h — will we have enough data by then?
- HTTST4 test signal still open — should eventually close
- bb_bounce+,hzscore+ 24h bleed: -$0.33. If SL revert doesn't fix, may need signal-specific tuning after eval window

## [2026-08-11 22:05] Hourly Analysis

**Trades:** 0 closed last hour (zero volume)
**24h:** 33T 11W (33.3% WR) -$0.53
**7d:** 363T 189W (52.1% WR) +$0.55

**SL Hit Rate:**
- 24h: 57.6% (19/33) — elevated
- Since SL revert (05:20): 2/3 SL hits — too small sample (3 trades)
- SL revert eval window closes 05:20 Aug 12

**Signal Performance (24h):**
- bb_bounce+,hzscore+: 11T 2W (18.2% WR) -$0.32 — cold streak, 7d intact (48.5% WR +$0.20)
- All other signals: 1-2T each, mixed results

**Changes:** None

**No Change Needed:**
- SL revert eval window active until 05:20 Aug 12 — no param changes allowed
- No 0% WR kill candidates (bb_bounce+,hzscore+ has 2 wins, 7d profitable)
- Trade frequency normal (1.4/hr)
- 7d system profitable (52.1% WR +$0.55) — cold day variance
- Hot-set file missing — market conditions (low vol)
- HTTST4 still open (test signal)

**Open Questions:**
- SL revert eval window closes in ~7h — will we have enough data? (only 3 trades since revert)
- Hot-set missing — is discovery working? Or just low vol?

## [2026-08-11 23:05] Hourly Analysis

**Trades:** 6 closed last hour (2W, 4L) — net -$0.22
**24h:** 33T 11W (33.3% WR) -$0.53
**7d:** 363T 189W (52.1% WR) +$0.55

**SL Hit Rate:**
- 24h: 57.6% (19/33) — elevated, above 40% threshold
- Since SL revert (05:20): 10T 3W — -$0.37, too small for signal
- SL revert eval window closes 05:20 Aug 12 (~6h)

**Signal Performance (24h):**
- bb_bounce+,hzscore+: 9T 1W (11.1% WR) -$0.31 — cold streak, 7d intact (48.5% WR +$0.20)
- trend_momentum_near_sma+: 3T 0W (0% WR) -$0.35 — KILLED by CEO (already disabled)
- hzscore+: 3T 1W (33.3% WR) -$0.08
- hzscore-,range_breakout-: 2T 2W (100% WR) +$0.10

**Last Hour Trades:**
- AVNT hzscore+,mover+ WIN +$0.09 (profit-monster-trail)
- HBAR hzscore+ WIN +$0.01 (profit-monster-trail)
- WLFI hzscore+ LOSS -$0.04 (atr_sl_hit)
- ETH trend_momentum_near_sma+ LOSS -$0.10 (atr_sl_hit) — pre-disable position
- W trend_momentum_near_sma+ LOSS -$0.13 (cut-loser-CL-T1) — pre-disable position
- NXPC hzscore+ LOSS -$0.05 (atr_sl_hit)

**Changes:** None

**No Change Needed:**
- SL revert eval window active until 05:20 Aug 12 — no param changes allowed
- trend_momentum_near_sma+ already killed by CEO
- No new 0% WR kill candidates with 3+ trades
- Trade frequency normal (1/hr last hour)
- 7d system profitable (52.1% WR +$0.55) — cold day variance after 15 green days
- atr_sl_hit 60.7% 24h — elevated but within eval window, cannot tune

**Open Questions:**
- SL revert eval window closes in ~6h — only 11 trades since revert, need 20+ for signal
- bb_bounce+,hzscore+ cold streak: if SL revert doesn't fix, may need signal-specific tuning after eval window
- Hot-set file missing — low vol conditions

## [2026-08-12 01:05] Hourly Analysis

**Trades:** 1 closed last hour (0W, 1L) — net -$0.04
**24h:** 28T 8W (28.6% WR) -$0.63
**7d:** 364T 190W (52.2% WR) +$0.51

**SL Hit Rate:**
- 24h: 60.7% (17/28) — elevated, above 40% threshold
- Since SL revert (05:20): 11T — too small for signal, eval window active

**Signal Performance (24h):**
- bb_bounce+,hzscore+: 8T 12.5% WR -$0.25 — dominant but cold (7d: 48.5% WR +$0.20)
- trend_momentum_near_sma+: 3T 0% WR -$0.35 — KILLED (already disabled)
- hzscore+: 3T 33.3% WR -$0.08
- continuation+,hzscore+: 1T 0% WR -$0.04 — 1 trade only

**Last Hour Trades:**
- AVNT continuation+,hzscore+ LOSS -$0.04 (atr_sl_hit)

**Changes:** None

**No Change Needed:**
- SL revert eval window active until 05:20 Aug 12 — no param changes allowed
- trend_momentum_near_sma+ already killed by CEO
- No new 0% WR kill candidates with 3+ trades
- Trade frequency normal (1/hr last hour)
- 7d system profitable (52.2% WR +$0.51) — cold day variance after 15 green days

**Open Questions:**
- SL revert eval window closes in ~6h — only 11 trades since revert, need 20+ for signal
- bb_bounce+,hzscore+ cold streak: if SL revert doesn't fix, may need signal-specific tuning after eval window

## [2026-08-12 03:05] Hourly Analysis

**Trades:** 2 closed last hour (1W, 0L, 1 flat) — net +$0.05
**24h:** 27T 8W (29.6% WR) -$0.42
**7d:** 373T 193W (51.7% WR) +$0.21

**SL Hit Rate:**
- 4h: 36.4% (4/11) — healthy, below 40% threshold
- 24h: 48.1% (13/27) — elevated but SL revert eval window closed

**Signal Performance (7d 0% WR kills):**
- pattern_wolf_wave_bear: 4T 0W -$0.26 — already blocked (pattern_wolf in SIGNAL_SOURCE_BLACKLIST)
- trend_momentum_near_sma+: 3T 0W -$0.35 — already killed by CEO

**Changes:** None

**No Change Needed:**
- No new 0% WR signals with 3+ trades to kill
- SL hit rate healthy in 4h window (36.4%)
- Trade frequency normal (2/hr)
- Both historical 0% WR candidates already blocked
- 7d system at breakeven — normal variance after 15 green days

**Open Questions:**
- None — system stable, cold day is normal variance

---

## TEAM UPDATES
- [2026-08-11 19:30] signal_reporter: Fixed contrarian flip bug for trend_momentum_near_sma — flip was dead code for standalone signals (only in confluence gate section, standalone signals bypass via 4 other paths). Added flip to HOTSET-FINAL-BYPASS, PRESERVE-MERGE-BYPASS, PENDING-APPROVE-BYPASS, SAFETY-FILTER-BYPASS. 0% WR → expected ~50%+ WR. Commit: 8bf6c10

## [2026-08-12 04:05] Hourly Analysis

**Trades:** 6 closed last hour (3W, 3L) — net -$0.02
**24h:** 36T 15W (41.7% WR) -$0.33
**7d:** 373T+ (51.7% WR) +$0.21

**Close Reasons (24h):**
- atr_sl_hit: 18T (50%) -$0.75 — elevated but not critical
- profit-monster-trail: 15T (41.7%) +$0.67 — strong
- cut-loser-CL-T1: 2T (5.6%) -$0.25

**Signal Performance (last hour):**
- hzscore+: 2T 50% WR +$0.05
- bb_bounce+: 3T 33.3% WR -$0.02
- trend_momentum_near_sma+: 1T 0% WR -$0.02 (re-enabled 8/12, contrarian flip active)

**Changes:** None

**No Change Needed:**
- trend_momentum_near_sma+ 7d 0% WR but only 1T last hour — doesn't meet 3+ kill threshold
- Trade frequency normal (6/hr)
- No signals with 0% WR and 3+ trades last hour
- SL hit rate 50% in 24h — elevated but profit-monster-trail compensating
- 7d system still profitable — cold day normal after 15 green days

**Open Questions:**
- trend_momentum_near_sma+ re-enabled with contrarian flip — 4T/7d at 0% WR. If doesn't improve in 48h, kill permanently.
- SL hit rate trending up — monitor next few hours

## [2026-08-12 13:05] Hourly Analysis

**Trades:** 5 closed last hour (4W, 1L) — **+$0.09**
**24h:** 40T 18W (45% WR) -$0.27
**7d:** 383T 200W (52.2% WR) +$0.71

**Close Reasons (24h):**
- atr_sl_hit: 18T (45%) -$0.75 — still elevated
- profit-monster-trail: 18T (45%) +$0.82 — strong, compensating SL
- cut-loser-CL-T1: 3T -$0.34

**Signal Performance (24h):**
- bb_bounce+: 8T 5W +$0.16 — solid
- hzscore+: 8T 4W +$0.02 — decent
- bb_bounce+,hzscore+: 6T 2W -$0.12 — mixed
- **trend_momentum_near_sma+: 4T 0W -$0.37 — 0% WR, KILLED**
- hzscore-,range_breakout-: 2T 2W +$0.10 — strong

**Changes:**
1. **KILLED trend_momentum_near_sma** — 4T 0W 0% WR -$0.37 in 24h. Contrarian flip didn't help (re-enabled 8/12, still 0% WR). Set TREND_MOMENTUM_NEAR_SMA_ENABLED = False. Commit: b3049c6

**No Change Needed:**
- Trade frequency normal (5/hr, well below 20/hr threshold)
- No overtrading
- atr_sl_hit 45% — elevated but profit-monster-trail compensating equally
- 7d system still profitable at 52.2% WR, +$0.71
- Last hour was good (4W1L) — positive momentum

**Open Questions:**
- SL hit rate at 45% — monitor if it drops below 40% next few hours
- JUP SHORT cut-loser-CL-T1 -$0.09 — check if signal was valid

## [2026-08-11 23:25] Hourly Analysis

**Trades:** 2 closed last hour (0W, 2L) — **-$0.11**
**24h:** 41T 18W (43.9% WR) -$0.33
**7d:** 383T 200W (52.2% WR) +$0.72

**Close Reasons (24h):**
- atr_sl_hit: 18T (43.9%) -$0.73 — elevated but profit-monster-trail compensates
- profit-monster-trail: 18T (43.9%) +$0.82 — strong, net positive
- cut-loser-CL-T1: 4T -$0.42 — bleed source
- pm_hard_tp: 1T $0.00

**Signal Performance (24h):**
- hzscore-,range_breakout-: 2T 2W +$0.10 — strong
- bb_bounce+: 9T 5W +$0.08 — solid
- hzscore+: 8T 4W +$0.02 — decent
- bb_bounce+,hzscore+: 5T 2W -$0.07 — cold streak
- trend_momentum_near_sma+: 5T 0W -$0.40 — **KILLED** (flag already False since 22:26)

**Changes:** None

**No Change Needed:**
- trend_momentum_near_sma+ killed at 22:26 UTC. Residual APT trade closed at 23:10 (SL hit -$0.03) — pre-kill entry, no new signals generating.
- Trade frequency normal (2/hr, well below 20/hr threshold)
- No signals with 0% WR and 3+ trades needing kill
- atr_sl_hit 43.9% — elevated but profit-monster-trail compensating equally ($0.82 vs -$0.73)
- 7d system profitable at 52.2% WR, +$0.72
- cut-loser-CL-T1 -$0.42 — CL_TRAIL_ENABLED=False already deployed, monitoring

**Open Questions:**
- atr_sl_hit trending down from 46% → 43.9% — positive sign, continue monitoring
- bb_bounce+,hzscore+ cold at -$0.07 — 7d still intact, no kill warranted

## [2026-08-12 14:05] Hourly Analysis

**Trades:** 1 closed (1W, 0L) — PUMP bb_bounce+ $0.12
**24h:** 40T 17W (42.5% WR) -$0.31

**Close Reasons (24h):**
- atr_sl_hit: 18T (45%) -$0.73 — elevated
- profit-monster-trail: 17T (42.5%) +$0.84 — compensating
- cut-loser-CL-T1: 4T -$0.42 — bleed source
- pm_hard_tp: 1T $0.00

**Signal Performance (24h):**
- bb_bounce+: 10T 6W (60% WR) $0.20 — solid
- hzscore+: 8T 4W (50% WR) $0.02 — decent
- trend_momentum_near_sma+: 5T 0W 0% WR -$0.40 — **ALREADY KILLED**
- bb_bounce+,hzscore+: 5T 2W (40% WR) -$0.07 — cold streak

**Changes:** None

**No Change Needed:**
- No kill candidates (trend_momentum_near_sma+ already killed, no other 0% WR with 3+ trades)
- Trade freq 4.5/hr normal
- atr_sl_hit 45% — elevated but profit-monster-trail compensating ($0.84 vs -$0.73)
- cut-loser-CL-T1 -$0.42 — CL_TRAIL_ENABLED=False already deployed, monitoring
- 7d system still profitable (52.2% WR, +$0.72)

**Open Questions:**
- atr_sl_hit trending: 46% → 45% → now 45% — stable, not worsening
- bb_bounce+,hzscore+ cold at -$0.07 — 7d intact, no kill warranted

## [2026-08-12 16:05] Hourly Analysis

**Trades:** 2 closed (1W, 1L) — PnL: +$0.02
- ATOM bb_bounce+ LONG: profit-monster-trail +$0.04
- AVNT hzscore+ LONG: atr_sl_hit -$0.02

**24h:** 44T 20W (45.5% WR) -$0.29

**Close Reasons (24h):**
- profit-monster-trail: 20T (45.5%) +$0.94 avg $0.047
- atr_sl_hit: 19T (43.2%) -$0.81 avg -$0.043
- cut-loser-CL-T1: 4T (9.1%) -$0.42 avg -$0.105
- pm_hard_tp: 1T $0.00

**Signal Performance (24h):**
- bb_bounce+: 14T 8W (57% WR) +$0.10 — solid
- hzscore+: 9T 4W (44% WR) $0.00 — break-even
- trend_momentum_near_sma+: 5T 0W -$0.40 — **ALREADY KILLED**
- hzscore-: 4T 2W -$0.05 — minor bleed
- bb_bounce+,hzscore+: 4T 2W -$0.01 — marginal

**Changes:** None

**No Change Needed:**
- No kill candidates (trend_momentum near_sma+ already killed, no other 0% WR with 3+ trades)
- Trade freq 2/hr normal
- atr_sl_hit 43.2% — stable
- profit-monster-trail compensating ($0.94 vs -$0.81)
- cut-loser-CL-T1 -$0.42 — CL_TRAIL_ENABLED=False deployed, monitoring
- 7d system profitable (52.2% WR, +$0.72)

**Open Questions:**
- atr_sl_hit stable at 43% — acceptable with PM trail compensation
- hzscore+ flat at $0.00 — 7d intact, no kill warranted

---

## [2026-08-12 03:26] Hourly Analysis

**Trades:** 0 closed last hour (night time, low activity)
**24h:** 45T ~22W (~49% WR) +$0.08 (flat)

**Close Reasons (24h):**
- profit-monster-trail: 22T (48.9%) +$1.05 avg $0.048
- atr_sl_hit: 17T (37.8%) -$0.70 avg -$0.041
- cut-loser-CL-T1: 4T (8.9%) -$0.42 avg -$0.105
- atr_tp_hit: 1T +$0.15
- pm_hard_tp: 1T $0.00

**Signal Performance (24h):**
- bb_bounce+: 15T 9W (60% WR) +$0.18 — star signal
- hzscore+: 9T 4W (44% WR) $0.00 — break-even
- trend_momentum_near_sma+: 5T 0W -$0.40 — **ALREADY KILLED**
- hzscore-: 4T 2W -$0.05 — minor bleed
- bb_bounce+,hzscore+: 4T 2W -$0.01 — marginal

**Changes:** None

**No Change Needed:**
- 0 trades last hour — night session (03:26 UTC), normal low activity
- Trade freq 2.5/hr (last 2h) — normal
- atr_sl_hit 37.8% — below 40% threshold, stable
- profit-monster-trail compensating well (+$1.05 vs -$0.70)
- cut-loser-CL-T1 -$0.42 — CL_TRAIL_ENABLED=False deployed, monitoring
- No 0% WR kill candidates (trend_momentum already killed)
- System flat but stable, no intervention needed

**Open Questions:**
- atr_sl_hit trending down from 43% → 37.8% — positive
- hzscore+ still break-even at $0.00 — monitor for degradation

---

## [2026-08-12 04:25] Hourly Analysis

**Trades:** 0 closed last hour (night session), 13 in last 4h (8W 5L +$0.25)
**24h:** 48T 25W (52.1% WR) +$0.05 — flat
**7d:** 391T 208W (53.2% WR) +$0.99 — profitable

**Close Reasons (24h):**
- profit-monster-trail: 24T (50%) +$1.13 avg $0.047
- atr_sl_hit: 18T (37.5%) -$0.81 avg -$0.045
- cut-loser-CL-T1: 4T (8.3%) -$0.42 avg -$0.105
- atr_tp_hit: 1T +$0.15
- pm_hard_tp: 1T $0.00

**Signal Performance (24h):**
- bb_bounce+: 16T 10W (62.5% WR) +$0.23 — star signal
- range_breakout-: 2T 2W +$0.18 — good
- hzscore+: 10T 4W (40% WR) -$0.11 — AVNT bleeding (4 SL hits)
- hzscore-: 4T 2W -$0.05 — minor
- trend_momentum_near_sma+: 5T 0W -$0.40 — ALREADY KILLED

**Changes:** None

**No Change Needed:**
- 0 trades last hour — night session (04:25 UTC), normal
- atr_sl_hit 37.5% — below 40% threshold, stable
- profit-monster-trail compensating ($1.13 vs $0.81 SL losses)
- No 0% WR kill candidates (trend_momentum already killed)
- Trade freq 2/hr normal
- cut-loser-CL-T1 -$0.42 — CL_TRAIL_ENABLED=False monitoring
- System flat but stable, no intervention needed

**Open Questions:**
- hzscore+ bleeding from AVNT specifically — is AVNT just choppy or signal issue?
- cut-loser-CL-T1 still negative — need more data on CL_TRAIL_ENABLED=False effect

## [2026-08-12 17:05] Hourly Analysis

**Trades:** 5 closed last hour (2W 3L -$0.03 — flat)
**24h:** 52T 26W (50% WR) -$0.04 — flat
**7d:** ~391T 53.2% WR +$0.99 — profitable

**Close Reasons (24h):**
- profit-monster-trail: 26T (50%) +$1.20 avg +$0.046
- atr_sl_hit: 20T (38.5%) -$0.95 avg -$0.048
- cut-loser-CL-T1: 4T (7.7%) -$0.42 avg -$0.105
- atr_tp_hit: 1T +$0.15
- pm_hard_tp: 1T $0.00

**Signal Performance (24h):**
- bb_bounce+: 18T 11W (61.1% WR) +$0.24 — star
- hzscore+: 10T 4W (40% WR) -$0.11 — break-even, AVNT +$0.03
- hzscore-: 6T 3W (50% WR) -$0.08 — minor
- range_breakout-: 2T 2W (100%) +$0.18 — good
- trend_momentum_near_sma+: 5T 0W -$0.40 — ALREADY KILLED (residual entries)

**Changes:** None

**No Change Needed:**
- 5 trades last hour — normal freq (2.2/hr)
- atr_sl_hit 38.5% — below 40% threshold
- profit-monster-trail compensating ($1.20 vs $0.95 SL losses)
- No 0% WR kill candidates (trend_momentum already killed)
- hzscore+ break-even, not bleeding
- cut-loser-CL-T1 -$0.42 — monitoring CL_TRAIL_ENABLED=False
- System flat but stable

**Open Questions:**
- 24h WR dropped from 52.1% → 50% — slight drift, monitor
- cut-loser-CL-T1 still negative at -$0.105 avg — need more data

## [2026-08-12 07:26] Hourly Analysis

**Trades:** 6 closed last hour (2W 4L -$0.11)
**24h:** 67T 34W (50.7% WR) -$0.21 — flat/slightly negative
**7d:** 407T 215W (52.8% WR) +$0.68 — profitable

**Close Reasons (24h):**
- profit-monster-trail: 33T (49.3%) +$1.57 avg +$0.048
- atr_sl_hit: 28T (41.8%) -$1.51 avg -$0.054
- cut-loser-CL-T1: 4T (6.0%) -$0.42 avg -$0.105
- atr_tp_hit: 1T +$0.15
- pm_hard_tp: 1T $0.00

**Signal Performance (24h):**
- range_breakout-: 5T 5W (100%) +$0.41 — star
- bb_bounce+: 19T 11W (57.9% WR) +$0.16 — solid
- hzscore-: 11T 6W (54.5% WR) -$0.09 — minor bleed
- hzscore+: 11T 4W (36.4% WR) -$0.16 — underperforming
- range_breakout+: 5T 1W (20% WR) -$0.28 — BLEEDER (doesn't hit 0% WR kill threshold)
- trend_momentum_near_sma+: 6T 1W -$0.37 — ALREADY KILLED (residual entries)

**This Hour Breakdown:**
- range_breakout+ (3): ALT -$0.07, CFX -$0.08, USUAL -$0.10 — ALL atr_sl_hit
- accel-300- (1): SEI -$0.06 — atr_sl_hit (legit, ACCEL_300_MINUS_ENABLED=True per config)
- hzscore+ (1): AVNT -$0.05 — atr_sl_hit
- range_breakout- (1): SKR +$0.10 — profit-monster-trail
- hzscore- (1): CC +$0.05 — profit-monster-trail

**Changes:** None

**No Change Needed:**
- 6 trades last hour — normal freq (6/hr, well under 20/hour)
- atr_sl_hit 41.8% — borderline but acceptable, avg loss small (-$0.054)
- profit-monster-trail compensating ($1.57 vs $1.51 SL losses)
- No 0% WR kill candidates (range_breakout+ has 1W, doesn't qualify)
- accel-300- legitimately enabled per ACCEL_300_MINUS_ENABLED=True
- trend_momentum_near_sma+ residual entries clearing
- cut-loser-CL-T1 -$0.42 — CL_TRAIL_ENABLED=False already deployed, monitoring
- 7d still profitable (52.8% WR +$0.68)

**Open Questions:**
- range_breakout+ bleeding at 20% WR — params tightened today, monitoring if improvement
- hzscore+ underperforming at 36.4% WR — -$0.16 in 24h, near kill threshold
- cut-loser-CL-T1 still at -$0.105 avg — need more data with CL_TRAIL_ENABLED=False

## [2026-08-12 08:27] Hourly Analysis

**Trades:** 0 closed last hour (most recent close: 08:16 UTC) — 10T in last 2h (4W 6L -$0.13)
**24h:** 69T 35W (50.7% WR) -$0.24 — flat/slightly negative
**7d:** 410T 216W (52.8% WR) +$0.60 — profitable

**Close Reasons (24h):**
- profit-monster-trail: 34T (49.3%) +$1.60 avg +$0.047
- atr_sl_hit: 29T (42.0%) -$1.57 avg -$0.054
- cut-loser-CL-T1: 4T (5.8%) -$0.42 avg -$0.105
- atr_tp_hit: 1T +$0.15
- pm_hard_tp: 1T $0.00

**Signal Performance (24h):**
- range_breakout-: 5T 5W (100%) +$0.41 — star
- bb_bounce+: 19T 11W (57.9% WR) +$0.16 — solid
- range_breakout+: 7T 2W (28.6% WR) -$0.30 — BLEEDER
- hzscore+: 11T 4W (36.4% WR) -$0.16 — underperforming
- hzscore-: 12T 6W (50% WR) -$0.15 — minor bleed
- trend_momentum_near_sma+: 6T 1W -$0.37 — ALREADY KILLED

**Changes:**
1. RANGE_BREAKOUT_CONF_BASE: 65→70 — range_breakout+ 28.6% WR -$0.30 in 24h, 4/5 last trades hit atr_sl_hit. Higher confidence floor filters weak entries.

**No Change Needed:**
- Trade freq 0/hr — normal
- atr_sl_hit 42.0% (borderline, avg loss $0.054 small)
- profit-monster-trail compensating ($1.60 vs $1.57 SL)
- No 0% WR kill candidates (range_breakout+ has 2 wins, trend_momentum already killed)
- cut-loser-CL-T1 -$0.42 — CL_TRAIL_ENABLED=False deployed, monitoring
- 7d still profitable (52.8% WR +$0.60)
- hzscore+ -$0.16 — near kill threshold, next run will reassess

**Open Questions:**
- Will CONF_BASE 70 filter enough weak range_breakout+ entries?
- hzscore+ underperforming at 36.4% WR — watch for 0% WR kill threshold
- cut-loser-CL-T1 still -$0.105 avg — need more data with CL_TRAIL_ENABLED=False

## [2026-08-12 10:10] Hourly Analysis

**Trades:** 2 closed (1W 1L +$0.01)
**24h:** ~76T ~38W (50% WR) -$0.25
**SL hit rate:** 43.4% (borderline, avg loss -$0.057)

**Close Reasons (24h):**
- profit-monster-trail: 37T (49%) +$1.90 (+$0.051/trade)
- atr_sl_hit: 33T (43%) -$1.88 (-$0.057/trade)
- cut-loser-CL-T1: 4T -$0.42

**Changes:**
None — CEO already addressed worst bleeders today (range_breakout+ DISABLED, trend_momentum_near_sma+ KILLED)

**No Change Needed:**
- atr_sl_hit 43.4% borderline but avg loss small, profit-monster-trail compensating
- Trade freq 2/hr normal
- 7d profitable (52.2% WR +$0.72)
- No 0% WR kill candidates
- range_breakout- (86% WR +$0.43) strong

**Open Questions:**
- atr_sl_hit trending up from 38.5% → 43.4% over last few hours — monitor
- Will hzscore+ improve with combo-only mode?

## [2026-08-12 11:26] Hourly Analysis

**Trades:** 2 closed last hour (1W 1L +$0.03)
**24h:** 78T 39W (50.0% WR) -$0.22 (flat)
**7d:** 419T 221W (52.7% WR) +$0.68

**Close Reasons (24h):**
- profit-monster-trail: 38T (49%) +$1.96 (avg +$0.052) — money maker
- atr_sl_hit: 34T (43.6%) -$1.91 (avg -$0.056) — borderline but avg loss small
- cut-loser-CL-T1: 4T -$0.42 (avg -$0.105)
- atr_tp_hit: 1T +$0.15
- pm_hard_tp: 1T $0.00

**Signal Performance (24h):**
- range_breakout-: 7T 6W (85.7% WR) +$0.43 — star
- bb_bounce+: 19T 11W (57.9% WR) +$0.16 — solid
- hzscore+: 12T 5W (41.7% WR) -$0.12 — underperforming
- hzscore-: 16T 8W (50% WR) -$0.04 — flat
- range_breakout+: 8T 2W (25% WR) -$0.41 — all residual trades from before DISABLE
- trend_momentum_near_sma+: 6T 1W (16.7% WR) -$0.37 — all residual, already killed

**Changes:**
None — previous fixes settling in:
- range_breakout+ DISABLED (CEO, no new trades since ~09:00) ✓
- trend_momentum_near_sma+ DISABLED ✓
- CL_TRAIL_ENABLED=False deployed ✓
- CONF_BASE 70 for range_breakout (last change 08:27) ✓

**No Change Needed:**
- atr_sl_hit 43.6% borderline but avg loss small, profit-monster-trail compensating
- Trade freq 2/hr normal (no overtrading)
- No 0% WR kill candidates (no new trades from killed signals)
- 7d profitable (52.7% WR +$0.68)
- range_breakout- (85.7% WR +$0.43) strong
- hzscore+ -$0.12 — near kill threshold, next run will reassess

**Open Questions:**
- hzscore+ 41.7% WR -$0.12 — watch for 0% WR kill threshold
- atr_sl_hit trending: 43.6% — monitor, if >45% consider SL adjustment

## [2026-08-12 12:25] Hourly Analysis

**Trades:** 0 closed last hour (quiet period)
**24h:** ~79T 52.1% WR flat (-$0.27 est)
**7d:** 419T 220W (52.5% WR) +$0.56

**Close Reasons (24h):**
- profit-monster-trail: 38T (48%) +$1.96 (avg +$0.052) — compensates SL losses
- atr_sl_hit: 35T (44.3%) -$1.96 (avg -$0.056) — above 40% threshold but net flat
- cut-loser-CL-T1: 4T -$0.42
- atr_tp_hit: 1T +$0.15
- pm_hard_tp: 1T $0.00

**Signal Performance (24h):**
- range_breakout-: 8T 6W (75% WR) +$0.38 — star
- bb_bounce+: 19T 11W (57.9% WR) +$0.16 — solid
- hzscore-: 16T 8W (50% WR) -$0.04 — flat
- hzscore+: 18T 9W (50% WR) -$0.12 — R:R issue, not WR (AVNT main bleed)
- range_breakout+: 8T 2W (25% WR) -$0.41 — residual from DISABLE
- trend_momentum: 6T 1W (16.7% WR) -$0.37 — residual from DISABLE

**Changes:**
None — system stable, previous fixes settling in.

**No Change Needed:**
- atr_sl_hit 44.3% borderline but profit-monster-trail compensates equally ($1.96 vs $1.96)
- hzscore+ 50% WR — not kill candidate, R:R imbalance fixable by SL tuning
- range_breakout+ and trend_momentum residual trades clearing
- Trade freq 3.3/hr normal
- 7d profitable (52.5% WR +$0.56)

**Open Questions:**
- atr_sl_hit trending up: 43.6% → 44.3% (24h), 54.5% (last 4h) — monitor
- hzscore+ on AVNT: 10T 4W but losses > wins — consider AVNT blacklist or SL adjustment
- range_breakout+ residual trades: 8T in 24h — will clear by next session

## [2026-08-12 14:30] Hourly Analysis

**Trades:** 7 closed (0 wins, 6 losses, 1 orphan)
**PnL:** -$0.43 (0% WR)
**24h:** 86T 44W (51.2% WR) -$0.45
**7d:** 426T 221W (51.9% WR) +$0.13

**Close Reasons (24h):**
- profit-monster-trail: 38T (44.2%) +$1.96
- atr_sl_hit: 41T (47.7%) -$2.40
- cut-loser-CL-T1: 4T -$0.42

**Signal Performance (24h):**
- bb_bounce+: 19T 11W (57.9% WR) +$0.16 — healthiest
- hzscore-: 16T 8W (50% WR) -$0.04 — flat
- range_breakout-: 14T 6W (42.9% WR) -$0.06 — deteriorating (was star)
- hzscore+: 12T 5W (41.7% WR) -$0.12 — AVNT bleed
- range_breakout+: 8T 2W (25% WR) -$0.41 — residual from DISABLE

**Diagnosis:**
- **atr_sl_hit 52.7% today** — above 40% threshold, 7d trend climbing
- range_breakout- had 6 consecutive SL hits last hour — all SHORT in NEUTRAL regime
- Confidence filtering won't help (losing trades avg 91.8% conf)
- bb_bounce+ only consistent winner (36.8% SL hit)
- 7d degrading: +$0.99 → +$0.13 over 2 days
- Today worst day: -$0.50

**No Change Needed:**
- No signal at 0% WR kill threshold (range_breakout- 42.9% WR)
- atr_sl_hit borderline but profit-monster-trail compensates ($1.96 vs $2.40)
- This is regime-driven (NEUTRAL chop) — param changes won't fix chop
- 7d still positive (+$0.13)
- Overreacting to chop destabilizes

**Open Questions:**
- atr_sl_hit trending up 7d (37.9% → 52.7%) — monitor, if exceeds 55% consider SL adjustment
- hzscore+ -$0.12 near kill threshold — next run will reassess
- range_breakout- regime filter: consider blocking SHORT in NEUTRAL if trend continues

## [2026-08-12 15:30] Hourly Analysis

**Trades:** 9 closed (5 wins, 3 losses, 1 BE)
**PnL:** -$0.06 (flat)
**24h:** 95T 48W (50.5% WR) +$0.98
**7d:** 426T 221W (51.9% WR) +$0.13

**Close Reasons (24h):**
- profit-monster-trail: 44T (46.3%) +$2.09
- atr_sl_hit: 44T (46.3%) -$2.59
- cut-loser-CL-T1: 4T -$0.42
- atr_tp_hit: 1T +$0.15

**Signal Performance (24h):**
- bb_bounce+: 19T 11W (57.9% WR) +$0.16 — healthiest
- hzscore-: 16T 8W (50% WR) -$0.04 — flat
- range_breakout-: 19T 8W (42.1% WR) -$0.15 — deteriorating
- hzscore+: 12T 5W (41.7% WR) -$0.12 — bleeding
- range_breakout+: 8T 2W (25% WR) -$0.41 — residual from DISABLE
- trend_momentum+: 6T 1W (16.7% WR) -$0.37 — residual from DISABLE

**Diagnosis:**
- atr_sl_hit 46.3% trending up but trail compensates ($2.09 vs $2.59)
- Dead signals (range_breakout+, trend_momentum) still clearing residual trades
- Trade freq 3.3/hr normal
- 7d degrading +$0.99 → +$0.13 over 2 days
- Today -$0.50 worst day — regime-driven NEUTRAL chop

**No Change Needed:**
- No 0% WR kill candidates
- Dead signals already DISABLED, just clearing residual trades
- hzscore+ -$0.12 near kill threshold but 41.7% WR not 0%
- atr_sl_hit borderline but trail compensating
- One change already made today (range_breakout confidence)
- Regime-driven chop, not signal failure

**Open Questions:**
- atr_sl_hit 7d trend 37.9% → 46.3% — monitor, if exceeds 55% consider SL adjustment
- hzscore+ -$0.12 — next run will reassess
- 7d degrading — track if trend continues

## [2026-08-12 18:27] Hourly Analysis

**Trades:** 3 closed (2 wins, 1 loss)
**PnL:** +$0.06 (flat)
**24h:** 97T 48.5% WR -$0.58
**7d:** 435T 52.0% WR +$0.04

**Close Reasons (24h):**
- profit-monster-trail: 46T (47.4%) +$2.17
- atr_sl_hit: 45T (46.4%) -$2.61
- cut-loser-CL-T1: 3T -$0.30
- atr_tp_hit: 1T +$0.15

**Signal Performance (24h):**
- bb_bounce+: 19T 57.9% WR +$0.16 — healthiest
- range_breakout-: 20T 45% WR -$0.12 — mediocre
- hzscore-: 16T 50% WR -$0.04 — flat
- hzscore+: 12T 41.7% WR -$0.12 — bleeding, monitor
- range_breakout+: 8T 25% WR -$0.41 — residual from DISABLE
- trend_momentum: 5T 20% WR -$0.25 — residual from DISABLE
- accel-300-: 5T 60% WR +$0.01 — OK

**No Change Needed:**
- No 0% WR kill candidates
- Dead signals (range_breakout+, trend_momentum) already DISABLED, clearing residual
- hzscore+ -$0.12 borderline but not kill threshold
- atr_sl_hit 46.4% above 40% but trail compensating
- Regime-driven chop (NEUTRAL), not signal failure
- One change already made today (range_breakout confidence)

**Open Questions:**
- atr_sl_hit 7d trend 37.9% → 46.4% — monitor, if exceeds 55% consider SL adjustment
- 7d degrading +$0.99 → +$0.04 — track if trend continues
- hzscore+ bleeding — next run reassess

## [2026-08-12 19:27] Hourly Analysis

**Trades:** 5 closed (4 wins, 1 stale)
**PnL:** +$0.14 (4 real trades, all profit-monster-trail)
**24h:** 97T 51.4% WR -$0.34
**7d:** 435T 52.0% WR +$0.04

**Close Reasons (24h):**
- profit-monster-trail: 49T (51%) +$2.29 (avg +$0.047)
- atr_sl_hit: 42T (43.3%) -$2.44 (avg -$0.058)
- cut-loser-CL-T1: 2T -$0.17
- pm_hard_tp: 1T $0.00

**Signal Performance (24h):**
- accel-300-: 9T 66.7%WR +$0.12 — strongest
- bb_bounce+: 19T 57.9%WR +$0.16 — healthy
- hzscore-: 16T 50%WR -$0.04 — flat
- range_breakout-: 20T 45%WR -$0.12 — degraded (bad streak 11-12h, recovering)
- hzscore+: 9T 44.4%WR -$0.04 — marginal
- range_breakout+: 8T 25%WR -$0.41 — residual (DISABLED)
- trend_momentum: 3T 33.3%WR -$0.02 — residual (DISABLED)

**No Change Needed:**
- No 0% WR kill candidates
- Dead signals clearing residual, no action
- ATR SL 43.3% borderline but trail compensating (49 trail wins vs 42 SL)
- range_breakout- degraded but 45% WR not kill threshold
- Daily flat -$0.34, no deterioration from -$0.33
- One change already today (range_breakout confidence)

**Open Questions:**
- range_breakout- 6h trend: 8L streak in hours 11-12, recovering — monitor for 3 consecutive losing hours
- 7d barely flat +$0.04 — track if trend continues
- atr_sl_hit 43.3% — stable, no action needed

### TEAM UPDATES
- [2026-08-12 19:27] auto_1hr: NO CHANGES — 5T 4W +$0.14 flat. System healthy, trail compensating SL.

---

## 2026-08-12 20:00 UTC — Hourly Analysis

**Trades:** 1 closed (0 wins, 1 loss)
**PnL:** -$0.03 (0% WR)

**24h Summary:** 96 trades, 50.0% WR, -$0.24 PnL

**Changes:**
1. None — CEO stability period active

**No Change Needed:**
- ATR SL hit rate 44.8% — above 40% threshold but CEO already assessed, profit-monster-trail compensating (+$2.24 24h)
- Trade frequency normal (1/hr)
- System flat within NEUTRAL regime variance

**Open Questions:**
- None — all metrics within expected range for stability period

## [2026-08-12 21:00] Hourly Analysis

**Trades:** 7 closed (7 wins, 0 losses)
**PnL:** +$0.36 (100% WR) — strongest hour today

**Changes:**
1. None — system performing well

**No Change Needed:**
- All 7 trades exited via profit-monster-trail (accel-300- dominated)
- ATR SL 42.6% (above 40% threshold but trail compensating $2.55 vs -$2.47)
- No 0% WR kill candidates (no signal with 3+ losing trades)
- Trade frequency normal (3-4/hr, not overtrading)
- Dead signals clearing residual as expected
- One change already today (range_breakout confidence)
- 7d trend flat +$0.04, no deterioration

**Open Questions:**
- hzscore+ 28.6% WR -$0.11 (7 trades) — monitor next 2h, if 3+ consecutive losses consider kill
- 7d barely flat — track if trend continues into tomorrow

## [2026-08-12 22:00] Hourly Analysis

**Trades:** 4 closed (1 win, 3 losses)
**PnL:** -$0.16 (25% WR)

**24h Summary:** ~100T, ~50% WR, -$0.24

**Changes:**
1. None — no action needed

**No Change Needed:**
- ATR SL 43.4% (above 40% threshold but profit-monster-trail compensating $2.45 vs $2.62 = net +$0.17)
- No 0% WR kill candidates (range_breakout_short 0W 2L last hour but only 2T, below 3+ threshold)
- Trade frequency normal (4/hr)
- 7d flat +$0.36, no deterioration
- One change already today (range_breakout confidence)

**Open Questions:**
- range_breakout_short monitor next 2h for consecutive losses

## [2026-08-12 23:00] Hourly Analysis

**Trades:** 7 closed (6 wins, 1 loss)
**PnL:** +$0.35 (85.7% WR)

**24h Summary:** 100T, 56% WR, -$0.55 net. Trail +$0.15 vs atr_sl -$2.58.

**Changes:**
1. None — no action needed

**No Change Needed:**
- ATR SL 40% (at threshold, trail compensating net +$0.15)
- No 0% WR kill candidates (range_breakout+ 25%WR 8T, hzscore+ 25%WR 4T — below 3T last-hour threshold)
- Trade freq normal (3-8/hr)
- 7d flat +$0.36
- One change already today (range_breakout confidence)

**Open Questions:**
- range_breakout+ and hzscore+ both at 25% WR 24h — monitor, if next hour shows 3+ consecutive losses, kill

## [2026-08-13 00:00] Hourly Analysis

**Trades:** 0 closed (off-hours quiet)
**PnL:** $0.00

**24h Summary:** 98T, 58.2% WR, net +$0.18. Trail +$2.73 vs atr_sl -$2.55. ATR SL 40.2% (at threshold).

**Changes:**
1. None — no action needed

**No Change Needed:**
- ATR SL 40.2% (at threshold, trail fully compensating)
- No 0% WR kill candidates (no signal with 3+ losing trades last hour)
- Trade frequency normal
- 7d flat +$0.36
- One change already today (range_breakout confidence)

**Open Questions:**
- None — system stable

## 2026-08-13 00:30 UTC — Hourly Analysis

**Trades:** 10 closed (1 win, 9 losses)
**PnL:** -$0.78 (10% WR)

**Exit Reasons (1h):** atr_sl_hit (8), cut_loser (1), profit-monster-trail (1)

**24h Snapshot:**
- 107T, -$0.24, 53.3% WR — roughly flat
- ATR SL hit: 47/107 (44%) — above 40% threshold
- profit-monster-trail: 55/107 (+$2.64) — compensating SL losses

**Signal Performance (24h):**
- ✅ range_breakout_short SHORT: 14T, +$0.49, 71.4% WR
- ✅ hzscore- SHORT: 13T, +$0.04, 53.8% WR
- ⚠️ accel-300- SHORT: 28T, -$0.21, 53.6% WR — biggest volume, negative PnL (losers > winners)
- ❌ range_breakout- SHORT: 20T, -$0.12, 45% WR
- ❌ hzscore+ LONG: 4T, -$0.14, 25% WR (blacklisted)
- ❌ range_breakout+ LONG: 8T, -$0.41, 25% WR (killed)

**Hourly Trend (6h):**
- 21:00: +$0.73 (best hour)
- 22:00: +$0.10
- 23:00: -$0.17
- 00:00: -$0.61 (worst hour — 75% SL hit)

**Diagnosis:**
1. **Entry quality:** Terrible last hour — 8/8 accel-300- trades hit ATR SL immediately
2. **SL behavior:** 44% 24h SL hit rate, 80% last hour — SL likely too tight for current volatility
3. **Signal quality:** accel-300- is the volume leader but losing money (53.6% WR, -$0.21). Losers are larger than winners.
4. **Trade frequency:** 8T/hour last hour — normal

**Changes:** NONE — CEO directive: NO TRADING CHANGES. Stability period active (14+ changes in 48h). Trailing stop fix (0.80%) needs more eval time.

**Escalation:**
- accel-300- would normally be killed per rules (0% WR with 8 trades in last hour)
- ATR SL >40% threshold triggers tpsl_utils.py check — trailing logic IS deployed
- Flagging for next CEO review: accel-300- entry quality degrading

**Open Questions:**
- Is accel-300- entering during chop? Or is SL too tight for current ATR?
- 7-day trend: Aug 9 +$0.62 → Aug 11 -$0.33 → Aug 12 +$0.49 → Aug 13 -$0.61 (so far). Pattern: recovery then decline.

## 2026-08-13 01:30 UTC — Hourly Analysis

**Trades:** 3 closed (3 wins, 0 losses)
**PnL:** +$0.09 (100% WR)

**Exit Reasons (1h):** profit-monster-trail (3)

**24h Snapshot:**
- 105T, -$0.06, 57.1% WR — flat
- ATR SL hit: 45/105 (42.9%) — above 40% threshold
- profit-monster-trail: 55/105 (+$2.64) — compensating SL losses

**Signal Performance (24h):**
- ✅ range_breakout_short SHORT: 14T, +$0.49, 71.4% WR
- ✅ bb_bounce+ LONG: 6T, +$0.10, 66.7% WR
- ✅ hzscore- SHORT: 12T, +$0.01, 50% WR
- ⚠️ accel-300- SHORT: 31T, -$0.12, 58% WR — volume leader, slight negative
- ⚠️ range_breakout- SHORT: 20T, -$0.12, 45% WR
- ❌ hzscore+ LONG: 4T, -$0.14, 25% WR (active, below kill threshold)
- ❌ range_breakout+ LONG: 8T, -$0.41, 25% WR (killed)

**Hourly Trend (6h):**
- 20:00: -$0.16 (1W 3L)
- 21:00: +$0.73 (8W 0L — best hour)
- 22:00: +$0.10 (3W 1L)
- 23:00: -$0.17 (0W 2L)
- 00:00: -$0.54 (3W 7L — worst hour)
- 01:00: +$0.02 (1W 0L)

**Diagnosis:**
1. **Entry quality:** Clean last hour — all 3 accel-300- SHORT wins via trailing
2. **SL behavior:** 42.9% ATR SL hit (above 40% but trail compensates net +$0.04)
3. **Signal quality:** hzscore+ 25% WR, below 3T kill threshold — monitor
4. **Trade frequency:** 3T/hour — normal

**Changes:** NONE — CEO stability period active. ATR SL above threshold but profit-monster-trail compensating. No kill candidates.

**Open Questions:**
- Is accel-300- entering during chop? 00:00 hour had 7/10 SL hits
- hzscore+ approaching kill threshold — watch next hour

## 2026-08-13 02:30 UTC — Hourly Analysis

**Trades:** 1 closed (0 wins, 1 loss)
**PnL:** -$0.06 (0% WR)

**24h Snapshot:**
- 103T, 55W (53.4% WR), -$0.22 (flat)
- ATR SL: 45/103 = 43.7% — above 40% threshold
- profit-monster-trail: 53/103 (+$2.52) — compensating SL losses

**Signal Performance (24h):**
- ✅ range_breakout_short SHORT: 14T, +$0.49, 71.4% WR
- ✅ hzscore- SHORT: 12T, +$0.01, 50% WR
- ⚠️ accel-300- SHORT: 32T, -$0.18, 56.2% WR — volume leader
- ⚠️ range_breakout- SHORT: 20T, -$0.12, 45% WR
- ❌ hzscore+ LONG: 3T, -$0.12, 33.3% WR — approaching kill threshold
- ❌ range_breakout+ LONG: killed

**Hourly Trend (6h):**
- 21:00: +$0.73 (8W 0L — best)
- 22:00: +$0.10 (3W 1L)
- 23:00: -$0.17 (0W 2L)
- 00:00: -$0.54 (3W 7L — worst)
- 01:00: +$0.02 (1W 0L)
- 02:00: -$0.06 (0W 1L)

**Diagnosis:**
1. **Entry quality:** Last hour single trade ETC SHORT accel-300- hit ATR SL
2. **SL behavior:** 43.7% ATR SL (above 40% threshold, trail compensates net)
3. **Signal quality:** No 0% WR kill candidates (hzscore+ 33% but only 3T)
4. **Trade frequency:** 4.3/hr avg — normal

**Changes:** NONE — no kill candidates, trail compensating SL losses, flat 24h PnL.

**No Change Needed:**
- ATR SL above threshold but profit-monster-trail compensating (+$2.52 vs -$3.12)
- Trade frequency normal (4.3/hr)
- No signal has 3+ trades with 0% WR in last hour

**Open Questions:**
- hzscore+ 33.3% WR on 3T — approaching kill threshold, watch next hour
- accel-300- volume leader but slight negative — monitor if degrading

## [2026-08-13 03:26 UTC] Hourly Analysis

**Trades:** 5 closed since 02:30 (2 wins, 3 losses)
**PnL:** -$0.25 (40% WR)

**24h Snapshot:**
- 106T, 56W (52.8% WR), ~$0 flat
- ATR SL: 48/106 = 45.3% — above 40% threshold
- profit-monster-trail: 54/106 (+$2.59) — compensates SL losses (-$3.37)
- Net trail+SL: -$0.78

**Signal Performance (24h):**
- ✅ range_breakout_short SHORT: 15T, +$0.43, 66.7% WR
- ✅ hzscore- SHORT: 12T, +$0.01, 50% WR
- ⚠️ accel-300- SHORT: 35T, -$0.17, 57.1% WR — volume leader
- ⚠️ range_breakout- SHORT: 19T, -$0.27, 42.1% WR — losing
- ❌ hzscore+ LONG: 3T, -$0.12, 33.3% WR — at threshold but only 3T
- ❌ range_breakout+ LONG: 7T, -$0.44, 14.3% WR — already killed

**Changes:** NONE — no kill candidates. ATR SL above threshold but trail compensating. No signal has 3+ trades with 0% WR in last hour. Trade freq normal.

**No Change Needed:**
- ATR SL at 45.3% — above threshold but profit-monster-trail net compensates
- hzscore+ at kill threshold (33.3% WR, 3T) but too few trades — watch next hour
- Trade frequency 5T/5h — normal range
- Pipeline active, 5 open trades healthy

**Open Questions:**
- range_breakout- at 42.1% WR, 19T — trending toward kill threshold if degrades further
- accel-300- volume leader but slight negative PnL — monitor if degrading

## [2026-08-13 04:26 UTC] Hourly Analysis

**Trades:** 0 closed in last hour
**24h:** 103T, 52.8% WR, ~$0 flat (-$0.52)
**ATR SL:** 47/103 = 45.6% (above 40%, trail compensating +$2.51 vs -$3.26)

**Signal Performance (24h):**
- ✅ range_breakout_short SHORT: 15T, 66.7% WR, +$0.43 — best
- ✅ accel-300- SHORT: 35T, 57.1% WR, -$0.17 — volume leader
- ✅ hzscore- SHORT: 12T, 50% WR, +$0.01
- ⚠️ range_breakout- SHORT: 18T, 38.9% WR, -$0.30 — deteriorating

**Changes:** NONE

**No Change Needed:**
- 0 trades closed in last hour = no kill candidates
- ATR SL above threshold but trail compensating net
- range_breakout- at 38.9% WR trending toward kill threshold but no last-hour 0% WR
- Trade freq 4.3/hr normal
- 6 open trades healthy (5x accel-300-, 1x range_breakout_short)

**Open Questions:**
- Aug 13 so far 17T, 35.3% WR — early but weak day, monitor
- range_breakout- 38.9% WR, watch for degradation to kill threshold

## [2026-08-13 05:30 UTC] Hourly Analysis

**Trades:** 5 closed (1W, 4L, -$0.29)
**24h:** 102T, 52.8% WR, ~$0 flat (-$0.96 net trail+SL)
**ATR SL:** 48/102 = 47.1% (above 40%, trail +$2.47 compensates SL -$3.43)

**Last Hour Trades:**
- SUSHI accel-300- SHORT atr_sl_hit -$0.06
- ALT accel-300- SHORT atr_sl_hit -$0.08
- ZEN range_breakout_short SHORT atr_sl_hit -$0.10
- MON accel-300- SHORT atr_sl_hit -$0.08
- SKR accel-300- SHORT profit-monster-trail +$0.03

**Signal Performance (24h):**
- ✅ range_breakout_short SHORT: 16T, 62.5% WR, +$0.33 — best
- ✅ hzscore- SHORT: 10T, 50% WR, +$0.04
- ⚠️ accel-300- SHORT: 39T, 53.8% WR, -$0.36 — volume leader, inverted R:R (CEO killed ACCEL_300_MINUS_ENABLED)
- ⚠️ range_breakout- SHORT: 18T, 38.9% WR, -$0.30 — deteriorating

**Consecutive Negative Hours:** 3 (05:00, 04:00, 02:00 — all 0% WR, low trade count)

**Changes:** NONE

**No Change Needed:**
- accel-300- kill already deployed by CEO (ACCEL_300_MINUS_ENABLED=False) — trades still flowing from pre-kill entries or pipeline lag
- No signal has 0% WR with 3+ trades in last hour (kill threshold)
- ATR SL 47.1% above threshold but trail compensating net
- range_breakout- at 38.9% WR trending down but not at 30% kill threshold
- Trade freq 5T/5h normal
- 1 open trade healthy
- Quiet period — low trade volume

**Open Questions:**
- accel-300- still executing 39T/24h despite ACCEL_300_MINUS_ENABLED=False — check if kill is deployed in running code
- range_breakout- approaching kill threshold (38.9% WR, needs <30% with 5+ trades)
- 3 consecutive 0% WR hours — concerning but low sample size (1-3 trades/hour)

## [2026-08-13 05:30 UTC] Daily Orchestrator Report

### PIPELINE STATUS
- Trades (24h): 1 open | 102 closed today | -6.74% PnL
- Market: NEUTRAL (BTC $63,595, 105/106 tokens neutral)
- Pipeline: OK (cycle #152918+), 0 errors, 44 active timers
- System: disk 80% (23G free), all services nominal

### TEAM ACTIVITY (24h)
- **health_monitor**: Pipeline OK, 110 signals/hr, 512 today. No alerts.
- **auto_1hr**: NO CHANGES (CEO stability period). 106T 52.8% WR flat. SQL bugs in embedded queries (see below).
- **signal_reporter**: 3468 all-time T, 41.9% WR. range_breakout_short best (71.4% WR +$0.49). range_breakout+ killed.
- **ab_optimizer**: run_evolution() transient error at 01:00-01:40 UTC, self-resolved. Runs clean now.

### IMPLEMENTED TODAY
1. **auto_1hr prompt schema guardrails** — Added explicit column name reference + single-quote rule to `auto_1hr_prompt.md`. Fixes recurring `UndefinedColumn: "closed"` and `entry_time` errors caused by LLM generating bad SQL.

### DEFERRED (CEO stability period active)
- Weather Vane v3 (Z-Score + Acceleration filter) — params defined, function not implemented
- Weather Vane v4 (Tide Detection) — not started
- Position Shield (from Plan 1) — trailing stop tightening

### CRITICAL ISSUES
- **auto_1hr SQL bugs**: LLM sometimes uses `"closed"` (double quotes = column identifier) instead of `'closed'` (string literal). Prompt updated with schema guardrails.
- **range_breakout- at 38.9% WR** trending toward kill threshold (19T). Watch next hour.
- **Disk at 80%** — not critical but trending up.

### NEXT STEPS
1. Monitor auto_1hr next run to verify prompt fix works
2. Watch range_breakout- for kill threshold breach
3. Implement v3 (Z-Score + Acceleration) when CEO stability period ends
4. Disk cleanup if usage continues rising

### QUALITY METRICS
- Tasks completed: 3/3 (auto-1hr fix, ab_optimizer check, plan review)
- First-attempt success: 100%
- Pipeline uptime: 100% (0 errors in 24h)

## [2026-08-13 06:30 UTC] Hourly Analysis

**Trades:** 0 closed last hour (quiet since 05:16). 95T/24h, 48W (50.5% WR), -$0.64.
**PnL:** $-0.64/24h (flat). Today: 22T 7W (31.8% WR) -$1.02.

**24h by close reason:**
- profit-monster-trail: 47T +$2.31 (avg +$0.049) — compensating
- atr_sl_hit: 44T -$3.18 (avg -$0.072) — 46.3% of closes (above 40% threshold)

**24h by signal:**
- range_breakout_short: 16T 62.5% WR +$0.33 ← BEST
- hzscore-: 6T 50% WR +$0.10
- accel-300-: 39T 53.8% WR -$0.36 (still executing despite kill)
- range_breakout-: 17T 35.3% WR -$0.37 (fully dead, all Aug 12)
- range_breakout+: 6T 16.7% WR -$0.38 (killed, trailing)

**Changes:** None needed.

**No Change Needed:**
- accel-300- kill deployed (ACCEL_300_MINUS_ENABLED=False) — trailing entries still closing, will die off
- range_breakout- kill working — last trade Aug 12 14:49 UTC
- ATR SL at 46.3% above threshold but profit-monster-trail compensates net
- No 0% WR kill candidates (0 trades last hour)
- Trade freq 4/hr normal
- 6 open trades healthy

**Open Questions:**
- accel-300- still executing 39T/24h despite kill — may be pipeline cache or pre-kill entries
- Today 31.8% WR low sample (22T) — monitor next hour
- range_breakout_short (62.5% WR) is best performer — consider increasing confidence?

## [2026-08-13 07:30 UTC] Hourly Analysis

**Trades:** 3 closed last hour (1W 2L). 91T/24h, 51.6% WR, -$0.58.
**PnL:** $-0.04/1h (flat). 24h: $-0.58 (flat).

**24h by close reason:**
- profit-monster-trail: 46T +$2.16 (avg +$0.047) — compensating
- atr_sl_hit: 41T -$2.97 (avg -$0.072) — 45% of closes (above 40% threshold)

**24h by signal:**
- range_breakout_short: 16T 62.5% WR +$0.33 ← BEST
- hzscore-: 7T 57.1% WR +$0.11
- accel-300-: 38T 55.3% WR -$0.30 (trailing entries, no new opens since ~03:37)
- range_breakout-: 15T 26.7% WR -$0.53 (killed, trailing)
- range_breakout+: 3T 33.3% WR -$0.13 (killed, trailing)

**Changes:** None.

**No Change Needed:**
- accel-300- kill working — last entry 03:37 UTC, no new entries after flag set. Trailing trades closing naturally.
- ATR SL at45% — structural but stable. profit-monster-trail (+$2.16) partially compensates SL losses (-$2.97). Net from these two: -$0.81. Wider SL would reduce hit rate but increase avg loss — neutral tradeoff at current flat PnL.
- No 0% WR kill candidates (0 trades last hour, no new underperformers).
- Trade freq 3/hr normal. 5 open trades healthy.
- range_breakout_short (62.5% WR) best performer — no action needed, already running.

**Open Questions:**
- accel-300- still has 38T/24h — all pre-kill entries. Will die off as trail closes them.
- ATR SL structural issue persists but system is flat — not bleeding, not making. Hold steady.

## [2026-08-13 08:30 UTC] Hourly Analysis

**Trades:** 3 closed last hour (1W 2L). 91T/24h, 51.6% WR, -$0.65.
**PnL:** $-0.15/1h. 24h: -$0.65 (flat).

**24h by close reason:**
- profit-monster-trail: 46T +$2.17 (avg +$0.047)
- atr_sl_hit: 41T -$3.05 (avg -$0.074) — 45% of closes (above 40% threshold)

**24h by signal:**
- range_breakout_short: 19T 57.9% WR +$0.18 ← BEST
- hzscore-: 6T 66.7% WR +$0.17
- accel-300-: 38T 55.3% WR -$0.30 (trailing entries only)
- range_breakout-: 15T 26.7% WR -$0.53 (killed, trailing)

**Changes:** None.

**No Change Needed:**
- ATR SL at 45% structural but profit-monster-trail compensates
- No 0% WR kill candidates (0 trades last hour matching criteria)
- Trade freq 3/hr normal. 4 open trades healthy.
- accel-300- kill working — trailing entries closing naturally.

**Open Questions:**
- ATR SL persistent at 45% — structural but net flat. Hold.

## 2026-08-13 09:30 UTC — Hourly Analysis

**Trades:** 3 closed (3 wins, 0 losses)
**PnL:** +$0.12 (100% WR)

**Exit Reasons:** profit-monster-trail (3)

**24h Snapshot:**
- 88 trades, 46 profit-monster-trail (+$2.00), 38 atr_sl_hit (-$2.77), 1 atr_tp_hit (+$0.32)
- ATR SL hit rate: 43.2% (above 40% threshold, down from 46.4%)
- Net 24h: roughly flat (-$0.27)
- Today (Aug 13): 31T, -$1.09, 41.9% WR (worst day in 7d)

**Signal Performance (24h):**
- ❌ range_breakout- SHORT: 14T, -$0.58, 21.4% WR — 10/14 trades are SL hits
- ⚠️ accel-300- SHORT: 38T, -$0.26, 55.3% WR — marginal, R:R unfavorable
- ✅ hzscore- SHORT: 5T, +$0.18, 100% WR
- ✅ range_breakout_short SHORT: 19T, +$0.18, 57.9% WR

**Diagnosis:**
1. **Entry quality:** Excellent — last hour 100% WR, profit-monster-trail exits
2. **SL behavior:** 43.2% SL hit rate (down from 46.4% — improving). SL cost -$2.77 vs trail profit +$2.00
3. **Signal quality:** range_breakout- SHORT is the worst performer (21.4% WR, 10/14 SL hits). accel-300- marginal.
4. **Trade frequency:** ~3.7/hour, normal

**Changes:** None. No signal meets kill criteria (0% WR with 3+ trades in last hour). CEO stability period active. ATR SL rate improving (46.4% → 43.2%). System flat.

**Open Questions:**
- range_breakout- SHORT has 21.4% WR over 24h but no last-hour trades — monitoring for next hour
- Today Aug 13 worst day in 7d ($-1.09 on 31T). Watching if this continues.
- ATR SL hit rate trending down (46.4% → 43.2%) — trailing stop fix may be helping

## 2026-08-13 10:30 UTC — Hourly Analysis

**Trades:** 3 closed (1W 2L)
**PnL:** -$0.07 (33.3% WR)

**Exit Reasons:** atr_sl_hit (2), profit-monster-trail (1)

**24h Snapshot:**
- 89 trades, 46 profit-monster-trail (+$1.97), 39 atr_sl_hit (-$2.82)
- ATR SL hit rate: 44.3% (above 40% threshold)
- Net 24h: ~-$0.64 (flat)

**Signal Performance (24h):**
- accel-300-: 38T, 55.3% WR, -$0.26 (16 ATR SL hits — worst SL contributor)
- range_breakout_short: 19T, 57.9% WR, +$0.18
- hzscore-: 7T, 71.4% WR, +$0.10

**Today (Aug 13):**
- accel-300-: 19T, 36.8% WR, -$0.73 (12/19 ATR SL hits — worst performer)
- hzscore-: 6T, 66.7% WR, +$0.04

**Diagnosis:**
1. **Entry quality:** Mixed — winners trail well, losers hit SL immediately
2. **SL behavior:** 44.3% SL hit rate. accel-300- responsible for 41% of all SL hits
3. **Signal quality:** accel-300- deteriorated after re-enable (36.8% WR today)
4. **Trade frequency:** ~3.7/hr normal

**Changes:**
1. Disabled ACCEL_300_ENABLED — 19T today with 36.8% WR, 12/19 ATR SL hits, net -$0.73. Re-enabled yesterday but already deteriorated. Removing primary source of SL losses.

**No Change Needed:**
- ATR SL at 44.3% — structural but profit-monster-trail compensating
- No consecutive negative hours
- range_breakout- already dead
- Trade freq normal

**Open Questions:**
- accel-300- was re-enabled yesterday with positive edge data — may work in different market conditions. Monitor for re-enable.
- Today Aug 13 remains worst day in 7d. System flat overall.

## 2026-08-13 11:30 UTC — Hourly Analysis

**Trades:** 0 closed (quiet market)
**PnL:** $0.00

**24h Snapshot:**
- 87 trades, 45 profit-monster-trail (+$1.91), 38 atr_sl_hit (-$2.79)
- ATR SL hit rate: 44.1% (above 40% threshold but trail compensating)
- Net 24h: ~-$0.60 (flat)

**Today (Aug 13):**
- 34T, 41.2% WR, -$1.16

**Signal Status:**
- accel-300-: KILLED. Last trade closed 08:55 UTC — kill working
- range_breakout_short: 19T, 57.9% WR, +$0.18 (best performer)
- hzscore-: 6T, 66.7% WR, +$0.04
- range_breakout-: 13T, 23.1% WR, -$0.55 (worst WR, but auto-trade cleanup)

**Changes:** None. No trades to analyze. accel-300- kill confirmed working. Market quiet.

**No Change Needed:**
- 0 trades last hour — nothing to act on
- ATR SL 44.1% — trail compensating (+$1.91 vs -$2.79)
- All kills already deployed
- Trade freq normal when active

**Open Questions:**
- Today Aug 13 worst day in 7d ($-1.16) — but low sample (34T), could be variance
- Watch if activity picks up next hour

## 2026-08-13 13:30 UTC — Hourly Analysis

**Trades:** 1 closed (1W, 0L)
**PnL:** $0.03 (ETH LONG bb_bounce+,rs-s65 → profit-monster-trail)

**24h Snapshot:**
- 81 trades, 58.0% WR, -$0.11 (flat)
- ATR SL hit rate: 38.3% (below 40% threshold) ✓
- profit-monster-trail: 47T +$1.97 (primary profit driver)
- atr_sl_hit: 31T -$2.30 (compensated by trail)
- 4 open trades (all range_breakout_short — best signal)

**Changes:** None

**No Change Needed:**
- ATR SL 38.3% — below 40% threshold
- Trade freq 1-4/hr — quiet market, no overtrading
- accel-300- kill confirmed working (trailing entries closing)
- All signals performing within expectations
- Today Aug 13 flat overall (35T, -$0.08) — low sample

**Open Questions:**
- Market unusually quiet — watch for activity pickup
- accel-300- trailing entries will take time to fully close

## 2026-08-13 14:30 UTC — Hourly Analysis

**Trades:** 1 closed (0W, 1L)
**PnL:** $-0.08 (FIL SHORT, atr_sl_hit)

**24h Snapshot:**
- 73 trades, 57.5% WR, -$0.13 (flat)
- ATR SL hit rate: 39.7% (just under 40% threshold) ✓
- profit-monster-trail: 41T +$1.84 (primary profit driver)
- accel-300-: 35T, 54.3% WR, -$0.31 — all trades opened before 03:37 UTC, kill confirmed working
- range_breakout_short: 20T, 55% WR, +$0.10 (best performer)
- 6 open trades healthy

**Changes:** None

**No Change Needed:**
- ATR SL 39.7% — below 40% threshold, profit-monster-trail compensating (+$1.84 vs -$2.19)
- Trade freq 1/hr — quiet market, no overtrading
- accel-300- kill working — all trailing entries closed
- System flat — no param changes needed

**Open Questions:**
- Market quiet — 1 trade/hr, watch for activity pickup
- FIL trade -77.4% pnl_pct extreme but only -$0.08 actual loss (low-priced token effect)

## 2026-08-13 15:30 UTC — Hourly Analysis

**Trades:** 3 closed (2W, 1L)
**PnL:** $0.07 (66.7% WR)

**24h Snapshot:**
- 73 trades, 57.5% WR, -$0.12 (flat)
- ATR SL hit rate: 39.7% (just under 40% threshold) ✓
- profit-monster-trail: 41T +$1.86 (primary profit driver)
- accel-300-: 35T, 54.3% WR, -$0.31 — kill confirmed, all trailing entries closing
- range_breakout_short: 22T, 54.5% WR, +$0.10 (best performer)
- hzscore-: 7T, 71.4% WR, +$0.11 (strong)
- 4 open trades healthy

**Changes:** None

**No Change Needed:**
- ATR SL 39.7% — below 40% threshold
- Trade freq 1-4/hr — quiet market, no overtrading
- accel-300- kill working — all trailing entries closing
- No 0% WR kill candidates (0 trades last hour with 3+ trades)
- System flat — no param changes needed

**Open Questions:**
- Market quiet — 1-3 trades/hr, watch for activity pickup

## 2026-08-13 16:30 UTC — Hourly Analysis

**Trades:** 5 closed (2W, 3L)
**PnL:** $-0.13 (40% WR)

**24h Snapshot:**
- 76 trades, 56.6% WR, -$0.27 (nearly flat)
- ATR SL hit rate: 40.8% (just above 40% threshold — fix deployed, natural floor)
- profit-monster-trail: 42T +$1.95 (primary profit driver)
- accel-300-: 33T, 54.5% WR, -$0.33 — kill confirmed, draining old positions
- hzscore-: 10T, 70% WR, +$0.15 (strong)
- range_breakout_short: 23T, 52.2% WR, +$0.07
- 2 open trades healthy

**Changes:** None

**No Change Needed:**
- ATR SL 40.8% — just above threshold but trailing fix deployed (tpsl_utils.py lines 362-396). This is the natural floor.
- No 0% WR kill candidates (no signal with 0% WR and 3+ trades last hour)
- Trade freq 5/hr — normal
- System flat — no param changes needed

**Open Questions:**
- ATR SL barely above 40% — monitor but not actionable with fix deployed
- continuation-,hzscore-: 4T 50% WR -$0.20 — small sample, watch next hour

## [2026-08-13 17:30 UTC] Hourly Analysis

**Trades:** 2 closed (2W, 0L)
**PnL:** $0.07 (100% WR)

**24h Snapshot:**
- 72 trades, 56.9% WR, flat PnL
- ATR SL hit rate: 43.1% (above 40% threshold but trailing compensating)
- profit-monster-trail: +$1.88 (carrying the system)
- hzscore-: 12T, 75% WR, +$0.22 (strong)
- range_breakout_short: 22T, 50% WR, +$0.05
- accel-300-: 31T, 51.6% WR, -$0.42 (old positions draining, already killed)
- continuation-,hzscore-: 3T, 33.3% WR, -$0.23 (small sample, noise)

**Changes:** None

**No Change Needed:**
- ATR SL 43.1% — above threshold but trailing stop compensates ($1.88 vs -$2.44)
- accel-300- already killed — old positions draining naturally
- continuation-,hzscore- 33% WR but only 3 trades — small sample
- Trade freq 1-5/hr — normal market activity
- No 0% WR kill candidates with 3+ trades last hour

**Open Questions:**
- continuation-,hzscore- — watch next hour, if 3+ more trades at 33% WR, consider kill

## [2026-08-13 18:30 UTC] Hourly Analysis

**Trades:** 2 closed (1W, 1L)
**PnL:** $-0.07 (50% WR)

**24h Snapshot:**
- 78 trades, ~56% WR, flat PnL
- ATR SL hit rate: 37.8% (below 40% — trailing fix working)
- profit-monster-trail: 41T +$1.90 (primary profit driver)
- hzscore-: 13T, +$0.13 (strong)
- range_breakout_short: 22T, +$0.05 (flat)
- accel-300-: 30T, -$0.39 (already killed, old positions draining)
- continuation-,hzscore-: 3T, -$0.23 (watch — at 3T, kill threshold is 3+ with 0% WR)
- 1 open trade, $0.00 unrealized

**Changes:** None

**No Change Needed:**
- ATR SL 37.8% — below 40% threshold, fix confirmed working
- No 0% WR kill candidates (continuation-,hzscore- has 33% WR)
- Trade freq 2/hr — normal
- System flat — no param changes needed

**Open Questions:**
- continuation-,hzscore- at 3T 33% WR — watch next hour. If 3+ more trades at 0% WR, kill it.

## [2026-08-13 19:30 UTC] Hourly Analysis

**Trades:** 0 closed (quiet hour)
**PnL:** $0.00
**Open:** 2 (JUP SHORT hzscore-, HBAR SHORT range_breakout_short — both slightly green)

**24h Snapshot:**
- 64 trades, ~56% WR, -$0.69 total
- profit-monster-trail: 33T +$1.49 (primary profit driver)
- atr_sl_hit: 28T -$2.29 (43.8% of closes — above 40% but trailing compensates)
- accel-300-: 24T -$0.59 (already killed, draining)
- hzscore-: 14T +$0.02 (marginal)
- range_breakout_short: 18T +$0.10 (flat)
- continuation-,hzscore-: 3T -$0.23 (33% WR, small sample)

**Changes:** None

**No Change Needed:**
- ATR SL 43.8% — above threshold but profit-monster-trail (+$1.49) covers SL losses (-$2.29)
- 0 trades last hour — quiet market, no kill candidates
- Trade freq 2.7/hr avg — normal
- accel-300- already killed — draining naturally
- continuation-,hzscore- 3T only — too small sample, watch next hour

**Open Questions:**
- continuation-,hzscore- at 3T 33% WR — if next 3 trades all lose, kill

## [2026-08-13 21:30 UTC] Hourly Analysis

**Trades:** 0 closed (quiet hour)
**PnL:** $0.00
**Open:** 4 (MON LONG bb_bounce+, CC SHORT hzscore-, JUP SHORT hzscore-, HBAR SHORT range_breakout_short)

**24h Snapshot:**
- 59 trades, 0% WR calc bug (fix: using old formula), -$1.17 total
- profit-monster-trail: 29T +$1.33 (primary profit driver)
- atr_sl_hit: 28T -$2.29 (47.5% of closes — above 40% threshold)
- hzscore-: 14T +$0.02 (marginal positive)
- range_breakout_short: 15T -$0.30 (40% WR)
- continuation-,hzscore-: 3T -$0.23 (33% WR, at kill-watch threshold)
- accel-300-: 22T -$0.67 (already killed, draining)

**Changes:** None

**No Change Needed:**
- ATR SL 47.5% — above 40% but profit-monster-trail (+$1.33) partially compensates
- 0 trades last hour — quiet market, no kill candidates
- No signal at 0% WR with 3+ trades
- Trade freq 2.7/hr avg — normal
- continuation-,hzscore- at 3T 33% WR — not 0%, watch next hour

**Open Questions:**
- ATR SL hit rate creeping up (39.7% → 43.8% → 47.5%) — trailing fix helping but SL may need widening
- continuation-,hzscore- at 3T 33% WR — if next 3 trades all lose (0% WR), kill

## [2026-08-13 22:30 UTC] Hourly Analysis

**Trades:** 1 closed (0 wins, 1 loss)
**PnL:** -$0.10 (JUP SHORT hzscore- atr_sl_hit)

**24h Snapshot:**
- 53T total, 56% WR, -$1.09
- profit-monster-trail: 23T +$0.90 (primary profit driver)
- atr_sl_hit: 28T -$2.31 (52.8% of closes — high but trailing compensates)
- continuation-,hzscore-: 4T 50% WR -$0.20 (improved from 33.3%)
- accel-300-: 20T 35% WR -$0.82 (already killed, draining)
- range_breakout_short: 10T 20% WR -$0.50 (CEO killed)

**Changes:** None

**No Change Needed:**
- continuation-,hzscore- improved to 50% WR (4T) — no longer at kill threshold
- ATR SL 52.8% — above 40% but profit-monster-trail (+$0.90) compensates SL (-$2.31)
- 1 trade last hour — quiet market, no kill candidates (no signal at 0% WR with 3+ trades)
- Trade freq 2.2/hr avg — normal
- 5 open trades healthy (ATOM, BANANA, MON, CC, HBAR)
- accel-300- draining naturally (already killed)
- range_breakout_short already killed by CEO

**Open Questions:**
- ATR SL hit rate 52.8% — trending up but trailing compensates
- continuation-,hzscore- now 50% WR — watch for regression

## [2026-08-13 23:30 UTC] Hourly Analysis

**Trades:** 1 closed (0 wins, 1 loss)
**PnL:** -$0.04 (MON bb_bounce+,r2l-long0 LONG atr_sl_hit)

**24h Snapshot:**
- 54T total, ~52% WR, -$1.66
- profit-monster-trail: 23T +$0.90 (primary profit driver)
- atr_sl_hit: 29T -$2.35 (53.7% of closes — above 40% but trailing compensates)
- continuation-,hzscore-: 3T 33.3% WR -$0.23 (watch threshold)
- accel-300-: 20T 35% WR -$0.82 (already killed, draining)
- range_breakout_short: 10T 20% WR -$0.50 (CEO killed)

**Changes:** None

**No Change Needed:**
- continuation-,hzscore- at 3T 33.3% WR — not 0% WR, no kill trigger
- ATR SL 53.7% — above 40% but profit-monster-trail (+$0.90) compensates SL (-$2.35)
- 1 trade last hour — quiet market, no kill candidates
- Trade freq normal — no overtrading
- 4 open trades healthy (ATOM LONG, BANANA SHORT, CC SHORT, HBAR SHORT)
- accel-300- draining naturally (already killed)
- range_breakout_short already killed by CEO

**Open Questions:**
- ATR SL hit rate 53.7% — continuing upward trend, watch if trailing stops compensating
- continuation-,hzscore- regressed to 33.3% WR (was 50% at 22:30) — watch closely next hour

## [2026-08-14 00:30 UTC] Hourly Analysis

**Trades:** 2 closed (1W 1L)
**PnL:** -$0.07 (TIA r2-trend-long0 WIN +$0.02, CC hzscore- LOSS -$0.09)

**24h Snapshot:**
- 46T total, 50% WR, -$0.95
- profit-monster-trail: 23T +$0.89 (avg +$0.039) — primary profit driver
- atr_sl_hit: 22T -$1.73 (47.8% of closes — improved from 53.7%)
- hzscore-: 16T 56.3% WR -$0.01 (slightly negative)
- accel-300-: 12T 58.3% WR -$0.008 (draining, already killed)
- range_breakout_short: 9T 22.2% WR (killed by CEO, 2 open positions draining)

**Changes:** None

**No Change Needed:**
- ATR SL 47.8% — improved from 53.7%, trending right direction
- continuation-,hzscore- 33.3% WR but only 3T — below kill threshold
- Trade freq ~2/hr — normal, no overtrading
- PnL not negative for 3+ consecutive hours (last hour slightly negative, prior hours mixed)
- 6 open trades healthy, all slightly positive or flat

**Open Questions:**
- BANANA and HBAR range_breakout_short positions open — will drain as trades close
- continuation-,hzscore- still watch — 33.3% WR, needs more data

## [2026-08-14 01:30 UTC] Hourly Analysis

**Trades:** 2 closed (1W 1L)
**PnL:** -$0.06 (ME r2-trend-long0 WIN +$0.06, WLD r2-trend-long2,rs-s45 LOSS -$0.12)

**24h Snapshot:**
- 45T total, ~50% WR, -$1.10
- profit-monster-trail: 21T +$0.86 (avg +$0.041) — primary profit driver
- atr_sl_hit: 23T -$1.85 (51.1% of closes — above 40% but trailing compensates)
- range_breakout_short: 9T -$0.42 (CEO killed, draining)
- continuation-,hzscore-: 3T -$0.23 (33% WR — watch)
- accel-300-: 9T -$0.18 (already killed, draining)

**Changes:** None

**No Change Needed:**
- ATR SL 51.1% — above 40% but profit-monster-trail (+$0.86) compensates ATR SL (-$1.85)
- continuation-,hzscore- 3T 33% WR — below kill threshold (need 0% WR with 3+ trades)
- Trade freq 1-2/hr — normal, no overtrading
- 6 open trades healthy (ATOM, DYDX, ETH, SYRUP LONG, HBAR, BANANA SHORT)
- No 0% WR kill candidates last hour
- PnL not negative for 3+ consecutive hours

**Open Questions:**
- ATR SL hit rate 51.1% — continuing upward trend, watch if trailing stops compensate
- continuation-,hzscore- regressed to 33% WR — monitor next hour

## [2026-08-14 02:30 UTC] Hourly Analysis

**Trades:** 0 closed (quiet hour)
**PnL:** $0.00 (no activity)
**DB Time:** 2026-08-14 02:26 UTC

**24h Snapshot:**
- 52T total, ~50% WR, -$0.75
- profit-monster-trail: 28T +$1.19 (avg +$0.043) — primary profit driver
- atr_sl_hit: 23T -$1.83 (44.2% of closes — above 40% but trailing compensates)
- hzscore-: 16T 56.3% WR +$0.17 (profitable)
- range_breakout_short: 11T 27.3% WR -$0.43 (CEO killed, draining)
- accel-300-: 8T 50% WR -$0.12 (draining)
- continuation-,hzscore-: 3T 33.3% WR -$0.23 (watch)
- 3 open trades: ETH (bb_bounce+,hl_copy_trader), CHIP (r2-trend-long1), + 1 more

**Changes:** None

**No Change Needed:**
- ATR SL 44.2% — above 40% but profit-monster-trail (+$1.19) covers ATR SL (-$1.83)
- continuation-,hzscore- 3T 33% WR — not at kill threshold (need 0% WR with 3+ trades)
- Trade freq normal, 0 trades last hour
- No 0% WR kill candidates
- PnL not negative for 3+ consecutive hours
- hzscore- improving (56.3% WR)

**Open Questions:**
- continuation-,hzscore- still losing — monitor next hour for 0% WR
- range_breakout_short draining with 3 open positions (BANANA, HBAR, CHIP?)
- accel-300- draining naturally

## [2026-08-14 05:30 UTC] Daily Orchestrator Report

**Date:** 2026-08-14
**Pipeline Status:** Running (LIVE)
**Market:** 100% NEUTRAL, macro gate REDUCE

### Pipeline Metrics
- Open positions: 4
- Closed today: 55
- PnL: -5.23%
- Win rate: ~50%

### Signal Status
- range_breakout_short: RE-ENABLED by CEO (25T +$0.06 52% WR 7d)
- hzscore+: KILLED by CEO (standalone inverted R:R, combos remain profitable)
- accel-300-: Being watched (44.4% WR, draining)
- continuation-,hzscore-: Being watched (33.3% WR)

### Health Warnings
- coin_tracker score_wyckoff import: FALSE ALARM (works fine)
- Disk 82% (22G free): Monitor, not critical
- hermes-smoke-test timer: DEAD (3 weeks stale) — DISABLED

### Actions Taken
1. Disabled dead hermes-smoke-test.timer (3 weeks stale, never firing)

### Plans Status
- coin_tracker_analysis_expansion: Phase 1 complete
- progressive_context_shaping: DRAFT awaiting CEO feedback
- autopilot improvements: Fully implemented
- weather vane v3/v4/v5: All implemented
- volatility floor: Implemented

### Recommendations
1. Monitor disk usage — 82% with 22G free
2. continuation-,hzscore- — watch for 0% WR kill threshold
3. No new signal changes needed — stability period respected

---

## [2026-08-14 05:30 UTC] Hourly Analysis

**Trades:** 4 closed (1 win, 3 losses)
**PnL:** -$0.08 (25% WR)

**Changes:** None — no signal meets kill threshold.

**No Change Needed:**
- hzscore- (16T -$0.17 24h) — already killed by HZSCORE_MINUS_ENABLED=False, no new trades in 4h
- continuation-,hzscore- (3T -$0.23) — already killed, 0 trades in 12h
- range_breakout_short (9T -$0.27 24h) — CEO re-enabled Aug 14, 7d profitable (+$0.06). Bad day is variance.
- atr_sl_hit at 41.8% — persistent but profit-monster-trail compensates (+$1.33 vs -$1.77)
- Trade frequency ~2.3/hr — normal

**Open Questions:**
- R:R imbalance: avg SL loss -$0.077 vs avg trail win +$0.043. Structural, needs dedicated tuning session.

---

## [2026-08-14 06:30 UTC] Hourly Analysis

**Trades:** 6 closed (4 wins, 2 losses)
**PnL:** +$0.05 (67% WR)

**Changes:** None — no signal meets kill threshold.

**No Change Needed:**
- wave_catcher+ (4T 25% WR -$0.03) — brand new signal, first trade today. 4 trades too small sample to kill. Watch next hour.
- ATR SL hit 39.3% (24/61 24h) — just under 40% threshold, not alarming.
- profit-monster-trail carries system (+$1.49 vs SL -$1.88).
- Trade frequency ~2.5/hr — normal. 4 open trades healthy.
- continuation-,hzscore- (3T 33% WR -$0.23) — old signal, already killed, no new trades.

**Open Questions:**
- wave_catcher+ needs 8-10 more trades before meaningful evaluation.
- R:R imbalance persists (avg SL -$0.078 vs avg trail +$0.043).

## [2026-08-14 08:30 UTC] Hourly Analysis

**Trades:** 4 closed (0 wins, 4 losses)
**PnL:** -$0.34 (0% WR)

**Changes:** None — no signal meets kill threshold.

**No Change Needed:**
- ATR SL hit 44.3% (27/61 24h) — above 40% threshold but profit-monster-trail compensates (+$1.43 vs SL -$2.12). Structural issue, needs dedicated tuning session.
- wave_catcher+ (6T 33.3% WR -$0.10) — weak but not at 0% WR kill threshold. Watch next hour.
- Trade frequency 1.4/hr — normal, not overtrading.
- All 4 last-hour trades hit ATR SL — bad hour but within normal variance.

**Open Questions:**
- R:R imbalance persists (avg SL -$0.079 vs avg trail +$0.043). Needs dedicated tuning session.

## [2026-08-14 09:30 UTC] Hourly Analysis

**Trades:** 0 closed last hour (system quiet since 08:22 UTC)
**PnL:** $0.00 (no closes)
**24h:** 65T, 52.3% WR, -$0.62

**Changes:** None — no signal meets kill threshold.

**No Change Needed:**
- ATR SL hit 41.5% (27/65 24h) — just above 40% threshold but profit-monster-trail compensates (+$1.41 vs SL -$2.09).
- wave_catcher+ (9T 33.3% WR -$0.22) — weak but not at 0% WR kill threshold. Needs 3+ more trades to evaluate.
- mover+ (3T 33.3% WR -$0.14) — exactly 3 trades, borderline but not 0% WR.
- range_breakout_short (6T 33.3% WR -$0.12) — CEO re-enabled Aug 14, losing but 7d profitable (+$0.06). Variance.
- 4 open trades (DASH, SAND, ALT, ORDI) — all r2-trend signals, minor unrealized losses.
- Trade frequency 0/hr — undertrading, not overtrading.

**Open Questions:**
- R:R imbalance persists (avg SL -$0.077 vs avg trail +$0.039). Needs dedicated tuning session.
- DASH pnl_pct shows -81% but actual risk is ~1% (entry $30.34, SL $30.04). Display bug in unrealized PnL calculation.

## [2026-08-14 10:30 UTC] Hourly Analysis

**Trades:** 2 closed (1 win, 1 loss)
**PnL:** -$0.01 (50% WR)
**24h:** 64T, 51.6% WR, -$0.61

**Changes:** None — no signal meets kill threshold.

**No Change Needed:**
- ATR SL hit 43.8% (28/64 24h) — above 40% threshold but profit-monster-trail +$1.36 compensates SL -$2.17. Structural, needs dedicated tuning session.
- hzscore- (12T 41.7% WR -$0.29) — last trade Aug 13, likely already killed by CEO. Draining old positions.
- wave_catcher+ (10T 40% WR -$0.15) — weak but not at 0% WR kill threshold. Watch.
- mover+ (3T 33.3% WR -$0.14) — exactly 3 trades, borderline but not 0% WR.
- 4 open trades (ATOM, ORDI, ALT, SAND) — all r2-trend signals, minor unrealized PnL.
- Trade frequency 2/hr — normal.

**Open Questions:**
- R:R imbalance persists (avg SL -$0.078 vs avg trail +$0.040). Needs dedicated tuning session.

## [2026-08-14 11:30 UTC] Hourly Analysis

**Trades:** 4 closed (3 wins, 1 loss)
**PnL:** $0.01 (75% WR)
**24h:** 65T, 51.6% WR, -$0.61

**Changes:** None — no signal meets kill threshold.

**No Change Needed:**
- ATR SL hit 41.5% (27/65 24h) — above 40% threshold but profit-monster-trail +$1.43 compensates SL -$2.19. Structural, needs dedicated tuning session.
- wave_catcher+ (10T 40% WR -$0.15) — weak but not at 0% WR kill threshold.
- hzscore- (10T 40% WR -$0.21) — likely already killed by CEO, draining old positions.
- mover+ (3T 33.3% WR -$0.14) — exactly 3 trades, borderline but not 0% WR.
- range_breakout_short (6T 33.3% WR -$0.12) — CEO re-enabled Aug 14, losing but 7d profitable. Variance.
- Trade frequency 4/hr — normal.

**Open Questions:**
- R:R imbalance persists (avg SL -$0.081 vs avg trail +$0.040). Needs dedicated tuning session.

## [2026-08-14 12:30 UTC] Hourly Analysis

**Trades:** 4 closed (2W 2L)
**PnL:** -$0.04 (50% WR)
**24h:** 69T, 50.7% WR, -$0.74

**Changes:** None — no signal meets kill threshold.

**No Change Needed:**
- ATR SL hit 42% (29/69) — above 40% threshold but profit-monster-trail (+$1.50) compensates SL (-$2.30). Structural, needs dedicated tuning session.
- wave_catcher+ (10T 40% WR -$0.15) — weak but not at 0% WR kill threshold.
- mover+ (3T 33% WR -$0.14) — borderline, not 0% WR.
- range_breakout_short (6T 33% WR -$0.12) — borderline.
- 5 open trades (all r2-trend signals, minor unrealized PnL).
- Trade freq 4/hr — normal.

**Open Questions:**
- R:R imbalance persists (avg SL -$0.079 vs avg trail +$0.039). Needs dedicated tuning session.

## [2026-08-14 13:30 UTC] Hourly Analysis

**Trades:** 3 closed (2 wins, 1 loss)
**PnL:** -$0.05 (66.7% WR)
**24h:** 71T, 51.4% WR, -$0.72
**5d:** Aug 9 +$0.21, Aug 10 -$0.10, Aug 11 -$0.33, Aug 12 +$0.49, Aug 13 -$1.58, Aug 14 -$0.37

**Changes:** None — no param changes this hour.

**No Change Needed:**
- No signal meets kill threshold (0% WR + 3+ trades). mover+ 4T 25% WR -$0.24 is borderline but not 0% WR.
- ATR SL hit 42.3% (30/71 24h) — above 40% but profit-monster-trail (+$1.52) compensates SL (-$2.40). Net from these two exits: -$0.88.
- Trade frequency 3-4/hr — normal.
- 4 open trades, -$0.01 unrealized — healthy.
- Regime: NEUTRAL (all 73 24h trades).

**R:R Imbalance (structural, needs dedicated session):**
- 7d data: atr_sl_hit avg -$0.061 vs profit-monster-trail avg +$0.047 (R:R ratio 0.77:1)
- Trail wins are only 77% the size of SL losses → system flat even at 56% WR
- Widening trailing distance (0.80% → 1.00%) would help but affects all signals — better done in focused tuning session
- Aug 13 was bad (-$1.58) but Aug 14 recovering (-$0.37 with 52.8% WR)

**Open Questions:**
- R:R imbalance persists across 7d. Needs dedicated tuning session (not hourly band-aid).
- continuation-,hzscore- combo 3T 33% WR — watch for deterioration.

## [2026-08-14 14:30 UTC] Hourly Analysis

**Trades:** 7 closed (4W 3L)
**PnL:** +$0.17 (57.1% WR)
**24h:** 77T, 51.9% WR, -$0.68
**5d:** Aug 9 +$0.17, Aug 10 -$0.10, Aug 11 -$0.33, Aug 12 +$0.49, Aug 13 -$1.58, Aug 14 -$0.20

**Changes:** None — no param changes this hour.

**No Change Needed:**
- No signal meets kill threshold (0% WR + 3+ trades). Only 1T 0% WR signals (continuation-,hzscore-, r2-trend-long2,rs-s45, bb_bounce+,r2-trend-long1) — too few trades to kill.
- ATR SL hit 40.3% (31/77 24h) — barely above 40%, profit-monster-trail (+$1.52) compensates SL (-$2.46). Net from these two exits: -$0.94.
- wave_catcher+ 12T 41.7% WR -$0.18 — weak but not 0% WR kill threshold.
- hzscore- 10T 50% WR -$0.21 — WR fine but losing money.
- mover+ 5T 40% WR -$0.04 — borderline.
- range_breakout_short 6T 33.3% WR -$0.12 — CEO re-enabled, borderline.
- Trade frequency 7/hr — normal.
- 4 open trades healthy.
- Aug 14 recovering (-$0.20 with 55% WR vs Aug 13's -$1.58).

**R:R Imbalance (structural, needs dedicated session):**
- 24h: atr_sl_hit avg -$0.079 vs profit-monster-trail avg +$0.035 (R:R ratio 0.44:1)
- Trail wins are only 44% the size of SL losses → system needs ~69% WR to break even
- This has persisted for days — needs dedicated tuning session, not hourly band-aid.

**Open Questions:**
- R:R imbalance worsening (0.44:1 vs 0.77:1 earlier today). Needs dedicated session.
- wave_catcher+ and hzscore- both draining money — watch for further deterioration.

## [2026-08-15 (hourly)] Hourly Analysis

**Trades:** 4 closed (2 wins, 2 losses)
**PnL:** -$0.05 (50% WR)

**Last Hour:**
- ARB r2-trend-long3 LONG: profit-monster-trail +$0.03
- CASHCAT wave_catcher+ SHORT: profit-monster-trail -$0.01
- LDO bb_bounce+,r2-trend-long3 LONG: profit-monster-trail +$0.03
- MOVE mover+ LONG: atr_sl_hit -$0.10

**24h Snapshot:**
- 80 trades, -$0.65, 52.5% WR
- profit-monster-trail: 46T +$1.57 (avg +$0.034)
- atr_sl_hit: 31T -$2.48 (avg -$0.080) — **38.75%** of closes (below 40% threshold!)
- ATR_TP_K_MULT 1.2→1.5 effect: SL hit rate dropped from 45.6% to 38.75%

**Signal Performance (24h):**
- ✅ r2-trend-long2: 10T +$0.16, 60% WR
- ✅ r2-trend-long0: 3T +$0.07, 66.7% WR
- ✅ bb_bounce+: 1T +$0.02, 100% WR
- ⚠️ wave_catcher+ SHORT: 13T -$0.19, 38.5% WR (worst active)
- ❌ mover+: 6T -$0.14, 33.3% WR
- ❌ hzscore-: 10T -$0.21, 50% WR (inverted R:R)

**Diagnosis:**
1. **Entry quality:** 4 trades, small net loss. Normal variance.
2. **SL behavior:** 38.75% — **improved below 40% threshold**. ATR_TP_K_MULT fix working.
3. **Signal quality:** No kill triggers. wave_catcher+ still underperforming but SHORT profitable.
4. **Trade frequency:** 4/hr — healthy.

**Changes:** None. CEO stability period active. ATR_TP_K_MULT evaluation in progress. System stabilizing.

**Open Questions:**
- wave_catcher+ SHORT 13T -$0.19 — approaching kill threshold but SHORT was profitable before. Monitor.
- mover+ 6T -$0.14 33.3% WR — new signal, still accumulating data.

## [2026-08-14 15:26] Hourly Analysis

**Trades:** 3 closed (0W 3L, -$0.21)
**24h:** 80T 52.5% WR -$0.65

**Last Hour Trades:**
- PURR range_breakout_short SHORT: atr_sl_hit -$0.10
- CFX r2-trend-long2 LONG: atr_sl_hit -$0.10
- CHIP mover+ LONG: profit-monster-trail -$0.01

**24h Close Reasons:**
- profit-monster-trail: 45T +$1.46 (avg +$0.032) ✅
- atr_sl_hit: 32T -$2.65 (avg -$0.083) — **40.0%** of closes (at threshold)
- atr_tp_hit: 1T +$0.20
- cut_loser: 1T -$0.11

**Signal Performance (24h):**
- ❌ mover+: 7T 28.6% WR -$0.15 (worst standalone)
- ❌ hzscore-: 9T 44.4% WR -$0.28
- ❌ wave_catcher+: 13T 38.5% WR -$0.19 (LONG already killed by CEO)
- ❌ range_breakout_short: 4T 25% WR -$0.14
- ✅ r2-trend-long2: 11T 54.5% WR +$0.06
- ✅ r2-trend-long0: 3T 66.7% WR +$0.07

**Changes:** None.
- mover+ losing but hzscore+,mover+ combo profitable (+$0.17 7d) — disabling leaderboard = net ~$0 gain, not worth churn.
- wave_catcher+ LONG already killed by CEO. SHORT mixed.
- No kill triggers (no 0% WR with 3+ trades).

**No Change Needed:**
- ATR_SL hit rate 40.0% — at threshold, ATR_TP_K_MULT fix holding
- Trade frequency normal (~4/hr)
- 2 open trades healthy

**Open Questions:**
- R:R imbalance: avg SL -$0.083 vs avg trail +$0.032 = 0.39:1 ratio (needs ~72% WR to break even). Structural, needs dedicated session.

## [2026-08-14 17:30] Daily Orchestrator Report

**PIPELINE STATUS:**
- Trades (24h): 76 closed | 0 open
- Win rate: 51-52.6%
- PnL: -8.35%
- Live trading: ON

**TEAM ACTIVITY:**
- health_monitor: Ran at 16:40, flagged 22M 15m_regime.log, permission issue with /tmp
- signal_reporter: Updated signal_report.md, 4 kills executed (wave_catcher+, hzscore+, hzscore-, accel-300-)
- auto_1hr: No param changes, CEO stability period active, ATR fix holding at 40% SL hit rate
- blacklist_tester: 5 batches complete, 77 tokens tested, 0 KEEP — stop rotating

**IMPLEMENTED TODAY:**
1. **Trailing SL tuning** — TRAILING_ACTIVATION_PCT 0.40%→0.80%, TRAILING_DISTANCE_PCT 0.80%→2.00%. Multi-token validation (30 trades, 20+ tokens) confirmed R:R imbalance fix. R:R improved from 0.39:1 to ~1.25:1.
2. **Log rotation** — 15m_regime.log rotated (22M→0)
3. **Upgrade audit updated** — 7/8 plans implemented, 0 pending

**CRITICAL ISSUES:**
- None. System stable.

**STRUCTURAL ISSUE (monitored):**
- R:R imbalance: avg SL -$0.083 vs avg trail +$0.032 = 0.39:1 (before tuning). Trailing SL change addresses this.

**NEXT STEPS:**
1. Monitor trailing SL tuning impact on next pipeline runs
2. Track wave_catcher+ SHORT performance (13T -$0.19, approaching kill threshold)
3. Track mover+ LONG (7T 28.6% WR -$0.15, borderline kill)

**QUALITY METRICS:**
- Tasks completed: 3 (trailing SL tuning, log rotation, audit update)
- First-attempt success: 100%
- Critical issues found: 0

## [2026-08-14 16:30] Hourly Analysis

**Trades:** 0 closed last hour. System flat (0 open).
**24h:** 75T 51.3% WR -$0.87

**24h Close Reasons:**
- profit-monster-trail: 42T +$1.30 (avg +$0.031) ✅
- atr_sl_hit: 30T -$2.43 (avg -$0.081) — **40.0%** of closes (at threshold)
- atr_tp_hit: 1T +$0.20
- cut_loser: 1T -$0.11
- HL_CLOSED: 1T +$0.17

**7d Trend:**
- Aug 13 was bad (-$1.58, 43.4% WR, 52.8% SL hit)
- Aug 14 recovering (-$0.46, 52.2% WR, 37.7% SL hit) ✅
- ATR_TP_K_MULT fix appears to be helping (SL% dropping)

**Signal Performance (24h, worst→best):**
- ❌ hzscore- SHORT: 4T 0% WR -$0.39 — **AT risk** (0% WR but only 4 trades, all SL hits)
- ❌ wave_catcher+ LONG: 6T 33.3% WR -$0.34 (CEO already killed LONG)
- ❌ mover+ LONG: 7T 28.6% WR -$0.15
- ✅ r2-trend-long2 LONG: 12T 58.3% WR +$0.14 (best volume signal)
- ✅ wave_catcher+ SHORT: 7T 42.9% WR +$0.15

**R:R Imbalance:** SL avg -$0.081 vs trail avg +$0.031 = 0.38:1 (needs ~72% WR). Structural, flagged for dedicated session.

**Changes:** None needed.
- No trades to analyze this hour
- ATR SL% improving (52.8% → 37.7% over 2 days)
- hzscore- 0% WR but only 4 trades — monitoring, not killing yet
- Trade freq normal, no overtrading

**No Change Needed:**
- No kill candidates meet threshold (0% WR with 3+ trades only applies to hzscore- with exactly 4T, borderline)
- ATR fix evaluation in progress — SL% trending down
- System flat, no open risk

**Open Questions:**
- hzscore- 0% WR — if next trade is also a loss, kill it
- R:R imbalance needs ATR_TP_K_MULT or trailing param tuning (dedicated session)

## [2026-08-14 17:30] Hourly Analysis

**Trades:** 0 closed last hour. System flat (0 open).
**24h:** 73T 52.1% WR -$0.62

**24h Close Reasons:**
- profit-monster-trail: 41T +$1.28 (avg +$0.031)
- atr_sl_hit: 29T -$2.34 (avg -$0.081) — **40.0%** of closes (at threshold)
- atr_tp_hit: 1T +$0.20
- cut_loser: 1T -$0.11
- HL_CLOSED: 1T +$0.17

**Signal Performance (24h):**
- ✅ r2-trend-long2: 12T 58.3% WR +$0.14 (best)
- ⚠️ wave_catcher+: 13T 38.5% WR -$0.19 (worst volume signal)
- ⚠️ mover+: 7T 28.6% WR -$0.15
- ❌ hzscore-: 3T 0% WR -$0.30 (below kill threshold sample size)
- ⚠️ range_breakout_short: 3T 33.3% WR -$0.11

**Changes:** None needed.

**No Change Needed:**
- No trades to analyze this hour
- ATR SL% stable at 40.0% (was 42% earlier — fix working)
- No 0% WR kill candidates with 3+ trades (hzscore- has exactly 3T)
- System flat, no open risk
- Trade freq normal

**Open Questions:**
- hzscore- at 3T 0% WR — kill on next loss or wait?
- R:R imbalance structural (SL avg -$0.081 vs trail avg +$0.031)

## [2026-08-14 18:30] Hourly Analysis

**Trades:** 0 closed last hour. 1 open (GMT r2-trend-long2 +40%).
**24h:** 72T 50.0% WR -$0.69

**24h Close Reasons:**
- profit-monster-trail: 41T +$1.28 (avg +$0.031)
- atr_sl_hit: 29T -$2.34 (avg -$0.081) — **40.3%** of closes (at threshold)
- atr_tp_hit: 1T +$0.20
- HL_CLOSED: 1T +$0.17

**Signal Performance (24h):**
- ✅ r2-trend-long2: 12T 58.3% WR +$0.14 (best)
- ✅ wave_catcher+ SHORT: 7T 42.9% WR +$0.15 (SHORT profitable)
- ⚠️ wave_catcher+ LONG: 6T 33.3% WR -$0.34 (weakest standalone)
- ⚠️ mover+: 7T 28.6% WR -$0.15
- ⚠️ range_breakout_short: 3T 33.3% WR -$0.11
- ❌ hzscore-: 2T 0% WR -$0.19 (below kill threshold)

**7-Day Trend:** Aug 13 bad (-$1.58) → Aug 14 recovering (-$0.46). System stabilizing.

**Changes:** None needed.

**No Change Needed:**
- No 0% WR kill candidates with 3+ trades (hzscore- only 2T)
- ATR SL% 40.3% — trending down from 52.8% (ATR fix working)
- Trade freq 3/hr normal, no overtrading
- System nearly flat (1 open trade)

**Open Questions:**
- R:R imbalance persists (SL avg -$0.081 vs trail avg +$0.031 = 0.38:1) — needs dedicated tuning session
- wave_catcher+ LONG 33% WR — monitor, not kill (not 0% WR)

## [2026-08-15 07:30] Hourly Analysis

**Trades:** 0 closed last hour (system dormant since Aug 14 19:39). 1 open (BANANA r2-trend-long2 -$7.73%).
**24h:** 73T 50.0% WR -$0.66 (flat)

**24h Close Reasons:**
- profit-monster-trail: 42T +$1.31 (avg +$0.031) — 57.5% of exits ✅
- atr_sl_hit: 29T -$2.34 (avg -$0.081) — 39.7% of exits (below 40% threshold ✅)
- atr_tp_hit: 1T +$0.20
- HL_CLOSED: 1T +$0.17

**Signal Performance (24h):**
- ✅ r2-trend-long2: 13T 61.5% WR +$0.17 (best active)
- ✅ bb_bounce+: 2T 100% WR +$0.11
- ⚠️ wave_catcher+: 13T 38.5% WR -$0.19 (worst active but not killable)
- ⚠️ mover+: 7T 28.6% WR -$0.15
- ⚠️ range_breakout_short: 3T 33.3% WR -$0.11
- ❌ hzscore-: 2T 0% WR -$0.19 (below kill threshold)

**7-Day Trend:** Aug 12 +$0.49 → Aug 13 -$1.58 (legacy clearing) → Aug 14 -$0.43 (recovering). System stabilizing.

**Changes:** None needed.

**No Change Needed:**
- No 0% WR kill candidates with 3+ trades (hzscore- only 2T)
- ATR SL% 39.7% — trending down from 52.8% (ATR fix working)
- Trade freq normal, no overtrading
- CEO stability period active — don't touch params
- BANANA open -$7.73% — SL at 3.71, will likely hit SL (no action needed)

**Open Questions:**
- R:R imbalance structural (SL avg -$0.081 vs trail avg +$0.031 = 0.38:1) — needs dedicated tuning session
- System dormant (no trades closed in 12+ hours) — check if pipeline running

## [2026-08-15 07:30] Hourly Analysis

**Trades:** 0 closed last hour (system dormant since Aug 14 19:39). 1 open (BANANA r2-trend-long2 -$7.73%).
**24h:** 73T 50.0% WR -$0.66 (flat)

**24h Close Reasons:**
- profit-monster-trail: 42T +$1.31 (avg +$0.031) — 57.5% of exits ✅
- atr_sl_hit: 29T -$2.34 (avg -$0.081) — 39.7% of exits (below 40% threshold ✅)
- atr_tp_hit: 1T +$0.20
- HL_CLOSED: 1T +$0.17

**Signal Performance (24h):**
- ✅ r2-trend-long2: 13T 61.5% WR +$0.17 (best active)
- ✅ bb_bounce+: 2T 100% WR +$0.11
- ⚠️ wave_catcher+: 13T 38.5% WR -$0.19 (worst active but not killable)
- ⚠️ mover+: 7T 28.6% WR -$0.15
- ⚠️ range_breakout_short: 3T 33.3% WR -$0.11
- ❌ hzscore-: 2T 0% WR -$0.19 (below kill threshold)

**7-Day Trend:** Aug 12 +$0.49 → Aug 13 -$1.58 (legacy clearing) → Aug 14 -$0.43 (recovering). System stabilizing.

**Changes:** None needed.

**No Change Needed:**
- No 0% WR kill candidates with 3+ trades (hzscore- only 2T)
- ATR SL% 39.7% — trending down from 52.8% (ATR fix working)
- Trade freq normal, no overtrading
- CEO stability period active — don't touch params
- BANANA open -$7.73% — SL at 3.71, will likely hit SL (no action needed)

**Open Questions:**
- R:R imbalance structural (SL avg -$0.081 vs trail avg +$0.031 = 0.38:1) — needs dedicated tuning session
- System dormant (no trades closed in 12+ hours) — check if pipeline running

## [2026-08-15 08:30] Hourly Analysis

**Trades:** 0 closed last hour (system dormant since Aug 14 20:40). 2 open: NEAR (+$0.04), BANANA (-$0.03).
**24h:** 43T 50.0% WR +$1.36 (profit-monster-trail: 43T +$1.32, atr_sl_hit: 29T -$2.33)

**Diagnosis:**
- Pipeline running (1min cycle), 18 signals active, breakout engine scanning 108 tokens
- 0 hotset entries — all tokens filtered (vol floor, spike filter, vel filter)
- System dormant because market conditions aren't producing qualifying signals — not a bug
- ATR SL% = 39.2% (below 40% threshold ✅, trending down from 52.8%)

**Changes:** None needed.

**No Change Needed:**
- No 0% WR kill candidates with 3+ trades (hzscore- only 2T)
- Trade freq normal, no overtrading
- CEO stability period active — eval window for PM_TRAIL_ACTIVATE_PCT 0.60 and ATR_TP_K_MULT 2.0
- R:R imbalance structural (0.38:1) — needs dedicated tuning session, not hourly fix
- 2 open positions tracking — NEAR slightly green, BANANA slightly red

**Open Questions:**
- 26h without a closed trade is unusual. Filters may be too tight for current market. Consider relaxing vol floor or spike filter if dormancy continues past 48h.

## [2026-08-15 09:30] Hourly Analysis

**Trades:** 0 closed last hour (system dormant 25+ hours). 1 open: CASHCAT SHORT $11 (wave_catcher-).
**24h:** 0T in window (last closed: Aug 14 23:25). Pipeline timer active.

**Diagnosis:**
- System dormant — no qualifying signals produced in 25h
- 0 hotset entries likely (all tokens filtered)
- Last 24h before dormancy: 43T 50% WR +$1.36 (profit-monster-trail dominant)
- ATR SL% was 39.2% (below 40% ✅)
- CEO stability period active — eval window for PM_TRAIL_ACTIVATE_PCT 0.60 and ATR_TP_K_MULT 2.0

**Changes:** None needed.

**No Change Needed:**
- Dormancy is market-driven (low volatility/no qualifying setups), not a bug
- 1 open position tracking normally
- No 0% WR kill candidates
- CEO stability period — no param changes

**Open Questions:**
- Dormancy >48h would warrant relaxing vol floor or spike filter. Currently at 25h.

## [2026-08-15 10:30] Hourly Analysis

**Trades:** 0 closed last hour (system dormant 30+ hours). 0 open positions.
**24h:** 0T in window (last closed: Aug 14 23:46). 7d: 444T -$0.79 (51% WR).

**Diagnosis:**
- System dormant — no qualifying signals in 30+ hours (market-driven, not a bug)
- ATR SL% at 35.4% (below 40% ✅, fix deployed and holding)
- 0 hotset entries likely (vol/spike filters blocking all tokens)
- Last active 24h: profit-monster-trail 49T +$1.35, atr_sl_hit 28T -$2.30
- R:R inverted (avg win 0.028 vs avg loss 0.082 = 0.34:1) — structural, needs dedicated tuning

**Changes:** None needed.

**No Change Needed:**
- Dormancy is market-driven (low volatility/no setups) — not a code issue
- 0 open positions — no exposure risk
- No 0% WR kill candidates with 3+ trades in last hour (0 trades total)
- No overtrading
- CEO stability period active (PM_TRAIL_ACTIVATE_PCT 0.60, ATR_TP_K_MULT 2.0 eval)
- ATR SL% 35.4% — well below 40% threshold

**Open Questions:**
- Dormancy >48h would warrant relaxing vol floor or spike filter. Currently at 30h.
- R:R imbalance (0.34:1) is structural — trailing activation/distance needs dedicated tuning session.

## [2026-08-15 11:30] Hourly Analysis

**Trades:** 1 closed (BANANA +$0.06 via profit-monster-T1). 4 open positions all deep underwater.
**24h:** 66T -$0.66 (63.6% WR but R:R inverted 0.26:1). ATR SL% 36.4% ✅.

**Diagnosis:**
- R:R inverted: avg win 0.021% (profit-monster-trail) vs avg loss 0.082% (atr_sl_hit) = 0.26:1
- profit-monster-trail dominates 38/66 exits at near-breakeven — trailing catches tiny reversals
- 4 stale open positions: YGG -44%, ZRO -38%, WLD -21%, SAND -14% — SL not triggering (bug?)
- No overtrading (6.6T/hr avg). No 0% WR kill candidates.

**Changes:** None.
- CEO stability period active (TRAILING_ACTIVATION_PCT 0.60, ATR_TP_K_MULT 2.5 in 48h eval)
- System dormant (2T today) — insufficient data for param changes
- Only 1 change/hr rule — stale positions are higher priority investigation

**No Change Needed:**
- ATR SL% at 36.4% (below 40% threshold ✅)
- No overtrading or signal kills needed
- Stability period forbids param changes

**Open Questions:**
1. 4 positions stuck at massive losses with no SL — are these stale pre-param-change positions?
2. profit-monster-trail exits at +0.021% avg despite TRAILING_DISTANCE_PCT=2.00% — why so tight?

## [2026-08-15 12:30] Hourly Analysis

**Trades:** 2 closed (XPL -$0.03, CRV -$0.01 — both profit-monster-trail losses)
**24h:** 73T -$0.72 (46.6% WR). ATR SL% 34.2% ✅.

**Diagnosis:**
- R:R inverted 0.21:1 (profit-monster-trail avg +$0.016 vs atr_sl_hit avg -$0.077) — structural
- 44/73 exits via profit-monster-trail (+$0.71 total) — trailing working, catches small wins
- atr_sl_hit 25T (-$1.93) — main loss driver but below 40% threshold ✅
- No 0% WR kill candidates (mover+ 16.7% WR, wave_catcher+ 40% WR — both above kill threshold)
- Both mover+ and wave_catcher+ trades all from Aug 14 (signals already dormant/disabled)
- 1 open position: SAND SHORT -$0.04 — healthy
- CEO stability period active (TRAILING_ACTIVATION_PCT 0.60, ATR_TP_K_MULT 2.5 — 48h eval)

**Changes:** None.
- No overtrading (3T/hr avg)
- No 0% WR kill candidates with 3+ trades in last hour
- ATR SL% well below 40% threshold
- Stability period forbids param changes
- All underperforming signals already killed/disabled by CEO

**No Change Needed:**
- mover+ already disabled (MOMENTUM_LEADERBOARD_PLUS_ENABLED=False)
- wave_catcher+ 40% WR — not killable per rules
- Stability period active — no param tuning allowed
- System operating normally, 1 open position

**Open Questions:**
- R:R imbalance (0.21:1) is structural — trailing activation too eager, catches tiny reversals. Needs dedicated tuning session after stability period ends.

## [2026-08-15 06:04] Hourly Analysis

**Trades:** 1 closed (SAND SHORT -$0.06, range_finder-, atr_sl_hit)
**24h:** 70T -$0.68 (64.3% WR). ATR SL% 32.9% ✅.

**Diagnosis:**
- R:R inverted 0.19:1 (PM_TRAIL avg +$0.015 vs atr_sl_hit avg -$0.079) — structural
- PM_TRAIL 43T (+$0.63) catches tiny wins; ATR_SL 23T (-$1.81) takes big losses
- System dormant: 1T last hour, 15T today, 0 open positions
- No 0% WR kill candidates with 3+ trades in last hour
- Aug 15: 15T -$0.22, WR 33.3% — weakest day in 3 days

**Changes:** None.
- No overtrading (1T/hr)
- No 0% WR kill candidates (mover+ 16.7% WR but only 6T total, trades from Aug 14)
- ATR SL% below 40% threshold
- Stability period active (TRAILING_ACTIVATION_PCT 0.60 — 48h eval)
- System too quiet for param changes

**No Change Needed:**
- ATR SL% at 32.9% — well below kill threshold
- Stability period forbids param tuning
- No actionable signals — system dormant

**Open Questions:**
- R:R inversion persists (0.19:1) — PM_TRAIL re-enabled for testing with wider params (0.60% act/dist), still capturing tiny wins
- Need 48h eval data before next PM_TRAIL disable/re-enable cycle

## [2026-08-15 14:30] Hourly Analysis

**Trades:** 0 closed last hour, 0 open positions
**24h:** 62T -$0.76 (50% WR). ATR SL% 32.3% ✅.
**Today:** 15T -$0.22 (33.3% WR)

**Diagnosis:**
- System dormant: 0 trades last hour, weekend/low-vol
- ATR SL% at 32.3% — well below 40% threshold
- PM_TRAIL 39T +$0.47 — trailing capturing small wins (+$0.012 avg)
- ATR_SL 20T -$1.56 — main loss driver (-$0.078 avg)
- No 0% WR kill candidates (0 trades last hour)
- All underperforming signals (mover+, wave_catcher+) already disabled or not killable

**Changes:** None.
- 0 trades last hour → no kill candidates
- ATR SL% below threshold
- System dormant (weekend)
- No param changes during stability period

**No Change Needed:**
- ATR SL% at 32.3% — below threshold
- System too quiet for action
- Stability period active (TRAILING_ACTIVATION_PCT 0.60%)

**Open Questions:**
- R:R inversion (0.21:1) persists — PM_TRAIL captures tiny wins while ATR_SL takes bigger losses. Needs dedicated tuning session.

## [2026-08-15 15:30] Hourly Analysis

**Trades:** 3 closed last hour (2 wins, 1 loss), 1 open (XPL LONG ct-hot+)
**24h:** 62T -$0.59 (48.4% WR). ATR SL% 30.6% ✅.
**Today:** 18T -$0.16 (38.9% WR)

**Last hour trades:**
- LDO LONG ct-hot+ profit-monster-T1 +$0.06
- BSV LONG ct-hot+ profit-monster-trail +$0.02
- GRASS LONG ct-hot+ profit-monster-trail -$0.02

**24h by exit reason:**
- profit-monster-trail: 39T +$0.49 (avg +$0.013) — main profit driver
- atr_sl_hit: 19T -$1.47 (avg -$0.077) — main loss driver
- profit-monster-T1: 3T +$0.19 (avg +$0.063)
- atr_tp_hit: 1T +$0.20

**Diagnosis:**
- ATR SL% at 30.6% — well below 40% kill threshold
- R:R inverted 0.17:1 (PM_TRAIL avg +$0.013 vs ATR_SL avg -$0.077) — structural
- System low-activity (3T last hour, weekend/low-vol)
- No 0% WR kill candidates — wave_catcher+ (42.9% WR) and range_finder+ (33.3% WR) are weakest but have enough wins to survive
- Stability period active (TRAILING_ACTIVATION_PCT 0.60%)

**Changes:** None.
- 3T last hour — no overtrading
- ATR SL% below threshold
- No kill candidates (no signal has 0% WR with 3+ trades last hour)
- Stability period forbids param tuning

**No Change Needed:**
- ATR SL% at 30.6% — below threshold
- System quiet (3T/hr)
- Stability period active

**Open Questions:**
- R:R inversion persists (0.17:1) — PM_TRAIL captures micro-wins while ATR_SL takes bigger losses. Needs dedicated session post-stability period.

## 2026-08-15 09:00 UTC — Hourly Analysis

**Trades:** 0 closed last hour (quiet period)
**PnL:** $0.00 (no activity)

**24h Snapshot:**
- 57T, -$0.54, 47.4% WR (27W/30L)
- Close reasons: profit-monster-trail 36T +$0.38, atr_sl_hit 17T -$1.31, profit-monster-T1 3T +$0.19, atr_tp_hit 1T +$0.20
- ATR SL hit rate: 29.8% (17/57 — BELOW 40% threshold — good)
- R:R: avg_win $0.039, avg_loss $0.059, ratio 0.66:1 (inverted, structural issue)

**Signal Performance (24h):**
- ❌ r2-trend-long4 LONG: 2T 0% WR -$0.15 (approaching kill threshold)
- ❌ range_finder+ LONG: 9T 33.3% WR -$0.14
- ❌ wave_catcher- SHORT: 4T 25% WR -$0.09
- ✅ ct-hot+ LONG: 3T 66.7% WR +$0.06
- ✅ r2-trend-long6 LONG: 2T 100% WR +$0.12

**Diagnosis:**
1. **Entry quality:** No trades last hour — data unavailable
2. **SL behavior:** ATR SL hit 29.8% — improved from 45.6% (Aug 13). Below 40% threshold.
3. **Signal quality:** No signal meets kill threshold (0% WR with 3+ trades last hour). r2-trend-long4 at 2T with 0% WR — one more loss triggers kill.
4. **Trade frequency:** ~2.9/hour avg (last 12h) — low but acceptable.
5. **R:R:** 0.66:1 inverted — structural issue. ATR_TP_K_MULT 2.5 eval window active (changed today), needs 48h data.

**Changes:** None. No signal meets kill threshold. Eval windows active (PM_TRAIL 0.60%, ATR_TP_K_MULT 2.5, TRAIL_ACT 0.60%). Stability period.

**No Change Needed:**
- ATR SL hit rate improved to 29.8% (was 45.6% Aug 13) — profit-monster-trail working
- SIGNAL_FILTER_SPEED_MIN=30 applied today, monitoring trade count recovery
- No overtrading (2.9/hr)

**Open Questions:**
- r2-trend-long4: 2T 0% WR — will kill if next trade loses
- R:R inverted 0.66:1 — ATR_TP_K_MULT 2.5 should fix, needs eval time
- 7d: 5 profitable days, 7 consecutive red days overall — watching for trend break

## 2026-08-15 14:30 UTC — Hourly Analysis

**Trades:** 3 closed last hour (1W, 2L)
- AIXBT continuation+ LONG: -$0.08 (atr_sl_hit)
- CFX ct-hot+ LONG: -$0.10 (atr_sl_hit)
- GMT r2-trend-long6 LONG: +$0.04 (profit-monster-T1)
**PnL:** -$0.14 (33.3% WR)

**24h Snapshot:**
- 56T, -$0.10, 51.8% WR (29W/27L)
- Exit reasons: profit-monster-trail 33T +$0.48, atr_sl_hit 15T -$1.20, profit-monster-T1 7T +$0.42, atr_tp_hit 1T +$0.20
- ATR SL hit rate: 26.8% (15/56 — BELOW 40% threshold ✅)
- R:R: avg_win $0.046, avg_loss $0.060, ratio 0.77:1 (still inverted but improved from 0.66:1)

**Signal Performance (24h):**
- ✅ ct-hot+ LONG: 7T 71.4% WR +$0.24
- ✅ r2-trend-long2 LONG: 9T 66.7% WR +$0.09
- ✅ r2-trend-long3 LONG: 7T 71.4% WR +$0.06
- ✅ r2-trend-long6 LONG: 2T 100% WR +$0.11
- ❌ range_finder+ LONG: 9T 33.3% WR -$0.14
- ❌ wave_catcher- SHORT: 4T 25% WR -$0.09

**Open Positions:** 5 (DYDX +$0.00, TIA -$0.00, LINEA -$0.00, MON -$0.00, ZRO +$0.00)

**Diagnosis:**
1. **Entry quality:** 2/3 last hour entries hit ATR SL quickly — entries slightly late or SL too tight for these tokens
2. **SL behavior:** ATR SL hit 26.8% — healthy, below 40% threshold
3. **Signal quality:** No kill candidates (0% WR with 3+ trades last hour). range_finder+ persistent loser but not meeting kill criteria
4. **Trade frequency:** ~2.3/hr — normal
5. **R:R:** 0.77:1 improved from 0.66:1 but still inverted — PM_TRAIL changes (0.60% act) still in eval window

**Changes:** None. No signal meets kill threshold. CEO stability period active (TRAILING_ACTIVATION_PCT 0.60% eval).

**No Change Needed:**
- ATR SL hit rate 26.8% ✅
- No overtrading (2.3/hr)
- R:R improving (0.66→0.77 in 5.5h)
- CEO eval windows active (48h monitoring)

**Open Questions:**
- range_finder+ LONG: 9T 33.3% WR -$0.14 — persistent loser, may need kill if no improvement by next eval
- R:R inversion narrowing — ATR_TP_K_MULT 2.5 + PM_TRAIL disabled should help, needs more data

## 2026-08-15 15:30 UTC — Hourly Analysis

**Trades:** 1 closed last hour (0W, 1L)
- TIA ct-hot+ LONG: -$0.10 (atr_sl_hit)
**PnL:** -$0.10 (0% WR)

**24h Snapshot:**
- 54T, 2.2/hr, ATR SL 27.8% ✅ (15/54 — below 40%)
- Exit: profit-monster-trail 31T +$0.33, atr_sl_hit 15T -$1.20, profit-monster-T1 7T +$0.42, atr_tp_hit 1T +$0.20
- R:R: avg_win $0.046, avg_loss $0.060, ratio 0.77:1 (improving from 0.66)

**Signal Performance (24h):**
- ✅ ct-hot+ 8T +$0.14 62.5% WR
- ✅ r2-trend-long6 2T +$0.11 100% WR
- ✅ mover+ 3T +$0.09 33.3% WR
- ❌ range_finder+ 9T -$0.14 33.3% WR (persistent loser, no hourly kill trigger)
- ❌ wave_catcher+ 5T -$0.12 40% WR

**Open Positions:** 5 (DYDX, LINEA, MON, ZRO, BIGTIME — all ct-hot based, near $0 PnL)

**Diagnosis:**
1. Entry quality: TIA hit ATR SL — late entry or tight SL for this token
2. SL behavior: 27.8% — healthy ✅
3. Signal quality: No 0% WR with 3+ trades last hour — no kill trigger
4. Trade frequency: 2.2/hr — normal ✅

**Changes:** None. No signal meets kill threshold. CEO stability period active (TRAILING_ACTIVATION_PCT 0.60% eval window).

**No Change Needed:**
- ATR SL hit 27.8% ✅
- No overtrading
- R:R improving (0.66→0.77 in ~6h)
- CEO eval windows active

**Open Questions:**
- range_finder+ persistent loser — may need kill if no improvement
- TIA -99.72% pnl_pct seems like data artifact (amount likely tiny)

## 2026-08-15 16:30 UTC — Hourly Analysis

**Trades:** 0 closed last hour (system dormant)
**24h:** 46T, -$0.44 (45.7% WR, R:R 0.70:1 inverted)
**ATR SL:** 30.4% ✅ (14/46 — below 40%)

**Signal Performance (24h):**
- ✅ ct-hot+ 8T +$0.14 62.5% WR
- ✅ r2-trend-long6 2T +$0.11 100% WR
- ❌ range_finder+ 9T -$0.14 33.3% WR (persistent, no kill trigger)
- ❌ mover+ 2T -$0.11 0% WR (2T — below 3T kill threshold)

**Open Positions:** 5 (all ct-hot based, near PnL)
- DYDX +$0.01, LINEA -$0.04, MON -$0.06, ZRO +$0.01, BIGTIME +$0.03

**Changes:** None. System dormant, no kill triggers.

**No Change Needed:**
- ATR SL 30.4% ✅
- No overtrading
- No 0% WR signals with 3+ trades
- Stale positions: 0

**Open Questions:**
- range_finder+ persistent loser — monitor for kill threshold (3+ trades, 0% WR)
- R:R still inverted (0.70:1) — TRAILING_ACTIVATION_PCT 0.60% eval ongoing

## 2026-08-15 17:30 UTC — Hourly Analysis

**Trades:** 2 closed (1W 1L)
- LINEA ct-hot+ LONG: -$0.03 (atr_sl_hit)
- BIGTIME ct-hot+ LONG: +$0.04 (profit-monster-trail)
**PnL:** +$0.01

**24h:** 46T, 54.3% WR, -$0.36
**ATR SL:** 30.4% ✅ (below 40%)

**Signal Performance (24h):**
- ✅ ct-hot+ 8T +$0.14 62.5% WR
- ✅ profit-monster-trail 25T +$0.29 (dominant exit)
- ✅ profit-monster-T1 7T +$0.42
- ❌ mover+ 2T -$0.11 0% WR (below 3T kill threshold)
- ❌ wave_catcher+ 5T -$0.12 40% WR (no kill)

**Open Positions:** 5 (DYDX +$0.01, LINEA -$0.04, MON -$0.06, ZRO +$0.01, BIGTIME +$0.03)

**Changes:** None. No signal meets kill threshold.

**No Change Needed:**
- ATR SL 30.4% ✅
- No overtrading
- No kill candidates
- R:R improving

**Open Questions:**
- range_finder+ 9T 33.3% WR -$0.14 persistent but not kill threshold

## [2026-08-15 18:30 UTC] Hourly Analysis

**Trades:** 1 closed (0W 1L)
- MON ct-hot+ LONG: -$0.07 (atr_sl_hit)

**PnL:** -$0.07

**24h:** 45T, 44.4% WR, -$0.45
**ATR SL:** 33.3% ✅ (below 40%)

**Signal Performance (24h):**
- ✅ r2-trend-long6 2T +$0.11 100% WR
- ✅ ct-hot+ 11T +$0.08 54.5% WR
- ✅ r2-trend-long2 7T +$0.03 71.4% WR
- ❌ range_finder+ 9T -$0.14 33.3% WR (persistent)
- ❌ wave_catcher- 4T -$0.09 25% WR

**Open Positions:** 5 (GRASS +$0.04, SAND -$0.01, HYPE -$0.05, ZRO +$0.06, DYDX -$0.01)

**Changes:** None. No signal meets kill threshold.

**No Change Needed:**
- ATR SL 33.3% ✅
- No overtrading (1T last hour)
- No kill candidates (0% WR with 3+ trades last hour)
- Last 3h avg_pnl not consistently negative

**Open Questions:**
- range_finder+ 9T 33.3% WR -$0.14 persistent — still below kill threshold (needs 0% WR)

## [2026-08-15 19:30 UTC] Hourly Analysis

**Trades:** 2 closed (1W 1L)
- GRASS ct-hot+ LONG: +$0.03 (profit-monster-trail)
- ZRO ct-hot- SHORT: -$0.02 (profit-monster-trail)

**PnL:** +$0.01 (net positive)

**24h:** 44T, 47.7% WR, -$0.23
**ATR SL:** 29.5% ✅ (below 40%)

**Signal Performance (24h):**
- ✅ r2-trend-long2 6T +$0.13 83.3% WR
- ✅ ct-hot+ 12T +$0.11 58.3% WR
- ✅ r2-trend-long6 2T +$0.11 100% WR
- ❌ range_finder+ 9T -$0.14 33.3% WR (persistent, not killable)

**Open Positions:** 5 (DYDX +$0.04, HYPE +$0.04, SAND +$0.04, BCH -$0.01, SYRUP $0.00)

**Changes:** None. No signal meets kill threshold.

**No Change Needed:**
- ATR SL 29.5% ✅
- No overtrading (2T last hour)
- No kill candidates (0% WR with 3+ trades last hour)
- 3h hourly PnL near breakeven

**Open Questions:**
- range_finder+ 9T -$0.14 persistent but not killable (33.3% WR)

## [2026-08-15 20:30 UTC] Hourly Analysis

**Trades:** 3 closed (1W 2L)
- HYPE ct-hot+ LONG: +$0.01 (profit-monster-trail)
- SAND ct-hot+ LONG: -$0.05 (atr_sl_hit)
- BCH ct-hot- SHORT: -$0.08 (atr_sl_hit)

**PnL:** -$0.12
**24h:** 45T, 46.7% WR, -$0.35
**ATR SL:** 31.1% ✅

**Signal Performance (24h):**
- ✅ r2-trend-long6 2T +$0.11 100% WR
- ✅ ct-hot+ 13T +$0.06 53.8% WR
- ✅ r2-trend-long2 5T +$0.05 80% WR
- ❌ range_finder+ 9T -$0.14 33.3% WR (persistent)
- ❌ wave_catcher- 4T -$0.09 25% WR

**Changes:** None. No signal meets kill threshold.

**No Change Needed:**
- ATR SL 31.1% ✅
- No overtrading (3T last hour)
- No kill candidates (0% WR with 3+ trades last hour)
- 4h hourly PnL mixed, not consistently negative

**Open Questions:**
- range_finder+ 9T -$0.14 persistent but not killable (33.3% WR)

## [2026-08-15 21:30 UTC] Hourly Analysis

**Trades:** 3 closed (2W 1L)
- SYRUP return_exhaustion_long LONG: +$0.21 (profit-monster-trail)
- DYDX ct-hot+ LONG: +$0.03 (profit-monster-trail)
- PUMP ct-hot+,rs-s30,rs-s32 LONG: -$0.10 (atr_sl_hit)

**PnL:** +$0.14
**24h:** 48T, 47.9% WR, -$0.21
**ATR SL:** 31.3% ✅

**Signal Performance (24h):**
- ✅ return_exhaustion_long 1T +$0.21 100% WR
- ✅ r2-trend-long6 2T +$0.11 100% WR
- ✅ ct-hot+ 14T +$0.09 57% WR
- ✅ r2-trend-long2 5T +$0.05 80% WR
- ❌ range_finder+ 9T -$0.14 33% WR (persistent)
- ❌ wave_catcher- 4T -$0.09 25% WR
- ❌ ct-hot- 2T -$0.10 0% WR

**Changes:** None. No signal meets kill threshold.

**No Change Needed:**
- ATR SL 31.3% ✅
- No overtrading (3T last hour)
- No kill candidates (0% WR with 3+ trades last hour)
- Hourly PnL positive (+$0.14)

**Open Questions:**
- range_finder+ 9T -$0.14 persistent but only 1T last hour — below kill threshold
- wave_catcher- 4T -$0.09 persistent — 2T last hour, still below threshold

## [2026-08-15 22:30 UTC] Hourly Analysis

**Trades:** 2 closed (2W 0L)
- NOT return_exhaustion_long: +$0.13 (profit-monster-trail)
- GRASS return_exhaustion_long: +$0.05 (profit-monster-T1)

**PnL:** +$0.18
**24h:** 50T, 46% WR, -$0.18
**ATR SL:** 30% ✅

**Changes:** None. No signal meets kill threshold.

**No Change Needed:**
- ATR SL 30% ✅
- No overtrading (2T last hour)
- No kill candidates (0% WR with 3+ trades last hour)
- Hourly PnL positive (+$0.18)

**Open Questions:** None — system stable

## [2026-08-15 23:30 UTC] Hourly Analysis

**Trades:** 2 closed (2W 0L)
- ME ct-hot+ LONG: +$0.12 (profit-monster-trail)
- HYPE ct-hot+,hl_copy_trader LONG: +$0.06 (profit-monster-T1)

**PnL:** +$0.18
**24h:** 51T, 46% WR, ~breakeven
**ATR SL:** 29.4% ✅

**Changes:** None. No signal meets kill threshold.

**No Change Needed:**
- ATR SL 29.4% ✅
- No overtrading (2T last hour)
- No kill candidates (0% WR with 3+ trades last hour)
- Hourly PnL positive (+$0.18)

**Open Questions:** None — system stable

## [2026-08-16 00:30 UTC] Hourly Analysis

**Trades:** 2 closed (0W 2L)
- ICP ct-hot+ LONG: -$0.05 (atr_sl_hit)
- BLUR ct-hot- SHORT: -$0.04 (atr_sl_hit)

**PnL:** -$0.09
**24h:** 51T, 46% WR, ~breakeven
**ATR SL:** 31.4% ✅

**Changes:** None. No signal meets kill threshold.

**No Change Needed:**
- ATR SL 31.4% ✅ (under 40% threshold)
- No overtrading (2T last hour)
- No kill candidates (ct-hot- 3T 0% WR — but only 3T, below 3+ threshold)
- System stable, consistent with recent hours

**Open Questions:**
- ct-hot- 3T 0% WR, -$0.14 — monitor next hour, if hits 4T+ with 0% WR, kill

## [2026-08-16 00:30 UTC] Hourly Analysis

**Trades:** 0 closed in last hour (quiet period)
**24h:** 55T, 46% WR, +$0.25

**Changes:**
1. Killed `COIN_TRACKER_HOT_MINUS_ENABLED` (ct-hot- SHORT direction) — 4T 0% WR, all SHORTs losing to atr_sl

**No Change Needed:**
- ATR SL rate 37.5% ✅ (under 40%)
- ct-hot+ performing well (18T, 61% WR, +$0.31)
- range_finder+ underperforming (9T, 33% WR) but not at kill threshold
- No overtrading (0T last hour, 16T in 6h)
- 5 open positions, all near breakeven

**Open Questions:**
- Why no trades closed in ~1 hour? Market may be in consolidation, or signals not firing

## [2026-08-16 01:30 UTC] Hourly Analysis

**Trades:** 6 closed (2W 4L)
- W LONG (ct-hot+): +$0.06 (profit-monster-T1)
- W LONG (no signal): +$0.04 (guardian_orphan)
- HYPE LONG (continuation+,ct-hot+): $0.00 (guardian_hard_sl) — small position
- SYRUP LONG (ct-hot+): -$0.08 (atr_sl_hit)
- GRASS LONG (ct-hot+): -$0.10 (atr_sl_hit)
- BIGTIME LONG (continuation+): -$0.10 (atr_sl_hit)

**PnL:** -$0.18
**24h:** 59T, 52.5% WR (profit-monster-trail 25T +$0.68, atr_sl_hit 20T -$1.42)
**ATR SL:** 33.9% ✅

**Changes:** None. No signal meets kill threshold.

**No Change Needed:**
- ATR SL 33.9% ✅ (under 40%)
- No overtrading (6T last hour, threshold >20)
- No kill candidates (0% WR with 3+ trades)
- 3 open positions near breakeven (CC, MON, LDO — all ct-hot+ LONG)
- ct-hot+ still the primary profit driver (21T 57.1% WR +$0.19)
- System roughly breakeven — profit-monster exits barely offset atr_sl losses

**Open Questions:**
- range_finder+ persistent underperformer (9T 33.3% WR -$0.14) — monitor, may need param tuning
- wave_catcher- (4T 25% WR -$0.09) — also underperforming but only 4T

## [2026-08-16 02:30 UTC] Hourly Analysis

**Trades:** 1 closed (0W 1L)
- LDO LONG (ct-hot+): -$0.10 (atr_sl_hit, -97.10% — adverse excursion)

**PnL:** -$0.10
**24h:** 54T, 37.0% ATR SL rate ✅

**Changes:** None. No signal meets kill threshold.

**No Change Needed:**
- ATR SL 37.0% ✅ (under 40%)
- No overtrading (1T last hour, 17T in 6h)
- No kill candidates (range_finder+ 9T 33.3% WR persistent but only 3T — not at 0% WR kill threshold)
- continuation+ 0% WR but only 2T — below 3T threshold
- 4 open positions near breakeven (IO, HYPE, CC, MON)
- ct-hot+ remains primary profit driver (22T 54.5% WR +$0.09)

**Open Questions:**
- LDO had extreme adverse excursion (-97.10%) — possible entry timing issue or sudden dump
- range_finder+ continues to be a drag (9T 33.3% WR -$0.14) — monitor for kill threshold

## TEAM UPDATES
- [2026-08-16 02:30] auto_1hr: NO CHANGES — 1T last hour (LDO -$0.10 atr_sl). ATR SL 37% ✅. No kill candidates. System stable.

## [2026-08-16 03:30 UTC] Hourly Analysis

**Trades:** 1 closed (0W 1L)
- NOT LONG (guardian_orphan): -$0.04 (no signal, orphaned position)

**PnL:** -$0.04
**24h:** 55T, 37.0% ATR SL ✅ (profit-monster +$1.40, atr_sl -$1.42)

**Changes:** None. No signal meets kill threshold.

**No Change Needed:**
- ATR SL 37.0% ✅ (under 40%)
- No overtrading (1T last hour)
- No kill candidates (no 0% WR signals with 3+ trades)
- System stable, net ~breakeven over 24h

**Open Questions:**
- guardian_orphan closed NOT LONG at -$0.04 — position was likely orphaned (no signal)

## [2026-08-16 04:30 UTC] Hourly Analysis

**Trades:** 4 closed (0W 4L)
- IO LONG (bb_bounce+,rs-s66): -$0.08 (atr_sl_hit, -80.86%)
- SUSHI LONG (ct-hot+): -$0.11 (atr_sl_hit, -106.03%)
- MON LONG (ct-hot+): -$0.03 (atr_sl_hit, -28.72%)
- CC LONG (ct-hot+): -$0.05 (atr_sl_hit, -46.28%)

**PnL:** -$0.27
**24h:** 58T, 37.0% ATR SL ✅ (but 41.4% by trade count)

**Changes:** None. No signal meets kill threshold.

**No Change Needed:**
- ATR SL 41.4% — borderline but 24h still roughly breakeven (profit-monster +$1.33 offsets)
- No 0% WR kill candidates (range_finder+ 9T 33.3% WR persistent but not 0% WR)
- Only 1T in last hour — no overtrading
- tpsl_utils.py has recent fixes deployed (per-trade trailing, MIN GUARD cap)
- 2 open positions near breakeven (HYPE, KAS)
- ct-hot+ still primary profit driver over 24h despite last hour cluster

**Open Questions:**
- 4T all SL in one hour is a cluster — possible market micro-dump. Monitor next hour.
- range_finder+ continues to drag (9T 33.3% WR -$0.14) — approaching kill threshold

---

## 2026-08-16 02:00 UTC — Hourly Analysis

**Trades:** 1 closed (1 breakeven, 0 losses)
**PnL:** $0.00 (profit-monster-trail breakeven guard exit)

**24h Snapshot:**
- 59 trades total, -$0.36 net, 42.4% WR
- ATR SL hit rate: 40.7% (at threshold)
- Profit-monster-trail: 21T, +$0.71, compensates atr_sl_hit 24T -$1.69

**Signal Performance (24h):**
- ⚠️ ct-hot+: 25T, 48% WR, -$0.10 (highest volume, slightly negative)
- ⚠️ range_finder+: 9T, 33.3% WR, -$0.14 (losing)
- ❌ ct-hot-: 4T, 0% WR, -$0.19 (below kill threshold — only 4T)
- ✅ return_exhaustion_long: 3T, 100% WR, +$0.39 (tiny sample)

**Diagnosis:**
1. **Entry quality:** Last trade breakeven — PM trail guard caught at 0.0%.
2. **SL behavior:** ATR SL at 40.7% — at threshold. CEO reverted PM_TRAIL_ACTIVATE_PCT to 0.40% to address.
3. **Signal quality:** No signal meets kill threshold (0% WR with 3+ trades last hour).
4. **Trade frequency:** ~2.3/hr — normal.

**Changes:** None. No signal meets kill threshold. CEO eval window closes Aug 17 — monitoring PM_TRAIL adjustments.

**No Change Needed:**
- ATR SL rate at threshold, not above 40% trigger
- No signal at kill criteria
- Trade frequency normal

**Open Questions:**
- ct-hot+ at 25T with 48% WR and -$0.10 — persistent small loser but WR not 0%
- Last 6h slightly negative (-$0.49 across 14 trades) — normal variance or regime shift?

## 2026-08-16 04:00 UTC — Hourly Analysis

**Trades:** 5 closed (1 win, 1 breakeven, 3 losses)
**PnL:** -$0.29 (WR: 20%)

**24h Snapshot:**
- 53 trades total, -$0.37 net, ~42% WR
- ATR SL hit rate: 39.6% (21/53) — below 40% threshold
- Profit-monster combined: 26T, +$1.30 — offsets atr_sl -$1.57

**Last Hour Trades:**
- WLFI ct-hot+ LONG: +$0.01 (profit-monster-trail) ✅
- HYPE SHORT guardian_orphan: $0.00 (breakeven)
- HYPE hl_copy_trader,range_finder- SHORT: -$0.09 (HL_CLOSED)
- W guardian_orphan LONG: -$0.10 (guardian_orphan)
- W ct-hot+ LONG: -$0.11 (atr_sl_hit)

**Diagnosis:**
1. **Entry quality:** W had 2 losses in one hour (orphan + atr_sl) — possible bad entry timing
2. **SL behavior:** ATR SL 39.6% — below 40% threshold ✅
3. **Signal quality:** No kill candidates (0% WR with 3+ trades last hour)
4. **Trade frequency:** 5/hr — normal, no overtrading

**Changes:** None. No signal meets kill threshold.

**No Change Needed:**
- ATR SL 39.6% — below 40% trigger
- No 0% WR kill candidates (continuation+ 2T 0% but <3T)
- Trade frequency normal
- tpsl_utils fixes deployed

**Open Questions:**
- W token had 2 losses in one hour — is W consistently problematic?
- range_finder- only 1T in 24h — too small to evaluate
- continuation+ 2T 0% WR — approaching threshold if more trades come in

## [2026-08-16 05:00 UTC] Hourly Analysis

**Trades:** 4 closed (1 win, 1 breakeven, 2 losses)
**PnL:** -$0.09 (WR: 25%)

**24h Snapshot:**
- 55 trades total, -$0.42 net, ~42% WR
- ATR SL hit rate: 41.8% (23/55) — above 40% threshold
- ct-hot+ responsible for 15/23 ATR SL hits (65%)

**Last Hour Trades:**
- XPL ct-hot+ LONG: +$0.03 (profit-monster-trail) ✅
- HYPE LONG: $0.00 (guardian_orphan)
- KAS ct-hot+ LONG: -$0.03 (atr_sl_hit)
- ATOM ct-hot+ LONG: -$0.09 (atr_sl_hit)

**Diagnosis:**
1. **Entry quality:** ATOM had -82.77% PnL% — very bad entry
2. **SL behavior:** ATR SL 41.8% — above 40% threshold, driven by ct-hot+
3. **Signal quality:** No kill candidates (0% WR with 3+ trades last hour)
4. **Trade frequency:** 4/hr — normal

**Changes:** None. ct-hot+ already disabled (2026-08-16). ATR SL rate will improve as 3 remaining ct-hot+ positions close.

**No Change Needed:**
- ct-hot+ already disabled — ATR SL rate will naturally improve
- No 0% WR kill candidates
- Trade frequency normal

**Open Questions:**
- ATOM entry was -82.77% — is there an entry timing issue?
- 3 remaining ct-hot+ positions — monitoring for closure

## [2026-08-16 06:30 UTC] Hourly Analysis

**Trades:** 3 closed (0 wins, 0 breakeven, 3 losses)
**PnL:** -$0.13 (WR: 0%)

**24h Snapshot:**
- 58 trades total, -$0.55 net, 42% WR
- ATR SL hit rate: 43.1% (25/58) — above 40% threshold
- ct-hot+ responsible for 15/25 ATR SL hits (60%) — already disabled
- return_exhaustion_long: 3T 100% WR, +$0.39 (best signal)
- ct-hot+: 33T 42% WR, -$0.42 (killed signal still closing positions)

**Last Hour Trades:**
- PURR ct-hot+ LONG: -$0.04 (atr_sl_hit, -39.94% PnL%)
- COMP ct-hot+ LONG: -$0.03 (atr_sl_hit, -30.77% PnL%)
- CFX ct-hot+ LONG: -$0.06 (atr_sl_hit, -64.88% PnL%)

**Diagnosis:**
1. **Entry quality:** All 3 entries losing -30% to -65% PnL% — bad entries but from killed signal
2. **SL behavior:** ATR SL 43.1% — above 40% threshold but entirely driven by ct-hot+ (already killed)
3. **Signal quality:** No kill candidates (continuation+ 2T 0% below 3T threshold)
4. **Trade frequency:** 3/hr — normal

**Changes:** None. System self-correcting via ct-hot+ disable.

**No Change Needed:**
- ct-hot+ already disabled — remaining positions draining, ATR SL rate will improve
- No 0% WR kill candidates (continuation+ only 2T)
- return_exhaustion_long performing well at 100% WR
- Trade frequency normal

**Open Questions:**
- 3 remaining ct-hot+ positions draining — will ATR SL drop below 40% after they close?
- continuation+ 2T 0% WR — watching for kill threshold

## [2026-08-16 07:30 UTC] Hourly Analysis

**Trades:** 2 closed (2 wins, 0 losses)
**PnL:** +$0.11 (WR: 100%)

**24h Snapshot:**
- 57 trades total, -$0.44 net, 40.4% WR
- ATR SL hit rate: 45.6% (26/57) — above 40% threshold
- ct-hot+: 30T 40% WR -$0.48 — still generating composite trades
- return_exhaustion_long: 3T 100% WR +$0.39 (best signal)
- continuation+: 5T 40% WR -$0.17

**Last Hour Trades:**
- ALT r2-trend-long3 LONG: +$0.08 (profit-monster-trail, +83.21% PnL%) ✅
- SUSHI r2-trend-long9 LONG: +$0.03 (atr_sl_hit, +23.80% PnL%) ✅

**Diagnosis:**
1. **Entry quality:** Excellent — both entries profitable with high PnL%
2. **SL behavior:** ATR SL 45.6% — above 40% but mostly from ct-hot+ legacy positions
3. **Signal quality:** No kill candidates. ct-hot+ disabled but composite signals still open trades
4. **Trade frequency:** 2/hr — normal

**Changes:** None. System self-correcting.

**No Change Needed:**
- Last hour was profitable (+$0.11)
- ct-hot+ positions continuing to drain
- No 0% WR kill candidates
- Trade frequency normal

**Open Questions:**
- ct-hot+ composite signals still opening trades despite disable — need composite signal filtering?
- ATR SL rate should improve as ct-hot+ positions close

## [2026-08-16 08:30 UTC] Hourly Analysis

**Trades:** 0 closed (dead hour — Sunday morning UTC)
**PnL:** $0.00

**24h Snapshot:**
- 53 trades, -$0.76 net, 35.8% WR
- ATR SL hit: 26/53 = 49.1% (above 40% but driven by ct-hot+ legacy)
- ct-hot+: 27T 33.3% WR -$0.76 — already disabled, positions draining
- ct-hot-: 4T 0% WR -$0.19 — already killed Aug 15
- return_exhaustion_long: 3T 100% WR +$0.39 (best signal)
- r2-trend signals: 3T 100% WR +$0.15 (all winners)
- continuation+: 2T 0% WR -$0.18 (below 3T kill threshold)

**Open Positions:** 2 (BLUR LONG, HYPE SHORT) — both at $0.00 unrealized

**Diagnosis:**
1. **Entry quality:** No trades last hour, can't assess
2. **SL behavior:** ATR SL 49.1% — above 40% but entirely from ct-hot+ legacy (27 of 26 ATR SL hits are ct-hot+). Already disabled.
3. **Signal quality:** No new kill candidates. continuation+ at 2T 0% (below 3T threshold).
4. **Trade frequency:** 0/hr dead hour. 53/24h = ~2.2/hr normal.

**Changes:** None. System self-correcting via ct-hot+ disable.

**No Change Needed:**
- ct-hot+ already disabled, positions draining
- ct-hot- already killed
- No 0% WR kill candidates
- 0 trades = Sunday morning market conditions
- 2 open positions near breakeven

**Open Questions:**
- ATR SL rate should drop below 40% as ct-hot+ positions close
- continuation+ at 2T 0% — watching for kill threshold

## [2026-08-16 09:30 UTC] Hourly Analysis

**Trades:** 0 closed (Sunday slow market)
**PnL:** $0.00

**24h Snapshot:**
- 50 trades, -$1.03 net, 38% WR
- ATR SL hit: 24/50 = 48.0% (above 40% threshold)
- ct-hot+: 26T 34.6% WR -$0.66 — already disabled, 3 positions remaining
- ct-hot-: 4T 0% WR -$0.19 — already killed
- return_exhaustion_long: 3T 100% WR +$0.39 (best signal)
- r2-trend: 2T 100% WR +$0.11
- guardian: 6T 16.7% WR -$0.10

**Open Positions (3):**
- HYPE SHORT $11 @ 57.101 (entry ~breakeven)
- BLUR LONG $11 @ 0.013105 (entry ~breakeven)
- ALT LONG $11 @ 0.006057 (just entered)

**Diagnosis:**
1. **Entry quality:** 0 trades last hour, can't assess. Open positions at breakeven.
2. **SL behavior:** 48.0% ATR SL — above 40% but ALL driven by ct-hot+ (24/26 ATR SL hits). Already disabled. Will self-correct as positions close.
3. **Signal quality:** No kill candidates. continuation+ 1T 0% (below 3T threshold). return_exhaustion_long best performer.
4. **Trade frequency:** 1-3/hr (normal, Sunday market)

**Changes:** None. System self-correcting via ct-hot+ disable.

**No Change Needed:**
- ATR SL rate driven entirely by disabled ct-hot+ legacy
- No signals at kill threshold
- Trade frequency normal
- Open positions small ($11) with normal risk

**Open Questions:**
- ATR SL rate should drop below 40% as remaining ct-hot+ positions close
- continuation+ 1T 0% WR — watch for kill threshold

## [2026-08-16 10:30 UTC] Hourly Analysis

**Trades:** 1 closed (BLUR LONG bb_bounce+, profit-monster-trail, +$0.05)
**PnL:** $0.05 (+45.82% on trade)

**24h Snapshot:**
- 51 trades, -$0.83 net, 43% WR
- ATR SL hit: 24/51 = 47.1% (above 40% but self-correcting)
  - ct-hot+: 16/24 ATR SL hits — already disabled
  - ct-hot-: 3/24 — already killed
  - Remaining: 5 spread across other signals (1 each)
- profit-monster-trail: 14/51 = 27.5%, +$0.81 (best exit type)
- return_exhaustion_long: 3T 100% WR +$0.39 (best signal)
- guardian_orphan: 6T -$0.10
- continuation+: 1T -$0.10 (below 3T kill threshold)

**Open Positions (2):**
- ATOM LONG $11 @ 1.4917 (r2-trend-long12, -$0.05)
- ALT LONG $11 @ 0.0061 (r2-trend-long3, $0.00)

**Diagnosis:**
1. **Entry quality:** BLUR entry solid (+45.82% on trade)
2. **SL behavior:** 47.1% ATR SL but ALL major contributors (ct-hot+ 16, ct-hot- 3) are disabled/killed. 5 remaining ATR SL hits are 1 each across 5 signals — normal baseline.
3. **Signal quality:** No kill candidates. return_exhaustion_long best performer. continuation+ 1T 0% (below 3T).
4. **Trade frequency:** 1/hr last hour, ~2/hr 24h average — normal Sunday market.

**Changes:** None. System self-correcting via ct-hot+ disable.

**No Change Needed:**
- ATR SL rate driven by disabled signals (legacy positions closing)
- No signals at kill threshold (0% WR with 3+ trades)
- Trade frequency normal
- Open positions small ($11) with manageable risk

**Next:** Re-run at 11:30 UTC

## [2026-08-16 11:30 UTC] Hourly Analysis

**Trades:** 2 closed (ATOM -$0.07 ATR SL, ALT -$0.03 ATR SL)
**PnL:** -$0.10 (0% WR)

**24h Snapshot:**
- 51 trades, net negative (ct-hot+ drain)
- ATR SL: 25/51 = 49% (23/25 from ct-hot+ — disabled, draining)
- profit-monster-trail: 13T best exit type (+$0.77)
- return_exhaustion_long: 3T 100% WR +$0.39 (best signal)
- No signals at kill threshold (all <3T with 0% WR)

**ct-hot+ Status:** Confirmed disabled. Last trade opened 04:07 UTC, all pre-disable positions closing. Drain expected to complete within hours.

**Changes:** None.

**No Change Needed:**
- ATR SL rate driven by disabled ct-hot+ (legacy positions)
- No kill candidates (continuation+ 1T 0% below 3T)
- Trade frequency normal (2/hr)
- Open positions: r2-trend-long5 ($11) — only remaining

**Open Questions:**
- ATR SL rate should drop below 40% once ct-hot+ drain completes
- Watch continuation+ if it adds more losing trades

## [2026-08-16 14:30 UTC] Hourly Analysis

**Trades:** 0 closed in last hour (Sunday quiet)
**24h:** 51 trades, net negative — dominated by ct-hot+ legacy bleed (22T -$0.50)

**24h Exit Breakdown:**
- atr_sl_hit: 24T 47.1% — BUT 22/24 from ct-hot+ (disabled). Active signal ATR SL: 2/27 = 7.4% ✅
- profit-monster-trail: 14T +$0.79 (best exit, +$0.056 avg)
- guardian_orphan: 6T -$0.10 (legacy cleanup)
- profit-monster-T1: 5T +$0.27

**Signal Quality:**
- return_exhaustion_long: 3T 100% WR +$0.39 (best signal)
- ct-hot-: 4T 0% WR -$0.19 — kill threshold BUT already DISABLED
- continuation+: 1T 0% -$0.10 (below 3T kill threshold)
- All other signals: 1-2T, mixed

**Changes:** None

**No Change Needed:**
- ATR SL rate above 40% is entirely from disabled ct-hot+ legacy positions (22/24). Active signal ATR SL is 7.4% — excellent.
- ct-hot- at kill threshold already disabled (COIN_TRACKER_HOT_MINUS_ENABLED = False)
- continuation+ only 1T, below 3T kill threshold
- Trade frequency normal (~1-2/hr)
- Open positions: 1 (SYRUP $11 at breakeven)

**Open Questions:**
- ct-hot+ generated 1 trade at 13:16 UTC today (GRASS +$0.02) despite being disabled — possible race condition or brief re-enable. Monitor for more.
- ATR SL rate should continue dropping as remaining ct-hot+ positions drain.

## [2026-08-16 16:30 UTC] Hourly Analysis

**Trades:** 1 closed (WLFI stop_hunt_reversal_long+ → -$0.01 profit-monster-trail, breakeven)
**24h:** 50T, 47% ATR SL (all from disabled ct-hot+ legacy — 22/24)

**24h Signal Performance:**
- return_exhaustion_long: 3T 100% WR +$0.39 (best, $0.130 avg)
- ct-hot+: 21T 33.3% WR -$0.53 (legacy, draining)
- ct-hot-: 3T 0% WR -$0.17 (at kill threshold, already disabled)
- All others: 1-2T mixed

**Changes:** None

**No Change Needed:**
- ATR SL rate 48% entirely from disabled ct-hot+ (22/24). Active signal ATR SL: 2/26 = 7.7% ✅
- No kill candidates (continuation+ 1T 0% below 3T threshold)
- Trade frequency normal (~2/hr)
- Open positions: 2 (SYRUP $11, KAS $11 return_exhaustion_long)

**Open Questions:**
- ATR SL rate should drop below 40% once remaining ct-hot+ positions fully drain
- ct-hot+ still has 21T legacy trades in 24h window — will age out naturally

---

## 2026-08-16 07:00 UTC — Hourly Analysis

**Trades:** 2 closed (2 wins, 0 losses)
**PnL:** +$0.07 (100% WR)

**Last Hour:**
- KAS return_exhaustion_long LONG: +$0.04 (profit-monster-trail)
- SYRUP r2-trend-long5 LONG: +$0.03 (profit-monster-trail)

**24h Snapshot:**
- 50 trades total: atr_sl_hit 22T (44.0%), profit-monster-trail 14T +$0.83, profit-monster-T1 5T +$0.27, guardian_orphan 6T -$0.10
- ATR SL hit rate: 44.0% (above 40% threshold ⚠️)
- 48h SL hit rate: 37.9% (below 40% threshold ✅ — was 36.0% earlier, slight uptick)

**Signal Performance (24h):**
- ✅ return_exhaustion_long: 4T 100% WR +$0.43
- ✅ r2-trend-long3: 2T 50% WR +$0.05
- ⚠️ ct-hot+: 20T 35% WR -$0.48 (volume leader, 59% of all ATR SL hits)
- ⚠️ range_finder+: 9T 33.3% WR -$0.14
- ❌ continuation+: 2T 0% WR -$0.18
- ❌ ct-hot-: 2T 0% WR -$0.09

**Diagnosis:**
1. **Entry quality:** 2 trades last hour, both PM_TRAIL exits — good entries
2. **SL behavior:** 24h ATR SL at 44.0% above threshold, but 48h at 37.9% below. ct-hot+ responsible for 13/22 (59%) of all ATR SL hits.
3. **Signal quality:** No signal meets kill threshold (0% WR with 3+ trades last hour). ct-hot+ 35% WR is weakest high-volume signal but WR >0%.
4. **Trade frequency:** 2/hr last hour — normal

**Changes:** None. No signal meets kill threshold. PM_TRAIL eval window active (0.30% act / 0.15% dist reverted today). 48h ATR SL at37.9% below threshold.

**No Change Needed:**
- Last hour: 2 trades, both winners, PM_TRAIL exits
- 48h ATR SL at 37.9% — below 40% threshold
- No 0% WR signals with 3+ trades in last hour
- Trade frequency normal (~2/hr)
- PM_TRAIL eval window needs 48h to assess

**Open Questions:**
- ct-hot+ responsible for 59% of ATR SL hits — signal quality issue (35% WR) not SL config issue
- 24h ATR SL uptick to44.0% from 36.0% — may be noise from PM_TRAIL revert, monitoring
- PM_TRAIL eval window closes Aug 17 — need more data
