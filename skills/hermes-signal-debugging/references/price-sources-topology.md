# Hermes Price Data Sources — Topology Reference

**Last verified:** 2026-05-18

## The Two DBs

| DB | Path | Table | Source | Freshness |
|----|------|-------|--------|-----------|
| `signals_hermes.db` | `/root/.hermes/data/` | `price_history` | HL allMids via `upsert_prices_from_allMids()` (price_collector.py, every ~60s) | **Most fresh** — sub-minute timestamps |
| `signals_hermes.db` | `/root/.hermes/data/` | `latest_prices` | Same as above, upserted every collection cycle | Current price |
| `candles.db` | `/root/.hermes/data/` | `candles_1m` | Binance candles via `_fetch_binance_candles()` (price_collector.py) | Minute-aligned, ~40s older than price_history |

## Typical Freshness (2026-05-18)

- `price_history` BTC latest: ts=1779126634 (~43s old)
- `candles_1m` BTC latest: ts=1779126480 (closed bar, ~81s old + 1 bar gap)
- `latest_prices` BTC: same ts as `price_history` latest, updated every collection cycle

## Critical: zscore_pump.py Does NOT Use candles.db

`zscore_pump._get_1m_prices()` reads from `signals_hermes.db → price_history`. It does NOT read from `candles.db → candles_1m`.

Confusion arises because:
1. The file comments say "candle data" — but refer to `price_history` (1m closes)
2. `candles_1m` in `candles.db` is NOT the source for any signal; it's used by `fetch_binance_candles()` for other purposes (macd_rules, etc.)
3. Both DBs have a `candles_1m` table with the same schema — but different content

## Which Signal Uses Which Source

| Signal | Current Price Source | Historical Lookback Source |
|--------|---------------------|---------------------------|
| zscore_pump | `latest_prices` (via `prices_dict`) | `signals_hermes.db → price_history` |
| accel_300 | `latest_prices` (via `prices_dict`) | `signals_hermes.db → price_history` |
| Most other signals | `get_all_latest_prices()` → `latest_prices` | `get_price_history()` → `price_history` |
| macd_rules | `get_latest_price()` | `candles.db → candles_1m` (Binance OHLCV) |

## Common Debugging Traps

1. **Assuming candles.db is fresher** — it's not, it's ~40s older
2. **Assuming signals read from candles_1m** — most signals read from `price_history`
3. **Checking candles.db for price data** — `price_history` in `signals_hermes.db` is the canonical source for signals
4. **price_collector writes to BOTH** `signals_hermes.db` (price_history/latest_prices) AND `candles.db` (candles_1m) — but the write cadence differs

## Key Code Locations

- `signal_schema.py:upsert_prices_from_allMids()` — writes to `price_history` + `latest_prices`
- `price_collector.py` — orchestrates collection, writes to both DBs
- `signal_schema.py:get_price_history()` — reads from `signals_hermes.db → price_history` (NOT candles.db)
- `signal_schema.py:get_all_latest_prices()` — reads from `signals_hermes.db → latest_prices`
- `zscore_pump._get_1m_prices()` — direct SQLite read from `signals_hermes.db → price_history`
