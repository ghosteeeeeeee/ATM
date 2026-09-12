# ATR SL Audit — Independent Verdict
**Date:** 2026-09-12  
**Auditor:** Independent code + data analysis  
**Files reviewed:** decider_run.py, position_manager.py, tpsl_utils.py, hermes_constants.py, run_pipeline.py  
**DB queries:** PostgreSQL brain (4960 closed trades analyzed)

---

## Code Path Trace: Trade Creation → First ATR SL Write

### Step 1: execute_trade() writes INITIAL SL (decider_run.py lines 1594-1607)

```python
# decider_run.py:1594-1607
from hermes_constants import ATR_SL_MIN_INIT, ATR_TP_MIN
_live_price = get_current_price(token) or price
price = _live_price
if direction == 'LONG':
    sl = round(_live_price * (1 - ATR_SL_MIN_INIT), 8)   # entry - 1.2%
    tp = round(_live_price * (1 + ATR_TP_MIN), 8)         # entry + 0.8%
else:
    sl = round(_live_price * (1 + ATR_SL_MIN_INIT), 8)   # entry + 1.2%
    tp = round(_live_price * (1 - ATR_TP_MIN), 8)         # entry - 0.8%
sl_pct_val = ATR_SL_MIN_INIT  # 0.012
```

**At trade open:** SL = live_price ± 1.2%. This is a **fixed 1.2%** value, NOT token-specific ATR. It is anchored to `live_price` (current market price at execution, not signal price).

This is then passed to brain.py via `--sl` and `--sl-distance 0.012` arguments, which writes it to the DB.

### Step 2: Pipeline order (run_pipeline.py line 30)

```python
STEPS_EVERY_MIN = ['signal_compactor', 'signal_analyst', 'breakout_engine',
                   'signals_runner', 'decider_run', 'position_manager', 'hermes-trades-api']
```

**decider_run runs BEFORE position_manager in the SAME pipeline cycle.** This means:
- T+0s: decider_run opens trade, writes SL = entry ± 1.2% to DB
- T+~5-15s: position_manager starts, reads positions (including the new trade)
- T+~15-25s: `_collect_atr_updates()` computes ATR-based SL/TP
- T+~25-30s: `_persist_atr_levels()` writes ATR SL to DB
- T+~30-35s: `check_atr_tp_sl_hits()` checks SL/TP hits using the fresh ATR SL

**Gap between trade open and first ATR SL write: ~15-30 seconds within the same cycle.**

### Step 3: position_manager ATR SL computation (_collect_atr_updates → compute_atr_sl_tp)

In `tpsl_utils.py`, `compute_atr_sl_tp()` determines the SL:

1. **BRAND-NEW TRADE GUARD** (line 341-360): If `trade_open_time` < 120s ago, forces `is_initial_write=True` and `is_new_trade=True`
2. **Anchor for new trades** (line 362-364): `ref_price = entry_price` (NOT highest_price/lowest_price)
3. **SL floor for new trades** (line 478): `MIN_SL_PCT = ATR_SL_MIN_INIT` (1.2%)
4. **k multiplier** (line 474): base k from `_atr_tier(atr_pct)` — 0.8/1.0/1.5 depending on volatility
5. **Effective SL** (line 496): `eff_sl_pct = min(max(k × atr_pct, ATR_SL_MIN_INIT), ATR_SL_MAX_INIT)` = clamp between 1.2% and 1.5%

For the first 2 minutes: **SL = entry_price ± eff_sl_pct** where eff_sl_pct ∈ [1.2%, 1.5%]

After 2 minutes (is_new_trade becomes False):
- In profit: trail from `highest_price`/`lowest_price` at `TRAILING_DISTANCE_PCT` (1.2%)
- In loss: ATR_SL_MIN (1.2%) floor from entry

### Step 4: check_atr_tp_sl_hits (position_manager.py lines 386-460)

Simple price-vs-SL check:
- LONG: `current_price <= stop_loss` → SL hit
- SHORT: `current_price >= stop_loss` → SL hit

Runs AFTER `_persist_atr_levels()` writes the ATR SL to DB, and after in-memory positions are updated (line 2429: `pos['stop_loss'] = u['new_sl']`).

---

## Specific Questions Answered

### a. What exact SL value is written to DB at trade creation time?

**SL = live_price ± ATR_SL_MIN_INIT (1.2%).** This is a **fixed 1.2%** distance, NOT a token-specific ATR computation. The `sl_distance` column is set to `0.012`. It is anchored to the live market price at execution time (via `get_current_price()`), NOT to the stale signal price.

**Evidence from DB:** 696 trades have `sl_distance = 0.012` (matching ATR_SL_MIN_INIT). 2183 trades have `sl_distance = 0` — these are legacy trades from BEFORE the fix was implemented (line 1594 comment: "Set initial SL/TP at trade open to eliminate the 60s zero-SL window").

### b. When does the FIRST ATR computation run?

**Same pipeline cycle, ~15-30 seconds after trade open.** Pipeline order: `decider_run` → `position_manager`. position_manager calls `_collect_atr_updates()` which invokes `tpsl_utils.compute_atr_sl_tp()`. This is the first real ATR computation. It runs in the SAME cycle, not the next one.

### c. What is the actual time gap between trade open and first real ATR SL?

**~15-30 seconds** (within the same pipeline cycle). The gap exists but is minimal because both scripts run sequentially in the same 1-minute pipeline. The initial 1.2% SL from execute_trade() provides protection during this gap.

### d. Does "trailing" start from T+0 or from T+60s? What anchors the SL at T+0?

**Trailing effectively starts from T+~15-30s** (first position_manager cycle), but with limitations:
- **T+0 to T+~15s:** SL is fixed at entry ± 1.2% (set by execute_trade). No trailing.
- **T+~15s to T+120s:** ATR SL computation runs, but `is_new_trade=True` forces anchor to `entry_price` and MIN_SL_PCT = ATR_SL_MIN_INIT (1.2%). SL is effectively fixed at entry ± [1.2%-1.5%].
- **T+120s+:** `is_new_trade` becomes False. If in profit, trailing takes over: SL trails from `highest_price`/`lowest_price` at `TRAILING_DISTANCE_PCT` (1.2%).

**At T+0, the SL is anchored to `live_price`** (current market price fetched via `get_current_price()`), not to the signal price. This was explicitly fixed: "use CURRENT market price (not signal price) — signal may be stale."

### e. Is the initial SL anchored to entry_price or to current_price?

**Both are used, at different stages:**
- **execute_trade (T+0):** Anchored to `live_price` = `get_current_price()` (current market price). This becomes the DB `entry_price`.
- **compute_atr_sl_tp (T+~15s):** For new trades (`is_new_trade=True`), `ref_price = entry_price` (from DB). The SL = entry_price × (1 ± eff_sl_pct).

In practice, `live_price` at T+0 ≈ `entry_price` at T+~15s (same price, minor drift).

### f. Would ATR_SL_MIN_INIT (1.2%) have been different from full ATR SL (k × ATR%)?

**YES — for HIGH volatility tokens, the full ATR SL would be WIDER (up to 1.5%).**

| Volatility | ATR% | k | k×ATR% | Effective SL (clamped) | Difference from 1.2% |
|-----------|------|---|--------|----------------------|---------------------|
| Low | 0.5% | 0.8 | 0.4% | 1.2% (floor) | Same |
| Normal | 1.0% | 1.0 | 1.0% | 1.2% (floor) | Same |
| Normal+ | 1.2% | 1.0 | 1.2% | 1.2% | Same |
| High | 1.5% | 1.5 | 2.25% | 1.5% (cap) | +0.3% wider |
| Extreme | 2.0% | 1.5 | 3.0% | 1.5% (cap) | +0.3% wider |

**For volatile tokens (ATR% > 1.5%), the full ATR SL would have been 1.5% instead of 1.2%** — a 0.3% wider stop that could have saved some trades from noise stop-outs. However, this only applies AFTER the first position_manager cycle (~15-30s), not at the very instant of trade open.

### g. What happens if price moves against the trade in the first 60 seconds?

**The trade IS protected — by the 1.2% fixed SL from execute_trade().** This SL is written to DB immediately at trade open and checked by `check_atr_tp_sl_hits()` on the next position_manager cycle (within ~30s).

However, for trades that were opened with `sl_distance=0` (legacy code path), there was NO SL protection at open. The DB query shows **20 trades with sl_distance=0 had ATR SL hits within 2 minutes** — these trades had their SL written by position_manager's first cycle, but the SL value could have been wrong (e.g., wrong-side SL from anchoring to current_price instead of entry_price).

---

## DB Evidence

### Trades with SL hit within 2 minutes of open: **175 trades**
### Trades with SL hit within 5 minutes of open: **307 trades**

### sl_distance distribution (ATR SL hits within 5 min):
| sl_distance | Count | Avg PnL% | Avg Duration(s) |
|------------|-------|----------|-----------------|
| 0 (legacy) | 194 | -0.28% | 84s |
| 0.015 (1.5%) | 27 | -0.50% | 60s |
| 0.01 (1.0%) | 26 | -1.16% | 175s |
| 0.005 (0.5%) | 22 | -0.22% | 160s |
| 0.008 (0.8%) | 22 | -1.20% | 200s |
| 0.012 (1.2%) | 12 | -8.61% | 135s |

### Average loss by exit timing (ATR SL hits only):
| Bucket | N | Avg PnL% | Avg PnL$ | Min PnL% | Max PnL% |
|--------|---|----------|----------|----------|----------|
| <2min | 175 | -0.70% | -$0.03 | -41.62% | +0.98% |
| 2-10min | 362 | -1.07% | -$0.06 | -18.85% | +7.81% |
| >10min | 2173 | -0.44% | -$0.05 | -12.58% | +47.53% |

### Wrong-side SL at close (within 2 min): **20 trades**
These are trades where SL was on the wrong side of entry (LONG SL above entry, SHORT SL below entry) — immediate guaranteed stop-out. Examples include PONS (SL +51% above entry), ME (SL +66% above entry), MORPHO (SL +2.4% above entry).

---

## Verdicts on Previous Claims

### Claim 1: "ATR SL IS already set from trade creation time — execute_trade() sets SL = entry ± ATR_SL_MIN_INIT (1.2%) immediately"
**Verdict: AGREE**  
**Evidence:** decider_run.py lines 1594-1607 explicitly set `sl = round(_live_price * (1 - ATR_SL_MIN_INIT), 8)` at trade open. The `sl_distance` column in DB confirms 696 trades with value 0.012. The comment on line 1594 states: "Set initial SL/TP at trade open to eliminate the 60s zero-SL window."  
**Confidence: HIGH**

### Claim 2: "Within ~60 seconds, position_manager replaces it with full ATR-based SL"
**Verdict: PARTIAL**  
**Evidence:** Pipeline order (run_pipeline.py:30) shows position_manager runs AFTER decider_run in the SAME cycle — the gap is ~15-30 seconds, not 60s. However, the "full ATR-based SL" is misleading: for the first 120 seconds, `compute_atr_sl_tp()` uses `is_new_trade=True` which clamps SL to ATR_SL_MIN_INIT (1.2%) — effectively the SAME value as the initial SL. The full ATR k×ATR% computation only takes effect after 120 seconds.  
**Confidence: HIGH**

### Claim 3: "The gap is NOT the problem — slippage from market orders is the real issue"
**Verdict: PARTIAL**  
**Evidence:** The gap is real but minimal (~15-30s within same cycle). The initial 1.2% SL provides protection during this gap. However, 20 trades show WRONG-SIDE SL at close (SL above entry for LONG, below for SHORT) — these are guaranteed instant stop-outs. These are caused by the ATR SL computation anchoring to current_price instead of entry_price for non-initial writes, which was partially fixed by the BRAND-NEW TRADE GUARD (2026-07-20). The 175 trades with SL hit within 2 minutes represent 3.5% of all 4960 closed trades — a non-trivial number. Slippage IS a real issue (especially for market orders), but the SL computation bugs (wrong-side, too tight) also contributed to losses.  
**Confidence: MEDIUM**

### Claim 4: "ATR SL trailing starts from the first pipeline cycle after trade open"
**Verdict: PARTIAL**  
**Evidence:** ATR SL computation runs in the first pipeline cycle after trade open (same cycle as trade creation). But "trailing" in the true sense (SL following peak/nadir) does NOT start until 120 seconds after trade open. For the first 120 seconds, the SL is fixed at entry ± [1.2%-1.5%], anchored to entry_price. After 120 seconds, if in profit, trailing from highest_price/lowest_price at TRAILING_DISTANCE_PCT (1.2%) takes over.  
**Confidence: HIGH**

---

## Key Findings

1. **The initial SL (1.2%) is NOT ATR-based** — it's a fixed constant (ATR_SL_MIN_INIT). For volatile tokens, the ATR-based SL would be wider (up to 1.5%). The 0.3% difference could save some trades from noise stop-outs.

2. **The 120-second INIT window is real** — for the first 2 minutes, trailing is disabled and SL is clamped to 1.2%-1.5%. This is by design (BRAND-NEW TRADE GUARD) to prevent wrong-side SL from peak-anchoring on fresh trades.

3. **20 trades had WRONG-SIDE SL** (SL above entry for LONG) within 2 minutes — these are immediate guaranteed stop-outs. The BRAND-NEW TRADE GUARD was added 2026-07-20 to fix this, but the data shows it still occurred.

4. **175 trades (3.5%) hit ATR SL within 2 minutes** — these trades barely survived their first pipeline cycle. Average loss: -0.70%.

5. **The sl_distance=0 legacy trades (2183 total, 194 ATR SL hits within 5 min)** had NO SL at trade open — they relied entirely on position_manager's first cycle to set SL. These are the most vulnerable.

6. **TRAILING_DISTANCE_PCT (1.2%) = ATR_SL_MIN_INIT (1.2%)** — the trailing distance matches the initial SL, so there's effectively no change in SL tightness between the INIT phase and the TRAILING phase for most tokens.
