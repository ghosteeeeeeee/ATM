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
    context_computed_at TEXT,           -- when context was computed (measures drift)
    closed INTEGER DEFAULT 0,           -- 0=pending, 1=closed
    closed_at TEXT,                     -- shadow close time (ISO)
    
    -- Context (captured at signal fire — pull from signals table + signal_metadata)
    context JSON,                       -- full context snapshot (see 3.2)
    leverage_used INTEGER,              -- execution leverage (from per-token registry, NOT signals.leverage)
    
    -- Gate information
    decision TEXT,                      -- EXPIRED, SKIPPED, PENDING, FAILED, EXECUTED
    decision_reason TEXT,               -- e.g. 'compaction_stale_10min', 'RSI hard floor'
    gate_blocked INTEGER DEFAULT 0,     -- 1 if blocked by a gate, 0 if passed
    gate_name TEXT,                     -- which gate blocked it (if any)
    gate_name_backfilled INTEGER DEFAULT 0,  -- 1 if gate_name was parsed from decision_reason
    
    -- Exit engine routing
    exit_config TEXT,                   -- 'atr', 'pump_exit', 'ride_it', 'rr_engine' (from _match_exit_config)
    
    -- Exit engine simulation results (one per engine)
    exit_atr_json JSON,                 -- ATR SL/TP simulation result (continuous peak-trailing)
    exit_pm_trail_json JSON,            -- PM Trail simulation result (tiered)
    exit_hard_max_json JSON,            -- Hard Max Loss simulation result
    exit_cut_loser_json JSON,           -- Cut Loser two-tier result (full closes)
    exit_speed_stale_json JSON,         -- Speed Stale exit result (fidelity gap: no speed_percentile gate)
    exit_universal_hold_json JSON,      -- Universal Max Hold result
    exit_trail_arm_timeout_json JSON,   -- Trail Arm Timeout result
    exit_rr_engine_json JSON,           -- RR Engine result (NULL in v1 — not simulated)
    
    -- First exit to fire (renamed from best_exit_engine per validation)
    first_exit_engine TEXT,             -- which engine fired first (deterministic tie-break, see §4.0)
    first_exit_price REAL,              -- exit price
    first_exit_pnl_pct REAL,            -- PnL % (direction-signed, after fees+slippage)
    first_exit_hold_minutes REAL,       -- hold time in minutes
    first_exit_reason TEXT,             -- e.g. 'atr_sl_hit', 'trail_sl'
    
    -- Fee/slippage application (per §12 decisions)
    fee_pct REAL DEFAULT 0.04,          -- fee percentage (0.04% per trade)
    slippage_pct REAL DEFAULT 0.10,     -- slippage percentage (0.10%)
    gross_pnl_pct REAL,                 -- PnL before fees/slippage
    net_pnl_pct REAL,                   -- PnL after fees/slippage
    
    -- Forward returns (for comparison)
    fwd_30m REAL,                       -- +30m forward return %
    fwd_1h REAL,                        -- +1h forward return %
    fwd_4h REAL,                        -- +4h forward return %
    excess_30m REAL,                    -- market-neutral excess @30m
    excess_1h REAL,                     -- market-neutral excess @1h
    excess_4h REAL,                     -- market-neutral excess @4h
    mfe_4h REAL,                        -- max favorable excursion @4h
    mae_4h REAL,                        -- max adverse excursion @4h
    mfe_pct REAL,                       -- MFE % (from first exit sim)
    mae_pct REAL,                       -- MAE % (from first exit sim)
    
    -- Validation join (for EXECUTED signals)
    trade_id TEXT,                      -- PostgreSQL trades.trade_id for validation
    
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
CREATE INDEX IF NOT EXISTS idx_shadow_first_exit ON shadow_trades(first_exit_engine);
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

> **IMPORTANT (own-conclusions validation 2026-10-20):** Section 4 was rewritten based on independent validation. The original spec had 3 of 6 engines factually wrong. All formulas below are verified against live code.

### 4.0 SIGNAL_EXIT_CONFIG Routing + Engine Roster (CRITICAL)

> **IMPORTANT (bug_hunter finding 7):** This is the ONE authoritative engine roster. Sections 2 and 5 must reference this table.

**Before simulating any exit engine, each signal must be routed to the correct engine family.**

The live system routes each signal to exactly one exit config via `_match_exit_config()` (`position_manager.py:55`) against `SIGNAL_EXIT_CONFIG` (`hermes_constants.py:1832`).

**⚠️ MANDATE (bug_hunter finding 4.0):** Import the REAL `_match_exit_config` from `position_manager`. Do NOT reimplement routing — the spec's simplified pseudocode misroutes versioned signals like `pump-chain-v5` (live strips `-vN` suffixes, handles `-`/`_` prefixes, and does stem matching).

```python
# CORRECT — import the real function
from position_manager import _match_exit_config
exit_config = _match_exit_config(source)  # returns 'atr' | 'pump_exit' | 'ride_it' | 'rr_engine' | None
```

#### Engine Roster (Authoritative)

| Engine | v1 Simulated? | Schema Column | Source File | Notes |
|--------|---------------|---------------|-------------|-------|
| ATR SL/TP | ✅ YES | `exit_atr_json` | `tpsl_utils.py` | Continuous peak-trailing |
| PM Trail | ✅ YES | `exit_pm_trail_json` | `profit_monster.py` | Tiered, with bypass check |
| Hard Max Loss | ✅ YES | `exit_hard_max_json` | `position_manager.py` | CUT_LOSER_PNL/leverage |
| Cut Loser | ✅ YES | `exit_cut_loser_json` | `cut_loser.py` | Two-tier full closes |
| Speed Stale | ✅ YES (info) | `exit_speed_stale_json` | `position_manager.py` | Fidelity gap: no speed_percentile gate |
| Universal Max Hold | ✅ YES | `exit_universal_hold_json` | `position_manager.py` | 480min, ride_it 24h |
| Trail Arm Timeout | ✅ YES | `exit_trail_arm_timeout_json` | `position_manager.py` | bb-squeeze 60min, pump-chain 45min |
| PM T1/T2 Tier | ❌ NO (v2) | — | `profit_monster.py` | Complex windows, full closes |
| RR Engine | ❌ NO (v2) | `exit_rr_engine_json` (NULL) | `risk_reward_engine.py` | Multi-hour sub-project |
| pump_exit | ❌ NO (v2) | — | `position_manager.py` | Route through universal stack, label exit_config |
| ride_it | ❌ NO (v2) | — | `ride_it_exit.py` | Route through universal stack, label exit_config |

**v1 scope decision (bug_hunter finding 4):** Simulate the 7 universal engines. Signals routed to `pump_exit` or `ride_it` are simulated through the universal stack (ATR + PM Trail + HML + etc.) and labeled with their `exit_config` for stratified analysis. This is an approximation — `pump_exit` and `ride_it` have different exit logic — but it provides data for 100% of signals without defining two new engine simulations.

#### Tie-Break Rule (bug_hunter finding 8)

When two engines fire in the same 1m candle, use deterministic precedence:

**Loss-side (worst first):** HML → Cut Loser Hard Stop → Cut Loser T2 → Cut Loser T1 → ATR SL → Speed Stale → Trail Arm Timeout → Universal Max Hold

**Profit-side (best first):** ATR TP → PM Trail → Speed Stale Winner

Record multi-fire engines in the engine JSONs (`fired: true` even when not first). This ensures `first_exit_engine` is deterministic across runs.

#### Leverage Sourcing (own-conclusions finding 8)

**⚠️ CRITICAL:** Do NOT use `signals.leverage` (defaults to 10, often NULL). Do NOT hardcode cap-at-5. Live 14d trades show: lev 5×191, **lev 3×125**, 10×9, 40×1 (per-token registry). Use the per-token leverage from the trade registry:

```python
# CORRECT — use per-token leverage from registry
from position_manager import get_trade_params
leverage = get_trade_params(token)['leverage']  # or query the per-token registry
# Fallback: min(signals.leverage or 5, MAX_LEVERAGE) if registry unavailable
```

---

### 4.1 ATR SL/TP (Continuous Peak-Trailing Engine)

> **CORRECTED (own-conclusions + bug_hunter):** The live engine is NOT a static initial stop. It continuously trails SL from peak. Engine ATR is **15m-primary** (via `tpsl_utils.get_fresh_atr` → atr_cache), not 1h. ATR_SL_MAX is **2.5%**, not 5.0%.

**Constants:**
- `TRAILING_DISTANCE_PCT = 1.20%` (`hermes_constants.py:728`)
- `ATR_SL_MIN_INIT = 1.5%` (`hermes_constants.py:711`)
- `ATR_SL_MIN_ACCEL = 0.30%` (`hermes_constants.py:705`)
- `ATR_SL_MAX = 2.5%` (`hermes_constants.py:696`)
- ATR(14) computed on **15m candles** (via `tpsl_utils.get_fresh_atr`), not 1h

**Logic (from `tpsl_utils.compute_atr_sl_tp`):**
```python
entry_price = candle_open_at_signal_ts
atr_pct = compute_atr_15m(token)  # ATR(14) on 15m candles (tpsl_utils.get_fresh_atr)

# Initial SL/TP
sl_distance_pct = atr_pct * get_sl_multiplier_v2(atr_pct, signal_type)
tp_distance_pct = atr_pct * get_tp_multiplier_v2(atr_pct, signal_type)
sl_price = entry_price * (1 - sl_distance_pct/100)  # for LONG
tp_price = entry_price * (1 + tp_distance_pct/100)  # for LONG

# Tracking state
peak_price = entry_price  # highest price since entry (LONG)
trail_active = False
min_sl_distance = ATR_SL_MIN_INIT  # starts at 1.5%

For each 1m candle after entry:
    # Update peak
    if direction == 'LONG':
        peak_price = max(peak_price, candle_high)
    else:
        peak_price = min(peak_price, candle_low)
    
    # Trail SL from peak (tightens only, never loosens)
    if direction == 'LONG':
        new_sl = peak_price * (1 - TRAILING_DISTANCE_PCT/100)
        sl_price = max(sl_price, new_sl)  # tighten only
        # Apply floors
        min_sl_distance = ATR_SL_MIN_ACCEL  # after first PM cycle
        max_sl = peak_price * (1 - min_sl_distance/100)
        sl_price = min(sl_price, max_sl)  # cap at floor
    else:
        new_sl = peak_price * (1 + TRAILING_DISTANCE_PCT/100)
        sl_price = min(sl_price, new_sl)  # tighten only
        min_sl_distance = ATR_SL_MIN_ACCEL
        min_sl = peak_price * (1 + min_sl_distance/100)
        sl_price = max(sl_price, min_sl)  # cap at floor
    
    # Check exits
    if direction == 'LONG':
        if candle_low <= sl_price:
            # Relabel: profitable trail exit vs initial SL
            if sl_price > entry_price:
                exit at sl_price, reason='atr_trail_hit'  # profitable
            else:
                exit at sl_price, reason='atr_sl_hit'  # loss
            break
        if candle_high >= tp_price:
            exit at tp_price, reason='atr_tp_hit'
            break
    else:
        if candle_high >= sl_price:
            if sl_price < entry_price:
                exit at sl_price, reason='atr_trail_hit'
            else:
                exit at sl_price, reason='atr_sl_hit'
            break
        if candle_low <= tp_price:
            exit at tp_price, reason='atr_tp_hit'
            break
```

**Key behaviors:**
- SL trails from peak (highest/lowest since entry)
- Trail distance = 1.20% from peak
- Tightens only (never loosens)
- INIT floor 1.5%, ACCEL floor 0.30%
- EXTREME vol widens ×1.2
- Profitable trail exits labeled `atr_trail_hit`, not `atr_sl_hit`

---

### 4.2 PM Trail (Profit Monster Trail)

> **CORRECTED (own-conclusions):** Added tiered distances, min hold, spider override, bypass signals.

**Constants:**
- `PM_TRAIL_ACTIVATE_PCT = 0.004` (0.40%)
- `PM_TRAIL_TIERS = {0.20%: <1.5%, 0.50%: 1.5-3%, 0.80%: 3-5%, 1.20%: 5%+}` (tiered by peak profit)
- `PM_TRAIL_MIN_HOLD = 2` (min post-activation candles before exit)
- `SPIDER_TRAIL_ACTIVATE_PCT = 0.003` (0.30% in NEUTRAL/spider regime)
- `PROFIT_MONSTER_BYPASS_SIGNALS` (~40 families — pump-chain, atr-spike, ai-trader, hh-hl, continuum-osc)

**Logic (from `profit_monster.py run_trail()`):**
```python
entry_price = candle_open_at_signal_ts
trail_active = False
peak_price = entry_price
activation_candle = None
bypass_check = source.rstrip('+-') in PROFIT_MONSTER_BYPASS_SIGNALS

# Spider regime override
if regime_4h == 'NEUTRAL':
    activate_pct = SPIDER_TRAIL_ACTIVATE_PCT * 100  # 0.30%
    tiers = {0.10: 1.5, 0.30: 3.0, 0.50: 5.0}  # tighter tiers
else:
    activate_pct = PM_TRAIL_ACTIVATE_PCT * 100  # 0.40%
    tiers = PM_TRAIL_TIERS  # 0.20/0.50/0.80/1.20

If bypass_check:
    # Signal bypasses PM Trail entirely
    return {'fired': False, 'notes': 'bypass signal'}

For each 1m candle after entry:
    # Update peak
    if direction == 'LONG':
        peak_price = max(peak_price, candle_high)
    else:
        peak_price = min(peak_price, candle_low)
    
    # Check activation
    current_pnl_pct = (candle_close / entry_price - 1) * 100  # for LONG
    if current_pnl_pct >= activate_pct:
        if not trail_active:
            trail_active = True
            activation_candle = current_candle_index
    
    # Check trail exit (with tiered distance and min hold)
    if trail_active:
        # Min hold check
        if current_candle_index - activation_candle < PM_TRAIL_MIN_HOLD:
            continue
        
        # Get tiered distance based on peak profit
        peak_profit_pct = (peak_price / entry_price - 1) * 100  # for LONG
        trail_distance = get_tiered_distance(peak_profit_pct, tiers)
        
        if direction == 'LONG':
            trail_price = peak_price * (1 - trail_distance/100)
            if candle_low <= trail_price:
                exit at trail_price, reason='trail_sl'
                break
        else:
            trail_price = peak_price * (1 + trail_distance/100)
            if candle_high >= trail_price:
                exit at trail_price, reason='trail_sl'
                break
```

**Key behaviors:**
- Tiered trail distance (0.20% → 1.20% based on peak profit)
- Min hold = 2 candles after activation
- Spider regime override (tighter activation and tiers)
- ~40 signal families bypass PM Trail entirely

---

### 4.3 Hard Max Loss (HML)

> **CORRECTED (own-conclusions + bug_hunter):** Formula was INVERTED. Live code uses `CUT_LOSER_PNL / leverage` unconditionally. The ATR branch is dead code after Oct-10 cap fix. **Leverage sourcing corrected:** use per-token registry, NOT cap-at-5 (live trades use lev 3×125, lev 5×191, lev 10×9).

**Constants:**
- `CUT_LOSER_PNL = -4.00` (account %)
- `MAX_LEVERAGE = 5` (fallback cap, but per-token registry is preferred)

**Logic (from `position_manager.py:3551-3587`):**
```python
entry_price = candle_open_at_signal_ts

# CRITICAL: Use per-token leverage from registry, NOT signals.leverage
# Live 14d: lev 5×191, lev 3×125, lev 10×9, lev 40×1
# signals.leverage is often NULL or defaults to 10
try:
    from position_manager import get_trade_params
    leverage = get_trade_params(token)['leverage']  # per-token registry
except:
    leverage = min(signals.leverage or 5, MAX_LEVERAGE)  # fallback: cap at 5

# HML threshold = CUT_LOSER_PNL / leverage (unconditionally)
# The ATR vol floor is dead code — account threshold always governs
hml_threshold_pct = CUT_LOSER_PNL / leverage  # e.g. -4.00/5 = -0.80% price, -4.00/3 = -1.33% price

hml_price = entry_price * (1 + hml_threshold_pct/100)  # for LONG

For each 1m candle after entry:
    if candle_low <= hml_price:  # LONG
        exit at hml_price, reason='hard_max_loss'
        break
```

**Key behaviors:**
- Threshold = `CUT_LOSER_PNL / leverage` (e.g., -4.00/5 = -0.80% price, -4.00/3 = -1.33% price)
- **Use per-token leverage from registry** — NOT signals.leverage (NULL/10), NOT cap-at-5
- ATR branch is dead code — account threshold always governs
- Only fires on losers (cannot block winners)

**Unit test (from validation):**
```python
# Verify HML formula matches live code
assert compute_hml_threshold(atr_pct=0.3, leverage=5) == -0.80  # NOT -0.15
assert compute_hml_threshold(atr_pct=1.0, leverage=5) == -0.80  # NOT -0.50
assert compute_hml_threshold(atr_pct=2.0, leverage=5) == -0.80  # NOT -1.00
```

---

### 4.4 Profit Monster T1/T2 Tier Exits (v2 — NOT SIMULATED IN V1)

> **DROPPED FROM V1 (bug_hunter finding 2):** The original spec had fabricated thresholds (PM_T1_EXIT_PCT=1.5%, PM_T2_EXIT_PCT=3.0%) and partial-exit logic (50%/25%). The real system uses windows-in-range semantics and FULL closes, not partials.

**Real behavior (for v2 reference):**
- Windows: `PM_TIER1 [0.65–2.0%]` / `PM_TIER2 [2.0–5.0%]` (`hermes_constants.py:1641–1649`)
- Full closes via `brain.py trade close`, NOT partial exits
- Has `max_close` caps, fire windows, and trail-state skipping
- No schema column stores T1/T2 results in v1

**v1 decision:** Do NOT simulate T1/T2. Mark as "not simulated in v1" in the engine roster.

---

### 4.5 Cut Loser (Two-Tier Loss Cutting)

> **CORRECTED (bug_hunter finding 2):** The original spec had fabricated partial-exit logic ("cut 50% / cut remaining"). The real system does FULL closes at each tier.

**Constants:**
- `CL_TIER1_MIN_PCT = -1.0%` / `CL_TIER1_MAX_PCT = -2.5%` (`hermes_constants.py:1965–1966`)
- `CL_TIER2_MIN_PCT = -2.5%` / `CL_TIER2_MAX_PCT = -3.0%` (`hermes_constants.py:1970–1971`)
- `CL_HARD_STOP_PCT = -3.0%` (cut any trade at -3.0% immediately)

**Logic (from `cut_loser.py`):**
```python
entry_price = candle_open_at_signal_ts
tier1_fired = False
tier2_fired = False

For each 1m candle after entry:
    current_pnl_pct = (candle_close / entry_price - 1) * 100  # for LONG
    
    # Hard stop: cut any trade at -3.0% immediately
    if current_pnl_pct <= -3.0:
        exit FULL POSITION at candle_close, reason='cut_loser_hard_stop'
        break
    
    # Tier 1: full close if in [-1.0%, -2.5%] range
    if not tier1_fired and CL_TIER1_MIN_PCT >= current_pnl_pct >= CL_TIER1_MAX_PCT:
        exit FULL POSITION at candle_close, reason='cut_loser_t1'
        tier1_fired = True
        break
    
    # Tier 2: full close if in [-2.5%, -3.0%] range
    if not tier2_fired and CL_TIER2_MIN_PCT >= current_pnl_pct >= CL_TIER2_MAX_PCT:
        exit FULL POSITION at candle_close, reason='cut_loser_t2'
        tier2_fired = True
        break
```

**Note:** `cut_loser.py` excludes the 40 `PROFIT_MONSTER_BYPASS_SIGNALS` families. The shadow sim should check this list before applying cut_loser.

---

### 4.6 Speed Stale Exit (Loser/Winner)

> **CORRECTED (bug_hunter finding 5 + own-conclusions):** The original spec's velocity constant was fabricated. Live is `VEL_STALE_THRESHOLD_PCT = 0.05` (% per candle), not 0.001. The live stall predicate requires `speed_percentile < 33 AND |vel| < thresh`, but shadow cannot reconstruct in-hold speed history (token_speeds keeps only a 241-row current snapshot).

**Constants:**
- `STALE_LOSER_TIMEOUT_MINUTES = 8` (stalled 8min + pnl ≤ -1.0%)
- `STALE_WINNER_TIMEOUT_MINUTES = 120` (stalled 120min + pnl ≥ +0.6%)
- `VEL_STALE_THRESHOLD_PCT = 0.05` (% per candle, `hermes_constants.py:559`)
- `SPEED_PERCENTILE_STALL = 33` (speed_percentile < 33 = stalled)

**⚠️ FIDELITY GAP (bug_hunter finding 5):** The live stall predicate is `speed_percentile < 33 AND |vel| < thresh`. Shadow omits the `speed_percentile` gate because in-hold speed history is unavailable. **Expect more stale fires than live.** Add `stall_gate_note` in `exit_speed_stale_json`. Consider downgrading speed-stale from "ranked engine" to "informational" in v1.

**Logic (from `position_manager.py:612-637`):**
```python
entry_price = candle_open_at_signal_ts
last_move_ts = entry_ts
last_price = entry_price

For each 1m candle after entry:
    current_pnl_pct = (candle_close / entry_price - 1) * 100  # for LONG
    
    # Check if price moved (updates last_move_ts)
    # NOTE: VEL_STALE_THRESHOLD_PCT is % per candle, not fraction
    if abs(candle_close - last_price) / last_price * 100 > VEL_STALE_THRESHOLD_PCT:
        last_move_ts = current_ts
        last_price = candle_close
    
    # Check stall duration
    stall_minutes = (current_ts - last_move_ts) / 60
    
    # Speed stale loser: stalled 8min + pnl ≤ -1.0%
    if stall_minutes >= 8 and current_pnl_pct <= -1.0:
        exit at candle_close, reason='speed_stale_loser'
        break
    
    # Speed stale winner: stalled 120min + pnl ≥ +0.6%
    if stall_minutes >= 120 and current_pnl_pct >= 0.6:
        exit at candle_close, reason='speed_stale_winner'
        break
```

---

### 4.7 Universal Max Hold

> **CORRECTED (own-conclusions):** The original spec used 240min. Actual is 480min with ride_it exemption. Citation corrected: `RIDE_IT_MAX_HOLD_HOURS = 24` (`hermes_constants.py:4307`), enforced in `ride_it_exit.py:342`.

**Constants:**
- `UNIVERSAL_MAX_HOLD_MINUTES = 480` (8 hours, `hermes_constants.py:1132`)
- `RIDE_IT_MAX_HOLD_HOURS = 24` (24 hours for ride_it signals, `hermes_constants.py:4307`)

**Logic (from `position_manager.py:3448-3472`):**
```python
entry_ts = signal_created_at
max_hold = 480  # default (minutes)

# Check if signal is ride_it exempt (substring match on signal string)
# NOTE: live uses substring match, NOT _match_exit_config
ride_it_substrings = ('ride_it', 'trend-ride', 'trend_ride', 'volume-breakout', 'volume_breakout', 'mover-')
if any(sub in source for sub in ride_it_substrings):
    max_hold = 1440  # 24 hours (RIDE_IT_MAX_HOLD_HOURS=24)

exit_ts = entry_ts + max_hold * 60
exit_price = candle_close_at_exit_ts
reason = 'universal_max_hold'
```

---

### 4.8 Trail Arm Timeout

> **CORRECTED (bug_hunter finding 6):** The original spec had "armed once → never times out" semantics. Live closes when **current** pnl < 0.40% **at** the 45/60-min mark. A trade that touched +0.5% then fell back to +0.1% before minute 45 IS closed live.

**Constants:**
- `BB_SQUEEZE_TRAIL_ARM_TIMEOUT_MIN = 60` (60min for bb-squeeze, `hermes_constants.py:1671`)
- `PUMP_CHAIN_TRAIL_ARM_TIMEOUT_MIN = 45` (45min for pump-chain LONGs, `hermes_constants.py:1682`)
- `PM_TRAIL_ACTIVATE_PCT = 0.004` (0.40% activation threshold)
- `BB_SQUEEZE_TRAIL_ARM_TIMEOUT_ENABLED` / `PUMP_CHAIN_TRAIL_ARM_TIMEOUT_ENABLED` (kill switches)

**Logic (from `position_manager.py:3599-3630`):**
```python
entry_ts = signal_created_at
activate_pct = 0.40  # +0.40% needed to arm trail

# Determine timeout based on signal family
if 'bb-squeeze' in source:
    timeout_min = 60
elif 'pump-chain' in source and direction == 'LONG':
    timeout_min = 45
else:
    timeout_min = None  # no timeout

# Respect ENABLED kill switches
if timeout_min and not timeout_enabled:
    timeout_min = None

If timeout_min:
    For each 1m candle after entry:
        current_pnl_pct = (candle_close / entry_price - 1) * 100
        
        # Check timeout: close if current pnl < 0.40% AT the timeout mark
        # NOTE (bug_hunter finding 6): NOT an "ever-armed" latch.
        # Live closes if hold >= timeout AND current pnl < activation threshold.
        # A trade that touched +0.5% then fell to +0.1% IS closed.
        hold_minutes = (current_ts - entry_ts) / 60
        if hold_minutes >= timeout_min and current_pnl_pct < 0.40:
            exit at candle_close, reason='trail_arm_timeout'
            break
```

---

### 4.9 RR Engine (v2 — NOT SIMULATED IN V1)

> **CORRECTED (own-conclusions):** The original spec had a placeholder. The actual RR engine is ~1200+ lines with structural S/R detection, stop-hunt buffering, regime-exempted thresholds, and continuous re-evaluation.

**v1 decision:** Do NOT simulate RR engine. Mark signals routed to `rr_engine` as `exit_rr_engine_json = None` with note "not simulated in v1".

**v2 scope:** Faithful RR engine simulation requires:
- Structural S/R level detection (`risk_reward_engine.py:608-638`)
- Stop-hunt buffering
- Regime-exempted thresholds
- Continuous re-evaluation at every PM cycle
- Immediate-close on trail breach

This is a multi-hour sub-project. Scope separately.

---

## 5. Implementation Plan

> **REVISED (own-conclusions validation):** The original 5-6 hour estimate is achievable only for a simplified v1. Corrected estimate: 6-8 hours for v1 (without RR engine). RR engine is a separate multi-hour sub-project.

### Phase 1: Extend `expiry_shadow.py` (3-4 hours)

**Goal:** Add exit engine simulation to existing shadow infrastructure.

**Changes:**
1. **Extend `record()` function:**
   - Record ALL signals (not just EXPIRED/SKIPPED)
   - Pull free context from `signals` table + `signal_metadata` (don't recompute)
   - Store `context_computed_at` to measure drift
   - Store `exit_config` from SIGNAL_EXIT_CONFIG routing
   - Store `leverage_used` = min(signals.leverage, MAX_LEVERAGE=5)

2. **Extend `close_events()` function:**
   - Add SIGNAL_EXIT_CONFIG routing (`_match_exit_config()`)
   - Add exit engine simulation (7 engines, not 6):
     - ATR SL/TP (continuous peak-trailing)
     - PM Trail (tiered, with bypass check)
     - Hard Max Loss (CUT_LOSER_PNL/leverage, unconditional)
     - Cut Loser (two-tier)
     - Speed Stale (loser 8min / winner 120min)
     - Universal Max Hold (480min, ride_it 1440min)
     - Trail Arm Timeout (bb-squeeze 60min, pump-chain 45min)
   - Apply fees (0.04%) and slippage (0.10%) to PnL
   - Store results in `exit_*_json` columns
   - Determine `first_exit_engine` (first to fire)
   - Backfill `gate_name` from `decision_reason`

3. **Add `report_v2()` function:**
   - Gate justification analysis
   - Exit engine A/B comparison
   - Signal quality rankings
   - Regime-specific analysis

### Phase 2: Context Enrichment (1 hour)

**Goal:** Capture full context at signal fire time.

**Changes:**
1. Pull free context from `signals` table + `signal_metadata` (don't recompute):
   - `z_score`, `z_score_tier`, `rsi_14`, `macd_value/signal/hist`, `momentum_state`, `leverage`, `price`
   - `signal_metadata` JSON: `bb_position`, `speed_percentile`, `wave_phase`, `momentum_score`, `price_at_signal`, `btc_score`, `btc_regime`, `btc_linreg_bias`
2. Compute additional context at record time (drift ≤30min):
   - Volatility regime (from ATR on 1h candles)
   - Market bias (1m, 4h)
   - BTC context (regime, ATR, EMA300, linreg)
   - Chop score, tide state, market phase
3. Store `context_computed_at` to measure drift

### Phase 3: A/B Testing Framework (1 hour)

**Goal:** Compare exit engines on the same signals.

**Changes:**
1. For each signal, simulate ALL applicable exit engines (based on SIGNAL_EXIT_CONFIG routing)
2. Record which engine fired first
3. Compare PnL across engines (after fees + slippage)
4. Aggregate by signal type, regime, direction

### Phase 4: Reporting & Analysis (1 hour)

**Goal:** Answer the questions T asked.

**Reports:**
1. **Gate Justification:** "Gate X blocked 100 trades, 45 would have won (45% WR)"
2. **Exit Engine A/B:** "Trailing stop works best for pump-chain (70% WR), ATR works best for bb-bounce (65% WR)"
3. **Signal Quality:** "bb-squeeze 70% WR in EXTREME, 30% in NORMAL → trade only in EXTREME"
4. **Regime Analysis:** "LONG signals work in trend (65% WR), fail in chop (35% WR)"

**Note:** This supersedes `gate_shadow.py` for gate justification analysis (see Section 10).

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

### 6.4 Slow-Engine Truncation (own-conclusions finding 9)

**⚠️ CRITICAL:** The close pass runs at 4.5h, but Universal Max Hold is 8h and ride_it is 24h. Without a re-close pass, slow engines are truncated and A/B biases toward fast engines.

**Fix:** Add a re-close pass that runs every 4 hours on signals where:
- `closed = 0` AND `created_at < now - 4.5h` (first pass missed)
- OR `first_exit_engine = 'universal_max_hold'` AND `hold_minutes < 480` (truncated)
- OR `first_exit_engine = 'universal_max_hold'` AND `hold_minutes < 1440` (ride_it truncated)

This ensures slow engines get full simulation.

### 6.5 Gate Attribution (own-conclusions finding 7)

**⚠️ CRITICAL:** 985/999 signals/24h have `decision_reason='compaction_stale_10min'`. Execution gates only exist in `pipeline.log`, not in the signals DB. The backfill design yields UNKNOWN for every gate except CONFLUENCE-EXPIRY.

**Fix:** Reuse `gate_shadow.py`'s log parser to extract gate names from `pipeline.log`. The parser already handles `[CTX-GATE]`-style strings with leading emoji/whitespace.

### 6.6 Performance
- Batch processing: record every 30min, close every 1h
- **Windowed candle reads** (not full-history caching): binary-search `[entry_ts, exit_ts]` window per signal. The 1m table is PK'd on `(token, ts)` so range reads are cheap.
- **Cache per (token, floor_ts) within a batch** to avoid re-reading same candles for signals on same token
- Use indexes for common queries
- Limit to 1000 signals per batch to avoid memory issues
- **Memory note:** Full-history caching would OOM (~33M tuples for 150 tokens). Use windowed reads only.

### 6.5 Timezone Handling
- All timestamps in UTC (ISO format)
- Use `calendar.timegm()` for timestamp conversion
- Store both signal time and record time

### 6.6 Entry Price Convention
- Entry = candle open at signal ts (assumes zero detection-to-execution latency)
- Live trades enter minutes later (staleness gotcha)
- **All shadow PnL will be optimistic vs live** — fine for relative A/B (same convention across engines), but do NOT read absolute shadow PnL as achievable

---

## 7. Testing Strategy

### 7.1 Unit Tests
- Test each exit engine simulation independently
- **HML formula test:** `compute_hml_threshold(atr_pct=0.3, leverage=5) == -0.80` (NOT -0.15)
- Test context capture with known values
- Test edge cases (missing candles, insufficient data)

### 7.2 Integration Tests
- Test record → close → report pipeline
- Test with real signals from signals DB
- Validate against actual live trades

### 7.3 Validation
- Compare shadow PnL vs actual PnL for EXECUTED signals
- **Qualitative reconciliation** (n≈2/day too thin for statistical bar)
- Live trades go through full cascade (cut_loser tiers, soft trigger, speed stale) which shadow doesn't simulate — mismatches are expected for structural reasons
- Use validation to check for gross errors, not statistical accuracy

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
| Data completeness | >95% | `SELECT 100.0 * SUM(CASE WHEN first_exit_engine IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*) FROM shadow_trades WHERE closed=1 AND first_exit_reason != 'unclosed_no_candles'` |
| Gate justification | Answered | Report shows "Gate X blocked N, M would have won" |
| Exit engine A/B | Complete | Report shows engine rankings per signal type |
| Validation | Qualitative | Compare shadow PnL vs actual PnL for EXECUTED signals (n≈2/day, too thin for statistical bar — use qualitative reconciliation) |

> **Note (own-conclusions validation):** The original 5%-match validation bar is unachievable at n≈2 EXECUTED/day. Live trades go through the full cascade (cut_loser tiers, soft trigger, speed stale, cascade flip) which the shadow doesn't simulate, so mismatches are guaranteed for structural reasons. Use qualitative reconciliation instead.

> **Note (bug_hunter finding 10):** Completeness metric excludes `unclosed_no_candles` — those are expected outcomes, not data quality issues.

### Retention & Purge (bug_hunter finding 9)

- **90-day retention:** Add purge to `expiry_shadow.py` main or a systemd timer
- **SQLite concurrency:** Use `PRAGMA journal_mode=WAL` + `busy_timeout=5000` or reuse `hermes_file_lock`
- **Table size projection:** ~1000 rows/day × 90d ≈ 90k rows + fat JSON columns — acceptable
- **Purge query:** `DELETE FROM shadow_trades WHERE created_at < datetime('now', '-90 days')`

---

## 10. Reconciliation with Existing Shadow Systems

> **IMPORTANT (own-conclusions validation):** 7 shadow systems already exist and accumulate data. This spec must explicitly state its relationship to them.

| System | Status | Data | Relationship |
|--------|--------|------|--------------|
| `expiry_shadow.py` | Running (15,480 events) | Forward returns for EXPIRED/SKIPPED | **EXTEND** — this spec extends it with exit engine simulation |
| `gate_shadow.py` | Running (24,641 events) | Per-gate shadow WR | **SUPERSEDES** for gate justification — this spec produces richer data |
| `t5_shadow.py` | Running | WOULD_TRADE/WOULD_SKIP vs live WR | **COMPLEMENTARY** — different purpose |
| `exit_optimizer_shadow.py` | Exists (no timer found) | MFE/MAE replay | **SUPERSEDES** — this spec can know path order, exit_optimizer cannot |
| `mom_filter_shadow.py` | Running | Momentum filter counterfactual | **COMPLEMENTARY** — different purpose |
| `temporal_confluence_shadow.py` | Exists (7th shadow system) | Temporal confluence counterfactual | **COMPLEMENTARY** — different purpose |
| `signal_outcomes` table | Exists | Signal outcome tracking | **EXTEND** — this spec adds exit engine simulation |

**Decision:** This spec EXTENDS `expiry_shadow.py` and SUPERSEDES `gate_shadow.py` + `exit_optimizer_shadow.py` for gate justification and exit engine analysis. The other shadow systems remain complementary.

---

## 10.5 Integration with Existing A/B Engine

> **IMPORTANT (T directive 2026-10-20):** An existing A/B testing engine was installed when the system started but was phased out. This spec must incorporate it.

### Existing A/B Engine (Verified)

| Component | Status | Location |
|-----------|--------|----------|
| `ab_optimizer.py` | Exists (phased out) | `scripts/ab_optimizer.py` |
| `hermes_ab_utils.py` | Exists (phased out) | `scripts/hermes_ab_utils.py` |
| `ab_results` table | Exists (stale data) | PostgreSQL `brain.ab_results` |
| `ab_tests.json` | Exists (empty config) | `config/ab_tests.json` |

**What it does:**
- **Epsilon-greedy selection** (15% exploration): picks one variant per live trade
- **Thompson sampling** (`hermes_ab_utils.py`): statistical variant selection
- **Evolution engine**: kills losing variants (PnL < -15%), spawns new variants
- **W&B tracking**: offline Weights & Biases logging

**Current state:**
- `ab_results` table has 5 rows but all show 0 wins / 0% WR / 0% PnL (stale)
- `ab_tests.json` is empty (no tests configured)
- Was used by `decider_run.py` for SL distance, entry timing, trailing stop
- Was used by `hl-sync-guardian.py` for flip strategy

### Key Difference: Live A/B vs Shadow A/B

| Aspect | Live A/B (existing) | Shadow A/B (this spec) |
|--------|---------------------|------------------------|
| Selection | Picks ONE variant per trade | Simulates ALL variants |
| Data source | Live trade outcomes | Simulated exit engine outcomes |
| Purpose | "Which variant should we use?" | "Which variant WOULD have worked?" |
| Cost | Real money at risk | Zero cost |
| Sample size | ~20 trades/day | ~1000 signals/day |

### Integration Strategy

**Reuse the `ab_results` schema** for shadow A/B results:

```sql
**⚠️ ISOLATION (bug_hunter finding 3):** Do NOT write shadow-simulated data into the live `ab_results` table. Use a separate `shadow_ab_results` table or hard `shadow:` namespace prefix. Never feed shadow rows to `get_ab_variant`/live evolution. This prevents simulated outcomes from silently steering live variant selection if live A/B is ever re-enabled.

**Use a separate table for shadow A/B results:**

```sql
-- Shadow A/B results in a SEPARATE table (not ab_results)
CREATE TABLE IF NOT EXISTS shadow_ab_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_name TEXT NOT NULL,
    variant_id TEXT NOT NULL,
    trades INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    win_rate_pct DOUBLE PRECISION DEFAULT 0,
    total_pnl_pct DOUBLE PRECISION DEFAULT 0,
    total_pnl_usdt DOUBLE PRECISION DEFAULT 0,
    avg_win_pct DOUBLE PRECISION DEFAULT 0,
    avg_loss_pct DOUBLE PRECISION DEFAULT 0,
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(test_name, variant_id)
);

INSERT INTO shadow_ab_results (test_name, variant_id, trades, wins, losses, 
                               win_rate_pct, total_pnl_pct, total_pnl_usdt)
VALUES ('exit-engine-atr', 'atr_sl_tp', 1000, 450, 550, 45.0, 12.5, 3.75)
ON CONFLICT (test_name, variant_id) 
DO UPDATE SET trades = EXCLUDED.trades, wins = EXCLUDED.wins, ...;
```

**Reuse the evolution engine** for shadow A/B (but on `shadow_ab_results`, not `ab_results`):
- Kill exit engines that consistently lose on shadow trades
- Spawn new exit engine variants (e.g., different trail distances)
- Redistribute weight to winning engines

**Adapt the selection logic:**
- Live A/B: `get_ab_variant()` picks ONE variant
- Shadow A/B: simulate ALL variants, record all outcomes

### New Shadow A/B Tests to Create

| Test Name | Variants | Purpose |
|-----------|----------|---------|
| `exit-engine-atr` | ATR SL/TP (static vs trailing) | Which ATR exit works best? |
| `exit-engine-trail` | PM Trail (0.20%/0.50%/0.80%/1.20%) | Which trail distance works best? |
| `exit-engine-hml` | HML (-0.5%/-0.8%/-1.2%) | Which HML threshold works best? |
| `exit-engine-combo` | ATR+Trail, Trail-only, ATR-only | Which combination works best? |

### Implementation

1. **Extend `expiry_shadow.py --close`**: After simulating exit engines, write results to `ab_results` table
2. **Add `--evolve` mode**: Run evolution on shadow A/B results
3. **Add `--report` mode**: Show which exit engines work best per signal type/regime

---

## 11. Risks & Mitigations

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
| `gate_shadow.py` | Exists (24,470 events) | `scripts/gate_shadow.py` |
| `exit_optimizer_shadow.py` | Exists (no timer found) | `scripts/exit_optimizer_shadow.py` |
| `mom_filter_shadow.py` | Exists | `scripts/mom_filter_shadow.py` |
| `temporal_confluence_shadow.py` | Exists (7th shadow system) | `scripts/temporal_confluence_shadow.py` |
| Cell stats | Exists (697 cells) | `brain/cell_stats.db` |
| `volatility_gate_v2.py` | Exists | `scripts/volatility_gate_v2.py` |
| `rsi_utils.py` | Exists | `scripts/rsi_utils.py` |
| `chop_detector.py` | Exists | `scripts/chop_detector.py` |
| `tpsl_utils.py` | Exists | `scripts/tpsl_utils.py` |
| `profit_monster.py` | Exists | `scripts/profit_monster.py` |
| `cut_loser.py` | Exists | `scripts/cut_loser.py` |
| `ride_it_exit.py` | Exists (v2 scope) | `scripts/ride_it_exit.py` |
| `risk_reward_engine.py` | Exists (v2 scope) | `scripts/risk_reward_engine.py` |
| `ab_optimizer.py` | Exists (phased out) | `scripts/ab_optimizer.py` |
| `hermes_ab_utils.py` | Exists (phased out) | `scripts/hermes_ab_utils.py` |

---

## Appendix D: Known Divergences from Live

> **IMPORTANT (bug_hunter recommendation 5):** These are known fidelity gaps in the shadow simulation. Day-8 analysis must NOT over-read shadow rankings.

| Divergence | Impact | Mitigation |
|------------|--------|------------|
| **Entry price optimism** | Shadow uses candle open at signal ts (zero latency). Live enters minutes later. All shadow PnL optimistic. | Fine for relative A/B (same convention). Do NOT read absolute shadow PnL as achievable. |
| **Speed-stale fidelity gap** | Shadow omits `speed_percentile < 33` gate (in-hold speed history unavailable). Expect more stale fires than live. | Downgrade speed-stale from "ranked" to "informational" in v1. |
| **ATR engine simplification** | Shadow uses simplified peak-trailing. Live is ~700 lines with entry floor, k-tiering, phase scaling, snap logic. | Acceptable as approximation. Label as "simplified ATR" in reports. |
| **Partial-close engines** | PM T1/T2 and Cut Loser tiers do partial closes live. Shadow simulates full closes only. | PnL accounting slightly wrong for partial-close trades. Note in reports. |
| **pump_exit/ride_it approximation** | Signals routed to these configs are simulated through universal stack, not their actual exit logic. | Label `exit_config` for stratified analysis. Do NOT compare pump_exit shadow vs pump_exit live. |
| **Speed history unavailability** | Shadow cannot reconstruct in-hold speed history (token_speeds keeps only 241-row current snapshot). | Speed-stale engine is informational only in v1. |
| **Probable live bug** | profit_monster trail appears to activate at +0.004% (percent vs fraction) instead of +0.40%. | Resolve before shadowing. If live bug confirmed, shadow should simulate the CORRECT behavior (+0.40%), not the buggy behavior. |

## Appendix B: Exit Engine Constants

| Constant | Value | Location |
|----------|-------|----------|
| `CUT_LOSER_PNL` | -4.00% | `hermes_constants.py:717` |
| `HML_VOL_ATR_MULT` | 0.5 | `hermes_constants.py:718` |
| `PM_TRAIL_ACTIVATE_PCT` | 0.004 (0.40%) | `hermes_constants.py:1659` |
| `PM_TRAIL_TIERS` | 0.20/0.50/0.80/1.20% | `hermes_constants.py:1732-1737` |
| `PM_TRAIL_MIN_HOLD` | 2 | `hermes_constants.py:1738` |
| `TRAILING_ACTIVATION_PCT` | 0.0040 (0.40%) | `hermes_constants.py:727` |
| `TRAILING_DISTANCE_PCT` | 1.20% | `hermes_constants.py:728` |
| `ATR_SL_MIN_INIT` | 1.5% | `hermes_constants.py:711` (not tpsl_utils) |
| `ATR_SL_MIN_ACCEL` | 0.30% | `hermes_constants.py:705` (not tpsl_utils) |
| `ATR_SL_MAX` | 2.5% | `hermes_constants.py:696` |
| `VEL_STALE_THRESHOLD_PCT` | 0.05 (%/candle) | `hermes_constants.py:559` |
| `STALE_LOSER_TIMEOUT_MINUTES` | 8 | `hermes_constants.py:565` |
| `STALE_WINNER_TIMEOUT_MINUTES` | 120 | `hermes_constants.py:564` |
| `STALE_LOSER_MAX_LOSS` | -1.0% | `hermes_constants.py:566` |
| `STALE_WINNER_MIN_PROFIT` | +0.6% | `hermes_constants.py:567` |
| `UNIVERSAL_MAX_HOLD_MINUTES` | 480 | `hermes_constants.py:1132` |
| `RIDE_IT_MAX_HOLD_HOURS` | 24 | `hermes_constants.py:4307` (not MINUTES) |
| `BB_SQUEEZE_TRAIL_ARM_TIMEOUT_MIN` | 60 | `hermes_constants.py:1671` |
| `PUMP_CHAIN_TRAIL_ARM_TIMEOUT_MIN` | 45 | `hermes_constants.py:1682` |
| `MAX_LEVERAGE` | 5 (fallback) | `position_manager.py:157` |
| ATR(14) | 15m-primary | `tpsl_utils.get_fresh_atr` (not volatility_gate 1h) |

## Appendix C: Gate Names (for `gate_name` column)

> **Note (own-conclusions validation):** CONFLUENCE-EXPIRY is the single largest filter (974/986 blocks in 24h = 98.9%). It must be included.

| Gate | Description | Est. Frequency |
|------|-------------|----------------|
| `CONFLUENCE-EXPIRY` | Single-source expired waiting for co-signal | ~98.9% of blocks |
| `CONFLUENCE-GATE-BLOCK` | Single-source not in STANDALONE_BYPASS | <1% |
| `SHORT-RSI-HARD-FLOOR` | SHORT RSI < 35 | ~50/day |
| `PUMP-CHAIN-SHORT-HIGH` | pump-chain- SHORT in HIGH vol | ~50/day |
| `VOL-GATE-BYPASS` | Vol gate override=0.0 | ~50/day |
| `CONTINUUM-BLOCK` | BTC bearish structure blocks LONG | ~50/day |
| `SHORT-REGIME-GATE` | SHORT in NORMAL/HIGH, conf < 75 | ~50/day |
| `LONG-NEUTRAL-CHOP` | LONG in NEUTRAL, BTC flat | ~50/day |
| `RR-ENGINE` | R:R < 0.55 hard block | ~50/day |
| `LONG-RSI-CEILING` | LONG RSI > 75 | ~10/day |
| `PUMP-CHAIN-RSI-MAX` | pump-chain+ LONG RSI >= 70 | ~10/day |

### Gate Name Backfill Mechanism

> **CORRECTED (own-conclusions finding 7):** 985/999 signals/24h have `decision_reason='compaction_stale_10min'`. Execution gates only exist in `pipeline.log`. The simple regex backfill yields UNKNOWN for every gate except CONFLUENCE-EXPIRY.

**Fix:** Reuse `gate_shadow.py`'s log parser to extract gate names from `pipeline.log`. The parser already handles `[CTX-GATE]`-style strings with leading emoji/whitespace.

1. **Record at fire:** Set `decision='PENDING'`, `gate_name=NULL`
2. **Backfill within 2h purge window:** 
   - For `decision_reason='compaction_stale_10min'` → `gate_name='CONFLUENCE-EXPIRY'`
   - For other reasons → parse from `pipeline.log` using `gate_shadow.py`'s parser
3. **Parse free-text reasons:** Use `gate_shadow.py`'s regex (handles leading emoji/whitespace)

```python
# CORRECT — reuse gate_shadow.py's parser
from gate_shadow import parse_gate_name_from_log
gate_name = parse_gate_name_from_log(pipeline_log_line)
# Falls back to: compaction_stale → CONFLUENCE-EXPIRY, else UNKNOWN
```
