# Independent Verdict — pump-chain SHORT `rise_1m >= 2` filter

**Auditor:** independent (fresh read of source data, no priming from prior analyses)
**Date:** 2026-10-07
**Data sources:**
- PostgreSQL brain DB — `trades WHERE signal LIKE 'pump-chain%' AND direction='SHORT'`
- `/root/.hermes/data/candles.db` — `candles_1m` (token, ts, close), boundary `ts <= entry_time`
- Entry time = `open_time`; `rise_1m` = count of consecutive rising 1m closes walking backwards from the most recent candle (`closes[i] > closes[i+1]`) until a non-rising candle.

## Dataset (verified from scratch)

140 pump-chain SHORT trades. Range: 2026-09-09 05:36 → 2026-10-07 13:41.
- Signals: `pump-chain-` (135) + 5 composites (`pump-chain-,r2-trend-short4`, `-rs-r54/61/64/68`).
- `pump_chain` (underscore, 2 SHORT trades, -$0.13) and `pump-chain+`/`-v5` (LONG) are NOT part of this set and were excluded.

`rise_1m` distribution across all 140: **rise=0 → 86, rise=1 → 27, rise=2 → 17, rise=3 → 8, rise=4 → 1, rise=6 → 1.** Blocked at `rise>=2`: **27 trades.**

Outcome by rise bucket (avg PnL/trade):
| rise | n | W | L | Z | avg PnL |
|------|---|---|---|---|---------|
| 0 | 86 | 44 | 37 | 5 | +0.0067 |
| 1 | 27 | 18 | 9 | 0 | **+0.0367** (best) |
| 2 | 17 | 4 | 11 | 2 | **-0.0865** (worst) |
| 3 | 8 | 4 | 3 | 1 | -0.0387 |
| 4 | 1 | 0 | 1 | 0 | -0.2700 |
| 6 | 1 | 1 | 0 | 0 | +0.1900 |

The edge lives specifically at `rise>=2`. rise=1 is the *best* bucket — which is why a `>=1` threshold destroys the filter.

---

## Claim-by-claim

### Claim 1 — Filter definition
> "rise_1m >= 2 filter: if 2+ consecutive rising 1m candles before entry, block the SHORT"

**Verdict: AGREE**
**Evidence:** Definition implemented exactly as specified and verified against raw candles. 27 of 140 trades (19.3%) are blocked. Methodology is insensitive to boundary choice: `ts<=` vs `ts<` and closed-only vs all-candles change `rise_1m` for **0 of 140** trades. Manual spot-check of ADA (Oct 7 08:08): closes most-recent-first `[0.2572, 0.2571, 0.257, 0.2572]` → rise=2, blocked. Correct.
**Confidence: HIGH**

### Claim 2 — Full-dataset effect
> "kills 9 winning trades, catches 18 losing trades, WR=50.7%→54.9%, net=+$1.86"

**Verdict: PARTIAL**
**Evidence (my independent counts on the 27 blocked trades):**
- Kills **9** winning trades (sum +$0.44) — AGREE.
- "Catches **18** losing trades" — the 18 is reproducible only as **15 real losers + 3 scratches** (losers sum -$2.30, scratches $0.00). Strictly it catches 15 losing trades; 18 counts the 3 scratch trades ($0.00) as "losing." Consistent with the `71W 69L` framing (see Claim 4), but the word "losing" is doing double duty. **PARTIAL.**
- WR 50.7%→54.9% — AGREE (71/140=50.71% → 62/113=54.87%, W/total convention).
- "net=+$1.86" — the number is real, but it is the **improvement delta**, not the resulting net. Blocked trades sum to **-$1.86**; removing them moves the book from **-$0.29 to +$1.57**. Improvement = +$1.86; resulting net PnL = **+$1.57**, not +$1.86. The claim's wording is ambiguous/misleading on this point.
**Confidence: HIGH** (numbers verified; the caveats are definitional, not computational)

### Claim 3 — Oct 7 specific
> "catches ADA -$0.06, GRASS $0.00, FIL -$0.12, kills 0 winners"

**Verdict: AGREE**
**Evidence:** Oct 7 has 7 pump-chain SHORT trades. The three named are all blocked, confirmed against raw candle data:
- **ADA** pnl=-0.06, rise=2 → BLOCKED ✓
- **GRASS** pnl=0.00, rise=3 → BLOCKED ✓
- **FIL** pnl=-0.12, rise=2 → BLOCKED ✓

"Kills 0 winners" on Oct 7 — correct: the only Oct 7 winner is APT +0.53, rise=0, kept. (Note: GRASS is a $0.00 scratch, so "catching" it is neutral, not a saved loss.)
**Confidence: HIGH**

### Claim 4 — Baseline
> "Baseline: 71W 69L (50.7% WR) PnL=$-0.29"

**Verdict: PARTIAL**
**Evidence:** Actual composition of the 140: **71 wins, 61 losses, 8 scratches ($0.00)**, total PnL **-$0.29**.
- 71W ✓, PnL -$0.29 ✓, WR 50.7% ✓ (71/140=50.71%).
- "69L" = **61 real losses + 8 scratches**. The 8 scratch trades are counted as losses. If you exclude scratches: 71W/61L → WR = 53.79% (W/(W+L)). Either convention is defensible, but the baseline as stated silently folds scratches into the loss column.
**Confidence: HIGH**

---

## Overall assessment

The filter's **direction and headline numbers are essentially right**: ≥2 is the correct threshold, it blocks 27 trades killing 9 winners and catching 15 losers (+3 scratches), lifts WR ~4pp, and improves the book by ~+$1.86 (book goes -$0.29 → +$1.57). Oct 7 claims are all correct.

Two corrections the prior analysis should carry:
1. **"catches 18 losing trades" = 15 losers + 3 scratches**, not 18 losses.
2. **"net=+$1.86" is the delta, not the resulting PnL (+$1.57).**

### Is the edge real? (my independent testing)
- **Permutation test** on the WR lift: **p = 0.036** (one-sided, 20k sims) — significant but not strong.
- **Bootstrap** on the net improvement: 95% CI **+$0.64 to +$3.15**, P(improvement>0)=0.999.
- **Robustness caveat:** the edge is **front-loaded**. First half: blocked 13 trades went 6W/6L (coin flip). Second half: blocked 14 went 3W/9L (the real edge). The filter is not uniformly predictive across the sample.
- **Overfit risk:** only 27 blocked trades / 9 killed winners. If this threshold was tuned on this same data, p=0.036 is optimistic. Treat as a modest, unconfirmed edge — roughly **+1.3¢ per trade** on 140 trades.

## Threshold sweep (my independent run)
| Block rule | blocked | kills W | catches L+Z | kept PnL | kept WR |
|-----------|---------|---------|-------------|----------|---------|
| rise>=1 | 54 | 27 | 27 | +$0.58 | 51.16% |
| **rise>=2** | **27** | **9** | **18** | **+$1.57** | **54.87%** |
| rise>=3 | 10 | 5 | 5 | +$0.10 | 50.77% |
| rise>=4 | 2 | 1 | 1 | -$0.21 | 50.72% |

**rise>=2 is the optimum.** >=1 is actively harmful (kills 27 winners incl. the strong rise=1 bucket). >=3/+ capture too little.

## Recommended filter
**Keep `rise_1m >= 2` as a block, with corrected framing:** it blocks ~19% of pump-chain SHORTs, removing ~-$1.86 of expected PnL (9 winners worth +$0.44 traded for 15 losers worth -$2.30). It is the best of the thresholds tested and beats every single entry-time feature I screened (bb_position kept +$1.18, rsi_14 +$0.84, macd_hist +$0.41 — all in-sample and still below rise>=2's +$1.57). Adding an RSI gate on top did not improve it. Before deploying: the edge is modest, statistically borderline (p=0.036), front-loaded in time, and derived from only 27 blocked trades — validate out-of-sample on fresh trades before relying on it.
