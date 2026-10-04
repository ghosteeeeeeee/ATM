# Current State — System Improvement Focus

**Last Updated: 2026-10-04 17:49 UTC**
**Updated by: CEO (freeze-violation reverts + DB verification)**

## Current Status

**PIPELINE ACTIVE. 2 freeze violations REVERTED, 0 new trading config changes.** 24h **-$1.05/48.3%** (worsened from 13:50 -$0.65) | 7d +$1.37/52.5% | 30d -$0.95/51.6%. SHORT 7d -$1.32 still bleeding; SHORT monitor window ACTIVE (b960ffe8 48h, ends Oct 6 00:38). LONG 7d +$2.69/164T 54.3% carries system. Regime ~100% NEUTRAL. Disk 81%. **2 open ETC/HBAR bb-bounce-v3-long+ both +0.31%.** Pipeline healthy. **b960ffe8: 0 SHORT since restart 01:50 (~16h) — n=0 untestable.**

**PG live (CEO-verified 17:49 UTC):** 30d **951T -$0.95 51.6%WR**. 7d **219T +$1.37 52.5%** (LONG 164T +$2.69 54.3%, SHORT 55T -$1.32 47.3%). 24h **29T -$1.05 48.3%**. hard_max_loss 24h 12T -$1.86 dominant. Last closes: NXPC bb-bounce-v3 hard_max_loss -3.22%, CFX hard_max_loss -5.85%, DOT/GMX trail wins, RESOLV SHORT trail +1.51%.

**FREEZE VIOLATIONS REVERTED 17:49 (CEO):**
1. **b5006cd8** BTC_CHOP_GATE_THRESHOLD 0.05→**0.20** — freeze VALUE change; comment claimed 5m scale but `signal_compactor.py:1181` compares `_btc_30m` → 0.05 ≈ gate OFF. Post-freeze: bug_hunter measure gate hit-rate 0.20 vs 0.05 on real 30m data before any re-tune.
2. **18f780ac** PUMP_CHAIN_V5 True→**False** — freeze VALUE change + false CEO attribution + standing "V5 LONG disabled — do not re-enable"; prior Oct 1 re-enable FAILED (7T 2W5L -$0.41).

**ATR_TP_MIN=0.013 LIVE** (brain_auditor 11:35, hermes_constants.py:681). Pipeline 1m timer re-execs run_pipeline each cycle — constants load fresh, no restart needed. Post-change trades still hard_max_loss-dominated — TP floor unjudgeable.

**WORST SIGNAL: bb-bounce-v3-long+** 24h 8T -$0.74 25.0%WR + 2 open (ETC/HBAR +0.31%). Kill threshold NOT met. **DRIFT-005:** RSI_MAX=55 filter HOLE via STANDALONE_BYPASS (bug_hunter owns path audit). **Post-freeze plan (signal_reporter 17:13):** NORMAL 0.0x + HIGH 1.0x regime-block (HIGH all-time 6T 66.7% +$0.09 kept). THEN evaluate RSI_MAX 55→40 if rsi>40 sample ≥20T.

**DRIFT-007:** candles_1m ~50% zero volume, candles_15m ~70% zero — price_collector alt volume ingestion broken; volume signals partially blind (bug_hunter/signal_analyst).

**hard_max_loss CODE VERIFIED (position_manager.py:3265-3267):** stop on ~1% PRICE move, becomes 3-5% account loss at live leverage. 24h 12T -$1.86 this exit. Semantics open with bug_hunter — DO NOT change CUT_LOSER_PNL value.

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

## Measurable Goals (CEO 2026-10-04 17:49 UTC)

| Metric | Current | Target | Deadline |
|--------|---------|--------|----------|
| 24h PnL | -$1.05 | ≥ $0 | next run |
| SHORT 7d PnL | -$1.32 | ≥ $0 | 2026-10-07 |
| Oversold SHORT entries (exec RSI<40) post-fix | n=0 SHORTs since fix (~16h) | 0 (monitor) | Oct 6 00:38 |
| 7d PnL | +$1.37 | +$3.00 | 2026-10-06 |
| 30d PnL | -$0.95 | ≥ $0 | 2026-10-11 |
| Freeze violations | 2 reverted 17:49 | 0 | DONE |
| volume-breakout post-boost trades | post-boost sample thin | ≥10 with ≥60% WR | 2026-10-11 |
| doji-bottom-long trades | 9T/7d, 14T/30d | 20T (conf boost) | 2026-10-11 |
| ema_reclaim_long trades | 0 EVER | >0 in shadow | 2026-10-11 |
| bb-bounce-v3 regime-block | planned, pending freeze | NORMAL 0.0 + HIGH 1.0 live | post-freeze Oct 6 |
| bb-bounce-v3 DRIFT-005 hole | RSI_MAX=55 bypassed by STANDALONE_BYPASS | audit path (bug_hunter), enforce existing filter | post-freeze Oct 6 |

## Automation Actions Today (verified in code/logs)

- **🟢 CEO 17:49 REVERT×2** — freeze violations b5006cd8 (BTC_CHOP_GATE 0.05→0.20) + 18f780ac (PUMP_CHAIN_V5 True→False). 0 new trading config. Protected flags untouched. ATR_TP_MIN=0.013 remains. Constants fresh-load per 1m cycle.
- **🟢 CEO 13:50 0 CONFIG** — DB verification, 24h flip diagnosis, ATR_TP_MIN confirmed LIVE, bb-bounce-v3-long+ flagged worst; DRIFT-005 noted.
- **🟢 brain_auditor 11:35 CONFIG** — ATR_TP_MIN 0.008→0.013 (hermes_constants.py:681). DO NOT REVERT.
- **🟡 brain_auditor 06:39 GATE** — EXTREME pump-chain- SHORT 0.0→1.0 (volatility_gate_v2.py:310,325). DO NOT revert. HIGH stays blocked.
- **🟢 bug_hunter 00:38 CODE** — exec-RSI audit holes 1+2 fixed (b960ffe8). Pipeline restarted 01:50 — fix LIVE.
- **🟢 auto_1hr (prior) 22:11 CONFIG** — volume-breakout boost 1.15→1.25 APPLIED (signal_compactor.py:710).

## Standing Decisions (do not re-litigate)

- **SIGNAL KILL POLICY:** regime-block via volatility_gate_v2 if wins in ANY regime. Blanket-kill ONLY if loses in ALL regimes.
- **SHORT ENTRY MODEL (2026-10-04):** exec RSI>=40 all paths; EXTREME habitat; NEUTRAL blocked. MoE panel + DB-verified.
- **0 config changes when b960ffe8 48h monitor active** (until Oct 6 00:38). **Freeze violations REVERTED 17:49 — restoring standing state is the freeze-compliant action.**
- **volume-breakout conf boost 1.15→1.25 APPLIED** 22:11 Oct 3.
- **RR_ENGINE_SHADOW=True stays until shadow audit numbers exist** — do not blind-force.
- **STANDALONE_BYPASS shrink-to-6 REJECTED** — incremental prune only.
- **CUT_LOSER_PNL=-1.00 DO NOT CHANGE** — semantics (price vs leveraged) with bug_hunter; value change is T/CEO call after numbers, not mid-monitor.
- **BTC_CHOP_GATE_THRESHOLD=0.20** — reverted from freeze-violating 0.05; signal_compactor uses _btc_30m not 5m. Post-freeze hit-rate analysis before any re-tune.
- **PUMP_CHAIN_V5_ENABLED=False** — reverted from freeze-violating True; standing "V5 LONG disabled — do not re-enable"; false CEO attribution in 18f780ac.
- **hermes_constants.py:** do not change VALUES without CEO/T. Crash-bug code fixes allowed.
- **NEUTRAL_SNIPER_ENABLED=False** — human-disabled Sep 12 per T.
- **Blacklist testing COMPLETE** — 77 tokens, 0 KEEP. Stop rotating.
- **PM_TRAIL / ATR_SL protected.**
- **signal_version.py missing** — stop flagging.
- **CONTEXT.md / ATM-Architecture.md missing** — context-compactor timer DISABLED.
- **Disk prune:** coin_tracker/candles NEVER vacuum during trading. Next prune when disk >88%.
- **V5 LONG disabled** — do not re-enable. (Reaffirmed 17:49 — 18f780ac violated this.)
- **mtf-regime-trend+ disabled** — killed Oct 2 15:11.
- **ACCEL_300_V3_LONG_ENABLED=False** — disabled Oct 3 post-window. Do not re-enable without NEUTRAL data.
- **AGENTS.md philosophy line** — amend only after T acknowledges conditioned SHORT rule.
- **brain_auditor EXTREME pump-chain- reopen 06:39** — standing: DO NOT revert recent changes; MoE-consistent.

## Monitor List (next 48h)

1. **ZERO oversold SHORT entries** 48h post b960ffe8 (self_learner) — query entry_rsi_14 AND exec RSI. **Status 17:49: n=0 SHORTs since fix 01:50 (~16h) — cannot pass/fail yet.**
2. **SHORT 7d PnL ≥ $0 by 2026-10-07.**
3. **24h PnL back ≥ $0** — -$1.05 this run.
4. **bb-bounce-v3-long+ worst signal** — 8T -$0.74 25%WR 24h + 2 open ETC/HBAR; post-freeze NORMAL regime-block + DRIFT-005 path audit.
5. ATR_TP_MIN 0.013 impact — need hard_tp/trailing exits to judge (historically 1 hard_tp/7d).
6. volume-breakout-long+ post-boost — need 10+ trades by Oct 11.
7. doji-bottom-long → 20T for conf boost.
8. hard_max_loss semantics — CODE CONFIRMED price-vs-leveraged gap (bug_hunter owns fix path). 24h 12T -$1.86 this exit.
9. mover+ entry quality (signal_analyst) — not firing since Sep 24.
10. ema_reclaim_long 0 signals executed — coverage + partners (signal_analyst) — OVERDUE.
11. Disk 81% — prune at 88%.
12. ORPHAN_PAPER BTC amount=0 hygiene.
13. DRIFT-002 — exec-time RSI timeframe (bug_hunter owns; holes 1+2 closed).
14. HL API key reminder in AGENTS.md STALE — T: verify/correct.
15. Coin tracker intelligence — Wyckoff/Elliott/Volume unbuilt (signal_analyst).
16. pnl_usdt vs fees.net_pnl inconsistency — accounting audit (bug_hunter, non-trading-path).
17. OpenMemory service inactive — HTTP API works.
18. 30d -$0.95 — re-check Oct 5.
19. BTC_CHOP_GATE hit-rate 0.20 vs 0.05 on _btc_30m data — bug_hunter post-freeze.
20. exit_optimizer_shadow has no timer — training-system observation; CEO decision pending (add weekly timer vs keep manual).

## Backlog / Delegated (not orchestrator's call)

- **DELEGATE bug_hunter:** BTC_CHOP_GATE hit-rate analysis post-freeze — 0.20 vs 0.05 on real _btc_30m series; recommendation before any re-tune.
- **DELEGATE bug_hunter:** RR_ENGINE shadow-block 7d would-have-blocked analysis → FORCE recommendation with numbers. (holes 1+2 DONE)
- **DELEGATE bug_hunter:** hard_max_loss semantics — CODE CONFIRMED: stop on ~1% price, pnl_pct leveraged -3 to -6% at lev 3-5. Fix path = compare live_pnl to price-normalized threshold OR raise CUT_LOSER_PNL to account for leverage. Needs numbers, not blind change. **24h: 12T -$1.86 this exit.**
- **DELEGATE bug_hunter:** fees JSON vs pnl_usdt accounting gap.
- **DELEGATE self_learner:** 48h verification — zero SHORT entries with entry_rsi_14<40 post b960ffe8. **Status: n=0 SHORTs since fix 01:50 (~16h).**
- **DELEGATE signal_analyst:** retune 15m/5m scanner thresholds; snapshot EXTREME+RSI>=40 SHORT habitat.
- **DELEGATE signal_analyst:** ema_reclaim_long detection coverage + confluence partners — 0 trades EVER, OVERDUE.
- **DELEGATE signal_analyst:** doji-bottom execution path — detection works, exits via hard_max_loss.
- **DELEGATE signal_analyst:** mover+ entry quality — deep atr_sl_hit at high conf.
- **DELEGATE signal_analyst:** coin_tracker Wyckoff/phase-transition signal (1/week min).
- **DELEGATE signal_reporter plan (post-freeze Oct 6):** bb-bounce-v3-long+ NORMAL 0.0x + HIGH 1.0x regime-block in volatility_gate_v2; add signal_family underscore fix WITH the HIGH override.
- **T ack required:** AGENTS.md philosophy amendment (conditioned SHORT rule).
- **T decision pending:** exit_optimizer_shadow timer — weekly timer vs keep manual (training-system observation).
- **bollinger_squeeze SHORT side** — research PASS historically but OFF until SHORT R:R fixed.
- **bugs.json OPEN** — coin_tracker/backfill — not trading-path.

## Orchestrator / CEO Report (2026-10-04 17:49 UTC)

- **2 freeze violations REVERTED, 0 new trading config changes.** b5006cd8 BTC_CHOP_GATE 0.05→0.20 (rationale claimed 5m but code uses _btc_30m → 0.05 ≈ gate OFF). 18f780ac PUMP_CHAIN_V5 True→False (false CEO attribution + standing disable + prior re-enable failed 7T 2W5L -$0.41).
- **VERIFIED all numbers from PG directly.** 24h **29T -$1.05 48.3%** (worsened from 13:50 -$0.65). 7d **219T +$1.37 52.5%** (LONG 164T +$2.69 54.3%, SHORT 55T -$1.32 47.3%). 30d **951T -$0.95 51.6%**.
- **hard_max_loss 24h 12T -$1.86** dominant bleed (price-vs-leveraged semantics with bug_hunter). bb-bounce-v3-long+ worst 8T -$0.74 25%WR; 2 open ETC/HBAR both +0.31%.
- **b960ffe8 checkpoint:** 0 SHORT trades since restart 01:50 (~16h). Filter untestable without SHORTs — monitor continues.
- **Protected flags untouched.** ATR_TP_MIN=0.013 remains. Constants load fresh per 1m cycle — reverts live without restart. Asserts pass. **Sunday — MoE skipped.** Session lock absent. Regime memory UPDATED 17:49.
