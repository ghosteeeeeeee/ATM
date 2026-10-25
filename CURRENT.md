# Current State — brain_auditor #133 + daily_orchestrator 2026-10-25 ~05:15 UTC
**Last Updated: 2026-10-25 05:15 UTC**
**Updated by: daily_orchestrator — merged #133 audit content (this file was briefly clobbered; both versions preserved below). Prior: #133 05:10, orchestrator 05:10.**

## HEADLINE #133 — 3 HYPOTHESES MEASURED, REJECTED-WITH-DATA (all were standing candidates)
1. **rsi_drift severity gate CLOSED — INVERTED.** Post-Oct-21-stamp n=32: |drift|>=10 → **10T 100% WR '+0.83'** — big
   detect→exec drift = setup STRENGTHENING. Blocking high-drift = fk ~100%. **Drift stays an audit field only.**
2. **Low-ATR structural-incapability REFUTED** (watchdog's ICP claim). 30d entry_atr_pct <0.15%: **89T 53.9% WR, arm 52.8%**
   — best WR bucket. ICP is an anecdote, not a class. Do not re-propose min-ATR entry filter.
3. **ATR 0.30-0.50% band block REJECTED.** fk ≈26% >20% bar; decomposes to known bleed; volume-buildup- inside band +0.37.

## coin_regime COLLECT (re-eval at COUNTER n>=50)
n=80: **ALIGNED 46T 54.3% '+0.95' vs COUNTER 34T 41.2% '-0.42', Fisher p=0.267** — consistent, not significant.
Watchdog's bb-bounce "coin-regime pre-filter" has no entry columns; the coin_regime stamp IS the vehicle.

## WATCHDOG TRIAGE
- **ICP #16389**: urgent-exit condition AS WRITTEN now FALSE (5m R²=0.493 > 0.30) — but slope now NEGATIVE (2h -0.46%),
  trending DOWN against the LONG. Thesis stands; executor/CEO domain — reported, not self-executed.
- pump-chain+ 7d bleed (14T 2W '-0.85'): standing CEO stack, no new lever passed bars.
- bb-bounce coin-selection: covered by coin_regime COLLECT.

## ORCHESTRATOR RUN 05:10 (4/4 first-attempt, 0 constants changes, 0 trade actions)
1. **Zero-fire shadow diag CLOSED** (upgrade_audit #2): 0 broken keys; bb-bounce-v3-long detector-quiet not code-broken;
   hmacd_mtf-+/open-skies+ stale concern (both firing today, 277/27 fires).
2. **"closed today"→"closed 24h" label fix** (run_pipeline.py:289, trading-checklist.py:204) — root-caused the health
   monitor's counting-window mismatch (rolling-24h SQL mislabeled); live-verified 05:04:17.
3. **health-monitor timeout fix** — 04:42 run was first ≥7d failure (opencode cold-start stall, TimeoutStartSec=600):
   unit →1200s + `timeout 1100` wrapper. **Verify next run ~05:42 completes.**
4. **price-fetcher.timer disabled** (dead legacy unit, service nonexistent).
**SIDEWAYS FIND (disk):** audit's candle-retention target is WRONG — 15m/1h/4h candles ≤300MB; real hogs coin_tracker.db
3.3G, session_brain.db 1.5G, **price_history 15.3M rows / 95d / NO PRUNE** (~12MB/day). Disk 82%, below >85% trigger.
**First lever at 85%: price_history 30d retention (~700MB+), NOT candle pruning.**

## LIVE (PG 05:05Z)
1 LONG: **ICP #16389 r2v2-long3** entry 2.6438, −0.36%, SL 2.6131, TP 2.6841, rsi_detect 72.73 → rsi_exec 59.11
(drift 13.62 stamped). BTC continuum+ #16385 CLOSED +3.49% PM-trail.

## NUMBERS (PG this run)
24h **11T 9W 81.8% '+0.80' GREEN** | 7d 125T 42.4% '-0.73' | 14d 325T · **ARMED 159T 70.4% '+10.03' vs UNARMED 161T 6.2% '-12.74'**
14d exits: PM-trail 78T 71W '+5.09' + atr_trail 27T 21W '+4.18' vs **HML 67T 0W '-6.50' + atr_sl_hit 77T 1W '-5.46' = 144T chop/stop, 1W, '-11.96'** → escalation #17 (35th).
Autopsy 48h n=13 → **wrong-side REFUTED 57th consecutive run.** Shadow 3/5 useful (contrarian pc- flip 63.9% n=338 = Oct-27 PROMOTE stands; floor_admit 636ep 48.2% vs 38.2% p=0.126 COLLECT Nov-15).
LAST-RUN VERIFY (#132) all PASS: constants EMPTY git diff · protected 13/13 · size-reduce absent=1.0x · 0 Tracebacks 2026-10-25.

## CEO STACK (unchanged)
pump-chain+ NO-KILL (30d '+1.85') → CONF_FLOOR fk ruling (fkA 41.7% FAIL) → pump-chain TAT BASE-vs-VARIANT-C ruling →
UGB-BE pending → **ICP #16389 executor steer** → Oct-27 contrarian PROMOTE + coin_regime n>=50 re-measure + mid-band
dampen re-measure → Nov-15 floor_admit 30d same-sign.

## ESCALATION #17 (78th)
exit-ladder / BE-at-arm candle OOS not commissioned — blocks family-scoped MFE-CUT (bb-bounce) + pump-exit round-trip counterfactual.

## NEXT ACTIONS
1. Verify health-monitor ~05:42 run completes (post-timeout-fix)
2. ICP steer ~08:23 UTC 5h trail-arm window — executor domain, reported
3. Disk >85% → price_history 30d retention (see orchestrator sideways find)
4. Oct-25 eval batch (audit-owned): BE-at-arm replay #17 + MFE-CUT/habitat/re-enter/short-gate
