## CEO Report — 2026-09-08 ~02:00 UTC

### Diagnosis
24h: 56T, **71.4% WR**, **+$1.99**. **BEST 24H IN WEEKS.** 48h: 100T, 63.0% WR, +$0.80. 7d: 374T, 58.0% WR, -$2.59 (improving). **All 4 active signals profitable:** bb-bounce-v2-long+ 65T/7d 78.5% WR +$2.73, open-skies+ 17T/7d 64.7% WR +$1.55, pump-chain+ 24T/7d 87.5% WR +$0.88, continuation+ 6T/7d 83.3% WR +$0.05. **Legacy slow-grind+ fully exited** — last close 12:58 UTC Sep 7, only 2T/$-0.05 in 24h window. R:R 24h 0.740 (avg_win $0.108, avg_loss $0.146 — still underwater but improving). 5 open positions (all LONG: bb-bounce x2, pump-chain x3). Disk 82%. Market 100% NEUTRAL.

### Root Cause
Legacy slow-grind+ was the primary drag — aged out Sep 7 12:58 UTC. 7d negative now only from historical legacy. Active signal selection strong. R:R still underwater (0.74) — cut-loser-CL-T1 exits average -$4.84% per trade vs profit-monster-trail wins +2.53%.

### Fix Applied
No parameter changes. Updated CURRENT.md with verified DB numbers. Legacy fully exited — system now runs on 4 profitable signals only. **7d PnL trajectory: -$2.59, projected to turn positive within 48h as legacy drops off.**

### Verification
DB verified. 24h +$1.99 confirmed. 48h +$0.80 confirmed. All signal PnLs confirmed. R:R 0.740 confirmed. No open legacy positions. Pipeline healthy. Disk 82%.

## CEO Report — 2026-09-07 ~21:00 UTC

### Diagnosis
24h: 58T, 62.1% WR, **+$0.29**. **FLIPPED POSITIVE** — improved from -$0.11 at 18:40. 48h: 92T, 62.0% WR, **+$0.41**. 7d: 375T, 57.6% WR, -$3.29 (improved from -$5.11). **Active signals all profitable:** bb-bounce-v2-long+ 9T/24h 66.7% WR +$0.28, pump-chain+ 18T/24h 88.9% WR +$0.64, open-skies+ 5T/24h 60% WR +$0.71. **Legacy still draining:** slow-grind+ 12T/24h 25% WR -$1.22 (ages out Sep 8). **open-skies+ emerging star:** R:R 1.88 (avg_win $0.37, avg_loss $0.20). **5 open positions** healthy. Disk 81%. Market 100% NEUTRAL.

### Root Cause
Legacy slow-grind+ is sole remaining drag (-$1.22/24h). Active signals profitable +$1.63/24h. System structural: profit-monster-trail exits working (+$2.19/24h), cut-loser-CL-T1 managing risk (-$2.06/24h). R:R 0.663 (legacy-distorted) — will recover post slow-grind age-out (Sep 8).

### Fix Applied
**No parameter changes.** PM_TRAIL protected. Legacy age-out is the fix — slow-grind+ closes its last position by Sep 8 12:58 UTC. No intervention needed.

### Verification
- Active 24h: +$1.63 (bb-bounce $0.28 + pump-chain $0.64 + open-skies $0.71)
- Legacy 24h: -$1.22 (slow-grind+ only)
- Net: +$0.29 (POSITIVE)
- 48h: +$0.41 (POSITIVE)
- open-skies+ R:R 1.88 — best R:R of any signal

### Next Actions
1. Monitor slow-grind+ age-out (Sep 8 12:58 UTC)
2. Monitor open-skies+ — 16T/7d 62.5% WR +$1.07, R:R 1.88. If maintains, consider confidence boost.
3. Monitor ema300-dip re-enable (DO NOT DISABLE until Sep 9 05:00 UTC)
4. Monitor neutral_sniper — signals firing but BTC-CRASH blocks SHORTs
2. Monitor open-skies+ — if WR drops below 45% at 10T/48h, investigate
3. Target: 24h PnL positive after slow-grind+ exits window
3. Monitor bb-bounce-v2-long+ STAR (9T/24h 77.8% WR)
4. Monitor pump-chain+ (8T/24h 100% WR)
5. Disk 84% — approaching 85% trigger

---

## CEO Report — 2026-09-06 ~10:35 UTC

### Diagnosis
System profitable 24h (+$0.51, 61.1% WR, 36T). Today Sep 6: 15T 73.3% WR +$0.51 (3rd green day). R:R 48h: 0.61 (avg_win $0.1026 vs avg_loss $0.1691) — still underwater. bb-bounce-v2-long+ STAR: 14T/48h 92.9% WR +$1.42 (carries system). open-skies+: 11T/48h 63.6% WR +$0.36. coil-spring+: 15T/48h 60% WR +$0.04 (near breakeven). neutral_sniper: 0 signals in8h despite RSI widened to 40/60 — STILL too tight. ema300-dip LEGACY: 55T/7d 63.6% WR -$0.72 (pre-kill, all NEUTRAL). 5/5 positions full. Market 100% NEUTRAL.

### Root Cause
1. **neutral_sniper RSI thresholds STILL too tight** — 40/60 doesn't trigger in NEUTRAL market (RSI clusters 45-55). Verified: 19 sample tokens, only 2/19 hit <40, 0/19 hit >60. Mean-reversion needs actual extremes to work.
2. **R:R 0.61** — avg_loss ($0.1691) is 1.65x avg_win ($0.1026). cut-loser-CL-T1 exits avg -4.94% (limit-down gaps through SL). profit-monster-trail avg +3.62% (working but not enough).
3. **Signal starvation** — 5/5 positions full, no new entries. System relies entirely on bb-bounce-v2-long+ (92.9% WR).

### Fix Applied
1. **PM_TRAIL_DISTANCE_PCT 0.50%→0.60%** (hermes_constants.py:1110). Lets winners run further before trailing. Expected: avg_win $0.1026→$0.12+, R:R 0.61→0.75+.
2. **neutral_sniper RSI 40/60→45/55** (neutral_sniper.py:50-55). Verified: 58% of tokens now hit RSI extremes (vs ~10% before). After CMF+ATR filters, expect 2-5 signals per cycle. Tested: ACE LONG (RSI=23, conf=73), ALT LONG (RSI=39.4, conf=73), AR SHORT (RSI=57.2, conf=68).

### Verification
- R:R target 0.80+ — needs 20+ new trades post-fix (currently 63 trades in 48h window)
- neutral_sniper signals — pipeline should produce signals within 1 cycle (tested OK)
- 3 consecutive green days (Sep 4 -$1.75, Sep 5 +$0.47, Sep 6 +$0.51 in progress)

---

## CEO Report — 2026-09-06 ~07:00 UTC

### Diagnosis
System profitable 24h (+$0.39, 58.8% WR, 34T). R:R 48h: 0.60 (avg_win $0.1003 vs avg_loss $0.1678) — still underwater. bb-bounce-v2-long+ STAR (90.9% WR 24h, 80.9% WR 7d +$2.24). coil-spring+ DEGRADED (60%→44.4% WR, -$0.21/24h). open-skies+ DEGRADED (63.6%→50% WR, -$0.19/24h). neutral_sniper LIVE but 0 signals in 4h — RSI thresholds too tight for NEUTRAL market. 5/5 positions full. 2 consecutive green days (Sep 5 +$0.47, Sep 6 +$0.20).

### Root Cause
neutral_sniper RSI thresholds (35/65) required actual oversold/overbought conditions. In 100% NEUTRAL market, RSI stays 45-55 — thresholds never triggered. coil-spring+ and open-skies+ degradation likely from same flat-market RSI compression.

### Fix Applied
Widened neutral_sniper RSI: LONG 35→40, SHORT 65→60 (neutral_sniper.py:50-51). Expected: signals fire within hours in flat market. No other parameter changes — monitoring coil-spring+ and open-skies+ before tuning.

### Verification
Pending — need to check signal log after next pipeline cycle for neutral_sniper signals. R:R at 0.60 (48h) still needs more time to reach 0.80+ target.

---

## CEO Report — 2026-09-06 ~02:35 UTC

### Diagnosis
System profitable 24h (+$0.64, 63.6% WR). R:R improving — 24h ratio 0.67 (up from 0.57 48h). bb-bounce-v2-long+ STAR (90.9% WR 24h). coil-spring+ emerging (60% WR). open-skies+ degraded (70%→63.6%). SHORT side has ZERO active backbone — all SHORT signals dead/killed/bleeding. neutral_sniper was in shadow mode since Sep 5 with 3756 signals but zero live trades.

### Root Cause
1. **SHORT starvation** — ema300-dip-short killed, accel-300-v2-short dead, macd-div- CEO-protected bleeding. System 100% LONG-dependent.
2. **R:R still underwater** — 48h ratio 0.57. PM_TRAIL distance widening (0.40→0.50%) improving to 0.67 in 24h. Needs more time.
3. **open-skies+ degradation** — WR dropped from 70% to 63.6% as trade count increased (5→11). Regression to mean.

### Fix Applied
1. **NEUTRAL_SNIPER FLIPPED LIVE** — SHADOW_MODE=False. First SHORT backbone for NEUTRAL regime. RSI+CMF+ATR mean-reversion. 3756 shadow signals in 11h confirms signal fires consistently. System finally has SHORT exposure in flat markets.
2. **signal_regime_memory.json updated** — fresh snapshots for bb-bounce-v2-long+ (46T/80.4%WR), open-skies+ (11T/63.6%WR), coil-spring+ (5T/60%WR), neutral_sniper (0T live).

### Verification
- 24h: 33T, 63.6% WR, +$0.64 ✅ (verified DB)
- 7d: 366T, 54.4% WR, -$4.16 (verified DB)
- R:R 24h: 0.67 (improving from 0.57)
- bb-bounce-v2-long+: 46T/7d 80.4% WR +$1.92 ★
- neutral_sniper: LIVE, 0 trades, monitor 48h
- Disk: 82%
- Pipeline: healthy

### Next Steps
1. Monitor neutral_sniper 48h — need 20+ live trades with WR >55%
2. Verify R:R reaches 0.80+ as PM_TRAIL distance fix matures
3. Build directional cap (65%) — awaiting T approval
4. Monitor open-skies+ degradation

---

## CEO Report — 2026-09-05 ~17:00 UTC — Position Replacement Engine Review

### Verdict: **DEFER**

### Why Not Build

**Three reasons to defer:**

**1. R:R is broken — fixing the engine beats swapping positions.**
Current R:R ratio 0.73 (avg_win $0.111 vs avg_loss $0.152). The replacement engine *compares* R:R but doesn't *fix* it. Swapping a 0.5 R:R position for a 0.75 R:R position still loses money — just slower. The PM_TRAIL_DISTANCE_PCT widening (0.40→0.50%) deployed today needs 20+ trades to verify. If R:R reaches 0.80+, the system becomes profitable without any replacement logic.

**2. Signal starvation makes replacement irrelevant.**
System has 1 profitable backbone (bb-bounce-v2-long+, 80% WR). Replacement requires *multiple* strong signals competing for capital. Right now, if bb-bounce fires, it's the only good option — there's nothing better to swap in. Build the SHORT backbone first, then replacement has something to compare.

**3. Fee drag + complexity vs. marginal alpha.**
At 0.06% round-trip, 2 swaps/hour = 0.12%/hour in fees. In a system making +$0.019/trade, that's 6+ trades of profit eaten per hour of churning. The complexity of integrating with position_manager, cut_loser, btc_crash_filter, AND trailing stops — for a system that's barely positive — is backwards.

### Open Questions — CEO Answers

| # | Question | Answer |
|---|----------|--------|
| 1 | Same-direction swaps? | **No.** Replace LONG YGG with LONG SOL = fees for marginal improvement. Only allow cross-direction swaps (LONG→SHORT or SHORT→LONG) when R:R improvement > 2x. |
| 2 | Track R:R decline over time? | **No, premature.** Track it only after the replacement engine is live. Add `rr_history` field but don't use it for decisions yet — adds complexity for zero proven benefit. |
| 3 | Trailing stop interaction? | **Close at current price, not trail floor.** The trail floor is already a "last resort" exit. If we're replacing, we want the *current* R:R, not the floor R:R. |
| 4 | Right replacement multiplier? | **1.5x is wrong.** Use 2.0x (100% better). At 1.5x, a 0.5 R:R position gets replaced by a 0.75 R:R — still losing. At 2.0x, 0.5→1.0 is breakeven, 0.5→1.5+ is actually profitable. |

### What to Build Instead (Priority Order)

1. **Directional Cap (65%)** — highest-impact mechanical fix, prevents regime-transition bleed
2. **SHORT backbone signal** — system 100% LONG-dependent, SHORT has 0 active signals
3. **Verify PM_TRAIL fix** — 31 trades at old distance, need 20+ at new 0.50%
4. **Then** build replacement engine — by then we'll have 2+ backbones, working R:R, and data to prove the concept

### Biggest Risks of Building Now

- **Complexity trap.** Integration with position_manager (3339 lines), cut_loser, btc_crash_filter, AND trailing stops = 4+ integration points to test and maintain. A bug in the swap logic = closed position + failed re-entry = lost capital.
- **Premature optimization.** The system isn't profitable enough to benefit from position selection. Fix R:R and add signals first.
- **Churning in flat markets.** In NEUTRAL regime (current), R:R estimates are unreliable. Swapping based on noisy R:R = random churn = fee bleed.

---

## CEO Report — 2026-09-05 ~16:00 UTC

### Diagnosis

**84% LONG concentration is the vulnerability.** When the tide turns, all positions bleed simultaneously. Existing protections (Directional Outcome, Weather Vane, LONG_NEUTRAL_BLOCK) are all REACTIVE — they fire after damage starts. The 4-phase cycle (LONG dominance → breakdown → oscillation → SHORT dominance) means the system always bleeds during transitions.

### Verified Numbers (DB)
- **7d:** 362 trades, 55.5% WR, -$3.95
- **LONG:** 265T, 57.4% WR, -$1.62
- **SHORT:** 97T, 47.4% WR, -$2.33
- **Today (Sep 5):** LONG 27T 77.8% WR +$1.55 | SHORT 5T 0% WR -$0.74
- **Open positions:** 4 LONG, 1 SHORT (80% LONG)

### Root Cause

The system loads up on the winning direction. LONG works → more LONG signals fire → more LONG positions open → 84% concentration. When regime shifts, ALL LONG positions bleed at once. No mechanical cap exists — only reactive penalties that fire too late.

### Strategic Recommendation: DIRECTIONAL CAP (highest-impact single change)

**Build a DIRECTIONAL CAP — max 65% of open positions in one direction.**

**Why 65% (not 60%):**
- Current LONG is 80% (4/5 open). 60% would have blocked 2 recent winners.
- 65% = 2 out of 3 positions max in one direction. Still allows conviction but prevents monoculture.
- When you hit the cap, you can only open the OTHER direction (or wait for closes).

**Implementation (lazy version):**
```python
# hermes_constants.py
DIRECTIONAL_CAP_ENABLED = True
DIRECTIONAL_CAP_MAX_PCT = 65  # max % of open positions in one direction

# position_manager.py — enforce_max_positions() or new function
def enforce_directional_cap(direction: str) -> bool:
    """Return True if opening this direction won't exceed cap."""
    if not DIRECTIONAL_CAP_ENABLED:
        return True
    long_count = count_open_positions('LONG')
    short_count = count_open_positions('SHORT')
    total = long_count + short_count
    if total == 0:
        return True
    if direction.upper() == 'LONG':
        return (long_count / total) * 100 < DIRECTIONAL_CAP_MAX_PCT
    else:
        return (short_count / total) * 100 < DIRECTIONAL_CAP_MAX_PCT
```

**Why this beats the alternatives:**

| Option | Verdict |
|--------|---------|
| Directional Cap (65%) | **BUILD THIS.** Simple, mechanical, prevents monoculture. Enforced at open time. |
| Regime-adaptive signals | Complex, requires accurate regime detection (currently unreliable). Future work. |
| Transition detection | Reactive by nature. Can't predict when tide turns. |
| Harder LONG_NEUTRAL_BLOCK | Already deployed. Doesn't prevent concentration during LONG_BIAS. |

### What This Prevents

1. **Regime transition bleed:** When LONG stops working, system can't have 80% LONG exposure.
2. **Simultaneous drawdown:** Cap limits how many positions can bleed at once in the same direction.
3. **Opportunity forcing:** When LONG is capped, the system MUST look for SHORT setups — building the SHORT backbone the system currently lacks.

### Execution

1. **Add `DIRECTIONAL_CAP_ENABLED` and `DIRECTIONAL_CAP_MAX_PCT` to hermes_constants.py**
2. **Add `enforce_directional_cap()` to position_manager.py**
3. **Call from signal_compactor.py before executing any trade**
4. **Log when cap blocks a trade** — so we can measure impact

**Expected impact:** Reduces maximum simultaneous directional exposure from ~80% to 65%. During regime transitions, limits giveback by 15-20%. Forces diversification into SHORT signals.

### Also: SHORT Backbone is CRITICAL

The cap alone won't fix the SHORT side. SHORT has 0% WR today, no active backbone signal. **Delegate to signal_analyst: build a SHORT backbone signal.** The cap creates the NEED for SHORT signals; we need to build the SUPPLY.

### Next Actions

1. **BUILD directional cap** — highest-impact mechanical fix
2. **DELEGATE SHORT signal build** — system 100% LONG-dependent
3. **Monitor PM_TRAIL_DISTANCE_PCT** — 31 trades at old distance, need 20+ at 0.50%
4. **Monitor neutral_sniper** — shadow mode, 5 SHORT signals in test

---

## CEO Report — 2026-09-06 ~Spike Filter Decision

### Decision: **GO (with modification)**

### Problem
Spike filter blocks LONG when any 5m candle has >0.3% bearish move. Catches minor pullbacks during strong rallies. 563 LONG signals blocked in 24h.

### Data
- open-skies+: 11 trades, 63.6% WR, +$0.36 — **profitable, wrongly blocked**
- coil-spring+: 3 trades, 33.3% WR, -$0.07 — **neutral**
- pump-chain+: 0 trades — **new signal**

### Fix (Modified from Proposal)

**Original proposal:**
1. Raise threshold 0.3% → 0.5%
2. Exempt momentum signals entirely
3. Add trend filter: price > EMA20 → +50% threshold

**CEO modification:**
1. **Raise threshold 0.3% → 0.5%** — conservative, not reckless
2. **Exempt momentum signals ONLY when trend filter confirms** (price > EMA20)
   - Full exemption removes safety check in downtrends where pullbacks ARE danger
   - Conditional exemption keeps safety in downtrends, freedom in uptrends
3. **Trend filter: price > EMA20 → threshold 0.75%** (0.5% × 1.5)

### Why GO
- 563 blocked trades = massive opportunity cost
- open-skies+ has 63.6% WR and is profitable — blocking it is counterproductive
- 0.3% threshold conflates healthy pullbacks with reversal signals
- Trend filter is the key piece — pullbacks in uptrends are buying opportunities, not danger

### Why Modified
- **Full momentum exemption is dangerous.** In downtrends, momentum signals still need spike protection. Conditional exemption (only when price > EMA20) keeps safety where it matters.

### Expected Impact
- Reclaims ~400+ blocked LONG trades per day (estimated 70% of 563)
- Improves open-skies+ execution (currently 63.6% WR, should improve with less blocking)
- Maintains protection in downtrends via trend filter

### Verification
- Log spike_filter blocks for 48h post-change
- Compare blocked vs executed signals
- Track if reclaimed trades improve or worsen WR
- Monitor if false positives decrease

### Action Required
Implement in spike filter logic. No delegation needed — this is a param change + conditional logic.
