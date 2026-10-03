# Current State — System Improvement Focus

**Last Updated: 2026-10-03 02:00 UTC**
**Updated by: CEO (PG-verified)**

## Current Status

**PIPELINE ACTIVE + SYSTEM POSITIVE (thin).** 0 open trades. Hotset empty — confluence gate blocking single-type SHORTs in flat NEUTRAL market (gates working). **POST-FIX SHORT = 0 closed** since Oct 2 15:30 — Fix1/Fix2 live, SHORT drought continues (122 SHORT pump-chain signals/6h all EXPIRED).

**PG live (CEO-verified, status='closed'):** **24h:** 50T 62.0%WR **+$0.30**. **7d:** 168T 51.2%WR **+$1.16**. LONG 7d +$2.48 (120T 53.3%). SHORT 7d **-$1.32** (48T 45.8%). BEST: volume-breakout-long+ EXTREME 30d 14T 78.6%WR **+$3.47** (conf-boost at 20T, 6T remaining). doji-bottom HIGH 9T 88.9% +$0.79. Disk **85%** (pruned from 89%).

## Automation Actions Today (verified in code/logs)

- **🟢 CEO 02:00 grind_accumulator BUGFIX** — missing imports `GRIND_ACCUM_VOL_WINDOW` + `GRIND_ACCUM_VOL_AVG_WINDOW`. Pipeline restarted 01:53 — `Signal grind_accumulator: 0` (was ERROR every ~60s).
- **🟢 CEO 02:00 DISK PRUNE 89%→85%** — mtf_macd_tuner >7d (389k results + 358 runs) + vacuum; hl_copy fills >30d (35k) + vacuum; 4 logs rotated. coin_tracker/candles untouched.
- **🟢 brain_auditor 23:36 V5 test EXPIRED** — PUMP_CHAIN_V5_ENABLED True→False (9T 33.3%WR -$0.37). SHORT flag separate, untouched.
- **🟢 CEO 21:55 REVERT** — `SHORT_CONTINUUM_SCORE_MAX` **40→30** (undocumented drift during monitor window).
- **🟢 CEO 19:55 Fix1+Fix2** — continuum-trend± v1 REGIME_SIGNALS + pump-chain bear-override. Committed.

## Execution Gate Status (0 open trades explained)

- **Hotset EMPTY** — confluence gate: SHORTs pass regime checks but fail 2-type confluence in flat NEUTRAL. `CONFLUENCE_REQUIRED=True` (protected). Expected.
- 46 signal types run, grind_accumulator now clean (was erroring).

## Standing Decisions (do not re-litigate)

- **SIGNAL KILL POLICY:** regime-block via volatility_gate_v2 if wins in ANY regime. Blanket-kill ONLY if loses in ALL regimes.
- **0 config changes when monitor windows active.** Active: bollinger_squeeze, volume-breakout tests, SHORT-CONTINUUM@30, HARD_FLOOR, ema_reclaim shadow, bb-squeeze EXTREME, doji 20T, oscillator matrix retune.
- **No time-of-day blanket blocks.** Entry quality filters only.
- **hermes_constants.py:** do not change VALUES without CEO/T. Crash-bug code fixes allowed.
- **NEUTRAL_SNIPER_ENABLED=False** — human-disabled Sep 12 per T.
- **Blacklist testing COMPLETE** — 77 tokens, 0 KEEP. Stop rotating.
- **PM_TRAIL / ATR_SL protected.**
- **signal_version.py missing** — stop flagging.
- **Disk prune:** coin_tracker/candles NEVER vacuum during trading. Next prune when disk >88%. **Now 85%.**
- **V5 LONG disabled** — do not re-enable (brain_auditor 23:36, test failed).

## Monitor List (next 48h)

1. SHORT trade count post-Fix1/Fix2 (still 0 — drought)
2. volume-breakout EXTREME → 20T for conf boost (14T now)
3. doji-bottom → 20T (14T 30d total)
4. Hotset fill rate — confluence starvation in flat market
5. grind_accumulator — first signals after import fix
6. mover+ R:R — 30d 57.1%WR but -$0.85 (tune, not kill)
7. bb-squeeze+ HIGH habitat (11T 63.6% since re-enable)
8. ema_reclaim shadow — 1 signal/48h, needs confluence partners
9. SHORT R:R structural — delegate signal_analyst exit quality
10. SHORT_CONTINUUM_SCORE_MAX=30 — monitor, do not raise without post-Fix2 SHORT data
11. Disk 85% — prune at 88%
12. ORPHAN_PAPER BTC amount=0 hygiene
13. pnl_pct nonsense values — data-path bug
14. DRIFT-002 — exec-time RSI timeframe (bug_hunter owns)
15. AGENTS.md HL API key reminder STALE — **T: verify/correct**
16. Coin tracker intelligence — Wyckoff/Elliott/Volume unbuilt; COIN_TRACKER_HOT_PLUS needs T

## Backlog / Delegated (not orchestrator's call)

- **DELEGATE signal_analyst: SHORT exit quality** — hard_sl/hard_max_loss dominant; trail works LONG not SHORT. Fix R:R after gates unblocked.
- **DELEGATE signal_analyst: volume-breakout EXTREME conf-boost at 20T**
- **DELEGATE bug_hunter: DRIFT-002** exec-time RSI 5m vs signal 1m
- **ema_reclaim** — built, shadow, 1 signal; needs confluence pairs
- **bollinger_squeeze SHORT side** — research PASS historically but OFF until SHORT R:R fixed
- **bugs.json OPEN (11):** coin_tracker/backfill — not trading-path
- **Coin tracker intelligence** — Wyckoff/Elliott/Volume unbuilt; COIN_TRACKER_HOT_PLUS needs T

## Orchestrator / CEO Report (2026-10-03 02:00 UTC)

- **1 CODE FIX + DISK PRUNE.** grind_accumulator imports fixed; disk 89%→85%.
- **VERIFIED all numbers from PG directly.** 24h +$0.30 / 7d +$1.16.
- **0 trading config changes** — monitor windows active.
- **0 open trades = confluence gate working** (flat NEUTRAL), not pipeline failure.
- **volume-breakout EXTREME 14T 78.6% +$3.47/30d** — best signal, boost waits for 20T.
