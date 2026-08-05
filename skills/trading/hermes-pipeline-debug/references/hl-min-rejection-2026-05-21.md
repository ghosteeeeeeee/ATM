# HL_MIN_NOTIONAL Rejection — Pipeline Working But Trades Rejected (2026-05-21)

## Symptom
Pipeline log shows:
```
EXEC: brain.py trade add BRETT long 3.5 0.007585... [--real]
❌ REJECTED: BRETT LONG — amount_usdt=3.5 < HL_MIN=11.0 (would fail on HL)
⚠️ ROLLBACK FAILED: sig#1023373 already claimed by another process
```

- `hotset.json`: 2 valid entries (BRETT:LONG, MERL:LONG) with 2-source combos
- `decider_run`: fires `execute_trade()` correctly
- `signals_hermes_runtime.db`: APPROVED rows exist for BRETT/MERL
- `brain.py`: rejects at `HL_MIN_NOTIONAL_USDT` gate (line 432)
- After rejection: ROLLBACK fails → signal stuck in claimed-but-not-executed state

## Root Cause
```
hermes_constants.py:248: DEFAULT_TRADE_SIZE_USDT = 3.5
hermes_constants.py:252: HL_MIN_NOTIONAL_USDT     = 11.0

brain.py:432: if effective_amount < HL_MIN_NOTIONAL_USDT → REJECTED
```

Every hot-set trade uses the default size (3.5 USDT). Hyperliquid's minimum notional is ~$11.
BRETT at $0.0076 × 3.5x leverage ≈ $12.25 notional → fee ≈ $0.003 < $11 minimum.

## Pipeline Flow (Confirmed Working 2026-05-21)
```
zscore_pump.py + rs.py → signals_hermes_runtime.db (MERGED PENDING rows)
     ↓
signal_compactor.py → PRESERVE-APPROVED-UPSERT → creates APPROVED DB rows
     ↓
decider_run.py → get_approved_signals() → queries DB APPROVED rows → fires trade
     ↓
brain.py → HL_MIN_NOTIONAL gate → REJECTED (if amount_usdt < 11.0)
```

The signal flow was FULLY WORKING. The block was at the HL minimum notional gate.

## Key Diagnostic Rule
When pipeline.log shows `EXEC: brain.py trade add` followed by `REJECTED: amount_usdt=X < HL_MIN=Y`:
- The signal/approval pipeline is working correctly
- The block is at brain.py's exchange-integration layer
- Fix: increase `DEFAULT_TRADE_SIZE_USDT` to meet `HL_MIN_NOTIONAL_USDT`

## Secondary Bug: ROLLBACK Failure
After brain.py REJECTS, `executed=1` (claimed) state is set but trade fails → rollback
attempted → fails with "already claimed." Leaves signal in inconsistent state,
blocking retry for the same token+direction.

## Fix
```python
# hermes_constants.py:248
DEFAULT_TRADE_SIZE_USDT = 11.0  # was 3.5, must meet HL minimum
```

## Audit Command
```bash
grep -n "DEFAULT_TRADE_SIZE\|HL_MIN\|min_notional\|min_trade" /root/.hermes/scripts/hermes_constants.py
```