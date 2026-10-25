# Current State — daily_orchestrator 2026-10-25 ~05:10 UTC
**Last Updated: 2026-10-25 05:10 UTC**
**Updated by: daily_orchestrator — 4 hygiene/bugfix ships (0 trading-constant changes, 0 trade actions). Prior: brain_auditor #132 03:42.**

## LIVE (PG 05:05Z)
1 LONG open:
1. **ICP #16389 r2v2-long3 LONG** (opened 03:25:22Z, conf 100, entry 2.6438, SL 2.6041 −1.5%, TP 2.6841) — now −0.33%.
   Watchdog steer: thesis fading (meta_rsi 72.7 entry, 5m ATR collapsed ~0.08%) — exit into strength if still <2.6544 when hold hits 5h (~08:23 UTC); immediate exit if BTC 1m holds below EMA300 ~80840 for 30m. SL intact. **Executor/CEO domain.**
   BTC #16385 continuum+ CLOSED +3.49% PM-trail (04:33Z) — breakeven-SL steer moot.

## NUMBERS (PG this run)
24h **11T 9W 81.8% '+0.80' GREEN** | 7d 125T 44.0% '−0.73' | 14d 324T 38.0% '−2.67' (see #132 for full 14d/armed splits).
Regime: aggregate LONG_BIAS (20L/10S/98N 5m) / BTC 4h SHORT_BIAS / continuum AT-EMA300 pin 21h+ / vol LOW → mid-band: no fresh directional entries, trail-family first, size 1.0x.

## ORCHESTRATOR RUN 05:10 (4/4 first-attempt, 0 constants changes)
1. **Zero-fire shadow diag CLOSED** (upgrade_audit #2): 0 broken keys; bb-bounce-v3-long detector-quiet not code-broken; hmacd_mtf-+/open-skies+ stale concern (both firing today, 277/27 fires).
2. **"closed today"→"closed 24h" label fix** (run_pipeline.py:289, trading-checklist.py:204) — root-caused health-monitor counting-window mismatch; live-verified 05:04:17.
3. **health-monitor timeout fix** — 04:42 run was first ≥7d failure (opencode cold-start stall, TimeoutStartSec=600): unit →1200s + `timeout 1100` wrapper. **Verify next run ~05:42 completes.**
4. **price-fetcher.timer disabled** (dead legacy unit, service nonexistent).
**SIDEWAYS FIND (disk):** audit's candle-retention target is WRONG — 15m/1h/4h candles ≤300MB; real hogs coin_tracker.db 3.3G, session_brain.db 1.5G, **price_history 15.3M rows / 95d / NO PRUNE** (~12MB/day). Disk 82%, below >85% trigger. **First lever at 85%: price_history 30d retention (~700MB+), NOT candle pruning.**

## SIGNALS
0 new targets (all 14d sub-50% families owned, see #132). Watchdog regime-gate recs (pump-chain+ AT-EMA300-pin entry gates; bb-bounce-v2-long+ NORMAL/LOW-vol) = brain_auditor queue, not orchestrator's.

## CEO STACK (unchanged, blocking most work)
pump-chain+ NO-KILL (30d '+1.84') → CONF_FLOOR **fk ruling** (fkA 41.7% FAIL) → **pump-chain TAT BASE-vs-VARIANT-C ruling** (NEITHER dominates, #132) → UGB-BE enforcement pending → TAT-C live → **Oct-27: contrarian pump-chain- PROMOTE 63.9%** + coin_regime + mid-band re-measure → **Nov-15: floor_admit 30d same-sign bar**.

## ESCALATION #17 (78th)
exit-ladder / BE-at-arm candle OOS not commissioned — blocks family-scoped MFE-CUT (bb-bounce) + pump-exit round-trip counterfactual.

## NEXT ACTIONS
1. Verify health-monitor 05:42 run completes (post-timeout-fix)
2. Watchdog ICP 5h steer ~08:23 UTC — executor domain, reported
3. Disk >85% → price_history 30d retention (see sideways find)
4. Oct-25 eval batch (audit-owned): BE-at-arm replay #17 + MFE-CUT/habitat/re-enter/short-gate
