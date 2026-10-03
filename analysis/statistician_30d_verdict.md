# Statistician Verdict — 30-Day Trade Data Gap Analysis

**Window:** 2026-09-03 → 2026-10-03 (30 days back from latest `open_time`)
**Source:** PostgreSQL `brain.trades` via `_secrets.BRAIN_DB_DICT` (source of truth per AGENTS.md)
**Method:** All numbers below were produced by executed code (`analysis/statistical_gap_analysis.py`, `_p2.py`, `_p3.py`, `_p4.py`). Wilson score CIs for proportions, percentile bootstrap (5000 resamples) for mean PnL, two-proportion z-tests, exact sign tests. Live DB — row count drifted 973→976 during analysis; figures are a snapshot.

---

## Statistician Verdict

- **Sample Size**: n = 973 closed trades (**ADEQUATE** for overall metrics; per-signal cells mostly INSUFFICIENT — see Section 2)
- **Measured Win Rate**: 53.81% (501 wins / 931 non-flat trades; 42 flat excluded)
- **Confidence Interval**: [50.60% – 56.99%] at 95% (Wilson) — significantly above coin-flip (sign test p = 0.0435)
- **Statistical Significance**: **NO** — for profitability. Bootstrap 95% CI on mean PnL = **[-0.01, +0.01] USDT/trade**, includes zero. Total PnL −2.23 USDT computed (−3.10 USDT Hyperliquid-realized) on ~12,767 USDT notional — statistically indistinguishable from zero.
- **Edge Assessment**: **NO proven edge at system level.** The system is break-even-negative: win rate is real but R:R is structurally against it (see Root Cause). One qualified signal-level edge exists (volume-breakout, n=23 < 30 → NEEDS MORE DATA). One qualified negative edge exists and is actionable (SHORT RSI<40).
- **Recommendation**: **Inconclusive on profitability — proceed only with the single targeted fix below; do not scale size, do not add signals.** The system needs ~+0.9pp win rate OR ~3.5% avg-loss reduction to break even; more samples at current config will not create an edge that the R:R structure forbids.
- **Root Cause**: **Entry-condition leak on oversold SHORTs + structurally thin reward:risk.** Avg win +0.1213 USDT vs avg loss −0.1465 USDT (R:R 0.83); breakeven WR needed = 54.71%, observed = 53.81% (gap −0.89pp). The exit engines are NOT the problem (verified: cut-loser realizes median raw −1.07% at design level, 3-min median lag). The single highest-EV change: **enforce an execution-time RSI floor (RSI ≥ 40) on ALL SHORT entries** — the 86 leaked oversold SHORTs lost −5.04 USDT, more than the entire system's 30-day loss.

---

## 1. Overall Performance

| Metric | Value |
|---|---|
| Closed trades | 973 (501 W / 430 L / 42 flat) |
| Total PnL (computed, gross of fees) | **−2.23 USDT** |
| Total PnL (HL-realized, `hype_realized_pnl_usdt`) | **−3.10 USDT** (959/973 populated) |
| Win rate (excl. flat) | 53.81% — CI [50.6, 57.0] |
| Avg win / avg loss | +0.1213 / −0.1465 USDT |
| R:R (win/loss) | **0.828** |
| Breakeven WR needed | **54.71%** (observed gap: **−0.89pp**) |
| Expectancy | −0.0024 USDT/trade |
| Profit factor | 0.965 |
| Bootstrap 95% CI mean PnL | [−0.01, +0.01] → includes zero |
| Total notional traded | ~12,767 USDT |

**Fee caveat (finding):** `pnl_usdt` in brain.trades is computed GROSS (`pnl_utils.py`: `calc_notional × raw_move`; fees are computed into `net_pnl` but not stored in the analyzed column; the `fees` column is empty for all 973 trades). HL-realized PnL is 0.73 USDT worse than computed — ~0.09% round-trip fee drag. Any breakeven target must clear fees. **Severity: MEDIUM. Fix: store `net_pnl` (or fees) per trade in analytics columns.**

**Weekly PnL (computed):**
| Week (ISO start date) | n | PnL |
|---|---|---|
| 2026-08-31 | 127 | −1.88 |
| 2026-09-07 | 331 | +2.45 |
| 2026-09-14 | 205 | +0.71 |
| 2026-09-21 | 122 | **−4.98** ← worst week drives the month |
| 2026-09-28 | 191 | +1.33 |

Last 7 days: **+2.05**. Days 8–30: −4.42. The 30-day loss is concentrated in one bad week + persistent micro-bleed — consistent with noise around a ~zero edge, not a constant bleed.

## 2. Signal Performance (n ≥ 10 only claimed; smaller = NEEDS MORE DATA)

24 signal labels have n ≥ 10 (11 positive PnL / 13 negative). Normalized to families, the material cells:

| Family | n | WR | PnL | p(WR > breakeven) | Verdict |
|---|---|---|---|---|---|
| **volume-breakout** | 23 | 69.6% | **+3.31** | **0.0006** | Significant edge vs breakeven — but **n < 30 → NOT high confidence; NEEDS MORE DATA** |
| open_skies | 19 | 70.6% | +1.56 | 0.037 | low-n, INCONCLUSIVE; also **stopped firing after Sep 18** (all 31 raw trades in early half — sample is stale) |
| bb_bounce | 51 | 68.0% | +0.99 | 0.235 | inconclusive |
| pump_chain (all) | 44 | 68.2% | +1.10 | 0.214 | inconclusive |
| pump-chain (hyphen, all) | 215 | 51.7% | +1.32 | 0.568 | inconclusive; **edge decayed: early-half +1.96 @60.3% WR → late-half +0.08 @48.1%** — watch |
| doji-bottom | 14 | 76.9% | +0.79 | 0.062 | low-n, NEEDS MORE DATA |
| pullback-entry | 126 | 52.5% | −0.07 | 0.967 | breakeven, no edge |
| pump-chain- (SHORT) | 122 | 56.0% | −0.29 | 0.843 | no edge |
| **ema300_dip (all variants)** | 51 | 44.0% | **−3.01** | **<0.0001** | Was a **significant loser** — but **all 51 trades pre-date Sep 18**; signal family already stopped/disabled. Bleed self-healed. |
| mover | 35 | 60.0% | −1.01 | 0.219 | flipped winner→loser mid-window (early +0.95 @82.6% / late −1.96 @16.7%); both halves n<30 — **NEEDS MORE DATA, do not scale** |
| coiled_spring / sma20_dip / slow_grind / trend_purity | 12–21 each | 40–47% | −0.65..−0.90 | 0.07–0.21 | all pre-Sep-18 only; already disabled/pennalized by regime gate |

**Win-rate sanity check (per your rule):** All WR figures above use non-flat trades from the correct signal label; combined multi-source labels (e.g. "pump-chain-,rs-r68") were normalized to primary family — 54 tiny families (n<5) combined for −1.53 USDT, no hidden winner there.

## 3. Direction Analysis

| Direction | n | WR | 95% CI | PnL | Bootstrap mean CI |
|---|---|---|---|---|---|
| LONG | 606 | 55.2% | [51.1–59.2] | **+1.65** | [−0.01, +0.02] includes 0 |
| SHORT | 367 | 51.5% | [46.4–56.7] | **−3.88** | [−0.03, +0.01] includes 0 |

WR difference LONG vs SHORT: z = 1.088, **p = 0.277 — NOT significant.** SHORTs are the PnL drag but not statistically distinguishable from LONGs on win rate alone. The drag is concentrated in one SHORT sub-segment (Section 7).

## 4. Regime Analysis (volatility_regime)

| Regime | n | WR | PnL | avg/trade |
|---|---|---|---|---|
| EXTREME | 377 | 53.5% | **+4.57** | +0.012 |
| HIGH | 347 | 53.6% | −3.18 | −0.009 |
| NORMAL | 233 | 53.6% | −4.36 | −0.019 |
| FLAT / UNKNOWN | 16 | — | +0.74 | NEEDS MORE DATA |

Regime × Direction (material cells):
- **LONG + EXTREME: n=207, +5.24 — the system's best cell.** Held up in both window halves (early +2.21 / late +3.03) and across ISO weeks (wk37 +1.70, wk38 +2.80, wk40 +2.46; only wk39 negative). Driven by pump_chain LONG EXTREME (n=89, +4.00) and volume_breakout LONG EXTREME (n=14, +3.47). **Promising, NOT proven** — WR CI [47.1–60.6] includes 50%.
- NORMAL regime lost money in 4 of 5 weeks (−0.43, −1.95, −1.38, +0.14, −0.74) — a persistent bleed zone, no single dominant signal.
- EXTREME SHORT −0.67/170, HIGH SHORT −1.28/124, HIGH LONG −1.90/223, NORMAL LONG −2.42/162 — all mild negative.

## 5. Filter Impact

**Data available:** pipeline logs (Sep 29 → Oct 3 only — full 30-day logs rotated; ~5-day sample) + `signal_cooldowns` (59 rows, mostly btc_pump_rider cooldowns) + `token_blocklist` (3 stale tokens). `missed_opportunity` flag = 0 trades in window. `ab_results` table is **stale (April 2026, all metrics zeroed)** — no live A/B counterfactual exists. **Severity: MEDIUM. Fix: either maintain ab_results or add shadow-mode logging of blocked-trade outcomes.**

**Blocked-trade counterfactual** (1,274 unique token/dir/gate/day events; 1,271 simulated against `candles_1m` with the system's own exit model — trail +0.4%/0.2%, cut −1.0%; model validated on 174 actual same-period trades: bias +0.056%/trade optimistic, corr 0.405 — **directional only**):

| Gate (top by volume) | n blocked | Modeled WR | Modeled PnL (raw % sum) | Directional read |
|---|---|---|---|---|
| LONG-NEUTRAL (confluence gate, "standalone bypass denied") | 243 | 71.2% | +25.9% (+4.42 USDT raw) | **May be blocking winners** — largest potential over-block; ~+2.1 USDT after bias correction |
| SHORT-NEUTRAL | 190 | 65.8% | +6.5% | slight over-block |
| CTX-GATE | 114 | 63.2% | +9.7% | slight over-block |
| PUMP-CHAIN-SHORT-HIGH | 104 | 66.3% | +12.2% | possibly over-blocked (gate cites 48% WR; 30d actual SHORT HIGH pump-chain = 54.5% WR, −0.36 ≈ breakeven) |
| SHORT-CONTINUUM (BTC not STRONG_NEG) | 187 | 61.5% | −6.8% | correctly filtering |
| HALL-SHAME (token 30d WR < 55%) | 88 | 58.0% | −10.3% | correctly filtering |
| PUMP-CHAIN-SHORT-RSI-MIN (RSI<40) | 109 | 55.0% | −5.6% | correctly filtering — consistent with executed-trade evidence (Section 7) |
| PUMP-CHAIN-SHORT-DEAD-HOUR | 31 | 45.2% | −11.3% | correctly filtering |

**Aggregate if all blocked trades had executed: +5.12 USDT raw over ~5 days; after model-bias correction ≈ flat (−0.7 USDT).** Filters as a whole are NOT the profitability gap. The composition matters: NEUTRAL-regime LONG confluence blocks plausibly suppress winners; the RSI/dead-hour/hall-of-shame SHORT blocks are doing their job.

**Recommendation:** Do NOT blanket-unfreeze. If testing, loosen only LONG-NEUTRAL for the top positive families (bb_bounce, volume-breakout, pump_chain LONG) in shadow mode first.

## 6. Time Analysis (UTC) — EXPLORATORY ONLY

- **12 of 24 hour-buckets negative.** With a ~zero edge and 24 buckets, roughly half negative is expected by chance — **no hour-of-day finding is significant without multiple-comparison correction.** (Worst: 03:00 −2.59/n=49. Best: 06:00 & 19:00 +2.15.) Per AGENTS.md philosophy, no time-of-day action recommended.
- **Tuesday: n=160, WR 45.0% (CI 37.3–53.0 — includes 50%), PnL −6.60.** Drill-down shows the loss is concentrated in known losing signals (pump_chain −1.54, pullback_entry −1.08, ema300_dip_short −0.81, sma20_dip −0.73) — **not an independent day-of-week effect.** Same for 02:00–05:59 UTC (−5.07): pump_chain dominates. **No time-based filter justified.**

## 7. Edge Detection

**System level:** Sign test 501W/430L, p = 0.0435 → win rate is significantly above coin-flip. But mean PnL bootstrap CI [−0.01, +0.01] includes zero → **the win-rate edge does not survive the R:R structure.** R:R 0.828 forces breakeven WR 54.71% vs observed 53.81%.

**Qualified positive cells:**
- volume-breakout family: p = 0.0006 vs breakeven — **n = 23 < 30 → NEEDS MORE DATA, not "proven", not "high confidence."**
- LONG RSI ≥ 40 (RSI-recorded subperiod Sep 14+): n=241, +4.51, avg +0.0187, **bootstrap CI [−0.006, +0.046] includes zero → INCONCLUSIVE.**
- LONG + EXTREME: n=207, +5.24, consistent across halves/weeks — **promising, CI includes 50% WR → not proven.**
- PM-trail exit engine: n=310, 82.3% WR, +19.03 — the only exit engine that prints; its exits are statistically solid on their own.

**Qualified negative cell (the one real, actionable edge):**

| Segment | n | WR | PnL | Bootstrap mean CI | Verdict |
|---|---|---|---|---|---|
| **SHORT entries with entry_rsi_14 < 40** | **86** | **34.1%** (CI 24.8–44.9) | **−5.04** | **[−0.093, −0.023] excludes zero** | **Real negative edge — statistically significant** |
| SHORT RSI ≥ 40 (control, same period) | 70 | 52.9% | −0.60 | [−0.046, +0.028] | flat |
| LONG RSI < 40 | 46 | 58.5% | −0.35 | [−0.042, +0.028] | flat (small-n) |

Difference SHORT RSI<40 vs ≥40: −0.050/trade, z = −1.93, **p = 0.054 (borderline at 95% — reported honestly)**. The segment's own CI excluding zero + mechanistic consistency (BANANA lesson in AGENTS.md; the PUMP-CHAIN-SHORT-RSI-MIN gate exists precisely because this pattern loses) make this the highest-confidence actionable finding.

**Leak sources within SHORT RSI<40** (where the existing gate is NOT protecting):
- pump_chain SHORT: n=52, WR 40.4%, −1.81 — **the PUMP-CHAIN-SHORT-RSI-MIN gate leaks** → consistent with AGENTS.md detection-time vs execution-time RSI gap (gate checks detection RSI; entry_rsi_14 recorded at execution; RSI crosses the threshold in between)
- pullback_entry SHORT: n=9, WR 0%, −1.67 — **no RSI gate on this path at all**
- mover_ SHORT: n=5, −0.73; accel_300_: n=8, −0.34; grind_trend_: n=3, −0.33
- By regime: EXTREME −3.02/60, HIGH −1.37/14 (WR 7.1%), NORMAL −0.64/11 — leaks everywhere.

**Caveats:** entry_rsi_14 populated only from Sep 14 (feature_recorder start) — RSI conclusions rest on the 518-trade subperiod (50.2% WR, −2.89 total). 533 window trades have NULL RSI; SHORT trades with NULL RSI were +1.52, so the within-period comparison (RSI<40 vs ≥40, both Sep 14+) is the valid one — and it holds.

**Time/exit structure supporting findings:** Cut-loser exits (n=92) reconstruct to **median raw exit −1.07% from entry with median 3-min lag from the −1% touch** (56/64 never recovered above −0.5% — cutting at −1% was correct 87.5% of the time). Exit engines fire at design levels; **the gap is in entries, not exits.** Note: raw signal `pnl_pct` is LEVERAGED (× lev 3–5); do not read −4.81% leveraged as −4.81% price move (analysis pitfall caught during this audit).

## 8. Root Cause — What Single Change Most Improves Profitability

**Do this: enforce an execution-time RSI floor (RSI ≥ 40) on ALL SHORT entries — every signal path, re-validated at execution time, not detection time.**

Evidence chain:
1. The leaked segment is real: n=86, WR 34.1%, −5.04 USDT, bootstrap CI excludes zero — **larger than the entire 30-day system loss (−2.23 computed / −3.10 HL-realized).**
2. The fix is proven in concept: PUMP-CHAIN-SHORT-RSI-MIN blocked 109 events in 5 days whose modeled outcome was negative (−5.6%) — the gate works where it applies.
3. The leak is mechanical, not philosophical: AGENTS.md already documents the detection-vs-execution RSI gap (CFX example) and the BANANA oversold-SHORT lesson. pullback_entry- and other paths simply have no gate.
4. Expected recovery at current scale: **~+5 USDT/30d → flips the month from −2.4 to ~+2.6 computed (−3.1 to ~+1.9 HL-real), before any other change.** This alone reaches breakeven-plus at present size.

Implementation notes (for the team, not executed here):
- Add the RSI check inside the execution gate path (decider_run exec gates) — recompute RSI from fresh candles at execution, fail-closed on stale data (pattern already exists: EXEC-RSI-HARD-FLOOR).
- Extend to all SHORT sources, minimum pullback_entry-, mover_, accel_300_ variants.
- Keep the existing pump-chain gate; fix its leak by re-checking at execution.
- After committing signal/gate changes, **restart the pipeline** (AGENTS.md: new code must be loaded).

**What NOT to do (data says no):**
- Do not add time-of-day or day-of-week blocks (multiple-comparison noise; losses trace to signals, not clocks).
- Do not unfreeze NORMAL-regime LONGs (bleed zone, 4/5 weeks negative).
- Do not scale volume-breakout yet (n=23 < 30 — promising, needs samples).
- Do not loosen cut-loser (it fires correctly; loosening re-opens the -1% cut that was right 87.5% of the time).
- Do not treat the 30-day −2.23 as a "big loss" to panic-fix — it is within noise; the fix is surgical, not structural.

**Secondary items (monitor / separate tickets):**
- pump_chain family decay (early 60.3% WR → late 48.1%) — re-evaluate regime routing weekly; largest family by volume.
- LONG-NEUTRAL confluence gate: candidate for a shadow-mode loosening test on top-3 positive families only.
- Fee accounting: store net_pnl per trade; breakeven targets must clear ~0.09% round-trip.
- ema300_dip / coiled_spring / sma20_dip / slow_grind / trend_purity / open_skies: all stopped mid-window — confirm intentional disablement vs silent breakage (see sideways findings).

---

## Sideways Findings (see something, say something)

| # | Finding | Severity | Suggested fix |
|---|---|---|---|
| 1 | `ab_results` table stale since April 2026, all metrics zeroed — cut_loser.py has `ab_group` config but no live counterfactual logging | MEDIUM | Re-enable A/B writes or add shadow-mode blocked-trade outcome logging |
| 2 | `entry_rsi_14` missing for 533/973 window trades (feature_recorder started 2026-09-14); `mfe_pct` only populated in final week; `mae_pct` values look wrong (min +0.001%, avg positive — adverse excursion stored as positive magnitude inconsistently) | MEDIUM | Backfill guard + normalize MAE sign convention |
| 3 | `hype_notional_usdt` column does not exist (actual: `hl_notional_usdt`) — script-facing naming mismatch | LOW | Alias or rename consistently |
| 4 | `fees` column empty for all window trades; `net_pnl` computed in pnl_utils but not persisted to trades | MEDIUM | Persist fees/net_pnl (see Section 1) |
| 5 | ema300_dip, coiled_spring, sma20_dip, slow_grind, trend_purity, open_skies all produce zero trades after ~Sep 18 — confirm intentional disablement vs import/runtime breakage (e.g., defunct `signal_gen` imports flagged previously) | MEDIUM | Verify signal files load; check signals.log for errors |
| 6 | 59 active `signal_cooldowns` rows are all `btc_pump_rider` with expiry dates into Nov 2026 — check whether these are intentional or stuck | LOW | Audit cooldown expiries |
| 7 | `token_blocklist` contains 3 tokens with reason "Stale position verified 2026-04-03" (SKR/STG/STRAX) — 6 months stale | LOW | Re-verify or purge |
| 8 | Analysis pitfall (documented for future analysts): `trades.pnl_pct` is LEVERAGED (raw × lev); reading it as price move overstates losses ~3–5× (led to a false "cut-loser bleeds to −4.8%" hypothesis, disproved by candle-path reconstruction: actual raw exit median −1.07%) | INFO | Document in brain/trade-stats notes |

---

## Reproduction

```bash
cd /root/.hermes && python3 analysis/statistical_gap_analysis.py      # overall/signal/direction/regime/time/exit
cd /root/.hermes && python3 analysis/statistical_gap_analysis_p2.py   # R:R structure, families, exit engines, RSI buckets
cd /root/.hermes && python3 analysis/statistical_gap_analysis_p3.py   # exit calibration, blocked-trade counterfactual, model validation
cd /root/.hermes && python3 analysis/statistical_gap_analysis_p4.py   # date-splits, EXTREME-LONG check, multiple-comparison guard
```

*All figures executed against live `brain.trades` on 2026-10-03. No number in this report is estimated from memory.*
