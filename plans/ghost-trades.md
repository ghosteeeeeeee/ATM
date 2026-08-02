# Ghost Trades — SUI Instant Closure Root Cause

## Context
SUI SHORT opened 2026-05-17 02:44:07, closed 02:44:12 (5 seconds), close_reason=atr_sl_hit.
PostgreSQL `brain.trades` shows: entry=1.0509, stop_loss=1.0070, target=0.9900, exit=1.05165, pnl=-0.0714%.

The SL at $1.0070 is ~4.18% below entry for a SHORT. This is not a normal ATR floor value.

## Questions to Answer

1. **Where did stop_loss=1.0070 come from?**
   - ATR-based SL for SUI SHORT at $1.0509 should be ABOVE entry (short SL is above entry price)
   - For a 10X leverage SHORT, reasonable SL is ~0.5-1.5% above entry = ~$1.056-$1.067
   - $1.007 is 4.18% below entry — wrong direction entirely
   - Was this set by position_manager._collect_atr_updates()? By decider_run execute_trade()? Something else?

2. **Why did atr_sl_hit fire at exit=1.05165 when SL was at 1.007?**
   - 1.05165 is NOT ≥ 1.0070, so SL should NOT have triggered
   - Unless: price briefly spiked to ≥$1.007 on HL feed (liquidation sweep, data gap)
   - Or: the SL check logic itself has a bug for SHORT positions

3. **Did the trade use pump-mode (fixed SL=1.5%) or ATR-mode (deferred SL)?**
   - Source string 'zscore-pump-' suggests pump-mode should apply
   - But $1.0070 is NOT a pump-mode SL (pump-mode SHORT SL would be entry*1.015 = $1.0667)
   - This implies either: pump-mode was bypassed, or SL was overwritten by ATR engine before first cycle

## Investigation Steps

- [ ] 1. Read decider_run.py execute_trade() — trace the exact SL/TP assignment for SUI trade
      - Which branch (pump vs non-pump) was taken?
      - Is there a code path that could produce SL=1.007?
      - Log line 1849 should show actual SL/TP values at execution

- [ ] 2. Read position_manager.py _collect_atr_updates() and check_atr_hits()
      - How is ATR SL computed for SHORT positions?
      - Is there a bug where SHORT SL is set below entry instead of above?
      - Check the peak-price tracking for SHORT — does it use lowest_price correctly?

- [ ] 3. Cross-reference hl-sync-guardian log around 02:44
      - Was there a price spike to $1.007+ on Hyperliquid feed?
      - Did guardian log any anomalies?

- [ ] 4. Query signals_hermes_runtime.db for the SUI signal record
      - What exact timestamp was the signal created vs trade opened?
      - Any gap between signal time and guardian price sync?

- [ ] 5. Check candles_1m for SUI around ts=1778985600 (02:40 window)
      - What was the actual price movement at 02:44?
      - Was there a wick/spike to $1.007 that closed immediately?

## Root Cause Hypothesis
The $1.007 SL suggests either:
- A data/pipeline error where price reference was inverted for SHORT (should be above entry, not below)
- An ATR calculation bug for SHORTs that produced an invalid floor value
- A price spike on HL that touched $1.007 momentarily triggering a correctly-set SL

## Files to Examine
- `/root/.hermes/scripts/decider_run.py` — execute_trade(), SL/TP assignment
- `/root/.hermes/scripts/position_manager.py` — _collect_atr_updates(), check_atr_hits()
- `/root/.hermes/scripts/hl-sync-guardian.py` — price sync and anomaly detection
- `/var/www/hermes/logs/trading.log` — full EXEC log line for SUI trade
- `/root/.hermes/data/signals_hermes_runtime.db` — signal records
- `/var/www/hermes/data/candles.db` — SUI 1m candles around 02:44

## Out of Scope
- zscore_pump.py signal logic (already verified correct)
- signal_compactor confluence logic (already verified passed)
- ZSCORE_PUMP_USE_TUNER flag (not relevant to SL bug)