# Error Alerts

## 2026-08-15 15:18 UTC — Health Monitor
- **INFO**: No CRITICAL or WARN issues detected
- **AUTO-FIX**: Disabled deprecated `hermes-self-close-watcher.timer` (logic migrated to `hermes-hl-sync-guardian`)
- **NOTE**: GRASS phantom-write guard active — blocking SL tighten within 0.08% of entry (trade_id=13905)

## 2026-08-15 20:19 UTC — Health Monitor
- **WARN** (1x): `hermes-brain.db` is EMPTY (0 bytes, 0 tables) — trades tracked via trades.json, brain DB appears defunct
- **WARN** (1x): BLUR mirror_close FAILED at 20:04 — "HL API failed: Non-dict response from exchange: None"
- **WARN** (1x): ROLLBACK FAILED at 20:13 — sig#1551419 already claimed by another process (race condition)
- **WARN** (1x): hl_cache.json has only 6 tokens vs 108 in price collector (may be expected if HL-only)
- **INFO**: Pipeline running, 5 open positions, 53 closed today, -0.58% PnL
- **AUTO-FIX**: None needed — no CRITICAL issues
