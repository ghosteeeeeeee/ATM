# SUI SHORT — 5s Close Root Cause (2026-05-17)

## What Happened

```
SUI SHORT opened 02:44:07, closed 02:44:12 (5 seconds)
entry:   $1.0509
stop_loss: $1.0070   ← WRONG: 4.18% ABOVE entry (should be BELOW)
target:  $0.9900
exit:    $1.05165
pnl_pct: -0.07%
close_reason: atr_sl_hit
signals: rs-r210,rs-r99,zscore-pump-
confidence: 93.7%, leverage: 5×
```

## Root Cause: SL Was Computed Wrong, Not Stale Prices

The SL of $1.0070 is **4.18% above the entry price** ($1.0509). For a SHORT:
- SL should be **below** entry (higher price = worse for SHORT)
- A 4.18% adverse move on 5× leverage = 20%+ loss on equity

But the exit was only **+0.07%** from entry — nowhere near $1.007. The SL was never actually hit at $1.05165.

**Two possible explanations:**
1. The SL was set incorrectly at entry (bad ATR computation at position open)
2. Price data showed SUI at $1.007 briefly (HL data gap) — guardian recorded it as `atr_sl_hit`

## Signal Was Correct

- `zscore-pump-` fired with z=-1.801 (SHORT direction, which is correct for negative z after the flip)
- Confluence: rs-r210 + zscore-pump- (2 unique types) — passed
- Signal timestamp: 02:44:03, price in signals_hermes.db was NOT stale (was 144s AFTER signal, meaning fresh)

## Diagnosis Steps Used

1. `signals_hermes_runtime.db` — checked `executed=1` signals for SUI to confirm dual-entry prevention worked
2. PostgreSQL `brain.trades` — confirmed trade in DB with wrong SL ($1.007 for SHORT)
3. `candles_1m` — SUI has data in candles.db (not token issue)
4. `price_history` in signals_hermes.db — confirmed freshness at signal time
5. Confirmed both signals (02:41:13 and 02:44:03) were `executed=1` in DB

## Key Files

- `position_manager.py` — `_collect_atr_updates()` for SL computation
- `tpsl_utils.py` — `compute_atr_sl_tp()` sole ATR authority
- `signals/zscore_pump.py` — staleness gate (was incorrectly blamed)
- `decider_run.py` — pump mode SL/TP using `PUMP_SL_PCT/PUMP_TP_PCT` from signal_gen.py

## PUMP_MODE Note

zscore-pump- uses PUMP_SL_PCT=1.5%, so SL for SHORT should be: `entry × (1 + 0.015)` = $1.0667. But the actual SL was $1.007 — this is NOT a pump-mode SL. The SL came from ATR computation, not pump-mode fixed SL.

## Related Prior Bug

SUI LONG (2026-05-16): SL=$1.0923 above entry=$1.064 — `compute_atr_sl_tp` new-trade gate bypassed when `highest_price > entry` from DB init. Pattern matches: SL above entry for a position that should have SL below entry.

## See Also
- `references/sui-ghost-trade-fix-2026-05-16.md` — prior SUI ghost trade (LONG SL above entry)
- `references/fil-short-initial-sl-bug-2026-05-15.md` — FIL SHORT wrong initial SL
- `references/atr-tp-sl-authority-2026-05-15.md` — tpsl_utils as sole ATR authority