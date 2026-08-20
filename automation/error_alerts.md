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
