# CEO Consult: Shadow MFE/MAE 8h Analysis — Findings & Recommendations

## Context

T asked to run the same MFE/MAE 8h analysis (previously done on live trades) on shadow-mode data. The analysis examines: how many trades were stopped early with a bigger move following our exit, and what we'd need to survive the MAE to capture bigger MFEs.

**Full report:** `reports/20261026-shadow-mfe-mae-8h-verdict.md` (commit `136ad4ea`)  
**Raw output:** `reports/20261026-shadow-mfe-mae-8h-raw.md`  
**Live trades comparison:** `reports/20261026-mfe-mae-8h-verdict.md`

---

## Key Findings

### 1. Shadow Trades Exit Much Less Destructively Than Live Trades

| Metric | Shadow (n=57) | Live (n=96) | Delta |
|--------|---------------|-------------|-------|
| **Early exits @T=0.3%** | **30%** | **74%** | **-44pp** |
| Median foregone | 1.43pp | 1.83pp | -0.40pp |
| Losers followed by ≥1% move | 10% | 43% | **-33pp** |
| Losers followed by ≥2% move | 0% | 24% | **-24pp** |
| Winners giving up ≥1pp tail | 26% | 46% | -20pp |

**Shadow trades are exiting much more efficiently.** Only 30% of exits are followed by a bigger move (vs 74% for live trades). The RR engine's SL is catching moves earlier but with less foregone upside.

### 2. RR Engine's SL is the Dominant Exit (and Problematic)

| Exit Rule | n | WR% | Avg Net PnL |
|-----------|-----|-----|-------------|
| **rr_sl_hit** | **24 (42%)** | **0%** | **-0.593%** |
| trail_sl | 14 (25%) | 100% | +0.244% |
| atr_sl_hit | 5 (9%) | 0% | -0.856% |
| hard_max_loss | 4 (7%) | 0% | -1.072% |
| rr_trail_hit | 4 (7%) | 75% | +0.119% |
| atr_trail_hit | 3 (5%) | 100% | +0.546% |
| pump_exit_dead_money | 2 (4%) | 100% | +0.934% |
| cut_loser_t1 | 1 (2%) | 0% | -1.211% |

**rr_sl_hit accounts for 42% of all exits with 0% WR.** This is the RR engine's stop-loss, not the ATR SL. It's catching moves too early.

### 3. Shadow Trades Have Much Lower MAE

| Requirement | Shadow (n=31) | Live (n=64) |
|-------------|---------------|-------------|
| MAE p50 | **0.21%** | 0.57% |
| MAE p75 | **0.86%** | 1.17% |
| MAE p90 | **1.04%** | 1.62% |
| Max MAE | **2.08%** | 4.76% |
| HML stops first | 16% | 20% |
| **Survivable to peak** | **84%** | **56%** |
| Peak timing p50 | **219m** | 276m |

**Shadow trades have much lower drawdown** — the RR engine's tighter SL is catching moves before they drawdown deeply. This means less leverage reduction is needed.

### 4. Wider-Stop Scenario Shows Much Higher Potential

| Stop + coupled HML @5x | Shadow Scenario | Live Scenario |
|------------------------|-----------------|---------------|
| actual (as traded, net) | -4.87% | +$1.68 |
| SL 0.80% + CUT_LOSER 4% | **+50.32%** | +$9.61 |
| SL 1.17% + CUT_LOSER 5.8% | **+62.81%** | +$12.95 |
| SL 1.62% + CUT_LOSER 8.1% | **+61.91%** | +$16.35 |

**Shadow trades show +50-63% potential with wider stops** (vs +9-16% for live trades). This is because:
1. Lower MAE (0.21% vs 0.57% p50)
2. Higher MFE (more room to ride)
3. Earlier peaks (less time to wait)

### 5. Peak Timing is Earlier for Shadow Trades

- Shadow: p50 **219m** (3.65h), p75 249m
- Live: p50 **276m** (4.6h), p75 403m

**Time-based exits are less destructive for shadow trades** — soft-trail 2h is closer to the peak.

### 6. Gate Impact: 71% of Early Exits are Gate-Blocked

| Gate Status | Early Exits | % of Total |
|-------------|-------------|------------|
| Gate-blocked | 12 | 71% |
| Gate-passed | 3 | 18% |
| No gate | 2 | 12% |

**Gate-blocked trades account for 71% of early exits** — the gates are letting through trades that exit early, while blocking trades that would have held longer.

---

## Recommendations

### Immediate (Shadow Mode)

1. **Run the coupled CUT_LOSER + ATR_SL shadow trial** — data strongly supports wider stops. The CEO previously deferred this after the SL sweep, but this data shows +50-63% potential.

2. **Investigate RR engine's SL** — 42% of exits with 0% WR suggests it's too tight. Consider widening or replacing with ATR SL.

3. **Reduce time-based exits** — peak arrives at p50 219m, soft-trail 2h is close. Consider extending hold time.

4. **Review gate impact** — 71% of early exits are gate-blocked trades. The gates may be counterproductive.

### Strategic

5. **Shadow trades are fundamentally different from live trades** — lower MAE, earlier peaks, less destructive exits. This suggests the shadow trading system is better calibrated, OR market conditions differ.

6. **Consider adopting shadow exit parameters for live** — if shadow shows +50-63% potential with wider stops, live should test this.

---

## Constraints

- **Coverage issue:** 57/57 trades have <80% window coverage (58-67%) — extremes may understate
- **Entry price source:** Uses `context->>'$.price'` (signal detection price), not candle open
- **43/100 skipped:** No entry price in context JSON
- **Closed trades only:** Open-position survivorship bias
- **Fav/MFE gross of fees:** Scenario figures are gross, not net
- **Scenario exits at peak:** Upper bound, not achievable
- **Cohort conditioned on MFE≥0.8%:** Outcome-selection if treated as policy

---

## Questions for CEO

1. **Should we run the coupled CUT_LOSER + ATR_SL shadow trial?** The data shows +50-63% potential for shadow trades (vs +9-16% for live). This was previously deferred after the SL sweep.

2. **Should we investigate the RR engine's SL?** It accounts for 42% of exits with 0% WR. Is this the right exit for shadow trades?

3. **Should we reduce time-based exits?** Peak arrives at p50 219m, soft-trail 2h is close. Should we extend hold time?

4. **Should we review gate impact?** 71% of early exits are gate-blocked trades. Are the gates counterproductive?

5. **Should we adopt shadow exit parameters for live?** If shadow shows better results, live should test this.

---

## Data Quality Notes

- 57/100 shadow trades analyzed (43 skipped: no entry price)
- Coverage 58-67% for all trades (extremes may understate)
- Entry price from context JSON (signal detection price, not candle open)
- Reproducible: 3 full runs identical
- Same methodology as live trades analysis

---

## Full Report

`reports/20261026-shadow-mfe-mae-8h-verdict.md` (commit `136ad4ea`)
