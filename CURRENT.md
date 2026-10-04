# Current State — System Improvement Focus

**Last Updated: 2026-10-04 05:50 UTC**
**Updated by: CEO (DB verification + b960ffe8 monitor checkpoint)**

## Current Status

**PIPELINE ACTIVE. 0 trading config changes this run.** 24h +$0.23/58.8% | 7d +$2.42/53.1% | **30d -$0.48/52.1% (improved from -$1.72)**. SHORT 7d -$1.38 still bleeding; SHORT monitor window ACTIVE (b960ffe8 48h, ends Oct 6 00:38). LONG 7d +$3.80/153T carries system. Regime ~100% NEUTRAL (203/207 7d). Disk 80%. 0 open positions. Pipeline restarted 01:50 UTC — exec-RSI audit fixes LOADED. **b960ffe8 post-fix: 0 SHORT trades since restart — oversold filter untestable (n=0), not failing.**

**PG live (CEO-verified 05:50 UTC):** 30d **956T -$0.48 52.1%WR**. 7d **207T +$2.42 53.1%** (LONG 153T +$3.80 55.6%, SHORT 54T -$1.38 46.3%). 24h **34T +$0.23 58.8%** (LONG 30T +$0.34 63.3%, SHORT 4T -$0.11 25%). Daily: Oct2 +$0.73, Oct3 +$1.15, Oct4 +$0.47 (8T 75% so far). hard_max_loss 48h **18T -$3.08** avg_pct -4.56 avg_lev 4.3 — dominant bleed, stop working, semantics open with bug_hunter. PRE_FIX Oct3-4 SHORT: 6T -$0.06, 5/6 entry_rsi<40.

## Bug-Hunter Audit Result (landed this session)

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

**Delegated:** bug_hunter (RR_ENGINE shadow analysis — holes 1+2 DONE, shadow numbers still pending), self_learner (48h zero-oversold-SHORT verification post b960ffe8 — n=0 SHORTs so far), signal_analyst (scanner retune + EXTREME SHORT habitat memory + ema_reclaim coverage + doji execution path + coin_tracker Wyckoff).

**Metric checkpoint 2026-10-07:** SHORT 7d ≥ $0, oversold SHORT entries = 0.

## Measurable Goals (CEO 2026-10-04 05:50 UTC)

| Metric | Current | Target | Deadline |
|--------|---------|--------|----------|
| SHORT 7d PnL | -$1.38 | ≥ $0 | 2026-10-07 |
| Oversold SHORT entries (exec RSI<40) post-fix | n=0 SHORTs since fix | 0 (monitor) | Oct 6 00:38 |
| 7d PnL | +$2.42 | +$3.00 | 48h |
| 30d PnL | -$0.48 | ≥ $0 | 7d |
| volume-breakout post-boost trades | 0 opened post-boost | ≥10 with ≥60% WR | 7d |
| doji-bottom-long trades | 14T/30d (detection live, 0 exec) | 20T (conf boost) | 7d |
| ema_reclaim_long trades | 0 EVER | >0 in shadow | 7d |

## Automation Actions Today (verified in code/logs)

- **🟢 CEO 05:50 0 CONFIG** — DB verification, b960ffe8 monitor checkpoint (0 SHORTs since fix), regime memory updated (doji regime corrected NEUTRAL), CURRENT.md refreshed. Protected flags untouched. Sunday MoE skipped.
- **🟢 CEO 01:55 0 CONFIG** — verified DB numbers, confirmed b960ffe8 loaded, regime memory updated.
- **🟢 bug_hunter 00:38 CODE** — exec-RSI audit holes 1+2 fixed (b960ffe8). continuum_trader RSI floor + decider_run fail-closed.
- **🟢 auto_1hr (prior) 22:11 CONFIG** — volume-breakout boost 1.15→1.25 APPLIED at signal_compactor.py:709 (re-verified 05:50).

## Standing Decisions (do not re-litigate)

- **SIGNAL KILL POLICY:** regime-block via volatility_gate_v2 if wins in ANY regime. Blanket-kill ONLY if loses in ALL regimes.
- **SHORT ENTRY MODEL (2026-10-04):** exec RSI>=40 all paths; EXTREME habitat; NEUTRAL blocked. MoE panel + DB-verified.
- **0 config changes when b960ffe8 48h monitor active** (until Oct 6 00:38).
- **volume-breakout conf boost 1.15→1.25 APPLIED** 22:11 Oct 3.
- **RR_ENGINE_SHADOW=True stays until shadow audit numbers exist** — do not blind-force.
- **STANDALONE_BYPASS shrink-to-6 REJECTED** — incremental prune only.
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

## Monitor List (next 48h)

1. **ZERO oversold SHORT entries** 48h post b960ffe8 (self_learner) — query entry_rsi_14 AND exec RSI. **Status 05:50: n=0 SHORTs since fix — cannot pass/fail yet.**
2. **SHORT 7d PnL ≥ $0 by 2026-10-07.**
3. volume-breakout-long+ post-boost live performance (conf 1.25) — need first post-boost trade, then 10+.
4. **RR_ENGINE shadow would-have-blocked analysis** (bug_hunter) — FORCE on/off with numbers.
5. 15m/5m scanner retune (signal_analyst).
6. doji-bottom-long → 20T for conf boost — detection live, execution path needs work.
7. hard_max_loss semantics — price vs leveraged PnL (bug_hunter, non-trading-path). 48h 18T -$3.08 confirmed.
8. mover+ entry quality (signal_analyst) — not firing since Sep 24.
9. ema_reclaim_long 0 signals executed — coverage + partners (signal_analyst) — OVERDUE.
10. Disk 80% — prune at 88%.
11. ORPHAN_PAPER BTC amount=0 hygiene.
12. DRIFT-002 — exec-time RSI timeframe (bug_hunter owns; holes 1+2 closed).
13. HL API key reminder in AGENTS.md STALE — T: verify/correct.
14. Coin tracker intelligence — Wyckoff/Elliott/Volume unbuilt (signal_analyst).
15. pnl_usdt vs fees.net_pnl inconsistency — accounting audit (bug_hunter, non-trading-path).
16. OpenMemory service inactive — HTTP API works.

## Backlog / Delegated (not orchestrator's call)

- **DELEGATE bug_hunter:** RR_ENGINE shadow-block 7d would-have-blocked analysis → FORCE recommendation with numbers. (holes 1+2 DONE)
- **DELEGATE bug_hunter:** fees JSON vs pnl_usdt accounting gap + hard_max_loss semantics (48h 18T -$3.08).
- **DELEGATE self_learner:** 48h verification — zero SHORT entries with entry_rsi_14<40 post b960ffe8. **Status: n=0 SHORTs since fix 01:50.**
- **DELEGATE signal_analyst:** retune 15m/5m scanner thresholds; snapshot EXTREME+RSI>=40 SHORT habitat.
- **DELEGATE signal_analyst:** ema_reclaim_long detection coverage + confluence partners — 0 trades EVER, OVERDUE.
- **DELEGATE signal_analyst:** doji-bottom execution path — detection works (10 signals/24h), 0 executed (starvation).
- **DELEGATE signal_analyst:** mover+ entry quality — deep atr_sl_hit at high conf.
- **DELEGATE signal_analyst:** coin_tracker Wyckoff/phase-transition signal (1/week min).
- **T ack required:** AGENTS.md philosophy amendment (conditioned SHORT rule).
- **bollinger_squeeze SHORT side** — research PASS historically but OFF until SHORT R:R fixed.
- **bugs.json OPEN** — coin_tracker/backfill — not trading-path.

## Orchestrator / CEO Report (2026-10-04 05:50 UTC)

- **0 trading config changes** — b960ffe8 48h monitor active. Sunday MoE skipped.
- **VERIFIED all numbers from PG directly.** 30d **-$0.48/52.1%** (improved +$1.24 from -$1.72). 7d +$2.42/53.1%. 24h +$0.23/58.8%. SHORT 7d -$1.38, LONG 7d +$3.80.
- **b960ffe8 checkpoint:** 0 SHORT trades since pipeline restart 01:50. PRE_FIX 6T SHORT Oct3-4, 5/6 oversold. Filter untestable without SHORTs — monitor continues, not a failure signal.
- **hard_max_loss 48h 18T -$3.08** — bb-squeeze+ 5T, pump-chain- 4T, pump-chain+ 2T; stop cutting ~1% price at lev 3-5. Semantics open with bug_hunter.
- **Regime memory corrected:** doji-bottom all NEUTRAL (prior HIGH claim stale — no HIGH regime in market).
- **volume-breakout boost re-verified** 1.25 in code; 0 post-boost trades yet.
- **Protected flags untouched.** MoE decisions standing. Session lock absent.
