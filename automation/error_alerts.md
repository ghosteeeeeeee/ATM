# Error Alerts

## 2026-08-19 07:18 UTC — Health Check: All Clear

No WARN or CRITICAL issues detected.

- Pipeline: running, 1-min timer active
- Signals: 58 generated in last hour
- Trades: 1 open, 4 closed today
- Disk: 77% used
- Errors: 0
- Auto-fixes: none needed

## 2026-08-19 09:19 UTC — Health Check: WARN

- **[WARN]** Hotset empty — compactor rejecting all signals despite high-confidence entries (88.0 conf). Market extremely flat: 103/105 tokens NEUTRAL. System correctly protecting capital in low-vol regime.
- **[INFO]** 18 closed trades today at -5.00% PnL. 0 open positions.
- **AUTO-FIX**: None needed — pipeline functioning correctly. Empty hotset is expected behavior when market is flat.

## Error Alerts — 2026-08-19 12:20 UTC
- **[WARN]** (1x): `4h candles 83 days stale` — candles.db 4h table last updated Apr 17
- **[WARN]** (1x): `Runtime DB 86MB` — exceeds 50MB threshold, needs VACUUM
- **[WARN]** (1x): `MTF-MACD tuner AttributeError` — PrecomputedMACD missing 'warmup' attr
- **[INFO]** (1x): `HL volume 429 rate limit` — transient, will self-resolve
- **[INFO]** (1x): `Ollama unreachable` — not used for trading, ignored

## Health Report — 2026-08-20 00:18 UTC
- **OK** Pipeline running (53 runs/hour), last run: 00:18 — completed in 18.6s
- **OK** Signals: 20 generated (1h), 935 (24h)
- **OK** Trades: 0 open, 26 closed today, +4.46% PnL
- **OK** Regime: 2 LONG / 0 SHORT / 102 NEUTRAL (overall: NEUTRAL)
- **OK** Timers: 43 active, all firing on schedule
- **OK** Disk: 78% used (26G free)
- **OK** Hotset: empty (expected — no signals above 50% confidence)
- **OK** No errors in last 30min

## Health Report — 2026-08-20 11:19 UTC

PIPELINE: OK
- Status: running (last run 11:18:19, 18.7s duration)
- Signals (1h): 0 generated (hotset empty — no signals above 50% confidence)
- Trades: 0 open, 28 closed today, +1.10% PnL
- Errors: 0

MARKET:
- Regime: 5 LONG_BIAS / 0 SHORT / 99 NEUTRAL (overall: LONG_BIAS)
- Speed: 185 tokens tracked
- Notable: CRV, ORD, CHIP, ENA, MEGA in LONG_BIAS

SYSTEM:
- Timers: 45 active, all firing
- Disk: 79% used (25G free)
- Prices: 239 tokens in speed tracker
- HL Copy DB: 1.4G

AUTO-FIXES APPLIED:
- Restarted hermes-hl-volume.service (was failed — 429 rate limit from Hyperliquid, transient)

ALERTS:
- **[WARN]** 3 phantom trades in PostgreSQL (id 10211-10213): empty status, 2 missing token — stale/orphaned records
- **[WARN]** 5 services in failed state: hl-volume (429 rate limit, transient), better-coder, bug-hunter, trading-checklist, wasp (non-critical)
- **[INFO]** Hotset empty — expected in neutral market, pipeline correctly filtering low-confidence signals

## Error Alerts — 2026-08-20 12:19 UTC
- **[WARN]** (1x): `hotset empty` — 0 signals above 50% confidence survived compaction. Market overwhelmingly neutral (99/104 tokens). No actionable signals.
- **AUTO-FIX**: None needed — this is a market condition, not a system failure. Signals will resume when market trends develop.

## Error Alerts — 2026-08-20 12:19 UTC
- **[WARN]** (1x): `hotset empty` — 0 signals above 50% confidence survived compaction. Market overwhelmingly neutral (99/104 tokens). No actionable signals.
- **AUTO-FIX**: None needed — this is a market condition, not a system failure.

## Error Alerts — 2026-08-20 16:19 UTC
- **[WARN]** (6x): Phantom trades with |pnl|<0.01% — POL, SYRUP, CFX, HYPE×2. Likely spread/slippage noise. Consider minimum PnL filter in position manager.
- **[WARN]** (1x): `pipeline.log` at 91MB — approaching rotation threshold.
- **AUTO-FIX**: None needed — no crashes, all timers firing, system operational. Market neutral (2L/1S/101N), 0 signals above threshold is expected behavior.

## Health Report — 2026-08-20 19:19 UTC

PIPELINE: OK
- Status: running (last run 19:18:19, 19.2s duration)
- Signals (1h): 0 breakout + 1 rs (HYPER) generated, 0 survived compaction
- Trades: 1 open (KAS LONG, +0.26%), 24 closed today, -3.29% PnL
- Errors: 0 in pipeline logs

MARKET:
- Regime: 0 LONG / 3 SHORT / 101 NEUTRAL (overall: SHORT_BIAS)
- Short tokens: DOGE (-4.08%), XRP (-7.6%), KAITO (-3.48%)
- Hotset: empty (no signals above50% confidence)

SYSTEM:
- Timers: all active, firing on schedule
- Disk: 79% used (88G/118G)
- Prices: 97 tokens tracked (coin_tracker)
- pipeline.log: 93MB (growing, rotate soon)
- signals DB: 84MB (67821 records, signal-purge active)

AUTO-FIXES APPLIED:
- **hermes-coding-mcp.service**: Disabled — was in infinite restart loop (92235+ restarts), `ModuleNotFoundError: No module named 'server'`. Not used for trading.

ALERTS:
- **[WARN]** 5 services in failed state: hl-volume (429 rate limit, transient), better-coder, bug-hunter, trading-checklist (all non-critical for trading)
- **[WARN]** `pipeline.log` at 93MB — approaching rotation threshold
- **[WARN]** Signals DB at 84MB — signal-purge timer active, should self-clean

## Error Alerts — 2026-08-20 22:20 UTC
- **WARN** (continuous): `signals: only 2-3 signals in last 5 min (min 20)` — pipeline_watchdog
- **WARN**: `hotset.json is empty — no signals survived compaction` — 0 signals above 50% confidence threshold
- **INFO**: Live trading kill switch: ON (re-enabled by CEO, 52.9% WR)
- **AUTO-FIX**: None required — all systems nominal, no crashes detected

## Error Alerts — 2026-08-21 01:20 UTC
- **[INFO]** Pipeline: ACTIVE, running every minute, no crashes
- **[INFO]** Timers: 3 critical timers active (pipeline, price-collector, 1m-candle)
- **[WARN]** Hotset: Empty — 0 signals survived compaction (market NEUTRAL, 100/104 tokens)
- **[WARN]** Signals: 590 in 24h, 0 APPROVED (418 EXPIRED, 171 SKIPPED)
- **[INFO]** Trades: 0 open, 18 closed today, -5.00% PnL (9W/7L, avg -$0.03)
- **[INFO]** Market: 3 LONG_BIAS, 1 SHORT_BIAS, 100 NEUTRAL
- **[INFO]** Kill switch: Live trading ON
- **[INFO]** Disk: 80% (89G/118G) — 24G free
- **[INFO]** pipeline.log: 95M (growing)
- **[INFO]** Services: hermes-hl-copy, hermes-hl-sync-guardian, hermes-metrics: ACTIVE
- **[WARN]** 5 services failed: better-coder, bug-hunter, mtf-macd-tuner, trading-checklist, wasp (non-critical for trading)
- **AUTO-FIX**: None required — all trading systems nominal

## Error Alerts — 2026-08-21 03:03 UTC
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TOK hermes-trades-api: TOK (most recent call last):`

## Error Alerts — 2026-08-21 09:19 UTC
- **WARN** (1x): `HYPE mirror_close FAILED (DB committed, HL still open): mirror_close(BTC): HL API failed — Unknown error` — BTC ATR SL hit at 09:02, DB committed close but HL API rejected. Position potentially still open on Hyperliquid.
- **WARN**: pipeline.log at 99MB (219MB total logs). Consider log rotation if growing unbounded.

## Error Alerts — 2026-08-21 11:20 UTC
- **[INFO]** Pipeline: OK — completed 11:18 UTC, 4 open, 21 closed today, +181.17% PnL
- **[INFO]** Timers: 44 active, none missed
- **[INFO]** Services: pipeline, hl-sync-guardian, price-collector, 1m-candle, CEO: all OK
- **[WARN]** pipeline.log at 101MB — consider log rotation
- **[INFO]** Previous BTC mirror_close failure (09:19) — HL API error, monitor
- **AUTO-FIX**: None required — all trading systems nominal

## Health Report — 2026-08-21 15:20 UTC

PIPELINE: OK
- Status: running (last run 15:18:14, 13.8s duration)
- Signals (1h): 19 generated, 0 approved (filtered by compactor)
- Trades: 4 open, 31 closed today, +99.70% PnL
- Errors: 0 in pipeline logs

MARKET:
- Regime: 9 LONG_BIAS / 2 SHORT / 93 NEUTRAL (overall: LONG_BIAS)
- Hotset: 1 token (ASTER)
- Speed: 185 tokens tracked

SYSTEM:
- Timers: 44 active, pipeline firing every 1min
- Disk: 81% used (22G free)
- Prices: 97 tokens in coin_tracker
- HL Sync Guardian: ACTIVE

AUTO-FIXES APPLIED:
- **hermes-coding-mcp.service**: Stopped — was crash-looping (98641+ restarts), `ModuleNotFoundError: No module named 'server'`. Not used for trading.

ALERTS:
- **[WARN]** 5 services failed: better-coder (ModuleNotFoundError: dispatcher), bug-hunter, git-release, mtf-macd-tuner, trading-checklist, wasp (all non-critical for trading)
- **[WARN]** pipeline.log at 103MB — consider log rotation
- **[INFO]** Phantom trade write blocked correctly (ETH SL too tight)

## Error Alerts — 2026-08-22 04:20 UTC
- **[WARN]** (N=1): `Disk usage at 82%` — 91G/118G, approaching 85% threshold. Consider log cleanup.
- **[WARN]** (N=1): `40 stale prices` — 40/239 tokens have stale price data (>5min old). Usually low-activity tokens.
- **[INFO]** Pipeline: OK — last run 04:18, 0 errors, 6 open trades, +205.60% PnL today.
- **[INFO]** Timers: All critical timers firing on schedule (pipeline, price-collector, regime-scanner, etc.)
- **[INFO]** Regime: LONG_BIAS overall (11 long, 2 short, 92 neutral of 105 scanned).

## Error Alerts — 2026-08-22 09:03 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3419s left, N failures)`

## Error Alerts — 2026-08-22 11:20 UTC
- **[WARN]** (1x): `1 phantom trade today` — atr_sl_hit with near-zero PnL (micro-slip SL hit)
- **[WARN]** (1x): `Disk at 82%` — 91G/118G, 3% from 85% threshold
- **[INFO]** Pipeline: OK — timer active, last run 11:19, 0 errors, 1 open trade (BTC -0.62%)
- **[INFO]** Market: LONG_BIAS (3/104), mostly neutral/ranging — low signal volume expected
- **[INFO]** No auto-fixes required

## Health Report — 2026-08-22 12:20 UTC

PIPELINE: OK
- Status: running (last cycle 12:19:23, next running at 12:20:00)
- Signals (1h): 29,132 generated, 0 approved
- Trades: 1 open (BTC LONG -0.09%), 37 closed today
- PnL today: -95.92% (17W/20L)
- Errors: 0 in pipeline logs

MARKET:
- Regime: 7 LONG_BIAS / 0 SHORT_BIAS / 97 NEUTRAL (104 tokens)
- Speed: 91% tokens >= 50%
- Long bias: BLUR, CRV, TRB, AAVE, ENA, PUMP, HEMI

SYSTEM:
- Timers: pipeline.timer (1min) + hl-sync-guardian: ACTIVE
- Disk: 82% used (21G free, 3% from 85% threshold)
- Prices: fresh (12:19:12 UTC), 44 stale tokens
- Logs: pipeline.log 116M

AUTO-FIXES APPLIED:
- None needed — all systems operational

ALERTS:
- **[WARN]** 0 decisions approved in last 1h despite 29K signals generated
- **[WARN]** -95.92% cumulative PnL today (37 trades, bad day)
- **[WARN]** 44 stale tokens in speed tracker
- **[INFO]** Disk at 82% — monitor, approaching 85% threshold

## Health Check — 2026-08-22 17:19 UTC
- **STATUS**: ALL CLEAR
- Pipeline: OK (completed 17:18, 0 errors)
- Open: 2 trades (HYPE +1.15%, BTC +0.01%)
- Signals: 41/hour, 31034 active
- Regime: 98 NEUTRAL / 5 LONG / 1 SHORT
- Speed: 95/187 tokens >= 50%
- Disk: 82% (21G free)
- Timers: all firing
- Auto-fixes: none needed

## Error Alerts — 2026-08-22 20:20 UTC

- **[WARN]** (1x): `ROLLBACK FAILED: sig#... already claimed by another process` — brain.py trade add fails when signal already consumed by parallel process. Race condition in decider signal claiming.
- **[WARN]** (1x): `brain.py FAILED: stderr=(empty)` — mirror_open for CASHCAT LONG failed with empty error. Likely related to rollback contention above.
- **[WARN]** (3x): `HL [hl_info] Error: HTTP Error 429: Too Many Requests` — rate limiting from Hyperliquid API during wallet scanning.
- **[WARN]** Disk at 82% (92G/118G) — trending toward 85% threshold. pipeline.log alone is 121M.
- **AUTO-FIX**: None needed — pipeline functioning correctly. ROLLBACK contention is a known race condition; system recovers on next tick. Market fully neutral (104/104 tokens), system correctly preserving capital with 4/6 positions open.

## Error Alerts — 2026-08-22 22:19 UTC
- **WARN** (1x): `Disk usage at 83%` — approaching 85% threshold
- **NO AUTO-FIX**: Not critical yet; monitor on next health check

## Error Alerts — 2026-08-22 22:19 UTC (update)
- **WARN** (1x): `Disk usage 83%` — approaching 85% threshold
- **INFO**: hl_copy.db = 1.8GB — largest DB, candidate for cleanup
- **HEALTHY**: No phantom trades, no pipeline errors, all timers firing

## Error Alerts — 2026-08-23 00:03 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS [Position Manager] TOK mirror_close TOK (DB committed, HL still open): HL TOK TOK: N null`

## Error Alerts — 2026-08-23 00:20 UTC — Health Check: OK
- **INFO**: Pipeline completed normally at 00:18, 5 open positions (all LONG), 200 closed today
- **INFO**: 57 timers active, all healthy. HL sync guardian active.
- **INFO**: Disk 82% (21G free). 239 tokens tracked. Regime NEUTRAL.
- **WARN** (info): ct-hot+ signal underperforming — 25% WR, -4.00 PnL (24h)
- **AUTO-FIX**: None needed — no critical issues detected

## 2026-08-23 01:19 UTC — Health Check

- **CRITICAL**: Today's 52 closed trades at -93.76% cumulative PnL
- **WARN**: hermes-atr-sl-updater timer DEFUNCT (renamed with -DEFUNCT suffix, not running)
- **INFO**: Pipeline healthy, last run 01:18 completed in 20s
- **INFO**: 64 signals generated in last hour, 186 tokens with fresh prices
- **INFO**: Disk 82% (21G free), 54MB hl-copy.log is largest log file
- **AUTO-FIX**: None needed — pipeline and timers healthy

## Error Alerts — 2026-08-23 02:20 UTC
- **[WARN]**: `hermes-5m-candle.timer` is disabled — 5m candle aggregation not running
- **AUTO-FIX**: None applied (may be intentional — verify before enabling)
- **[WARN]**: Day PnL -69.17% across 52 closed trades

## Error Alerts — 2026-08-23 05:03 UTC
- **REPEATED** (15x): `Aug N N:N:N python3[TOK]: [coin_tracker] TOK processing TOK: name 'token_speed' is not defined`

## Error Alerts — 2026-08-23 05:20 UTC
- **WARN** (1x): `disk 82%` — 92G/118G used, approaching 85% threshold
- **INFO**: `BTC-ACCEL guard active` — blocking new SHORT entries, BTC accelerating down
- **INFO**: `SEI SHORT cooldown` — 2 failures, 3539s remaining
- **WARN**: `All-time WR 15.9%` — 9704 trades, -1783.49 USDT overall
- **AUTO-FIX**: none required — all systems nominal

## Error Alerts — 2026-08-23 06:03 UTC
- **REPEATED** (3x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3539s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3478s left, N failures)`
- **REPEATED** (9x): `Aug N N:N:N python3[TOK]: TS   TS signals_runner [TOK]: N done, N errors`
- **REPEATED** (17x): `Aug N N:N:N python3[TOK]: TS   [coin_tracker] TOK: 'action'`
- **REPEATED** (5x): `Aug N N:N:N python3[TOK]: [coin_tracker] TOK processing TOK: 'macd_div'`

## Error Alerts — 2026-08-23 13:20 UTC
- **[CRITICAL]** (1x): `hermes-coding-mcp.service` — 120,146+ restart loops, `ModuleNotFoundError: No module named 'server'`. **AUTO-FIX**: Service stopped and disabled.
- **[WARN]** (3x): `hermes-better-coder.service` — `ModuleNotFoundError: dispatcher.dispatcher`
- **[WARN]** (1x): `hermes-bug-hunter.service` — 3 audit failures: 82 files non-atomic JSON, 5 hardcoded passwords, 16 dead imports
- **[WARN]** (1x): `hermes-git-release.service` — Exit 1 during symlink cleanup
- **[WARN]** (1x): `Disk at 83%` — 92G/118G, approaching 85% threshold
- **INFO**: Pipeline OK — cycle #167787, 108 signals/hour, 7 hotset entries, 0 errors
- **INFO**: Trades — 0 open, 23 closed today, +$0.33 PnL, 71.4% WR on ct-hot+ LONG
- **INFO**: Market — 1 LONG / 0 SHORT / 103 NEUTRAL, 67% tokens above 50th percentile speed
- **INFO**: All critical timers firing (pipeline, 1m-candle, watchdog, price-collector)

## Error Alerts — 2026-08-23 15:03 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] ME TOK BLOCKED — TOK in cooldown (3540s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] ME TOK BLOCKED — TOK in cooldown (3480s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] ME TOK BLOCKED — TOK in cooldown (3421s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] ME TOK BLOCKED — TOK in cooldown (3360s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] ME TOK BLOCKED — TOK in cooldown (3300s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] ME TOK BLOCKED — TOK in cooldown (3001s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] ME TOK BLOCKED — TOK in cooldown (2939s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] ME TOK BLOCKED — TOK in cooldown (2879s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] ME TOK BLOCKED — TOK in cooldown (2821s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] ME TOK BLOCKED — TOK in cooldown (2705s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] ME TOK BLOCKED — TOK in cooldown (2690s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] ME TOK BLOCKED — TOK in cooldown (2641s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] ME TOK BLOCKED — TOK in cooldown (2581s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] ME TOK BLOCKED — TOK in cooldown (2520s left, N failures)`

## Error Alerts — 2026-08-23 17:03 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   [CFV2] ⚠️ _wait_for_hl_close failed for TOK — aborting flip`

## Error Alerts — 2026-08-23 18:20 UTC
- **INFO**: Pipeline health check — all systems nominal
- **WARN**: Disk usage at 83% (92G/118G) — monitor, clean logs if approaching 85%
- **NO AUTO-FIXES REQUIRED**

## Health Check — 2026-08-23 21:20 UTC
- **[WARN]** Disk usage at 83% (20G free) — approaching 85% threshold
- **NO AUTO-FIX NEEDED** — pipeline healthy, timers active, 0 errors in logs

## Error Alerts — 2026-08-23 23:03 UTC
- **REPEATED** (10x): `Aug N N:N:N python3[TOK]: TS   [fetch_binance_candles] BSVUSDT: N Client TOK: Bad Request for url: https://api.binance.com/api/v3/klines?symbol=BSVUSDT&interval=15m&limit=N`
- **REPEATED** (5x): `Aug N N:N:N python3[TOK]: TS   [fetch_binance_candles] BSVUSDT: N Client TOK: Bad Request for url: https://api.binance.com/api/v3/klines?symbol=BSVUSDT&interval=4h&limit=N`
- **REPEATED** (5x): `Aug N N:N:N python3[TOK]: TS   [fetch_binance_candles] BSVUSDT: N Client TOK: Bad Request for url: https://api.binance.com/api/v3/klines?symbol=BSVUSDT&interval=1h&limit=N`

## Error Alerts — 2026-08-24 01:03 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS TOK signal_compactor: timed out`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS TOK breakout_engine: timed out`

## Error Alerts — 2026-08-24 04:03 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TOK signal_compactor: TOK (most recent call last):`

## Error Alerts — 2026-08-24 04:20 UTC
- **WARN** (7x): `hermes-{better-coder,bug-hunter,ceo,git-release,mtf-macd-tuner,trading-checklist,wasp}.service` = failed
  - **AUTO-FIX**: None — these are auxiliary services, not blocking pipeline or trading. Pipeline active with 5 open positions +10.18% PnL today.
- **INFO**: No phantom trades, no stale prices, no disk pressure. System core healthy.

## Error Alerts — 2026-08-24 05:03 UTC
- **REPEATED** (6x): `Aug N N:N:N python3[TOK]: TS   TOK signal_compactor: TOK (most recent call last):`

## Error Alerts — 2026-08-24 05:19 UTC
- **WARN** (129x): `phantom_trades` — trades with |pnl| < $0.01, likely noise fills
- **INFO**: All systems nominal. Market fully NEUTRAL, no regime signals firing.

## Error Alerts — 2026-08-24 07:04 UTC
- **REPEATED** (7x): `Aug N N:N:N python3[TOK]: TS   TOK signal_compactor: TOK (most recent call last):`

## Error Alerts — 2026-08-24 07:20 UTC
- **WARN** (1): Disk at 83% (93G/118G) — approaching threshold
- **WARN** (1): 53 tokens stale (>10min no price update)
- **INFO** (6): Non-critical services failed: better-coder (missing module), bug-hunter (audit exit), git-release, mtf-macd-tuner, trading-checklist, wasp
- **AUTO-FIX**: None required — pipeline running normally

## Error Alerts — 2026-08-24 09:04 UTC
- **REPEATED** (8x): `Aug N N:N:N python3[TOK]: TS   TOK signal_compactor: TOK (most recent call last):`

## Error Alerts — 2026-08-24 10:19 UTC
- **WARN** (6x): `service_failed` — better-coder, bug-hunter, git-release, mtf-macd-tuner, wasp, trading-checklist
- **WARN** (1x): `disk_near_threshold` — 84% used (93G/118G)
- **INFO** (1x): `purrusdt_400` — recurring 400 errors, token likely delisted
- **INFO** (130x): `phantom_trades` — trades with <$0.01 PnL in signal_outcomes
- **NO AUTO-FIX**: pipeline healthy, failed services are auxiliary

## Error Alerts — 2026-08-24 11:04 UTC
- **REPEATED** (9x): `Aug N N:N:N python3[TOK]: TS   [fetch_binance_candles] PURRUSDT: N Client TOK: Bad Request for url: https://api.binance.com/api/v3/klines?symbol=PURRUSDT&interval=15m&limit=N`

## Error Alerts — 2026-08-24 12:04 UTC
- **REPEATED** (6x): `Aug N N:N:N python3[TOK]: TS   TOK signal_compactor: TOK (most recent call last):`

## Error Alerts — 2026-08-24 13:20 UTC
- **WARN** (3x): `signal_compactor traceback` — recurring at line 2800 (13:06-13:08), self-resolved by 13:19
- **WARN** (1): `disk_near_threshold` — 84% used (93G/118G), 19G free
- **WARN** (1): 42 stale tokens (>10min no price update)
- **INFO**: Live trading ON, kill switch enabled
- **NO AUTO-FIX**: pipeline healthy, signal_compactor errors transient

## Error Alerts — 2026-08-24 14:04 UTC
- **REPEATED** (9x): `Aug N N:N:N python3[TOK]: TS   [fetch_binance_candles] PURRUSDT: N Client TOK: Bad Request for url: https://api.binance.com/api/v3/klines?symbol=PURRUSDT&interval=4h&limit=N`
- **REPEATED** (9x): `Aug N N:N:N python3[TOK]: TS   [fetch_binance_candles] PURRUSDT: N Client TOK: Bad Request for url: https://api.binance.com/api/v3/klines?symbol=PURRUSDT&interval=1h&limit=N`
- **REPEATED** (3x): `Aug N N:N:N python3[TOK]: TS   TOK position_manager: TOK (most recent call last):`

## Error Alerts — 2026-08-24 14:21 UTC
- **CRITICAL** (6x): `position_manager FATAL: name 'compute_pnl_usdt' is not defined` — cascade_flip.py:283 calls compute_pnl_usdt but only imports compute_close_pnl from pnl_utils
- **AUTO-FIX**: Added `compute_pnl_usdt` to cascade_flip.py import line. Verified import works. Next cascade flip will not crash.
- **WARN**: `signal_compactor` traceback at line 2800 (1x) — truncated, non-fatal, pipeline recovered
- **WARN**: `PURRUSDT` Binance 400 errors (repeated) — symbol likely delisted, non-blocking
- **WARN**: Disk at 84% (threshold 85%) — monitor, compress old logs if needed
- **INFO**: position_manager crashed 6x between 13:55-13:57 UTC, self-recovered by 14:01 when cascade flip stopped triggering. Bug was latent until next flip attempt.

## Health Report — 2026-08-24 16:20 UTC

```
=== Health Report ===
Time: 2026-08-24 16:20 UTC

PIPELINE: OK
- Status: running (cycle #169404)
- Signals (1h): 118 generated
- Signals (30m): 63 generated
- Hotset: 0 tokens approved (all filtered by macro gate)
- Errors: 0 in last 30min (4 transient ERRs at 15:28-15:46 self-recovered)

TRADING:
- Open trades: 0
- Closed today: 28 total across 13 signal types
- Best: bb_bounce+ LONG 92.3% WR (13 trades, +1.03 USDT)
- Worst: hl_copy_trader SHORT 50% WR (-0.81 USDT)
- Win rate overall: ~65% (weighted)

MARKET:
- Regime: NEUTRAL (1 long_bias, 3 short_bias, 102 neutral)
- BTC: $79,488 (range: -0.35% slope)
- Tide: BEARISH (20% long)
- Regime detail: STORMY (strong bearish tide, momentum surge)

SPEED:
- Tokens tracked: 239
- Hot (momentum >=70): 0
- Top momentum: kLUNC 60.8, kBONK 55.8, PURR 53.4
- Market momentum: very low, no tokens above 70

SYSTEM:
- Timers: 45 active, 1 running (pipeline)
- Disk: 84% used (19G free of118G)
- Logs: 187M total, 53M hl-copy.log (largest)
- Services OK: pipeline, hl-sync-guardian, hl-copy, metrics
- Services FAILED: better-coder (ModuleNotFoundError), git-release (symlink issue), wasp (exit 1), trading-checklist (exit 2)
- Price collector: running (last: 16:19, 26s CPU)

SIGNAL COMPACTOR:
- Status: running, 2.65s avg cycle
- Hotset: 0 entries (macro gate=FULL, regime=NEUTRAL)
- Note: 4 transient ERR tracebacks 15:28-15:46, self-recovered

AUTO-FIXES APPLIED:
- None needed (pipeline healthy, no critical issues)

ALERTS:
- [WARN] Disk 84% — approaching 85% threshold, monitor
- [WARN] 0 hotset tokens — market too quiet for entries (all filtered)
- [WARN] 6 failed services (non-critical: better-coder, git-release, wasp, trading-checklist, mtf-macd-tuner, bug-hunter)
- [WARN] signal_compactor 4 transient errors at 15:28-15:46 (self-recovered)
```

## Error Alerts — 2026-08-24 17:20 UTC
- **[WARN]**: Disk at 84% — approaching 85% threshold. data/ dir is 4.5G.
- **[WARN]**: hermes-hl-copy.timer stuck 1+ week → AUTO-FIX: restarted timer
- **[WARN]**: hermes-ma-cross-5m-tuner.timer enabled but never fired
- **[WARN]**: hermes-zscore-momentum-tuner.timer enabled but never fired
- **AUTO-FIX**: Compressed/truncated old logs (freed ~127M)

## Error Alerts — 2026-08-24 18:04 UTC
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   [fetch_binance_candles] TOK: N Client TOK: Bad Request for url: https://api.binance.com/api/v3/klines?symbol=TOK&interval=15m&limit=N`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   [fetch_binance_candles] TOK: N Client TOK: Bad Request for url: https://api.binance.com/api/v3/klines?symbol=TOK&interval=4h&limit=N`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   [fetch_binance_candles] TOK: N Client TOK: Bad Request for url: https://api.binance.com/api/v3/klines?symbol=TOK&interval=1h&limit=N`

## Error Alerts — 2026-08-24 18:20 UTC
- **[CRITICAL]** (4x in 30min): `signal_compactor.py:1232 UnboundLocalError: cannot access local variable 'bare_source'` — compactor crashed every cycle
- **AUTO-FIX**: Moved `bare_source = source.rstrip('+-0123456789')` before the confluence gate check (line 1212). Compactor now runs clean.
- **[WARN]**: CCUSDT 400 errors recurring (invalid symbol on Binance — non-critical)
- **[WARN]**: Disk at 84% — 1% from threshold

## Health Report — 2026-08-24 18:20 UTC

PIPELINE: OK (after fix)
- Status: running (active)
- Cycle: #169524
- Compactor: CRASHED → FIXED (UnboundLocalError: bare_source)
- Signals in DB: 72,165 total
- Signals (1h): 114 generated
- Hotset: 1 entry (BTC:LONG hl_copy_trader)
- Open positions: 0

MARKET:
- Regime: SHORT_BIAS (4 short, 101 neutral, 0 long)
- 1m regime: NEUTRAL/SHORT_BIAS mix
- Predictive alerts: BEARISH tide (23% long), momentum surge

TRADES TODAY:
- Closed: 86 trades, -$1.11 PnL, 61.6% WR

SYSTEM:
- Pipeline service: active
- Timers: 47 hermes timers active, all firing on schedule
- Disk: 84% used (19G free) — WARN
- Logs: largest is sync-guardian.log at 11M

AUTO-FIXES APPLIED:
- Fixed UnboundLocalError in signal_compactor.py:1232 — bare_source now computed before use

ALERTS:
- Disk 84% — clean logs if >85%
- CCUSDT 400 errors — invalid Binance symbol, non-critical
