## CEO Report — 2026-08-08

### Diagnosis (Verified Numbers — DB queried directly)

| Period | Trades | PnL | WR |
|--------|--------|-----|-----|
| Last 24h | 52 | +$0.42 | 61.5% |
| Last 7d | 406 | -$1.23 | 48.0% |
| Lifetime | 9004 | -$1782.95 | 13.1% |

**Daily trend (7d):**
- Aug 1: 8t, -$0.60, 12.5% WR
- Aug 2: 46t, -$3.87, 8.7% WR
- Aug 3: 32t, -$3.07, 6.3% WR
- Aug 4: 32t, -$3.50, 3.1% WR
- Aug 5: 139t, +$2.32, 52.5% WR ← turning point
- Aug 6: 82t, -$0.54, 56.1% WR
- Aug 7: 56t, +$0.40, 62.5% WR
- Aug 8: 11t, +$0.15, 54.5% WR (partial)

**Signal combos bleeding (48h, worst):**
- hzscore-,return_exhaustion-: 8t, -$0.27, 37.5% WR
- ma100-cross,return_exhaustion-: 7t, -$0.28, 42.9% WR
- return_exhaustion-: 4t, -$0.09, 50% WR

**Winning combos (48h):**
- bb_bounce+,range_finder+: 9t, +$0.38, 88.9% WR
- hzscore+,return_exhaustion_long: 11t, +$0.12, 54.5% WR
- vortex_break_short: 2t, +$0.10, 100% WR

**System health:**
- 238/549 tokens stale (43%) — dead tokens cluttering speed tracker
- ATR SL widening (1.0%→1.2%) showing improvement

### Root Cause

**return_exhaustion- is hemorrhaging.** 14 trades across combos in 48h, -$0.64 total. The SHORT direction of return_exhaustion is consistently losing while the LONG variant (return_exhaustion_long) is profitable. Same pattern as hzscore- — SHORT variants of trend-fading signals lose in this market.

### Fix Applied

Disabled `RETURN_EXHAUSTION_MINUS_ENABLED = False` (hermes_constants.py:1301). This kills return_exhaustion- SHORT signals. The LONG variant (return_exhaustion_long) and confluence combos remain enabled.

### Verification

Monitor for 24h: expect return_exhaustion- combos to stop appearing. Target: eliminate the -$0.28/day bleed from return_exhaustion- losses. Also watch for stale token count — may need cleanup mechanism.
