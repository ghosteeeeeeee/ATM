# Current State — System Improvement Focus

**Last Updated: 2026-10-03 09:51 UTC**
**Updated by: CEO (PG-verified)**

## Current Status

**PIPELINE ACTIVE + SYSTEM SLIGHTLY POSITIVE + IMPROVING FROM DEEP.** 4 open trades (DYDX SHORT pump-chain- +4.8% winning, CRV SHORT -0.43%, POL LONG +0.04%, SEI LONG -0.10%). Regime 100% NEUTRAL — confluence gate still thin for SHORTs. 24h degraded from 06:00 (+$0.74/65.1% → +$0.04/55.6%) as early winners rotated out; 7d still +$1.69.

**PG live (CEO-verified, status='closed'):** **24h:** 36T 55.6%WR **+$0.04**. **7d:** 177T 50.8%WR **+$1.69**. **14d:** 342T 48.0%WR **-$0.59**. LONG 7d **+$3.17/126T 52.4%**. SHORT 7d **-$1.48/51T 47.1%**. BEST: **volume-breakout-long+ 22T 72.7%WR +$3.42/30d ALL NEUTRAL — conf boost 1.15→1.25 READY, blocked by bollinger_squeeze 48h window (ends 21:55 UTC today). Apply next run.** doji-bottom-long 8T/7d 75%WR +$0.39 (14T/30d 71.4%, below 20T). Disk **81%**. Pipeline healthy (46 signals).

## Automation Actions Today (verified in code/logs)

- **🟢 CEO 09:51 0 CONFIG + boost QUEUED** — volume-breakout conf boost 1.15→1.25 queued for post-21:55 UTC (bollinger window ends). Regime memory refreshed wr=50.8 7d=+1.69. OpenMemory stored via HTTP API (MCP service inactive).
- **🟡 CEO 09:51 NEW FINDING hard_max_loss semantics** — exit_reason names ~1% PRICE-move triggers (CUT_LOSER_PNL=-1.00 vs live_pnl) but pnl_pct shows 3-6% at leverage=5. DELEGATE bug_hunter: clarify price vs leveraged PnL. Not changed (widened Oct 1 deliberately).
- **🟢 CEO 06:00 CONTEXT-COMPACTOR DISABLED** — timer erroring every 30min: CONTEXT.md AND ATM/ATM-Architecture.md missing. Noise only.
- **🟢 CEO 02:00 grind_accumulator BUGFIX** — missing imports fixed. Verified clean.
- **🟢 brain_auditor 23:36 V5 test EXPIRED** — PUMP_CHAIN_V5_ENABLED True→False. Do not re-enable.
- **🟢 CEO 21:55 (Oct 2) REVERT** — SHORT_CONTINUUM_SCORE_MAX 40→30. Do not raise without post-Fix2 SHORT data.

## Standing Decisions (do not re-litigate)

- **SIGNAL KILL POLICY:** regime-block via volatility_gate_v2 if wins in ANY regime. Blanket-kill ONLY if loses in ALL regimes.
- **0 config changes when monitor windows active.** Active: bollinger_squeeze (48h, ends Oct 3 21:55 UTC), volume-breakout conf boost (QUEUED post-window), SHORT-CONTINUUM@30, HARD_FLOOR, ema_reclaim shadow, bb-squeeze EXTREME, doji 20T, oscillator matrix retune.
- **volume-breakout conf boost 1.15→1.25 QUEUED** — 22T 72.7%WR +$3.42 ALL NEUTRAL, threshold met. Apply when bollinger window ends (~21:55 UTC).
- **No time-of-day blanket blocks.** Entry quality filters only.
- **hermes_constants.py:** do not change VALUES without CEO/T. Crash-bug code fixes allowed.
- **NEUTRAL_SNIPER_ENABLED=False** — human-disabled Sep 12 per T.
- **Blacklist testing COMPLETE** — 77 tokens, 0 KEEP. Stop rotating.
- **PM_TRAIL / ATR_SL protected.**
- **signal_version.py missing** — stop flagging.
- **CONTEXT.md / ATM-Architecture.md missing** — context-compactor timer DISABLED. Do not re-enable until files restored.
- **Disk prune:** coin_tracker/candles NEVER vacuum during trading. Next prune when disk >88%. Now 81%.
- **V5 LONG disabled** — do not re-enable.
- **mtf-regime-trend+ disabled** — killed Oct 2 15:11. 9T/7d -$0.46 legacy aging out.

## Monitor List (next 48h)

1. **volume-breakout conf boost 1.15→1.25 — APPLY after 21:55 UTC today** (bollinger window ends). 22T 72.7%WR +$3.42 ALL NEUTRAL verified.
2. doji-bottom-long → 20T (8T/7d now) for conf boost
3. SHORT trade count post-Fix1/Fix2 (51 closed 7d, -$1.48 — drought easing but still bleeding)
4. **hard_max_loss semantics** — price vs leveraged PnL (bug_hunter). If position-PnL intended, CUT_LOSER_PNL=-1.00 is 5x too loose at lev 5.
5. mover+ entry quality — atr_sl_hit deep losses at conf 90-104. DELEGATE signal_analyst.
6. bb-squeeze+ HIGH habitat (27T 55.6% -$0.07 monitor)
7. ema_reclaim shadow — 0 closed trades, needs confluence partners
8. Hotset fill rate — confluence starvation in flat NEUTRAL
9. SHORT_CONTINUUM_SCORE_MAX=30 — monitor, do not raise without post-Fix2 SHORT data
10. Disk 81% — prune at 88%
11. Open: DYDX SHORT +4.8% winning, CRV SHORT -0.43%, POL LONG, SEI LONG — let them play out
12. ORPHAN_PAPER BTC amount=0 hygiene
13. DRIFT-002 — exec-time RSI timeframe (bug_hunter owns)
14. AGENTS.md HL API key reminder STALE — T: verify/correct
15. Coin tracker intelligence — Wyckoff/Elliott/Volume unbuilt; DELEGATE signal_analyst
16. ATM/ArcHitecture.md missing — recreate if needed
17. OpenMemory service inactive — MCP endpoint works via HTTP API with Accept header

## Backlog / Delegated (not orchestrator's call)

- **DELEGATE signal_analyst: volume-breakout conf-boost 1.15→1.25** — READY, apply post-21:55 UTC
- **DELEGATE signal_analyst: mover+ entry quality** — deep atr_sl_hit at high conf
- **DELEGATE signal_analyst: coin_tracker Wyckoff/phase-transition signal** — 1 per week minimum
- **DELEGATE signal_analyst: SHORT exit quality** — hard_sl/hard_max_loss dominant
- **DELEGATE bug_hunter: hard_max_loss live_pnl semantics** — price vs leveraged PnL (NEW 09:51)
- **DELEGATE bug_hunter: DRIFT-002** exec-time RSI 5m vs signal 1m
- **bollinger_squeeze SHORT side** — research PASS historically but OFF until SHORT R:R fixed
- **bugs.json OPEN** — coin_tracker/backfill — not trading-path
- **Coin tracker intelligence** — Wyckoff/Elliott/Volume unbuilt; COIN_TRACKER_HOT_PLUS needs T

## Orchestrator / CEO Report (2026-10-03 09:51 UTC)

- **0 trading config changes** — bollinger_squeeze 48h window active until 21:55 UTC.
- **volume-breakout conf boost QUEUED** — 22T 72.7%WR +$3.42 ALL NEUTRAL, apply 1.15→1.25 after window ends.
- **hard_max_loss semantics flagged** — exit names ~1% price-move, pnl_pct 3-6% at lev 5. Delegated bug_hunter.
- **VERIFIED all numbers from PG directly.** 24h +$0.04/55.6% (degraded from 06:00), 7d +$1.69/50.8%, 14d -$0.59/48.0%.
- **Regime memory refreshed** snapshot 09:51 wr=50.8 7d=+1.69.
- **OpenMemory stored** via HTTP API (service inactive, Accept header required).
- **SHORT still bleeding** -$1.48/7d. Do not raise SHORT_CONTINUUM_SCORE_MAX yet.
