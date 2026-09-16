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
