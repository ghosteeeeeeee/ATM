# Health Report — 2026-08-23 13:20 UTC

## PIPELINE: OK
- Status: running, cycle #167787
- Signals (1h): 108 generated, 7 in hotset
- Trades: 0 open, 23 closed today (+$0.33)
- Win rate: 71.4% (ct-hot+ LONG), 50% (others)
- Errors: 0 pipeline errors

## MARKET: NEUTRAL
- Regime: 1 LONG / 0 SHORT / 103 NEUTRAL (104 tokens scanned)
- Speed: 125/186 tokens ≥ 50th percentile (67%)
- Top movers: CASHCAT (89.6 pctl), kLUNC (91.9 pctl), kNEIRO (73.6 pctl)
- Liquidation heatmap: 9 coins, 194 clusters, 0 cascade zones

## SYSTEM
- Critical timers: 4/4 active (pipeline, 1m-candle, watchdog, price-collector)
- Disk: 83% used (20G free) — OK but watch
- HL Copy: active (daemon running)
- HL Sync Guardian: active

## FAILED SERVICES (non-critical, no auto-fix)
| Service | Error | Action Needed |
|---------|-------|---------------|
| hermes-coding-mcp | `ModuleNotFoundError: server` — **120,146 restart loops** | STOP immediately, fix import |
| hermes-better-coder | `ModuleNotFoundError: dispatcher.dispatcher` | Fix import path |
| hermes-bug-hunter | 3 audit failures (non-atomic JSON, hardcoded passwords, dead imports) | Code quality issues, not crashes |
| hermes-git-release | Exit 1 during symlink cleanup | Check push script |

## AUTO-FIXES APPLIED
- None needed — pipeline healthy, timers firing on schedule

## ALERTS
- **CRITICAL**: hermes-coding-mcp in restart storm (120K+ crashes). Stopping it now.
- **WARN**: Disk at 83%. Compress logs if >85%.
- **WARN**: 4 services in failed state (non-critical to trading)
