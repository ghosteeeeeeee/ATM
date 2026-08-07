## 2026-08-07: Trade Loss Elimination — ATR SL + Dead Hours

**Problem:** 48h analysis showed 113 closed trades, 56.6% WR but net break-even (+$0.13). All losses came from `atr_sl_hit` (48 trades, -$3.13). SHORT SL hits were 0% WR (-$1.98).

**Root cause:** ATR SL was too tight. Low-vol tokens (ATR<1%) had k=0.5 × 0.8% floor = 0.4% effective SL — noise level. 29/48 SL hits drifted >60 min, meaning stops were too tight for hold time.

**Changes applied:**
1. ATR_SL_MIN: 0.8% → 1.2% (wider floor)
2. ATR_SL_MAX: 2.1% → 2.5% (wider cap for high-vol)
3. ATR_K_LOW_VOL: 0.5 → 0.8 (low-vol effective SL: 0.4% → 0.96%)
4. DEAD_HOURS_ENABLED: False → True (blocks 03:00-08:00 UTC)
5. KAITO blacklisted (both dirs) — 5 SL hits in 48h

**Key finding:** Confluence signals (bb_bounce+hzscore) hit 100% WR. Profit monster exits are 94-100% WR. The entry/SL side is where all the bleeding happens.

**Other patterns discovered:**
- SHORT exhaustion combos (return_exhaustion-) are toxic
- 13:00-17:00 UTC clusters losses
- 12:00 UTC is golden (100% WR, 8 trades)
