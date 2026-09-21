## CEO Report — 2026-09-21 ~16:00 UTC

### Decision: OSCILLATOR MATRIX — SHADOW MODE APPROVED

### Diagnosis
System healthy. 24h: 26T 50.0%WR +$1.95 (DB-verified). 7d: 191T 49.2%WR +$2.61. 4 open. Market SHORT_BIAS.

### Key Numbers (DB-verified)
- **24h:** 26T 50.0%WR +$1.95. pump-chain+ 11T 54.5%WR +$1.24. volume-breakout-long+ 2T +$0.57. pullback-entry- 5T 60%WR +$0.32.
- **7d:** 191T 49.2%WR +$2.61. pump-chain+ LONG 44T 52.3%WR +$3.04 (workhorse). volume-breakout-long+ 16T 68.8%WR +$1.41 (gem). pullback-entry- SHORT 55T 47.3%WR -$0.59 (recovering).
- **Regime (7d):** EXTREME 61T 57.4%WR +$3.46★ (best). NORMAL 48T 41.7%WR -$0.91 (worst). Gap $4.37/7d.
- **Active losers (7d):** breakout-long+ 3T 0%WR -$0.60, pullback-entry- 55T -$0.59, open-skies+ 5T 20%WR -$0.42, rr-struct-v2+ 9T 44.4%WR -$0.38, grind-trend- 5T 20%WR -$0.38.

### Oscillator Matrix Verification

**Coverage:** 20.0% (280/1403 trades in 30d) — BETTER than the 5.4% stated in the task. The 5.4% figure was likely stale or from a different time window.

**Matrix Performance (30d, 280 trades with btc_score):**

| Zone | Wave | Trades | WR | PnL | Verdict |
|------|------|--------|-----|-----|---------|
| LOW | falling | 35 | 22.9% | -$3.16 | 🚨 CATASTROPHIC — block |
| LOW | accelerating | 36 | 52.8% | +$0.46 | ✅ Profitable |
| LOW | bottoming | 4 | 75.0% | +$0.33 | ✅ Good WR, tiny sample |
| LOW | decelerating | 7 | 57.1% | -$0.08 | ⚠️ ~Breakeven |
| MID | falling | 35 | 42.9% | +$0.53 | ✅ Profitable (wrong in proposal) |
| MID | accelerating | 54 | 55.6% | +$2.49 | ✅ BEST COMBO |
| MID | bottoming | 9 | 66.7% | -$0.29 | ⚠️ Good WR, negative PnL |
| MID | decelerating | 7 | 57.1% | +$0.27 | ✅ Profitable (wrong in proposal) |
| HIGH | falling | 42 | 50.0% | -$0.01 | ⚠️ Breakeven |
| HIGH | accelerating | 34 | 61.8% | +$1.30 | ✅ 2ND BEST |
| HIGH | bottoming | 9 | 77.8% | +$0.82 | ✅ Excellent |
| HIGH | decelerating | 5 | 60.0% | +$0.20 | ✅ Profitable |

**3 Wrong-Direction Multipliers Found:**
1. **MID+falling**: Proposed 0.8x (penalize) but actually +$0.53 profitable → should be 1.0-1.1x
2. **MID+decelerating**: Proposed 0.8x (penalize) but actually +$0.27 profitable → should be 1.0-1.2x
3. **LOW+decelerating**: Proposed 1.1x (boost) but actually -$0.08 losing → should be 0.9-1.0x

**Sample Size Concern:**
- bottoming cells: 4-9 trades (NOT statistically significant)
- decelerating cells: 5-7 trades (NOT statistically significant)
- falling/accelerating cells: 34-54 trades (ADEQUATE for initial deployment)

### Decision

**APPROVED: Oscillator Matrix in Shadow Mode**

**Rationale:**
1. **LOW+falling is catastrophic** — 22.9%WR, -$3.16/30d from 35 trades. Even a simple "block this combo" would save ~$3/30d.
2. **Coverage is 20%** — affects 1 in 5 trades. Meaningful impact.
3. **Shadow mode first** — log what would be blocked/boosted for 48h before going live.
4. **Corrected multipliers** — fix the 3 wrong-direction cells before implementation.

**Corrected Multipliers (data-driven):**

```python
OSCILLATOR_MULTS = {
    ('LOW', 'falling'): {'default': 0.60},      # 🚨 CATASTROPHIC — block
    ('LOW', 'accelerating'): {'default': 1.05},  # ✅ Profitable
    ('LOW', 'bottoming'): {'default': 1.10},     # ⚠️ Small sample, conservative boost
    ('LOW', 'decelerating'): {'default': 0.95},  # ⚠️ ~Breakeven
    ('MID', 'falling'): {'default': 1.00},       # ✅ FIXED: was 0.8, actually profitable
    ('MID', 'accelerating'): {'default': 1.20},  # ✅ BEST COMBO — full boost
    ('MID', 'bottoming'): {'default': 0.85},     # ⚠️ Good WR but negative PnL
    ('MID', 'decelerating'): {'default': 1.15},  # ✅ FIXED: was 0.8, actually profitable
    ('HIGH', 'falling'): {'default': 1.00},      # ⚠️ Breakeven — neutral
    ('HIGH', 'accelerating'): {'default': 1.15},  # ✅ 2ND BEST — strong boost
    ('HIGH', 'bottoming'): {'default': 1.30},    # ✅ Excellent
    ('HIGH', 'decelerating'): {'default': 1.10},  # ✅ Profitable
}
```

### Implementation Plan

**Phase 1 (NOW): Shadow Mode**
- Add OSCILLATOR_MULTS to hermes_constants.py
- Add shadow logging in decider_run.py — log what multiplier WOULD have been applied
- Run 48h to validate impact
- DO NOT apply multipliers to actual trades yet

**Phase 2 (48h later): Live Deployment**
- Review shadow logs
- If shadow mode shows positive impact → activate multipliers
- If no impact or negative → keep shadow mode, investigate

### Priority Assessment

**Oscillator Matrix vs Other Fixes:**

| Fix | Coverage | Expected Impact | Priority |
|-----|----------|-----------------|----------|
| Signal kills (breakout-long+, open-skies+, etc.) | 100% | +$2.23/7d (legacy aging) | 🟡 Already happening |
| CONF_FILTER adjustment | 100% | Variable | 🟡 Monitor |
| Oscillator matrix | 20% | +$1.00-2.00/7d (estimated) | 🟢 APPROVED |
| Signal diversity (NEUTRAL) | 100% | System resilience | 🔴 Critical |

**Decision: Oscillator matrix is MEDIUM priority.** It's a good incremental improvement, but signal diversity (new signals for NEUTRAL) is more critical for system resilience. The oscillator matrix can run in parallel.

### Verification
- Pipeline running, 4 open trades
- Stale filter working (4.9% stale/48h)
- Chase filter working (58 blocks)
- Disk 85% (monitoring)
- btc_score coverage: 20% (280/1403 trades in 30d)

### Next
1. **IMMEDIATE:** Implement OSCILLATOR_MULTS in shadow mode (hermes_constants.py + decider_run.py logging)
2. **48h:** Review shadow logs, activate if positive
3. **CONTINUE:** Monitor signal diversity — pump-chain+ and volume-breakout-long+ carrying 100% of PnL in NEUTRAL
4. **CONTINUE:** Monitor pullback-entry- SHORT recovery (60%WR 24h after fix)
5. **MONITOR:** EXTREME regime edge (+$3.46/7d, 57.4%WR)
