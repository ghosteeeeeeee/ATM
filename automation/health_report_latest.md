# Health Report — 2026-10-05 22:48 UTC

PIPELINE: OK
- Status: running (cycle #230259+, rc=0 every step)
- Signals (1h): 80 generated (signals table); 2 outcomes logged
- Trades: 5 open / 6 max (portfolio source of truth); 29 closed today, net -$0.85, 58.6% WR (17/29)
- Errors: 0 Traceback/CRASH, 0 `database is locked` in last 30m

MARKET:
- Regime: LONG_BIAS — 45 LONG / 13 SHORT / 64 NEUTRAL (ts 22:45)
- Speed: 53.1% tokens ≥ 50th percentile (128/241)

SYSTEM:
- Timers: 3/3 active (pipeline 15s, price-collector 3s, 1m-candle 1m43s ago)
- Disk: 83% used (under 85% WARN)
- Prices: 85 tokens, latest candle 1.3 min old, prices.json 1.8 min
- Phantom atr_sl_hit (|pnl|<0.01%): 0
- hl-sync-guardian: active
- candles.db writers: 3 normal pipeline processes, no stuck lock

AUTO-FIXES APPLIED:
- Disabled `hermes-coding-mcp.service` — crash-looping (restart #743,336) on missing `run_mcp_server.py`. Non-trading path; left inactive.

ALERTS:
- Non-critical failed units: better-coder, bug-hunter, git-release (unchanged, not on trading path)
- Stale 0-byte `/root/.hermes/data/trades.json` (Apr 27) — dashboard uses `/var/www/hermes/data/trades.json` (healthy)
- Disk 83% approaching 85% threshold — compress old logs if it climbs
