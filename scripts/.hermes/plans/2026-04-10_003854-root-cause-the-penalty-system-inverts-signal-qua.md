# Plan: Fix the Penalty System That Inverts Signal Quality

## Root Cause Summary

The **confidence paradox** is real: low-confidence LONG trades (+0.53% avg) outperform max-confidence LONG trades (+0.04% avg) by **13x per trade**. The system is systematically blocking good signals while letting bad ones through.

**Three confirmed bugs:**

| # | File | Issue | Severity |
|---|------|-------|----------|
| 1 | `decider_run.py` | `confidence` variable uninitialized before `confidence -= trap_penalty` (line 1112) | **CRASH** — should be NameError when trap_penalty > 0 |
| 2 | `decider_run.py` | Penalty chain uses `confidence`, threshold check uses `effective_conf` — penalties have **zero effect** on approvals | **LOGIC FAILURE** — entire penalty system broken |
| 3 | `position_manager.py` | `refresh_current_prices()` computes `pnl_pct` in-memory but never writes to DB | **DATA GAP** — open position PnL always reads as 0 in DB |

---

## BUG 1 & 2 Fix: Rebuild the Penalty Chain in `_run_hot_set()`

### Current Broken Code Flow (lines 1104–1208)

```
line 1104: effective_conf = float(sig_conf) * wave_mult
line 1112: confidence -= trap_penalty     ← confidence never initialized!
line 1130: confidence -= penalty          ← also uses uninitialized confidence
line 1155: confidence -= 20              ← also uses uninitialized confidence
line 1164: confidence -= 20              ← also uses uninitialized confidence

lines 1192/1195/1208:
  should_approve = effective_conf >= threshold  ← uses effective_conf (penalties never applied!)
```

### The Core Design Flaw

The penalty chain was built assuming `confidence = effective_conf` and then `confidence` gets penalized. But:
1. `confidence` is **never initialized** — Python would crash with NameError
2. Even if initialized, the threshold check uses `effective_conf` — the **un-penalized** value
3. The penalty system is **completely non-functional** — penalties have zero effect on approvals

### Proposed Fix (Option B + partial C hybrid)

**Step 1: Initialize confidence from effective_conf**
```python
effective_conf = float(sig_conf) * wave_mult
confidence = effective_conf   # ← ADD THIS LINE (fixes BUG 1)
```

**Step 2: Cap total penalty stack at 25pts**
```python
trap_penalty, trap_reason = _check_counter_trend_trap(token, direction)
if trap_penalty > 0:
    confidence -= min(trap_penalty, 25)   # cap individual penalty at 25
    ...
```

And similarly for regime penalty:
```python
penalty = min(int(regime_conf * 0.4), 25)   # cap at 25
confidence -= penalty
```

**Step 3: Use penalized `confidence` for threshold comparison** (fixes BUG 2)
```python
# Change from:
should_approve = effective_conf >= threshold
# To:
should_approve = confidence >= threshold   # penalties now actually matter
```

**Step 4: Confidence floor for high-conviction signals**
If `sig_conf >= 90` (before wave multiplier), set floor at 70:
```python
if sig_conf >= 90:
    confidence = max(confidence, 70)   # hard to block signals that started at 90+
```

### Re-weighting Based on Data (Option C partial)

| Signal | Current | Proposed | Rationale |
|--------|---------|----------|-----------|
| `vel-hermes` | neutral (1.0) | **1.2 boost** | SHORT data: +5.59% avg return is exceptional |
| `hzscore` (combo) | suppressed (0.15–0.4) | **0.8** | Data shows +0.37% avg, WR 67% on NIL |
| `pct-hermes` | suppressed (0.6) | **0.8** | Not killing us, ambiguous signal |
| `hmacd-mtf_macd` | 1.0 | keep 1.0 | Solid MACD crossover signals |
| `rsi-hermes` | 1.0 | keep 1.0 | +1.18% LONG on small n |

---

## BUG 3 Fix: Write PnL to DB in `refresh_current_prices()`

### Location
`position_manager.py`, function `refresh_current_prices()` (line 1705)

### Current Behavior
- Computes `pnl_pct`, `pnl_usdt`, `cur_price` from HL data
- Updates in-memory `pos['pnl_pct']`, `pos['pnl_usdt']`, `pos['current_price']`
- **Never executes**: `UPDATE trades SET pnl_pct = ?, pnl_usdt = ?, current_price = ? WHERE id = ? AND status = 'open'`

### Fix
After computing values (around line 1785), add:
```python
if cur_price > 0:
    pos['pnl_pct'] = pnl_pct
    pos['current_price'] = cur_price
    pos['pnl_usdt'] = pnl_usdt
    updated += 1

    # BUG FIX: persist to DB so direct DB queries return correct PnL
    try:
        c.execute("""
            UPDATE trades
            SET pnl_pct = ?, pnl_usdt = ?, current_price = ?, updated_at = ?
            WHERE id = ? AND status = 'open'
        """, (pnl_pct, pnl_usdt, cur_price, now_str, trade_id))
        conn.commit()
    except Exception as e:
        print(f"  [Position Manager] Failed to persist PnL for trade {trade_id}: {e}")
```

Note: The function currently takes `server` param but opens its own DB connection. Need to ensure the `conn` and `c` cursors are available for the UPDATE. The function signature needs a minor refactor to expose the connection.

---

## Files to Change

| File | Lines | Change |
|------|-------|--------|
| `decider_run.py` | 1104 | Add `confidence = effective_conf` after `effective_conf` assignment |
| `decider_run.py` | 1112 | Change to `confidence -= min(trap_penalty, 25)` |
| `decider_run.py` | 1129 | Change to `penalty = min(int(regime_conf * 0.4), 25)` |
| `decider_run.py` | 1192, 1195, 1208 | Change `effective_conf >=` to `confidence >=` |
| `decider_run.py` | ~1104 | Add confidence floor: `if sig_conf >= 90: confidence = max(confidence, 70)` |
| `ai_decider.py` | SOURCE_WEIGHTS dict | Update vel-hermes, hzscore, pct-hermes weights |
| `position_manager.py` | ~1785 | Add SQL UPDATE to persist pnl_pct to DB |

---

## Testing / Validation

1. **BUG 1 fix**: Run `_run_hot_set()` with a signal that triggers `trap_penalty > 0` — should not NameError
2. **BUG 2 fix**: Verify that penalized `confidence` is used in threshold comparison — add debug log
3. **BUG 3 fix**: Query DB for an open position before/after running `refresh_current_prices()`:
   ```sql
   SELECT token, pnl_pct, current_price FROM trades WHERE status='open';
   ```
4. **Regression**: Existing APPROVED signals in DB should not be affected

---

## Risks & Tradeoffs

- **Risk**: Changing penalty logic could alter approval outcomes for tokens currently in hot-set. Monitor first few cycles.
- **Risk**: Capping penalties at 25pts means high-conviction counter-regime signals that previously leaked through (due to bug) will now be blocked. Net positive but could reduce trade frequency.
- **Tradeoff**: vel-hermes boost (1.0→1.2) may increase SHORT entries. Short data shows +5.59% avg — worth trying but watch for regime_fit.
- **Open Question**: Should the confidence floor apply before or after all penalties? (Before — floor is for base conviction only.)

---

## Open Questions for T

1. Should we also address the `pct-hermes` suppression issue (0.6→0.8)? It enters hot-set at 69-99% before penalties, suggesting it's not the primary problem.
2. For the `vel-hermes` SHORT boost — should this apply only in certain regimes or be unconditional?
