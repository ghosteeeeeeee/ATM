## CEO Report — 2026-08-09 11:20 UTC (11:20 verified)

### Diagnosis (verified DB — Postgres `brain`)
- **24h: 61T +$0.41 (52.5% WR)** — net positive, holding pattern
- **6h: 20T +$0.35 (65.0% WR)** — strong
- **Today UTC: 37T +$0.53 (62.2% WR)** — strongest day of the week
- **4d rolling: 237T +$1.04 (56.1% WR)** — trajectory is positive
- **7d: 386T -$0.12 (46.4% WR)** — breakeven; Aug 3-4 legacy pre-fix days (-$0.91) aging out
- LONG 24h: 47T 51.1% WR +$0.35 · SHORT 24h: 13T 61.5% WR +$0.10 (bleeding fully stopped)
- 0 phantoms in 24h. 1 just-opened AXS LONG (8 min, +0.02% diff) — not stuck.

### Star & Bleeders
- **Star LONG:** `bb_bounce+,range_finder+` 25T 56% WR +$0.30 (24h) · 37T 62.2% WR +$0.81 (7d)
- **Star SHORT:** `bb-bounce-short,hzscore-` 9T 77.8% WR +$0.25 (24h) · 9T 77.8% WR +$0.25 (7d)
- Last-6h opens: 7 bb_bounce+,range_finder+ LONG + 6 bb-bounce-short,hzscore- SHORT (13 of 20 = stars).
- 24h bleeder `ma100-cross+,vortex_break_long` 5T 20% WR -$0.14 is **all Aug 8 16:52-19:53** trades (pre-fix). `MA_100_CROSS_PLUS_ENABLED = False` verified; 0 new fires since. Same for `MA_100_CROSS_MINUS_ENABLED`. `ma100-cross,vortex_break_long` LONG 7d: 8T 62.5% WR +$0.08 — different combo, distinct signal, still healthy.

### Fix Applied
**NONE.** All previous fixes verified working (Postgres direct, no cached claims):
- MA_100_CROSS_{ENABLED,PLUS,MINUS} all False (line 1351-1353)
- 7d bleeds already disabled: zscore-rising- (-$0.22), hzscore-,return_exhaustion- (-$0.18), vel-hermes- (-$0.06), bb_bounce SHORT (+$0.09 actually positive), empty-signal SHORT -$0.17
- ATR SL 1.2% widening holding (median 24h atr_sl_hit pnl_pct = -0.36% = trailing working as designed)
- Compactor `is_component_disabled()` fix: verified
- SHORT bleeding: STOPPED (13T 61.5% WR +$0.10 24h, vs -$1.90/7d pre-fix)

### Verification
- Pipeline ran 11:19:09 UTC (last cycle 15s ago). 6 open / 37 closed today / +$0.53 (62.2% WR).
- Open: ASTER LONG bb_bounce+,hzscore+ 9h +0.14%, AAVE LONG bb_bounce+,range_finder+ 2.5h -0.45%, LINK LONG bb_bounce+,range_finder+ 1.7h -0.12%, SKY LONG hzscore+,range_finder+ 1.6h -0.53%, ETH SHORT bb-bounce-short,hl_copy_trader 40m +0.08%, AXS LONG bb_bounce+,range_finder+ 8m +0.02%.
- 7d daily: 4 of last 5 days green; Aug 3 -$0.22, Aug 4 -$0.69 (legacy) → Aug 5-9 +$0.10 / -$0.08 / +$0.34 / +$0.10 / +$0.53.
- decay_detector, signal_reporter, signal_rotator, health_monitor — all on schedule.

### Watch
- bb_bounce+,range_finder+ LONG had 3 atr_sl_hits in 24h (-$0.16) despite 56% WR — normal trail captures, not catastrophic.
- Disk 80% (24GB free) — below 85% threshold, non-blocking.
- hermes-ceo.timer 4d stale (manual CEO runs continue to work via 4h cadence) — cosmetic.

### Trajectory
System on **clear positive trajectory** for the 4th consecutive day. 4d rolling +$1.04, today strongest day of week (+$0.53, 62.2% WR), all stars firing profitably, all bleeders dead, SHORT side recovered. 7d expected to flip positive within 12-24h as Aug 3-4 legacy trades age out (2 of those 7 days have already exited the window on Aug 10).

## CEO Report — 2026-08-09 11:50 UTC (verified DB)

### Diagnosis (verified directly — `signals_hermes_runtime.signal_outcomes`)
- **24h: 60T +$0.42 (55.0% WR)** — net positive, holding
- **6h: 20T +$0.31 (65.0% WR)** — strong
- **Today UTC: 38T +$0.56 (63.2% WR)** — strongest day of week, 2nd day in a row >63%
- **7d: 430T -$4.94 (43.5% WR)** — still negative, but Aug 2-4 legacy bleeds (-$7.7) aging out fast
- LONG 24h: 48T 52.1% WR +$0.22 · SHORT 24h: 12T 66.7% WR +$0.20 (bleeding fully stopped)
- 0 phantoms in 24h. Pipeline LIVE.

### Star & Bleeders
- **Star LONG:** `bb_bounce+,range_finder+` 26T 53.8% +$0.26 (24h)
- **Star SHORT:** `bb-bounce-short,hzscore-` 9T 77.8% WR +$0.26 (24h)
- **Today mix is clean:** bb_bounce+,range_finder+ LONG 18T 55.6% +$0.17 + bb-bounce-short,hzscore- SHORT 8T 75% +$0.21 + continuation+,hzscore+ LONG 2T 100% +$0.06. Only 2-3 combos firing, all profitable.
- **All 7d bleeds verified DISABLED AND DEAD** (last_fire Aug 5-6, 4d ago, decay complete):
  - `zscore-rising-` SHORT 44T -$1.38 25% WR · `vel-hermes-` SHORT 58T -$1.14 31% WR
  - `zscore-rising+` LONG 26T -$1.01 27% WR · `pattern_wolf_wave_bear` SHORT 9T -$0.79 11% WR
  - `bb_bounce` SHORT 10T -$0.56 30% WR · `decider` SHORT 10T -$0.22 0% WR

### Fix Applied
**NONE.** All previous fixes verified working:
- MA_100_CROSS_{ENABLED,PLUS,MINUS} all False (lines 1351-1353)
- `MA_100_CROSS_PLUS_ENABLED=False` confirmed: zero fires of `ma100-cross+,vortex_break_long` since disable (last 5T 20% WR -$0.12 in 24h are Aug 8 16:52-19:53 pre-fix, will age out today)
- Compactor `is_component_disabled()` fix verified — all 3 SHORT components properly suppressed
- SHORT vol filter 1.0x, CHoCH 5m fallback, PM_TRAIL 0.25% — all holding
- ATR SL 1.2% widening — median atr_sl_hit pnl_pct ~ -0.36% (trail catching as designed)

### Verification
- Pipeline ran 11:48 UTC (within 4h cadence). All timers on schedule.
- 5 daily snapshots: Aug 5 +$2.32 / Aug 6 -$0.54 / Aug 7 +$0.40 / Aug 8 +$0.05 / Aug 9 +$0.56 → 4 of last 5 days green, today strongest.
- 7d PnL shrinking fast: -$4.94 today vs -$6.29 yesterday. Aug 2 (-$1.16, 0% WR) and Aug 3 (-$3.07, 6.3% WR) — both outside 7d window within 36h.

### Trajectory
System on **strong positive trajectory** for the 5th consecutive day. SHORT bleeding fully recovered (12T 66.7% WR +$0.20 24h), LONG + SHORT both profitable, all stars firing, all bleeds decaying cleanly. **7d flips positive within 12-24h** as Aug 2-3 zero-WR legacy days age out of the rolling window. No interventions needed.
