# Brief: Find the Winning Combos — Infrastructure Is Built, Find the Combinations

**From:** T
**Date:** 2026-10-14
**Urgency:** HIGH — T is defining the actual engineering task before stepping away

## T's Core Point

The CEO said "fewer, better trades." T's response:

**"There is no silver bullet. Fewer trades is not the answer either. When the winrate was 67%, we were firing trades CONSTANTLY. We are currently at least 2x slower."**

T is right. The 67% WR period had HIGH frequency, not low. The difference wasn't fewer trades — it was BETTER COMBINATIONS of the pieces we already have.

## What T Is Actually Asking For

**"We have hundreds of entry points (signals) and multiple exit points (atr_sl, pm_trail, rr_exit etc.). You guys need to figure out (or make) the winning combos. ALL or almost all of the infrastructure is already built."**

This is a combinatorial optimization problem, not a filter problem:

- **Entry signals**: pump-chain+, pump-chain-, bb-squeeze+, bb-bounce-v2+, volume-breakout+, mover+, continuum-trend+, mtf-regime-trend-, doji-bottom, ai-trader+, etc. (~30+ active signals)
- **Exit strategies**: atr_sl, pm_trail, rr_engine, hard_max_loss, cut-loser, pump_exit, trail_sl, etc. (~10+ exit types)
- **Regimes**: NORMAL, HIGH, EXTREME, FLAT × LONG_BIAS/SHORT_BIAS/NEUTRAL
- **Conditions**: RSI bands, z-score bands, volatility, momentum, confluence count

The system has ALL the pieces. What it lacks is knowing WHICH COMBINATIONS are profitable.

## The Task

**Find the profitable (signal × direction × regime × exit × condition) tuples and only trade those.**

This is exactly what the cell_stats system was built for — but it's been running as shadow-only. And the exit_optimizer_shadow has been running but producing "no proposals." The pieces exist. They need to be actually USED to select combinations.

## What's Already Built (but underutilized)

1. **cell_stats.db** — nightly cell statistics (signal × regime × direction). 512 cells, 54 admitted (n≥15). Has WR/PnL per cell.
2. **gate_shadow.db** — 14,234 gate events, 1,312 closed outcomes. Shows which gates block winners vs losers.
3. **exit_optimizer_shadow** — simulates exit configs per cell. Verdict: "current exit configs near-quantile-optimal."
4. **t5_shadow** — trade trainer that evaluates WOULD_TRADE cohorts.
5. **Hebbian associative_memory** — 5,634 trade_log rows with concept associations.
6. **ML classifier v1** — trained on 3,537 trades (AUC 0.58, needs better features).
7. **signal_outcomes** — tracks MFE/MAE/exit_reason per signal.

## The Real Question

Why hasn't the system figured out the winning combos with all this infrastructure? Is it because:
1. The cell_stats aren't being used for live selection?
2. The exit_optimizer isn't proposing changes?
3. The Hebbian recall isn't influencing trade selection?
4. The data exists but nothing connects it to the entry decision?

## What We Need From You

1. What's the concrete plan to find winning combos from existing data?
2. Which existing system (cell_stats, Hebbian, exit_optimizer, ML) should be the primary combo selector?
3. What's the 2-week deliverable that turns "we have the pieces" into "we found the combos"?
4. Can we run a combo-mining analysis NOW to find the top 10 profitable tuples from the last 30 days of data?
