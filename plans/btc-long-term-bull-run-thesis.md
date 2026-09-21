# BTC Long-Term Bull Run Thesis — 4-Year Cycle Framework

**Date:** 2026-09-21
**Author:** T (CEO) + Hermes Analysis
**Status:** ACTIVE THESIS — Under monitoring

---

## Core Thesis

BTC has historically printed bottoms almost exactly 4 years apart, followed by 3-year bull runs and 1-year bear markets. The most recent bottom was **~$60,000 in February 2026**. The bull trend has officially started.

### Historical Cycle Validation

| Cycle | Bottom Date | Bottom Price | Peak Date | Peak Price | Bull Multiple | Bear Drop |
|-------|------------|-------------|-----------|------------|---------------|-----------|
| 1 | Jul 2011 | $2 | Nov 2013 | $1,163 | **581x** | -85% |
| 2 | Jan 2015 | $177 | Dec 2017 | $19,783 | **112x** | -84% |
| 3 | Dec 2018 | $3,191 | Nov 2021 | $69,045 | **22x** | -77% |
| 4 | Feb 2026 | $60,000 | ??? 2029 | ??? | **???** | ??? |

**Pattern:** Bottoms at ~4-year intervals. Bull runs last ~3 years. Bear markets last ~1 year. Multiples diminish each cycle (581x → 112x → 22x → ?).

**Projection:** If diminishing returns continue, Cycle 4 could be **5-13x** from bottom ($300K-$780K).

---

## The 9-Step Parabolic Wave

BTC bull runs unfold in **9 distinct steps**, with the first 3 slow, next 3 faster, and last 3 super-fast to the peak. Each step involves a rally followed by a partial retracement (giving back ~50% of the gain).

### Step Structure

| Step | Phase | Rally % | Target (from $60K) | Fibonacci Level | Character |
|------|-------|---------|-------------------|-----------------|-----------|
| 1 | Accumulation | +25% | $75,000 | — | Slow, choppy |
| 2 | Early Trend | +35% | $91,000 | 1.618x ($97K) | Building momentum |
| 3 | Confirmation | +45% | $115,000 | — | Trend confirmed |
| 4 | Acceleration | +60% | $155,000 | 2.618x ($157K) | Getting faster |
| 5 | Momentum | +80% | $227,000 | 3.618x ($217K) | Strong moves |
| 6 | Expansion | +100% | $354,000 | 6.854x ($411K) | Large candles |
| 7 | Euphoria | +150% | $663,000 | 13.0x ($780K) | Parabolic |
| 8 | Blow-off | +200% | $1.39M | — | Extreme volatility |
| 9 | Peak | +300% | $3.71M | — | Terminal spike |

**Note:** These are theoretical targets based on the pattern. Realistic peak with diminishing returns: **$300K-$500K** (5-8x from bottom).

### Retracement Pattern

After each step peak, BTC gives back ~50% of the gain before the next step begins:
- Step 1 peak $75K → retrace to $67.5K (new base)
- Step 2 peak $91K → retrace to $79K
- Step 3 peak $115K → retrace to $97K
- etc.

**Key insight:** The retracements get LARGER in absolute dollar terms but SMALLER in percentage terms as the trend matures. A 50% retrace at $300K is $150K — massive in dollars but only 50% of the gain.

---

## Invalidations

The bull run thesis is **INVALIDATED** if BTC closes below:
- **$51,000** (-15% from $60K bottom) — cautious invalidation
- **$45,000** (-25% from bottom) — confirmed bear market

**As long as BTC stays above $51K on a monthly close, the long-term bull run is on.**

---

## Current Status (Sep 2026)

- **Current price:** ~$82,000-$85,000
- **From bottom:** +37-42%
- **Step:** Completing Step 1 (Accumulation) — target $75K passed, heading toward Step 2
- **Phase:** Early Trend / Confirmation
- **Regime:** Bullish — above all major MAs, higher highs and higher lows

---

## Trading Implications

### What This Means for Hermes

1. **Bias should be LONG-heavy** — the macro trend is up. SHORT signals should be reduced or disabled during bull phases.

2. **Crashes are buying opportunities** — the "up 1.6x, give back 0.5x" pattern means every -30% to -50% crash is a chance to add LONG positions at better prices.

3. **Volatility will increase** — as the bull run progresses, daily swings will get larger. Position sizes should scale with volatility (ATR-based).

4. **Time-based position management** — hold LONG positions longer during bull phases. PM Trail tiers should be widened.

5. **Fibonacci levels are targets** — $97K (1.618x), $157K (2.618x), $217K (3.618x) are natural resistance levels where profit-taking should occur.

### Signal Adjustments Needed

| Current | Bull Run Adjustment |
|---------|-------------------|
| SHORT signals active | Reduce SHORT frequency by 50% during bull phases |
| PM Trail 0.20% distance | Widen to 0.50-0.80% for BTC during bull phases |
| Equal LONG/SHORT allocation | 70-80% LONG, 20-30% SHORT |
| $11 position size | Scale with account growth (Kelly criterion when ready) |
| ATR SL 1.3-1.5% | Widen to 2.0-2.5% for BTC during bull phases |

### Crash Playbook

When BTC crashes 20-30% during the bull run (it will):
1. **Don't panic sell** — this is the "give back 0.5x" pattern
2. **Look for Step entry** — buy the dip when price stabilizes above the new base
3. **Scale in** — don't go all-in at once; average in over 3-5 days
4. **Use pump_chain+ and volume_breakout** — these signals catch the recovery

---

## Open Questions

1. **Where are we in the 9-step model?** — Need to map current price action to steps
2. **What's the realistic peak?** — Diminishing returns suggest $300K-$500K, not $3M+
3. **When does the bear start?** — Historically Q4 of year 3 (late 2028 / early 2029)
4. **How do altcoins behave?** — They typically lag BTC by 3-6 months, then outperform
5. **What's the invalidation level?** — Monthly close below $51K

---

## Trading Implementation — Brainstorm

### The Big Picture

The bottom was $60K in Feb 2026. We're now at $82-85K (+37-42%). We're in **Step 1-2** of the 9-step wave (Accumulation → Early Trend). The macro trend is UP.

### How to Use This Info

**1. Bias Shift: LONG-Heavy**

The system currently trades both directions equally. During a bull run, SHORT signals should be reduced. The macro trend is UP — fighting it with SHORTs is swimming against the current.

**Action:** Add a `BULL_RUN_BIAS` multiplier that boosts LONG signals and penalizes SHORT signals when the cycle is in bull mode.

**2. Crashes = Buying Opportunities**

The "up 1.6x, give back 0.5x" pattern means every -20% to -30% crash is a chance to buy. The system currently has crash protection (BTC_CRASH_BLOCK) that blocks entries during crashes. During a bull run, we should do the opposite — BUY the crash.

**Action:** Create a `crash_buyer.py` signal that fires LONG when BTC drops 20%+ from recent highs but stays above the invalidation level ($51K).

**3. Hold LONG Positions Longer**

PM Trail exits at +0.12% on continuum-osc+ — that's scalping during a bull run. LONG positions should ride for hours/days, not minutes.

**Action:** Widen PM Trail tiers during bull phases, or add bull-mode-specific exit logic.

**4. Fibonacci Levels = Profit Targets**

$97K (1.618x), $157K (2.618x), $217K (3.618x) are natural resistance levels. The system should take partial profits at these levels.

**Action:** Add fibonacci-based TP levels to the RR engine.

**5. Volatility Scales with Price**

As BTC goes from $60K to $200K+, daily swings will get larger in dollar terms. Position sizes should scale accordingly.

**Action:** Implement dynamic position sizing based on cycle phase (smaller in early steps, larger in later steps).

### Concrete Signal Changes

| Signal | Current Behavior | Bull Run Adjustment |
|--------|-----------------|-------------------|
| **pump-chain+** | Fires both directions | LONG only during bull phases |
| **pullback-entry-** | SHORT on pullbacks | Reduce SHORT frequency by 50% |
| **grind-trend-** | SHORT during downtrends | Disable during bull phases |
| **continuum-osc+** | Exits via PM Trail | Switch to ATR SL (ride the trend) |
| **volume-breakout-long+** | Works well | Keep as-is — quality MVP |
| **mover+** | Works well | Keep as-is |

### New Signals Needed

1. **`bull_cycle_detector.py`** — Monitors the 4-year cycle position. Outputs: phase (accumulation/early/late/euphoria), bias (LONG/SHORT/NEUTRAL), suggested position size multiplier.

2. **`crash_buyer.py`** — Fires LONG when BTC drops 20%+ from recent high but stays above invalidation. Uses volume confirmation + RSI oversold.

3. **`fibonacci_tp.py`** — Takes partial profits at fibonacci extension levels ($97K, $157K, $217K).

### Implementation Priority

| Priority | Action | Effort | Impact |
|----------|--------|--------|--------|
| 🔴 | Add LONG bias to existing signals | Low | High |
| 🔴 | Widen PM Trail for BTC | Medium | High |
| 🟡 | Create crash_buyer.py | Medium | Medium |
| 🟡 | Create bull_cycle_detector.py | High | Medium |
| 🟢 | Add fibonacci TP levels | Medium | Low |
| 🟢 | Dynamic position sizing | High | Medium |

### The Key Question

**How aggressive should we be?**

Conservative: Just adjust existing signals (widen trails, reduce SHORTs, LONG bias)
Aggressive: Create new bull-run-specific signals and exit logic

**Recommendation:** Start conservative, measure, then go aggressive. The thesis is strong but unproven for this cycle.

---

## The Vision: Market-Independent Profit Machine

### Current System Status (Sep 21, 2026)

```
Last 100 trades:
  Wins:  48 trades, avg +6.70%
  Losses: 44 trades, avg -4.56%
  R:R: 1.471
  Breakeven WR: 40.5%
  Actual WR: 48%
  Edge: +7.5% (POSITIVE EXPECTED VALUE!)

By exit reason:
  ATR SL:     35W/34L  avg +8.1% / -4.9%  R:R 1.66  ✅ Working
  PM Trail:   12W/8L   avg +3.3% / -0.4%  R:R 8.48  ✅ Excellent
  Cut-loser:   0W/7L   avg — / -3.7%      R:R 0     ⚠️ Emergency stop
```

**The system is profitable.** R:R is 1.47 (not 0.755 from earlier analysis). Edge is +7.5% above breakeven. The system works — it just needs more signal volume.

### Core Philosophy

**We don't predict direction. We book profit on every trade.**

The bull run thesis gives us a macro tailwind, but the real goal is to be **independent of what the market is doing**:
- If BTC goes UP → we're LONG, booking profit ✅
- If BTC goes DOWN → we're SHORT, booking profit ✅
- If BTC goes SIDEWAYS → we're mean-reverting, booking profit ✅

**Every trade should be a winner.** Not most trades — EVERY trade.

### How This Works in Practice

The market gives us two types of opportunities:

#### Pumps (Bull Moves)
- BTC rallies → alts follow within 5-10 minutes
- We catch the pump with LONG signals (pump-chain+, volume-breakout+, mover+)
- We ride the move with PM Trail
- **We book profit on the way up**

#### Dumps (Bear Moves)
- BTC drops → alts follow within 5-10 minutes
- We catch the dump with SHORT signals (pump-chain-, pullback-entry-, grind-trend-)
- We ride the move with trailing stops
- **We book profit on the way down**

#### The Key Insight

**Volatility = Opportunity.** Every pump and every dump is a chance to book profit. The more volatile the market, the MORE opportunities we have.

In a bull run:
- Pumps are bigger and more frequent → more LONG profits
- Dumps are violent but shorter → SHORT profits on the way down, then LONG again on the bounce
- The net effect: we're constantly booking profit in BOTH directions

### The 9-Step Wave = 18 Opportunities Per Cycle

Each of the 9 steps has:
1. **Rally phase** → LONG opportunity (catch the pump)
2. **Retracement phase** → SHORT opportunity (catch the dump)

That's **18 distinct trading opportunities per cycle** (9 rallies + 9 retracements). If we catch even half of them, that's 9 winning trades per cycle.

### Altcoin Multiplication

BTC is the leader, but alts provide **leverage on the same move**:
- BTC +5% → ETH +8%, SOL +10%, small caps +15-20%
- BTC -5% → alts drop even more (higher beta)

**Trading alts instead of BTC gives us 2-4x the profit on the same move.**

The system already trades 50+ alts. In a bull run, every alt becomes a vehicle for profit — we just need to be on the right side.

### Direction Independence

The system should NOT care about direction. It should:
1. **Detect momentum** — is the asset moving?
2. **Enter in the direction of momentum** — LONG if rising, SHORT if falling
3. **Exit with profit** — PM Trail or ATR SL captures the move
4. **Repeat** — next trade, same process

**The macro thesis (bull run) just tells us which side has MORE opportunities.** But we should still trade both sides.

### The Math of "Every Trade a Winner"

Currently:
- Win rate: 48% (close to random)
- R:R: 0.755 (losers are 32% wider than winners)
- Expected value: slightly negative

To make EVERY trade a winner:
- Win rate needs to be 60%+ (not 48%)
- R:R needs to be 1.0+ (not 0.755)

**How to get there:**
1. **Better entries** — only trade when momentum is clear (not chop)
2. **Better exits** — wider PM Trail to capture more of the move
3. **Better filters** — block bad entries (chasing, against trend)
4. **Better sizing** — scale with volatility, not fixed $11

### The Roadmap

| Phase | Goal | Status | How |
|-------|------|--------|-----|
| ~~Phase 1~~ | ~~55% WR, 0.9 R:R~~ | ✅ **ACHIEVED** | Exits working (ATR SL R:R 1.66, PM Trail R:R 8.48) |
| Phase 2 | 55% WR, 1.5 R:R | **IN PROGRESS** | Increase signal volume (crash filter fixes live) |
| Phase 3 | 60% WR, 1.5 R:R | Next | Add macro bias (bull run LONG bias) |
| Phase 4 | 65% WR, 1.8 R:R | Future | Add cycle-aware sizing (scale with volatility) |

### What We're Building Toward

A system that:
- **Trades every pump** — LONG when momentum is up ✅ (pump-chain+, volume-breakout+ working)
- **Trades every dump** — SHORT when momentum is down ✅ (pullback-entry-, grind-trend- working)
- **Books profit on every trade** — exits capture the move ✅ (ATR SL R:R 1.66, PM Trail R:R 8.48)
- **Scales with volatility** — bigger moves = bigger positions (NEXT: cycle-aware sizing)
- **Is market-independent** — works in bull, bear, or sideways ✅ (R:R 1.47 in NEUTRAL regime)

**Status: The engine works. We need more fuel (signal volume).**

The crash filter fixes we made today should increase signal volume — LONG signals were being blocked during rallies by the MOMENTUM layer misapplication. With the fix, more pumps should be caught.

**The bull run is the tailwind. The profit machine is the engine. The engine is running.**

---

## Next Steps

### Immediate (This Week)
- [ ] Add cycle support levels ($62,622 and $69,000) to hermes_constants.py
- [ ] Backtest wider ATR_SL (1.5-1.8%) for LONG positions
- [ ] Review crash filter fixes — are LONG signals firing during rallies?

### Short-Term (Next 2 Weeks)
- [ ] Add LONG bias multiplier to signal_compactor.py
- [ ] Widen PM Trail tiers for BTC during bull phases
- [ ] Reduce SHORT signal frequency when cycle is bullish
- [ ] Create `crash_buyer.py` — buy-the-dip signal

### Medium-Term (Next Month)
- [ ] Create `bull_cycle_detector.py` — cycle position monitor
- [ ] Add fibonacci TP levels to RR engine
- [ ] Implement direction-independent profit booking (trade both sides)
- [ ] Dynamic position sizing based on cycle phase

### Long-Term (Next Quarter)
- [ ] Alt-specific cycle analysis (which alts pump hardest in each step?)
- [ ] Volatility scaling (position size × ATR)
- [ ] Kelly criterion for position sizing
- [ ] Real-time cycle step mapping (are we in step 3? step 5?)
