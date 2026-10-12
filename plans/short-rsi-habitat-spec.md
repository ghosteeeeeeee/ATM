# Spec: SHORT RSI Habitat Gate — Per-Signal RSI Bands

## Problem

`SHORT_RSI_HARD_FLOOR = 45` is a blanket gate that blocks ALL SHORT signals when RSI < 45. But different signals have different RSI habitats — some work at low RSI, some at high. The blanket floor blocks profitable trades for signals whose habitat is below 45.

**Evidence (60d, meta RSI from _signal_metadata):**

| Family | RSI <25 | 25-35 | 35-45 | **45-55** | 55-65 | 65-75 | 75+ |
|--------|---------|-------|-------|-----------|-------|-------|-----|
| pump-chain | 8T −$0.81 | 9T +$0.01 | 27T −$0.37 | **41T +$0.15** | 19T −$0.07 | 9T +$0.01 | 5T −$0.22 |
| other | **105T +$0.39** | 97T −$1.54 | 97T −$3.09 | 83T −$0.86 | 48T −$0.60 | 43T −$0.64 | 19T −$0.99 |
| grind | — | 6T −$0.10 | 7T −$0.72 | 5T −$0.28 | — | — | — |

**Key findings:**
- **pump-chain SHORT habitat = RSI 45-55** (41T, 48.8% WR, +$0.15). Current floor of 45 is correctly placed — blocks the negative 35-45 band, allows the positive 45-55 band.
- **"other" signals habitat = RSI <25** (105T, 58.1% WR, +$0.39). Current floor of 45 **blocks this entire profitable band**.
- **grind SHORT loses everywhere** — no RSI band saves it.

## Proposal

Replace the blanket `SHORT_RSI_HARD_FLOOR = 45` with per-signal RSI bands, similar to `volatility_gate_v2.py SIGNAL_TYPE_OVERRIDES`.

### Design

```python
# Per-signal SHORT RSI bands: (min, max) — None = no limit
# Signals not listed use the default floor (SHORT_RSI_HARD_FLOOR)
SHORT_RSI_HABITATS = {
    'pump-chain':    (40, 70),   # 45-55 is the sweet spot; 40 buffer for exec drift
    'volume-breakout': (30, 75), # needs more data
    'volume-buildup':  (30, 75), # needs more data
    'ai-trader':    (25, 70),   # needs more data
    'hzscore':      (20, 70),   # needs more data
    'range-reversion': (15, 65), # mean-reversion, works at extremes
    'spike-exhaustion': (10, 50), # exhaustion at extremes
    'rs':           (20, 70),   # S/R signal
    # grind: not listed — uses default floor (loses everywhere)
}
```

### Behavior

1. Signal fires as SHORT
2. Look up signal family in `SHORT_RSI_HABITATS`
3. If found: check RSI against (min, max) band — block if outside
4. If not found: use default `SHORT_RSI_HARD_FLOOR` (45)
5. Bear-structure override: if BTC is LEAN_BEAR + BELOW EMA300, relax min by 10 (oversold = continuation in confirmed downtrend)

### Constants

```python
SHORT_RSI_HABITAT_ENABLED = True     # master switch
SHORT_RSI_HARD_FLOOR = 45            # default for unlisted signals (unchanged)
SHORT_RSI_HABITAT_BEAR_RELAX = 10    # relax min by this when BTC bear structure
```

## Risks

1. **Small samples** — some bands have n=5-9. Need 7d monitoring.
2. **Filter collision** — bear-structure override might conflict with SHORT_CONTINUUM_SCORE_MAX.
3. **Execution drift** — signal-time RSI vs exec-time RSI can differ by 10-20 points (DRIFT-E). Bands need buffer.

## Mitigation

1. Shadow-log first: log what WOULD be blocked vs current behavior for 7d
2. Bands have ±5 point buffer beyond the data-driven edges
3. Bear-structure override is additive (relaxes min, never tightens)

## Implementation

1. Add `SHORT_RSI_HABITATS` dict to `hermes_constants.py`
2. Add `SHORT_RSI_HABITAT_ENABLED` flag (default True)
3. Modify `signal_compactor.py` SHORT RSI check to use per-signal bands
4. Modify `decider_run.py` exec-time SHORT RSI check to use per-signal bands
5. Shadow-log mismatches for 7d

## Success Metrics

- SHORT trades/day increases (currently ~0-2, target 3-5)
- SHORT WR maintained or improved (currently ~40%)
- "other" signals at RSI <25: monitor if the +$0.39/60d edge holds
- pump-chain at RSI 40-45: monitor if relaxing from 45 to 40 hurts
