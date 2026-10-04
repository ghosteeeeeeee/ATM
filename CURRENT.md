# Current State — System Improvement Focus

**Last Updated: 2026-10-04 09:50 UTC**
**Updated by: CEO (DB verification + hard_max_loss code confirm + brain_auditor EXTREME gate note)**

## Current Status

**PIPELINE ACTIVE. 0 trading config changes this run.** 24h +$0.49/60.5% | 7d +$2.18/52.8% | 30d -$1.19/51.7% (window-edge roll from -$0.48, NOT new bleed). SHORT 7d -$1.38 still bleeding; SHORT monitor window ACTIVE (b960ffe8 48h, ends Oct 6 00:38). LONG 7d +$3.56/160T carries system. Regime ~100% NEUTRAL (210/214 7d). Disk 81%. 0 open positions. Pipeline healthy, timers firing. **b960ffe8 post-fix: 0 SHORT trades since restart 01:50 (~8h) — oversold filter untestable (n=0), not failing.**

**PG live (CEO-verified 09:50 UTC):** 30d **954T -$1.19 51.7%WR**. 7d **214T +$2.18 52.8%** (LONG 160T +$3.56 55.0%, SHORT 54T -$1.38 46.3%). 24h **38T +$0.49 60.5%**. Last close 09:37. Post-reopen (brain_auditor 06:39 EXTREME pump-chain-): 5 LONG -$0.13, 0 SHORT.

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

## Measurable Goals (CEO 2026-10-04 09:50 UTC)

| Metric | Current | Target | Deadline |
|--------|---------|--------|----------|
| SHORT 7d PnL | -$1.38 | ≥ $0 | 2026-10-07 |
| Oversold SHORT entries (exec RSI<40) post-fix | n=0 SHORTs since fix (~8h) | 0 (monitor) | Oct 6 00:38 |
| 7d PnL | +$2.18 | +$3.00 | 48h |
| 30d PnL | -$1.19 | ≥ $0 | 2026-10-11 |
| volume-breakout post-boost trades | 0 opened post-boost (~11h) | ≥10 with ≥60% WR | 2026-10-11 |
| doji-bottom-long trades | 8T/7d, 14T/30d | 20T (conf boost) | 2026-10-11 |
| ema_reclaim_long trades | 0 EVER | >0 in shadow | 2026-10-11 |

## Automation Actions Today (verified in code/logs)

- **🟢 CEO 09:50 0 CONFIG** — DB verification, hard_max_loss code path confirmed (price-vs-leveraged), brain_auditor EXTREME pump-chain- gate reopen noted MoE-consistent (DO NOT revert), regime memory updated, CURRENT.md refreshed. Protected flags untouched. Sunday MoE skipped.
- **🟡 brain_auditor 06:39 GATE** — EXTREME pump-chain- SHORT 0.0→1.0 (volatility_gate_v2.py:310,325). MoE-consistent: EXTREME RSI>=40 is only profitable SHORT cell (30d 18T +$0.96 72.2%WR). HIGH stays blocked. RSI floors are oversold defense. Post-reopen 0 SHORTs (NEUTRAL regime).
- **🟢 CEO 05:50 0 CONFIG** — DB verification, b960ffe8 monitor checkpoint (0 SHORTs since fix), regime memory updated, CURRENT.md refreshed.
- **🟢 bug_hunter 00:38 CODE** — exec-RSI audit holes 1+2 fixed (b960ffe8). continuum_trader RSI floor + decider_run fail-closed.
- **🟢 auto_1hr (prior) 22:11 CONFIG** — volume-breakout boost 1.15→1.25 APPLIED at signal_compactor.py:709-710 (re-verified 09:50).

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

1. **ZERO oversold SHORT entries** 48h post b960ffe8 (self_learner) — query entry_rsi_14 AND exec RSI. **Status 09:50: n=0 SHORTs since fix 01:50 (~8h) — cannot pass/fail yet.**
2. **SHORT 7d PnL ≥ $0 by 2026-10-07.**
3. volume-breakout-long+ post-boost live performance (conf 1.25) — STILL 0 post-boost trades ~11h; need first trade, then 10+.
4. **RR_ENGINE shadow would-have-blocked analysis** (bug_hunter) — FORCE on/off with numbers.
5. 15m/5m scanner retune (signal_analyst).
6. doji-bottom-long → 20T for conf boost — detection live, execution path needs work.
7. hard_max_loss semantics — **CODE CONFIRMED price-vs-leveraged gap** (bug_hunter owns fix path). 48h bleed continues.
8. mover+ entry quality (signal_analyst) — not firing since Sep 24.
9. ema_reclaim_long 0 signals executed — coverage + partners (signal_analyst) — OVERDUE.
10. Disk 81% — prune at 88%.
11. ORPHAN_PAPER BTC amount=0 hygiene.
12. DRIFT-002 — exec-time RSI timeframe (bug_hunter owns; holes 1+2 closed).
13. HL API key reminder in AGENTS.md STALE — T: verify/correct.
14. Coin tracker intelligence — Wyckoff/Elliott/Volume unbuilt (signal_analyst).
15. pnl_usdt vs fees.net_pnl inconsistency — accounting audit (bug_hunter, non-trading-path).
16. OpenMemory service inactive — HTTP API works.
17. 30d window-edge: -$0.48→-$1.19 is aging-out of older winners, not new bleed — re-check Oct 5 before alarm.

## Backlog / Delegated (not orchestrator's call)

- **DELEGATE bug_hunter:** RR_ENGINE shadow-block 7d would-have-blocked analysis → FORCE recommendation with numbers. (holes 1+2 DONE)
- **DELEGATE bug_hunter:** hard_max_loss semantics — CODE NOW CONFIRMED: stop on ~1% price, pnl_pct leveraged -3 to -6% at lev 3-5. Fix path = compare live_pnl to price-normalized threshold OR raise CUT_LOSER_PNL to account for leverage. Needs numbers, not blind change.
- **DELEGATE bug_hunter:** fees JSON vs pnl_usdt accounting gap.
- **DELEGATE self_learner:** 48h verification — zero SHORT entries with entry_rsi_14<40 post b960ffe8. **Status: n=0 SHORTs since fix 01:50 (~8h).**
- **DELEGATE signal_analyst:** retune 15m/5m scanner thresholds; snapshot EXTREME+RSI>=40 SHORT habitat.
- **DELEGATE signal_analyst:** ema_reclaim_long detection coverage + confluence partners — 0 trades EVER, OVERDUE.
- **DELEGATE signal_analyst:** doji-bottom execution path — detection works, 0 executed (starvation).
- **DELEGATE signal_analyst:** mover+ entry quality — deep atr_sl_hit at high conf.
- **DELEGATE signal_analyst:** coin_tracker Wyckoff/phase-transition signal (1/week min).
- **T ack required:** AGENTS.md philosophy amendment (conditioned SHORT rule).
- **bollinger_squeeze SHORT side** — research PASS historically but OFF until SHORT R:R fixed.
- **bugs.json OPEN** — coin_tracker/backfill — not trading-path.

## Orchestrator / CEO Report (2026-10-04 09:50 UTC)

- **0 trading config changes** — b960ffe8 48h monitor active (~8h in). Sunday MoE skipped.
- **VERIFIED all numbers from PG directly.** 24h **38T +$0.49 60.5%**. 7d **214T +$2.18 52.8%**. 30d **954T -$1.19 51.7%** — worse than 05:50 (-$0.48) due to window-edge roll of older winners, NOT new bleed (24h still positive, last close 09:37).
- **b960ffe8 checkpoint:** 0 SHORT trades since pipeline restart 01:50 (~8h). Filter untestable without SHORTs — monitor continues, not a failure signal.
- **brain_auditor 06:39:** EXTREME pump-chain- SHORT gate 0.0→1.0 — MoE-consistent (EXTREME RSI>=40 only profitable SHORT cell). DO NOT revert. HIGH stays blocked. RSI floors remain oversold defense. Post-reopen: 0 SHORTs (NEUTRAL regime).
- **hard_max_loss CODE CONFIRMED:** position_manager.py:3265-3267 fires on live_pnl ~-1% (price-scale) while trades.pnl_pct is leveraged -3 to -6% at lev 3-5. Semantics open with bug_hunter. CUT_LOSER_PNL value untouched.
- **volume-breakout boost re-verified** 1.25 in code (signal_compactor.py:710); 0 post-boost trades ~11h after apply.
- **Protected flags untouched.** MoE decisions standing. Session lock absent.
