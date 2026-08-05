---
name: context-gate-analyzer
description: Analyze trades, test context gate decisions, and verify z-score FLIP logic. Use when reviewing trade performance, testing new signals, or debugging context gate issues.
---

# Context Gate Analyzer

Analyze trades and test context gate decisions with the full LLM prompt.

## Usage

### Analyze a single trade
```bash
python3 /root/.hermes/skills/trading/context-gate-analyzer/analyze_trade.py <TOKEN> <DIRECTION> <SIGNAL> <ENTRY_TIME>
```

Example:
```bash
python3 /root/.hermes/skills/trading/context-gate-analyzer/analyze_trade.py TNSR LONG tl_break_long "2026-07-29 20:30:00"
```

### Analyze multiple trades from a list
```bash
python3 /root/.hermes/skills/trading/context-gate-analyzer/analyze_trades.py
```

### Test context gate with custom parameters
```bash
python3 /root/.hermes/skills/trading/context-gate-analyzer/test_gate.py <TOKEN> <DIRECTION> <SIGNAL> [Z_SCORE]
```

## What It Does

1. **Calculates z-score at entry time** from price_history
2. **Runs full context gate** (rule-based + LLM)
3. **Shows Hebbian data** (WR estimate, concepts)
4. **Determines if FLIP would have triggered**
5. **Compares actual outcome vs predicted**

## Output Format

```
=== TNSR LONG (tl_break_long) ===
Entry: $0.0301
Z-Score at entry: -1.13
Phase: accelerating
Speed: 79.3%
Hebbian WR: 50% (n=1)
Hebbian Concepts: SHORT=2.5, LONG=0.5

Context Gate Verdict: WARN
LLM Reason: Hebbian data shows SHORT has higher weight
Confidence Penalty: -15

Flip Triggered: No
Actual Outcome: -0.17%
Would Flip Have Helped: No (z=-1.13 is correct for LONG)
```

## Key Metrics

- **Z-Score**: Price relative to 20-period average
  - z > 0: Overbought (good for SHORT)
  - z < 0: Oversold (good for LONG)
  - |z| > 1.5: Strong trend
  - |z| < 0.5: Ranging

- **Hebbian WR**: Historical win rate for (token, signal) pair
  - WR > 60%: High confidence
  - WR < 40%: Low confidence
  - n < 3: Too few trades, unreliable

- **FLIP Logic**:
  - LONG + z > 0.5 → FLIP to SHORT
  - SHORT + z < -0.5 → FLIP to LONG

## Files

- `analyze_trade.py` — Analyze single trade
- `analyze_trades.py` — Analyze multiple trades
- `test_gate.py` — Test context gate with custom parameters
