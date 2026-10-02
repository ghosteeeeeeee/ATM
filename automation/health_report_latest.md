# Health Report — 2026-10-02 15:49 UTC

## Pipeline: OK
- Status: completed LIVE at 15:45:27 (oneshot+timer — `inactive` between runs is normal)
- Signals (1h): 134 generated (signal DB)
- Trades: 2 open (BTC LONG, JUP LONG per position manager; trades.json shows 1 open BTC), 51 closed today
- PnL today: +29.28% (pipeline portfolio line)
- Errors (30min): 5x psycopg2 UnboundLocalError in rate-limit check (FIXED); 0 Tracebacks; 0 CRASH

## Market
- Regime: SHORT_BIAS — 0 LONG / 5 SHORT / 112 NEUTRAL (regime_5m.json, 15:45:04)
- Speed: 128/241 tokens ≥50th percentile (53.1%)

## System
- Timers: 30+ hermes-* active, all firing on schedule (pipeline every 1min, last pass 15:45)
- Services: hermes-pipeline inactive (normal), hermes-hl-sync-guardian active
- Disk: 86% used (95G/118G, 17G free) — WARN
- Prices: 86 tokens, updated 21s ago — fresh
- Failed non-critical units: 12 (LLM jobs: better-coder, bug-hunter, ceo, daily-orchestrator, git-release, mtf-macd-tuner, signal-reporter, summarizer, trading-checklist, upgrade-implementer, weather-station-api)

## Auto-Fixes Applied
1. **decider_run.py psycopg2 UnboundLocalError** — removed shadowing `import psycopg2` at line 3660 inside `run()`. Root cause: local import made `psycopg2` function-scoped, breaking rate-limit check (fail-open — 15s entry gap disabled) and losers WR hard-block (fail-closed — over-blocking LOSERS tokens). Module-level import at line 8 now resolves. py_compile OK. Takes effect next pipeline run.
2. Journal vacuum: freed 0B (already clean from 14:48 vacuum of 259.7M)

## Alerts
- **WARN**: Disk 86% — DB growth recurring; CEO DB-pruning decision still open since 2026-10-01
- **WARN**: hermes-git-release failing hourly (uncommitted-changes gate + symlink) — known, not auto-fixed
- **INFO**: hermes-atr-sl-updater.timer unit not-found (ghost, harmless)
- **INFO**: Pipeline "inactive" between runs is normal oneshot+timer behavior — not a crash
