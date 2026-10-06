# Current State — CEO Run 13:55 UTC

**Last Updated: 2026-10-06 13:55 UTC**
**Updated by: CEO — verified PG run, no trading config changes**

## CEO RUN 13:55 — VERIFIED, RATIFIED, NO CONFIG CHANGES

**PG verified direct (not memory):** 24h **19T −$0.81 42.1%WR** | 7d **221T +$0.31 53.4%** (LONG +$1.38/179T 55.3%, SHORT **−$1.07/42T 45.2%**) | 30d **945T −$3.41 51.1%**. Open **1**: ENS oversold-bounce+ LONG @6.875 (12:57). Regime SHORT_BIAS (17L/21S/82N). Hotset empty (fallback DB 0). Disk 84%. Pipeline healthy.

**7d PnL flipped POSITIVE** (+$0.31) vs morning orchestrator −$0.66. SHORT still bleeding but improved from −$1.88.

**7d exit bleed:** hard_max_loss **56T −$7.99 #1** | hard_sl 14T −$2.67 | cut-loser-MAE-GUARD 3T −$0.37 | atr_sl_hit only **1T** (ATR_TP_MIN=0.013 holding).

### DECISIONS THIS RUN
1. **RATIFY 45da8fcf** — trendline_bounce_long confidence boost (BASE 70→75, max 88→92, distance bonus). 0 trades all-time → boost cannot cause bleed. Monitor: if 0 trades by 2026-10-13, blocker is detection not confidence.
2. **0 trading config changes** — best signals already tuned; bleed path delegated; regime habitats correct; protected flags untouched.
3. **hard_max_loss root cause CONFIRMED** — `compute_live_pnl` (pnl_utils.py) is unleveraged price %; CUT_LOSER_PNL=-1.00 fires at −1% price = −3−5% account at lev 3–5. Value NOT changed (standing rule). Semantics fix = bug_hunter with this evidence.
4. **Oversold SHORT guard VERIFIED HOLDING** — 0 RSI<25 entries since brain.py guard ~06:45. Pre-guard LTC RSI 9.90 closed −5.57% hard_max_loss. Metric PASS at first checkpoint.
5. **Disabled signals CLEAN** — mtf-regime-trend+/-, accel-300-, pump-chain-v5: **0 post-kill trades**. 7d "losers" are historical aging out of window. Flags effective.
6. **pump-chain- EXTREME habitat KEEP** — 24T −$0.05 50% (MoE habitat, DO NOT revert 1.0). NORMAL 3T −$0.32 33% small-n. decider_run EXTREME block flag False (aligned with vol gate 1.0).
7. **Best signals untouched** — pump-chain+ 10T 70% +$1.09 (boost 1.2 already live; 30d RSI 70+ still net +$0.50 — do NOT tighten) | bb-bounce-v2-long+ 12T 75% +$0.30 (1.4 live, PM trail 90%) | volume-breakout-long+ 5T 60% +$1.50 | doji-bottom-long 8T 75% +$0.11. **No stack-on-winners.**

### VERIFIED — NO CHANGE
- bb-squeeze+ 7d 69T 60.9% −$0.05 — HIGH 40T −$0.26 60% (volume engine, not kill) | NORMAL 18T +$0.25 66.7% (habitat) | EXTREME 13T −$0.25 46.2% (blocked). hard_max_loss tail is exit-structure issue.
- PROFIT_MONSTER_BYPASS pump-chain: KEEP (standing).
- BB_SQUEEZE_LONG_EXTREME_BLOCK_ENABLED=True — live in decider_run bypass catch.

### PROTECTED FLAGS (verified intact)
CONFLUENCE_REQUIRED=True · LIVE_TRADING_ENABLED=True · ATR_TP_MIN=0.013 · BTC_CHOP_GATE_THRESHOLD=0.2 · BTC_CHOP_GATE_3H_PCT=0.5 · CUT_LOSER_PNL=-1.00 · PUMP_CHAIN_V5_ENABLED=False · MTF_REGIME_TREND_MINUS/PLUS_ENABLED=False · ACCEL_300_MINUS_ENABLED=False · RR_ENGINE_SHADOW=True · ATR_SL/PM_TRAIL protected · PUMP_CHAIN_SHORT_EXTREME_BLOCK_ENABLED=False (aligned with vol gate 1.0) · BB_SQUEEZE_LONG_EXTREME_BLOCK_ENABLED=True.

### CRITICAL / OPEN
1. **hard_max_loss leverage semantics** — CONFIRMED root cause, delegated bug_hunter. Metric: 7d bleed −$7.99 → ≥50% cut.
2. **Hotset empty intermittent** — fallback 0 still at 13:51. Deep audit delegated signal_analyst.
3. **SHORT 7d PnL −$1.07** — lever is pump-chain- oversold (now guarded) + hard_max_loss/hard_sl. Target ≥$0 by Oct 7.
4. **trend-ride+** 7T −$0.18 42.9% — n≥10 eval Oct 7. Don't stack filters.
5. **trendline_bounce_long 0 trades all-time** — detection audit if still 0 by Oct 13.
6. **Disk 84%** — prune at 85–88%. No candles vacuum mid-trading.
7. **decider_run v1→v2 + fail-open removal** — still delegated bug_hunter (architectural DRIFT-A root). Fail-closed now live at vol-gate error path (verified in code).
8. **45da8fcf** — RATIFIED this run. Closed.

### METRICS (Oct 12 checkpoint)
| Metric | Current | Target | Deadline |
|--------|---------|--------|----------|
| 24h PnL | −$0.81 | ≥ $0 | next run |
| 7d PnL | **+$0.31** | +$3.00 | keep positive |
| SHORT 7d PnL | −$1.07 | ≥ $0 | 2026-10-07 |
| 30d PnL | −$3.41 | ≥ $0 | 2026-10-11 |
| Oversold SHORT RSI<25 entries | **0 since guard** | 0 | HOLDING |
| hard_max_loss 7d bleed | −$7.99 (56T) | reduced ≥50% | 2026-10-11 |
| Hotset approved | intermittent 0 | sustained >0 | post audit |
| trend-ride+ | 7T −$0.18 | n≥10 eval | 2026-10-07 |
| trendline_bounce_long trades | 0 all-time | n≥1 in 7d | 2026-10-13 |
| bb-bounce-v2-long+ 1.4 | LIVE | 24h n≥5 eval | 2026-10-07 |
| mtf-regime-trend post-kill | 0 trades | stays 0 | ongoing |

## Monitor List (next 48h)
1. **hard_max_loss fix** — bug_hunter with confirmed unleveraged-pnl evidence.
2. **SHORT 7d PnL ≥ $0 by 2026-10-07.**
3. **24h PnL back ≥ $0.**
4. **Hotset empty** — audit in flight; watch approval rate.
5. **trend-ride+ n≥10** Oct 7 — don't stack filters.
6. **trendline_bounce_long** — any trades in 7d post-ratify?
7. **Disk 84%** — prune at 85–88%.
8. **RR_ENGINE_SHADOW=True** until shadow numbers exist.
9. **ENS open trade** — watch, don't auto-close.
10. **Oversold guard** — continue 0 RSI<25 verify.
11. **pump-chain- EXTREME** — habitat keep; watch NORMAL small-n.
12. **IO pnl_usdt accounting** — position_manager fix committed earlier; verify future closes.
13. **HL API key** AGENTS.md reminder still STALE — T to verify.

## Standing Decisions (do not re-litigate)
- **SIGNAL KILL POLICY:** regime-block via volatility_gate_v2 if wins in ANY regime. Blanket-kill ONLY if loses in ALL regimes.
- **SHORT ENTRY MODEL:** exec RSI>=40 all paths; EXTREME habitat; NEUTRAL blocked; HARD_FLOOR=25 no override.
- **ATR_TP_MIN=0.013** — brain_auditor approved, DO NOT REVERT.
- **EXTREME pump-chain- SHORT 0.0→1.0** — DO NOT revert.
- **RR_ENGINE_SHADOW=True** until shadow audit numbers exist.
- **STANDALONE_BYPASS shrink-to-6 REJECTED** — incremental prune only.
- **CUT_LOSER_PNL=-1.00 DO NOT CHANGE** — semantics with bug_hunter (root cause now confirmed unleveraged live_pnl).
- **BTC_CHOP_GATE_THRESHOLD=0.20** / **BTC_CHOP_GATE_3H_PCT=0.50** — live.
- **PUMP_CHAIN_V5_ENABLED=False** — standing disable.
- **PROFIT_MONSTER_BYPASS keeps pump-chain** — verified; removal claim refuted.
- **hermes_constants.py:** do not change VALUES without CEO/T. Crash-bug code fixes allowed.
- **NEUTRAL_SNIPER_ENABLED=False** — human-disabled per T.
- **MTF_REGIME_TREND_MINUS/PLUS_ENABLED=False + NEVER_REENABLE** — killed; 0 post-kill trades verified.
- **ACCEL_300_MINUS_ENABLED=False** — killed Oct 1; 0 post-kill trades verified.
- **45da8fcf trendline_bounce_long boost — RATIFIED 2026-10-06.**
- **bb-bounce-v3-long NOT in STANDALONE_BYPASS** — DRIFT-A closed.
- **Agents commit own files only.**
- **Disk prune** when >88%. Coin_tracker/candles NEVER vacuum during trading.

## Delegated (not orchestrator's call)
- **bug_hunter:** hard_max_loss leverage-aware semantics — CONFIRMED: compute_live_pnl unleveraged vs CUT_LOSER_PNL=-1.00; 7d 56T −$7.99
- **bug_hunter:** decider_run v1→v2 import + fail-open removal (architectural DRIFT-A root) — fail-closed now on vol-gate error path
- **bug_hunter:** cut-loser-CL-T1 MFE audit then fix (30d bleed; 7d label mostly aged out)
- **bug_hunter:** bypass-path full audit remaining (oversold floors on all paths — brain.py guard is first slice)
- **bug_hunter:** DRIFT-I bb-squeeze+ EXTREME block path gap (brain_auditor)
- **self_learner:** 24h oversold SHORT verify post brain.py guard — n=0 so far PASS
- **self_learner:** trend-ride+ habitat data for Oct 7 n≥10 eval
- **signal_analyst:** hotset empty multi-factor audit; ema_reclaim; mover+; coin_tracker Wyckoff/Elliott/Volume signal (1/week)
- **CEO/T:** exit_optimizer_shadow timer; AGENTS.md philosophy ack; HL key verify

## Sideways finds this run
- **pump_chain- SETUP-RECALL spam** — pipeline.log shows repeated `[SETUP-RECALL] FOGO/ME/ALGO/MERL pump-chain- SHORT: n=129 WR=56%` every ~30s for same tokens. Not a trade bug but log noise; if setup-recall is meant to fire once per setup, check dedup. Low severity.
- **decider_run EXTREME block comments stale** — lines 1662-1663 say "EXTREME bleeds / Pump_Flow:0.0" but flag is False and vol gate is 1.0 (correct alignment). Cosmetic comment debt, skip.
- **coin_tracker.db 3.3GB, 112 coins, _meta ts 1791232297** — tracker updating. Dashboard JSON missing at /var/www path (only DB present). If coin_tracker.html expects JSON, check timer/API script. Medium — dashboard may be stale.
- **signal_versions.json pump-chain- non-dict** — still open from auto_1hr (minor).
- **scripts/signal_version.py MISSING** — still open from auto_1hr.

## Orchestrator / CEO Report (2026-10-06 13:55 UTC)
- PG-verified numbers from PostgreSQL brain, not memory. 7d PnL flipped positive.
- RATIFIED 45da8fcf. 0 trading config changes. Protected flags intact.
- hard_max_loss root cause confirmed (unleveraged live_pnl) and re-delegated with evidence.
- Oversold guard verified holding. Disabled signals verified clean.
- Artifacts: automation/ceo/ceo_report.md, automation/ceo/ceo_kanban.md, data/signal_regime_memory.json.
