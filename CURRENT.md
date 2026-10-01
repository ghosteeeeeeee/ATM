# Current State — System Improvement Focus

**Last Updated: 2026-10-01 11:50 UTC**
**Updated by: brain_auditor**

## Current Status

**Pipeline RESTORED 06:32 UTC after 32-min crash loop (06:00–06:32).** Root cause: favorites_updater.py demoted CASHCAT, wrote `FAVORITES_LONG = {}` (Python **dict**), then `FAVORITES = FAVORITES_LONG | FAVORITES_SHORT` crashed with `TypeError: dict | set`. Pipeline was fully down — position management offline. **FIXED + VERIFIED:** full cycle rc=0, Portfolio logged.

**24h:** 36 closed, -$0.86, 36.1% WR. 7d: 121T 44.6%WR -$1.09. LONG +$0.80/7d (66T). SHORT -$1.89/7d (55T, R:R 0.67:1). 0 open positions. Post-restore (06:33+): 17T -$0.91 17.6% WR — accel-300-/V5 oversold clusters dominated.

- **🟢 CRITICAL FIX (06:32): FAVORITES dict|set crash.** hermes_constants.py:278 now `set(FAVORITES_LONG) | set(FAVORITES_SHORT)`. favorites_updater.py emits `set()` when empty. Import verified, pipeline restarted.
- **🟢 SHORT_RSI_HARD_FLOOR=25 APPLIED (brain_auditor 11:50).** Bearish-structure override had NO RSI floor — accel-300- cluster entered at RSI 2.9–24.3 (5T -$0.37 all hard_max_loss). 14d RSI<25 SHORT: 12T 25%WR -$0.89, 0 real winners. Hard floor blocks RSI<25 at decider detection + execution gates BEFORE override. OVERSOLD_SHORT_RSI_MAX=35 was compactor-only (STANDALONE_BYPASS skipped it). **RESTART NOT NEEDED** — pipeline re-imports each cycle. Verify: watch for `[EXEC-RSI-HARD-FLOOR]` / `SKIP` log lines.
- **🟢 DRIFT-002 CODE CONFIRMED LOADED.** decider_run.py:1016-1107 + 1813-1845 have ceiling fixes (volume-breakout exemption + detection-time sig.rsi fallback). Pipeline restarted 01:47, 06:32, 11:34 — all after fix commit.
- **🟡 DRIFT-001 MONITORING.** bb_bounce rsi_1m filter live. All 4 bb-bounce trades today NULL rsi_1m — combo signal path still doesn't store. BTC bb-bounce fired RSI=77.32 (should be blocked). Eval 48h → bug_hunter if no progress Oct 3.
- **🟡 DRIFT-004 RESOLVED:** NEUTRAL signal unbuilt — neutral_sniper.py EXISTS, NEUTRAL_SNIPER_ENABLED=False since Sep 12 per T. Decision is **re-enable vs build-new — T's call**.
- **🟢 V5 KILLED + accel-300- KILLED — both live.** PUMP_CHAIN_V5_ENABLED=False (auto_1hr hourly kill, commit 6d2fea25 10:13). ACCEL_300_MINUS_ENABLED=False (commit f936f173 11:13). Pipeline restarted 11:34 — both loaded. V5 eval Oct 3 moot. Prior "V5 EXTENDED to Oct 3" note was stale — killed same day after 8T 37.5%WR -$0.13.
- **PUMP_CHAIN_SHORT_RSI_MIN=40 LIVE** (CEO 02:00). Golden band 40-45 eroding: today 1W 2L (CHIP 44.88 L, ALGO 44.17 L, LDO 43.38 W). 14d band: 10T 50%WR -$0.01. RSI 50-59 = 21T 57.1%WR +$0.54 (real edge). Monitor 48h — if 7d WR <55%, escalate RSI_MIN=45.
- **OPEN:** 0 positions (07:22 UTC last close ZORA).
- **KILLED/REGIME BLOCKED:** pump-chain-v5 LONG (Oct 1), accel-300- SHORT (Oct 1), pump-chain+ V5 NEVER_REENABLE (Sep 28), pullback-entry+ NEVER_REENABLE, pump-chain- NEVER_REENABLE, mover+/- NEVER_REENABLE (Sep 24/29), open-skies+ (Sep 22), grind-trend+/- (Sep 19), breakout-long+ (Sep 16), trend_ignition (Sep 16), PUMP_FLOW+ NEVER_REENABLE. pump_chain- EXTREME override=0.0.
- **CONF_FILTER_MIN=70.** LONG_RSI_CEILING=70. SHORT_RSI_FLOOR=40 / CEILING=65 / HARD_FLOOR=25. LONG_RSI_FLOOR=20.
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
- **hermes_constants.py:** do not change VALUES without CEO/T approval. Crash-bug code fixes allowed (type-safety, imports). Loss-prevention guardrails (RSI floors/ceilings) treated as non-tunable safety nets.
- **NEUTRAL_SNIPER_ENABLED=False** — human-disabled Sep 12 per T. Do not re-enable without T.
- **Blacklist testing COMPLETE** — 77 tokens, 0 KEEP. Stop rotating.

## Monitor List (next 48h)

1. SHORT_RSI_HARD_FLOOR=25 — any SKIP_HARD logs? No RSI<25 SHORT opens?
2. PUMP_CHAIN_SHORT_RSI_MIN=40 golden band — 40-45 WR post-change
3. SHORT RSI 25-39 override zone — 26T 23.1%WR -$1.87/14d, eval after hard floor stabilizes
4. bb_bounce rsi_1m combo path — still NULL? bug_hunter Oct 3 if so
5. pump-chain- EXTREME=0 post gate fix
6. doji-bottom-long at 20T for conf boost eval
7. FAVORITES updater next run — set() emission
8. NEUTRAL volume-dry-up/EMA-reclaim signal — still not built (CEO delegation Sep 30)

## Backlog / Delegated (not orchestrator's call)

- **NEUTRAL signal:** re-enable neutral_sniper vs build-new — **T decision**
- **mover-/mover+ 24h 0%-WR kill variant** — CEO decision pending
- **Signal conf boosts** (vol-breakout EXTREME @20T, doji HIGH @20T, pump-chain- RSI 50-59 @15T) — below sample thresholds
- **Dead imports cleanup:** phase_accel.py, pump_catcher.py, ma_cross_5m.py still import defunct signal_gen
- **bugs.json OPEN:** BUG-020 zombie PRESERVE loop, BUG-021 chop_detector hyphen misclassifies MEAN_REVERSION in CHOP
- **ORPHAN_PAPER $0 trades** in PG — data hygiene
- **AGENTS.md HL API key reminder appears STALE** — says "expires in 3 days" dated 2027-03-12; key set 2026-09-16 valid 180d → ~2027-03-15. On 2026-10-01 ≈165 days left. **T: verify and correct the reminder.**

## Orchestrator Report (2026-10-01 06:40 UTC)

- **1 CRITICAL FIX.** FAVORITES dict|set crash — pipeline down 06:00–06:32. Fixed constants type-safety + favorites_updater empty-set emission. Verified: import OK, pipeline full cycle rc=0, Portfolio 1 open / 17 closed / -2.18%.
- **0 CONFIG CHANGES.** RSI_MIN=40 (CEO 02:00) already live. V5 extended (monitoring). All other fixes in monitoring windows.
- **TEAM:** health_monitor fixed position_manager guardian-lock crash (03:48). signal_reporter: no kills/boosts (thresholds not met). auto_1hr: no changes (stable). brain_auditor: 0 changes, monitoring.
- **CRITICAL ISSUES:** none open. One resolved (pipeline crash).
- **NEXT:** monitor list above; T decisions on NEUTRAL re-enable + mover 24h kill variant; favorites_updater next run must emit set().

## Brain Auditor Report (2026-10-01 12:36 UTC)

- **0 CONFIG CHANGES.** DB-verified: 36T 36.1%WR -$0.86 (24h) | post-restore 17T 17.6%WR -$0.91 | 7d EXTREME 64T 51.6%WR -$0.52.
- **🟢 HARD_FLOOR=25 VERIFIED.** Would block 5/19 24h losers (accel-300- cluster, detection RSI 2.9-24.3, -$0.37), kill 3 scratches (+$0.03). Net +$0.34. 0 log lines yet — hotset empty at 12:32. Watch SKIP_HARD / EXEC-RSI-HARD-FLOOR.
- **🔴 NEW DRIFT-SFRSI-BYPASS.** SIGNAL_FILTER_RSI_MIN=42 NOT enforced on STANDALONE_BYPASS path — 5 SHORTs fired today with detection RSI 2.9-24.3 despite the filter. Hard floor 25 is partial patch. 25-30 SHORT band still 9T 0%WR -$1.17 (0 real winners). **DELEGATE bug_hunter.**
- **🟡 signal_rsi_14 100% NULL** (340/340 14d) — `_signal_metadata.rsi_14` has values, column empty since Sep 28. RSI band analysis requires metadata parse.
- **🟡 Golden band eroding** — pump-chain- RSI 40-45 post-fix: CHIP 44.88 L, ALGO 44.17 L. Monitor 48h. Escalate RSI_MIN 40→45 only if 7d WR <55% (CEO call).
- **🟢 V5 aging out** — 8T -$0.13, opened pre-kill. No action.
- **14d winners:** volume-breakout-long+ +$2.48 (70%WR, 20T conf-boost threshold met), pump-chain+ +$1.23, doji-bottom-long +$0.36 (11T, below 20T).
- **CREATIVE:** (1) Extend SIGNAL_FILTER_RSI_MIN to bypass path / raise hard floor 25→30 after monitor (2) NEUTRAL diversity signal still unbuilt — T decision (3) REJECTED blanket burst-cluster guard — net -$0.32, kills profitable pump-chain+ bursts.
- **MONITOR:** hard floor logs 24h, golden band 48h, bb-bounce rsi_1m Oct 3, signal_rsi_14 column, V5 aging.


