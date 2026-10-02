# Current State — System Improvement Focus

**Last Updated: 2026-10-02 18:45 UTC**
**Updated by: Daily Orchestrator (PG-verified)**

## Current Status

**PIPELINE ACTIVE + SYSTEM POSITIVE (weaker than 14:00 snapshot).** 0 real open trades. Only PG open row: BTC ORPHAN_PAPER amount_usdt=0.00 continuum_engine (data hygiene). Hotset intermittent — when populated, execution gates block (volatility storm / LLM reject), not compactor failure.

**PG live (orchestrator-verified, status='closed'):** **24h:** 53T 62.3%WR **+$1.11**. **Today:** 51T 60.8%WR +$0.92. **7d:** 164T 50.6%WR **+$0.99** (was +$2.22 at 14:00 — PnL faded). LONG 7d +$2.31 (116T 52.6%). SHORT 7d **-$1.32** (48T 45.8%). Regimes 7d: EXTREME +$0.78 (74T), FLAT +$0.27 (5T), HIGH +$0.20 (40T), **NORMAL -$0.26 (42T) — flipped negative**.

## Automation Actions Today (verified in code/logs)

- **🟢 auto_1hr KILLED mtf-regime-trend+** 15:11 (`MTF_REGIME_TREND_PLUS_ENABLED=False`). **Kill verified:** 0 LONG signals since 15:11. Policy OK — 7d by regime: HIGH 6T 2W -$0.40, NORMAL 3T 2W -$0.06, no winning regimes → blanket-kill allowed. MINUS untouched (still generating shorts).
- **🟢 signal_reporter BOOSTED bb-squeeze+** 17:12 — compactor weight **1.2x** (`signal_compactor.py:616`), FAMILY_MAP Squeeze entry present. PG: bb-squeeze+ 25T 60%WR +$0.21 (thin edge, sample ≥20). SHORT side stays OFF.
- **🟢 upgrade_implementer OSCILLATOR_MULTS retune** 18:20 — MID/falling 1.0→**0.7**, LOW/accelerating 1.1→**0.9** (45d PG join). Pipeline restarted. Monitor window active — **do not stack**.
- **🟢 ema_reclaim detection WORKS** — XPL LONG conf=79 at 15:20:14 in runtime DB. CURRENT 14:00 "0 signals" was stale. Rate still low (1/24h) by design (decline≥0.4%, vol≥0.6x, RSI 35–55). NOT standalone-bypass. **Close signal_analyst delegation — detection confirmed.**

## Execution Gate Status (0 open trades explained)

- **STX SHORT (mtf-regime-trend-)**: hotset conf=93 → blocked `volatility gate: storm ATR=1.62% > 1.5%` — working as designed.
- **BTC SHORT (continuum-osc-)**: hotset conf=77 → blocked `LLM rejected: setup is actively harmful` — context gate working.
- Health monitor "compactor approving 0 of 218" is **intermittent hotset emptiness + execution blocks**, not a dead compactor. Approved signals appear when signals survive compaction.

## Standing Decisions (do not re-litigate)

- **SIGNAL KILL POLICY:** regime-block via volatility_gate_v2 (0.0x) if wins in ANY regime. Blanket-kill ONLY if loses in ALL regimes. FAMILY_MAP in market_phase_gate.py.
- **0 config changes when monitor windows active.** Active: bollinger_squeeze re-enable, volume-breakout tests, SHORT-CONTINUUM, HARD_FLOOR, ema_reclaim shadow, bb-squeeze EXTREME, doji 20T, **oscillator matrix retune (18:20)**.
- **No time-of-day blanket blocks.** Entry quality filters only.
- **hermes_constants.py:** do not change VALUES without CEO/T. Crash-bug code fixes allowed.
- **NEUTRAL_SNIPER_ENABLED=False** — human-disabled Sep 12 per T.
- **Blacklist testing COMPLETE** — 77 tokens, 0 KEEP. Stop rotating.
- **PM_TRAIL / ATR_SL protected.**
- **signal_version.py missing** — stop flagging.
- **Disk prune:** mtf_macd_tuner backtest OK >7d. coin_tracker/candles NEVER vacuum during trading. Next prune when disk >88%.

## Monitor List (next 48h)

1. Hotset fill rate — intermittent empty cycles; starvation if LONG signals stay rare
2. NORMAL regime 7d -$0.26 — was +$0.31; regime bleed new
3. Oscillator matrix retune — MID/falling, LOW/accelerating WR over 7d
4. bb-squeeze+ — thin edge at 25T; HIGH habitat
5. volume-breakout-long+ live tests (JUP/IMX)
6. doji-bottom-long — 20T conf-boost; NORMAL bleed
7. ema_reclaim — low fire rate OK; watch confluence pairs
8. SHORT_CONTINUUM_SCORE_MAX=30 — legitimate STRONG_NEG SHORTs
9. SHORT R:R structural -$1.32/7d
10. bb-bounce-v3-long+ — 3T kill threshold
11. Disk 85% — growth rate
12. pump_chain_v5_short rsi:0 spam — fix if worsens
13. ORPHAN_PAPER BTC amount=0 hygiene
14. pnl_pct nonsense values — data-path bug
15. hermes-wasp LOCK-WAIT + better-coder ModuleNotFoundError — code-owner
16. continuum+ 7d 2T 0%WR — watch to 3 closes

## Backlog / Delegated (not orchestrator's call)

- **ema_reclaim detection** — CONFIRMED WORKING (XPL 15:20). Delegation closable.
- **bollinger_squeeze SHORT side** — research PASS historically but OFF until SHORT R:R fixed
- **NEUTRAL diversity beyond ema_reclaim** — volume-dry-up unbuilt
- **Signal conf boosts** below sample thresholds
- **Dead code cleanup:** orphan signal files with signal_gen imports
- **bugs.json OPEN (11):** coin_tracker/backfill — not trading-path
- **AGENTS.md HL API key reminder STALE** — "expires in 3 days" wrong (set 2026-09-16, ~164d left). **T: verify/correct.**
- **Coin tracker intelligence** — Wyckoff/Elliott/Volume unbuilt; COIN_TRACKER_HOT_PLUS needs T

## Orchestrator / Report (2026-10-02 18:45 UTC)

- **0 TRADING CONFIG CHANGES.** Monitor windows active; stacking prevents measurement.
- **VERIFIED all numbers from PG directly** (status lowercase; close_time). Prior CURRENT 24h +$2.43 / 7d +$2.22 were stale — actual +$1.11 / +$0.99.
- **Verified automation implementations:** mtf-regime-trend+ kill, bb-squeeze+ boost+FAMILY_MAP, oscillator retune, ema_reclaim detection (1 fire).
- **0 open trades = gates working** (storm + LLM), not pipeline failure.
- **NEW FINDING:** NORMAL regime 7d -$0.26 (flipped from +$0.31).
