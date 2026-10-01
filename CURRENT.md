# Current State — System Improvement Focus

**Last Updated: 2026-10-01 18:45 UTC**
**Updated by: daily-orchestrator**

## Current Status

**PIPELINE HEALTHY.** 1 open: BTC LONG continuum-osc+ (entry $84229, opened 13:49, IN_PROFIT). Hotset empty — signal starvation continues (NEUTRAL signal unbuilt, #1 gap). Pipeline live, compactor cycling every minute, SHORT-CONTINUUM filter firing correctly.

**24h (PG live):** 31T 35.5%WR -$1.11. **7d:** 112T 47.3%WR -$0.09. LONG 7d +$1.15 (63T). SHORT 7d -$1.24 (49T). Regime NEUTRAL / BTC score 92-98 z=POS (strongly bullish — SHORTs correctly blocked by new filter).

- **🟢 SHORT-CONTINUUM FILTER LIVE + VERIFIED** (upgrade_implementer 18:15). Blocks SHORT when BTC state_score>10 AND zscore_tier != STRONG_NEG. Logs show constant correct blocks: WLD/ALT/TRX/BTC/PUMP SHORT blocked (score=92-98, z=POS). Plans/continuum-filter-analysis.md implemented. LONG side untouched.
- **🟢 upgrade_implementer 4 changes VERIFIED LIVE:** OSCILLATOR_MULT_ENABLED=True, DOJI_BOTTOM_ENABLED=True (flag decoupled from DOJI_TOP), SHORT continuum filter, REGIME_SIGNALS EXTREME cleanup (pump-chain- removed from both volatility_gate files). py_compile OK. Pipeline + compactor restarted.
- **🟢 bugs.json RECONCILED.** 4 bugs verified fixed in code but stale status: BUG-001 (MACD histogram — runtime test confirmed hist=line-sig), BUG-011 (PG conn leak — try/finally present), BUG-020 (PRESERVE zombie — 30min age guard + entry_origin_ts as created_at live), BUG-021 (chop hyphen — p_normalized + overrides added, 14/14 tests pass). Marked FIXED with verification notes. 11 bugs remain OPEN (coin_tracker/backfill cluster — not trading-path).
- **🟡 SIGNAL STARVATION PERSISTS.** Hotset empty 18:32-18:41. 40+ signals generated/cycle, 0-5 pass compaction (confidence<50 or safety filters). NEUTRAL diversity signal (volume-dry-up/EMA-reclaim) still unbuilt — delegated signal_analyst Sep 30, re-delegated 13:51. momentum signals (r2-trend) blocked by BTC-CHOP-GATE when BTC flat, then expire.
- **🟡 24h losers root-caused + fixed:** pump-chain- SHORT 9T 22.2% WR -$0.63 (all EXTREME — vol gate 0.0 + EXTREME allowlist removal 18:15). accel-300- SHORT 8T 37.5% -$0.34 (killed 10:50). pump-chain-v5 LONG 6T -$0.17 (killed 10:18). Legacy aging out.
- **🟡 doji-bottom-long** still below 20T conf-boost threshold. **bb-bounce-v3-long+** 2T 0%WR -$0.12 — below 3T kill threshold, monitor.
- **🟡 DISK 87%** (97G/118G, 15G free). DB growth: coin_tracker 3.3G, candles 2.3G, mtf_macd_tuner 1.3G. **Needs CEO prune call** — do NOT VACUUM active DBs during trading. Delegated bug_hunter for safe analysis.
- **🟡 Failing non-trading services:** hermes-wasp (LOCK-WAIT loop, timer still fires 30min), hermes-better-coder (ModuleNotFoundError). Both disabled, code-owner fixes delegated. hermes-atr-sl-updater.timer is ghost (unit renamed -DEFUNCT; ATR managed locally by guardian via DB — not a gap).
- **🟡 pump_chain_v5_short.py** generates without generation-time RSI/vol (rsi:0 in file). 342 signals/day, 0 executed — execution gates in signal_compactor hold (RSI_MIN=40, HIGH_BLOCK, SHORT-CONTINUUM). Signal spam, not money-losing. Fix later if spam worsens.
- **🟡 bollinger_squeeze research PASS** (70.8%WR, 805T historical) but BOLLINGER_SQUEEZE_ENABLED=False since Aug 1 (0%WR on 4 live trades). Existing bollinger_squeeze.py already implements pattern; _candidates/ are stubs. Re-enable = CEO call.
- **OPEN:** 1 position (BTC LONG continuum-osc+).
- **KILLED/REGIME BLOCKED:** pump-chain-v5 LONG (Oct 1 10:18), accel-300- SHORT (Oct 1 10:50), pump-chain+ V5 NEVER_REENABLE (Sep 28), pullback-entry+ NEVER_REENABLE, pump-chain- NEVER_REENABLE, mover+/- NEVER_REENABLE (Sep 24/29), open-skies+ (Sep 22), grind-trend+/- (Sep 19), breakout-long+ (Sep 16), trend_ignition (Sep 16), PUMP_FLOW+ NEVER_REENABLE.
- **CONF_FILTER_MIN=70.** LONG_RSI_CEILING=70. SHORT_RSI_FLOOR=40 / CEILING=65 / HARD_FLOOR=25. PUMP_CHAIN_SHORT_RSI_MIN=40. LONG_RSI_FLOOR=20.
- **PM_TRAIL:** ACTIVATE 0.40%, DISTANCE 0.20%. Protected (DO NOT CHANGE).
- **ATR_SL:** MIN 1.3%, MAX 2.0%. EXTREME: MIN 1.5%, 1.2x. VERIFIED — 3 hits/7d, atr_sl_hit 0% today.
- **BTC_CHOP_GATE:** blocks momentum signals when BTC 30m flat. Correct behavior but starves NEUTRAL diversity — NEUTRAL signal is the fix.
- **SHORT_CONTINUUM_FILTER_ENABLED=True.** SCORE_MAX=10. ALLOW_Z=('STRONG_NEG',).
- **Disk:** 87% (15G free).
- **LONG_NEUTRAL_BLOCK_ENABLED=True.**
- **FINAL_CONFIDENCE:** by design not in _signal_metadata — hotset JSON only.

## Standing Decisions (do not re-litigate)

- **SIGNAL KILL POLICY:** regime-block via volatility_gate_v2 (0.0x) if signal wins in ANY regime. Blanket-kill ONLY if loses in ALL regimes. FAMILY_MAP in market_phase_gate.py.
- **No time-of-day blanket blocks.** Entry quality filters only.
- **hermes_constants.py:** do not change VALUES without CEO/T approval. Crash-bug code fixes allowed (type-safety, imports). Loss-prevention guardrails (RSI floors/ceilings) treated as non-tunable safety nets.
- **NEUTRAL_SNIPER_ENABLED=False** — human-disabled Sep 12 per T. Do not re-enable without T.
- **Blacklist testing COMPLETE** — 77 tokens, 0 KEEP. Stop rotating.
- **0 config changes when fixes are in monitor windows** — stacking changes prevents measurement. Active windows: SHORT-CONTINUUM (18:15), SHORT_RSI_HARD_FLOOR (11:50), pump-chain- RSI_MIN, V5/accel kills aging out.
- **signal_version.py missing** — CEO 22:00 Sep 30: stop flagging, JSON store exists.

## Monitor List (next 48h)

1. BTC LONG continuum-osc+ — outcome, SL/TP/trail behavior
2. SHORT-CONTINUUM filter — confirm no legitimate STRONG_NEG SHORTs blocked; BTC score trend
3. SHORT_RSI_HARD_FLOOR=25 — SKIP_HARD logs, RSI<25 SHORT opens
4. hard_max_loss exits — should decline as accel-300-/V5 age out
5. doji-bottom-long — 20T conf-boost threshold
6. bb-bounce-v3-long+ — 3T kill threshold
7. NEUTRAL volume-dry-up/EMA-reclaim signal — still unbuilt? signal_analyst status
8. Disk growth rate — CEO prune call pending
9. pump_chain_v5_short spam — 342/day, fix if worsens
10. hermes-wasp LOCK-WAIT + better-coder ModuleNotFoundError — code-owner fixes

## Backlog / Delegated (not orchestrator's call)

- **NEUTRAL signal:** re-enable neutral_sniper vs build-new — **T decision** (build-new delegated to signal_analyst)
- **bollinger_squeeze re-enable** — research PASS but live 0%WR historically — CEO call
- **mover-/mover+ 24h 0%-WR kill variant** — CEO decision pending
- **Signal conf boosts** (vol-breakout EXTREME @20T, doji HIGH @20T, pump-chain- RSI 50-59 @15T) — below sample thresholds
- **Dead code cleanup:** orphan signal files with signal_gen imports (phase_accel, pump_catcher, ma_cross_5m, etc.) — NOT in active 73-entry registry, dead files, backlog
- **bugs.json OPEN (11):** coin_tracker/backfill cluster (BUG-002..010, 012, 022) — not trading-path
- **ORPHAN_PAPER $0 trades** in PG — data hygiene
- **AGENTS.md HL API key reminder appears STALE** — says "expires in 3 days" dated 2027-03-12; key set 2026-09-16 valid 180d → ~2027-03-15. On 2026-10-01 ≈165 days left. **T: verify and correct the reminder.**

## Orchestrator Report (2026-10-01 18:45 UTC)

- **0 CONFIG CHANGES.** Multiple fixes in monitor windows (SHORT-CONTINUUM 30min old, SHORT_RSI_HARD_FLOOR 7h, pump-chain- RSI_MIN, V5/accel kills aging).
- **VERIFIED** upgrade_implementer's 4 changes live + SHORT-CONTINUUM filter firing correctly (BTC score 92-98 z=POS, SHORTs blocked as designed).
- **RECONCILED bugs.json** — 4 stale FIXED statuses corrected with runtime/static verification (BUG-001/011/020/021).
- **24h:** 31T 35.5%WR -$1.11. Losers root-caused (pump-chain- EXTREME, accel-300-, V5 — all already fixed/killed).
- **DELEGATED (unchanged):** signal_analyst (NEUTRAL signal), bug_hunter (disk safe analysis + wasp/better-coder), CEO (disk prune, bollinger_squeeze re-enable, HL key reminder).
- **MONITOR:** BTC trade outcome, SHORT-CONTINUUM correctness, SKIP_HARD logs, hard_max_loss aging, doji at 20T, NEUTRAL signal 48h, disk.
