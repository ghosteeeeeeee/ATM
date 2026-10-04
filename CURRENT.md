# Current State — System Improvement Focus

**Last Updated: 2026-10-04 00:30 UTC**
**Updated by: CEO (MoE panel decisions)**

## Current Status

**PIPELINE ACTIVE. MoE PROFITABILITY-PANEL DECISIONS MADE. 0 trading config changes this run.** 24h +$1.15/58.8% | 7d +$1.95/52.0% | **30d -$2.22/51.4% (SHORT -$4.12 is entire net loss)**. Bollinger window OVER (ended 21:55 UTC Oct 3). volume-breakout conf boost **APPLIED** 22:11 (1.15→1.25, pipeline restarted). Regime still NEUTRAL-heavy. Disk ~82%. Pipeline healthy.

**PG live (CEO-verified this session):** 30d **966T -$2.22 51.4%WR**. SHORT RSI<40 **86T -$5.04 32.6%WR**. Only positive SHORT cell: EXTREME RSI>=40 **40T +$0.98 62.5%WR**. profit-monster* **+$18.83/307T 82.1%** only big winner. MoE "wave bottoms 94%WR" **REJECTED** (DB: RSI<40 = 32.6%).

## MoE Decisions (standing until T overrides)

1. **SHORT model = A (data-first):** SHORT only when exec-time RSI>=40; primary habitat EXTREME; NEUTRAL SHORT blocked; NORMAL/HIGH only with quality gates. Not "during falls" into oversold.
2. **Implement order:** (1) audit remaining exec-RSI holes — floor ALREADY LIVE (bf96d7cd Oct 3), do not blindly re-add filters; (2) fix 15m/5m scanner (file is 5m data, 0.35%/candle thresholds, misnamed); (3) RR_ENGINE audit-then-FORCE; (4) **SKIP** bypass shrink-to-6 — incremental prune only; (5) SHORT gate = RSI>=40 + EXTREME, not EXTREME-only.
3. **Frequency = B:** fix edge first; raise entry bar only if fee drag still dominates after 48h; reject size-up.
4. **Philosophy = A (amended):** "every dump is a SHORT opportunity **only when not oversold** (exec RSI>=40, regime habitat)". **T must acknowledge before AGENTS.md rewrite.**

**Delegated:** bug_hunter (exec-RSI path audit + RR_ENGINE shadow analysis), self_learner (48h zero-oversold-SHORT verification), signal_analyst (scanner retune + EXTREME SHORT habitat memory).

**Metric checkpoint 2026-10-07:** SHORT 7d ≥ $0, oversold SHORT entries = 0.

## Automation Actions Today (verified in code/logs)

- **🟢 CEO 00:30 MoE decisions — 0 CONFIG** — full report automation/ceo/ceo_report.md. Kanban updated. Protected flags untouched.
- **🟢 auto_1hr 22:11 CONFIG** — volume-breakout boost 1.15→1.25 APPLIED at signal_compactor.py:709, pipeline restarted 23:10. Bollinger window over.
- **🟢 CEO 17:50 0 CONFIG — window was active** — historical; window since ended.

## Standing Decisions (do not re-litigate)

- **SIGNAL KILL POLICY:** regime-block via volatility_gate_v2 if wins in ANY regime. Blanket-kill ONLY if loses in ALL regimes.
- **SHORT ENTRY MODEL (2026-10-04):** exec RSI>=40 all paths; EXTREME habitat; NEUTRAL blocked. MoE panel + DB-verified.
- **0 config changes when monitor windows active.** None active now (bollinger ended).
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
- **AGENTS.md philosophy line** — amend only after T acknowledges conditioned SHORT rule.

## Monitor List (next 48h)

1. **Exec-RSI audit result** — which paths still allow SHORT with exec RSI<40 (bug_hunter).
2. **ZERO oversold SHORT entries** 48h post-audit (self_learner) — query exec RSI, not entry_rsi_14.
3. **SHORT 7d PnL ≥ $0 by 2026-10-07.**
4. volume-breakout-long+ post-boost live performance (conf 1.25).
5. accel_300_v3_long — still ENABLED, prior watch NEUTRAL bleed.
6. RR_ENGINE shadow would-have-blocked analysis (bug_hunter).
7. 15m/5m scanner retune (signal_analyst).
8. doji-bottom-long → 20T for conf boost.
9. hard_max_loss semantics — price vs leveraged PnL (bug_hunter).
10. mover+ entry quality (signal_analyst).
11. ema_reclaim_long 0 signals — coverage + partners (signal_analyst).
12. Disk 82% — prune at 88%.
13. ORPHAN_PAPER BTC amount=0 hygiene.
14. DRIFT-002 — exec-time RSI timeframe (bug_hunter owns).
15. HL API key reminder in AGENTS.md STALE — T: verify/correct.
16. Coin tracker intelligence — Wyckoff/Elliott/Volume unbuilt (signal_analyst).
17. pnl_usdt vs fees.net_pnl inconsistency — accounting audit (bug_hunter, non-trading-path).
18. OpenMemory service inactive — HTTP API works.

## Backlog / Delegated (not orchestrator's call)

- **DELEGATE bug_hunter:** SHORT exec-RSI path audit (bypass, stale fail-open, DRIFT-002).
- **DELEGATE bug_hunter:** RR_ENGINE shadow-block 7d would-have-blocked analysis → FORCE recommendation with numbers.
- **DELEGATE bug_hunter:** fees JSON vs pnl_usdt accounting gap.
- **DELEGATE self_learner:** 48h verification — zero SHORT entries with exec RSI<40.
- **DELEGATE signal_analyst:** retune 15m/5m scanner thresholds; snapshot EXTREME+RSI>=40 SHORT habitat.
- **DELEGATE signal_analyst:** ema_reclaim_long detection coverage + confluence partners.
- **DELEGATE signal_analyst:** mover+ entry quality — deep atr_sl_hit at high conf.
- **DELEGATE signal_analyst:** coin_tracker Wyckoff/phase-transition signal (1/week min).
- **T ack required:** AGENTS.md philosophy amendment (conditioned SHORT rule).
- **bollinger_squeeze SHORT side** — research PASS historically but OFF until SHORT R:R fixed.
- **bugs.json OPEN** — coin_tracker/backfill — not trading-path.

## Orchestrator / CEO Report (2026-10-04 00:30 UTC)

- **0 trading config changes** — MoE decision run only.
- **D1=A, D2 priority with skip list, D3=B, D4=A** — full reasoning in automation/ceo/ceo_report.md.
- **VERIFIED all numbers from PG directly.** 30d -$2.22/51.4%, SHORT -$4.12, oversold SHORT -$5.04, EXTREME RSI>=40 SHORT +$0.98 only positive cell.
- **MoE claim rejected:** "wave bottoms 94%WR" — DB contradicts (32.6%WR at RSI<40).
- **Exec-RSI floor already live** (bf96d7cd Oct 3) — priority is audit holes, not re-add filters.
- **Bypass shrink-to-6 rejected** — would freeze NEUTRAL system.
- **volume-breakout boost applied** 22:11 by auto_1hr — window over.
- **Protected flags untouched.**

