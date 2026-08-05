# Opp/Same Ratio — Opposing Signal Noise Filter
**Date:** 2026-05-24
**Source:** 24h empirical audit (81 trades, PostgreSQL brain.trades + SQLite signals_hermes_runtime.db)

---

## Finding

For each trade, count the ratio of opposing-direction signals to same-direction signals in the 60 min before entry. The opposing/same ratio is a strong predictor of loss.

| Bucket | Trades | WR | Avg PnL |
|--------|--------|-----|---------|
| **Opp=Same** | 6 | 66.7% | +29.4% |
| **Opp<Same** | 50 | 46.0% | +24.8% |
| **Opp>Same** | 20 | 30.0% | -31.0% |
| **Opp>>Same (2x)** | 3 | 0.0% | -103% |

**Interpretation:**
- When same-dir signals equal or outnumber opposing signals → market has a clear bias → trade likely wins
- When opposing signals dominate → market is choppy/conflicting → trade likely loses
- The 2 trades with 0 opposing signals both lost badly (-71.8% avg) — no market context at all

---

## Proposed Constant (no-code tweak)

In `hermes_constants.py`, a simple gate:

```python
# Block trade if opposing signals outnumber same-dir signals in 60-min window
RS_OPP_SAME_RATIO_BLOCK = True   # True = block if opp > same
RS_OPP_SAME_RATIO_MAX  = 1.5    # block if opposing/same > 1.5 (50% more opposing than same-dir)
```

Or more surgical:

```python
# Block ONLY when opposing is 2x or more of same-dir (extreme chop)
RS_OPP_SAME_RATIO_BLOCK_EXTREME = True  # block if opp/same >= 2.0
```

---

## Impact if Implemented

- Block 3 trades in "Opp>>Same" bucket (0% WR, -103% avg) → saves ~$3
- Let through 6 "Opp=Same" trades (66.7% WR, +29.4% avg) → gains significant
- Block 20 trades in "Opp>Same" bucket (30% WR, -31% avg) → avoids major losses

---

## Notes

- Data: SQLite `signals_hermes_runtime.db` signals table queried with 60-min lookback
- Counted signals of types: `zscore_pump_long`, `zscore_pump_short`, `support_resistance`
- Not limited to RS signals — all signal types matter for this ratio
- Implementation location: `decider_run.py` as pre-trade gate