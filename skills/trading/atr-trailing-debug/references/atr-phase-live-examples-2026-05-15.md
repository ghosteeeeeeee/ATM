# ATR Phase System — Live Examples (2026-05-15)

Complete worked examples for MON and ADA showing how the three-stage model resolves in practice. These are real live trades verified against the running system.

## The Two Phase Detection Systems

**`_phase_from_pct`** (tpsl_utils.py:73-88) — used for ATR k scaling:
```
Thresholds: 50 / 70 / 90
Returns: 'neutral', 'building', 'accelerating', 'exhaustion', 'extreme'
```

**`detect_phase`** (signal_gen.py:491-511) — used for signal generation:
```
Thresholds: PHASE_BUILDING=60, PHASE_ACCELERATING=75, PHASE_EXHAUSTION=88, PHASE_EXTREME=95
First check: percentile < 60 AND |velocity| < 0.05 → 'quiet'
```

**⚠️ These produce DIFFERENT phase labels for the same momentum state.** The ATR k scaling uses `_phase_from_pct`, NOT `detect_phase`. Do not conflate the two — they serve different purposes.

---

## MON (LONG) — 2026-05-15

**Position:** entry=0.028891, current=0.028923, highest=0.028923, pnl=+0.11%, state=IN_PROFIT

**Momentum data:**
- ATR(15m) = 0.000266 → atr_pct = 0.92% (< 1% → LOW_VOL)
- percentile_long = 40.5
- velocity = -0.0341 (negative = price falling against LONG direction)
- phase (from get_momentum_stats) = 'building'

**Stage 1 — ATR tier:**
```
atr_pct = 0.000266 / 0.028891 = 0.92% < ATR_PCT_LOW_THRESH=1%
→ base_k = ATR_K_LOW_VOL = 1.0
```

**Stage 2 — Phase detection (`_phase_from_pct(40.5, -0.0341)`):**
```
pct=40.5 < 50 → 'neutral'  (tier 0)
phase_tier < PHASE_TIER_ACCELERATING (2)
→ mult = 1.0  (no acceleration squeeze)
k_final = 1.0 × 1.0 = 1.0
```

**Stage 3 — compute_atr_sl_tp:**
```
is_new_trade = False  (highest=0.028923 vs entry=0.028891, diff=0.11% > 0.1%)
in_profit = True (pnl_pct=0.11 > 0)
→ state = IN_PROFIT
→ MIN_SL_PCT = ATR_SL_MIN_ACCEL = 0.70%  (established trade floor)

sl_pct = k_final × atr_pct = 1.0 × 0.00922 = 0.922%
tp_pct = k_final × ATR_TP_K_MULT × atr_pct = 1.0 × 1.25 × 0.00922 = 1.153%

eff_sl_pct = min(max(0.922%, 0.70%), 1.0%) = 0.922%  (raw wins, above floor)
eff_tp_pct = min(max(1.153%, 1.5%), 5.0%) = 1.153%

anchor = highest_price = 0.028923 (LONG)
new_sl = 0.028923 × (1 - 0.00922) = 0.028656
new_tp = 0.028923 × (1 + 0.01153) = 0.029256

Trailing gate (LONG): new_sl=0.028656 vs current_sl=0.028656 → 0.028656 > 0.028656? NO → needs_sl=False
TP tightening (LONG): new_tp=0.029256 vs current_tp=0.029256 → same anchor, would tighten → needs_tp=True
```

**Result:** SL unchanged, TP would tighten slightly. k=1.0, phase=neutral, no acceleration.

---

## ADA (LONG) — 2026-05-15

**Position:** entry=0.26107, current=0.260675, highest=0.26107, pnl=-0.15%, state=ESTABLISHED (underwater)

**Momentum data:**
- ATR(15m) = 0.001554 → atr_pct = 0.60% (< 1% → LOW_VOL)
- percentile_long = 60.0
- velocity = -0.0487 (negative = price falling against LONG direction)
- phase (from get_momentum_stats) = 'quiet'

**Stage 1 — ATR tier:**
```
atr_pct = 0.001554 / 0.26107 = 0.595% < ATR_PCT_LOW_THRESH=1%
→ base_k = ATR_K_LOW_VOL = 1.0
```

**Stage 2 — Phase detection (`_phase_from_pct(60.0, -0.0487)`):**
```
pct=60 falls in 50-69 range → 'neutral'  (tier 0)
phase_tier < PHASE_TIER_ACCELERATING (2)
→ mult = 1.0  (no acceleration squeeze)
k_final = 1.0 × 1.0 = 1.0
```

**Stage 3 — compute_atr_sl_tp:**
```
is_new_trade = False  (highest=0.26107 vs entry=0.26107, diff=0.00% < 0.1%)
  BUT: is_new_trade requires BOTH peak≈entry AND in_profit=True.
  in_profit = False (pnl_pct=-0.15% < 0) → is_new_trade = False
→ state = ESTABLISHED
→ MIN_SL_PCT = ATR_SL_MIN_ACCEL = 0.70%  (not new trade)
→ MIN_TP_PCT = ATR_TP_MIN_ACCEL = 1.0%

sl_pct = k_final × atr_pct = 1.0 × 0.00595 = 0.595%
tp_pct = k_final × ATR_TP_K_MULT × atr_pct = 1.0 × 1.25 × 0.00595 = 0.744%

eff_sl_pct = min(max(0.595%, 0.70%), 1.0%) = 0.700%  (ACCEL floor wins!)
eff_tp_pct = min(max(0.744%, 1.0%), 5.0%) = 1.000%  (ACCEL floor wins!)

anchor = highest_price = 0.26107 (LONG, price currently below peak)
new_sl = 0.26107 × (1 - 0.00700) = 0.259247
new_tp = 0.26107 × (1 + 0.01000) = 0.263686

Trailing gate (LONG): new_sl=0.259247 vs current_sl=0.259247 → equal, not tighter → needs_sl=False
TP gate (LONG): new_tp=0.263686 vs current_tp=0.263686 → equal → needs_tp=False
```

**Result:** SL and TP both at their floored values. needs_sl=False, needs_tp=False. k=1.0, phase=neutral.

---

## Key Insight — Why Both Get k=1.0 Despite Different Momentum States

The ACCEL floor (0.70%) on ADA is what sets the actual SL distance, not the raw atr_pct (0.60%). ADA's sl_pct would be 0.595% but the floor forces it to 0.70%. MON's sl_pct (0.922%) exceeds the INIT floor (0.50%) so the raw value wins.

Both coins are LOW_VOL (atr_pct < 1%) → base_k=1.0. Neither gets a phase multiplier squeeze because both resolve to 'neutral' in `_phase_from_pct` (which uses 50/70/90 thresholds), not 'accelerating' or 'exhaustion' (which would require percentile ≥ 90).

The different `detect_phase` labels ('quiet' for MON, 'building' for ADA) are irrelevant for ATR k scaling — the k scaling reads `_phase_from_pct` directly, not `detect_phase`.