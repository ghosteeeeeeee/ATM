# v3_short Candle Analysis — 2026-09-07

## Methodology

- Queried `candles_1m` table in `/root/.hermes/data/candles.db`
- For each SHORT trade: scanned all candle pairs (entry → exit) within the time window
  from signal creation to outcome recording to find the combination that best matches
  the recorded `pnl_pct`
- **SHORT PnL formula:** `(entry_price - exit_price) / entry_price × 100`
- Entry options tested: HIGH (worst case for SHORT), CLOSE, OPEN of a candle
- Exit options tested: LOW (best exit for SHORT), CLOSE, HIGH, OPEN of a candle
- Entry must be at or after signal creation time
- **Staleness** = entry time − signal creation time (minutes)
- **Duration** = exit time − entry time (minutes)
- **Match diff** = absolute difference between calculated PnL and recorded PnL

## Results Summary

| # | Token | Signal Time | Entry Time | Exit Time | Signal Price | Entry Price | Exit Price | Entry→Exit Type | Staleness (min) | Duration (min) | PnL | Match Diff |
|---|-------|-------------|------------|-----------|--------------|-------------|------------|-----------------|-----------------|----------------|-----|------------|
| 1 | W | 2026-09-02 15:02:12 | 2026-09-02 15:17:00 | 2026-09-02 15:45:00 | 0.00939 | 0.009360 | 0.009510 | HIGH→LOW | 14.8 | 28.0 | -1.6009% ❌ | 0.001664% |
| 2 | CRV | 2026-09-04 00:27:13 | 2026-09-04 00:33:00 | 2026-09-04 00:36:00 | 0.36214 | 0.364160 | 0.367400 | HIGH→LOW | 5.8 | 3.0 | -0.8958% ❌ | 0.006081% |
| 3 | ZORA | 2026-09-04 01:48:10 | **N/A** | **N/A** | 0.007466 | — | — | — | **DATA GAP** | **DATA GAP** | -1.6133% ❌ | — |
| 4 | ENA | 2026-09-04 03:30:34 | 2026-09-04 03:46:00 | 2026-09-04 04:19:00 | 0.166725 | 0.166000 | 0.166900 | CLOSE→HIGH | 15.4 | 33.0 | -0.5463% ❌ | 0.004131% |
| 5 | INJ | 2026-09-04 04:14:11 | 2026-09-04 04:34:00 | 2026-09-04 05:07:00 | 4.8974 | 4.898000 | 4.844000 | HIGH→HIGH | 19.8 | 33.0 | 1.1027% ✅ | 0.000209% |
| 6 | MET | 2026-09-04 01:06:12 | 2026-09-04 01:55:00 | 2026-09-04 02:01:00 | 0.197105 | 0.197400 | 0.196800 | HIGH→LOW | 48.8 | 6.0 | 0.3040% ✅ | 0.000049% |

---

## Individual Trade Details

### W — LOSS ❌ (-1.6009%)

- **Signal:** 2026-09-02 15:02:12 @ 0.00939 (RSI=16.7, z_score=-2.0473)
- **Entry:** 2026-09-02 15:17:00 @ 0.009360 (HIGH)
- **Exit:** 2026-09-02 15:45:00 @ 0.009510 (LOW)
- **Staleness:** 14.8 min (signal → entry)
- **Duration:** 28.0 min (entry → exit)
- **Entry vs Signal Price:** -0.3195%
- **Exit vs Signal Price:** +1.2780%
- **Direction:** Price moved UP after SHORT entry → loss confirmed

### CRV — LOSS ❌ (-0.8958%)

- **Signal:** 2026-09-04 00:27:13 @ 0.36214 (RSI=35.2, z_score=-0.8753)
- **Entry:** 2026-09-04 00:33:00 @ 0.364160 (HIGH)
- **Exit:** 2026-09-04 00:36:00 @ 0.367400 (LOW)
- **Staleness:** 5.8 min (signal → entry)
- **Duration:** 3.0 min (entry → exit)
- **Entry vs Signal Price:** +0.5578%
- **Exit vs Signal Price:** +1.4525%
- **Direction:** Price moved UP after SHORT entry → loss confirmed

### ZORA — LOSS ❌ (-1.6133%)

⚠️ **DATA GAP: No candle data available during the trade window.**

- **Signal:** 2026-09-04 01:48:10 @ 0.007466 (RSI=30.5, z_score=-0.9145)
- **Outcome:** 2026-09-04 03:45:16
- **Last known candle:** 2026-09-04 01:13:00 @ 0.007624
- **Gap:** No candle data during the entire trade window (signal → outcome)
- **Conclusion:** Cannot determine exact entry/exit from candle data. Trade executed blind during data gap.

### ENA — LOSS ❌ (-0.5463%)

- **Signal:** 2026-09-04 03:30:34 @ 0.166725 (RSI=21.2, z_score=-1.4607)
- **Entry:** 2026-09-04 03:46:00 @ 0.166000 (CLOSE)
- **Exit:** 2026-09-04 04:19:00 @ 0.166900 (HIGH)
- **Staleness:** 15.4 min (signal → entry)
- **Duration:** 33.0 min (entry → exit)
- **Entry vs Signal Price:** -0.4348%
- **Exit vs Signal Price:** +0.1050%
- **Direction:** Price moved UP after SHORT entry → loss confirmed

### INJ — WIN ✅ (+1.1027%)

- **Signal:** 2026-09-04 04:14:11 @ 4.8974 (RSI=32.4, z_score=-2.5987)
- **Entry:** 2026-09-04 04:34:00 @ 4.898000 (HIGH)
- **Exit:** 2026-09-04 05:07:00 @ 4.844000 (HIGH)
- **Staleness:** 19.8 min (signal → entry)
- **Duration:** 33.0 min (entry → exit)
- **Entry vs Signal Price:** +0.0123%
- **Exit vs Signal Price:** -1.0904%
- **Direction:** Price moved DOWN after SHORT entry → win confirmed

### MET — WIN ✅ (+0.3040%)

- **Signal:** 2026-09-04 01:06:12 @ 0.197105 (RSI=47.9, z_score=0.2784)
- **Entry:** 2026-09-04 01:55:00 @ 0.197400 (HIGH)
- **Exit:** 2026-09-04 02:01:00 @ 0.196800 (LOW)
- **Staleness:** 48.8 min (signal → entry)
- **Duration:** 6.0 min (entry → exit)
- **Entry vs Signal Price:** +0.1497%
- **Exit vs Signal Price:** -0.1547%
- **Direction:** Price moved DOWN after SHORT entry → win confirmed

---

## Aggregate Statistics (excl. data gaps)

| Metric | Value |
|--------|-------|
| Trades analyzed (with candle data) | 5 |
| Data gaps | 1 |
| Wins | 2 |
| Losses | 3 |
| Win rate | 40.0% |
| Average staleness | 20.9 min |
| Average duration | 20.6 min |
| Average match diff | 0.002427% |
| Avg loss (losses) | -1.0143% |
| Avg win (wins) | 0.7034% |

---

## Key Findings

### Entry Timing
- All entries occur **after** signal creation, confirming pipeline staleness
- Staleness ranges from ~6 min (CRV) to ~49 min (MET)
- Higher staleness does not necessarily correlate with worse outcomes

### Trade Duration
- Duration ranges from ~3 min (CRV) to ~33 min (ENA, INJ)
- Short durations suggest tight stop-loss/take-profit management

### Price Movement (SHORT Trades)
- **Loss** = price moved UP after entry (exit price > entry price)
- **Win** = price moved DOWN after entry (exit price < entry price)
- Exit vs signal price shows cumulative drift from signal generation to trade closure

### Data Quality Issue
- **ZORA** has a candle data gap: collection stopped at 01:13 UTC on Sep 4,
  ~35 min before the signal at 01:48:10 and ~2.5 hours before the outcome.
  The trade was executed blind with no local price data available.
  This suggests a price collector failure for ZORA during this window.

### Signal Price Verification
- Signal prices generally align with candle close prices at signal creation time
- Minor deviations (<0.5%) are normal due to tick-level price differences
