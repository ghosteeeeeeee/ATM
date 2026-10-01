# Current State — System Improvement Focus

**Last Updated: 2026-10-01 13:51 UTC**
**Updated by: CEO**

## Current Status

**TRADING RESUMED — BTC LONG continuum-osc+ open (conf=94.4 @ $83691, 13:49).** Hotset empty 13:40-13:48 was transient: BTC RSI=72 blocked by LONG_RSI_CEILING=70, then RSI dropped, signal passed all gates (confluence bypass, REGIME-CONF 0.50x HIGH, safety filter bypass, hotset-final). Pipeline healthy, 30 successful runs.

**24h:** 36T 38.9%WR -$0.83. **7d:** 118T 45.8%WR -$0.35. LONG +$0.80/7d (66T). SHORT -$1.15/7d (52T). All NEUTRAL. **ATR_SL fix VERIFIED:** 3 atr_sl_hit/7d (was 40+). Today's hard_max_loss exits = accel-300-/pump-chain-v5 legacy aging (killed 10:13/11:13, opened pre-kill).

- **🟢 BTC CONTINUUM-OSC+ EXECUTED 13:49.** Passed: LONG-NEUTRAL-BYPASS (1m LONG_BIAS), CONFLUENCE standalone bypass, REGIME-CONF HIGH→0.50x, HOTSET-FINAL-BYPASS, SAFETY-FILTER-BYPASS. Hebbian est WR=58% (n=5), setup-recall 67% (n=6). CTX-GATE rule-based GO. SL=1.3% ATR, TP=0.8% ATR, trail 0.60%/1.20%, 5x lev.
- **🟢 ATR_SL WIDENING VERIFIED WORKING.** 7d: 3 atr_sl_hit (was 40+). hard_max_loss exits remain but are fixed-percentage caps working as designed (5x lev amplifies 0.5%→2.5% actual).
- **🟢 pump-chain- SHORT filters VERIFIED LIVE.** RSI_MIN=40 blocked IOTA RSI=18.4. HIGH_BLOCK blocked BABY/GMT/COMP. 7d 32T 53.1%WR +$0.01 breakeven — quality gate correct.
- **🟢 SHORT_RSI_HARD_FLOOR=25 APPLIED (brain_auditor 11:50).** ~2h old, few trades fired yet. Watch SKIP_HARD / EXEC-RSI-HARD-FLOOR logs.
- **🟢 V5 KILLED + accel-300- KILLED.** PUMP_CHAIN_V5_ENABLED=False (10:13), ACCEL_300_MINUS_ENABLED=False (11:13). Today's hard_max_loss exits from these signals = legacy aging, will clear 48h.
- **🟡 NEUTRAL DIVERSITY SIGNAL STILL UNBUILT.** Delegated signal_analyst Sep 30 — volume-dry-up/EMA-reclaim not in scripts/signals/. #1 gap: 100% trades NEUTRAL, momentum signals (r2-trend-long) blocked by BTC-CHOP-GATE when BTC flat (-0.038%), then expire. Re-delegated 13:51.
- **🟡 doji-bottom-long BEST SIGNAL.** 6T 66.7%WR +$0.27/7d. Below 20T conf-boost threshold. Monitor.
- **🟡 DISK 87%** (97G/118G, 15G free). Large: coin_tracker 3.3G, candles 2.3G, mtf_macd_tuner 1.3G. Delegated bug_hunter for safe analysis (VACUUM INTO backup, candle archive). Do NOT VACUUM active DBs during trading.
- **🟡 Failing services (non-trading):** hermes-wasp (LOCK-WAIT, disabled), hermes-better-coder (ModuleNotFoundError, disabled). Code-owner fixes delegated.
- **OPEN:** 1 position (BTC LONG continuum-osc+).
- **KILLED/REGIME BLOCKED:** pump-chain-v5 LONG (Oct 1 10:13), accel-300- SHORT (Oct 1 11:13), pump-chain+ V5 NEVER_REENABLE (Sep 28), pullback-entry+ NEVER_REENABLE, pump-chain- NEVER_REENABLE, mover+/- NEVER_REENABLE (Sep 24/29), open-skies+ (Sep 22), grind-trend+/- (Sep 19), breakout-long+ (Sep 16), trend_ignition (Sep 16), PUMP_FLOW+ NEVER_REENABLE.
- **CONF_FILTER_MIN=70.** LONG_RSI_CEILING=70 (blocked BTC RSI=72 at 13:47-13:48, worked). SHORT_RSI_FLOOR=40 / CEILING=65 / HARD_FLOOR=25. PUMP_CHAIN_SHORT_RSI_MIN=40. LONG_RSI_FLOOR=20.
- **PM_TRAIL:** ACTIVATE 0.40%, DISTANCE 0.20%. Protected (DO NOT CHANGE).
- **ATR_SL:** MIN 1.3%, MAX 2.0%. EXTREME: MIN 1.5%, 1.2x. VERIFIED — 3 hits/7d.
- **BTC_CHOP_GATE:** blocks momentum signals when BTC 30m flat. Correct behavior but starves NEUTRAL diversity — NEUTRAL signal is the fix.
- **Disk:** 87% (15G free).
- **LONG_NEUTRAL_BLOCK_ENABLED=True.**
- **FINAL_CONFIDENCE:** by design not in _signal_metadata — hotset JSON only.

## Standing Decisions (do not re-litigate)

- **SIGNAL KILL POLICY:** regime-block via volatility_gate_v2 (0.0x) if signal wins in ANY regime. Blanket-kill ONLY if loses in ALL regimes. FAMILY_MAP in market_phase_gate.py.
- **No time-of-day blanket blocks.** Entry quality filters only.
- **hermes_constants.py:** do not change VALUES without CEO/T approval. Crash-bug code fixes allowed (type-safety, imports). Loss-prevention guardrails (RSI floors/ceilings) treated as non-tunable safety nets.
- **NEUTRAL_SNIPER_ENABLED=False** — human-disabled Sep 12 per T. Do not re-enable without T.
- **Blacklist testing COMPLETE** — 77 tokens, 0 KEEP. Stop rotating.
- **0 config changes when fixes are in monitor windows** — stacking changes prevents measurement.

## Monitor List (next 48h)

1. BTC LONG continuum-osc+ — outcome, SL/TP/trail behavior
2. SHORT_RSI_HARD_FLOOR=25 — SKIP_HARD logs, RSI<25 SHORT opens
3. hard_max_loss exits — should decline as accel-300-/V5 age out
4. doji-bottom-long — 20T conf-boost threshold
5. NEUTRAL volume-dry-up/EMA-reclaim signal — still unbuilt? Re-delegated 13:51
6. Disk growth rate — bug_hunter safe analysis
7. PUMP_CHAIN_SHORT_RSI_MIN=40 — golden band 40-45 WR
8. bb_bounce rsi_1m combo path — bug_hunter Oct 3
9. hermes-wasp LOCK-WAIT + better-coder ModuleNotFoundError — code-owner fixes

## Backlog / Delegated (not orchestrator's call)

- **NEUTRAL signal:** re-enable neutral_sniper vs build-new — **T decision** (build-new also delegated to signal_analyst)
- **mover-/mover+ 24h 0%-WR kill variant** — CEO decision pending
- **Signal conf boosts** (vol-breakout EXTREME @20T, doji HIGH @20T, pump-chain- RSI 50-59 @15T) — below sample thresholds
- **Dead imports cleanup:** phase_accel.py, pump_catcher.py, ma_cross_5m.py still import defunct signal_gen
- **bugs.json OPEN:** BUG-020 zombie PRESERVE loop, BUG-021 chop_detector hyphen misclassifies MEAN_REVERSION in CHOP
- **ORPHAN_PAPER $0 trades** in PG — data hygiene
- **AGENTS.md HL API key reminder appears STALE** — says "expires in 3 days" dated 2027-03-12; key set 2026-09-16 valid 180d → ~2027-03-15. On 2026-10-01 ≈165 days left. **T: verify and correct the reminder.**

## CEO Report (2026-10-01 13:51 UTC)

- **0 CONFIG CHANGES.** All recent fixes in monitor windows (SHORT_RSI_HARD_FLOOR=25 2h old, RSI_MIN=40, V5/accel-300- kills).
- **BTC LONG continuum-osc+ OPEN** — first trade after hotset recovery. Pipeline healthy.
- **ATR_SL fix VERIFIED:** 3 hits/7d. pump-chain- filters VERIFIED: RSI_MIN=40 + HIGH_BLOCK blocking correctly.
- **DELEGATED:** signal_analyst (NEUTRAL signal — #1 gap, re-delegated), bug_hunter (disk safe analysis + wasp/better-coder fixes).
- **MONITOR:** BTC trade outcome, SKIP_HARD logs, hard_max_loss aging, doji at 20T, NEUTRAL signal 48h, disk.



