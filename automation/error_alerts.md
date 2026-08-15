## Error Alerts — 2026-08-14 13:40 UTC

- **[WARN]** (1x): `[HYPE Mirror] FAILED — brain.py stderr empty`
- **[WARN]** (1x): `ROLLBACK FAILED: sig#1547142 already claimed by another process`
- **[WARN]** (128x): `Phantom trades — atr_sl_hit with <0.01% PnL`
- **[WARN]** (17x): `Stale prices — 17 tokens >5min without fresh candle`
- **[INFO]**: Disk at 82% — 3% from WARN threshold (85%)
- **[INFO]**: 5 empty DB files (0 bytes): brain.db, hermes.db, hermes_brain.db, hebbian_brain.db, hermes_db.db

## Error Alerts — 2026-08-14 14:09 UTC
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   [TOK Mirror] TOK`

## Error Alerts — 2026-08-14 17:41 UTC
- **[WARN]**: Disk at 83% — 2% from WARN threshold (85%). Recommend: `find /root/.hermes/logs -name "*.log" -mtime +7 -exec gzip {} \;`
- **[WARN]**: Phantom trade — NOT SHORT #13822 closed at exactly 0.00% PnL

## Error Alerts — 2026-08-14 18:42 UTC
- **[WARN]** (6x): Auxiliary services in failed state (better-coder, bug-hunter, hl-volume, mtf-macd-tuner, trading-checklist, wasp)
- **[WARN]**: Market 100% NEUTRAL — 104 tokens, no directional bias, hotset empty
- **[INFO]**: Pipeline healthy — 0 open positions, 73 closed today, -8.10% PnL
- **ROOT CAUSES**: hl-volume=429 rate limit, mtf-macd=AttributeError, better-coder=ModuleNotFoundError

## Error Alerts — 2026-08-14 22:09 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS signals_runner: ImportError — signals module not available: cannot import name 'R2_TREND_PLUS_ENABLED' from 'hermes_constants' (/root/.hermes/scripts/hermes_constants`

## Error Alerts — 2026-08-15 00:40 UTC
- **[INFO]**: Pipeline OK — ran 00:39:26, completed in 26s, 0 errors
- **[INFO]**: 85 signals generated in last hour (60766 total)
- **[INFO]**: Trades — 78 closed today, -0.46 USDT PnL, 0 open positions
- **[WARN]** (2x): Phantom trades — CASHCAT SHORT + NOT SHORT closed at 0.00% PnL via profit-monster-trail
- **[INFO]**: Regime — 102/104 NEUTRAL, 1 LONG, 1 SHORT. Speed: 7 hot, 94 warm, 8 cold
- **[INFO]**: Timers — 43 active, all core timers firing (pipeline 646ms ago, price-collector 10s ago, regime-scanner 9min ago)
- **[INFO]**: Services — hl-sync-guardian active, hl-copy daemon running (since Aug 6)
- **[INFO]**: Disk — 83% used (93G/118G), 2% from WARN threshold
- **[INFO]**: Data freshness — candles 1m: 1min, coin_tracker: 1min, regime: 10min
- **NO AUTO-FIXES NEEDED** — system healthy
