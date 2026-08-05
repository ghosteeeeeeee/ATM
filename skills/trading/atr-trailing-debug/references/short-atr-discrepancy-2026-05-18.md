# SHORT ATR TP/SL Discrepancy — Two Separate ATR Systems (2026-05-18)

## Symptom

TPSL pipeline log shows correct ATR-computed SL/TP for SHORT trades, but `trades.json` (and thus the display layer) holds different values. ETH LONG is correct (exact match). All SHORT trades are wrong.

| Trade | Direction | Display SL | TPSL SL | Display TP | TPSL TP |
|-------|-----------|------------|---------|------------|---------|
| ETH | LONG | 2111.544196 | 2111.544196 | 2147.693492 | 2147.693492 |
| SNX | SHORT | 0.308540 | 0.305423 | 0.296380 | 0.298751 |
| UNI | SHORT | 3.492564 | 3.423800 | 3.354926 | 3.354926 |
| SKY | SHORT | 0.070700 | 0.069178 | 0.067914 | 0.067914 |
| STRK | SHORT | 0.041168 | 0.040814 | 0.039546 | 0.040125 |

For SHORT trades: **display SL is ALWAYS higher** (further from current) than TPSL output, and **display TP is often lower** (different from TPSL).

## Root Cause: TWO Separate ATR Systems

### System A — Canonical ATR Engine (CORRECT)
```
position_manager._collect_atr_updates()
  → tpsl_utils.compute_atr_sl_tp()     # uses lowest_price/highest_price as anchor
  → _persist_atr_levels()              # writes to PostgreSQL
  → [TPSL] pipeline log                # correct values here
```
Produces: `SL = ref_price * (1 + eff_sl_pct)` for SHORT (anchor = lowest_price).

### System B — Legacy _dynSL / _dynTP (WRONG for display)
```
position_manager._compute_dynamic_sl()  # lines 1454-1493
position_manager._compute_dynamic_tp()  # lines 1496-1528
```
These compute SL/TP using `current_price` as anchor (not `lowest_price`/`highest_price`):
- `_dynSL()` SHORT: `current_price * (1 + ATR_SL_MIN)` where `ATR_SL_MIN = 0.005`
- `_dynTP()` SHORT: `current_price * (1 - effective_tp_pct)` where `effective_tp_pct = ATR_TP_MIN = 0.01` for established trades

For STRK: `_dynSL = 0.04093 * 1.005 = 0.041135` ≈ display `0.041168` ✓

**These functions are legacy dead code.** They are defined but never called from the main `_collect_atr_updates()` path. However, if ANY code path (guardian, notification, display) calls them instead of reading from PostgreSQL, it gets the wrong values.

## Why ETH LONG Works But SHORT Doesn't

Both systems happen to produce the same result for LONG when price has moved up (highest_price > entry → canonical is tight). For SHORT, `current_price` and `lowest_price` diverge significantly (e.g., SNX: current=0.306360 vs lowest=0.303300 = 1% gap), causing the two systems to produce meaningfully different values.

## Back-Calculated Reference Prices from Display SL

For SHORT trades where display SL ≠ TPSL SL, back-calculate which ref_price the display SL used:

```python
# For SHORT: display_SL = ref * (1 + 0.005) where ref = some price
# display_SL / 1.005 = implied reference price
# Compare to: lowest_price (canonical), entry_price, current_price

# SNX: display_SL=0.308540, lowest=0.303300, entry=0.303450, current=0.306360
# implied_ref = 0.308540 / 1.005 = 0.306407  → closest to current_price=0.306360
# canonical uses lowest=0.303300 → SL=0.303300*1.007=0.305423 (TPSL)

# UNI: display_SL=3.492564, lowest=3.400000, entry=3.433750, current=3.446850
# implied_ref = 3.492564 / 1.005 = 3.474790  → closest to current=3.446850
# canonical uses lowest=3.400000 → SL=3.400000*1.007=3.423800 (TPSL)

# SKY: display_SL=0.070700, lowest=0.068697, entry=0.069293, current=0.069293
# implied_ref = 0.070700 / 1.005 = 0.070348  → closest to current=0.069293
# canonical uses lowest=0.068697 → SL=0.068697*1.007=0.069178 (TPSL)
```

**Conclusion:** The display SL values for SHORT trades are consistent with `_dynSL()` using `current_price` as anchor, NOT `lowest_price`. The canonical engine (using `lowest_price`) is correct and produces tighter SLs. The display layer is reading from the wrong system.

## SNX TP Anomaly

SNX display TP = 0.296380 corresponds to `eff_tp_pct = 2.28%` (not 1.5% MIN or 1.0% ACCEL).

Possible sources:
1. `get_trade_params()` at open used `TP_PCT_FALLBACK=8%` path but with some adjustment
2. Some other fallback computation

The TPSL log shows `eff_tp=1.500%` (INIT floor applied correctly by canonical engine). The display TP is more aggressive (wider) than the canonical INIT floor allows — suggesting it was set at open time before the ATR engine's INIT floor was applied.

## Fix

The TPSL engine (`tpsl_utils.compute_atr_sl_tp`) is **mathematically correct**. The values written to PostgreSQL by `_persist_atr_levels()` are correct.

The display layer (`trades.json` written by `_update_trades_json_atr()` in guardian) is reading values that don't match PostgreSQL, OR PostgreSQL has wrong values for SHORT trades.

**Immediate action:** For any SHORT trade with a display SL/TP mismatch:
1. Query PostgreSQL directly: `SELECT stop_loss, target, highest_price, lowest_price FROM trades WHERE token='SNX' AND status='open'`
2. If PostgreSQL matches TPSL log (correct) but trades.json doesn't → guardian write path bug
3. If PostgreSQL matches trades.json (wrong) → `_persist_atr_levels()` not running or delta gate blocking it for SHORT

## Key Files

- `tpsl_utils.py:248-495` — `compute_atr_sl_tp()` — CANONICAL engine, CORRECT
- `position_manager.py:1454-1528` — `_dynSL()` / `_dynTP()` — LEGACY dead code, WRONG anchor
- `position_manager.py:1710-1749` — `_persist_atr_levels()` — writes canonical values to PostgreSQL
- `hl-sync-guardian.py:3433-3511` — `_update_trades_json_atr()` — reads from PostgreSQL, writes to trades.json

## Diagnostic Command

```python
import psycopg2
conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres', password='Brain123')
cur = conn.cursor()
cur.execute("""
    SELECT token, direction, entry_price, stop_loss, target, 
           highest_price, lowest_price, current_price, atr_managed
    FROM trades WHERE status='open' AND direction='SHORT'
""")
for row in cur.fetchall():
    token, direction, entry, sl, tp, hp, lp, cp, managed = row
    sl_pct = (sl/lp - 1)*100 if lp else None  # what eff_sl_pct was used
    tp_pct = (1 - tp/lp)*100 if lp else None  # what eff_tp_pct was used
    print(f"{token}: entry={entry}, lowest={lp}, current={cp}")
    print(f"  SL={sl} (implied eff_sl={sl_pct:.2f}% if ref=lowest)")
    print(f"  TP={tp} (implied eff_tp={tp_pct:.2f}% if ref=lowest)")
    print(f"  atr_managed={managed}")
    # Compare to TPSL log values
    # If sl_pct ≈ 0.50%: _dynSL with ATR_SL_MIN=0.5% using current_price
    # If sl_pct ≈ 0.70%: canonical with ACCEL floor using lowest_price
```