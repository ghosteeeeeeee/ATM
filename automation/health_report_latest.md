## Health Report — 2026-09-10 08:23 UTC

PIPELINE: ✅ OK
- Status: running (last cycle 08:22:48)
- Signals (1h): 49 generated, 0 above 50% confidence (normal for NEUTRAL regime)
- Hotset: empty (no signals survived compaction)
- Open positions: 4/5
- Closed today: 10 trades, +$0.81 PnL, 60.0% WR
- Errors: 1 transient (signal_compactor timeout at 08:22, self-recovered)

MARKET:
- Regime: NEUTRAL (0 long, 2 short, 103 neutral)
- Overall: NEUTRAL — quiet market, no trades expected
- No phantom trades detected

SYSTEM:
- Pipeline service: active
- HL Sync Guardian: active
- Timers: 55 active, all firing on schedule
- Disk: 83% (93G/118G, 25G free) — 2% from threshold
- Price collector: active (fired 28s ago)
- Lock file: present (normal for running pipeline)

AUTO-FIXES APPLIED:
- None needed

ALERTS:
- **[WARN]** Disk at 83% — 2% from 85% threshold. Monitor closely.
- **[WARN]** signal_compactor timeout at 08:22 — self-recovered on next cycle. Persistent issue from earlier today (multiple timeouts logged in error_alerts.md).
