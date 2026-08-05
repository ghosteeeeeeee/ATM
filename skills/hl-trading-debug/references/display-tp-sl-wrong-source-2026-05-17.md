# Display vs DB Mismatch — Wrong TP/SL Values (2026-05-17)

## Symptom
Display shows TP/SL values for tokens (ETH, AVAX, PEOPLE, XMR) that don't match PostgreSQL or trades.json. PostgreSQL has completely different open positions (STBL, MOVE, ZEN, STRK, BSV) with correct ATR values.

## Root Cause
**The display was reading from a different data source than PostgreSQL/trades.json.**

PostgreSQL and trades.json had CORRECT values (position_manager overwrites decider_run's pump-mode values within 1 cycle). The display was reading from somewhere else entirely.

## Key Diagnostic Steps

1. **Query PostgreSQL directly** — always start here as source of truth:
```bash
psql -h /var/run/postgresql -U postgres -d brain -t -c "
SELECT token, direction, entry_price, stop_loss, target, atr_managed
FROM trades WHERE status='open' ORDER BY open_time;"
```

2. **Compare with trades.json**:
```bash
cat /var/www/hermes/data/trades.json | python3 -c "
import json, sys
d = json.load(sys.stdin)
for t in d.get('open', []):
    print(t['coin'], t['direction'], 'ep=%s sl=%s tp=%s' % (t['entry_price'], t['sl'], t['tp']))
"
```

3. **Check your display's actual data source** — don't assume it reads from PostgreSQL or trades.json. Look at:
   - API endpoint being called (hermes-trades-api.py, custom dashboard, HL itself)
   - WebSocket subscriptions
   - Redis/cache layers
   - HL portfolio display (which shows HL-side TP/SL, not Hermes DB values)

4. **Verify the display shows HL positions** — if the display is reading directly from HL's `/api/v1/accountSummary` or similar, those are HL-side TP/SL orders. Hermes brain.py writes TP/SL to PostgreSQL but those may not sync to HL for display purposes.

## Two Separate TP/SL Systems

| System | Where | Values |
|--------|-------|--------|
| HL TP/SL orders | Hyperliquid exchange | Set by brain.py Step 5 or HL-side |
| PostgreSQL TP/SL | Hermes brain DB | Set by decider_run (pump-mode) then overwritten by position_manager (ATR) |

Display reading from HL shows values from brain.py Step 5 (pump-mode fixed 1.5%/2.5%), not the corrected ATR values from position_manager.

## The Actual Bug (Decider_Run Pump Mode)
`decider_run.py` lines 614-619 set fixed PUMP_SL_PCT=1.5%, PUMP_TP_PCT=2.5% for signals with `source` containing `pump-`. These write to PostgreSQL as initial values. position_manager then overwrites with correct ATR values within 1 cycle.

If display reads from a source that isn't updated by position_manager, it shows stale pump-mode values.

## Resolution
1. PostgreSQL and trades.json had correct ATR values (STBL/MOVE/ZEN/STRK/BSV)
2. Display showed ETH/AVAX/PEOPLE/XMR/BSV with pump-mode values (1.5% SL)
3. **Fix**: Identify and correct the display's data source — it was NOT reading from PostgreSQL