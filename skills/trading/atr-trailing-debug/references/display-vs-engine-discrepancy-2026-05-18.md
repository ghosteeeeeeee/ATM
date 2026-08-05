# Display vs Engine Discrepancy — TPSL Engine Is Correct (2026-05-18)

## Symptom

Displayed SL/TP values appear wrong (e.g., SNX SHORT: display shows `SL=$0.3042` at entry `$0.3034`), but the TPSL pipeline log shows the correct ATR-computed values (`SL=0.305423, TP=0.296380`).

| Source | SNX SHORT Entry | SL | TP |
|--------|-----------------|----|----|
| TPSL log (correct) | $0.303450 | $0.305423 (+0.65%) | $0.296380 (-2.32%) |
| Displayed | $0.3034 | $0.3042 (+0.26%) | ??? |

The TPSL engine `compute_atr_sl_tp()` in `tpsl_utils.py` is **mathematically correct**. The SHORT side sign logic is correct (SL above entry, TP below entry). The discrepancy is in the **display/messaging path**.

## Root Cause

Two separate code paths produce SL/TP values:

### Path A — ATR Engine (CORRECT)
```
position_manager._collect_atr_updates()
  → tpsl_utils.compute_atr_sl_tp()
  → _persist_atr_levels() → PostgreSQL
  → [TPSL] pipeline log
```
Output: `SL=0.305423, TP=0.296380` for SNX SHORT. Correct in every respect.

### Path B — get_trade_params() Fallback (WRONG for display)
```
decider_run / guardian / notification layer
  → position_manager.get_trade_params() (line ~1875)
  → If ATR lookup fails or called outside full cycle:
    → SL = entry * (1 + SL_PCT_FALLBACK=0.015)  = 0.3034 * 1.015 = 0.3080
    → TP = entry * (1 - TP_PCT_FALLBACK=0.08)   = 0.3034 * 0.92  = 0.2791
```
The fallback values (1.5% / 8%) are applied directly to entry without going through the ATR engine. If `get_trade_params()` is called for display without a valid ATR token context, it returns these fallbacks.

## Diagnostic Steps

1. **Always check the TPSL pipeline log first** — `[TPSL]` entries show the actual ATR-computed values:
   ```bash
   grep '\[TPSL\].*SNX' /root/.hermes/logs/pipeline.log | tail -5
   ```
   The TPSL log is the source of truth, not the displayed SL/TP in trade UIs.

2. **Check if the display is reading from DB or computing independently:**
   ```python
   # TPSL engine writes here:
   # PostgreSQL trades.stop_loss, trades.target (via _persist_atr_levels)
   
   # Display may read from DB directly or call get_trade_params() independently
   # If get_trade_params() has no valid ATR context, it uses fallback
   ```

3. **Verify the ATR engine ran for this trade:**
   ```python
   import psycopg2
   conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres', password='Brain123')
   cur = conn.cursor()
   cur.execute("SELECT token, direction, entry_price, stop_loss, target, atr_managed FROM trades WHERE token='SNX' AND status='open'")
   print(cur.fetchone())
   ```
   If `atr_managed=TRUE`, the ATR engine has claimed this trade. If `FALSE`, the fallback SL/TP from entry time persists.

## Fix

Ensure all display/notification paths read SL/TP from **PostgreSQL** (after ATR engine has written them), not from `get_trade_params()` which has its own fallback path.

The `get_trade_params()` function is for **trade opening** (initial SL/TP at entry), NOT for trailing updates. It uses `SL_PCT_FALLBACK=0.015` and `TP_PCT_FALLBACK=0.08` as initial values — these are correct at open time but stale for display.

## Key Distinction

| Function | Purpose | Fallback |
|----------|---------|----------|
| `tpsl_utils.compute_atr_sl_tp()` | Trailing SL/TP each cycle | SL=1.5%, TP=8% (if ATR unavailable) |
| `position_manager.get_trade_params()` | Initial SL/TP at trade open | SL=1.5%, TP=8% (hardcoded) |

**Never use `get_trade_params()` output as the "current" SL/TP for an established trade.** It has no knowledge of trailing, phase, or peak price.

## Verification Commands

```bash
# Check TPSL log for correct ATR-computed values
grep '\[TPSL\].*SNX' /root/.hermes/logs/pipeline.log | grep -oE 'SL=[0-9.]+ TP=[0-9.]+' | tail -3

# Check what PostgreSQL has (should match TPSL log if atr_managed=TRUE)
python3 -c "
import psycopg2, json
conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres', password='Brain123')
cur = conn.cursor()
cur.execute(\"SELECT token, direction, entry_price, stop_loss, target, atr_managed FROM trades WHERE token='SNX' AND status='open'\")
row = cur.fetchone()
if row:
    print(f'Token: {row[0]} {row[1]}')
    print(f'Entry: ${row[2]:.6f}')
    print(f'SL: ${row[3]:.6f} ({((row[3]/row[2])-1)*100:+.2f}%)')
    print(f'TP: ${row[4]:.6f} ({((row[4]/row[2])-1)*100:+.2f}%)')
    print(f'atr_managed: {row[5]}')
"
```
