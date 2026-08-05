# HL_MIN_NOTIONAL Rejection — Pipeline Working But Trades Rejected (2026-05-21)

## Symptom
Pipeline log shows:
```
EXEC: brain.py trade add BRETT long 3.5 0.007585... [--real]
❌ REJECTED: BRETT LONG — amount_usdt=3.5 < HL_MIN=11.0 (would fail on HL)
⚠️ ROLLBACK FAILED: sig#1023373 already claimed by another process
```

- `signals_hermes_runtime.db`: APPROVED rows exist for BRETT and MERL
- `hotset.json`: 2 valid entries (BRETT:LONG, MERL:LONG) with 2-source combos, updated ~51s ago
- `decider_run`: fires `execute_trade()` correctly
- `brain.py`: rejects at `HL_MIN_NOTIONAL_USDT` gate (line 432)
- After rejection: ROLLBACK fails → signal left in claimed-but-not-executed state

## Root Cause
```
hermes_constants.py:248: DEFAULT_TRADE_SIZE_USDT = 3.5
hermes_constants.py:252: HL_MIN_NOTIONAL_USDT     = 11.0

brain.py:432: if effective_amount < HL_MIN_NOTIONAL_USDT → REJECTED
```

Every hot-set trade uses the default size (3.5 USDT). Hyperliquid's minimum notional is ~$11.
The position value for BRETT at $0.0076 × 3.5x leverage ≈ $12.25 notional → fee ≈ $0.003 < $11 minimum.

## Fix
```python
# hermes_constants.py:248
DEFAULT_TRADE_SIZE_USDT = 11.0  # was 3.5, must meet HL minimum
```

Or higher to provide buffer above minimum.

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

The pipeline was NOT broken. The signal flow was correct. The block was at the
Hyperliquid minimum notional gate in brain.py.

## ROLLBACK Failure (Secondary Bug)
After brain.py REJECTS, `executed=1` (claimed) state is set but trade fails → rollback
attempted → fails with "already claimed." This leaves the signal in inconsistent state,
blocking retry for same token+direction.

Fix needed in brain.py or decider_run: properly restore `executed=0` on rejection.

## Investigation Pattern That Found the Bug
1. Assumed the bug was DB-level (APPROVED rows missing) — WRONG
2. Traced `_live_zscore` bug — real but not causing rejection
3. Traced zscore propagation fix — working correctly
4. Eventually read brain.py grep output showing `amount_usdt=3.5 < HL_MIN=11.0` — FOUND IT

**Rule:** When pipeline shows signals entering hotset.json and decider_run firing but no
trades execute, check brain.py's HL-level rejection gates, not the DB-level signal flow.
The DB and pipeline were working; the block was at Hyperliquid API level.

## Related Constants Audit
```bash
grep -n "DEFAULT_TRADE_SIZE\|HL_MIN\|min_notional\|min_trade" /root/.hermes/scripts/hermes_constants.py
```