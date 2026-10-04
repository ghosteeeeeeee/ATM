# Health Report — 2026-10-04 13:46 UTC

## Pipeline: OK
- Status: **active** (hermes-pipeline.service), LIVE run 13:46:00 rc=0
- Position manager: healthy, rc=0 every cycle, 3/6 slots used
- Signals (1h): **82** generated
- Trades: **3 open** | **34–35 closed today** | PnL **-12.8% → -15.4%** (source of truth = position_manager)
- Errors in 30m: **0** (no Traceback/CRASH/exception)

## Market
- Regime: **LONG_BIAS** (34 LONG / 6 SHORT / 77 NEUTRAL, 117 tokens, ts 13:45)
- Speed: **53.5%** tokens ≥ 50th percentile (129/241, updated 13:46:22)

## System
- Services: pipeline **active**, hl-sync-guardian **active**, price-collector **active**
- Core timers firing: pipeline (1m), price-collector, signal-compactor, pump-hunter, 1m-candle, watchdog, coin-tracker, regime scanners
- Disk: **81%** used (under 85% threshold)
- Prices: fresh — regime_5m 1.7m, token_speeds 13:46:22
- Logs: 150M, no files >7d needing compression

## Auto-fixes applied
- None required. Pipeline healthy, prices fresh, disk under threshold, no crashes, signals flowing.

## Alerts
- **WARN** (known): `signal_outcomes` partial vs portfolio — use position_manager/trades.json for trade counts.
- **WARN** (known, non-trading-path): dead timers `hermes-atr-sl-updater.timer` (not-found), `hermes-regime-24h-check.timer` + `hermes-regime-transition-check.timer` (OnBootSec by design).
- **INFO**: 113/241 token_speeds have `is_stale=1` but updated_at is fresh — flag = no recent price move, not staleness.
- **INFO**: today's PnL -15.4% — trading performance, not system health.
