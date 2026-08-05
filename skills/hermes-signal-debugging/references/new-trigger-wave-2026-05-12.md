# New Triggers (2026-05-12)

## Signal Fire Rate Anomalies

- "only accel-300 and rs fire — everything else is 0"
- "15 signal modules listed but none producing signals"
- "ma_cross not firing even though it has signals"
- "pct-hermes hwave hzscore mtf-macd not firing"
- "short signals not firing — where are the shorts"
- "_run_signal re-imports module looking for run attr"
- "signals_runner skips scan_* only modules"
- "all 22 approved tokens blocked by WR gate"
- "hot-set shows signals but decider_run opens zero trades"
- "more live trades being opened — regime filtering too tight"

## Root Causes Captured

See `references/run-signal-missing-run-attr-bug.md` — `_run_signal` in `signals/__init__.py` does `getattr(mod, 'run', None)` on re-imported modules. Most signal modules only export `scan_*` functions, not `run()`, so 15 modules silently produce zero signals.

Also `references/postgresql-wr-filter-blindness.md` — WR filter in signal_compactor reads PostgreSQL (0 closed trades) instead of archive SQLite — causing all 22 tokens to fail WR gate.

See `references/decider-run-regime-disabled-2026-05-11.md` — `_get_regime_1m()` exists but is commented out in decider_run.py.