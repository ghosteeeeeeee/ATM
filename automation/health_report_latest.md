# Health Report — 2026-10-02 22:49 UTC

```
=== Health Report ===
Time: 2026-10-02 22:49 UTC

PIPELINE: OK
- Status: running (active, multiple clean cycles in last 30min)
- Signals (1h): 83 generated, 0 approved (hotset empty)
- Trades: 0 open, 47 closed today (30 wins / 63.8% WR, +$0.32 PnL)
- Errors: 0 Tracebacks / 0 CRASH in last 30min
- Position manager: clean (0 open | 0 closed | 0 adjusted this cycle)

MARKET:
- Regime: 0 LONG / 0 SHORT / 117 NEUTRAL (fully flat)
- Speed: 129 tokens >= 50th percentile
- Prices: fresh (86 tokens, 32s old)

SYSTEM:
- Timers: all key units firing (pipeline, price-collector, signal-compactor,
  health-monitor, hl-sync-guardian, coin-tracker, daily-commit)
- Disk: 88% used (98G/118G, 15G free) — WARN
- Failed units (non-critical): better-coder, mtf-macd-tuner, wasp,
  bug-hunter, git-release, trading-checklist — trading path unaffected

AUTO-FIXES APPLIED:
- WAL checkpoint session_brain.db — freed 73.8MB
- WAL checkpoint signals_hermes.db — freed 4.6MB
- candles.db WAL (3.2GB) still locked by active price_collector — cannot
  checkpoint mid-collection; will reclaim when collector exits
- No logs >7d to compress (already done at 21:46)

ALERTS:
- WARN: Disk 88% — DBs dominate (coin_tracker 3.3G, candles 2.3G+3.2G WAL,
  signals_hermes 905M, session_brain 866M, mtf_macd_tuner 529M).
  CEO DB-retention decision still open.
- WARN: hotset.json empty repeatedly — "fallback DB query returned 0 tokens"
  despite 16839 rows in signals table. All-neutral regime + confidence gate
  blocking execution is expected; DB-fallback returning 0 is worth auditing
  in signal_compactor filters.
- INFO: better-coder broken: ModuleNotFoundError 'dispatcher.dispatcher'
- INFO: mtf-macd-tuner broken: AttributeError PrecomputedMACD.warmup
- INFO: wasp.service failing every 30min (exit 1)
- NOTE: signals table holds 16839 rows — signal-purge timer may not be
  reclaiming; worth a retention audit.
```
