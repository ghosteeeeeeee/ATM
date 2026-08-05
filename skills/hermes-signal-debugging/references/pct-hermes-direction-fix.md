# pct-hermes Direction Fix + BLACKLIST (2026-05-04/05)

## Summary of Decisions

| Signal | Action | Reason |
|--------|--------|--------|
| `pct-hermes-` | **BLOCKED** (2026-05-05) | 0% WR in bear market — fires at bottoms, catches falling knives |
| `pct-hermes+` | **UNBLOCKED** (2026-05-05) | Direction flipped 2026-05-04, now correct: buy suppressed, sell elevated |
| `pct-hermes` (bare) | BLOCKED | Combo-only source |

## The Direction Fix (2026-05-04)

**Location**: `signal_gen.py` lines 1686-1692

**Semantics** (counter-intuitive naming):
```
pct_short = % of 200-bar lookback where price >= current
           → HIGH pct_short = price at BOTTOM of range (most bars are above you)

pct_long  = % of 200-bar lookback where price <= current
           → HIGH pct_long = price at TOP of range (most bars are below you)
```

**OLD — inverted**:
```python
if pct_long >= 72:
    pct_signal_dir = 'LONG'    # WRONG: buy at top
elif pct_short >= 72:
    pct_signal_dir = 'SHORT'   # WRONG: sell at bottom
```

**NEW — correct**:
```python
if pct_long >= 72:
    pct_signal_dir = 'SHORT'    # price elevated = sell the rally
elif pct_short >= 72:
    pct_signal_dir = 'LONG'     # price suppressed = buy the dip
```

**Emulated results after flip (62 trades)**:
| pct_short bucket | Before | After flip |
|---|---|---|
| 72-80% | 4.5% WR | **95.5%** WR |
| 80-85% | 0% | **100%** |
| 85-90% | 0% | **100%** |
| 90-95% | 0% | **96.2%** |
| 95%+ | 0% | **83.3%** |

## Why pct-hermes- Was BLOCKED (2026-05-05)

`pct-hermes-` fires SHORT when `pct_long >= 72` (price elevated). In a bear market:
- Price is elevated because it's bouncing UP from lows
- SHORT on elevated price = SHORT near the BOTTOM of the bounce
- Bear market: price bounces then continues down → SHORT wins
- But: price at bottom of bounce in bear market often bounces AGAIN (dead cat bounce)
- Result: 0% WR in bear market

Live evidence: All 30+ most recent losing trades were SHORTs with `pct-hermes-`. Win rate = 0%.

**Blocked via**: `SIGNAL_SOURCE_BLACKLIST` exact-match entry `'pct-hermes-'` in `hermes_constants.py` + component-level check in `signal_schema.py add_signal()`.

## Blacklist Entries (as of 2026-05-05)

```python
SIGNAL_SOURCE_BLACKLIST = {
    'pct-hermes-',   # BLOCKED: fires at bottoms in bear market, 0% WR
    'pct-hermes',    # BLOCKED: bare combo-only
    'gap-300-',      # BLOCKED: 14.3% WR, -1.52% PnL across 7 trades (worst active loser)
    # vel-hermes caught via SENTINEL_BASES suffix-agnostic check
}
# pct-hermes+ was UNBLOCKED after data analysis: 30.6% WR, +4.08% PnL across 36 trades
```
