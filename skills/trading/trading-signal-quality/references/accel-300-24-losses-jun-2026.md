# accel-300 Signal Quality Failures — June 2026

## Session Context
- Date: 2026-06-07
- Event: 24 consecutive accel-300 losses (both LONG and SHORT), ~1-2% each, 3-16 min hold times
- Tokens: XLM, MORPHO, MOVE, MERL, XMR, TON, ONDO, MON, LINEA, UMA, ENS, BSV, AVNT, Z2, LINK, etc.
- Core issue: signal fires at micro-gaps near EMA that immediately reverse — catching tops/bottoms

---

## The 5 Bugs Identified

| # | Bug | Severity | Fix |
|---|---|---|---|
| 1 | `ACCEL_300_LOOKBACK=35` — cross search misses recent crosses, falls back to ancient cross (200+ bars ago), making gap_expansion check meaningless | CRITICAL | `LOOKBACK: 35 → 500` |
| 2 | `ACCEL_300_MIN_GAP_EXPANSION=0.00` — any positive gap passes since ancient cross gap≈0% | CRITICAL | `EXPANSION: 0.00 → 0.05` |
| 3 | `ACCEL_300_STALE_BARS=200` defined but never checked in code — misleading dead code | LOW | Remove from constants |
| 4 | No minimum bars check — tokens with <350 bars have unconverged EMA(300), garbage gaps | MEDIUM | Require ≥350 bars before scanning |
| 5 | Stale gate skipped when `i = n-2` (signal bar = newest) — gap can collapse immediately post-signal without detection | MEDIUM | Always check newest bar gap |

---

## Why All Trades Lost

The signal logic sequence for a typical trade (e.g., XLM LONG at 22:54):

1. cond2 (gap check): gap=1.55% > MIN_GAP=0.08% → **PASS**  
2. cond3 (persistence): price above EMA for 4 bars → **PASS**  
3. cross_bar: primary search (35 bars) misses; fallback finds bar 209 bars ago → gap_at_cross≈0%  
4. cond4c (gap_expansion): gap_now(1.55%) > gap_at_cross(0%) + 0.00% → **PASS** (meaningless)  
5. stale gate: skipped because `i = n-2`  
6. **SIGNAL FIRES** at gap=1.55% — but gap is already collapsing

Post-signal: gap falls from 1.55% → 0.65% over 8 bars (~8 min). Price mean-reverts. SL hit.

---

## Key Diagnostic Traces

```python
# Trace bars_since_cross for any token — if >35, primary search is missing crosses
# ACCEL_300_LOOKBACK=35: crosses found 35+ bars ago use FALLBACK search
# STALE_BARS=200: bars_since > 200 flagged as STALE but NOT BLOCKED (dead code)

# To check: what is ACCEL_300_LOOKBACK currently set to?
from hermes_constants import ACCEL_300_LOOKBACK
print(ACCEL_300_LOOKBACK)  # if 35, cross search is too short

# To check: is MIN_GAP_EXPANSION blocking anything?
from hermes_constants import ACCEL_300_MIN_GAP_EXPANSION
print(ACCEL_300_MIN_GAP_EXPANSION)  # if 0.00, gate is non-functional
```

---

## Recommended Fix Priority

1. **Immediate**: `ACCEL_300_LOOKBACK: 35 → 500`  
2. **Immediate**: `ACCEL_300_MIN_GAP_EXPANSION: 0.00 → 0.05`  
3. **Quick**: Add minimum 350 bars check before scanning token  
4. **Quick**: Fix stale gate to always check newest bar regardless of signal position  
5. **Cleanup**: Remove `ACCEL_300_STALE_BARS=200` from hermes_constants (dead code)  
6. **Consider**: `ACCEL_300_PERSISTENCE_BARS: 4 → 6` (filter micro-pullbacks)