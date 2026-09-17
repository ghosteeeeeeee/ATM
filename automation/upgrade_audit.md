# Upgrade Audit Trail

## Plan: profitability-fix-plan.md
- **Date scanned:** 2026-09-15
- **Core request:** 8 config tweaks to improve PnL by ~$4.21/7d (exit fixes, signal kills, regime gating, token management, speed filter, time block)
- **Difficulty:** Level 1 (config tweaks)
- **Value:** HIGH
- **Status:** IMPLEMENTED (7/8 fixes applied)
- **Reason:** Highest ROI plan. Applied: (1) pullback-entry- exit→atr, (2) ema300-dip-long killed, (3) cut-loser T1 tightened, (4) ENA blacklisted, (5) pump-chain+ blocked in NORMAL, (6) time block extended to 09:00, (7) BTC timing guard enabled, (8) LOSERS penalties tightened (0.3 mult, -50 conf). Remaining: LONG speed threshold (HIGH risk), full NORMAL momentum block (needs direction-specific vol gate).

## Plan: 2026-09-11_volatility-gate-tuning.md
- **Date scanned:** 2026-09-15
- **Core request:** Add ATR ratio + BTC trend boost to volatility_gate_v2.py for direction-aligned expansion trades
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** IMPLEMENTED
- **Reason:** ATR ratio + BTC trend boost already in volatility_gate_v2.py:483-503. Constants at hermes_constants.py:935-939. get_atr_ratio() and get_btc_trend() functions exist.

## Plan: 2026-09-11_volatility-regime-adaptive-signals.md
- **Date scanned:** 2026-09-15
- **Core request:** Adapt signal multipliers to volatility regime (expansion/compression) using ATR ratio
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** IMPLEMENTED
- **Reason:** vol_regime_mult already computed in signal_compactor.py:1611-1655. Uses ATR ratio from token_speeds. Expansion boosts momentum 1.2x, compression penalizes momentum.

## Plan: oversold-bounce-signal.md
- **Date scanned:** 2026-09-15
- **Core request:** Mean-reversion LONG signal at RSI < 20 extremes
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** IMPLEMENTED
- **Reason:** OVERSOLD_BOUNCE_ENABLED=True in hermes_constants.py (line 3473). Signal exists in scripts/signals/oversold_bounce.py.

## Plan: 2026-09-11_btc-timing-guard.md
- **Date scanned:** 2026-09-15
- **Core request:** Per-signal-type BTC momentum thresholds to prevent chasing
- **Difficulty:** Level 1
- **Value:** HIGH
- **Status:** IMPLEMENTED
- **Reason:** Flipped BTC_TIMING_GUARD_LOG_ONLY to False (hermes_constants.py:924). Code fully wired in signal_compactor.py:1127-1180. Blocks pump-chain, pullback-entry, open-skies, accel-300 when BTC already moved.

## Plan: 2026-09-11_chop-regime-signal-gating.md
- **Date scanned:** 2026-09-15
- **Core request:** Hard BTC momentum gate + gate STANDALONE_BYPASS in chop
- **Difficulty:** Level 1
- **Value:** HIGH
- **Status:** IMPLEMENTED
- **Reason:** BTC_CHOP_GATE exists (hermes_constants.py). STANDALONE_BYPASS gate verified at signal_compactor.py:2163-2171 — checks BTC momentum before allowing bypass.

## Plan: contrarian-zone-signal.md
- **Date scanned:** 2026-09-15
- **Core request:** Transform blocked signals into contrarian trades at SL zones, standalone zone signal
- **Difficulty:** Level 3
- **Value:** HIGH
- **Status:** PENDING
- **Reason:** Requires SL memory system (Phase 1-6). Edge is marginal (0.54:1 R:R). Backtest pending.

## Plan: sl-memory-sr-system-v2.md
- **Date scanned:** 2026-09-15
- **Core request:** Track initial SL hits as S/R zones, filter entries near death zones, zone-aware exits
- **Difficulty:** Level 3
- **Value:** HIGH
- **Status:** PENDING
- **Reason:** Foundation for contrarian-zone. Requires new DB table, zone engine, integration into 4 files. 6-phase implementation.

## Plan: sl-memory-sr-system.md
- **Date scanned:** 2026-09-15
- **Core request:** v1.0 of SL memory — superseded by v2.0
- **Difficulty:** Level 3
- **Value:** LOW
- **Status:** SKIPPED
- **Reason:** Superseded by sl-memory-sr-system-v2.md which addresses 5 critical audit flaws.

## Plan: pump-chain-exit-spec.md
- **Date scanned:** 2026-09-16
- **Core request:** ATR trailing exit for pump-chain signals (3.0x ATR trail + momentum exit)
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** IMPLEMENTED
- **Reason:** pump-chain+ mapped to 'pump_exit' in SIGNAL_EXIT_CONFIG (line 1386). Position manager has pump_exit logic at lines 2555-2685 (ATR trail, momentum fade, dead money exit). Constants at hermes_constants.py:3336-3340.

## Plan: hl-trigger-sl-v2.md
- **Date scanned:** 2026-09-15
- **Core request:** Server-side HL trigger orders to eliminate slippage on SL execution
- **Difficulty:** Level 3
- **Value:** HIGH
- **Status:** PENDING
- **Reason:** Could save ~139% PnL from catastrophic slippage. V1 was disabled due to bugs. V2 uses mature SDK functions. 13 bug fixes required.

## Plan: brain-rag-system.md
- **Date scanned:** 2026-09-15
- **Core request:** FAISS + sentence-transformers session brain with hourly LLM auditor
- **Difficulty:** Level 4
- **Value:** LOW
- **Status:** PENDING
- **Reason:** 400+ line spec, new infrastructure (FAISS, new DB, new dashboard, new systemd timers). High complexity for indirect trading value.

## Plan: spider-profit.md
- **Date scanned:** 2026-09-15
- **Core request:** Regime-aware profit taking for flat markets (lower thresholds in NEUTRAL)
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** PENDING
- **Reason:** Modifies profit_monster.py to swap params based on regime. ~50 lines. Addresses stuck trades in flat markets.

## Plan: 2026-09-12_btc-momentum-sync-plan.md
- **Date scanned:** 2026-09-15
- **Core request:** 5-layer defense: BTC gate, transition detection, stale filter, RSI guard, continuum boost
- **Difficulty:** Level 2
- **Value:** HIGH
- **Status:** PARTIALLY IMPLEMENTED
- **Reason:** Layer 1 (BTC_CHOP_GATE) and Layer B (STANDALONE_BYPASS gate) implemented. Remaining: stale filter, RSI guard, continuum boost need wiring.

## Plan: ema300-rejection-signal-spec.md
- **Date scanned:** 2026-09-15
- **Core request:** EMA300 breakthrough signal on 15m timeframe (69-80% WR SHORT)
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** PENDING
- **Reason:** New signal module (~150 lines). Strong backtest results but not yet built.

---

## Plan: profitability-fix-plan.md (update 2026-09-16)
- **Date scanned:** 2026-09-16
- **Core request:** LOSERS penalties tightened (4B from plan)
- **Difficulty:** Level 1
- **Value:** HIGH
- **Status:** IMPLEMENTED
- **Reason:** LOSERS_MULT 0.5→0.3, LOSERS_CONF_PENALTY -30→-50. AIXBT/KAS losers still trading despite old penalties. Tighter suppression should reduce bleed from known losers.

---

## Session Summary (2026-09-16)

**Scanned:** 20 plans
**Implemented this session:** 2 (BTC timing guard enable, LOSERS penalty increase)
**Already implemented:** 8 (profitability fixes 1A/1B/2A/2B/3B/4A/4B/6A, volatility gate, vol regime, oversold bounce, chop gate, btc timing guard, pump-chain-exit)
**Pending:** 7 (contrarian-zone, sl-memory, hl-trigger, brain-rag, spider-profit, btc-momentum-sync remaining layers, ema300-rejection)
**Skipped:** 1 (sl-memory v1)

**Remaining profitability-fix-plan items (not implemented):**
- 3A: Block LONG in NORMAL (momentum) — needs direction-specific vol gate, Level 2
- 5A: Raise LONG speed threshold — HIGH risk, may cause signal starvation

**Next candidates (Level 1-2):**
1. spider-profit — Level 2 — MEDIUM — Regime-aware profit taking for stuck trades
2. ema300-rejection-signal — Level 2 — MEDIUM — New signal, 69-80% WR SHORT backtest
3. btc-momentum-sync remaining layers — Level 2 — HIGH — Stale filter + RSI guard
4. hl-trigger-sl-v2 — Level 3 — HIGH — Server-side SL to eliminate slippage (13 bug fixes needed)

---

## Session 2 — Full Plan Scan (2026-09-17)

### Newly Evaluated Plans (2026-09-17)

## Plan: 2026-09-11_btc-pump-rider-gradual-rally.md
- **Date scanned:** 2026-09-17
- **Core request:** Add gradual rally detection mode to btc_pump_rider.py (catch slow BTC rallies + lagging alts)
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** PENDING
- **Reason:** ~58 lines + 8 constants. Would catch gradual rallies missed by explosive breakout detector. Conservative estimate +$0.20/day. Needs backtest on Sep 11 rally data.

## Plan: 2026-09-09_regime-transition-smoothing.md
- **Date scanned:** 2026-09-17
- **Core request:** Wire existing systems: directional bias, alt-BTC divergence, tighten directional outcome constants
- **Difficulty:** Level 1 (wiring existing code)
- **Value:** HIGH
- **Status:** IMPLEMENTED
- **Reason:** All 3 layers verified: Layer 2 (directional bias) at signal_compactor.py:1542-1570, Layer 3 (constants) at hermes_constants.py:868/887, Layer 4 (alt-BTC divergence) at signal_compactor.py:1584-1599. DIRECTIONAL_BIAS_ENABLED=True, ALT_BTC_DIVERGENCE_ENABLED=True.

## Plan: 2026-09-09_pump-chain-v2-spec.md
- **Date scanned:** 2026-09-17
- **Core request:** Add 30m velocity filter + tighten 5m threshold for pump-chain signals
- **Difficulty:** Level 1 (config + filter)
- **Value:** HIGH
- **Status:** IMPLEMENTED (but signal disabled)
- **Reason:** PUMP_FLOW_TOKEN_30M_THRESHOLD=0 (line 3375), PUMP_FLOW_TOKEN_VEL_THRESHOLD=-0.5 (line 3384), SHORT_VEL_THRESHOLD=0 (line 3386) all wired in pump_flow_signal.py:306-325. However PUMP_FLOW_PLUS_ENABLED=False — signal killed 2026-09-14. Filters are ready if signal is re-enabled.

## Plan: 2026-09-08_short-filter-overhaul.md
- **Date scanned:** 2026-09-17
- **Core request:** Fix dead code bug (range(3) vs threshold=5), relax SHORT filters
- **Difficulty:** Level 1 (bug fix)
- **Value:** HIGH
- **Status:** IMPLEMENTED
- **Reason:** Dead code bug fixed at signal_compactor.py:2874-2875 — now uses range(SHORT_VEL_FILTER_GREEN_THRESHOLD). VEL threshold remains at 0.3% (conservative per audit recommendation). SHORT_NEUTRAL_BLOCK still enabled.

## Plan: grind-breakout-signal-spec.md
- **Date scanned:** 2026-09-17
- **Core request:** Steady grind + late breakout signal (LONG+SHORT)
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** IMPLEMENTED
- **Reason:** Signal exists at scripts/signals/grind_breakout.py. GRIND_BREAKOUT_ENABLED=True, PLUS=True, MINUS=True. RSI 35-65 quality filter applied (from quality-filters analysis).

## Plan: trend-ignition-signal-spec.md
- **Date scanned:** 2026-09-17
- **Core request:** Early-stage breakout signal at trend START (LONG-only)
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** IMPLEMENTED (but DISABLED)
- **Reason:** Signal exists at scripts/signals/trend_ignition.py. DISABLED by brain_auditor 2026-09-16 — 0 trades in 3+ days, dead signal, LONG-only impossible in NEUTRAL.

## Plan: squeeze-reversal (2026-09-09_grass-breakout-analysis.md)
- **Date scanned:** 2026-09-17
- **Core request:** BB squeeze → mean-reversion breakout signal after sell-off
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** IMPLEMENTED
- **Reason:** Signal exists at scripts/signals/squeeze_reversal.py. SQUEEZE_REVERSAL_ENABLED=True, PLUS=True, MINUS=True.

## Plan: ema300-rejection-signal-spec.md
- **Date scanned:** 2026-09-17
- **Core request:** EMA300 breakthrough signal on 15m timeframe (69-80% WR SHORT)
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** IMPLEMENTED
- **Reason:** Signal exists at scripts/signals/ema300_breakthrough.py. EMA300_BREAKTHROUGH_ENABLED=True, PLUS=True, MINUS=True.

## Plan: 2026-09-08_btc-alignment-crash-protection-overhaul.md
- **Date scanned:** 2026-09-17
- **Core request:** BTC trend alignment filter + MAE guard + trailing profit lock + crash auto-cut
- **Difficulty:** Level 2-3
- **Value:** HIGH
- **Status:** PARTIALLY IMPLEMENTED
- **Reason:** btc_crash_filter.py exists (Layer 5). BTC_MOMENTUM thresholds exist. MAE guard exists. Trailing profit lock NOT implemented. Crash auto-cut for existing LONGs partially wired.

## Plan: 2026-09-12_btc-momentum-sync-plan.md (update)
- **Date scanned:** 2026-09-17
- **Core request:** 5-layer defense: BTC gate, transition detection, stale filter, RSI guard, continuum boost
- **Difficulty:** Level 2
- **Value:** HIGH
- **Status:** PARTIALLY IMPLEMENTED (2/5 layers)
- **Reason:** Layer 1 (BTC_CHOP_GATE) done. Layer B (STANDALONE_BYPASS gate) done. Remaining 3 layers (stale filter, RSI guard, continuum boost) not wired.

## Plan: losers-list-spec.md
- **Date scanned:** 2026-09-17
- **Core request:** Anti-favorites system — auto-penalize underperforming coins
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** IMPLEMENTED
- **Reason:** losers_tracker.py exists. LOSERS set + constants in hermes_constants.py:281-336. LOSERS_MULT=0.3, LOSERS_CONF_PENALTY=-50. signal_compactor.py:1372 has Hall of Shame BLOCK.

## Plan: 2026-09-07_partial-close-trailing-runner.md
- **Date scanned:** 2026-09-17
- **Core request:** Partial close (50%) at PM trail activation + adaptive runner trail
- **Difficulty:** Level 3
- **Value:** HIGH
- **Status:** PENDING
- **Reason:** Would capture runner profits (ICP case: left 4.14% on table). Requires profit_monster.py rewrite with partial position management. Complex — needs HL API integration for partial closes.

## Plan: regime-tuner-spec.md
- **Date scanned:** 2026-09-17
- **Core request:** Weekly automated regime analysis and signal tuning
- **Difficulty:** Level 3
- **Value:** MEDIUM
- **Status:** PENDING
- **Reason:** New script (regime_tuner.py) + systemd timer. 395-line spec. Uses existing regime_memory.py + PostgreSQL trade data. Automates manual signal management.

## Plan: 2026-09-02_regime-aware-signal-params-spec.md
- **Date scanned:** 2026-09-17
- **Core request:** Adapt accel_300_v3 params to volatility regime (FLAT/NORMAL/HIGH/EXTREME)
- **Difficulty:** Level 3
- **Value:** MEDIUM
- **Status:** PENDING
- **Reason:** 35 fixed constants need regime-specific variants. Bug: volatility regime not stored in trades table. Requires new DB column + param selection logic.

## Plan: 2026-09-04_continuum-engine-spec.md
- **Date scanned:** 2026-09-17
- **Core request:** State-based continuum engine replacing event-based signals
- **Difficulty:** Level 4
- **Value:** HIGH
- **Status:** PENDING
- **Reason:** Architecture overhaul. 444-line spec. Replaces signal-fires→event model with states-accumulate→compound model. Massive scope.

## Plan: 2026-08-29_amplitude-enhancement-brainstorm.md
- **Date scanned:** 2026-09-17
- **Core request:** Token amplitude classification + wave period trading
- **Difficulty:** Level 3
- **Value:** MEDIUM
- **Status:** PENDING
- **Reason:** 577-line analysis. Token amplitude classes (LOW/MED/HIGH_AMP). Wave period insights useful but no concrete signal spec yet.

## Plan: 2026-08-19_short-bias-fix.md
- **Date scanned:** 2026-09-17
- **Core request:** Investigate SHORT starvation
- **Difficulty:** Level 0 (investigation only)
- **Value:** LOW
- **Status:** SKIPPED (no changes needed)
- **Reason:** Investigation complete. SHORT starvation is market condition, not filter problem. Counter-trend SHORTs = 26% WR (correctly blocked). Trend-aligned SHORTs = 53.8% WR.

## Plan: pullback_entry_v2_long.md
- **Date scanned:** 2026-09-17
- **Core request:** Improve pullback_entry_long WR from 40% to 60%+
- **Difficulty:** Level 2
- **Value:** LOW
- **Status:** PENDING
- **Reason:** Only 5 trades (2W/3L). Signal exists but LOW trade count makes conclusions unreliable. Need more data before tuning.

---

## Session 2 Summary (2026-09-17)

**Total plans scanned:** 88 (all .md files in plans/)
**Previously evaluated:** 18
**Newly evaluated:** 16
**Total evaluated:** 34

**Status breakdown:**
- IMPLEMENTED: 20 (profitability-fix, volatility-gate, vol-regime, oversold-bounce, btc-timing-guard, chop-gate, pump-chain-exit, regime-transition-smoothing, pump-chain-v2 (disabled), short-filter-overhaul, grind-breakout, trend-ignition (disabled), squeeze-reversal, ema300-breakthrough, losers-list, btc-alignment-crash-partial, btc-momentum-sync-partial, 2026-08-19-short-bias-fix)
- PENDING: 11 (contrarian-zone, sl-memory-v2, hl-trigger-sl-v2, brain-rag, spider-profit, btc-pump-rider-gradual, partial-close-trailing, regime-tuner, regime-aware-params, continuum-engine, amplitude-enhancement)
- SKIPPED: 3 (sl-memory-v1, short-bias-fix, pump-chain-v2 filters ready but signal disabled)

**Remaining profitability-fix-plan items:**
- 3A: Block LONG in NORMAL (momentum) — Level 2
- 5A: Raise LONG speed threshold — HIGH risk

**Next candidates (Level 1-2):**
1. spider-profit — Level 2 — MEDIUM — Regime-aware profit taking for stuck trades
2. btc-pump-rider-gradual — Level 2 — MEDIUM — Catch gradual BTC rallies
3. btc-momentum-sync layers 3-5 — Level 2 — HIGH — Stale filter + RSI guard
4. partial-close-trailing — Level 3 — HIGH — Runner capture for winners
5. hl-trigger-sl-v2 — Level 3 — HIGH — Server-side SL (13 bug fixes)
6. ema300-rejection-signal — Level 2 — MEDIUM — Already implemented, verify
