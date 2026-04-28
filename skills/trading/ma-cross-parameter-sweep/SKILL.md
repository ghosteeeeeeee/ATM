---
name: ma-cross-parameter-sweep
description: Systematically test and validate EMA cross signal parameters before implementation. Uses exit-on-reverse methodology (not fixed TP/SL) which is critical for realistic signal quality assessment.
tags: [backtest, ema-cross, parameter-sweep, signal-validation, hermes]
triggers:
  - test new ema pair
  - validate ma cross parameters
  - ema cross backtest
  - new ma cross signal
---

# EMA Cross Parameter Sweep Skill

## When to Use

Testing a new EMA cross signal before building it. Specifically when:
- Adding a new MA cross variant (e.g., 8/50, 12/50, 20/100)
- Evaluating which EMA periods to use for a signal
- Determining signal direction (LONG vs SHORT vs both)

## Critical Principle: Exit on Reverse Cross, Not Fixed TP/SL

**Never use fixed TP/SL exits for MA cross backtesting.** Here's why:

Fixed exits (e.g., TP 1%, SL 2%) clip winners and misclassify reversals as "stop losses."
This creates misleading win rates (70%+ WR on paper) while net P&L is catastrophic.

The correct methodology: **exit on reverse EMA cross** (the actual signal exit rule).
This reveals the true signal quality:

```
Cross detected at bar i → entry at close[i]
Hold until: EMA fast crosses back through EMA slow
Exit at: close[k] where k = first reverse cross after i
PnL = (close[k] - close[i]) / close[i]  [for LONG]
```

This is how the backtester models T's "book profit fast" philosophy.
It produces realistic WR (18-30%) and accurate P&L.

## Step-by-Step: Sweep EMA Pairs

### Step 1 — Design the Parameter Grid

Test medium-term pairs, not just the obvious ones:

```python
pairs = [
    (5, 50),    # fast/medium
    (8, 50),    # sweet spot
    (12, 50),   # moderate
    (20, 50),   # moderate/slow
    (20, 100),  # slow
    (20, 200),  # very slow (golden/death — often too lagging)
    (12, 100),
    (5, 20),    # short-term (often too noisy)
]
```

Golden cross (20/200) is the **baseline to beat**, not the target.
Medium pairs (8/50, 12/50) typically outperform because they react faster.

### Step 2 — Run Full Universe Backtest

Load all token closes once, then sweep. Pre-compute EMA series per token:

```python
def backtest_ma_cross(closes, fp, sp):
    """Exit on reverse cross only. Returns (longs_list, shorts_list)."""
    n = len(closes)
    fb = calc_ema_series(closes, fp)  # full series
    sb = calc_ema_series(closes, sp)  # full series
    longs, shorts = [], []
    max_idx = min(len(fb), len(sb), n)
    for j in range(2, max_idx - 1):
        efp, efc = fb[j-1], fb[j]
        esp, esc = sb[j-1], sb[j]
        if None in (efp, efc, esp, esc): continue
        entry = closes[j]
        if entry <= 0: continue
        # LONG: fast crosses above slow
        if efp <= esp and efc > esc:
            pnl = 0
            for k in range(j+1, max_idx):
                if fb[k] is None or sb[k] is None: continue
                if fb[k] <= sb[k]:  # reverse
                    pnl = (closes[k] - entry) / entry * 100; break
            else:
                pnl = (closes[max_idx-1] - entry) / entry * 100
            longs.append(pnl)
        # SHORT: fast crosses below slow
        elif efp >= esp and efc < esc:
            pnl = 0
            for k in range(j+1, max_idx):
                if fb[k] is None or sb[k] is None: continue
                if fb[k] >= sb[k]:  # reverse
                    pnl = (entry - closes[k]) / entry * 100; break
            else:
                pnl = (entry - closes[max_idx-1]) / entry * 100
            shorts.append(pnl)
    return longs, shorts
```

### Step 3 — Analyze Results Per Direction

```
Pair      Longs  L%    Lpnl    Shorts S%    Spnl    Total  Net
5/50     1814  17.9% -348%    1808  24.9%  +525%   3622  +177%
8/50     1397  18.1% -269%    1391  28.0%  +605%   2788  +336%
20/50     910  19.0% -421%     900  32.0%  +457%   1810   +35%
20/200    360  13.1% -697%     363  38.3%  +196%    723  -501%
```

Key metrics:
- **WR alone is meaningless** — 20/50 has highest WR (32%) but 20/200 is worst net (-501%)
- **Net P&L** is the primary metric (sum of all P&L % across all trades)
- **Signal volume** matters for practicality (more signals = more opportunities)
- **Longs and shorts can have opposite outcomes** — always test separately

### Step 4 — Survival Analysis (Separation → Duration)

Separation bonus only matters if larger separation predicts longer survival.
Run cross survival analysis:

```python
def survive_bars(closes, ef, es, fp, sp, min_sep_pct=0.0):
    """For each cross, measure how many bars until reverse."""
    n = len(closes)
    fb = {i: ef[i] for i in range(n) if i < len(ef) and ef[i] is not None}
    sb = {i: es[i] for i in range(n) if i < len(es) and es[i] is not None}
    common = sorted(set(fb.keys()) & set(sb.keys()))
    out = []
    for j in range(1, len(common)):
        ic, ip = common[j], common[j-1]
        if ic >= n or ip >= n: continue
        efp, efc = fb[ip], fb[ic]
        esp, esc = sb[ip], sb[ic]
        if None in (efp, efc, esp, esc): continue
        entry = closes[ic]
        if entry <= 0: continue
        sep_pct = abs(efc - esc) / entry * 100
        if sep_pct < min_sep_pct: continue
        # Detect cross direction
        cross_dir = None
        if efp <= esp and efc > esc: cross_dir = 'LONG'
        elif efp >= esp and efc < esc: cross_dir = 'SHORT'
        else: continue
        # Measure survival (bars until reverse)
        rev_bars = None
        for k in range(ic+1, n):
            if k in fb and k in sb:
                if cross_dir == 'LONG' and fb[k] <= sb[k]:
                    rev_bars = k - ic; break
                if cross_dir == 'SHORT' and fb[k] >= sb[k]:
                    rev_bars = k - ic; break
        if rev_bars is None: rev_bars = n - ic - 1
        out.append((sep_pct, rev_bars))
    return out
```

Expected result (8/50, 163 tokens):

| sep range | n | median bars | mean bars |
|-----------|---|-------------|-----------|
| 0.0-0.1% | 8583 | 26 | 73 |
| 0.1-0.2% | 201 | 50 | 103 |
| >1.0% | 44 | 698 | 666 |

Larger separation = dramatically longer survival before reverse. This validates the separation bonus in confidence scoring.

## Key Findings (2026-04-20)

### Shorts Dominate Across All Pairs (163 tokens, 3+ months)

| Pair | Net P&L |
|------|---------|
| 5/50 | +4984% |
| 8/50 | +4214% |
| 12/50 | +4112% |
| 20/50 | +3932% |
| 20/200 | -501% |

### Golden/Death Cross is Too Slow
20/200 fires fewer signals and loses money (net -501%) because:
- By the time 10 EMA crosses 200 EMA, the move is already over
- Most crosses have tiny separation (<0.1%) — pure noise
- The "sweet spot" is medium pairs (8/50, 12/50)

### Practical Signal Design

For a new MA cross signal:
1. **Medium EMA pair (8/50 or 12/50)** — react faster, catch moves before they're over
2. **SHORT only** — longs are structurally broken in bear market data
3. **Separation filter (0.05% min)** — removes noise crosses where EMAs barely touch
4. **Confidence = base + sep_bonus + recency_bonus** (cap 88)
5. **Exit on reverse cross** — match the backtest methodology to live behavior

## Files

- `/root/.hermes/scripts/backtest_ma_cross.py` — parameter sweep backtester
- `/root/.hermes/scripts/ma_cross_signals.py` — 10/200 EMA cross signal (existing)
- `/root/.hermes/scripts/ma_fast_signals.py` — 8/50 EMA cross SHORT signal (new 2026-04-20)

## Related
- `trend-signal-backtest`: MACD/ADX backtest — SHORT dominance confirmed there too
- `per-token-signal-implementation`: how to add a new signal to Hermes
- `surfing-gap-analysis`: compare signal design against Surfing philosophy
