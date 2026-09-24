## Error Alerts — 2026-09-23 23:45 UTC
- **[WARN]** (1x): `signal_compactor: timed out (killed after 60.1s)` at 23:38:02
- **AUTO-FIX**: None needed — recovered on next pipeline cycle (23:44:05, 2.1s). Transient LLM timeout, not a recurring failure.
- **[WARN]** (1x): Disk at 84% (19G free of 118G). Approaching 85% threshold.
- **AUTO-FIX**: Monitoring only. If it crosses 85%, compress old logs or run `find /root/.hermes/logs -name "*.log" -mtime +7 -exec gzip {} \;`.

## Error Alerts — 2026-09-24 00:45 UTC
- **WARN** (8x): `signal_compactor: timed out (killed after 60.1s)` — compactor slow, 8 timeouts in 2h
- **WARN**: `regime_5m.json` is empty `{}` — no regime data available
- **WARN** (6x): Phantom trades (PnL < 0.01%) — dust from breakeven exits
- **WARN**: Disk at 84% (19G free) — monitor, compress logs at 85%
- **WARN**: Hotset empty — 0 signals survived compaction, pipeline idle
- **INFO**: Pipeline running, all 65 timers active, services healthy

## Error Alerts — 2026-09-24 04:57 UTC
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS TOK signal_compactor: timed out (killed after N.0s)`

## Error Alerts — 2026-09-24 05:45 UTC
- **WARN** (1x): `hermes-hl-sync-guardian.timer` — Trigger: n/a, last fired 22h ago. Timer shows active since Aug 17 but trigger metadata stale. Service running but timer may not re-arm.
- **WARN** (1x): Win rate 11.1% today (1/9 trades). All losses small (<$0.35). Review signal quality.
- **WARN** (1x): Disk at 85% (94G/118G). No immediate action, monitor.

## Error Alerts — 2026-09-24 07:46 UTC
- **WARN** (4x): `BLUR LONG` trade failed repeatedly (07:37-07:40). stderr=(empty), HL API rejecting. At 5/6 position capacity — likely max positions reached. Signal not rolled back (prevents retry loop).
- **WARN** (1x): `signal_compactor` timed out at 07:42:02 (killed after 60.1s). One-off — subsequent runs completed fine. No action needed.
- **WARN** (1x): Disk at 85% (94G/118G). Journal logs consuming 354M. Watch level only.
- **INFO**: Phantom trades cleaned (43 stale records removed). These were trade_ids with pnl_usdt=0.0 from weeks ago still counted as "open".
- **AUTO-FIX**: Compressed logs >1 day old. Cleaned 43 phantom trade records from signal_outcomes.

## Error Alerts — 2026-09-24 07:57 UTC
- **REPEATED** (6x): `Sep N N:N:N python3[TOK]: TS TOK signal_compactor: timed out (killed after N.1s)`

## Error Alerts — 2026-09-24 10:57 UTC
- **REPEATED** (7x): `Sep N N:N:N python3[TOK]: TS TOK signal_compactor: timed out (killed after N.1s)`
- **REPEATED** (8x): `Sep N N:N:N python3[TOK]: TS WARNING: N steps failed: signal_compactor`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`

## Error Alerts — 2026-09-24 11:45 UTC
- **WARN** (5x): `signal_compactor: timed out (killed after 60.0s)` — recurring, 5 timeouts in last hour. Root cause: 10,344 stale signals bloating DB queries.
- **WARN**: Disk at 85% (95G/118G) — at threshold.
- **WARN**: Win rate 30.0% today (6/20 trades). PnL: -$1.47 USDT.
- **INFO**: Pipeline healthy, all timers firing, no crashes. 4 positions managed locally by guardian.
- **AUTO-FIX**: Purged 9,075 stale signals (>24h old) from signals table (10,344 → 1,637). Compressed old logs. Next signal_compactor run should complete under 60s.

## Error Alerts — 2026-09-24 11:57 UTC
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   [brain.py] ❌ REJECTED: TOK TOK — amount_usdt=N.N < HL_MIN=N.N (would TOK on HL)`

## Error Alerts — 2026-09-24 12:45 UTC
- **CRITICAL** (1x): `Today's PnL: -49.63% with 28.6% winrate (21 trades, -1.79 USDT)` — Severe underperformance
- **WARN** (1x): `Disk usage at 85%` — At threshold, monitor closely

## Error Alerts — 2026-09-24 13:45 UTC
- **WARN** (1x): `signal_compactor: timed out (killed after 60.0s)` at 13:44:02 — recovered on next cycle (ran in 0.8s at 13:44:24)
- **WARN**: Disk at 85% (95G/118G). Top consumers: coin_tracker.db (2.8G), candles.db (2.1G), mtf_macd_tuner.db (840M)
- **INFO**: 8 zero-byte orphan DBs found (associative_memory.db, brain.db, hermes_brain.db, hermes.db, prices.db, price_candles.db, hermes_prices.db, speeds_hermes_runtime.db) — candidates for cleanup

## Error Alerts — 2026-09-24 14:57 UTC
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   ⚠️ [TOK-TOK] TOK failed for TOK: Command '['/root/.opencode/bin/opencode', 'run', 'You are a crypto trading gate. Evaluate this signal and reply TOK of: GO, TOK, TO`

## Error Alerts — 2026-09-24 15:46 UTC
- **[WARN]** (1x): `signal_compactor timed out (killed after 60.1s)` at 15:35:02
- **AUTO-FIX**: None needed — self-resolved on next cycle (0.6s). Transient.
- **[WARN]** (1x): `Disk at85%` — 95G/118G used. Databases = 7.8G (coin_tracker 2.8G, candles 2.1G).
- **AUTO-FIX**: Compressed old logs. No data dir cleanup (requires manual review).

## Error Alerts — 2026-09-24 15:57 UTC
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS TOK signal_compactor: timed out (killed after N.0s)`

## Error Alerts — 2026-09-24 16:45 UTC
- **[WARN]** (15x/2h): `signal_compactor: timed out (killed after 60.1s)` — caused by DB lock contention on `info_rate` table (13,053 lock-wait retries). Intermittent: recovers on next cycle. Last 3 runs OK (0.8s, 0.9s, 1.9s).
- **AUTO-FIX**: No action needed — self-healing. If pattern persists, investigate concurrent writers to `info_rate`.
- **[WARN]** (1x): `Disk at 85%` — 95G/118G used. Top consumers: signal-compactor.log (34M), pipeline.log (30M), 15m_regime.log (25M).
- **AUTO-FIX**: Compressed old logs. No data dir cleanup (requires manual review).

## Error Alerts — 2026-09-24 16:57 UTC
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] W TOK — continuum says TOK+LEAN_BULL+TOK, allowing despite TOK filter`

## Error Alerts — 2026-09-24 17:47 UTC
- **WARN** (2x): `signal_compactor: timed out (killed after 60.1s)` at 17:35 and 17:43 — DB lock contention on `info_rate` table (13,157 total LOCK-WAIT retries in err.log). Self-heals on next cycle.
- **WARN** (1x): `ImportError: cannot import name 'SPEED_HOTSET_THRESHOLD'` — stale .pyc files causing intermittent import failure.
- **AUTO-FIX**: Cleaned all __pycache__/*.pyc files. Verified import works: `SPEED_HOTSET_THRESHOLD=80, SPEED_HOTSET_BONUS=0.15`.
- **WARN** (1x): Hotset empty — 0 tokens survived compaction. Not an error; no signals meeting criteria right now.
- **WARN** (1x): Disk at 85% (94G/118G). Freed ~1GB via journal vacuum (423MB) + log compression.
- **INFO**: Pipeline healthy. 3 open positions (BTC SHORT in profit, CASHCAT SHORT). 34 closed today, -56% PnL. All timers active.
