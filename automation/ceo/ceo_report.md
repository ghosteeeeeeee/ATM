## CEO Report — 2026-09-22 ~17:50 UTC

### Decision: RE-ENABLE bb_bounce_v2_long

### Diagnosis
24h: 26T 26.9%WR -$2.51. 7d: 189T 45.5%WR -$0.05. Dead hours fix WORKING — 0 pump-chain+ trades after 09:30 UTC. Without dead hours, pump-chain+ = 30T 60%WR +$3.48/7d (excellent). bb_bounce_v2_long killed Sep 11 by signal_reporter (4T/24h 25%WR) but30d = 73T 74%WR +$2.08 — best standalone WR in system.

### Root Cause
bb_bounce_v2_long was killed based on 4-trade sample (short-term variance). Signal has73 trades at 74% WR over 30d — statistically significant edge. Dead hours enforcement was working but trades before fix still impacted 24h numbers.

### Fix Applied
1. **BB_BOUNCE_V2_LONG_ENABLED = True** — re-enabled. NOT in NEVER_REENABLE_FLAGS. Expected +$0.50-1.00/7d.
2. **Dead hours fix verified** — 0 pump-chain+ trades after 09:30 UTC. Non-dead-hours performance: 30T 60%WR +$3.48/7d.

### Verification
- DB: 0 pump-chain+ LONG trades with open_time > 09:30 UTC ✅
- bb_bounce_v2_long30d: 73T 74%WR +$2.08 ✅
- Current.md updated ✅, kanban updated ✅, this report ✅

---

## CEO Report — 2026-09-22 ~14:00 UTC

### Decision: NO CONFIG CHANGE — MONITORING DEAD HOURS FIX

### Diagnosis
System fragile. 24h: 32T 31.3%WR -$2.92 (worst day recently). 7d: 194T 46.9%WR +$0.53 (barely positive). All NEUTRAL. 0 open. Dead hours enforcement re-enabled today — expected to recover.

### Key Numbers (DB-verified)
- **24h:** 32T 31.3%WR -$2.92. ATR_SL 26/32 exits (81%). pump-chain+ 13T 15.4%WR -$1.51 (dead hours bleed). pullback-entry- 4T 0%WR -$1.10 (cold streak).
- **7d:** 194T 46.9%WR +$0.53. pump-chain+ 55T 41.8%WR +$1.23 (workhorse, DEGRADED). volume-breakout-long+ 16T 68.8%WR +$1.41 (gem).
- **30d active:** 50 signal types. Only 2 are net positive (pump-chain+ and volume-breakout-long+). System carried by 2 signals.
- **pump-chain+ RSI analysis:** RSI 55-65 = sweet spot (60%WR +$1.35). RSI 76-80 = dead zone (6T 0%WR -$0.82). RSI>80 = big winners (14T +$1.13). RSI_MAX=75 optimal — blocks dead zone, preserves winners.

### Root Cause
PUMP_CHAIN_LONG_DEAD_HOURS enforcement was COMMENTED OUT in signal_compactor.py. Config existed [0,1,2,3,4,5,23] but trades still fired in hours 0-5,23 (0%WR historically). 14d dead hours = 29T 0%WR -$3.30.

### Fix Applied
Dead hours enforcement re-enabled ~09:30 UTC today. Expected +$1.65/7d.

### RSI_MAX Decision
NOT changing PUMP_CHAIN_LONG_RSI_MAX from 75 to 65. Brain_auditor proposed 65 but data shows RSI>80 = 14T +$1.13 (big winners). RSI_MAX=65 would block winners. Current 75 blocks dead zone (76-80) while preserving RSI>80.

### Signal Diversity Problem
Only pump-chain+ LONG and volume-breakout-long+ pass confluence in NEUTRAL. 50 signal types active but 48 are net negative or blocked. Need new signals for diversity.

### Monitoring
1. Dead hours fix — verify no pump-chain+ trades in hours 0-5,23 on next runs
2. pullback-entry- cold streak — 30d lifetime still positive (53.4%WR +$0.94), likely variance
3. pump-chain+ DEGRADED — no regime >55%WR, monitoring if dead hours fix helps
4. Oscillator shadow eval due Sep 23
5. System structurally healthy — active signals profitable

---

## CEO Report — 2026-09-21 ~18:10 UTC

### Decision: NO CONFIG CHANGE — MONITORING

### Diagnosis
System healthy but thin. 24h: 24T 37.5%WR -$0.05 (breakeven). 7d: 193T 49.2%WR +$2.36. 1 open. All NEUTRAL regime.

### Key Numbers (DB-verified)
- **24h:** 24T 37.5%WR -$0.05. 10Atr_sl losses, 14 wins. Normal variance.
- **7d:** 193T 49.2%WR +$2.36. LONG 120T 50.8%WR +$3.32. SHORT 73T 46.6%WR -$0.96.
- **Top signals:** pump-chain+ LONG 47T 48.9%WR +$2.66 (workhorse). volume-breakout-long+ 16T 68.8%WR +$1.41 (gem).
- **SHORT bleed:** pullback-entry- 55T 47.3%WR -$0.59 (7d). But 90d: 112T 55.4%WR +$2.04 — cold streak, not systemic.
- **Regime:** 100% NEUTRAL. No EXTREME edge available.

### Why No Action
1. 24h breakeven — no emergency
2. SHORT losses are cold streaks in generally profitable signals
3. Oscillator shadow running (eval due ~Sep 23)
4. Hotset empty by design — confluence gate correctly filtering low-confidence signals
5. System is $2.36/7d positive — thin but real

### Next
- Monitor oscillator shadow eval (Sep 23)
- Signal diversity remains priority (NEUTRAL regime bottleneck)
- No config changes unless numbers deteriorate

---

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

---

## CEO Report — 2026-09-21 ~18:00 UTC — MACRO THESIS REVIEW

### Decision: BTC 4-Year Cycle — System Adaptation Recommendations

### Thesis Assessment
BTC bottomed Aug 2026 at $62,622. Current: $85,966 (+38%). 13-year pattern: 3yr bull + 1yr bear, 9-step parabolic moves. If valid, bull runs until ~Aug 2029.

**Verdict: Thesis is credible.** 4 confirmed cycles with 77-85% bear drawdowns and consistent timing. The Aug 2026 bottom aligns with the ~1,400-day cycle spacing. System should adapt.

### Verified System Context
- **7d:** 191T, 49.2% WR, +$2.61 (NEUTRAL regime only)
- **LONG vs SHORT:** LONG +$3.61/7d (51.3% WR). SHORT -$0.96/7d (45.9% WR). **LONG already dominant.**
- **30d NEUTRAL LONG:** bb_bounce_v2_long 74%WR +$2.08, volume-breakout-long+ 68.8%WR +$1.41, pump-chain+ 45.7%WR +$2.39. **Profitable.**
- **LONG_NEUTRAL_BLOCK=True** — currently blocks LONG entries in NEUTRAL. Data says this is wrong for a bull macro.

### Recommendations (Ranked by Impact)

**1. LONG Bias — Already Happening (NO CHANGE NEEDED)**
The system is already implicitly LONG-biased: pump-chain+ LONG carries +$2.95/7d, volume-breakout-long+ adds +$1.41. SHORT signals are net losers (-$0.96/7d). The data agrees with the macro thesis — LONG is the winning side.

**2. Cycle Support Level — Define the Invalidation Price**
- **$62,622** (Aug 2026 bottom) = absolute floor. Below = thesis broken.
- **$69,000** (previous cycle peak) = first warning. Below = investigate.
- **Action:** Add `BTC_CYCLE_SUPPORT = 62622` and `BTC_CYCLE_WARNING = 69000` to hermes_constants.py. If BTC drops below warning, reduce position sizes. If below support, flatten and reassess.

**3. Wider Stops for LONG — YES, but cautiously**
- Current ATR_SL: 1.3-1.5%. In a bull market with 0.3-0.6x corrections, stops at 1.3% will get hit on normal pullbacks.
- **Recommendation:** Widen ATR_SL_MIN to 1.5%, ATR_SL_MAX to 1.8% for LONG positions only. Short-term pain (bigger losses on stops) but fewer stopped-out winners.
- **Expected impact:** Fewer premature exits, but larger losses when wrong. Net positive if thesis holds.
- **Caveat:** This is a macro bet. If thesis is wrong, wider stops = bigger losses. The 0.6x correction target at $85k = $51k (-40%). Wider stops won't survive that — only the cycle support level matters.

**4. Fibonacci Price Targets — Map the 9 Steps**
From $62,622 bottom, using Fibonacci extensions:
- Step 1-3: $85k-$100k (we're here — slow grind phase)
- Step 4-6: $120k-$160k (acceleration phase, ~12-18 months)
- Step 7-9: $200k-$300k+ (parabolic blow-off, last 3-6 months)
- **Action:** No system change needed for targets. The PM_TRAIL already handles profit-taking dynamically.

**5. Position Sizing — DO NOT change yet**
- Current sizing works. Don't increase LONG size until the thesis is confirmed by price action above $100k.
- **If BTC breaks $100k:** Consider increasing LONG position size by 20-30%.
- **If BTC drops below $69k:** Reduce LONG size by 50%.

**6. SHORT Strategy — Reduce, Don't Eliminate**
- SHORT signals are already losers (-$0.96/7d). The SHORT_RSI_FLOOR=30 and SHORT_NORMAL_PENALTY=0.85 are already suppressing SHORT entries.
- **Recommendation:** Keep SHORT alive for hedging only. Don't disable completely — violent corrections (0.5x) are shorting opportunities. But SIZE SHORT positions smaller than LONG.

**7. Late Bull Risk Management**
- The 9-step pattern shows corrections get more violent (0.3x → 0.5x → 0.6x).
- **Action:** When BTC is above $200k (step 7+), tighten PM_TRAIL distance from 0.20% to 0.15% to lock in profits faster. Not now — too early.

### What NOT to Do
- **DO NOT** remove LONG_NEUTRAL_BLOCK yet — current data is mixed, wait for bull confirmation
- **DO NOT** increase position sizes — too early, thesis not confirmed above $100k
- **DO NOT** disable SHORT entirely — corrections are buying opportunities, but also shorting opportunities
- **DO NOT** change PM_TRAIL — it's already optimized for profit capture

### Implementation Priority
| Change | Impact | Risk | Action |
|--------|--------|------|--------|
| Define cycle support levels | HIGH | None | Add constants, log only |
| Widen LONG stops (1.5-1.8%) | MEDIUM | Medium | Backtest first, then implement |
| Reduce SHORT normal penalty | LOW | Low | Already at 0.85, monitoring |
| Increase LONG size at $100k | HIGH | High | WAIT — not yet |
| Tighten PM_TRAIL at $200k | MEDIUM | Low | WAIT — too early |

### Next Steps
1. **Immediate:** Add BTC_CYCLE_SUPPORT and BTC_CYCLE_WARNING constants
2. **This week:** Backtest wider ATR_SL (1.5-1.8%) on LONG positions — does it improve 7d PnL?
3. **Monthly:** Re-evaluate thesis — is BTC above the cycle support trajectory?
4. **If BTC breaks $100k:** Revisit position sizing recommendations

---

## CEO Report — 2026-09-21 ~17:30 UTC — Architecture Review: Real-Time Regime Check

### Decision: DO NOT ADD — Detection-time regime is correct

### Architecture Assessment

**Q1: Is this duplicating existing logic?**

YES. Two regime check mechanisms already exist in `decider_run.py` (lines 3211-3255), **both disabled on 2026-05-11** for the same reason: 1m LR regime is too noisy for execution gating. Additionally, `signal_compactor.py` already computes regime at compaction time (line 2247: `get_regime_1m()`, line 2248: `get_regime_4h()`) and applies 15+ regime-specific filters before signals enter hotset.json.

**Q2: Does this increase complexity unnecessarily?**

YES. Adding a real-time regime check in `decider_run.py` would be a **third layer** of regime filtering on top of:
1. signal_compactor scoring (1m regime, line 2571)
2. signal_compactor confluence gates (4h regime, lines 2347-2408)
3. Hotset entry regime data (line 2769)

This creates contradictory filter interactions — compactor approved based on regime X, execution blocks because regime shifted to Y.

**Q3: Simplest implementation?**

**Skip it.** The detection-time regime is the correct signal. Here's why:

- Compactor runs every ~2min, execution follows within the same pipeline cycle
- The staleness window is ~2-4 minutes — regime rarely shifts meaningfully in that window
- When regime DOES shift (crash, sudden reversal), other filters catch it: BTC crash filter (line 2993), staleness price drift check (line 3129), ATR stop-loss
- Adding a regime re-check would block valid trades that survived compaction's vetting

**Q4: 1m vs 4h regime?**

Neither is appropriate for execution-time checks:
- **1m regime**: Proven too noisy (disabled twice for false SHORT_BIAS). 50-candle linear regression on 1m data = 50 minutes of noisy price action
- **4h regime**: Too slow — changes every 4 hours, won't catch rapid shifts between detection and execution

The 5m regime scanner (15m_regime_scanner.py) is the best available, but even it doesn't add value at execution time because compactor already vetted the signal against it.

**Q5: Alternative approaches?**

If regime staleness becomes a measurable problem (evidence: trades losing specifically because regime shifted in the 2-4min window), the simplest fix is:

1. **Log regime shift** (not block) — add a counterfactual log: "regime was X at detection, is Y now"
2. **After 100+ logged shifts**, analyze if any correlation with losses exists
3. **Only then** add a conditional block for extreme shifts (e.g., LONG_BIAS→SHORT_BIAS with conf>70)

### Complexity Analysis

| Approach | Lines | Risk | Value |
|----------|-------|------|-------|
| Real-time regime check (proposed) | ~30 new, conflicts with existing 15+ filters | HIGH — false blocks, contradictory gating | LOW — staleness window is 2-4min |
| Log-only regime shift tracking | ~10 lines, no conflicts | NONE | MEDIUM — gathers data for future decisions |
| Do nothing (recommended) | 0 | NONE | HIGH — existing architecture is correct |

### Recommendation

**DO NOT implement real-time regime check.** The detection-time regime is the correct design decision. The compactor is the "approval authority" (decider_run.py:2969), and it already does comprehensive regime filtering. Adding execution-time regime re-checks:

1. Contradicts the compactor's approval
2. Adds filter interaction bugs (two filters making opposite decisions)
3. Solves a problem that doesn't exist yet (no evidence of losses from regime staleness)

If you want regime staleness data for future analysis, the lazy version is a single log line in the exec loop (10 lines, zero risk). Say the word and I'll add it.

### Verification
- Lines 3211-3255 in decider_run.py: both regime checks disabled 2026-05-11
- Lines 2247-2408 in signal_compactor.py: 15+ active regime checks at compaction time
- Staleness window: compactor→execution = ~2-4 minutes (pipeline cycle time)
- No evidence in trade data of losses attributable to regime staleness
