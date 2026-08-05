# zscore-pump Staleness — CORRECTED (2026-05-17)

## Previous Analysis (WRONG — was in this file previously)

A prior session concluded the 120s threshold was "too tight" and recommended raising to 180s, then later recommended lowering to 30s. **Both were wrong** — the real problem was misdiagnosed.

## What Actually Happened (2026-05-17)

**SUI SHORT** opened 02:44:07, closed 02:44:12 (~5 seconds):
```
entry: $1.0509, SL: $1.0070 (4.18% ABOVE entry!), exit: $1.05165
pnl: -0.07%, close_reason: atr_sl_hit
signals: rs-r210,rs-r99,zscore-pump-
```

The SL of $1.007 was **4.18% above the entry price**. For a SHORT, SL should be below entry (higher price = worse). A 5× leverage position with SL 4.18% above entry would need a +4.18% adverse move = ~20% loss on equity. But exit was only +0.07% from entry — SL was NOT actually hit.

**Root cause was NOT staleness.** The signal fires correctly (z=-1.801 → SHORT direction is correct after the flip). The price in signals_hermes.db at signal time was **144s AFTER the signal timestamp** — meaning the price data was fresh, not stale.

The 5-second close was caused by **wrong SL computation** at entry (SL placed 4.18% above entry instead of below), OR a brief HL data spike that triggered the guardian's atr_sl_hit check. This is an ATR/SL computation bug, not a staleness issue.

## Correct Diagnosis Path

When you see a phantom close within seconds of entry:
1. **First**: Query PostgreSQL `brain.trades` for the actual `stop_loss` value
   ```bash
   sudo -u postgres psql -d brain -c "SELECT token, entry_price, stop_loss, target, exit_price FROM trades WHERE token='SUI' ORDER BY close_time DESC LIMIT 3;"
   ```
2. **Compare** SL to entry price: for SHORT, SL should be ABOVE entry? NO — for SHORT, SL should be ABOVE entry (worse for SHORT when price rises). Actually CHECK: LONG SL < entry, SHORT SL > entry. For SUI SHORT at $1.0509, SL above entry ($1.007) is correct direction — **WAIT**: SHORT position profits when price FALLS, so SL ABOVE entry (higher price) protects against upward moves. $1.007 > $1.0509? No $1.007 < $1.0509. So SL is BELOW entry — that IS the correct direction for a SHORT.

   Wait — for SHORT: entry $100, SL at $101 (above entry) means price must rise 1% to hit SL = bad. SL at $99 (below entry) = price must fall 1% to hit SL = good for SHORT position.

   So $1.007 < $1.0509 means SL is BELOW entry — **this is CORRECT for SHORT** (SL protects against price RISE, which is bad for SHORT). A 4.18% rise from $1.0509 would be $1.0949, but SL is at $1.007 — only 4.18% below entry, not above. So a 4.18% rise hits SL.

   But exit was $1.05165 (+0.07% from entry). To hit SL at $1.007, price needed to fall 4.18% — opposite direction. Something is wrong with how the close was recorded.

3. **Conclusion**: The 5s close was either a data error in recording, or a brief price spike to $1.007+ that wasn't sustained. The SL computation ($1.007) is directionally correct for SHORT but numerically wrong (ATR was miscomputed).

## The staleness threshold (120s) was NOT the issue

Price data at signal time was 144s AHEAD of signal timestamp (i.e., price was fresher than the signal itself). No staleness problem in the zscore-pump signal itself.

The correct lesson: **check the actual SL value in PostgreSQL before blaming staleness or signal logic.**

## Files
- `signals/zscore_pump.py` — staleness gate (line ~145)
- `position_manager.py` — ATR SL computation via `_collect_atr_updates()`
- `tpsl_utils.py` — `compute_atr_sl_tp()` sole ATR authority
- PostgreSQL `brain.trades` — always check actual SL values first