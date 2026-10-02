# Current State — System Improvement Focus

**Last Updated: 2026-10-02 21:55 UTC**
**Updated by: CEO (PG-verified)**

## Current Status

**PIPELINE ACTIVE + SYSTEM POSITIVE (fading).** 0 open trades. Hotset empty — confluence gate blocking single-type SHORTs in flat SHORT_BIAS/NEUTRAL market (gates working, not pipeline failure). Only PG open row historically: BTC ORPHAN_PAPER amount=0 hygiene.

**PG live (CEO-verified, status='closed'):** **24h:** 53T 60.4%WR **+$0.73**. **7d:** 166T 50.6%WR **+$0.80** (was +$2.22 at 14:00 — PnL faded). LONG 7d +$2.12 (118T 52.5%). SHORT 7d **-$1.32** (48T 45.8%, avgW $0.104 vs avgL $0.139). Volatility regimes 7d: EXTREME +$0.78 (74T), FLAT +$0.27 (5T), HIGH -$0.07 (41T), **NORMAL -$0.26 (42T)**. BEST: volume-breakout-long+ EXTREME 30d 16T 81.3%WR +$3.72 (conf-boost at 20T, 4T remaining).

## Automation Actions Today (verified in code/logs)

- **🟢 auto_1hr KILLED mtf-regime-trend+** 15:11. **Kill verified:** 0 LONG signals since 15:11. 7d by regime: no winning regimes → blanket-kill allowed. MINUS untouched.
- **🟢 signal_reporter BOOSTED bb-squeeze+** 17:12 — compactor weight **1.2x**, FAMILY_MAP Squeeze entry present.
- **🟢 upgrade_implementer OSCILLATOR_MULTS retune** 18:20 — MID/falling 1.0→**0.7**, LOW/accelerating 1.1→**0.9**. Pipeline restarted. Monitor window active — **do not stack**.
- **🟢 ema_reclaim detection WORKS** — XPL LONG conf=79 at 15:20:14. Detection confirmed. Not standalone-bypass.
- **🟢 CEO 19:55 plan:** Fix1 (continuum-trend± v1 REGIME_SIGNALS) SHIPPED+committed; Fix2 (pump-chain bear-override RSI_MIN) COMMITTED 151bf30a; bear/bull RSI overrides live; CL_TIER1 inversion fix committed.
- **🟢 CEO 21:55 REVERT:** `SHORT_CONTINUUM_SCORE_MAX` **40→30** — working-tree raise was undocumented while monitor window active at 30. Bear-structure bypass already live via Fix1/Fix2. Compactor one-shot timer reloaded SCORE_MAX=30.

## Execution Gate Status (0 open trades explained)

- **Hotset EMPTY** — confluence gate: MON SHORT passes SHORT-NEUTRAL-BYPASS (1m SHORT_BIAS) but blocked as single-type (hmacd_mtf--) not in STANDALONE_BYPASS. `CONFLUENCE_REQUIRED=True` (protected). Expected in flat market.
- 45 signal types run, 89 signals in last 2h signals_db, 0 approved — quality gate, not detector failure.

## Standing Decisions (do not re-litigate)

- **SIGNAL KILL POLICY:** regime-block via volatility_gate_v2 if wins in ANY regime. Blanket-kill ONLY if loses in ALL regimes.
- **0 config changes when monitor windows active.** Active: bollinger_squeeze re-enable, volume-breakout tests, SHORT-CONTINUUM@30, HARD_FLOOR, ema_reclaim shadow, bb-squeeze EXTREME, doji 20T, **oscillator matrix retune (18:20)**.
- **No time-of-day blanket blocks.** Entry quality filters only.
- **hermes_constants.py:** do not change VALUES without CEO/T. Crash-bug code fixes allowed.
- **NEUTRAL_SNIPER_ENABLED=False** — human-disabled Sep 12 per T.
- **Blacklist testing COMPLETE** — 77 tokens, 0 KEEP. Stop rotating.
- **PM_TRAIL / ATR_SL protected.**
- **signal_version.py missing** — stop flagging.
- **Disk prune:** mtf_macd_tuner backtest OK >7d. coin_tracker/candles NEVER vacuum during trading. Next prune when disk >88%. **Now 87%.**

## Monitor List (next 48h)

1. SHORT trade count post-Fix1/Fix2 (drought)
2. pump-chain- bear-override WR — re-eval at 15 post-fix trades (currently 8T 25% -$0.59)
3. volume-breakout EXTREME → 20T for conf boost (16T now)
4. Hotset fill rate — confluence starvation in flat market
5. NORMAL regime 7d -$0.26
6. Oscillator matrix retune — MID/falling, LOW/accelerating WR over 7d
7. bb-squeeze+ — thin edge 26T; HIGH habitat
8. doji-bottom-long — 20T conf-boost threshold
9. SHORT R:R structural — delegate signal_analyst exit quality
10. SHORT_CONTINUUM_SCORE_MAX=30 — monitor, do not raise without data
11. Disk 87% — prune at 88%
12. ORPHAN_PAPER BTC amount=0 hygiene
13. pnl_pct nonsense values — data-path bug
14. continuum+ 7d 4T 25%WR — watch
15. AGENTS.md HL API key reminder STALE — **T: verify/correct**
16. Coin tracker intelligence — Wyckoff/Elliott/Volume unbuilt; COIN_TRACKER_HOT_PLUS needs T

## Backlog / Delegated (not orchestrator's call)

- **DELEGATE signal_analyst: SHORT exit quality** — hard_sl/hard_max_loss dominant; trail works LONG not SHORT. Fix R:R after gates unblocked.
- **DELEGATE signal_analyst: volume-breakout EXTREME conf-boost at 20T**
- **ema_reclaim** — detection confirmed; needs confluence pairs
- **bollinger_squeeze SHORT side** — research PASS historically but OFF until SHORT R:R fixed
- **NEUTRAL diversity beyond ema_reclaim** — volume-dry-up unbuilt
- **bugs.json OPEN (11):** coin_tracker/backfill — not trading-path
- **Coin tracker intelligence** — Wyckoff/Elliott/Volume unbuilt; COIN_TRACKER_HOT_PLUS needs T

## Orchestrator / CEO Report (2026-10-02 21:55 UTC)

- **1 CONFIG REVERT.** SHORT_CONTINUUM_SCORE_MAX 40→30 (undocumented drift during active monitor window). Compactor reloaded.
- **VERIFIED all numbers from PG directly.** 24h +$0.73 / 7d +$0.80 (faded from +$2.22/+0.99).
- **Fix1+Fix2 committed earlier today** (continuum-trend v1 + pump-chain bear-override).
- **0 open trades = confluence gate working** (single-type SHORT blocked), not pipeline failure.
- **volume-breakout EXTREME 16T 81.3% +$3.72/30d** — best signal, boost waits for 20T.
