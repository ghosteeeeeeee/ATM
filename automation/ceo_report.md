## CEO Report — 2026-08-09 (SHORT Signal Filter Analysis)

### Diagnosis
SHORT signals aren't firing. 100% NEUTRAL regime, volume low across the board. All4 SHORT signals require `MIN_VOLUME_RATIO = 1.2` — in a low-volume market, almost nothing passes this filter. Additionally, RSI overbought thresholds are at 55-60 (tight for NEUTRAL momentum).

### Root Cause
Volume filter is the primary blocker. In NEUTRAL regimes, volume rarely exceeds 1.2x average. RSI 55-60 is also tight for NEUTRAL markets where momentum is weaker.

### Fix Applied
**Option A: Volume 1.2x → 1.0x** on all4 SHORT signals.

Files changed:
- `scripts/signals/bb_bounce_short.py` — `MIN_VOLUME_RATIO = 1.0`
- `scripts/signals/range_finder_short.py` — `MIN_VOLUME_RATIO = 1.0`
- `scripts/signals/return_exhaustion_short.py` — `MIN_VOLUME_RATIO = 1.0`
- `scripts/signals/ma_100_cross_short.py` — `MIN_VOLUME_RATIO = 1.0`

All marked with `ponytail:` comments noting the original value and when to restore.

### Why Not Option C (also relax RSI)?
Lazy approach: try volume fix first, observe signal volume over 24h, then revisit RSI if needed. If volume alone doesn't generate enough signals, relax RSI thresholds next run.

### Verification
- Run `python3 scripts/signals/bb_bounce_short.py ETH` (and other tokens) to test signal generation
- Monitor pipeline log for SHORT signal entries over next 24h
- If SHORT signals still sparse, next step: relax RSI 55→50 on bb_bounce_short + range_finder_short
