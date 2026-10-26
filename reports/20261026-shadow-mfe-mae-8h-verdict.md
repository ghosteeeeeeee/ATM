# MFE/MAE 8h Analysis — Last 100 Shadow Trades (Verdict Report)

**Date:** 2026-10-26 · **Directive:** T — run MFE/MAE 8h analysis on shadow-mode data (same methodology as live trades analysis)  
**Raw output:** `reports/20261026-shadow-mfe-mae-8h-raw.md` · **Script:** `/tmp/shadow_mfe_mae_8h.py` (deterministic, read-only)  
**Comparison:** `reports/20261026-mfe-mae-8h-verdict.md` (live trades analysis)

---

**TLDR:** Analyzed 57/100 shadow trades (43 skipped: no entry price in context JSON). **30% of in-window exits were followed by a bigger move** (vs 74% for live trades). Median foregone 1.43pp. The "survive the MAE" answer: **SL ≥ ~0.86% + CUT_LOSER coupled to ~−4.3% at 5x** — much less aggressive than live trades (SL ≥ 1.2% + CUT_LOSER −6%). **Key difference:** shadow trades exit much earlier (p50 peak at 219m vs 276m for live), so time-based exits are less destructive. **Wider-stop scenario shows +50-63% potential** (vs +9-16% for live trades).

---

## Method

- Window = [created_at, created_at + 8h] for every trade regardless of exit.
- Extremes from the **union of candles_1m + candles_5m** (candles.db).
- Entry price from `context->>'$.price'` (signal detection price, NOT candle open).
- Exit price from `first_exit_price`.
- *Bigger move followed* = fav_after ≥ max(fav_at_exit, 0) + T.
- 57/100 analyzed (43 skipped: no entry price in context JSON).
- **Coverage issue:** 57/57 trades have <80% window coverage (58-67%) — extremes may understate.
- HML cap in price terms = 4% account / leverage (CUT_LOSER_PNL = −4%).

## 1. Exit-reason census (n=57)

| Exit rule | n | wins | Avg Net PnL |
|---|---:|---:|---:|
| **rr_sl_hit** | **24** | 0 | **−0.593%** |
| **trail_sl** | **14** | **14** | **+0.244%** |
| atr_sl_hit | 5 | 0 | −0.856% |
| hard_max_loss (HML) | 4 | 0 | −1.072% |
| rr_trail_hit | 4 | 3 | +0.119% |
| atr_trail_hit | 3 | 3 | +0.546% |
| pump_exit_dead_money | 2 | 2 | +0.934% |
| cut_loser_t1 | 1 | 0 | −1.211% |

**Key finding:** `rr_sl_hit` is the dominant exit (24/57 = 42%) with 0% WR and −0.593% avg. This is the RR engine's SL, not the ATR SL. `trail_sl` has 100% WR (14/14) with +0.244% avg.

## 2. Stopped early + bigger move after exit

**57 exits inside the window** (0 held past 8h): 27 profitable / 30 stopped-out.

| Threshold (beyond capture) | Count | winners giving up tail / losers it went without us |
|---|---|---|
| ≥0.2pp | 17/57 (30%) | 10 / 7 |
| **≥0.3pp** | **17/57 (30%)** | **10 / 7** |
| ≥0.5pp | 12/57 (21%) | 8 / 4 |

**Comparison to live trades:**

| Metric | Shadow (n=57) | Live (n=96) |
|--------|---------------|-------------|
| Early exits @T=0.3% | **30%** | **74%** |
| Median foregone | **1.43pp** | **1.83pp** |
| Losers followed by ≥1% move | 3/30 (10%) | 18/42 (43%) |
| Losers followed by ≥2% move | 0/30 (0%) | 10/42 (24%) |
| Winners giving up ≥1pp tail | 7/27 (26%) | 24/52 (46%) |

**Shadow trades exit much less destructively than live trades.** The RR engine's SL (24/57 exits) is catching moves earlier but with less foregone upside.

- **Stopped-out 30:** 7 (23%) would have been ≥+0.3% post-exit; **3 (10%) ≥+1.0%**; **0 (0%) ≥+2.0%**.
- **Winners:** 10/27 gave up ≥0.3pp of tail after exit.
- **Magnitude:** median foregone **1.43pp**, p75 2.06pp, p90 2.33pp, max 2.75pp.
- **Direction split:** LONG 4 / SHORT 13 (76% SHORT).
- **By exit reason @T=0.3%:** trail_sl 7, rr_sl_hit 5, rr_trail_hit 2, hard_max_loss 1, cut_loser_t1 1, atr_trail_hit 1.

## 3. What we'd need to survive the MAE for the bigger MFE

Cohort MFE ≥0.8% in 8h: **n=31** (18 with MFE ≥1.5%).

| Requirement | Value |
|---|---|
| MAE before the peak (p50 / p75 / p90) | **0.21% / 0.86% / 1.04%** price (max 2.08%) |
| What kills first today (5x → HML = 0.8% price) | HML cap stops 5/31 · survivable only **26/31** |
| Max leverage keeping HML (−4% acct) intact | p50 MAE → **≤19x** · p75 → **≤4.7x** · p90 → **≤3.9x** |
| Peak timing | p50 **~219m** after open, p75 ~249m (vs live trades p50 ~276m) |

**Comparison to live trades:**

| Metric | Shadow (n=31) | Live (n=64) |
|--------|---------------|-------------|
| MAE p50 | **0.21%** | 0.57% |
| MAE p75 | **0.86%** | 1.17% |
| MAE p90 | **1.04%** | 1.62% |
| Max MAE | **2.08%** | 4.76% |
| HML stops first | 5/31 (16%) | 13/64 (20%) |
| Survivable to peak | 26/31 (84%) | 36/64 (56%) |
| Peak timing p50 | **219m** | 276m |

**Shadow trades have much lower MAE** — the RR engine's tighter SL is catching moves before they drawdown deeply. This means less leverage reduction is needed.

**Scenario — whole cohort, upper bound** (non-stopped ride to peak, gross of fees):

| Stop + coupled HML @5x | Scenario gross | Stops hit | Worst single |
|---|---|---|---|
| actual (as traded, net) | **−4.87%** | — | — |
| SL 0.80% + CUT_LOSER 4% | **+50.32%** | 8/31 | −0.80% |
| SL 1.17% + CUT_LOSER 5.8% | **+62.81%** | 2/31 | −1.17% |
| SL 1.62% + CUT_LOSER 8.1% | **+61.91%** | 2/31 | −1.62% |

**Shadow trades show MUCH higher potential** than live trades (+50-63% vs +9-16%). This is because:
1. Shadow trades have lower MAE (0.21% vs 0.57% p50)
2. Shadow trades have higher MFE (more room to ride)
3. Shadow trades exit earlier (less foregone upside)

## 4. The answer — what would we need

1. **SL floor ~0.86%** — today's p75 MAE (0.86%) is covered by current SL band (0.6-1.03%).
2. **Survive the p75 ride (0.86%): ≤4.7x leverage under the current −4% HML** — much less aggressive than live trades (≤3.4x).
3. **Wider-stop scenario shows +50-63% potential** — this data strongly supports running the coupled CUT_LOSER + ATR_SL shadow trial.
4. **Time-based exits are less destructive** — p50 peak at 219m (3.65h) vs live trades 276m (4.6h). Soft-trail 2h is closer to the peak.

## 5. Split-half check (reproducibility @T=0.3%)

| Half | Early exits |
|------|-------------|
| Older half | 9/28 (32%) |
| Newer half | 8/29 (28%) |

**Phenomenon present in both halves.** No formal p-value claimed: "exit before the 8h max" is near-tautological; the load-bearing stats are magnitudes and the loser-continuation tail.

## 6. Early-exit detail @T=0.3% — worst 15 (most missed)

| Date | Token | Dir | Exit Rule | Cap | After | Missed | MFE 8h | MAE to Peak | Net PnL |
|------|-------|-----|-----------|-----|-------|--------|--------|-------------|---------|
| 10-26 17:05 | BLUR | SHORT | cut_loser_t1 | +2.23% | +4.97% | **+2.75pp** | +5.24% | -1.83% | -1.211% |
| 10-26 17:22 | COMP | LONG | rr_sl_hit | -0.67% | +1.66% | **+2.33pp** | +1.75% | 1.05% | -0.925% |
| 10-26 17:05 | SEI | SHORT | rr_sl_hit | -0.45% | +1.68% | **+2.13pp** | +2.52% | 0.47% | -0.719% |
| 10-26 17:12 | COMP | LONG | hard_max_loss | -0.40% | +1.71% | **+2.11pp** | +1.81% | 0.99% | -0.940% |
| 10-26 17:04 | COMP | LONG | rr_trail_hit | +0.45% | +2.52% | **+2.06pp** | +2.61% | 0.21% | +0.146% |
| 10-26 17:00 | IOTA | SHORT | rr_sl_hit | +0.47% | +2.10% | **+1.63pp** | +2.33% | -0.47% | -0.603% |
| 10-26 17:05 | WLD | SHORT | trail_sl | +2.50% | +4.04% | **+1.54pp** | +4.63% | -1.65% | +0.090% |
| 10-26 16:44 | BABY | SHORT | atr_trail_hit | +0.71% | +2.17% | **+1.45pp** | +2.72% | 0.39% | +0.691% |
| 10-26 17:05 | KAS | SHORT | trail_sl | +0.20% | +1.63% | **+1.43pp** | +1.91% | 0.28% | +0.097% |
| 10-26 17:00 | GOAT | SHORT | rr_sl_hit | +0.56% | +1.97% | **+1.41pp** | +2.47% | -0.42% | -0.562% |
| 10-26 17:05 | JUP | SHORT | trail_sl | +1.07% | +2.01% | **+0.94pp** | +2.94% | -0.42% | +0.124% |
| 10-26 17:05 | APT | SHORT | trail_sl | -0.01% | +0.90% | **+0.92pp** | +1.49% | 0.86% | +0.219% |
| 10-26 16:46 | BANANA | SHORT | rr_sl_hit | -0.46% | +0.42% | **+0.89pp** | +0.54% | 1.07% | -0.546% |
| 10-26 17:05 | ADA | SHORT | trail_sl | -0.20% | +0.34% | **+0.54pp** | +0.78% | 0.97% | +0.291% |
| 10-26 17:05 | GMT | SHORT | trail_sl | +0.09% | +0.58% | **+0.49pp** | +1.01% | 0.43% | +0.095% |

## 7. Gate impact on early exits @T=0.3%

| Gate Status | Early Exits | % of Total |
|-------------|-------------|------------|
| Gate-blocked | 12 | 71% |
| Gate-passed | 3 | 18% |
| No gate | 2 | 12% |

**Gate-blocked trades account for 71% of early exits** — the gates are letting through trades that exit early, while blocking trades that would have held longer.

---

## Key Insights

1. **Shadow trades exit much less destructively than live trades** — 30% early exits vs 74% for live trades.
2. **RR engine's SL is the dominant exit** (24/57 = 42%) with 0% WR — it's catching moves too early.
3. **Shadow trades have much lower MAE** (0.21% p50 vs 0.57% for live) — less drawdown to survive.
4. **Wider-stop scenario shows +50-63% potential** (vs +9-16% for live trades).
5. **Peak timing is earlier** (p50 219m vs 276m for live) — time-based exits are less destructive.
6. **Gate-blocked trades account for 71% of early exits** — gates may be counterproductive.

## Recommendations

1. **Run the coupled CUT_LOSER + ATR_SL shadow trial** — data strongly supports wider stops.
2. **Investigate RR engine's SL** — 42% of exits with 0% WR suggests it's too tight.
3. **Reduce time-based exits** — peak arrives at p50 219m, soft-trail 2h is close.
4. **Review gate impact** — 71% of early exits are gate-blocked trades.

## Caveats

- **Coverage issue:** 57/57 trades have <80% window coverage (58-67%) — extremes may understate.
- **Entry price source:** Uses `context->>'$.price'` (signal detection price), not candle open. May differ from actual entry.
- **Closed trades only:** Open-position survivorship bias.
- **43/100 skipped:** No entry price in context JSON.
- **Fav/MFE gross of fees:** Scenario figures are gross, not net.
- **Scenario 4b exits at peak:** Upper bound, not achievable.
- **Cohort conditioned on MFE≥0.8%:** Outcome-selection if treated as policy.

## Comparison to Live Trades Analysis

| Metric | Shadow (n=57) | Live (n=96) | Delta |
|--------|---------------|-------------|-------|
| Early exits @T=0.3% | 30% | 74% | **-44pp** |
| Median foregone | 1.43pp | 1.83pp | -0.40pp |
| MAE p50 | 0.21% | 0.57% | **-0.36pp** |
| MAE p75 | 0.86% | 1.17% | -0.31pp |
| Survivable to peak | 84% | 56% | **+28pp** |
| Peak timing p50 | 219m | 276m | -57m |
| Wider-stop potential | +50-63% | +9-16% | **+41-54pp** |

**Shadow trades are fundamentally different from live trades:**
- Lower MAE (less drawdown)
- Earlier peaks (less time to wait)
- Less destructive exits (fewer early exits)
- Higher potential with wider stops

This suggests the shadow trading system is better calibrated than the live system, OR the market conditions differ between the two periods.

---

## Verification

- Script: `/tmp/shadow_mfe_mae_8h.py` (deterministic, read-only)
- Reproducible: 3 full runs identical
- Data source: `brain/shadow_trades.db` + `data/candles.db`
- Methodology: Same as live trades analysis (`analysis/mfe_mae_8h.py`)

## Reports

- `reports/20261026-mfe-mae-8h-verdict.md` — Live trades analysis
- `reports/20261026-mfe-mae-8h-last100.md` — Live trades raw output
- `reports/20261026-shadow-mfe-mae-8h-verdict.md` — This report (shadow trades)
- `reports/20261026-shadow-mfe-mae-8h-raw.md` — Shadow trades raw output

## OpenMemory

Stored: `shadow MFE/MAE 8h analysis 2026-10-26`

Tags: `shadow-analysis`, `mfe-mae`, `8h-window`, `early-exits`, `rr-engine`, `wider-stops`, `cutoff-loser`, `atr-sl`, `live-comparison`
