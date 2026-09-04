## Error Alerts — 2026-09-04 17:22 UTC
- **[WARN]** (4x/1h, 426 total): `signal_compactor: timed out` — compactor completes in ~1s but subprocess timeout hit intermittently. Likely OS scheduling delay, not logic bug.
- **[WARN]**: Disk at 84% (94G/118G) — pipeline.log is 86MB. Recommend compressing old logs.
- **[INFO]**: 0 open trades, system flat. Win rate 54% today (-1.85 USDT).

## Error Alerts — 2026-09-04 18:22 UTC
- **WARN** (1x): `signal_compactor: timed out` at 18:17 — recovered on next cycle, no restart needed
- **WARN**: Disk at 84% (19G free) — monitor for growth, compress logs if >85%

## Error Alerts — 2026-09-04 21:22 UTC
- **WARN** (1x): `disk usage 84%` — approaching 85% threshold, 18GB free on 118GB disk
- **INFO**: `prices.db empty` — 0 bytes, prices stored in candles.db (889MB) instead

## Error Alerts — 2026-09-04 22:22 UTC
- **WARN** (repeating): `z_tier check failed: name 'z_score' is not defined` — `decider_run.py:3082` referenced `z_score` from `_run_hot_set()` scope but was in `run()` scope. **AUTO-FIXED**: changed to `sig.get('z_score', 0.0)`.
- **WARN**: Disk at 84% (94G/118G) — 18GB free. pipeline.log=90MB, 15m_regime.log=50MB. Close to 85% threshold.
- **INFO**: Market deeply NEUTRAL (105/106 tokens). Only DASH has LONG_BIAS. 1 signal in last hour, 0 open trades.
- **AUTO-FIX LOG**: [22:22] health_monitor: Auto-fixed NameError in decider_run.py — z_score variable scope mismatch between _run_hot_set() and run(). Changed line 3082 to use sig.get('z_score', 0.0).
