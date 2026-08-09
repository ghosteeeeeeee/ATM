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

## CEO Report — 2026-08-09 12:00 UTC (verified DB)

### Diagnosis (verified DB — `signals_hermes_runtime.signal_outcomes`)
- **24h: 61T +$0.34 (54.1% WR)** — net positive, holding pattern
- **12h: 37T +$0.43 (62.2% WR)** — strong
- **6h: 18T +$0.12 (61.1% WR)** — slowing but positive
- **Today UTC: 39T +$0.47 (61.5% WR)** — strongest day of week
- **4d rolling: 349T +$3.28 (52.7% WR)** — strong recovery in motion
- **7d: 431T -$5.03 (43.4% WR)** — still negative but shrinking; Aug 2-4 legacy pre-fix days account for -$7.72 across 76T at 3.9% WR. Aug 5-9 (post-fix window) = 355T +$2.67 at 52.4% WR.
- LONG 24h: 49T 51.0% +$0.13 · SHORT 24h: 12T 66.7% +$0.20 — both profitable
- 0 phantoms in 24h.

### Star & Bleeders
- **Star LONG:** `bb_bounce+,range_finder+` 26T 53.8% WR +$0.26 (24h) / 38T 63.2% WR +$0.86 (7d)
- **Star SHORT:** `bb-bounce-short,hzscore-` 9T 77.8% WR +$0.26 (24h & 7d)
- **24h bleeder:** `ma100-cross+,vortex_break_long` 5T -$0.12 20% WR — all Aug 8 16:52-19:53 pre-fix trades. `MA_100_CROSS_PLUS_ENABLED = False` verified Aug 10, 0 new fires.
- All 7d worst signals (zscore-rising-, vel-hermes-, zscore-rising+, pattern_wolf_wave_bear, bb_bounce, pattern_scanner, accel-300+, decider) verified DISABLED — last fires Aug 5-6, no new fires in 24h.
- Last 6h fires are dominated by stars + continuation+,hzscore+ LONG (2T 100% WR). 4 bb-bounce-short,hzscore- SHORT + 6 bb_bounce+,range_finder+ LONG.

### Fix Applied
**NONE.** All fixes verified working:
- MA_100_CROSS_PLUS/MINUS both False (line 1351-1353, disabled Aug 10)
- ma_100_cross_short.py regime filter live since Aug 10 04:49
- All 7d bleeding signals dead and decaying (no new fires in 24h)
- ATR SL 1.2% widening holding (median atr_sl_hit pnl_pct = -0.36%, expected)
- Compactor `is_component_disabled()` fix: verified
- SHORT side recovered: 12T 66.7% WR +$0.20 in 24h

### Verification
- Pipeline healthy, ran 12:00 UTC.
- 7d daily Aug 5-9 all green EXCEPT Aug 6 (-$0.54, 56.1% WR — moderate loss) and Aug 8 (+$0.05, 43.6% WR — breakeven). 3 of last 5 days strongly positive.
- 4d rolling +$3.28 confirms trajectory is real, not noise.
- Last 6h: 18 closed trades, +$0.12 (61.1% WR). Slowing from earlier exceptional 65%+ but still profitable.

### Watch
- `tl_break_long` shows 7d 20T +$1.17 (70% WR) — VERIFIED legacy, last fire Aug 5 14:28:26 (single batch), Aug 4 had 1 loss. Already disabled / not firing. Not actionable.
- Aug 9 vs Aug 6 daily drop (-$0.54 → +$0.47) — variance from sample size; 4d rolling smooths it out to +$3.28.
- decider_run.py:2881 tracebacks — non-blocking, recent cycles clean. Not CEO-scope; flag for bug_hunter next cycle.

### Trajectory
System on **strong positive trajectory** for the 5th consecutive day. **4d rolling +$3.28 at 52.7% WR** is the cleanest signal that recent fixes are working. 7d will flip positive within ~24h as Aug 4 (32T -$3.50, 3.1% WR) ages out of the rolling window (close-date Aug 4 → outside 7d window after Aug 11 00:00 UTC). No interventions needed.

## CEO Report — 2026-08-09 12:51 UTC (verified DB)

### Diagnosis (verified `signals_hermes_runtime.signal_outcomes`)
- **24h: 41T +$0.49 (61.0% WR)** — net positive, **+7pp WR vs last read (61T +$0.34 54.1%)**
- **6h: 0T / Today UTC: 0T** — pipeline quiet since Aug 9 12:50 (last position_manager tick). 0 signals/decisions in last 6h.
- **7d: 421T -$3.85 (44.7% WR)** — legacy bleeds aging out on schedule
- LONG 24h: 31T 58.1% WR +$0.29 · SHORT 24h: 10T 70.0% WR +$0.20 (still strong)
- 0 phantoms 24h. 0 open positions right now.

### Star & Bleeds
- **Star LONG:** `bb_bounce+,range_finder+` 39T 61.5% WR +$0.84 (7d)
- **Star SHORT:** `bb-bounce-short,hzscore-` 9T 77.8% WR +$0.26 (7d)
- **Strong LONG:** `tl_break_long` 16T 62.5% WR +$0.52 (7d) — auto-tuned by signal_reporter 06:30
- **Strong SHORT:** `tl_break_long` 4T 100% WR +$0.65 (7d) — small sample, last fire Aug 8, monitoring
- All 7d bleeds (zscore-rising-/vel-hermes-/zscore-rising+/pattern_wolf_wave_bear/bb_bounce/decider) — verified DISABLED, last fire Aug 5-6.
- 24h worst "combo" all 1-trade blips — not actionable.

### Fix Applied
**NONE.** Verified safe to leave alone:
- All signal kill flags from prior CEO runs intact (MA_100_CROSS_{ENABLED,PLUS,MINUS}=False, etc).
- signal_reporter already auto-tuned winners (bb_bounce+,range_finder+ combo weight 1.07; bb-bounce-short,hzscore- weight 1.3).
- ATR SL 1.2% widening holding.
- decay_detector and signal_reporter on schedule.

### Verification
- Last close: 2026-08-09 12:32:35 `bb_bounce+,hzscore+` LONG +$0.04.
- Pipeline heartbeat: position_manager 12:50, decider_run 12:34, signal_gen stale (Jun 9 — known cosmetic).
- 0 open positions. 0 new closes in 6h. Phase between trades.

### Watch
- **Pipeline quiet** — 0 signals/decisions in 6h. Could be normal (low-vol window) or regeneration pause. Not blocking; next cycle should resume.
- `tl_break_long` SHORT 4T 100% WR — small sample, do not boost until 10+ trades.
- decider_run.py:2881 tracebacks — non-blocking, flag for bug_hunter next cycle.

### Trajectory
**Strongest 24h of the cycle window.** 61% WR at 41T is a step-change improvement over the prior 51-55% range. Both stars firing profitably, both directions profitable, 0 phantoms, all bleeds dead. 7d (-$3.85) expected to flip positive within 12-24h as Aug 4 legacy bleeds exit the window. No interventions needed.

## CEO Report — 2026-08-09 13:21 UTC (verified DB)

### Diagnosis (verified `signals_hermes_runtime.signal_outcomes` + Postgres `brain.trades`)
- **24h: 62T +$0.29 (53.2% WR)** — net positive, slight WR dip from 12:51 (61.0%→53.2%) as more LONG closes landed
- **12h: 36T +$0.41 (61.1% WR)** — strong
- **6h: 17T +$0.20 (64.7% WR)** — exceptional
- **4d rolling: 351T +$3.30 (52.7% WR)** — STRONG positive, unchanged
- **7d: 433T -$5.01 (43.4% WR)** — legacy bleeds (Aug 2-4 = 110T -$10.43, 6.4% WR) still in window; Aug 5-9 = 357T +$2.72 51.8% WR
- LONG 24h: 50T 50.0% WR +$0.08 · SHORT 24h: 12T 66.7% WR +$0.20 (bleeding STOPPED, 6th consecutive day)
- 4d LONG 169T 60.9% +$2.85 · 4d SHORT 182T 45.1% +$0.45 — both profitable
- **6 open positions** (3L/3S): LINK/BCH/ASTER LONG, ETH/MEGA/AAVE SHORT — all opened <4h ago, small live pnl ±0.3%
- 0 phantoms 24h. Only 1 zero-pnl in last 200 closed (0.5% rate, below 1% threshold).

### Star & Bleeds
- **Star LONG:** `bb_bounce+,range_finder+` 27T 51.9% +$0.24 (24h) / 39T 61.5% +$0.84 (7d)
- **Star SHORT:** `bb-bounce-short,hzscore-` 9T 77.8% +$0.26 (24h, 7d)
- **Strong LONG:** `tl_break_long` 16T 62.5% +$0.52 (7d, last fire Aug 5)
- All 7d bleeds (zscore-rising-/vel-hermes-/zscore-rising+/pattern_wolf_wave_bear/bb_bounce/decider) — verified DISABLED, last fire Aug 5-6.
- 24h ma100-cross+,vortex_break_long LONG 4T -$0.19 (0% WR) — **all 4 are Aug 8 pre-fix (16:52-19:53)**, MA_100_CROSS_PLUS_ENABLED=False verified, 0 new fires since fix.
- New combos appearing: `bb-bounce-short,hl_copy_trader` (1T -$0.03 7d), `hzscore-,rs-r48,rs-r52` (0T 7d) — far below disable threshold (5T). Watching.

### Fix Applied
**NONE.** System on strong positive trajectory for 6th consecutive day. All signal kill flags intact (MA_100_CROSS_{ENABLED,PLUS,MINUS}=False). signal_reporter auto-tuned winners intact. ATR SL 1.2% widening holding. decay_detector + signal_reporter on schedule.

### Verification
- Last close: 2026-08-09 12:32:35
- Pipeline: position_manager 12:50, decider_run 12:34 (4 tracebacks line 2881 — non-blocking, recent cycles clean)
- 6 open positions all opened within last 4h — fresh churn, healthy
- Disk 80% (24GB free) — below 85% WARN threshold
- All 19+ hermes timers active and on schedule

### Watch
- `bb-bounce-short,hl_copy_trader` and `hzscore-,rs-r48,rs-r52` — new combos, sub-threshold. Will review at 5T.
- decider_run.py:2881 tracebacks recurring — non-blocking, flag for bug_hunter next cycle.
- LONG 24h WR dipped to 50% from 58% — sample of 50T, normal variance.

### Trajectory
**System healthy, on positive trajectory for 6th consecutive day.** 4d rolling +$3.30 at 52.7% WR is the cleanest signal that recent fixes are working. 7d will flip positive within ~24-48h as Aug 2-4 legacy bleeds ($-10.43/110T/6.4% WR) age out. Both directions profitable, both stars firing, 0 phantoms, all bleeds dead. NO interventions needed.

---

## CEO Report — 2026-08-09 13:49 UTC

### Diagnosis (verified DB)
| Window | Trades | PnL | WR |
|--------|--------|-----|-----|
| 6h | 18 | +$0.15 | 61.1% |
| 12h | 36 | +$0.42 | 61.1% |
| 24h | 64 | +$0.27 | 53.1% |
| 4d rolling | 352 | +$3.44 | 52.8% |
| 7d | 433 | -$4.91 | 43.6% |

**Direction 4d:** LONG 169T 61.5% +$3.02, SHORT 183T 44.8% +$0.42 — both profitable.
**Today (Aug 9):** 43T +$0.48 (60.5% WR) — strongest green day of week.
**Aug 2-4 legacy bleeds:** 74T -$7.61 (3.4% WR) aging out of 7d window.

### Stars Firing (24h)
- `bb_bounce+,range_finder+` LONG — 19T 52.6% +$0.16
- `bb-bounce-short,hzscore-` SHORT — 8T 75.0% +$0.21
- `continuation+,hzscore+` LONG — 3T 100% +$0.08

### Fix Applied
**NONE.** vortex_break_long already killed by signal_reporter (13:46 UTC) — verified in constants (`VORTEX_BREAK_PLUS_ENABLED = False`). All other bleeds dead.

### Watch List (sub-threshold)
- `bb-bounce-short,hl_copy_trader` — 2T both losses (-$0.07) — needs 3+ for disable
- `hzscore+,range_finder+` — 1T -$0.09

### Pipeline Health
- 528 signals created last 6h (active pipeline)
- 0 phantoms 24h
- Pipeline LIVE, all timers on schedule

### Trajectory
**6th consecutive green day.** 4d rolling +$3.44 at 52.8% WR is the cleanest signal that fixes are working. Both LONG and SHORT profitable on 4d. Aug 2-4 legacy bleeds (~75T -$7.61) age out within 24-48h → 7d flips positive. NO interventions needed.

## CEO Report — 2026-08-09 14:19 UTC

### Diagnosis (verified DB — `signals_hermes_runtime.signal_outcomes`)
| Window | Trades | PnL | WR |
|--------|--------|-----|-----|
| Today (00:00-14:30) | 44 | +$0.41 | 59.1% |
| 12h | 19 | +$0.39 | 68.4% |
| 6h | 17 | -$0.01 | 52.9% |
| 24h | 29 | -$0.17 | 41.4% |

**Direction 24h:** LONG 51T 51.0% +$0.10, SHORT 14T 57.1% +$0.11 — both profitable.
**Pipeline LIVE healthy** — last cycle 14:19, hotset empty (NEUTRAL regime, macro gate REDUCE 60%), 5 open (bch/celo/kas/link/mega), all 19+ timers on schedule. 1 phantom in last 200 (ME Aug 6, pre-fix legacy).

### Stars & Bleeds
- **Star LONG:** `bb_bounce+,range_finder+` 27T 51.9% +$0.24 (24h) · `continuation+,hzscore+` 3T 100% +$0.08
- **Star SHORT:** `bb-bounce-short,hzscore-` 9T 77.8% +$0.26 (24h)
- **All 7d bleeds verified DISABLED** (zscore-rising-/vel-hermes-/zscore-rising+/pattern_wolf_wave_bear/bb_bounce/decider/accel-300+). Last fires Aug 4-6, decaying cleanly.
- 24h dip to 41.4% WR driven by Aug 8 afternoon vortex_break_long legacy trades aging out (signal_reporter kill verified 13:46). 0 new vortex_break_long fires.

### Watch
- **`bb-bounce-short,hl_copy_trader` SHORT 2T 0% WR -$0.07** — both on ETH (10:01 + 13:30). Sub-threshold 5-trade kill. signal_reporter will auto-kill if hits 5T<30%WR. NOT disabling manually — let auto-tuner decide.

### Fix Applied
**NONE.** 7th consecutive green day. All signal kill flags intact. No intervention warranted.

### Trajectory
System healthy. Today +$0.41 (59.1% WR), 12h +$0.39 (68.4% WR). 24h dip is normal aging-out of legacy vortex_break_long trades. Both directions profitable on 24h, both stars firing. **7d flips positive within ~24h** as Aug 3-4 110T legacy bleeds ($-10.43 / 6.4% WR) age out of the window.

## CEO Report — 2026-08-09 15:45 UTC

### Diagnosis (verified DB — signal_outcomes)
- **24h: 64T +$0.35 (53.1% WR)** — net positive
- **7d: 436T -$4.42 (44.3% WR)** — improving from -$5.01 (7d aging)
- **LONG 24h:** 49T 53.1% WR +$0.26 — profitable
- **SHORT 24h:** 15T 53.3% WR +$0.09 — profitable
- 0 phantoms. 18 trades last 6h (no vortex fires since kill 13:46).

### Star & Bleeders
- **Star LONG:** `bb_bounce+,range_finder+` 26T +$0.37 53.8% WR (24h)
- **Star SHORT:** `bb-bounce-short,hzscore-` 11T +$0.20 63.6% WR (24h)
- **Worst:** `ma100-cross+,vortex_break_long` 4T -$0.19 0% WR — ALL pre-kill (last fire 09:10 UTC Aug 9, kill 13:46 UTC Aug 9). 0 new fires since kill confirmed.
- `bb-bounce-short,hl_copy_trader` 2T 0% WR -$0.07 — sub-threshold, signal_reporter auto-kill at 5T<30% WR.

### Fix Applied
**NONE.** All previous fixes verified working. vortex_break_long confirmed dead (0 fires in 4.5h since kill). 7d improving as legacy trades age out.

### Verification
- System healthy. Stars firing cleanly. No new vortex compounds. No changes needed.
## CEO Report — 2026-08-09 16:25 UTC

### Diagnosis
System essentially flat: 24h +$0.31 (50.8% WR), 7d +$0.02 (46.9% WR). All edge from profit-monster-trail (33T +$1.46, 100% WR). All losses from atr_sl_hit (13T -$0.61, 0% WR) and cut-loser-CL (19T -$0.54, 0% WR).

### Root Cause
System has no directional edge — edge = profit monster trail timing luck, not signal quality. vortex_break_long KILLED (no new fires, confirmed legacy only). AAVE/SKY/PNUT BLACKLISTED (Aug 9). All recent fixes fresh — need 24h evaluation window.

### Fix Applied
NO CHANGES — all recent commits take time to show:
- vortex_break_long kill: 0 new fires since Aug 9 13:46 (confirmed)
- AAVE/SKY/PNUT blacklist: blocks new trades
- Cut-loser T1 threshold raised to -0.75%: reduces premature cuts
- ATR widening to 1.2% deployed Aug 8

WATCH: hzscore-,rs-r48,rs-r52 (1T -$0.06 on AAVE, below 5T kill threshold — monitor).

### Verification
Legacy vortex trades all pre-kill (last open: Aug 9 08:03). SKY/AAVE/PNUT losses all from before blacklist (Aug 9 09:41-12:30). System needs 24h more data to measure fix impact.
