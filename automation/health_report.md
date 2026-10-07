
# Hermes Health Report — 2026-10-07 13:50 UTC

## Status: OK (WARN: disk 85%)

PIPELINE:
- Status: active (cycle #232539, position_manager rc=0)
- Signals (1h): 86 generated
- Trades: 2 open (APT SHORT +0.56%, FIL SHORT +0.82%), 8 closed today (+0.50 USDT, 2 wins)
- Errors: 0 Tracebacks/CRASH in 30min window
- Phantom trades (atr_sl_hit <0.01%): 0 today
- Regime gate: SHORT_BIAS — macro gate LONG=REDUCE, SHORT=FULL

MARKET:
- Regime: SHORT_BIAS 5 LONG / 69 SHORT / 50 NEUTRAL (124 tokens, 5m)
- coin_tracker: STORMY, MOMENTUM_SURGE predictive alert (gust 0.34 vs sustained 0.05)
- Speeds: 127/241 tokens >= 50th percentile (52.7%)
- Prices: fresh (87 tokens, age ~8s)

SYSTEM:
- Timers: pipeline / price-collector / 1m-candle all active (<90s last fire)
- Services: pipeline, hl-sync-guardian active
- Disk: 85% used (95G/118G) — WARN, no uncompressed logs >7d
- Active DBs (do not delete): coin_tracker 3.3G, candles 2.6G, mtf_macd_tuner 1.5G

AUTO-FIXES APPLIED:
- Disabled hermes-coding-mcp.service — crash-looping (765k+ restarts), ExecStart script missing (`scripts/run_mcp_server.py`), MCP dir gutted (dispatcher/ empty). Not part of trading path.
- Disabled hermes-better-coder.service + timer — `ModuleNotFoundError: dispatcher.dispatcher`, module deleted. Non-critical maintenance.

ALERTS:
- WARN: disk 85% — recurring; active DBs are the growth drivers, CEO retention decision still open
- WARN: hermes-git-release fails hourly on uncommitted changes (update-git.py refuses dirty tree) — needs a commit when ready, not a service fix
- WARN: hermes-bug-hunter / trading-checklist / upgrade-implementer still failing on code-quality audits (known, non-critical)
- INFO: GRASS SHORT closed at exactly 0.00% PnL via atr_trail_hit — not a phantom (real exit, zero net), filter/entry quality issue not system health
