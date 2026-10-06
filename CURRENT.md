# Current State — Post-Freeze Implementation

**Last Updated: 2026-10-06 06:45 UTC**
**Updated by: Daily Orchestrator — post-freeze queue implementation**

## ORCHESTRATOR RUN 06:45 — POST-FREEZE, QUEUE ITEMS SHIPPED

**Freeze b960ffe8 ENDED 00:38.** This run implemented data-backed post-freeze queue items. PG verified from source of truth.

**PG 06:35:** 24h **26T −$1.25 45.8%WR** | 7d **237T −$0.66 55.1%** (LONG +$1.22/191T, SHORT **−$1.88/46T**) | 30d **955T −$2.81 53.7%**. Open **1**: LTC pump-chain- SHORT (entry_rsi_14=**9.90**, opened 03:29). Regime LONG_BIAS. Disk 83%. Pipeline healthy.

**30d exit bleed:** cut-loser-CL-T1 69T −$9.62 | hard_max_loss 57T −$7.86 | atr_sl_hit 350T −$3.68.

### IMPLEMENTED THIS RUN
1. **FAMILY_MAP underscore** (market_phase_gate.py) — bb_bounce_v2_long/v3_long + source forms → Bollinger (were 'Other'). signal_family verified.
2. **brain.py SHORT RSI hard floor** — add_trade rejects SHORT when signal_rsi_14 or metadata rsi < SHORT_RSI_HARD_FLOOR=25. Root cause: LTC entered 03:29 with RSI 9.90 via brain.py path (CTX-GATE may have seen higher live RSI; entry_rsi recorded later). Defense-in-depth, no bear override.
3. **Committed completed post-freeze work** (was uncommitted in working tree): vol-gate mtf-regime-trend- 0.0 all regimes + underscore forms; DRIFT-A VOL-GATE-BYPASS in signal_compactor; bb-bounce-v2-long+ **1.4**; bb_bounce_v3_long conf<=0 habitat fix; position_manager pnl_pct stored fix; FAVORITES/LOSERS automation updates.

### ALREADY LIVE (verified, not re-done)
- bb-bounce-v3 NORMAL 0.0 + HIGH 1.0 (0cb0784b, CEO-ratified). 7d HIGH 5T +$0.11 KEEP / NORMAL 16T −$0.39 blocked.
- bb-bounce-v2-long+ 1.4 RE-APPLIED post-freeze (brain_auditor). 7d all regimes win.
- mtf-regime-trend- **KILLED** (bd1728f4) + NEVER_REENABLE + vol-gate 0.0 defense-in-depth. Post-kill trades: 0.
- bb-bounce-v3-long removed from STANDALONE_BYPASS (DRIFT-A).
- Oversold SHORT floors live in decider_run: HARD_FLOOR=25, fail-closed when both RSI sources None. CTX-GATE verified blocking (CC SHORT LIVE RSI 36.5 < 40).

### VERIFIED — NO CHANGE
- **PROFIT_MONSTER_BYPASS pump-chain: KEEP.** 7d: PUMP_EXIT 9T +$0.94 (8W) | TRAIL 8T +$1.52 (8W) | HARD_MAX 14T −$1.96 (0W). Removal claim NOT supported. Bleed is hard_max/hard_sl, not PM trail.

### PROTECTED FLAGS (verified intact)
CONFLUENCE_REQUIRED=True · LIVE_TRADING_ENABLED=True · ATR_TP_MIN=0.013 · BTC_CHOP_GATE_THRESHOLD=0.2 · BTC_CHOP_GATE_3H_PCT=0.5 · CUT_LOSER_PNL=-1.00 · PUMP_CHAIN_V5_ENABLED=False · MTF_REGIME_TREND_MINUS_ENABLED=False (+NEVER_REENABLE) · NEUTRAL_SNIPER_ENABLED=False · ACCEL_300_V3_LONG_ENABLED=False · RR_ENGINE_SHADOW=True · ATR_SL/PM_TRAIL protected.

### CRITICAL / OPEN
1. **Oversold SHORT leak** — 5/6 oversold since b960ffe8; 1/1 since freeze end (LTC RSI 9.90). brain.py guard now live — monitor 24h. Metric: 0 entries with RSI<25.
2. **Hotset empty intermittent** — 06:07–06:31 mostly `no signals survived` + fallback DB 0; FIL pump-chain- appears r1 sc=79 then vanishes. Multi-factor (LONG_BIAS + pump-chain- HIGH blocked + oversold filtered + confluence). **DELEGATE deep audit.**
3. **cut-loser-CL-T1** 69T −$9.62 — top: bb-squeeze+ hard_max 17T −$2.44 (MFE 0.14%), sma20_dip 9T −$1.27, bb_bounce_v2_long 7T −$1.02. Losers never worked. **DELEGATE bug_hunter MFE audit.**
4. **hard_max_loss** 57T −$7.86 — bb-squeeze+ LONG 17T −$2.44 lev 3.7 dominant. **DELEGATE bug_hunter semantics.**
5. **decider_run v1→v2 + fail-open removal** — architectural DRIFT-A root. **DELEGATE bug_hunter.** Not done this run.

### METRICS (Oct 12 checkpoint)
| Metric | Current | Target | Deadline |
|--------|---------|--------|----------|
| 24h PnL | −$1.25 | ≥ $0 | next run |
| 7d PnL | −$0.66 | +$3.00 | 2026-10-06 |
| SHORT 7d PnL | −$1.88 | ≥ $0 | 2026-10-07 |
| 30d PnL | −$2.81 | ≥ $0 | 2026-10-11 |
| Oversold SHORT RSI<25 entries | leaking (5/6 since b960ffe8) | 0 | 24h post brain.py guard |
| cut-loser-CL-T1 30d bleed | −$9.62 | reduced ≥50% | 2026-10-11 |
| hard_max_loss 30d | −$7.86 | reduced ≥50% | 2026-10-11 |
| bb-bounce-v3 NORMAL block | LIVE 0.0 | sustained (HIGH only) | monitor |
| bb-bounce-v2-long+ 1.4 | LIVE | 24h n≥5 eval | 2026-10-07 |
| mtf-regime-trend- post-kill | 0 trades | stays 0 | ongoing |
| Hotset approved | intermittent 0 | sustained >0 | post audit |
| trend-ride+ | 7T −$0.18/48h | n≥10 eval | 2026-10-07 |

## Monitor List (next 48h)
1. **Oversold SHORT via brain.py guard** — expect 0 RSI<25 SHORT entries 24h post-fix. (self_learner + orchestrator)
2. **SHORT 7d PnL ≥ $0 by 2026-10-07** — pump-chain- hard_sl/hard_max is the lever.
3. **24h PnL back ≥ $0.**
4. **Hotset empty** — deep audit delegated; watch approval rate.
5. bb-bounce-v3 NORMAL block sustained — no NORMAL habitat entries.
6. bb-bounce-v2-long+ 1.4 — 24h n≥5 for boost confidence.
7. trend-ride+ 48h monitor (don't stack filters).
8. hard_max_loss / CL-T1 — bug_hunter owns audits.
9. Disk 83% — prune at 85–88%. No candles vacuum mid-trading.
10. LTC pump-chain- SHORT open against LONG_BIAS — watch, don't auto-close.
11. HL API key reminder in AGENTS.md still marked STALE — T to verify.
12. RR_ENGINE_SHADOW=True until shadow numbers exist.
13. 45da8fcf trendline_bounce_long boost — still unratified (CEO: RATIFY or REVERT).
14. IO pnl_usdt accounting — position_manager fix committed; verify future closes.

## Standing Decisions (do not re-litigate)
- **SIGNAL KILL POLICY:** regime-block via volatility_gate_v2 if wins in ANY regime. Blanket-kill ONLY if loses in ALL regimes.
- **SHORT ENTRY MODEL:** exec RSI>=40 all paths; EXTREME habitat; NEUTRAL blocked; HARD_FLOOR=25 no override.
- **ATR_TP_MIN=0.013** — brain_auditor approved, DO NOT REVERT.
- **EXTREME pump-chain- SHORT 0.0→1.0** — DO NOT revert.
- **RR_ENGINE_SHADOW=True** until shadow audit numbers exist.
- **STANDALONE_BYPASS shrink-to-6 REJECTED** — incremental prune only.
- **CUT_LOSER_PNL=-1.00 DO NOT CHANGE** — semantics with bug_hunter.
- **BTC_CHOP_GATE_THRESHOLD=0.20** / **BTC_CHOP_GATE_3H_PCT=0.50** — live.
- **PUMP_CHAIN_V5_ENABLED=False** — standing disable.
- **PROFIT_MONSTER_BYPASS keeps pump-chain** — verified 2026-10-06; removal claim refuted.
- **hermes_constants.py:** do not change VALUES without CEO/T. Crash-bug code fixes allowed.
- **NEUTRAL_SNIPER_ENABLED=False** — human-disabled per T.
- **Blacklist testing COMPLETE** — 77 tokens, 0 KEEP.
- **MTF_REGIME_TREND_MINUS_ENABLED=False + NEVER_REENABLE** — killed 2026-10-06.
- **bb-bounce-v3-long NOT in STANDALONE_BYPASS** — DRIFT-A closed.
- **Agents commit own files only.**
- **Disk prune** when >88%. Coin_tracker/candles NEVER vacuum during trading.

## Delegated (not orchestrator's call)
- **bug_hunter:** decider_run v1→v2 import + fail-open removal (architectural DRIFT-A root)
- **bug_hunter:** cut-loser-CL-T1 MFE audit then fix (69T −$9.62 30d; data gathered this run)
- **bug_hunter:** hard_max_loss leverage-aware semantics (57T −$7.86; bb-squeeze+ 17T −$2.44)
- **bug_hunter:** bypass-path full audit remaining (oversold floors on all paths — brain.py guard is first slice)
- **self_learner:** 24h oversold SHORT verify post brain.py guard
- **signal_analyst:** hotset empty multi-factor audit; HIGH-regime LONG throttle research; ema_reclaim; mover+
- **CEO/T:** 45da8fcf ratify/revert; exit_optimizer_shadow timer; AGENTS.md philosophy ack; HL key verify

## Sideways finds this run
- **LTC CTX-GATE log missing** at entry — entered via brain.py without visible CTX-GATE line (CC shows CTX-GATE every cycle). Possible log gap or path difference. brain.py guard added regardless.
- **signal_versions.json `pump-chain-` non-dict (list)** — audit store corruption, minor (from auto_1hr).
- **scripts/signal_version.py MISSING** — audit script referenced by SOP does not exist (from auto_1hr, still open).
- **paths.py + candles_lock.py + weather_station_api.py** uncommitted other-agent WIP — NOT committed this run (incomplete pair). paths.py adds CANDLES_LOCK; candles_lock.py is the consumer.
- **decisions table stale since April** — ai_decider defunct, expected (health monitor note).

## Orchestrator / CEO Report (2026-10-06 06:45 UTC)
- Post-freeze queue: 3 implemented (FAMILY_MAP underscore, brain.py SHORT RSI guard, commit completed work), 1 verified-no-change (PROFIT_MONSTER pump-chain KEEP), 3 delegated (CL-T1, hard_max_loss, decider v1→v2), 1 delegated audit (hotset empty).
- PG-verified numbers from PostgreSQL brain, not memory.
- Protected flags intact. Pipeline healthy. Freeze over — config changes allowed with evidence.
- Artifacts: automation/trading_log.md, automation/ceo_kanban.md, automation/daily_orchestrator_report_2026-10-06.md.
