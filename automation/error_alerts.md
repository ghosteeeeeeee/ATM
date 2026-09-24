## Error Alerts — 2026-09-23 23:45 UTC
- **[WARN]** (1x): `signal_compactor: timed out (killed after 60.1s)` at 23:38:02
- **AUTO-FIX**: None needed — recovered on next pipeline cycle (23:44:05, 2.1s). Transient LLM timeout, not a recurring failure.
- **[WARN]** (1x): Disk at 84% (19G free of 118G). Approaching 85% threshold.
- **AUTO-FIX**: Monitoring only. If it crosses 85%, compress old logs or run `find /root/.hermes/logs -name "*.log" -mtime +7 -exec gzip {} \;`.
