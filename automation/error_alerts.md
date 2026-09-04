## Error Alerts — 2026-09-04 17:22 UTC
- **[WARN]** (4x/1h, 426 total): `signal_compactor: timed out` — compactor completes in ~1s but subprocess timeout hit intermittently. Likely OS scheduling delay, not logic bug.
- **[WARN]**: Disk at 84% (94G/118G) — pipeline.log is 86MB. Recommend compressing old logs.
- **[INFO]**: 0 open trades, system flat. Win rate 54% today (-1.85 USDT).

## Error Alerts — 2026-09-04 18:22 UTC
- **WARN** (1x): `signal_compactor: timed out` at 18:17 — recovered on next cycle, no restart needed
- **WARN**: Disk at 84% (19G free) — monitor for growth, compress logs if >85%
