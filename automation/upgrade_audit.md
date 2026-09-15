# Upgrade Audit Trail

## Plan: profitability-fix-plan.md
- **Date scanned:** 2026-09-15
- **Core request:** 8 config tweaks to improve PnL by ~$4.21/7d (exit fixes, signal kills, regime gating, token management, speed filter, time block)
- **Difficulty:** Level 1 (config tweaks)
- **Value:** HIGH
- **Status:** IMPLEMENTED (5/8 fixes applied)
- **Reason:** Highest ROI plan — all changes are single-line constants in hermes_constants.py. Data-backed with two independent audits.

## Plan: 2026-09-11_volatility-gate-tuning.md
- **Date scanned:** 2026-09-15
- **Core request:** Add ATR ratio + BTC trend boost to volatility_gate_v2.py for direction-aligned expansion trades
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** PARTIALLY IMPLEMENTED
- **Reason:** VOL_PHASE_MULTS already blocks many family/regime combos. ATR ratio extension is new code (~30 lines).

## Plan: 2026-09-11_volatility-regime-adaptive-signals.md
- **Date scanned:** 2026-09-15
- **Core request:** Adapt signal multipliers to volatility regime (expansion/compression) using ATR ratio
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** PARTIALLY IMPLEMENTED
- **Reason:** volatility_gate_v2.py already has regime-based multipliers. ATR ratio layer is new (~33 lines).

## Plan: oversold-bounce-signal.md
- **Date scanned:** 2026-09-15
- **Core request:** Mean-reversion LONG signal at RSI < 20 extremes
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** IMPLEMENTED
- **Reason:** OVERSOLD_BOUNCE_ENABLED=True in hermes_constants.py (line 3470). Signal exists in scripts/signals/.

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
- **Date scanned:** 2026-09-15
- **Core request:** ATR trailing exit for pump-chain signals (3.0x ATR trail + momentum exit)
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** PENDING
- **Reason:** Pump-chain currently uses rr_engine exit. New exit logic ~120 lines in position_manager.py. Based on single FIL case study.

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
- **Reason:** BTC_CHOP_GATE (Layer 1) exists. BTC_TIMING_GUARD (partial Layer 3) exists but LOG_ONLY. Stale filter, RSI guard, continuum boost need wiring.

## Plan: 2026-09-11_btc-timing-guard.md
- **Date scanned:** 2026-09-15
- **Core request:** Per-signal-type BTC momentum thresholds to prevent chasing
- **Difficulty:** Level 1
- **Value:** HIGH
- **Status:** PARTIALLY IMPLEMENTED
- **Reason:** Constants exist (BTC_TIMING_GUARD_*) but LOG_ONLY=True. Needs implementation in signal_compactor.py or LOG_ONLY=False.

## Plan: ema300-rejection-signal-spec.md
- **Date scanned:** 2026-09-15
- **Core request:** EMA300 breakthrough signal on 15m timeframe (69-80% WR SHORT)
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** PENDING
- **Reason:** New signal module (~150 lines). Strong backtest results but not yet built.

## Plan: 2026-09-11_chop-regime-signal-gating.md
- **Date scanned:** 2026-09-15
- **Core request:** Hard BTC momentum gate + gate STANDALONE_BYPASS in chop
- **Difficulty:** Level 1
- **Value:** HIGH
- **Status:** PARTIALLY IMPLEMENTED
- **Reason:** BTC_CHOP_GATE exists. STANDALONE_BYPASS gate (Layer B) needs verification in signal_compactor.py.
