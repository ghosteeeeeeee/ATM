# Health Report — 2026-09-30 13:48 UTC

## PIPELINE: OK
- Status: completed 13:45:35 (LIVE) — service inactive between timer fires (normal)
- Cycle: rc=0, 31s CPU, 0 errors, 0 tracebacks
- Position Manager: 0 open | 0 closed this cycle
- Portfolio: 0 open | 20 closed today
- Signals (1h): 60 generated (ONDO/IOTA/IMX/BIGTIME/ACE support_resistance @ 74–88 conf)
- Decisions (2h): 0 written — compactor quiet, worth a look next cycle
- Errors (30min): 0

## MARKET
- Regime: LONG_BIAS — 14 LONG / 1 SHORT / 101 NEUTRAL (116 tokens, ts 13:45:05)
- Speed: 127/241 tokens ≥50th percentile (52.7%)
- Open trades: 0 | Closed today: 20 | Phantom trades 24h: 0

## SYSTEM
- Timers: 67 hermes units — pipeline, price-collector, signal-compactor, watchdog, 15m-regime all firing on schedule
- hl-sync-guardian: active (live_trading=True, DRY=False)
- Disk: 84% used (93G/118G, 19G free) — sustained 13h, under 85% threshold
- Prices: 86 tokens, fresh (13:45:30) — candles.db 2.3GB updated 13:45:43
- Failed units: 0 after reset (was 5: 4 non-trading + checklist-by-design)
- Journald: 212MB (vacuumed earlier today)

## AUTO-FIXES APPLIED
- `reset-failed` × 5: 5m-candle (redundant), better-coder, brain-auditor, git-release, trading-checklist (exit-2 by design)
- No disk cleanup needed — no logs >7d, journald already small
- No pipeline restart needed — cycle completed cleanly

## ALERTS
- WARN: disk 84% sustained 13h — monitor, compress if it crosses 85%
- INFO: signals DB 11385 rows — checklist flags for cleanup; archive timer runs daily 04:00
- INFO: 0 decisions in 2h — recheck if signals keep firing without compactor output
- INFO: `list-timers hermes-*` glob returns 0 — use `list-timers --all | grep hermes` instead
