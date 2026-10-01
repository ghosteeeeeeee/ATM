# Current State — System Improvement Focus

**Last Updated: 2026-10-01 06:40 UTC**
**Updated by: daily_orchestrator**

## Current Status

**Pipeline RESTORED 06:32 UTC after 32-min crash loop (06:00–06:32).** Root cause: favorites_updater.py demoted CASHCAT, wrote `FAVORITES_LONG = {}` (Python **dict**), then `FAVORITES = FAVORITES_LONG | FAVORITES_SHORT` crashed with `TypeError: dict | set`. Pipeline was fully down — position management offline. **FIXED + VERIFIED:** full cycle rc=0, Portfolio logged, 1 open position managed.

**24h (post-restore 06:33):** 17 closed today, -2.18% PnL, 1 open. 7d: 115T 46.1%WR -$1.64 (as of 03:45). LONG +$0.16 profitable (64T, R:R 1.35:1). SHORT -$1.80 bleeding (51T, R:R 0.61:1). Near breakeven system.

- **🟢 CRITICAL FIX (06:32): FAVORITES dict|set crash.** hermes_constants.py:278 now `set(FAVORITES_LONG) | set(FAVORITES_SHORT)`. favorites_updater.py emits `set()` when empty + regex matches both forms (mirrors losers_tracker.py). Import verified, pipeline restarted, full cycle clean.
- **🟢 DRIFT-002 CODE CONFIRMED LOADED.** decider_run.py:1016-1107 + 1813-1845 have ceiling fixes (volume-breakout exemption + detection-time sig.rsi fallback). Pipeline restarted 01:47 and 06:32 — both after fix commit. brain_auditor 04:35 "DRIFT-002 OPEN" entry was STALE. Eval with trades.
- **🟡 DRIFT-001 MONITORING.** bb_bounce rsi_1m filter live (restarted 01:47). 2 post-restart bb-bounce trades both NULL rsi_1m metadata — combo signal path may not store. Eval 48h.
- **🟡 DRIFT-004 (brain_auditor 03:45): "NEUTRAL signal unbuilt" is STALE.** neutral_sniper.py EXISTS at scripts/signals/, NEUTRAL_SNIPER_ENABLED=False since Sep 12 per T. Decision is **re-enable vs build-new — T's call**. Orchestrator will not touch.
- **PUMP_CHAIN_SHORT_RSI_MIN=40 LIVE** (CEO 02:00). Verified safe: 0 winners killed 14d, golden band 40-45 passes (LDO +$0.05 RSI 43.38). Monitor 48h.
- **V5 TEST EXTENDED to Oct 3** (CEO). 3T +$0.27 closed + open. Eval Oct 3.
- **OPEN:** 1 position (JUP pump-chain-v5 LONG as of 06:12; BTC continuum-trend+ conf=99 hotset YES at 06:32 decider — watch).
- **KILLED/REGIME BLOCKED:** pump-chain+ V5 NEVER_REENABLE (Sep 28), pullback-entry+ NEVER_REENABLE, pump-chain- NEVER_REENABLE, mover+/- NEVER_REENABLE (Sep 24/29), open-skies+ (Sep 22), grind-trend+/- (Sep 19), breakout-long+ (Sep 16), trend_ignition (Sep 16), PUMP_FLOW+ NEVER_REENABLE. pump_chain- EXTREME override=0.0 (monitor 48h, 30d EXTREME was only profitable SHORT band).
- **CONF_FILTER_MIN=70.** LONG_RSI_CEILING=70. SHORT_RSI_FLOOR=40 / CEILING=65. LONG_RSI_FLOOR=20.
- **PM_TRAIL:** ACTIVATE 0.40%, DISTANCE 0.20%. Protected (DO NOT CHANGE).
- **ATR_SL:** MIN 1.3%, MAX 2.0%. EXTREME: MIN 1.5%, 1.2x. VERIFIED — 0 ATR_SL hits post-fix.
- **TIME_BLOCK:** 00-09 UTC 0.7x penalty. DEAD_HOURS disabled (Sep 30).
- **Disk:** 85% (18G free).
- **LONG_NEUTRAL_BLOCK_ENABLED=True.**
- **FINAL_CONFIDENCE:** by design not in _signal_metadata — hotset JSON only.
- **🟢 POSITION_MANAGER CRASH LOOP FIXED (health_monitor 03:48).** hl-sync-guardian.py lock now behind `if __name__ == '__main__'` (line 184). position_manager rc=0 verified repeatedly post-fix.

## Standing Decisions (do not re-litigate)

- **SIGNAL KILL POLICY:** regime-block via volatility_gate_v2 (0.0x) if signal wins in ANY regime. Blanket-kill ONLY if loses in ALL regimes. FAMILY_MAP in market_phase_gate.py.
- **No time-of-day blanket blocks.** Entry quality filters only.
- **hermes_constants.py:** do not change VALUES without CEO/T approval. Crash-bug code fixes allowed (type-safety, imports).
- **NEUTRAL_SNIPER_ENABLED=False** — human-disabled Sep 12 per T. Do not re-enable without T.
- **Blacklist testing COMPLETE** — 77 tokens, 0 KEEP. Stop rotating.

## Monitor List (next 48h)

1. PUMP_CHAIN_SHORT_RSI_MIN=40 — golden band preserved?
2. bb_bounce rsi_1m filter — metadata combo path gap?
3. pump-chain- EXTREME=0 post gate fix — 30d EXTREME was +$0.32
4. V5 eval Oct 3
5. DRIFT-002 — any RSI>ceiling LONG leaks?
6. BTC continuum-trend+ hotset entry (conf=99)
7. FAVORITES updater next run — does it write set() correctly?

## Backlog / Delegated (not orchestrator's call)

- **NEUTRAL signal:** re-enable neutral_sniper vs build-new — **T decision**
- **mover-/mover+ 24h 0%-WR kill variant** — CEO decision pending (auto_1hr flagged 7d 0% WR)
- **Signal conf boosts** (vol-breakout EXTREME @20T, doji HIGH @20T, pump-chain- golden band @15T) — below sample thresholds
- **Dead imports cleanup:** phase_accel.py, pump_catcher.py, ma_cross_5m.py still import defunct signal_gen — signals are NEVER_REENABLE/dead so no live impact. Cleanup when touching those files.
- **bugs.json OPEN:** BUG-020 zombie PRESERVE loop, BUG-021 chop_detector hyphen misclassifies MEAN_REVERSION in CHOP (11/16 wrong) — relevant to signal diversity, needs independent backtest before change
- **ORPHAN_PAPER $0 trades** in PG — data hygiene
- **AGENTS.md HL API key reminder appears STALE** — says "expires in 3 days" dated 2027-03-12; key set 2026-09-16 valid 180d → ~2027-03-15. On 2026-10-01 ≈165 days left. **T: verify and correct the reminder.**

## Orchestrator Report (2026-10-01 06:40 UTC)

- **1 CRITICAL FIX.** FAVORITES dict|set crash — pipeline down 06:00–06:32. Fixed constants type-safety + favorites_updater empty-set emission. Verified: import OK, pipeline full cycle rc=0, Portfolio 1 open / 17 closed / -2.18%.
- **0 CONFIG CHANGES.** RSI_MIN=40 (CEO 02:00) already live. V5 extended (monitoring). All other fixes in monitoring windows.
- **TEAM:** health_monitor fixed position_manager guardian-lock crash (03:48). signal_reporter: no kills/boosts (thresholds not met). auto_1hr: no changes (stable). brain_auditor: 0 changes, monitoring.
- **CRITICAL ISSUES:** none open. One resolved (pipeline crash).
- **NEXT:** monitor list above; T decisions on NEUTRAL re-enable + mover 24h kill variant; favorites_updater next run must emit set().
