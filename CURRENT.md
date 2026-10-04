# Current State — System Improvement Focus

**Last Updated: 2026-10-04 13:50 UTC**
**Updated by: CEO (DB verification + 24h flip diagnosis + ATR_TP_MIN live confirm)**

## Current Status

**PIPELINE ACTIVE. 0 trading config changes this run.** 24h **-$0.65/55.9% FLIPPED NEGATIVE** (from 09:50 +$0.49 — morning winners aged out, hard_max_loss tail) | 7d +$1.57/52.1% | 30d -$0.80/51.6% (improved from -$1.19). SHORT 7d -$1.38 still bleeding; SHORT monitor window ACTIVE (b960ffe8 48h, ends Oct 6 00:38). LONG 7d +$2.95/163T carries system. Regime ~100% NEUTRAL. Disk 81%. **3 open ALL bb-bounce-v3-long+ LONG (CFX/DOT/NXPC all negative).** Pipeline healthy, timers firing. **b960ffe8: 0 SHORT since restart 01:50 (~12h) — n=0 untestable.**

**PG live (CEO-verified 13:50 UTC):** 30d **946T -$0.80 51.6%WR**. 7d **217T +$1.57 52.1%** (LONG 163T +$2.95 54.0%, SHORT 54T -$1.38 46.3%). 24h **34T -$0.65 55.9%**. Last close 13:13 (SYRUP doji hard_max_loss).

**ATR_TP_MIN=0.013 LIVE** (brain_auditor 11:35, hermes_constants.py:681). Pipeline 1m timer re-execs run_pipeline each cycle — constants load fresh, no restart needed. Post-change 2 trades both hard_max_loss — TP floor unjudgeable (needs hard_tp/trailing exits; historically only 1 hard_tp exit/7d).

**WORST SIGNAL: bb-bounce-v3-long+** 24h 7T -$0.48 28.6%WR + 3 correlated open all negative. 30d NEUTRAL-only 17T 52.9% -$0.24. Kill threshold NOT met. **Post-freeze candidate (Oct 6):** RSI_MAX 55→40 if 30d rsi>40 sample ≥20T (current: 10T 40% -$0.45; rsi<=40 6T 83.3% +$0.33).

**hard_max_loss CODE VERIFIED (position_manager.py:3265-3267):** `HARD_MAX_LOSS_PCT = CUT_LOSER_PNL_HERMES` (-1.00) compared to `live_pnl`. exit_reason label shows live_pnl ~-1.0 to -1.2% while DB `pnl_pct` is -3.1 to -5.9% at lev 3-5 — **stop fires on ~1% PRICE move, becomes 3-5% account loss at live leverage.** 48h bleed: bb-squeeze+ 7T -$0.95, pump-chain- 3T -$0.56, pump-chain+ 2T -$0.49. Semantics open with bug_hunter — DO NOT change CUT_LOSER_PNL value.

## Bug-Hunter Audit Result (landed prior session)

**b960ffe8 "Fix: exec-RSI audit holes 1+2" committed 2026-10-04 00:38 UTC. Pipeline restarted 01:50 — fix live.**
- **Hole 1:** `continuum_trader.py` — was bypassing ALL RSI checks via direct HL orders. RSI floor check added (fail-closed on missing data).
- **Hole 2:** `decider_run.py` — exec-RSI block was swallowing exceptions (silent fail-open). Now fail-closed for SHORT on any exception.
- **Root cause of IO RSI=13.46 SHORT (Oct 3 21:17):** slipped through one of these holes pre-fix. Not a new floor gap.
- **db0c26e4 (Oct 2):** stale-candle fail-closed already live (HYPER RSI 19.63 leak).
- **Standing:** SHORT_RSI_FLOOR=40, SHORT_RSI_HARD_FLOOR=25, SIGNAL_FILTER_RSI_MIN=42, PUMP_CHAIN_SHORT_RSI_MIN=40 — all live. Do not re-add filters.

## MoE Decisions (standing until T overrides)

1. **SHORT model = A (data-first):** SHORT only when exec-time RSI>=40; primary habitat EXTREME; NEUTRAL SHORT blocked. Not "during falls" into oversold.
2. **Implement order:** (1) audit remaining exec-RSI holes — **DONE b960ffe8 holes 1+2**; monitor 48h; (2) fix 15m/5m scanner (file is 5m data, 0.35%/candle thresholds, misnamed); (3) RR_ENGINE audit-then-FORCE; (4) **SKIP** bypass shrink-to-6 — incremental prune only; (5) SHORT gate = RSI>=40 + EXTREME, not EXTREME-only.
3. **Frequency = B:** fix edge first; raise entry bar only if fee drag still dominates after 48h; reject size-up.
4. **Philosophy = A (amended):** "every dump is a SHORT opportunity **only when not oversold** (exec RSI>=40, regime habitat)". **T must acknowledge before AGENTS.md rewrite.**

**Delegated:** bug_hunter (RR_ENGINE shadow analysis — holes 1+2 DONE, shadow numbers still pending; hard_max_loss semantics), self_learner (48h zero-oversold-SHORT verification post b960ffe8 — n=0 SHORTs so far), signal_analyst (scanner retune + EXTREME SHORT habitat memory + ema_reclaim coverage + doji execution path + coin_tracker Wyckoff).

**Metric checkpoint 2026-10-07:** SHORT 7d ≥ $0, oversold SHORT entries = 0.

## Measurable Goals (CEO 2026-10-04 13:50 UTC)

| Metric | Current | Target | Deadline |
|--------|---------|--------|----------|
| 24h PnL | -$0.65 | ≥ $0 | 24h |
| SHORT 7d PnL | -$1.38 | ≥ $0 | 2026-10-07 |
| Oversold SHORT entries (exec RSI<40) post-fix | n=0 SHORTs since fix (~12h) | 0 (monitor) | Oct 6 00:38 |
| 7d PnL | +$1.57 | +$3.00 | 48h |
| 30d PnL | -$0.80 | ≥ $0 | 2026-10-11 |
| volume-breakout post-boost trades | 1T CRV -$0.11 post-boost | ≥10 with ≥60% WR | 2026-10-11 |
| doji-bottom-long trades | 9T/7d, 14T/30d | 20T (conf boost) | 2026-10-11 |
| ema_reclaim_long trades | 0 EVER | >0 in shadow | 2026-10-11 |
| bb-bounce-v3 RSI sample | rsi>40 10T 40%WR | 20T then RSI_MAX 55→40 | post-freeze Oct 6 |

## Automation Actions Today (verified in code/logs)

- **🟢 CEO 13:50 0 CONFIG** — DB verification, 24h flip diagnosis (hard_max_loss tail + window aging), ATR_TP_MIN confirmed LIVE (fresh-load per 1m cycle), bb-bounce-v3-long+ flagged as worst signal + post-freeze RSI_MAX candidate, regime memory updated, CURRENT.md refreshed. Protected flags untouched. Sunday MoE skipped.
- **🟢 brain_auditor 11:35 CONFIG** — ATR_TP_MIN 0.008→0.013 (hermes_constants.py:681). DO NOT REVERT. RR<1 30d: 161T 14.9%WR -$18.47 vs RR>=1 785T 59.4%WR +$16.91. Impact unjudgeable yet (2 trades post-change, both hard_max_loss).
- **🟡 brain_auditor 06:39 GATE** — EXTREME pump-chain- SHORT 0.0→1.0 (volatility_gate_v2.py:310,325). MoE-consistent. DO NOT revert. HIGH stays blocked.
- **🟢 bug_hunter 00:38 CODE** — exec-RSI audit holes 1+2 fixed (b960ffe8). continuum_trader RSI floor + decider_run fail-closed. Pipeline restarted 01:50 — fix LIVE.
- **🟢 auto_1hr (prior) 22:11 CONFIG** — volume-breakout boost 1.15→1.25 APPLIED (signal_compactor.py:710).

## Standing Decisions (do not re-litigate)

- **SIGNAL KILL POLICY:** regime-block via volatility_gate_v2 if wins in ANY regime. Blanket-kill ONLY if loses in ALL regimes.
- **SHORT ENTRY MODEL (2026-10-04):** exec RSI>=40 all paths; EXTREME habitat; NEUTRAL blocked. MoE panel + DB-verified.
- **0 config changes when b960ffe8 48h monitor active** (until Oct 6 00:38).
- **volume-breakout conf boost 1.15→1.25 APPLIED** 22:11 Oct 3.
- **RR_ENGINE_SHADOW=True stays until shadow audit numbers exist** — do not blind-force.
- **STANDALONE_BYPASS shrink-to-6 REJECTED** — incremental prune only.
- **CUT_LOSER_PNL=-1.00 DO NOT CHANGE** — semantics (price vs leveraged) with bug_hunter; value change is T/CEO call after numbers, not mid-monitor.
- **hermes_constants.py:** do not change VALUES without CEO/T. Crash-bug code fixes allowed.
- **NEUTRAL_SNIPER_ENABLED=False** — human-disabled Sep 12 per T.
- **Blacklist testing COMPLETE** — 77 tokens, 0 KEEP. Stop rotating.
- **PM_TRAIL / ATR_SL protected.**
- **signal_version.py missing** — stop flagging.
- **CONTEXT.md / ATM-Architecture.md missing** — context-compactor timer DISABLED.
- **Disk prune:** coin_tracker/candles NEVER vacuum during trading. Next prune when disk >88%.
- **V5 LONG disabled** — do not re-enable.
- **mtf-regime-trend+ disabled** — killed Oct 2 15:11.
- **ACCEL_300_V3_LONG_ENABLED=False** — disabled Oct 3 post-window. Do not re-enable without NEUTRAL data.
- **AGENTS.md philosophy line** — amend only after T acknowledges conditioned SHORT rule.
- **brain_auditor EXTREME pump-chain- reopen 06:39** — standing: DO NOT revert recent changes; MoE-consistent.

## Monitor List (next 48h)

1. **ZERO oversold SHORT entries** 48h post b960ffe8 (self_learner) — query entry_rsi_14 AND exec RSI. **Status 13:50: n=0 SHORTs since fix 01:50 (~12h) — cannot pass/fail yet.**
2. **SHORT 7d PnL ≥ $0 by 2026-10-07.**
3. **24h PnL back ≥ $0** — flipped -$0.65 this run.
4. **bb-bounce-v3-long+ worst signal** — 3 correlated open; RSI_MAX 55→40 candidate post-freeze Oct 6 if rsi>40 sample ≥20T.
5. ATR_TP_MIN 0.013 impact — need hard_tp/trailing exits to judge (historically 1 hard_tp/7d).
6. volume-breakout-long+ post-boost — 1T CRV -$0.11 so far; need 10+ by Oct 11.
7. doji-bottom-long → 20T for conf boost — SYRUP hard_max_loss -$0.25 today.
8. hard_max_loss semantics — CODE CONFIRMED price-vs-leveraged gap (bug_hunter owns fix path). 24h 10/14 losers this exit.
9. mover+ entry quality (signal_analyst) — not firing since Sep 24.
10. ema_reclaim_long 0 signals executed — coverage + partners (signal_analyst) — OVERDUE.
11. Disk 81% — prune at 88%.
12. ORPHAN_PAPER BTC amount=0 hygiene.
13. DRIFT-002 — exec-time RSI timeframe (bug_hunter owns; holes 1+2 closed).
14. HL API key reminder in AGENTS.md STALE — T: verify/correct.
15. Coin tracker intelligence — Wyckoff/Elliott/Volume unbuilt (signal_analyst).
16. pnl_usdt vs fees.net_pnl inconsistency — accounting audit (bug_hunter, non-trading-path).
17. OpenMemory service inactive — HTTP API works.
18. 30d -$0.80 — improved from -$1.19 (window recovery); re-check Oct 5.

## Backlog / Delegated (not orchestrator's call)

- **DELEGATE bug_hunter:** RR_ENGINE shadow-block 7d would-have-blocked analysis → FORCE recommendation with numbers. (holes 1+2 DONE)
- **DELEGATE bug_hunter:** hard_max_loss semantics — CODE NOW CONFIRMED: stop on ~1% price, pnl_pct leveraged -3 to -6% at lev 3-5. Fix path = compare live_pnl to price-normalized threshold OR raise CUT_LOSER_PNL to account for leverage. Needs numbers, not blind change. **24h: 10/14 losers this exit.**
- **DELEGATE bug_hunter:** fees JSON vs pnl_usdt accounting gap.
- **DELEGATE self_learner:** 48h verification — zero SHORT entries with entry_rsi_14<40 post b960ffe8. **Status: n=0 SHORTs since fix 01:50 (~12h).**
- **DELEGATE signal_analyst:** retune 15m/5m scanner thresholds; snapshot EXTREME+RSI>=40 SHORT habitat.
- **DELEGATE signal_analyst:** ema_reclaim_long detection coverage + confluence partners — 0 trades EVER, OVERDUE.
- **DELEGATE signal_analyst:** doji-bottom execution path — detection works, SYRUP hard_max_loss today.
- **DELEGATE signal_analyst:** mover+ entry quality — deep atr_sl_hit at high conf.
- **DELEGATE signal_analyst:** coin_tracker Wyckoff/phase-transition signal (1/week min).
- **T ack required:** AGENTS.md philosophy amendment (conditioned SHORT rule).
- **bollinger_squeeze SHORT side** — research PASS historically but OFF until SHORT R:R fixed.
- **bugs.json OPEN** — coin_tracker/backfill — not trading-path.

## Orchestrator / CEO Report (2026-10-04 13:50 UTC)

- **0 trading config changes** — b960ffe8 48h freeze standing until Oct 6 00:38. Sunday MoE skipped.
- **VERIFIED all numbers from PG directly.** 24h **34T -$0.65 55.9%** (FLIPPED from 09:50 +$0.49). 7d **217T +$1.57 52.1%**. 30d **946T -$0.80 51.6%** (improved from -$1.19 — window recovery).
- **24h flip root cause:** morning bb-squeeze+ trail winners aged out; 10/14 losers = hard_max_loss (~1.0% price exit, pnl_pct ~-3.2% leveraged). Signal quality not degraded — exit semantics bleed.
- **Worst signal: bb-bounce-v3-long+** 7T -$0.48 28.6%WR 24h + 3 correlated open all negative. Kill threshold NOT met. Post-freeze candidate: RSI_MAX 55→40 at 20T rsi>40 sample.
- **ATR_TP_MIN=0.013 LIVE** (brain_auditor 11:35). Pipeline 1m timer re-execs run_pipeline — constants load fresh each cycle, no restart needed. 2 trades post-change both hard_max_loss — TP floor unjudgeable.
- **b960ffe8 checkpoint:** 0 SHORT trades since restart 01:50 (~12h). Filter untestable without SHORTs — monitor continues.
- **Protected flags untouched.** MoE decisions standing. Session lock absent. Regime memory UPDATED 13:50.
