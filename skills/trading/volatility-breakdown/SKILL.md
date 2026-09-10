---
name: volatility-breakdown
description: Generate a volatility regime breakdown table for any signal. Shows WR and PnL by regime (EXTREME, HIGH, NORMAL, FLAT). Use when analyzing signal performance across market conditions. Triggers on keywords like "volatility breakdown", "regime breakdown", "performance by regime".
---

# Volatility Breakdown — Signal Performance by Regime

Analyze how a signal performs across different volatility regimes (EXTREME, HIGH, NORMAL, FLAT).

## Usage

```bash
cd /root/.hermes && python3 -c "
import sys
sys.argv = ['volatility_breakdown', '<signal_name>']
exec(open('skills/trading/volatility-breakdown/volatility_breakdown.py').read())
"
```

Or call the function directly:

```python
from skills.trading.volatility_breakdown.volatility_breakdown import volatility_breakdown
result = volatility_breakdown('pullback-entry+')
print(result)
```

## Output Format

```
By Regime:

Regime    WR           PnL
EXTREME   33% (2W/4L)  -$17.02
HIGH      42% (5W/7L)  -$28.54
NORMAL    50% (3W/3L)  -$14.46
FLAT      (no trades)  —

Total: 33% WR (10W/14L), -$59.02%

Key insight: The signal performs worst in EXTREME (33% WR) and HIGH (42% WR).
```

## Files

- `volatility_breakdown.py` — Main script
- `SKILL.md` — This file

## Data Sources

- `brain_trading.db` — Trade outcomes with volatility_regime column
- `volatility_gate.py` — Regime classification (FLAT < 0.48%, NORMAL 0.48-1.0%, HIGH 1.0-1.5%, EXTREME > 1.5%)

## Requirements

- Trade must have `volatility_regime` column populated (set by `decider_run.py` at entry)
- Signal source must match (e.g., `pullback-entry+`, `bb-bounce-short`, etc.)
