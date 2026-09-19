# Upgrade Audit Trail

**Created:** 2026-09-19
**Scanned:** 20 most recent plans

---

## Plan: ride-it-exit-spec.md
- **Date scanned:** 2026-09-19 01:00
- **Core request:** 2-phase ride-it exit system with volume spike override for momentum trades
- **Difficulty:** Level 2
- **Value:** HIGH
- **Status:** IMPLEMENTED
- **Reason:** ride_it_exit.py exists, constants added to hermes_constants.py, integrated into position_manager.py

## Plan: continuum-ma-signal-spec.md
- **Date scanned:** 2026-09-19 01:00
- **Core request:** New signal using MA-smoothed continuum score for crossover detection
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** PENDING
- **Reason:** No signal script exists. Requires continuum.db data + new signal file. Deferred — lower priority than gradual rally.

## Plan: btc-oscillator-30d-plan.md
- **Date scanned:** 2026-09-19 01:00
- **Core request:** BTC oscillator correlation analysis for trade filtering
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** PENDING
- **Reason:** Plan recommends WAIT AND MONITOR (only 14d data, need 30d). Premature to implement.

## Plan: btc-oscillator-correlation-plan.md
- **Date scanned:** 2026-09-19 01:00
- **Core request:** Block LONG when BTC bearish, boost SHORT when BTC bullish
- **Difficulty:** Level 2
- **Value:** HIGH
- **Status:** PARTIALLY IMPLEMENTED
- **Reason:** BTC chop gate (BTC_CHOP_GATE) and BTC timing guard already exist. BTC momentum gate partially covers this via signal_compactor.py.

## Plan: profitability-fix-plan.md
- **Date scanned:** 2026-09-19 01:00
- **Core request:** 8 fixes to improve PnL by ~$4.21/7d
- **Difficulty:** Level 1-2
- **Value:** HIGH
- **Status:** MOSTLY IMPLEMENTED
- **Reason:** 6/8 fixes done: rr_engine for pullback-entry- (✅), kill ema300-dip-long (✅), blacklist ENA (✅), tighten cut-loser T1 (✅), extend time block (✅), increase LOSERS penalties (✅). Remaining: block LONG in NORMAL (partially via VOL_PHASE_MULTS), raise LONG speed threshold (not done).

## Plan: 2026-09-11_volatility-gate-tuning.md
- **Date scanned:** 2026-09-19 01:00
- **Core request:** ATR ratio + BTC trend boost for direction-aligned expansion trades
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** IMPLEMENTED
- **Reason:** get_atr_ratio(), get_btc_trend(), and expansion boost all exist in volatility_gate_v2.py (lines 326-504).

## Plan: 2026-09-11_volatility-regime-adaptive-signals.md
- **Date scanned:** 2026-09-19 01:00
- **Core request:** Signal weighting by volatility regime (expansion/compression/normal)
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** IMPLEMENTED
- **Reason:** VOL_PHASE_MULTS matrix in volatility_gate_v2.py covers all regime+phase combinations with signal family multipliers.

## Plan: oversold-bounce-signal.md
- **Date scanned:** 2026-09-19 01:00
- **Core request:** Mean reversion LONG signal at extreme oversold (RSI < 25)
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** IMPLEMENTED
- **Reason:** oversold_bounce.py exists, registered in signals/__init__.py, constants in hermes_constants.py.

## Plan: contrarian-zone-signal.md
- **Date scanned:** 2026-09-19 01:00
- **Core request:** Contrarian signal at SL memory zones (flip direction when approaching death zone)
- **Difficulty:** Level 3
- **Value:** MEDIUM
- **Status:** PENDING
- **Reason:** sl_zones.py exists but contrarian zone transformation logic NOT wired into signal_compactor.py. Depends on Phase 1-6 of SL Memory system.

## Plan: sl-memory-sr-system-v2.md
- **Date scanned:** 2026-09-19 01:00
- **Core request:** SL memory as support/resistance with entry filtering, zone-aware exits
- **Difficulty:** Level 3
- **Value:** HIGH
- **Status:** PARTIALLY IMPLEMENTED
- **Reason:** sl_zones.py and sl_zones_api.py exist (zone aggregation engine). Entry filter, exit logic, and position sizing NOT wired into signal_compactor.py or position_manager.py.

## Plan: sl-memory-sr-system.md
- **Date scanned:** 2026-09-19 01:00
- **Core request:** Original SL memory spec (v1.0, superseded by v2.0)
- **Difficulty:** Level 3
- **Value:** LOW
- **Status:** SUPERSEDED
- **Reason:** Replaced by sl-memory-sr-system-v2.md

## Plan: pump-chain-exit-spec.md
- **Date scanned:** 2026-09-19 01:00
- **Core request:** ATR trailing exit for pump-chain signals (bypass PM trail and RR engine)
- **Difficulty:** Level 2
- **Value:** HIGH
- **Status:** IMPLEMENTED
- **Reason:** pump_exit constants exist in hermes_constants.py, position_manager.py handles pump_exit exit type.

## Plan: hl-trigger-sl-v2.md
- **Date scanned:** 2026-09-19 01:00
- **Core request:** HL trigger orders for server-side SL/TP (eliminate slippage)
- **Difficulty:** Level 3
- **Value:** HIGH
- **Status:** PENDING
- **Reason:** V1 was disabled (2026-05-15). V2 spec exists with bug-hunter audit. Requires re-enabling with fixes. Critical for reducing catastrophic losses.

## Plan: brain-rag-system.md
- **Date scanned:** 2026-09-19 01:00
- **Core request:** Session brain (FAISS+SQLite) + hourly brain auditor + dashboard
- **Difficulty:** Level 4
- **Value:** MEDIUM
- **Status:** PARTIALLY IMPLEMENTED
- **Reason:** session_brain.py and brain_api.py exist. Dashboard (brain.html) and hourly auditor NOT implemented.

## Plan: spider-profit.md
- **Date scanned:** 2026-09-19 01:00
- **Core request:** Regime-aware profit taking for NEUTRAL markets
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** IMPLEMENTED
- **Reason:** SPIDER_* constants exist in hermes_constants.py, integrated into profit_monster.py.

## Plan: 2026-09-12_btc-momentum-sync-plan.md
- **Date scanned:** 2026-09-19 01:00
- **Core request:** 5-layer defense: BTC momentum gate, transition detection, stale filter, RSI guard, continuum boost
- **Difficulty:** Level 3
- **Value:** HIGH
- **Status:** PARTIALLY IMPLEMENTED
- **Reason:** BTC momentum gate (via btc_chop_gate + btc_timing_guard) partially implemented. Transition detection, stale filter tightening, and continuum boost NOT implemented.

## Plan: 2026-09-11_btc-timing-guard.md
- **Date scanned:** 2026-09-19 01:00
- **Core request:** Per-signal-type BTC momentum thresholds
- **Difficulty:** Level 2
- **Value:** HIGH
- **Status:** IMPLEMENTED
- **Reason:** BTC_TIMING_GUARD constants exist in hermes_constants.py, check exists in signal_compactor.py.

## Plan: 2026-09-11_btc-pump-rider-gradual-rally.md
- **Date scanned:** 2026-09-19 01:00
- **Core request:** Detect gradual BTC rallies (not just explosive breakouts) and buy lagging alts
- **Difficulty:** Level 2
- **Value:** HIGH
- **Status:** IMPLEMENTED
- **Reason:** detect_btc_gradual_rally() + find_lagging_alts_gradual() both exist in btc_pump_rider.py (lines 182-297). Constants in hermes_constants.py. Integrated in run() (lines 462-470).

## Plan: ema300-rejection-signal-spec.md
- **Date scanned:** 2026-09-19 01:00
- **Core request:** EMA300 breakthrough signal (price crashes through EMA300 with momentum)
- **Difficulty:** Level 2
- **Value:** HIGH
- **Status:** IMPLEMENTED
- **Reason:** ema300_breakthrough.py exists, registered in signals/__init__.py, constants in hermes_constants.py.

## Plan: 2026-09-11_chop-regime-signal-gating.md
- **Date scanned:** 2026-09-19 01:00
- **Core request:** BTC chop gate + gate STANDALONE_BYPASS in flat markets
- **Difficulty:** Level 2
- **Value:** HIGH
- **Status:** IMPLEMENTED
- **Reason:** BTC_CHOP_GATE constants exist, check in signal_compactor.py. STANDALONE_BYPASS gated by BTC momentum.

---

## Summary

| Status | Count | Plans |
|--------|-------|-------|
| IMPLEMENTED | 12 | ride-it, vol-gate-tuning, vol-regime-adaptive, oversold-bounce, pump-chain-exit, spider-profit, btc-timing-guard, ema300-breakthrough, chop-gate, profitability-fix (6/8), btc-pump-rider-gradual |
| PARTIALLY IMPLEMENTED | 3 | btc-oscillator-correlation, sl-memory-v2, btc-momentum-sync, brain-rag |
| PENDING (High Value) | 2 | contrarian-zone, hl-trigger-sl-v2 |
| PENDING (Medium Value) | 2 | continuum-ma, btc-oscillator-30d |
| SUPERSEDED | 1 | sl-memory-v1 |

## Next Candidates

1. **BTC Pump Rider Gradual Rally** — Level 2 — HIGH — extends existing btc_pump_rider.py, catches gradual rallies missed by explosive breakout mode
2. **Contrarian Zone Signal** — Level 3 — MEDIUM — depends on sl_memory wiring, high complexity
3. **HL Trigger SL/TP V2** — Level 3 — HIGH — critical for reducing catastrophic losses but complex rework
