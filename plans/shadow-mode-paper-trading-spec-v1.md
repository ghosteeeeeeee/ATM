# Shadow-Mode Paper Trading System — Spec v1

**Date:** 2026-10-20
**Author:** Hermes (CEO agent)
**Status:** DRAFT — pending own-conclusions validation
**Approver:** T (user) + CEO
**Priority:** CRITICAL — highest-leverage investment per CEO verdict

---

## 1. Executive Summary

The Hermes Trading System detects ~850 signals/day but executes only ~20 (2.3%). The other 98% expire without any outcome data. We don't know if gated signals would have won or lost, which exit engine works best for which signal, or which gates are blocking winners.

**This spec defines a shadow-mode paper trading system that:**
1. Processes EVERY signal fire as a simulated live trade
2. Sets TP/SL according to the exit engine that would manage it
3. Collects all context data (regime, volatility, trend, RSI, etc.)
4. Runs virtual A/B tests on exit engines
5. Answers gate justification questions ("would this blocked trade have won?")
6. Costs nothing — no money at stake, pure data collection

**Expected impact:** ~1000 shadow outcomes/day vs ~20 live trades/day = ~50× data. Within 7 days: gate justification numbers and exit-engine rankings per signal class.

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     SIGNAL DETECTION                            │
│  signals_runner → signals DB (850/day)                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     SHADOW RECORD (new)                         │
│  • Snapshot ALL signals (not just EXPIRED/SKIPPED)             │
│  • Capture full context: regime, vol, RSI, MACD, ATR, etc.     │
│  • Store: signal_id, token, direction, source, confidence,     │
│    created_at, context JSON                                    │
│  • Output: brain/shadow_trades.db (own file, freeze-safe)      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     SHADOW CLOSE (new)                          │
│  For each signal >4.5h old:                                    │
│  1. Load 1m candles from entry_ts forward                      │
│  2. Simulate EACH exit engine independently:                   │
│     • ATR SL/TP (initial stop)                                 │
│     • PM Trail (activate +0.40%, distance 0.20%)              │
│     • Hard Max Loss (CUT_LOSER_PNL=-4.00% acct, HML ATR mult) │
│     • Profit Monster Trail                                     │
│     • Stale exit (max hold time)                               │
│     • RR Engine (R:R-based)                                    │
│  3. Record: which exit fired first, PnL, hold time, MFE/MAE   │
│  4. Store: exit_engine, exit_price, pnl_pct, hold_minutes,     │
│    mfe_pct, mae_pct, closed_at                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     SHADOW REPORT (new)                         │
│  • Gate justification: "Gate X blocked 100, 45 would have won" │
│  • Exit engine A/B: "Trailing works best for pump-chain"       │
│  • Signal quality: "bb-squeeze 70% WR in EXTREME, 30% in NORMAL"│
│  • Regime analysis: "LONG signals work in trend, fail in chop" │
│  • Output: stdout + brain/shadow_trades.db queries             │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Data Schema

### 3.1 Shadow Trades Table (`brain/shadow_trades.db`)

```sql
CREATE TABLE IF NOT EXISTS shadow_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Signal identification
    signal_id INTEGER UNIQUE,           -- FK to signals_hermes_runtime.db
    token TEXT NOT NULL,
    direction TEXT NOT NULL,            -- LONG / SHORT
    signal_type TEXT NOT NULL,          -- e.g. 'pump_chain', 'bb_bounce_v2_long'
    source TEXT NOT NULL,               -- e.g. 'pump-chain+', 'bb-squeeze+'
    confidence REAL NOT NULL,
    
    -- Timing
    created_at TEXT NOT NULL,           -- signal fire time (ISO)
    recorded_at TEXT NOT NULL,          -- shadow record time (ISO)
    closed INTEGER DEFAULT 0,           -- 0=pending, 1=closed
    closed_at TEXT,                     -- shadow close time (ISO)
    
    -- Context (captured at signal fire)
    context JSON,                       -- full context snapshot (see 3.2)
    
    -- Gate information
    decision TEXT,                      -- EXPIRED, SKIPPED, PENDING, FAILED, EXECUTED
    decision_reason TEXT,               -- e.g. 'compaction_stale_10min', 'RSI hard floor'
    gate_blocked INTEGER DEFAULT 0,     -- 1 if blocked by a gate, 0 if passed
    gate_name TEXT,                     -- which gate blocked it (if any)
    
    -- Exit engine simulation results (one per engine)
    exit_atr_json JSON,                 -- ATR SL/TP simulation result
    exit_pm_trail_json JSON,            -- PM Trail simulation result
    exit_hard_max_json JSON,            -- Hard Max Loss simulation result
    exit_profit_monster_json JSON,      -- Profit Monster Trail result
    exit_stale_json JSON,               -- Stale exit result
    exit_rr_engine_json JSON,           -- RR Engine result
    
    -- Best exit (first to fire)
    best_exit_engine TEXT,              -- which engine fired first
    best_exit_price REAL,               -- exit price
    best_exit_pnl_pct REAL,             -- PnL % (direction-signed)
    best_exit_hold_minutes REAL,        -- hold time in minutes
    best_exit_reason TEXT,              -- e.g. 'atr_sl_hit', 'trail_sl'
    
    -- Forward returns (for comparison)
    fwd_30m REAL,                       -- +30m forward return %
    fwd_1h REAL,                        -- +1h forward return %
    fwd_4h REAL,                        -- +4h forward return %
    excess_30m REAL,                    -- market-neutral excess @30m
    excess_1h REAL,                     -- market-neutral excess @1h
    excess_4h REAL,                     -- market-neutral excess @4h
    mfe_4h REAL,                        -- max favorable excursion @4h
    mae_4h REAL,                        -- max adverse excursion @4h
    mfe_pct REAL,                       -- MFE % (from best exit sim)
    mae_pct REAL,                       -- MAE % (from best exit sim)
    
    -- Metadata
    created_at_db TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_shadow_token ON shadow_trades(token);
CREATE INDEX IF NOT EXISTS idx_shadow_direction ON shadow_trades(direction);
CREATE INDEX IF NOT EXISTS idx_shadow_signal_type ON shadow_trades(signal_type);
CREATE INDEX IF NOT EXISTS idx_shadow_source ON shadow_trades(source);
CREATE INDEX IF NOT EXISTS idx_shadow_created ON shadow_trades(created_at);
CREATE INDEX IF NOT EXISTS idx_shadow_closed ON shadow_trades(closed);
CREATE INDEX IF NOT EXISTS idx_shadow_gate ON shadow_trades(gate_blocked, gate_name);
CREATE INDEX IF NOT EXISTS idx_shadow_best_exit ON shadow_trades(best_exit_engine);
```

### 3.2 Context JSON Schema

Captured at signal fire time, stored as JSON:

```json
{
  "vol_regime": "EXTREME",           // FLAT / NORMAL / HIGH / EXTREME
  "atr_pct": 1.53,                   // current ATR %
  "regime_1m": "LONG_BIAS",          // 1m market bias
  "regime_4h": "LONG_BIAS",          // 4h market bias
  "btc_regime_4h": "LONG_BIAS",      // BTC 4h regime
  "btc_atr_pct": 0.64,               // BTC ATR %
  "btc_ema300_position": "ABOVE",    // ABOVE / BELOW / AT
  "btc_linreg": "LEAN_BULL",         // LEAN_BULL / BULL / NEUTRAL / LEAN_BEAR / BEAR
  "rsi_14": 65.2,                    // signal RSI
  "macd_hist": 0.0023,               // MACD histogram
  "macd_value": 0.0045,              // MACD value
  "macd_signal": 0.0022,             // MACD signal line
  "z_score": 2.1,                    // z-score
  "z_score_tier": "HIGH",            // LOW / MED / HIGH
  "momentum_state": "ACCELERATING",  // DECELERATING / STABLE / ACCELERATING
  "bb_width": 0.0073,                // Bollinger Band width
  "volume_ratio": 1.8,               // volume / avg volume
  "price_vs_ema300_pct": 2.5,        // price vs EMA300 %
  "chop_score": 15,                  // chop detector score (0-100)
  "tide_state": "RISING",            // FALLING / FLAT / RISING
  "market_phase": "trend_building",  // market phase from phase gate
  "leverage": 5,                     // leverage that would be used
  "sl_pct": 1.5,                     // initial SL % (from ATR)
  "tp_pct": 3.0,                     // initial TP % (from ATR)
  "rr_ratio": 2.0,                   // risk:reward ratio
  "atr_period": 14,                  // ATR period used
  "candle_ts_at_fire": 1792517000,   // timestamp of candle at fire
  "price_at_fire": 0.0593            // price at fire
}
```

### 3.3 Exit Engine Simulation JSON Schema

Each `exit_*_json` column stores:

```json
{
  "engine": "atr_sl_tp",
  "fired": true,                     // did this engine fire?
  "exit_type": "sl_hit",            // sl_hit / tp_hit / trail_sl / trail_tp / stale / hard_max / no_exit
  "exit_price": 0.0587,             // exit price
  "exit_ts": 1792518500,            // exit timestamp
  "hold_minutes": 25.0,             // hold time
  "pnl_pct": -1.01,                 // PnL % (direction-signed)
  "mfe_pct": 0.85,                  // max favorable excursion during hold
  "mae_pct": -1.20,                 // max adverse excursion during hold
  "sl_price": 0.0584,               // initial SL price
  "tp_price": 0.0611,               // initial TP price
  "trail_activated": false,         // did trail activate?
  "trail_activate_price": null,     // price when trail activated
  "trail_exit_price": null,         // price when trail exited
  "notes": "SL hit at 25min"        // any notes
}
```

---

## 4. Exit Engine Simulation Logic

### 4.1 ATR SL/TP (Initial Stop)

**Constants:**
- `CUT_LOSER_PNL = -4.00` (account %)
- `HML_VOL_ATR_MULT = 0.5`
- `ATR_PERIOD = 14`

**Logic:**
```
entry_price = candle_open_at_signal_ts
sl_distance_pct = atr_pct * SL_MULTIPLIER  # from get_sl_multiplier_v2()
sl_price = entry_price * (1 - sl_distance_pct/100)  # for LONG
tp_distance_pct = atr_pct * TP_MULTIPLIER
tp_price = entry_price * (1 + tp_distance_pct/100)  # for LONG

For each 1m candle after entry:
    if candle_low <= sl_price:  # LONG
        exit at sl_price, reason='atr_sl_hit'
        break
    if candle_high >= tp_price:  # LONG
        exit at tp_price, reason='atr_tp_hit'
        break
```

### 4.2 PM Trail (Profit Monster Trail)

**Constants:**
- `PM_TRAIL_ACTIVATE_PCT = 0.004` (0.40%)
- `PM_TRAIL_DISTANCE_PCT = 0.002` (0.20%)

**Logic:**
```
entry_price = candle_open_at_signal_ts
trail_active = False
peak_price = entry_price

For each 1m candle after entry:
    # Update peak
    if direction == 'LONG':
        peak_price = max(peak_price, candle_high)
    else:
        peak_price = min(peak_price, candle_low)
    
    # Check activation
    current_pnl_pct = (candle_close / entry_price - 1) * 100  # for LONG
    if current_pnl_pct >= PM_TRAIL_ACTIVATE_PCT * 100:
        trail_active = True
    
    # Check trail exit
    if trail_active:
        if direction == 'LONG':
            trail_price = peak_price * (1 - PM_TRAIL_DISTANCE_PCT)
            if candle_low <= trail_price:
                exit at trail_price, reason='trail_sl'
                break
        else:
            trail_price = peak_price * (1 + PM_TRAIL_DISTANCE_PCT)
            if candle_high >= trail_price:
                exit at trail_price, reason='trail_sl'
                break
```

### 4.3 Hard Max Loss (HML)

**Constants:**
- `CUT_LOSER_PNL = -4.00` (account %)
- `HML_VOL_ATR_MULT = 0.5`

**Logic:**
```
entry_price = candle_open_at_signal_ts
# HML price threshold = max(account_threshold/leverage, ATR-based_threshold)
account_threshold_pct = CUT_LOSER_PNL / leverage  # e.g. -4.00/5 = -0.80% price
atr_threshold_pct = -atr_pct * HML_VOL_ATR_MULT   # e.g. -1.5% * 0.5 = -0.75%
hml_threshold_pct = max(account_threshold_pct, atr_threshold_pct)  # less negative
hml_price = entry_price * (1 + hml_threshold_pct/100)  # for LONG

For each 1m candle after entry:
    if candle_low <= hml_price:  # LONG
        exit at hml_price, reason='hard_max_loss'
        break
```

### 4.4 Profit Monster Trail (Full)

Same as PM Trail but with additional logic:
- Bypasses certain signals (`PROFIT_MONSTER_BYPASS_SIGNALS`)
- Has different activation/distance for different signal types

### 4.5 Stale Exit

**Constants:**
- `MAX_HOLD_MINUTES = 240` (4 hours, configurable)

**Logic:**
```
entry_ts = signal_created_at
exit_ts = entry_ts + MAX_HOLD_MINUTES * 60
exit_price = candle_close_at_exit_ts
reason = 'stale_exit'
```

### 4.6 RR Engine

**Constants:**
- `RR_ENGINE_CONF_HARD_BLOCK_RR = 0.55`
- `RR_ENGINE_CONF_HARD_BLOCK_RR_CONFIRMED = 0.35`

**Logic:**
```
entry_price = candle_open_at_signal_ts
rr_ratio = tp_distance_pct / sl_distance_pct

if rr_ratio < RR_ENGINE_CONF_HARD_BLOCK_RR:
    # Would have been blocked by RR engine
    return {'fired': False, 'notes': f'R:R {rr_ratio} < 0.55 hard block'}

# Simulate ATR SL/TP with RR engine adjustments
# (RR engine adjusts SL/TP based on S/R levels, ATR, etc.)
```

---

## 5. Implementation Plan

### Phase 1: Extend `expiry_shadow.py` (2-3 hours)

**Goal:** Add exit engine simulation to existing shadow infrastructure.

**Changes:**
1. **Extend `record()` function:**
   - Record ALL signals (not just EXPIRED/SKIPPED)
   - Capture full context JSON (regime, vol, RSI, MACD, ATR, etc.)
   - Store gate information (which gate blocked it)

2. **Extend `close_events()` function:**
   - Add exit engine simulation (6 engines)
   - Store results in `exit_*_json` columns
   - Determine `best_exit_engine` (first to fire)

3. **Add `report_v2()` function:**
   - Gate justification analysis
   - Exit engine A/B comparison
   - Signal quality rankings
   - Regime-specific analysis

### Phase 2: Context Enrichment (1 hour)

**Goal:** Capture full context at signal fire time.

**Changes:**
1. Import `volatility_gate_v2`, `rsi_utils`, `chop_detector`, etc.
2. At record time, compute and store:
   - Volatility regime (from ATR)
   - Market bias (1m, 4h)
   - BTC context (regime, ATR, EMA300, linreg)
   - RSI, MACD, z-score, momentum
   - BB width, volume ratio
   - Chop score, tide state, market phase

### Phase 3: A/B Testing Framework (1 hour)

**Goal:** Compare exit engines on the same signals.

**Changes:**
1. For each signal, simulate ALL exit engines
2. Record which engine fired first
3. Compare PnL across engines
4. Aggregate by signal type, regime, direction

### Phase 4: Reporting & Analysis (1 hour)

**Goal:** Answer the questions T asked.

**Reports:**
1. **Gate Justification:** "Gate X blocked 100 trades, 45 would have won (45% WR)"
2. **Exit Engine A/B:** "Trailing stop works best for pump-chain (70% WR), ATR works best for bb-bounce (65% WR)"
3. **Signal Quality:** "bb-squeeze 70% WR in EXTREME, 30% in NORMAL → trade only in EXTREME"
4. **Regime Analysis:** "LONG signals work in trend (65% WR), fail in chop (35% WR)"

---

## 6. Edge Cases & Error Handling

### 6.1 Missing Candles
- If no candles for token: close as `unclosed_no_candles`, not a loss
- If insufficient forward data: close as `unclosed_insufficient_data`

### 6.2 Signal Already Executed
- If signal was actually traded (EXECUTED), still record shadow trade
- Mark `gate_blocked = 0`, `gate_name = 'PASSED'`
- Compare shadow PnL vs actual PnL for validation

### 6.3 Data Corruption
- Use `INSERT OR IGNORE` to avoid duplicates
- Validate JSON before storing
- Use atomic writes for DB operations
- Add `created_at_db` and `updated_at` for audit trail

### 6.4 Performance
- Batch processing: record every 30min, close every 1h
- Cache candles in memory (per token)
- Use indexes for common queries
- Limit to 1000 signals per batch to avoid memory issues

### 6.5 Timezone Handling
- All timestamps in UTC (ISO format)
- Use `calendar.timegm()` for timestamp conversion
- Store both signal time and record time

---

## 7. Testing Strategy

### 7.1 Unit Tests
- Test each exit engine simulation independently
- Test context capture with known values
- Test edge cases (missing candles, insufficient data)

### 7.2 Integration Tests
- Test record → close → report pipeline
- Test with real signals from signals DB
- Validate against actual live trades

### 7.3 Validation
- Compare shadow PnL vs actual PnL for EXECUTED signals
- Should match within 5% (accounting for slippage/fees)
- If mismatch: investigate and fix

---

## 8. Rollout Plan

### Day 1: Build & Test
- Implement Phase 1-4
- Run unit tests
- Run integration tests with real data

### Day 2: Shadow Deployment
- Deploy to production (freeze-safe, zero live impact)
- Run record + close cycles
- Monitor for errors

### Day 3-7: Data Collection
- Collect ~1000 shadow outcomes/day
- Run daily reports
- Identify patterns and insights

### Day 8: Analysis & Action
- Analyze collected data
- Identify gates to loosen
- Identify exit engines to optimize
- Present findings to T and CEO

---

## 9. Success Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Shadow outcomes/day | ~1000 | `SELECT COUNT(*) FROM shadow_trades WHERE created_at > datetime('now', '-1 day')` |
| Data completeness | >95% | `SELECT 100.0 * SUM(CASE WHEN best_exit_engine IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*) FROM shadow_trades WHERE closed=1` |
| Gate justification | Answered | Report shows "Gate X blocked N, M would have won" |
| Exit engine A/B | Complete | Report shows engine rankings per signal type |
| Validation accuracy | >95% | Shadow PnL matches actual PnL for EXECUTED signals |

---

## 10. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Data corruption | High | Use INSERT OR IGNORE, validate JSON, atomic writes |
| Performance issues | Medium | Batch processing, caching, index optimization |
| Incorrect exit simulation | High | Validate against live trades, unit tests |
| Memory issues | Medium | Limit batch size, cache eviction |
| Timezone bugs | Low | Use UTC everywhere, calendar.timegm() |

---

## 11. Dependencies

- `expiry_shadow.py` (existing, to be extended)
- `volatility_gate_v2.py` (for regime classification)
- `rsi_utils.py` (for RSI calculation)
- `chop_detector.py` (for chop score)
- `candles.db` (for price data)
- `signals_hermes_runtime.db` (for signal data)
- `brain/shadow_trades.db` (new, output)

---

## 12. Open Questions

1. **Should we simulate fees?** Live trades pay fees (~0.04% per trade). Shadow trades don't. This affects PnL comparison.
   - **Decision:** Include fees in simulation for accuracy.

2. **Should we simulate slippage?** Live trades have slippage (~0.1-0.5%). Shadow trades don't.
   - **Decision:** Include conservative slippage estimate (0.1%).

3. **How long to keep shadow data?** 
   - **Decision:** 90 days, then archive.

4. **Should we create a dashboard?**
   - **Decision:** No dashboard in v1. DB + queries are enough.

---

## 13. Approval

- [ ] T (user) — approve spec
- [ ] CEO — approve spec
- [ ] Bug Hunter — validate implementation
- [ ] Own Conclusions — independent validation

---

## Appendix A: Existing Infrastructure

| Component | Status | Location |
|-----------|--------|----------|
| `expiry_shadow.py` | Exists, to be extended | `scripts/expiry_shadow.py` |
| `t5_shadow.py` | Exists | `scripts/t5_shadow.py` |
| `gate_shadow.py` | Exists | `scripts/gate_shadow.py` |
| Cell stats | Exists (697 cells) | `brain/cell_stats.db` |
| `volatility_gate_v2.py` | Exists | `scripts/volatility_gate_v2.py` |
| `rsi_utils.py` | Exists | `scripts/rsi_utils.py` |
| `chop_detector.py` | Exists | `scripts/chop_detector.py` |

## Appendix B: Exit Engine Constants

| Constant | Value | Location |
|----------|-------|----------|
| `CUT_LOSER_PNL` | -4.00% | `hermes_constants.py:717` |
| `HML_VOL_ATR_MULT` | 0.5 | `hermes_constants.py:718` |
| `PM_TRAIL_ACTIVATE_PCT` | 0.004 (0.40%) | `hermes_constants.py:1659` |
| `PM_TRAIL_DISTANCE_PCT` | 0.002 (0.20%) | `hermes_constants.py:1660` |
| `TRAILING_ACTIVATION_PCT` | 0.0040 (0.40%) | `hermes_constants.py:727` |
| `ATR_PERIOD` | 14 | `volatility_gate_v2.py` |

## Appendix C: Gate Names (for `gate_name` column)

| Gate | Description |
|------|-------------|
| `CONFLUENCE-GATE-BLOCK` | Single-source not in STANDALONE_BYPASS |
| `SHORT-RSI-HARD-FLOOR` | SHORT RSI < 35 |
| `PUMP-CHAIN-SHORT-HIGH` | pump-chain- SHORT in HIGH vol |
| `VOL-GATE-BYPASS` | Vol gate override=0.0 |
| `CONTINUUM-BLOCK` | BTC bearish structure blocks LONG |
| `SHORT-REGIME-GATE` | SHORT in NORMAL/HIGH, conf < 75 |
| `LONG-NEUTRAL-CHOP` | LONG in NEUTRAL, BTC flat |
| `RR-ENGINE` | R:R < 0.55 hard block |
| `LONG-RSI-CEILING` | LONG RSI > 75 |
| `PUMP-CHAIN-RSI-MAX` | pump-chain+ LONG RSI >= 70 |
