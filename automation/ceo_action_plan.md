# CEO Action Plan — 2026-08-02 23:15 UTC

## Status: EDGE WEAK · INFRA OK · PARAM DRIFT

Starvation blockers from earlier today are **closed**. Current problem is weak WR + constant thrash + speed-gate inconsistency.

## Done (do not reopen)
- ACCEL_300 re-enabled + NEVER_REENABLE on inv-accel family
- Dead-hours, preserve filter, signals_runner sync
- Kill-switch layers for disabled signals
- ACCEL_300_BREAKOUT disabled
- Pipeline + hl-sync-guardian active

## Now (only)

| P | Action | Detail |
|---|--------|--------|
| P0 | DISABLE ACCEL_300_MINUS | ✅ DONE 23:20 UTC |
| P0 | FREEZE params 48h | ✅ DONE — auto-1hr + param-auto-tuner timers disabled; prompt frozen |
| P0 | Resolve lock conflict | ✅ RESTORED locked set (2.0% / 0.25·0.50 / 45) |
| P1 | Unify speed metric | ✅ DONE — CTX-GATE uses SpeedTracker same as EXEC |
| P1 | Fix guardian_orphan closes | ✅ DONE — None=already-flat success; retry; clear marker if flat |
| P2 | Watch vel-hermes- | n≥30 before any scale |
| P2 | Disk 81% | cleanup noncritical logs/archives |

## Locked parameters (reaffirm — DO NOT REVERT without data + CEO)

Until explicit re-lock of the auto-1hr set:

| Parameter | Locked |
|-----------|--------|
| ATR_SL_MIN_INIT | 2.0% |
| TRAILING_ACTIVATION_PCT | 0.25% |
| TRAILING_DISTANCE_PCT | 0.50% |
| SIGNAL_FILTER_SPEED_MIN | 45 |

If live narrower SL/trail stays, CEO must re-lock after MFE/MAE proof — not silent tuner overwrite.

## Signal stance

| Signal | Stance |
|--------|--------|
| inv-accel-* | PERMANENT OFF |
| accel-300-breakout | OFF |
| accel-300- | DISABLE (P0) |
| accel-300+ | ON, watch decay |
| vel-hermes- | ON, trial |
| pattern_scanner | ON, poor 24h — no expand |
| pct-hermes- | flag-gated as live |

## Do not
- Pause live trading
- Re-enable inv-accel
- Chase 0% WR with more constant churn
- Treat 04:00–12:00 starvation writeups as current blockers
