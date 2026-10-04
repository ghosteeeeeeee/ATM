# Current State — System Improvement Focus

**Last Updated: 2026-10-04 01:55 UTC**
**Updated by: CEO (verified numbers + audit-fix confirmation)**

## Current Status

**PIPELINE ACTIVE. 0 trading config changes this run.** 24h +$0.84/57.6% | 7d +$2.00/52.2% | **30d -$1.72/51.7% (improved from -$2.22)**. SHORT 7d -$1.38 still bleeding; SHORT 30d -$4.02. LONG 7d +$3.38/147T carries system. Regime 100% NEUTRAL (196/201 7d). Disk 82%. Pipeline restarted 01:50 UTC — exec-RSI audit fixes LOADED.

**PG live (CEO-verified this session):** 30d **959T -$1.72 51.7%WR**. SHORT 30d by entry_rsi_14: **<25=24T -$2.86 8.3%WR**, 25-40=62T -$2.18 41.9%, 40-50=36T -$0.77, **>=50=34T +$0.17 55.9%**, NULL=211T +$1.62 56.4%. Post-floor (since Oct 3 22:11): 1 SHORT closed — IO pump-chain- RSI=13.46 -$0.24 (hole bypass, now fixed). **0 oversold SHORT entries post b960ffe8.**

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

**Delegated:** bug_hunter (RR_ENGINE shadow analysis — holes 1+2 DONE), self_learner (48h zero-oversold-SHORT verification post b960ffe8), signal_analyst (scanner retune + EXTREME SHORT habitat memory + ema_reclaim coverage).

**Metric checkpoint 2026-10-07:** SHORT 7d ≥ $0, oversold SHORT entries = 0.

## Measurable Goals (CEO 2026-10-04 01:55 UTC)

| Metric | Current | Target | Deadline |
|--------|---------|--------|----------|
| SHORT 7d PnL | -$1.38 | ≥ $0 | 2026-10-07 |
| Oversold SHORT entries (exec RSI<40) post-fix | 1 pre-fix (IO) | 0 | 48h |
| 7d PnL | +$2.00 | +$3.00 | 48h |
| 30d PnL | -$1.72 | ≥ $0 | 7d |
| volume-breakout post-boost WR | 1T closed (pre-boost open) | ≥60% | 7d |
| doji-bottom-long trades | 14T/30d | 20T (conf boost) | 7d |

## Automation Actions Today (verified in code/logs)

- **🟢 CEO 01:55 0 CONFIG** — verified DB numbers, confirmed b960ffe8 loaded (pipeline restart 01:50), regime memory updated, CURRENT.md refreshed. Protected flags untouched.
- **🟢 bug_hunter 00:38 CODE** — exec-RSI audit holes 1+2 fixed (b960ffe8). continuum_trader RSI floor + decider_run fail-closed.
- **🟢 auto_1hr (prior) 22:11 CONFIG** — volume-breakout boost 1.15→1.25 APPLIED at signal_compactor.py:709.

## Standing Decisions (do not re-litigate)

- **SIGNAL KILL POLICY:** regime-block via volatility_gate_v2 if wins in ANY regime. Blanket-kill ONLY if loses in ALL regimes.
- **SHORT ENTRY MODEL (2026-10-04):** exec RSI>=40 all paths; EXTREME habitat; NEUTRAL blocked. MoE panel + DB-verified.
- **0 config changes when monitor windows active.** None active now.
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

1. **ZERO oversold SHORT entries** 48h post b960ffe8 (self_learner) — query entry_rsi_14 AND exec RSI.
2. **SHORT 7d PnL ≥ $0 by 2026-10-07.**
3. volume-breakout-long+ post-boost live performance (conf 1.25) — need 10+ trades.
4. **RR_ENGINE shadow would-have-blocked analysis** (bug_hunter) — FORCE on/off with numbers.
5. 15m/5m scanner retune (signal_analyst).
6. doji-bottom-long → 20T for conf boost.
7. hard_max_loss semantics — price vs leveraged PnL (bug_hunter, non-trading-path).
8. mover+ entry quality (signal_analyst).
9. ema_reclaim_long 0 signals — coverage + partners (signal_analyst).
10. Disk 82% — prune at 88%.
11. ORPHAN_PAPER BTC amount=0 hygiene.
12. DRIFT-002 — exec-time RSI timeframe (bug_hunter owns; holes 1+2 closed).
13. HL API key reminder in AGENTS.md STALE — T: verify/correct.
14. Coin tracker intelligence — Wyckoff/Elliott/Volume unbuilt (signal_analyst).
15. pnl_usdt vs fees.net_pnl inconsistency — accounting audit (bug_hunter, non-trading-path).
16. OpenMemory service inactive — HTTP API works.

## Backlog / Delegated (not orchestrator's call)

- **DELEGATE bug_hunter:** RR_ENGINE shadow-block 7d would-have-blocked analysis → FORCE recommendation with numbers. (holes 1+2 DONE)
- **DELEGATE bug_hunter:** fees JSON vs pnl_usdt accounting gap.
- **DELEGATE self_learner:** 48h verification — zero SHORT entries with entry_rsi_14<40 post b960ffe8.
- **DELEGATE signal_analyst:** retune 15m/5m scanner thresholds; snapshot EXTREME+RSI>=40 SHORT habitat.
- **DELEGATE signal_analyst:** ema_reclaim_long detection coverage + confluence partners.
- **DELEGATE signal_analyst:** mover+ entry quality — deep atr_sl_hit at high conf.
- **DELEGATE signal_analyst:** coin_tracker Wyckoff/phase-transition signal (1/week min).
- **T ack required:** AGENTS.md philosophy amendment (conditioned SHORT rule).
- **bollinger_squeeze SHORT side** — research PASS historically but OFF until SHORT R:R fixed.
- **bugs.json OPEN** — coin_tracker/backfill — not trading-path.

## Orchestrator / CEO Report (2026-10-04 01:55 UTC)

- **0 trading config changes** — verification + memory run.
- **VERIFIED all numbers from PG directly.** 30d **-$1.72/51.7%** (improved +$0.50 from -$2.22). 7d +$2.00/52.2%. 24h +$0.84/57.6%. SHORT 7d -$1.38, SHORT 30d -$4.02.
- **Daily trend improving:** Sep 29 -$1.13 → Oct 2 +$0.73 → Oct 3 +$1.15.
- **bug_hunter delivered:** b960ffe8 exec-RSI holes 1+2 (continuum_trader + decider_run fail-closed). Pipeline restarted 01:50 — LIVE. IO RSI=13.46 root-caused to pre-fix hole.
- **accel_300_v3_long already ENABLED=False** (Oct 3 post-window) — stale monitor item removed.
- **Protected flags untouched.** MoE decisions standing.
