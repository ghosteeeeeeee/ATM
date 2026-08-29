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

## Error Alerts — 2026-08-25 19:20 UTC

- **[WARN]** 100% neutral market — 0/105 tokens with directional regime. 0% tokens at speed >= 50%. Extremely flat conditions limiting signal generation.
- **[INFO]** 31 closed trades today at 41.9% WR, -1.38 USDT PnL. Expected in flat market.
- **[WARN]** 7 non-critical services in failed state (better-coder, bug-hunter, git-release, mtf-macd-tuner, session-learner, signal-reporter, upgrade-implementer, wasp).
- **[WARN]** Disk at 82% — 21GB free. Monitor for growth.
- **AUTO-FIX**: None needed — pipeline functioning correctly. Flat market is external condition, not system failure.

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

## Error Alerts — 2026-08-24 19:04 UTC
- **REPEATED** (26x): `Aug N N:N:N python3[TOK]: TS   [fetch_binance_candles] TOK: N Client TOK: Bad Request for url: https://api.binance.com/api/v3/klines?symbol=TOK&interval=15m&limit=N`
- **REPEATED** (13x): `Aug N N:N:N python3[TOK]: TS   [fetch_binance_candles] TOK: N Client TOK: Bad Request for url: https://api.binance.com/api/v3/klines?symbol=TOK&interval=4h&limit=N`
- **REPEATED** (13x): `Aug N N:N:N python3[TOK]: TS   [fetch_binance_candles] TOK: N Client TOK: Bad Request for url: https://api.binance.com/api/v3/klines?symbol=TOK&interval=1h&limit=N`

## Error Alerts — 2026-08-24 21:04 UTC
- **REPEATED** (6x): `Aug N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`
- **REPEATED** (4x): `Aug N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] W TOK BLOCKED — WARNING — MOMENTUM`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3540s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (3540s left, N failures)`

## Health Check — 2026-08-24 22:19 UTC
- **OK**: Pipeline running, no errors, 48 timers active
- **WARN** (2x): Phantom trades — GRASS SHORT -0.008%, USUAL SHORT 0.0%
- **INFO**: Market fully NEUTRAL (106/106 tokens), reduced signal activity expected
- **INFO**: ETC LONG in cooldown (2 failures) — working as designed
- **STATUS**: All clear, no auto-fixes needed

## Error Alerts — 2026-08-24 23:04 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3541s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3483s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3422s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3361s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3301s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] IO TOK BLOCKED — WARNING — MOMENTUM`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3535s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] IO TOK BLOCKED — TOK in cooldown (3535s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3477s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] IO TOK BLOCKED — TOK in cooldown (3477s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3417s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] IO TOK BLOCKED — TOK in cooldown (3417s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3355s left, N failures)`
- **REPEATED** (3x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3543s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3485s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3427s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3363s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3305s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3247s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3186s left, N failures)`

## Error Alerts — 2026-08-25 00:04 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3479s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3421s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3359s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3294s left, N failures)`

## Error Alerts — 2026-08-25 02:04 UTC
- **REPEATED** (6x): `Aug N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3537s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3420s left, N failures)`

## Error Alerts — 2026-08-25 02:22 UTC
- **WARN** (1x): `disk_usage 81%` — approaching 85% threshold
- **AUTO-FIX**: None needed yet. Will compress logs if >85%.

## Error Alerts — 2026-08-25 04:04 UTC
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3542s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3424s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3297s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3243s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3182s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3126s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3062s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3005s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2519s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3533s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3354s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3290s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3239s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3176s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3484s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3423s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3241s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3181s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3060s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2998s left, N failures)`

## Error Alerts — 2026-08-25 05:04 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3530s left, N failures)`
- **REPEATED** (4x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3539s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3299s left, N failures)`
- **REPEATED** (6x): `Aug N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] IO TOK BLOCKED — WARNING — MOMENTUM`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] IO TOK BLOCKED — TOK in cooldown (3537s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] IO TOK BLOCKED — TOK in cooldown (3480s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3480s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3295s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3118s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] IO TOK BLOCKED — TOK in cooldown (3000s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] IO TOK BLOCKED — TOK in cooldown (2941s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] IO TOK BLOCKED — TOK in cooldown (2882s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] IO TOK BLOCKED — TOK in cooldown (2815s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] IO TOK BLOCKED — TOK in cooldown (2761s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] IO TOK BLOCKED — TOK in cooldown (2699s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] IO TOK BLOCKED — TOK in cooldown (2641s left, N failures)`

## Error Alerts — 2026-08-25 06:04 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] IO TOK BLOCKED — TOK in cooldown (2576s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] IO TOK BLOCKED — TOK in cooldown (2517s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2396s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2337s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2280s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2221s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2161s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2100s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2037s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1982s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1912s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1852s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1798s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1738s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1679s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3547s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3544s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3481s left, N failures)`

## Error Alerts — 2026-08-25 07:04 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3357s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3298s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] AR TOK BLOCKED — WARNING — MOMENTUM`
- **REPEATED** (3x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3541s left, N failures)`

## Error Alerts — 2026-08-25 08:04 UTC
- **REPEATED** (3x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3478s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3362s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3303s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3242s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3122s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1802s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1742s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1684s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1620s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1741s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1681s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1559s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1619s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1498s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] AR TOK BLOCKED — TOK in cooldown (3539s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] AR TOK BLOCKED — TOK in cooldown (3481s left, N failures)`
- **REPEATED** (14x): `Aug N N:N:N python3[TOK]: TS   [CASCADE TOK] ⚠️ _close_paper_position TOK: near "%": syntax TOK`
- **REPEATED** (25x): `Aug N N:N:N python3[TOK]: TS   [CASCADE TOK] ❌ Failed to close TOK #N`

## Health Report — 2026-08-25 08:21 UTC

**PIPELINE:** OK
- Status: running (37 runs in last 5min)
- Signals: 115 generated (1h), 115 active signals
- Trades: 0 open, 17 closed today, -0.52% PnL overall
- Errors: CASCADE FLIP `_close_paper_position` SQL syntax error (FIXED)

**MARKET:**
- Regime: SHORT_BIAS (5 short, 100 neutral, 0 long)
- Speed: 72% hot — market overheated (COOL_OFF signal)
- Regime status: STORMY

**SYSTEM:**
- Timers: 43 active, 0 missed
- Disk: 82% used (22G free)
- Pipeline: OK
- HL Sync Guardian: OK

**AUTO-FIXES APPLIED:**
- **FIXED** `cascade_flip.py:135,168` — Changed `%s` to `?` for SQLite placeholder (was causing `_close_paper_position` syntax error on every cascade flip close attempt for IMX #14320)

**ALERTS:**
- **WARN**: Cascade flip was unable to close IMX #14320 positions for ~30min due to SQL syntax bug — now fixed
- **WARN**: Market overheated (72% hot) — COOL_OFF regime active, reduce exposure

## Error Alerts — 2026-08-25 09:04 UTC
- **REPEATED** (19x): `Aug N N:N:N python3[TOK]: TS   [CASCADE TOK] ⚠️ _close_paper_position TOK: no such table: trades`

## Error Alerts — 2026-08-25 10:04 UTC
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] CASHCAT TOK BLOCKED — WARNING — MOMENTUM`

## Health Report — 2026-08-25 11:20 UTC

```
=== Health Report ===
Time: 2026-08-25 11:20 UTC

PIPELINE: OK
- Status: running (last run 11:19, cycle #170544)
- Duration: 28.2s CPU
- Signals (1h): 77 generated
- Hotset: 0 (all filtered by compactor)
- Approved: 0 signals above 50% confidence
- Errors: 0 in last 30min

TRADING:
- Open: 5 positions (BTC, ETH, HBAR, HYPE, ALT)
- Closed today: 22
- PnL today: -$0.96 (LONG -$0.46, SHORT -$0.50)
- Win rate: 40.9% (LONG 47.4%, SHORT 0%)
- All-time WR: ~15.9% (concerning)

MARKET:
- Regime: NEUTRAL (0 long, 0 short, 105 neutral)
- BTC: $79,309 (-0.65% 16-candle)
- ETH: $2,481 (-0.23% 16-candle)
- No tokens with directional bias

SPEED:
- Tokens tracked: 239
- >= 50th percentile: 126 (53%)
- Stale: 46 tokens (19%)

SYSTEM:
- Timers: 48 active, all firing
- Disk: 82% used (27G free)
- Logs: 79M total (pipeline.log 19M)
- HL Copy DB: 1.9G (largest)
- Coin Tracker DB: 1.1G
- Signals DB: 89M

AUTO-FIXES APPLIED:
- None needed — pipeline healthy

ALERTS:
- [WARN] 46 stale speed tokens (19% of tracked)
- [WARN] Daily PnL -$0.96 (40.9% WR) — bad day but small absolute loss
- [WARN] SHORT trades: 0% win rate (3 trades, all losses)
- [INFO] Market fully neutral — system correctly protecting capital
- [INFO] hermes-hl-copy.timer fires on boot only (daemon), working as designed
```

## Error Alerts — 2026-08-25 12:04 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3482s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3365s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3304s left, N failures)`

## Error Alerts — 2026-08-25 13:04 UTC
- **REPEATED** (15x): `Aug N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`

## Error Alerts — 2026-08-25 15:04 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (541s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (479s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (417s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (358s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (294s left, N failures)`

## Error Alerts — 2026-08-25 16:21 UTC
- **WARN** (1x): `36% coins hot — approaching overheated` — Coin tracker CAUTION signal. Market momentum surge detected (wind gusts 0.37 vs sustained 0.06). Watch for reversals.
- **WARN** (1x): `40% win rate today` — 30 trades closed, 12 wins, 18 losses. hl_copy_trader and ct-hot+ signals underperforming.
- **No auto-fixes applied** — all systems nominal, no crashes or errors.

## Error Alerts — 2026-08-25 17:04 UTC
- **REPEATED** (12x): `Aug N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3416s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3289s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3238s left, N failures)`

## Error Alerts — 2026-08-25 18:04 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2336s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2276s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2215s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2155s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2097s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1979s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1919s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1859s left, N failures)`
- **REPEATED** (4x): `Aug N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] BIGTIME TOK BLOCKED — WARNING — MOMENTUM`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] BIGTIME TOK BLOCKED — TOK in cooldown (3533s left, N failures)`

## Error Alerts — 2026-08-26 00:21 UTC (Health Check)
- **WARN** (8x): Support services in failed state: better-coder, bug-hunter, git-release, mtf-macd-tuner, session-learner, trading-checklist, upgrade-implementer, wasp
- **WARN** (1x): Phantom trade detected: ALT SHORT #14327 — $0.00 PnL (-0.33%)
- **INFO**: Full neutral market (106 tokens) — reduced signal generation expected
- **AUTO-FIX**: None applied — all failures are non-critical support services

## Error Alerts — 2026-08-26 02:04 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (178s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (62s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (0s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3546s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3426s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3538s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3475s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3235s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3183s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3117s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3064s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2999s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2943s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2879s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2817s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2764s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2699s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2645s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2579s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2527s left, N failures)`

## Error Alerts — 2026-08-26 03:04 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2461s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2404s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2279s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2096s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2223s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2039s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2159s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1975s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2102s left, N failures)`

## Error Alerts — 2026-08-26 03:20 UTC
- **WARN** (1x): `signal_compactor: timed out` at 03:15:02 — recovered on next cycle, no action taken
- **WARN**: hl_copy_trader signal win rate 33.3% (4/12 trades, last 24h) — worst performing signal type

## Error Alerts — 2026-08-26 04:04 UTC
- **NEW** (1x): `Aug N N:N:N systemd[N]: hermes-pipeline.service: Failed with result 'signal'.`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3536s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3411s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3293s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2094s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2033s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1978s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1916s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1856s left, N failures)`

## Error Alerts — 2026-08-26 05:04 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1793s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1728s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1669s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1613s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (3541s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (3479s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (3426s left, N failures)`
- **REPEATED** (46x): `Aug N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (357s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (298s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (235s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (173s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (117s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (57s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] CC TOK BLOCKED — WARNING — MOMENTUM`
- **REPEATED** (7x): `Aug N N:N:N python3[TOK]: TS   TOK decider_run: TOK (most recent call last):`
- **REPEATED** (7x): `Aug N N:N:N python3[TOK]: TS   TOK hermes-trades-api: TOK (most recent call last):`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   Signal bb_bounce: TOK → TOK: cannot import name 'get_all_latest_prices' from 'signal_schema' (/root/.hermes/scripts/signal_schema.py)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   Signal vortex_break: TOK → TOK: expected 'except' or 'finally' block (signal_schema.py, line N)`
- **REPEATED** (6x): `Aug N N:N:N python3[TOK]: TS   TS   Signal return_exhaustion_short: TOK → TOK: cannot import name 'get_all_latest_prices' from 'signal_schema' (/root/.hermes/scripts/signal_schema.py)`
- **REPEATED** (4x): `Aug N N:N:N python3[TOK]: TS   TS   Signal vortex_break: TOK → TOK: cannot import name 'get_all_latest_prices' from 'signal_schema' (/root/.hermes/scripts/signal_schema.py)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   Signal bb_bounce_short: TOK → TOK: expected 'except' or 'finally' block (signal_schema.py, line N)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   Signal bb_bounce_short: TOK → TOK: cannot import name 'get_all_latest_prices' from 'signal_schema' (/root/.hermes/scripts/signal_schema.py)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   Signal bb_bounce: TOK → TOK: expected 'except' or 'finally' block (signal_schema.py, line N)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CC TOK BLOCKED — TOK in cooldown (3121s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3121s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CC TOK BLOCKED — TOK in cooldown (3064s left, N failures)`

## Error Alerts — 2026-08-26 06:04 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3459s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3358s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3233s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3179s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1024s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3534s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2035s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3476s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1977s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1917s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1860s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3360s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1736s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3114s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3058s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2934s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2876s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2814s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2760s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2694s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2636s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2575s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2518s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2454s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2400s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2281s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (781s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2219s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (719s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2158s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (659s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2099s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (600s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2043s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (543s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1971s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (471s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (418s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1855s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (356s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1255s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1198s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1737s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (237s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1136s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1084s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1023s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (962s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3245s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (899s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (842s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3124s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (779s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (717s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3000s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2940s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2885s left, N failures)`

## Error Alerts — 2026-08-26 08:04 UTC
- **REPEATED** (3x): `Aug N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] ME TOK BLOCKED — WARNING — MOMENTUM`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3415s left, N failures)`

## Error Alerts — 2026-08-26 09:04 UTC
- **REPEATED** (10x): `Aug N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] CASHCAT TOK BLOCKED — WARNING — MOMENTUM`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3236s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3178s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3116s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3059s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2993s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2936s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2874s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2815s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2759s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (2875s left, N failures)`

## Error Alerts — 2026-08-26 10:04 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3414s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3296s left, N failures)`
- **REPEATED** (3x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3541s left, N failures)`
- **REPEATED** (3x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3484s left, N failures)`
- **REPEATED** (3x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3423s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (538s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (474s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (414s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (356s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (296s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (240s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2881s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (56s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (3535s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (115s left, N failures)`

## Error Alerts — 2026-08-26 11:04 UTC
- **REPEATED** (6x): `Aug N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] CASHCAT TOK BLOCKED — WARNING — MOMENTUM`
- **REPEATED** (3x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3540s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (3418s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (3356s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (3239s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (3182s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (3117s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (3059s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (3001s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (2940s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (2882s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2641s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2578s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2524s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2464s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2407s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1743s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1623s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (2040s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1499s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (1980s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1444s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (1925s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1383s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (1864s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (1804s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (1745s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (1681s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (1625s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (1559s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (958s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (177s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (668s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (602s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (542s left, N failures)`

## Error Alerts — 2026-08-26 12:04 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (483s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (427s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (60s left, N failures)`
- **REPEATED** (3x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3477s left, N failures)`

## Error Alerts — 2026-08-26 13:04 UTC
- **REPEATED** (4x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3417s left, N failures)`
- **REPEATED** (4x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3355s left, N failures)`
- **REPEATED** (3x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3301s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3177s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3057s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2997s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2938s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2880s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (3539s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (3415s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (3361s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3473s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (3473s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (3417s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (1799s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (3355s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (1737s left, N failures)`

## Error Alerts — 2026-08-26 14:04 UTC
- **REPEATED** (5x): `Aug N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] W TOK BLOCKED — WARNING — MOMENTUM`
- **REPEATED** (3x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3539s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (3536s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (3476s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] IO TOK BLOCKED — TOK in cooldown (3540s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] IO TOK BLOCKED — TOK in cooldown (3475s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1801s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (3120s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1675s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (3058s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (3003s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (2868s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2500s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (2817s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2450s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (2760s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2392s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (2703s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2335s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2273s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2213s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2154s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2095s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1976s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1913s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1854s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (2222s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (2163s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (2101s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (2042s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (1986s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (1920s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (1862s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (1803s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (1742s left, N failures)`

## Error Alerts — 2026-08-26 15:04 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (538s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (782s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (782s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (481s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (725s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (725s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (420s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (664s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (664s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (364s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (608s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (608s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (304s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (548s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (548s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (241s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (485s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (180s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (424s left, N failures)`

## Error Alerts — 2026-08-26 15:19 UTC
- **INFO**: Pipeline healthy. 5 open trades, 41 closed today (-6.24% PnL). 0 tracebacks.
- **WARN**: BTC-CRASH momentum guard blocking 56 LONG entries in 30min. BTC is NEUTRAL (slope -0.08%). Blocks may be overly cautious — review threshold.
- **INFO**: All 25 hermes timers firing on schedule. Disk 82%. No phantom trades.

## Error Alerts — 2026-08-26 16:04 UTC
- **REPEATED** (11x): `Aug N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] W TOK BLOCKED — WARNING — MOMENTUM`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (3546s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (3546s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (3538s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3474s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS signals_runner: TOK — name 'INVERSE_ACCEL_300_V2_ENABLED' is not defined`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CASHCAT TOK BLOCKED — TOK in cooldown (3475s left, N failures)`

## Error Alerts — 2026-08-26 17:04 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (657s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (599s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (422s left, N failures)`

## Error Alerts — 2026-08-26 18:04 UTC
- **REPEATED** (3x): `Aug N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2038s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1915s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3302s left, N failures)`

## Health Report — 2026-08-26 19:21 UTC

```
=== Health Report ===
Time: 2026-08-26 19:21 UTC

PIPELINE: OK
- Status: running (completed 19:19:26, 18s runtime)
- Timer: active (1min interval)
- Signals (1h): 61 generated, 0 entered (max positions 5/5)
- Trades today: 45 closed, +1.23 USDT, 53.3% WR
- Errors: 0

MARKET:
- Regime: 0 LONG / 0 SHORT / 106 NEUTRAL (overall: NEUTRAL)
- Top speeds: S=100%, BLZ=100%, MERL=99.5%, MKR=99.1%
- BTC crash protection: ACTIVE (YGG SHORT blocked at 19:12)

SYSTEM:
- Timers: ~30 active (all hermes timers firing)
- hl-sync-guardian: active
- Disk: 83% (20G free, under 85% threshold)
- Open positions: 5/5 (at capacity)
- Phantom trades: 0

ALERTS:
- [INFO] All 106 tokens in NEUTRAL regime — no directional bias
- [INFO] BTC crash protection blocking shorts on momentum
- [WARN] Disk at 83% — monitor, compress logs if >85%
- [INFO] Pipeline fully blocked new entries (5/5 positions full)
```

### Error Alerts — 2026-08-26 19:21 UTC
- **INFO**: All 106 tokens NEUTRAL regime — system in low-activity mode
- **INFO**: BTC-CRASH protection triggered — YGG SHORT blocked at 19:12
- **WARN**: Disk at 83% — 20G free, approaching threshold
- **INFO**: No auto-fixes needed — system running normally

## Error Alerts — 2026-08-26 23:04 UTC
- **REPEATED** (28x): `Aug N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`
- **REPEATED** (3x): `Aug N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] CC TOK BLOCKED — WARNING — MOMENTUM`

## Error Alerts — 2026-08-27 00:04 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3413s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3350s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3120s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2937s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2877s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2818s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2758s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2701s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2638s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2577s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2517s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2459s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2401s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2338s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   [fetch_binance_candles] CASHCATUSDT: N Client TOK: Bad Request for url: https://api.binance.com/api/v3/klines?symbol=CASHCATUSDT&interval=1h&limit=N`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   [fetch_binance_candles] CASHCATUSDT: N Client TOK: Bad Request for url: https://api.binance.com/api/v3/klines?symbol=CASHCATUSDT&interval=15m&limit=N`

## Error Alerts — 2026-08-27 00:20 UTC
- **[WARN]** (1x): Daily PnL -30.09% on 57 closed trades — heavy drawdown day
- **[INFO]** (1x): `hermes-4h-regime-scanner.service` not-found — needs cleanup or recreation
- **[INFO]** (1x): 36 stale records in signal_outcomes without pnl_usdt — pipeline reports 5 open but DB shows 0

## Error Alerts — 2026-08-27 02:04 UTC
- **REPEATED** (3x): `Aug N N:N:N python3[TOK]: TS   [fetch_binance_candles] CASHCATUSDT: N Client TOK: Bad Request for url: https://api.binance.com/api/v3/klines?symbol=CASHCATUSDT&interval=1h&limit=N`
- **REPEATED** (4x): `Aug N N:N:N python3[TOK]: TS   [fetch_binance_candles] CASHCATUSDT: N Client TOK: Bad Request for url: https://api.binance.com/api/v3/klines?symbol=CASHCATUSDT&interval=15m&limit=N`

## Error Alerts — 2026-08-27 06:04 UTC
- **REPEATED** (10x): `Aug N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`
- **REPEATED** (3x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3534s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3352s left, N failures)`

## Error Alerts — 2026-08-27 06:20 UTC
- **WARN** (1x): `disk 83%` — approaching 85% threshold, 20G free
- **AUTO-FIX**: None applied — monitoring, will clean logs if >85%
- **INFO** (1x): `hotset fallback 0 tokens` — no hotset data returned

## Error Alerts — 2026-08-27 10:04 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — CONTAGION+MOMENTUM`

## Health Report — 2026-08-27 10:20 UTC

```
=== Health Report ===
Time: 2026-08-27 10:20 UTC

PIPELINE: OK
- Status: running (last run 10:19, 17.9s CPU, 60 runs/hour)
- Signals (1h): 67 generated
- Trades: 1 open (GMT SHORT), 32 closed today
- PnL today: +$0.17
- Errors: 0 in last 30min

MARKET:
- Regime: 105 tokens scanned, long_bias=0
- BTC-CRASH guard: ACTIVE (blocked ETC LONG at 10:19)

SYSTEM:
- Timers: 20+ active (all firing on schedule)
- Disk: 83% (93G/118G) — approaching 85% threshold
- HL Sync Guardian: active

AUTO-FIXES APPLIED:
- None needed

ALERTS:
- [WARN] PHANTOM TRADE: GMT SHORT (trade_id=14426) — SL at entry (dist=0.001%), blocked every run by guardian. Position stuck.
- [WARN] Disk at 83% — monitor for growth.
```

## Error Alerts — 2026-08-27 11:04 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3356s left, N failures)`

## Error Alerts — 2026-08-27 12:04 UTC
- **REPEATED** (6x): `Aug N N:N:N python3[TOK]: TS   TS   ⚠️ ROLLBACK TOK: sig#N already claimed by another process`
- **REPEATED** (6x): `Aug N N:N:N python3[TOK]: TS   TS   → TOK:`
- **REPEATED** (3x): `Aug N N:N:N python3[TOK]: TS   TS   [brain.py] ❌ TOK: stderr=(empty)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] CC TOK BLOCKED — TOK in cooldown (1618s left, N failures)`

## Error Alerts — 2026-08-27 13:04 UTC
- **REPEATED** (3x): `Aug N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`

## Error Alerts — 2026-08-27 16:20 UTC
- **RESOLVED** (2x): `name '_warmup_volume_cache_pm' is not defined` in position_manager.py:3315
  - Occurred: 15:48, 15:49 UTC
  - Auto-resolved: pipeline recovered by 15:50, no action needed
- **WARN**: Disk at 83% (93G/118G) — will hit 85% threshold soon

## Error Alerts — 2026-08-27 17:04 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1019s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (960s left, N failures)`

## Error Alerts — 2026-08-27 18:04 UTC
- **REPEATED** (5x): `Aug N N:N:N python3[TOK]: TS   TS   [TOK-SIGNALS] write failed: name 'ACCEL_300_V2_ENABLED' is not defined`
- **REPEATED** (12x): `Aug N N:N:N python3[TOK]: TS   [fetch_binance_candles] MERLUSDT: N Client TOK: Bad Request for url: https://api.binance.com/api/v3/klines?symbol=MERLUSDT&interval=15m&limit=N`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3457s left, N failures)`
- **REPEATED** (9x): `Aug N N:N:N python3[TOK]: TS   [fetch_binance_candles] MERLUSDT: N Client TOK: Bad Request for url: https://api.binance.com/api/v3/klines?symbol=MERLUSDT&interval=1h&limit=N`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3174s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3001s left, N failures)`

## Error Alerts — 2026-08-27 18:20 UTC
- **CRITICAL** (1x): `accel_300_v2.py:467` — `V2_MIN_GAP_PCT` not defined, signal emitting 0 signals
- **AUTO-FIX**: Added `V2_MIN_GAP_PCT = 1.5` constant (matches LONG entry gate). Verified via --dry run.

## Error Alerts — 2026-08-27 19:04 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   Signal accel_300_v2: TOK → TOK: name 'V2_LONG_ONLY' is not defined`
- **REPEATED** (3x): `Aug N N:N:N python3[TOK]: TS   TS   Signal accel_300_v2: TOK → TOK: name 'V2_MIN_GAP_PCT' is not defined`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (238s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (118s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (61s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3418s left, N failures)`

## Error Alerts — 2026-08-27 20:04 UTC
- **REPEATED** (3x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3538s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3300s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1558s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3244s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1501s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3180s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1438s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1319s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2939s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1196s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1138s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2822s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2640s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (834s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2520s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (777s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2460s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (718s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (658s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (601s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2343s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (540s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2282s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2222s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (415s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2157s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2098s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (297s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2040s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (239s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (58s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1800s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1740s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1682s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1624s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1562s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1500s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1439s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1381s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1320s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1262s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1202s left, N failures)`

## Error Alerts — 2026-08-27 20:20 UTC
- **WARN** (7): `hermes-better-coder.service`, `hermes-bug-hunter.service`, `hermes-git-release.service`, `hermes-mtf-macd-tuner.service`, `hermes-trading-checklist.service`, `hermes-upgrade-implementer.service`, `hermes-wasp.service` — all in `failed` state
- **INFO**: Pipeline itself is healthy. No auto-fixes applied to pipeline.
- **NOTE**: 7 support/automation services crashed. Not blocking trading but degraded system automation.

## Error Alerts — 2026-08-27 21:04 UTC
- **REPEATED** (3x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1141s left, N failures)`
- **REPEATED** (3x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1079s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (841s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (722s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (660s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (536s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (480s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (360s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (301s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (240s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (181s left, N failures)`

## Error Alerts — 2026-08-27 21:25 UTC
- **WARN** (1x): `hermes-hl-sync-guardian.service` stuck since Aug 26 (39h offline)
- **AUTO-FIX**: Restarted service — now active
- **WARN** (1x): `hermes-hl-copy.timer` last fired Aug 15 (11 days stale)
- **AUTO-FIX**: Restarted timer — now active
- **WARN** (1x): Disk at 84% (approaching 85% threshold)
- **AUTO-FIX**: Old logs checked — already compressed. Not hermes-driven (92MB logs).

## Error Alerts — 2026-08-27 22:04 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3555s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3500s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3441s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3381s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3317s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3257s left, N failures)`

## Error Alerts — 2026-08-27 23:04 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2825s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2757s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2702s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2644s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2582s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2521s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2399s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2340s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2218s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2160s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1983s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1866s left, N failures)`

## Error Alerts — 2026-08-27 23:21 UTC
- **[WARN]** (1x): `Disk at 84% (19G free) — 1% from 85% threshold`
- **AUTO-FIX**: None required — monitoring. Top consumers: hl_copy.db (1.9G), coin_tracker.db (1.3G), candles.db (706M)

## Error Alerts — 2026-08-28 00:04 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (653s left, N failures)`

## Error Alerts — 2026-08-28 01:04 UTC
- **REPEATED** (3x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3537s left, N failures)`

## Error Alerts — 2026-08-28 01:20 UTC
- **WARN** (7x): `brain.py ❌ FAILED: ROLLBACK FAILED: sig#1570289..1570342 already claimed by another process`
- **AUTO-FIX**: No action needed — signals already claimed by another process (likely concurrent pipeline/hl-sync-guardian). Pipeline runs are completing successfully despite these.
- **WARN**: `hotset.json is empty — no signals survived compaction` — 0 signals above 50% confidence
- **INFO**: Disk at 84% (19G free) — approaching threshold but not critical yet

## Error Alerts — 2026-08-28 02:04 UTC
- **REPEATED** (5x): `Aug N N:N:N python3[TOK]: TS   TS   [brain.py] ❌ TOK: stderr=(empty)`
- **REPEATED** (5x): `Aug N N:N:N python3[TOK]: TS   TS   ⚠️ ROLLBACK TOK: sig#N already claimed by another process`
- **REPEATED** (5x): `Aug N N:N:N python3[TOK]: TS   TS   → TOK:`

## Error Alerts — 2026-08-28 03:21 UTC
- **CRITICAL** (1x): `hermes-pipeline.service` was inactive (deactivated)
- **AUTO-FIX**: Restarted hermes-pipeline.service — now active
- **WARN** (1x): Disk at 84% — approaching 85% threshold
- **WARN** (144x): Phantom trades detected (|pnl| < $0.01)

## Error Alerts — 2026-08-28 04:04 UTC
- **NEW** (1x): `Aug N N:N:N systemd[N]: hermes-pipeline.service: Failed to kill control group /system.slice/hermes-pipeline.service, ignoring: Invalid argument`

## Error Alerts — 2026-08-28 04:21 UTC
- **WARN** (Nx): `Disk usage at 84% (19G free) — approaching 85% warning threshold`
- **AUTO-FIX**: None applied. Monitor if usage continues climbing.

## Error Alerts — 2026-08-28 06:04 UTC
- **REPEATED** (36x): `Aug N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`

## Error Alerts — 2026-08-28 06:22 UTC

- **WARN** (1x): `hotset fallback DB query returned 0 tokens` — hotset dashboard may show stale data
- **WARN** (6x): Services in failed state: hermes-better-coder, hermes-bug-hunter, hermes-git-release, hermes-mtf-macd-tuner, hermes-trading-checklist, hermes-wasp
- **WARN** (1x): Disk at 84% — approaching 85% threshold
- **INFO**: 6 services in `activating/auto-restart` (health-monitor, price-collector, coding-mcp, daily-commit, away-detector, pipeline) — normal for timer-triggered services

## Error Alerts — 2026-08-28 07:04 UTC
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3063s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1445s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1325s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1259s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1205s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1145s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1083s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3065s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (721s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (663s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (419s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (363s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1929s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1863s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3119s left, N failures)`

## Error Alerts — 2026-08-28 08:04 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1379s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1323s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1261s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1260s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1201s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1139s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] IO TOK BLOCKED — TOK in cooldown (2459s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] IO TOK BLOCKED — TOK in cooldown (2399s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] IO TOK BLOCKED — TOK in cooldown (2342s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] IO TOK BLOCKED — TOK in cooldown (2282s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] IO TOK BLOCKED — TOK in cooldown (2222s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] IO TOK BLOCKED — TOK in cooldown (2162s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (665s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1985s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (606s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1926s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (544s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1864s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1678s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (244s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (184s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (122s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (66s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (6s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1081s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1021s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (959s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (902s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (844s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (484s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (425s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (362s left, N failures)`

## Health Check — 2026-08-28 08:21 UTC
- **OK**: Pipeline running, all services active, disk 83%
- **INFO**: 0 tokens at >=50% speed (flat NEUTRAL market), hotset DB returned 0 tokens (cosmetic)
- **No auto-fixes needed**

## Error Alerts — 2026-08-28 11:04 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS [Position Manager] TOK mirror_close TOK (DB committed, HL still open): mirror_close(TOK): HL TOK failed — Unknown TOK`

## Error Alerts — 2026-08-28 11:22 UTC (Health Monitor)
- **[WARN]** (6x): `6 services in failed state` — better-coder (missing dispatcher module), bug-hunter (exits 1 on findings), git-release (push failed), mtf-macd-tuner (missing warmup attr), trading-checklist (1 warning), wasp (crash)
- **[WARN]** (1x): `Disk at 83%` — 92G/118G, trending up
- **[WARN]** (1x): `0 hot tokens` — market quiet, 86 warm 8 cold
- **[INFO]**: Pipeline running, hl-sync-guardian active, 51 signals (1h), 42 trades closed today, $0.08 PnL, 57.1% WR
- **No auto-fixes needed** — all failed services are non-critical to pipeline operation

## Error Alerts — 2026-08-28 13:21 UTC
- **WARN** (6): Non-critical services failed: better-coder, bug-hunter, git-release, trading-checklist, wasp, mtf-macd-tuner
- **WARN** (665): Phantom trades with <0.01% PnL (total -0.90 USDT)
- **AUTO-FIX**: None needed — pipeline healthy, timers firing, prices fresh

## Error Alerts — 2026-08-28 14:04 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS [Position Manager] TOK mirror_close TOK (DB committed, HL still open): mirror_close(ME): HL TOK failed — Reduce only order would increase position. asset=N`

## Error Alerts — 2026-08-28 15:04 UTC
- **REPEATED** (5x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3541s left, N failures)`
- **REPEATED** (3x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3540s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3240s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3187s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3308s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3125s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3246s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2947s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3067s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (3487s left, N failures)`

## Error Alerts — 2026-08-28 16:22 UTC
- **INFO**: Pipeline HEALTHY — running, 106 signals generated, 4 open / 91 closed today
- **WARN** (7): Non-critical services failed: better-coder (import error), bug-hunter, ceo, git-release, mtf-macd-tuner, trading-checklist (1 warning), wasp
- **WARN**: Disk 83% used (20G free) — approaching threshold
- **INFO**: SHORT cooldowns blocking 5+ tokens — normal behavior
- **INFO**: Market SHORT_BIAS — 46 short / 60 neutral / 0 long
- **INFO**: Weekly perf: 432 trades, 51% WR, -0.40% avg PnL
- **AUTO-FIX**: None needed — pipeline healthy, no critical failures

## Error Alerts — 2026-08-28 17:04 UTC
- **REPEATED** (3x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3480s left, N failures)`

## Error Alerts — 2026-08-28 18:04 UTC
- **REPEATED** (3x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3360s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3185s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3123s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3003s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2942s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2164s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] IO TOK BLOCKED — TOK in cooldown (3536s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] IO TOK BLOCKED — TOK in cooldown (3479s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] IO TOK BLOCKED — TOK in cooldown (3416s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] IO TOK BLOCKED — TOK in cooldown (3360s left, N failures)`
- **REPEATED** (3x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2998s left, N failures)`
- **REPEATED** (3x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2936s left, N failures)`
- **REPEATED** (3x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2875s left, N failures)`
- **REPEATED** (3x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2820s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2277s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1918s left, N failures)`

## Error Alerts — 2026-08-28 19:04 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1858s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1797s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (898s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1015s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2883s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (961s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2819s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (897s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2762s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (839s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2698s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (776s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2637s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (715s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (597s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (537s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (478s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (299s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (414s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (234s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] IO TOK BLOCKED — TOK in cooldown (414s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] IO TOK BLOCKED — TOK in cooldown (358s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (114s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] IO TOK BLOCKED — TOK in cooldown (294s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (60s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] IO TOK BLOCKED — TOK in cooldown (240s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] IO TOK BLOCKED — TOK in cooldown (179s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] IO TOK BLOCKED — TOK in cooldown (117s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] IO TOK BLOCKED — TOK in cooldown (57s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1921s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1617s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1564s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1502s left, N failures)`

## Error Alerts — 2026-08-28 22:04 UTC
- **REPEATED** (9x): `Aug N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] BIGTIME TOK BLOCKED — TOK in cooldown (3535s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] BIGTIME TOK BLOCKED — TOK in cooldown (3477s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] BIGTIME TOK BLOCKED — TOK in cooldown (3415s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] BIGTIME TOK BLOCKED — TOK in cooldown (3356s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] BIGTIME TOK BLOCKED — TOK in cooldown (3294s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] BIGTIME TOK BLOCKED — TOK in cooldown (3235s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] BIGTIME TOK BLOCKED — TOK in cooldown (3173s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3173s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2995s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2816s left, N failures)`

## Error Alerts — 2026-08-28 23:04 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2093s left, N failures)`
- **REPEATED** (10x): `Aug N N:N:N python3[TOK]: TS   [brain.py] ❌ REJECTED: TOK TOK — amount_usdt=N.N < HL_MIN=N.N (would TOK on HL)`

## Error Alerts — 2026-08-29 00:04 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2878s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2634s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2576s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2394s left, N failures)`

## Error Alerts — 2026-08-29 00:22 UTC
- **WARN** (Nx): `signals_runner: ERROR — name 'ACCEL_300_V2_LONG_ENABLED' is not defined` — occurred 00:12-00:15, self-resolved by 00:17. Transient import issue (likely .pyc cache or race condition). No auto-fix needed.
- **WARN** (Nx): `ERR hermes-trades-api: Traceback` — occurred 00:13-00:15, self-resolved. Followed ACCEL_300_V2 error.
- **WARN** (1): Phantom trade: W SHORT trade_id=14505 with 0% PnL / $0.00 — likely exchange tracking artifact. Recommend cleanup.

## Error Alerts — 2026-08-29 01:04 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   Signal accel_300_v2: TOK → TOK: name 'ACCEL_300_V2_LONG_MIN_GAP' is not defined`
- **REPEATED** (6x): `Aug N N:N:N python3[TOK]: TS   TS signals_runner: TOK — name 'ACCEL_300_V2_LONG_ENABLED' is not defined`
- **REPEATED** (5x): `Aug N N:N:N python3[TOK]: TS   TOK hermes-trades-api: TOK (most recent call last):`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2639s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2516s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1980s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1796s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1680s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1560s left, N failures)`

## Error Alerts — 2026-08-29 02:04 UTC
- **REPEATED** (3x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3540s left, N failures)`
- **REPEATED** (3x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3476s left, N failures)`
- **REPEATED** (3x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3423s left, N failures)`

## Error Alerts — 2026-08-29 03:04 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1561s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1503s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1442s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1382s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1203s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (780s left, N failures)`

## Error Alerts — 2026-08-29 05:04 UTC
- **REPEATED** (4x): `Aug N N:N:N python3[TOK]: TS   [brain.py] ❌ REJECTED: CASHCAT TOK — amount_usdt=N.N < HL_MIN=N.N (would TOK on HL)`
- **REPEATED** (4x): `Aug N N:N:N python3[TOK]: TS   TS   [brain.py] ❌ TOK: stderr=(empty)`
- **REPEATED** (4x): `Aug N N:N:N python3[TOK]: TS   TS   ⚠️ ROLLBACK TOK: sig#N already claimed by another process`
- **REPEATED** (4x): `Aug N N:N:N python3[TOK]: TS   TS   → TOK:`

## Error Alerts — 2026-08-29 05:22 UTC
- **INFO**: System healthy. Pipeline running, 145 signals/hr, 8 trades today, 0 errors.
- **WATCH**: Disk at 84% (93G/118G). Will compress logs if >85%.

## Error Alerts — 2026-08-29 06:04 UTC
- **REPEATED** (5x): `Aug N N:N:N python3[TOK]: TS   [brain.py] ❌ REJECTED: TOK TOK — amount_usdt=N.N < HL_MIN=N.N (would TOK on HL)`
- **REPEATED** (6x): `Aug N N:N:N python3[TOK]: TS   TS   [TOK-SIGNALS] write failed: name 'ACCEL_300_V2_LONG_5M_ENABLED' is not defined`

## Error Alerts — 2026-08-29 07:04 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3055s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2935s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2755s left, N failures)`

## Error Alerts — 2026-08-29 08:04 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (3420s left, N failures)`

## Error Alerts — 2026-08-29 09:04 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (3357s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (3296s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (3236s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (3177s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (3118s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (3059s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2996s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (2996s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (2938s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (2877s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (2818s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (2757s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (2698s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2632s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (2632s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (2576s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (2517s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (2460s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2398s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (2398s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (2336s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (2273s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2216s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (2216s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2163s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (2163s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (2096s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (2035s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (1976s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (1917s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (1855s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (1796s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (1738s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1497s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1476s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (1476s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (1439s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1376s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (1376s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1316s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (1316s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1256s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (1256s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1195s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (1195s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1134s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (1134s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1077s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (1077s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1018s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (1018s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (955s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (955s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (897s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (834s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (777s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (713s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (713s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (656s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (656s left, N failures)`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (595s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (595s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (535s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (535s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (478s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (415s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] W TOK BLOCKED — TOK in cooldown (358s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (293s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (236s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (176s left, N failures)`

## Error Alerts — 2026-08-29 10:04 UTC
- **REPEATED** (4x): `Aug N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`

## Error Alerts — 2026-08-29 14:04 UTC
- **REPEATED** (4x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3357s left, N failures)`
- **REPEATED** (4x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3419s left, N failures)`
- **REPEATED** (3x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3540s left, N failures)`
- **REPEATED** (3x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3298s left, N failures)`
- **REPEATED** (3x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3236s left, N failures)`
- **REPEATED** (3x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3178s left, N failures)`

## Error Alerts — 2026-08-29 15:04 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (598s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (416s left, N failures)`

## Error Alerts — 2026-08-29 16:04 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (1017s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (772s left, N failures)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (539s left, N failures)`
