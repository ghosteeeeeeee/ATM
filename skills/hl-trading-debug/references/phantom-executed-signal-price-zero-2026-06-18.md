# Phantom EXECUTED Signal — price=0.0 Investigation (2026-06-18)

## Symptom
ENS and 0G show `decision=EXECUTED` in signals DB but zero trades in PostgreSQL and zero positions on Hyperliquid. Guardian marked them "executed" but nothing actually happened.

## Key Finding
Signals had `price=0.0` written at signal time. Guardian's batch mirror uses `prices.get(token)` (current market price) not the signal's price field. Trades may have:
1. Filled at market but at bad levels (immediately hit hard stop)
2. Been orphaned in a race condition between guardian batch and per-trade fallback

## Evidence from signals DB
```
ENS SHORT: price=0.0 → decision=EXECUTED, executed=0, no DB trade
0G SHORT: price=0.0 → decision=EXECUTED, executed=0, no DB trade
TIA LONG: price=0.39493 (valid) → decision=EXECUTED, executed=1 (real trade placed)
```

The `price=0.0` signals all have `executed=0` — guardian marked `decision=EXECUTED` but the `executed` flag (meaning "trade actually placed on HL") is 0. The guardian's `mark_signal_executed()` uses `decision='EXECUTED'` when it tries to mirror, but the actual HL fill may have failed silently.

## Related
- `signals/rs.py` — RS signal generator (writes price=0.0 when price fetch is stale/missing)
- `hl-sync-guardian.py` — Batch mirror path that uses current prices, not signal prices
- `signal_schema.py` — `mark_signal_executed()` with `decision='EXECUTED'` vs `decision='SKIPPED'`
