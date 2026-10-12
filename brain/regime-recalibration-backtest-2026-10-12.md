# Volatility Regime Recalibration — Backtest (2026-10-12)

## Method
- Basis: 5,140 closed trades (PostgreSQL brain) with derivable ATR%(14) at entry,
  computed from 1h candles (same basis as `classify_volatility` in volatility_gate_v2.py).
- ATR% = ATR(14)/close*100, using the 15 1h candles strictly before each trade's open_time.
- Significance: t-stat on per-trade PnL; flag |t|>=2.0 & n>=30 as likely-real.

## Current thresholds (classify_volatility:515)
FLAT<0.48 | NORMAL<1.0 | HIGH<1.5 | EXTREME>=1.5
Distribution across 209 live tokens: EXTREME=26%, HIGH+=63%. Top bucket captures a
quarter of the universe -> label is miscalibrated ("EXTREME" = "somewhat hot or worse").

## Key findings

### 1. Regime must be DIRECTION-AWARE (strongest result)
Single ATR ladder hides opposite edges. Direction x ATR% grid:
- LONG:  +$0.0127 at FLAT (t=2.57, only significant cell), decaying monotonically,
         worst at >=4.0 (MAXXED) -$0.0259. Higher ATR = worse for LONG, cleanly.
- SHORT: negative/flat everywhere EXCEPT a profitable hump at 2.5-4.0% ATR:
         +$0.0140 avg, 52.1% WR, t=1.92. Collapses at >=4.0 (30.2% WR).

### 2. The SHORT 2.5-4.0 hump is real, not a small-n artifact
- 65 distinct tokens; leave-one-out (drop XMR, top token): n=244 +$4.22 55.3% t=2.10.
- Cleanest sub-bin 2.5-3.0: n=141 +$3.06 58.2% WR t=2.09.

### 3. >=4.0 ATR ("maxxed out") is genuinely bad BOTH directions
- LONG 43.2% WR -$0.0259 | SHORT 30.2% WR -$0.0319. Justifies a real top tier.

### 4. Concrete cost of current EXTREME(>=1.5) conflation
- 148 profitable 2.5-4.0 SHORT trades worth +$15.71 are suppressed by the flat
  EXTREME block. This is the "missing trades" the CEO flagged.

### 5. PUMP (the flagged token) validates the thesis
- 28 trades, WR 32.1% -$1.29 — bad overall (so blocking it wasn't crazy),
- BUT its SHORTs at 2.0-2.6% ATR were net WINNERS while its LONGs bled at every level.
- At the moment it was blocked it was LONG at ~1.86% ATR — a "tame" reading wearing
  the EXTREME label. The label said storm; the data said mild-long-bleed.

## Caveat (per AGENTS.md THE_PATTERN)
Per-signal overrides in volatility_gate_v2.py were calibrated WITHIN the current
buckets. Re-cutting boundaries changes every cited winrate. The direction-aware
finding above is additive (a new dimension) and does NOT invalidate existing
within-bucket numbers — prefer it over re-drawing the single ladder.

## Recommendation
- Do NOT simply re-cut the 0.48/1.0/1.5 ladder.
- ADD: (a) a MAXXED tier (>=4.0%) — genuinely bad both directions; (b) direction-
  aware override in EXTREME-hi (2.5-4.0): allow SHORT, restrict LONG.
- Requires independent verification (own-conclusions) before touching live classifier.
