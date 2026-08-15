## CEO Report — 2026-08-15

### Diagnosis
24h 71T -$0.72 (49.3% WR — RED). 48h R:R inverted 0.60:1: avg win 0.45% ($0.045) vs avg loss -0.73% (-$0.074). ATR_SL dominates losses: 50T avg -0.79% (-$4.03). Profit-monster-trail exits at avg 0.32% (+$2.15 winners). ATR_TP barely fires (1T/48h). SHORT atr_sl_hit trades have 1.85% avg MFE but still close at -0.78% — trailing not catching reversals. NEUTRAL regime (102/104 tokens), 2 open, disk 83%.

### Root Cause
Structural R:R inversion. Losses are 1.6x larger than wins (-0.73% vs 0.45%). ATR_TP_K_MULT 2.0 sets target at ~1.6%, but trailing exits winners at 0.32% before reaching it. ATR_SL at -0.79% is the dominant exit. The gap between win size and loss size is the core bleed.

### Fix Applied
BUMPED ATR_TP_K_MULT 2.0→2.5. New target: ~2.0% (capped by ATR_TP_MAX). Expected R:R improvement: 0.60:1 → 0.75:1. Even if trailing continues to dominate, higher target means winners that do reach ATR_TP capture more profit.

### Verification
Monitor 48h: R:R ratio (should ↑ from 0.60:1), avg win (should ↑ from 0.45%), atr_sl_hit count (should ↓). If no improvement by Aug 17 → consider widening ATR_SL range or adjusting trailing activation.
