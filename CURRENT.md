# Current State — System Improvement Focus

**Last Updated: 2026-10-03 06:00 UTC**
**Updated by: CEO (PG-verified)**

## Current Status

**PIPELINE ACTIVE + SYSTEM POSITIVE + IMPROVING.** 3 open trades (APT SHORT losing, DYDX SHORT winning, JUP LONG slight win). Hotset thin — confluence gate + flat NEUTRAL still limiting SHORTs (3 SHORT closed 24h, drought easing). Today alone: 8T 75%WR +$1.39.

**PG live (CEO-verified, status='closed'):** **24h:** 43T 65.1%WR **+$0.74**. **7d:** 174T 51.7%WR **+$2.19**. LONG 7d +$3.46 (124T 53.2%). SHORT 7d **-$1.27** (50T 48.0%). BEST: **volume-breakout-long+ 22T 72.7%WR +$3.42/30d** — ALL NEUTRAL regime, **crossed 20T conf-boost threshold** (boost blocked by active volume-breakout monitor window — READY to apply when window ends). doji-bottom-long 14T 71.4% +$0.79 (below 20T). Disk **82%**. Pipeline healthy (46 signals). grind_accumulator clean post-fix.

## Automation Actions Today (verified in code/logs)

- **🟢 CEO 06:00 CONTEXT-COMPACTOR DISABLED** — `hermes-context-compactor.timer` erroring every 30min: `CONTEXT.md` AND `ATM/ATM-Architecture.md` both missing (deleted in Apr cleanup, never restored). Timer was noise on trading path. CURRENT.md is the live state file. **T: recreate ATM/ArcHitecture.md if architecture doc needed.**
- **🟢 CEO 02:00 grind_accumulator BUGFIX** — missing imports `GRIND_ACCUM_VOL_WINDOW` + `GRIND_ACCUM_VOL_AVG_WINDOW`. Verified clean in pipeline log.
- **🟢 CEO 02:00 DISK PRUNE 89%→85%→82%** — mtf_macd_tuner >7d + hl_copy fills >30d deleted; auto_1hr tmp cleanup 86%→82%.
- **🟢 brain_auditor 23:36 V5 test EXPIRED** — PUMP_CHAIN_V5_ENABLED True→False. Do not re-enable.
- **🟢 CEO 21:55 REVERT** — `SHORT_CONTINUUM_SCORE_MAX` **40→30**. Do not raise without post-Fix2 SHORT data.

## Standing Decisions (do not re-litigate)

- **SIGNAL KILL POLICY:** regime-block via volatility_gate_v2 if wins in ANY regime. Blanket-kill ONLY if loses in ALL regimes.
- **0 config changes when monitor windows active.** Active: bollinger_squeeze, volume-breakout tests, SHORT-CONTINUUM@30, HARD_FLOOR, ema_reclaim shadow, bb-squeeze EXTREME, doji 20T, oscillator matrix retune.
- **No time-of-day blanket blocks.** Entry quality filters only.
- **hermes_constants.py:** do not change VALUES without CEO/T. Crash-bug code fixes allowed.
- **NEUTRAL_SNIPER_ENABLED=False** — human-disabled Sep 12 per T.
- **Blacklist testing COMPLETE** — 77 tokens, 0 KEEP. Stop rotating.
- **PM_TRAIL / ATR_SL protected.**
- **signal_version.py missing** — stop flagging.
- **CONTEXT.md / ATM-ArcHitecture.md missing** — context-compactor timer DISABLED 2026-10-03. Do not re-enable until files restored.
- **Disk prune:** coin_tracker/candles NEVER vacuum during trading. Next prune when disk >88%. Now 82%.
- **V5 LONG disabled** — do not re-enable.

## Monitor List (next 48h)

1. **volume-breakout conf boost — 22T reached, READY.** Apply when volume-breakout monitor window ends. All 22 trades NEUTRAL (not EXTREME as previously assumed).
2. doji-bottom-long → 20T (14T now) for conf boost
3. SHORT trade count post-Fix1/Fix2 (3 closed 24h — drought easing, keep watching)
4. mover+ entry quality — atr_sl_hit 13T deep losses (-3% to -7.5%) at conf 90-104. R:R broken not WR. **DELEGATE signal_analyst.**
5. bb-squeeze+ HIGH habitat (27T 55.6% -$0.07 monitor)
6. ema_reclaim shadow — 0 closed trades, needs confluence partners
7. Hotset fill rate — confluence starvation in flat NEUTRAL
8. SHORT_CONTINUUM_SCORE_MAX=30 — monitor, do not raise without post-Fix2 SHORT data
9. Disk 82% — prune at 88%
10. APT SHORT pump-chain- (open, losing) + DYDX SHORT (open, winning) — let them play out
11. ORPHAN_PAPER BTC amount=0 hygiene
12. pnl_pct nonsense values — data-path bug
13. DRIFT-002 — exec-time RSI timeframe (bug_hunter owns)
14. AGENTS.md HL API key reminder STALE — **T: verify/correct**
15. Coin tracker intelligence — Wyckoff/Elliott/Volume unbuilt; **DELEGATE signal_analyst** build 1 phase-transition signal
16. ATM/ArcHitecture.md missing — recreate if needed (context-compactor disabled)

## Backlog / Delegated (not orchestrator's call)

- **DELEGATE signal_analyst: volume-breakout conf-boost params** — 22T threshold met, prepare boost, apply post-monitor-window
- **DELEGATE signal_analyst: mover+ entry quality** — deep atr_sl_hit losses at high conf; add entry filter (volume/session/trend alignment)
- **DELEGATE signal_analyst: coin_tracker Wyckoff/phase-transition signal** — 1 per week minimum
- **DELEGATE signal_analyst: SHORT exit quality** — hard_sl/hard_max_loss dominant; trail works LONG not SHORT
- **DELEGATE bug_hunter: DRIFT-002** exec-time RSI 5m vs signal 1m
- **bollinger_squeeze SHORT side** — research PASS historically but OFF until SHORT R:R fixed
- **bugs.json OPEN (11):** coin_tracker/backfill — not trading-path
- **Coin tracker intelligence** — Wyckoff/Elliott/Volume unbuilt; COIN_TRACKER_HOT_PLUS needs T

## Orchestrator / CEO Report (2026-10-03 06:00 UTC)

- **0 trading config changes** — monitor windows active.
- **1 infra fix:** context-compactor timer disabled (CONTEXT.md + ATM missing, erroring 30min for weeks).
- **VERIFIED all numbers from PG directly.** 24h +$0.74/65.1% (improving), 7d +$2.19/51.7%. Today +$1.39/75%WR.
- **volume-breakout crossed 20T** — conf boost READY, blocked only by monitor window. All trades NEUTRAL (EXTREME habitat claim was stale).
- **mover+ R:R diagnosed** — atr_sl_hit deep losses at conf 90-104; delegated entry-quality fix.
- **SHORT drought easing** — 3 closed 24h. Do not raise SHORT_CONTINUUM_SCORE_MAX yet.
