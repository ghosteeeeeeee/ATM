# Current State — System Improvement Focus

**Last Updated: 2026-10-03 17:50 UTC**
**Updated by: CEO (PG-verified)**

## Current Status

**PIPELINE ACTIVE + 7d/24h IMPROVING + BOOST QUEUED.** 2 open LONG near-breakeven (COMP bb-bounce-v3 +0.16%, SUSHI bb-squeeze -0.51%). Regime 100% NEUTRAL. **Bollinger 48h window ACTIVE until 21:55 UTC — 0 trading config changes until then.**

**PG live (CEO-verified, status='closed'):** **24h:** 31T 61.3%WR **+$1.24** (improved from 13:50 $0.00/43.3%). **Oct3 alone 28T 64.3%WR +$1.67.** **7d:** 194T 52.6%WR **+$2.47** (up from +$2.22). LONG 7d **+$3.61/141T 54.6%**. SHORT 7d **-$1.14/53T 47.2%** (improved from -$1.48). BEST: **volume-breakout-long+ 22T 72.7%WR +$3.42/30d all regime=NEUTRAL — conf boost 1.15→1.25 QUEUED at signal_compactor.py:709 until 21:55 UTC.** doji-bottom 14T 71.4% +$0.79/30d (below 20T). **ema_reclaim_long: 0 signals every cycle.** **accel_300_v3_long: ENABLED=True, 7T/7d -$0.37 42.9%WR all NEUTRAL — NEW WATCH post-window.** Disk **80%**. Pipeline healthy.

## Automation Actions Today (verified in code/logs)

- **🟢 CEO 17:50 0 CONFIG — window active** — volume-breakout boost still QUEUED; location re-verified signal_compactor.py:709. 7d improved +$2.47. **NEW WATCH: accel_300_v3_long 7T/7d -$0.37 NEUTRAL** — EXTREME/FLAT blocks don't cover active regime. Regime memory refreshed wr=52.6 7d=+2.47.
- **🟢 CEO 13:49 0 CONFIG — window active** — volume-breakout boost 1.15→1.25 still QUEUED; location confirmed signal_compactor.py:709. 7d improved +$2.22. ema_reclaim 0-trade escalated. Regime memory refreshed.
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
- **Disk prune:** coin_tracker/candles NEVER vacuum during trading. Next prune when disk >88%. Now 80%.
- **V5 LONG disabled** — do not re-enable.
- **mtf-regime-trend+ disabled** — killed Oct 2 15:11. 9T/7d -$0.46 legacy aging out.

## Monitor List (next 48h)

1. **volume-breakout conf boost 1.15→1.25 — APPLY after 21:55 UTC today** at signal_compactor.py:709. 22T 72.7%WR +$3.42 all regime=NEUTRAL verified. Restart pipeline after apply.
2. **accel_300_v3_long post-window** — ENABLED=True, 7T/7d -$0.37 42.9%WR all NEUTRAL. EXTREME/FLAT blocks don't cover active regime. NEUTRAL block or disable.
3. doji-bottom-long → 20T (14T/30d now) for conf boost
4. SHORT trade count post-Fix1/Fix2 (53 closed 7d, -$1.14 — drought easing but still bleeding)
5. **hard_max_loss semantics** — price vs leveraged PnL (bug_hunter). If position-PnL intended, CUT_LOSER_PNL=-1.00 is 5x too loose at lev 5.
6. mover+ entry quality — atr_sl_hit deep losses at conf 90-104. DELEGATE signal_analyst.
7. bb-squeeze+ HIGH habitat (27T 55.6% -$0.07 monitor)
8. ema_reclaim shadow — 0 closed trades, needs confluence partners
9. Hotset fill rate — confluence starvation in flat NEUTRAL
10. SHORT_CONTINUUM_SCORE_MAX=30 — monitor, do not raise without post-Fix2 SHORT data
11. Disk 80% — prune at 88%
12. Open: COMP bb-bounce-v3 +0.16%, SUSHI bb-squeeze -0.51% — let them play out
13. ORPHAN_PAPER BTC amount=0 hygiene
14. DRIFT-002 — exec-time RSI timeframe (bug_hunter owns)
15. AGENTS.md HL API key reminder STALE — T: verify/correct
16. Coin tracker intelligence — Wyckoff/Elliott/Volume unbuilt; DELEGATE signal_analyst
17. ATM/ArcHitecture.md missing — recreate if needed
18. OpenMemory service inactive — MCP endpoint works via HTTP API with Accept header

## Backlog / Delegated (not orchestrator's call)

- **DELEGATE signal_analyst: ema_reclaim_long 0 signals every cycle** — detection coverage + confluence partner build
- **DELEGATE signal_analyst: volume-breakout conf-boost 1.15→1.25** — READY, apply post-21:55 UTC at signal_compactor.py:709
- **DELEGATE signal_analyst: mover+ entry quality** — deep atr_sl_hit at high conf
- **DELEGATE signal_analyst: coin_tracker Wyckoff/phase-transition signal** — 1 per week minimum
- **DELEGATE signal_analyst: SHORT exit quality** — hard_sl/hard_max_loss dominant
- **DELEGATE signal_analyst: accel_300_v3_long NEUTRAL habitat** — 7T/7d -$0.37 42.9%, post-window
- **DELEGATE bug_hunter: hard_max_loss live_pnl semantics** — price vs leveraged PnL
- **DELEGATE bug_hunter: DRIFT-002** exec-time RSI 5m vs signal 1m
- **bollinger_squeeze SHORT side** — research PASS historically but OFF until SHORT R:R fixed
- **bugs.json OPEN** — coin_tracker/backfill — not trading-path
- **Coin tracker intelligence** — Wyckoff/Elliott/Volume unbuilt; COIN_TRACKER_HOT_PLUS needs T

## Orchestrator / CEO Report (2026-10-03 17:50 UTC)

- **0 trading config changes** — bollinger_squeeze 48h window active until 21:55 UTC.
- **volume-breakout conf boost QUEUED** — 22T 72.7%WR +$3.42 ALL NEUTRAL, apply 1.15→1.25 after window ends (signal_compactor.py:709 re-verified).
- **NEW WATCH: accel_300_v3_long** — ENABLED=True, 7T/7d -$0.37 42.9%WR all NEUTRAL. EXTREME/FLAT blocks don't cover active regime. Post-window: NEUTRAL block or disable.
- **VERIFIED all numbers from PG directly.** 24h +$1.24/61.3% (improved from 13:50 $0.00/43.3%), 7d +$2.47/52.6%, Oct3 alone +$1.67/64.3%.
- **Regime memory refreshed** snapshot 17:50 wr=52.6 7d=+2.47.
- **SHORT still bleeding** -$1.14/53T 47.2% (improving). Do not raise SHORT_CONTINUUM_SCORE_MAX yet.
