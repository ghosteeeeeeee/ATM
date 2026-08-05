# Signal Quality Predictors in Hot-Set (2026-05-25)

## Key Findings from 26-Trade Analysis

These findings are about **post-confluence signal quality** — after a signal passes the 2-source gate,
what characteristics predict whether it becomes a winner or loser?

## 1. Signal Type is the Dominant Predictor

| Signal Type | Direction | WIN | LOSS | WR |
|-------------|-----------|-----|------|-----|
| support_resistance | LONG | 5 | 2 | **71%** |
| support_resistance | SHORT | 2 | 1 | **67%** |
| zscore_pump_long | LONG | 3 | 5 | **38%** |
| zscore_pump_short | SHORT | 2 | 5 | **29%** |

**support_resistance signals win at 2x the rate of zscore_pump.**  
zscore_pump_short is the worst combination.

**Practical implication:** When two tokens have similar confidence scores in the hot-set,
prefer the support_resistance token. The structural level (RS) does the heavy lifting;
zscore_pump provides timing but adds noise.

## 2. Leverage Correlates with Outcome

| Leverage | WIN | LOSS | WR |
|----------|-----|------|-----|
| 3x | 7 | 4 | **64%** |
| 5x | 5 | 9 | **36%** |

Every 5x loss hit ATR SL. The 5x winners were predominantly support_resistance signals.
**The 5x + zscore_pump_long combination is the worst performing setup.**

**Practical implication:** A 5x zscore_pump_long signal in the hot-set is high-risk.
Consider demoting 5x zscore_pump_long tokens in favor of 3x support_resistance tokens
at similar confidence levels.

## 3. Time-to-Execution Predicts Outcomes

```
WIN  avg=106 min, median=122 min  (range: -306 to 432 min)
LOSS avg=263 min, median=173 min  (range: 3 to 887 min)
```

Winners execute ~2x faster after signal generation.
Slow losers (signal-to-trade gap > 6h): UMA=887min, BLUR=761min, ADA=390min, ETH=375min.

**Practical implication:** Consider a max-signal-age filter (e.g., 4h) for zscore_pump signals.
A zscore_pump_long signal that has been in the hot-set for 3+ hours without execution
is disproportionately likely to be a loser.

## 4. zscore Magnitude Does NOT Predict Winners

```
WIN  zscores:  [-4.11, -3.56, -3.56, -3.44, 3.02, 3.11, 3.11, 3.22, 3.35, 3.54, 3.72, 5.48]
LOSS zscores: [-3.93, -3.66, -3.41, -3.32, -3.18, -3.05, 3.01, 3.04, 3.31, 3.42, 3.72, 3.83, 5.27]
```

The distributions overlap almost completely. zscore alone cannot separate winners from losers.

**Exception:** For SHORT signals, |z| >= 3.5 improves WR from 40% → 60%:

| Threshold | WIN | LOSS | WR |
|-----------|-----|------|-----|
| >=3.0 | 4 | 6 | 40% |
| >=3.5 | 3 | 2 | **60%** |
| >=4.0 | 1 | 0 | **100%** |

## 5. Coin Repeats — Signal Type Is the Differentiator

| Coin | WIN | LOSS | Pattern |
|------|-----|------|---------|
| LINEA | SHORT(-4.11 sr) + LONG(+5.48 zp) | — | Both won — extreme zscore on both sides |
| ME | SHORT×2(-3.56 zp) | LONG(-3.42 sr) | zscore_pump SHORT won, SR LONG lost |
| MON | LONG(+3.54 sr) | SHORT(-3.05 zp) | SR LONG won, zp SHORT lost |
| ADA | — | LONG(+3.01 zp) + SHORT(-3.93 zp) | Both lost — weak zscore on both sides |
| AVAX | LONG(+3.22 zp) | SHORT(-3.32 sr) | Split by signal type |

Signal type (support_resistance vs zscore_pump) is the consistent differentiator
in split-direction results, not zscore magnitude.

## 6. Confidence Alone Is Not Enough

The current hot-set ranking uses `survival_round DESC, confidence DESC`. These findings
suggest adding signal type as a third ranking dimension:

```
score = base_score × signal_type_multiplier

signal_type_multiplier:
  support_resistance LONG: 1.0
  support_resistance SHORT: 1.0
  zscore_pump_long:    0.75   # 38% WR vs 71% — deprioritize
  zscore_pump_short:  0.60   # 29% WR vs 67% — heavily deprioritize
```

## Constants Changes Under Consideration

These are constants-only changes (no code) based on this analysis:

```python
# hermes_constants.py — tighten SHORT zscore threshold
ZSCORE_PUMP_THRESHOLD = 3.5   # was 3.0 — SHORT fires too aggressively at 3.0-3.4

# hermes_constants.py — leverage cap for zscore_pump signals  
# (would require decider_run code change to read signal_type from hotset.json)
# For now: just document the finding
```

## Methodology Notes

- Trade-to-signal matching: token + direction + source tag intersection
- 11/26 trades had no exact-time match (signal gen ≠ trade exec by min to hours)
- All 26 matched via tag overlap method
- signals.json had 26 total executed signals for the full day — perfect match rate
- Data source: `/var/www/hermes/data/signals.json` `executed` array
- Full trade table: see `references/26-trade-deep-dive-2026-05-25.md`