# Signal Debugging — Session Notes (2026-06-17)

## Post-Reboot Price Warmup
After a full system reboot with 20+ days downtime:
- `price_collector` only writes prices for tokens currently returned by HL `allMids`
- 148/230 tokens in `signals_hermes.db` haven't been updated since May 28 (~20 days old)
- Only 82 tokens have fresh data (updated within seconds)
- **Result**: signals_runner `[rs]` stale warnings for those 148 tokens — not bugs, expected behavior
- The system warms up organically as delisted tokens drop off and active tokens appear in `allMids`
- If backfill needed: fetch historical HL/Binance 1m candles into `signals_hermes.db` price_history

## Verifying Signal Flow (don't trust the pipeline log)
- `signals_runner` is backgrounded via `run_bg()` with `start_new_session=True` — fully detached
- Pipeline log shows "[signals_runner] forked as PID X" but output goes to pipeline.log separately
- **Direct verification**: `sqlite3 /root/.hermes/data/signals_hermes_runtime.db "SELECT token, signal_type, confidence, created_at, combo_key FROM signals ORDER BY id DESC LIMIT 10"`
- A signal reaching the DB with decision=PENDING means the signal generator works
- A hotset staying empty means the compactor confluence gate is blocking them

## Confluence Gate (not a bug)
- `signal_compactor.py` lines 571-589: requires 2+ unique signal types per combo_key
- Single-source signals (accel_300 alone, rs alone, etc.) stay PENDING → expire after 5 min
- With only 5 fast signals registered and most tokens stale, no two different signal types fire for the same token in the same window
- **This is correct behavior** — the system refusing to trade on single-source signals
- Fix: multiple signal types must fire for the same token+direction within 5 min (confluence)
