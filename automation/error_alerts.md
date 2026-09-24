## Error Alerts — 2026-09-23 23:45 UTC
- **[WARN]** (1x): `signal_compactor: timed out (killed after 60.1s)` at 23:38:02
- **AUTO-FIX**: None needed — recovered on next pipeline cycle (23:44:05, 2.1s). Transient LLM timeout, not a recurring failure.
- **[WARN]** (1x): Disk at 84% (19G free of 118G). Approaching 85% threshold.
- **AUTO-FIX**: Monitoring only. If it crosses 85%, compress old logs or run `find /root/.hermes/logs -name "*.log" -mtime +7 -exec gzip {} \;`.

## Error Alerts — 2026-09-24 00:45 UTC
- **WARN** (8x): `signal_compactor: timed out (killed after 60.1s)` — compactor slow, 8 timeouts in 2h
- **WARN**: `regime_5m.json` is empty `{}` — no regime data available
- **WARN** (6x): Phantom trades (PnL < 0.01%) — dust from breakeven exits
- **WARN**: Disk at 84% (19G free) — monitor, compress logs at 85%
- **WARN**: Hotset empty — 0 signals survived compaction, pipeline idle
- **INFO**: Pipeline running, all 65 timers active, services healthy
