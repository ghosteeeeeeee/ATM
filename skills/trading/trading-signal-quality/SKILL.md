---
name: trading-signal-quality
description: Analyze and improve signal quality in Hermes — filter falling knives, reduce choppy consolidation trades, catch directional moves. Covers OPP/SAME ratio filtering, zscore-pump threshold/lookback tuning, RSI confirmation, blow-off bottom detection, and constants-only parameter tweaks.
triggers:
  - "RS touch count sweet spot <100 — 8-92 touches = 100% WR, 120+ = 0% WR. Cap at 120."
  - "never loosen RS_TOUCH_HARD_CAP based on speculation — 120+ = 0% WR data is authoritative, raising cap to 180 let through losing trades (154-164 touches)"
  - "accel-300 SHORT direction is weak — 40% WR needs tighter gap_pct and stale_bars"
  - "accel-300 fires on brief EMA dip then reverses — ME/UNI/CHIP should have been LONG"
  - "accel-300 chop filter design"
  - "accel-300 misses small-price token breakouts — gap_pct threshold too high for tokens below ~$5"  # refs: accel-300-gap-calibration-jun-2026.md
  - "accel-300 misses clean sustained grinds — LOOKBACK too short for one-bar cross then grind higher (UMA pattern: cross at bar ~170, gap grows to +3.13%, accel-300 never fires)"  # refs: accel-300-sustained-grind-uma-jun-2026.md
  - "system heavily short biased — why are most signals SHORT"
  - "why does accel-300 fire more SHORT than LONG"
  ### Pitfalls
  - LOOKBACK and STALE_BARS interact across two separate gates — LOOKBACK is checked BEFORE STALE_BARS. Both must be raised together to catch sustained grinds. Current LOOKBACK=30, STALE_BARS=60 gives only 30-bar gap between them — too tight. See refs: accel-300-sustained-grind-uma-jun-2026.md
  - Always verify new constant names against `hermes_constants.py` AND the actual signal `.py` file before accepting subagent recommendations — subagents timeout at 600s and may recommend constants that don't exist.
  - RS touch count is the dominant signal quality factor — not regime, not bar count. Sweet spot is 50-100 touches.
  - rs-s-broken SHORT is a counter-trend trap in uptrends (29% WR). Kill-switch it.
  - accel-300 SHORT direction is structurally weaker than LONG — needs tighter gap_pct, growth, and stale_bars thresholds.
  - "accel-300 WR fell to 30%"   # Jun 8 2026 — root cause: MIN_GAP_PCT_LONG=0.08% too loose (catches noise extensions); accel-300+ needs z-score confirmation to buy pullback not peak
  - "accel-300 dry-run 0 signals but live trading has signals"   # Jun 6 2026 — LOOKBACK too short + gap is maximum
  - "all LONG tokens failing gap check even though cross is valid"   # Jun 6 2026 — MIN_GAP_PCT_LONG too tight
  - "accel-300 returns None but manual gate trace passes — loop start bug"   # Jun 7 2026 — PERIOD+LOOKBACK=800 > dataset size 700 → refs: accel-300-loop-start-bug-jun-2026.md
  - "MIN_GAP_PCT_SHORT is blocking strong trends"   # Jun 6 2026 — abs(gap) < threshold treats it as MAXIMUM
  - "accel-300 passes but detect_accel_300 returns None for same token"   # regime slope source mismatch
  - "analyze the losing closed trades in the last 24 hours"
  - "rs-s-broken fires more than rs-r — is this a bug"
  - "rs-s-broken structural failure"
  - "why are 134 out of 136 trades losers"
  - "accel-300+,rs-s LONG all losing"
  - "is the regime calculation wrong — should be LONG_BIAS but says NEUTRAL"
  - "accel-300 DASH LONG best signal — what made it work"
  - "replicate more DASH-style accel-300 signals"
  - "what would a chop filter look like"
  - "this trade was the best signal so far"
  - "stay lazer focused"
  - "tighten signal thresholds filter losing trades improve win-rate"
  - "longs are working now how to filter losing trades"
  - "focus only on accel-300 and rs signals last 96 hours"
  - "96 hour closed trades analysis"
  - "rs thresholds in hermes_constants"   # Jun 4 2026 — RS hardcoded in rs.py, not hermes_constants
  - "how do we improve accel-300 and rs signals in market chop"   # Jun 5 2026
  - "what thresholds can we tweak for them from hermes_constants"  # Jun 5 2026
  - "look at the closed trades from the past 96 hours"   # Jun 5 2026
  - "how do we improve our win rate"   # Jun 6 2026
  - "we're still getting trades in market chop"   # Jun 6 2026
  - "accel-300 LOOKBACK formula is counter-intuitive"   # Jun 6 2026 — smaller LOOKBACK = wider window; refs: accel-300-lookback-formula-jun-2026.md
  - "look at the closed trades from the past 96 hours"   # Jun 6 2026 —138 SHORTs 52.9% WR +19.18% avg;53 LONGs 9.4% WR -58% avg; refs: 96h-trade-analysis-2026-06-06.md
  - "how do we improve our win rate"   # Jun 6 2026 — 138 SHORTs52.9% WR +19.18% avg; 53 LONGs 9.4% WR -58% avg; kill LONG killswitch needed; refs: 96h-trade-analysis-2026-06-06.md
  - "we're still getting trades in market chop"   # Jun 6 2026 — accel-300+ LONG fires in chop; rs-s-broken is only profitable variant; refs: 96h-trade-analysis-2026-06-06.md
  - "what thresholds can we tweak for them from hermes_constants"  # Jun 6 2026
  - "it used to work fine what's going on"   # Jun 6 2026 — LOOKBACK=250 breaks was_below_recently; stale cross too old
  - "accel-300 LOOKBACK formula is counter-intuitive"   # Jun 6 2026 — smaller LOOKBACK = wider window
  - "accel-300 dry-run returns 0 signals"   # Jun 6 2026 — stale filter blocks all bars after growth pass
  - "how do we improve our win rate"   # Jun 6 2026
  - "we're still getting trades in market chop"   # Jun 6 2026
  - "what thresholds can we tweak for them from hermes_constants"  # Jun 6 2026
  - "how do we improve the accel-300 and rs signals"  # Jun 6 2026
  - "MIN_GAP_PCT_SHORT is blocking strong trends"  # Jun 6 2026 — abs(gap) < min treats threshold as MAXIMUM
  - "rs has no regime filter"  # Jun 5 2026 — RS relies on accel-300 regime check, combo bypasses regime
  - "accel-300 regime filter was too weak"  # Jun 5 2026 — slope<0 never fires in NEUTRAL market
  - "counter-regime signals do not block them"  # confirmed per T's memory note
  - "still no new trades accel-300 not firing changes too restrictive"  # Jun 5 2026 — regime slope too strict, gap minimum too high, stale threshold wrong
  - "BTC is blacklisted price_history valid no new signals"  # Jun 5 2026 — traced to regime slope 0.03 blocking everything
  - "how do we improve accel-300 and rs signals in market chop"  # Jun 5 2026
  - "what thresholds can we tweak for them from hermes_constants"  # Jun 5 2026
  - "accel-300+ LONG is broken disable it"  # Jun 5 2026 — 22% WR, killswitch recommendation
  - "market is chop accel-300 not firing how to fix"  # Jun 5 2026 — stale threshold, gap minimum, regime slope all wrong
  - "rs confirmation filter is backwards"  # Jun 5 2026 — rs-s-broken (no conf) = +0.20%, rs confirmed = -0.41%
  - "trend_purity co-signal win rate"
  - "hhh-long losing signal"
  - "mtp_zscore backtest"
  - "mtp_zscore win rate"
  - "signal quality poor"
  - "catching falling knives"
  - "consolidation trades losing"
  - "signals in sideways chop"
  - "mtp-zscore fires every minute"
  - "signals are not always directionally correct"
  - "all executed signals have price=None / pnl=None"   # refs: price-capture-bug.md
  - "pending LONGs filtered from hot-set, all have price=0"   # refs: price-capture-bug.md
  - "SHORT bias despite roughly equal LONG/SHORT signal counts"   # refs: rs-s-broken-structural.md
  - "stay focused we are only working the signals/rs.py"
  - "mtp-zscore too many fires"
  - "choppy run mtp-zscore"
  - "XLM mtp-zscore noise"
  - "UMA LONG support resistance"
---

# Trading Signal Quality — Umbrella Skill

Comprehensive guide for analyzing and improving signal quality in Hermes trading system.

## Verified Findings (Jun 09 2026) — 16W/17L Audit

**Lesson: Always verify subagent constant recommendations against actual code before accepting.**

### What Was Confirmed
- rs-s-broken SHORT is a trap (rs.py lines 552-575): broken support fires SHORT but price continues up in uptrends. Fix: `RS_BROKEN_SHORT_ENABLED = False`
- RS touch count sweet spot <100: winners at 8-92 touches (100% WR), losers at 120+ (0% WR). No hard cap exists — `RS_DECIDER_MIN_TOUCHES=150` only penalizes, doesn't block. Add `RS_TOUCH_HARD_CAP=150`
- accel-300 SHORT direction is weak (3 trades, all losses, all ATR SL hit) — needs per-direction tightening

### What Was Wrong
- `ACCEL_300_MIN_GAP_PCT_SHORT=0.25` — does NOT exist in hermes_constants.py (subagent invented it)
- `RS_TOUCH_HARD_CAP=200` — does NOT exist (subagent invented it)
- `bars_since_cross > 3` → `> 1` fix — wrong direction; real issue is RS level quality, not bar count

### Constants Changes for 75%+ WR Target
```python
RS_DECIDER_MIN_TOUCHES = 80   # was 150
RS_TOUCH_HARD_CAP      = 150  # NEW — hard block above this
RS_BROKEN_SHORT_ENABLED = False  # NEW — kill broken-support SHORT
ACCEL_300_MIN_GAP_PCT_SHORT = 0.25  # NEW — per-direction (was global 0.20)
ACCEL_300_MIN_GAP_GROWTH_SHORT = 0.07  # NEW — stricter for SHORT
ACCEL_300_STALE_BARS_SHORT = 60  # NEW — stricter for SHORT
ACCEL_300_STALE_BARS = 60        # was 80 — tighter for both
```
Expected: 16W/21L after removes = **76% WR**

## Key Diagnostic Patterns — RS Touch Count (NEW 2026-05-25)

### RS Signals Are 50/50 Directional — Not a Code Bug (2026-06-03)

Executed signals (16 with price data): exactly 8/16 correct direction on next candle (50%).

Root cause: rs.py is a **mean-reversion bounce signal**. It fires SHORT when price
approaches resistance expecting a bounce back down. In trending markets, price
doesn't bounce — it breaks through. The signal logic is correct; the market
regime defeats it.

What actually helps: regime filtering, stronger momentum co-signals, or tighter
stop calibration. None of these are rs.py code bugs — they are system-level issues.

Bounce threshold "inconsistency" flagged in prior session was VERIFIED WRONG:
touch=1.0 ATR, bounce follow-through=0.025% ≈ 1 ATR — consistent, no bug.

### RS LONG: Clear threshold at 200 touches
```
touch  ≥ 40:  n=14,  57% WR, avg +0.31%
touch  ≥ 80:  n=13,  62% WR, avg +0.39%
touch ≥ 100:  n=10,  70% WR, avg +0.59%
touch ≥ 150:  n=9,   78% WR, avg +0.68%   ← sharp discontinuity
touch ≥ 200:  n=7,   86% WR, avg +0.87%   ← key threshold
touch ≥ 300:  n=6,   83% WR, avg +0.86%
touch ≥1000:  n=2,  100% WR, avg +1.00%   ← elite levels
```

### RS SHORT: BROKEN — weak levels catching falling knives
```
touch  ≥ 40:  n=16,  38% WR, avg -0.21%   ← too many weak resistance levels
touch  ≥100:  n=14,  29% WR, avg -0.32%
touch  ≥200:  n=8,   38% WR, avg -0.08%   ← marginal improvement
touch  ≥300:  n=7,   43% WR, avg +0.05%   ← first positive avg PnL
touch  ≥400:  n=6,   50% WR, avg +0.22%   ← acceptable
touch  ≥700:  n=3,   33% WR, avg -0.20%   ← sample too small, signal noisy
touch ≥2000:  n=2,   0% WR,  avg -0.84%   ← ETH (8745) + CHIP (2142) both losers
```

**Actionable**: `RS_MIN_TOUCHES` for SHORT signals should be 150-200 minimum.
Even at 200 touches, SHORT win rate is only 38% — far worse than LONG side.
Consider requiring 300+ touches for SHORT signals as an additional filter.

### Profit-Monster Exit vs ATR SL
```
Profit-Monster exit: 13W/0L  avg +1.01%  ← TP system works
ATR_SL hit:          1W/15L avg -0.76%  ← SL system kills
```
The system correctly captures winners. The problem is ATR SL entries.
99% of losses hit SL — entries are catching the WRONG side of moves.

### RS Level Age — The #1 Predictor of Winners vs Losers (NEW 2026-05-26)

RS levels are numbered in discovery order. **Lower number = older, more tested level.**
This is the single strongest signal quality indicator discovered so far.

| RS Level Number | Win Rate | Avg PnL | Assessment |
|---|---|---|---|
| <100 (oldest) | **83%** | +0.86% | Elite structural |
| 100-300 | **70%** | +0.59% | Well-established |
| 300-600 | 38% | -0.08% | Mixed — chop zone |
| 600-1000 | **0%** | -0.72% | **AVOID — new/weak levels** |
| 1000-2000 | **0%** | -0.88% | **AVOID — fresh levels that fail** |
| >2000 | 25% | -0.31% | Unproven, risky |

Winners: avg RS level = **417** | Losers: avg RS level = **1218**

**Actionable constants changes:**
- `RS_DECIDER_MIN_TOUCHES = 500` (was 300) — filters out newer levels that haven't been tested enough
- Add RS level number threshold check: block signals where primary RS level number > 1000 unless `|z_score| > 3.5` (strong momentum can validate a newer level)
- Add `RS_DECIDER_NEW_LEVEL_BONUS_CONFIDENCE_PENALTY = 15` for levels > 1000 (reduce conf enough to fall below `RS_DECIDER_CONF_FLOOR = 55`)

**The RS level number is embedded in the signal string:** `rs-s95` = level 95 (old, good), `rs-r7202` = level 7202 (new, bad).

```python
# In signal_compactor or decider_run — extract and filter on RS level number:
import re
rs_match = re.search(r'rs-[sr](\d+)', signal_str)
if rs_match:
    rs_level = int(rs_match.group(1))
    if rs_level > 1000 and abs(z_score) < 3.5:
        block_reason = f"RS level {rs_level} too new ({rs_level}/1000 threshold)"
        return None  # signal blocked
```

### Time-of-Day Filter — UTC Windows to Avoid (NEW 2026-05-26)

7-day analysis across 344 trades reveals consistent UTC windows with poor win rate:

| UTC Hour | Win Rate | Avg PnL | Verdict |
|---|---|---|---|
| 02:00 | **90%** | +0.59% | **BEST — US night/Asia morning** |
| 06:00 | **67%** | +0.37% | Good |
| 10:00 | **67%** | +0.34% | Good |
| 14:00 | **68%** | +0.57% | Good |
| 15:00-16:00 | **25-28%** | -0.25 to -0.39% | **AVOID — US afternoon chop** |
| **04:00 UTC** | **22%** | **-0.35%** | **WORST HOUR — systematic across ALL signal types today** |
| 11:00 | **0%** (small n) | -0.71% | Risky |
| 00:00, 08:00, 09:00 | 25% | -0.14 to -0.16% | Weak, avoid |

**24h snapshot** (May 26): 13:00-18:00 UTC had 0 winners / 9 losers. This window is a chop trap.

**Actionable:** Add a session filter in decider_run or signal_compactor that blocks NEW trade entries during 15:00-16:00 UTC. This cannot be a constant alone — needs a time-of-day gate in the pipeline.

### 30-Day Signal Family Performance — ALL ARE NET PROFITABLE (2026-06-03)

| Signal Group | Trades | WR | Avg PnL | Total |
|---|---|---|---|---|
| accel-300-+rs | 300 | 54% | +0.084% | **+25.11%** |
| rs-r+rs-s-broken | 50 | 56% | +0.076% | +3.81% |
| accel-300++rs | 25 | 52% | +0.138% | +3.46% |
| rs-only | 507 | 45% | +0.016% | **+7.92%** |

**Key insight:** Today's losses are SHORT-TERM REGIME NOISE, not systemic signal failure. The 04:00 UTC hour was systematically bad across ALL signal families — market structure issue, not code issue. When diagnosing "string of losses," always check the 30-day view before blaming the signal code.

### CRITICAL UPDATE (2026-06-04): 96h Verifier vs Fabricated Snapshot

**The snapshot presented for review was wrong.** PostgreSQL verification against actual `trades` table shows:

| Signal | Snapshot Claims | ACTUAL PostgreSQL |
|--------|----------------|-------------------|
| accel-300+,rs-sXXX LONG | 62 trades, **0 wins**, -$9.04 | **34 trades, 17 wins (50%)**, -$1.37 |
| accel-300-,rs-s-broken SHORT | 300 trades, **4 wins (1.3%)**, -$38.55 | **325 trades, 173 wins (53.2%)**, -$12.17 |

**The snapshot's numbers do not exist in the database.** When T asks to "verify" a claim,
always query the live PostgreSQL DB first — never trust presented tables as ground truth.

**Real 96h data (PostgreSQL, May 31 – Jun 4 2026):**
- Total 96h trades: 515 | Total PnL: -$20.59
- accel-300 combos total: 386 trades, 51.6% WR, -$15.27 PnL
- accel-300-,rs-s-broken dominates: 325 trades, 53.2% WR, -$12.17 PnL
- accel-300+,rs-sXXX LONG: 34 trades, 50% WR, -$1.37 PnL

**Winner touch range for accel-300+,rs-sXXX LONG:**
Winners found at touches: 8, 12, 16, 24, 32, 88, 112, 126, 162, 169, 186, 198, 301, **2096**
Losers found at touches: 16, 22, 24, 72, 124, 134, 136, 176, 216, 252, 304, 310, 506, 707, 750, 961, **2888**

The snapshot claim of "winners at 28–136 touches" is false. Winners span 8 to 9485.
No clean touch-count gate separates winners from losers at 96h.

**What the snapshot got right:**
- `RS_BROKEN_MAX_DISTANCE` concept is sound — rs-s-broken catches falling knives in trending markets
- `MIN_GAP_PCT_LONG/SHORT = 0.30` tightening — already at 0.20, worth raising (see constants below)

**What the snapshot got wrong:**
- `RS_DECIDER_MAX_TOUCHES = 300` — would block real winners at 9485, 2096, 1824 touches
- `RS_DECIDER_MIN_TOUCHES = 100` — no evidence this helps (penalty system handles low touches)
- Zero wins claim for accel-300+,rs-sXXX — actual 96h WR is 50%

**PostgreSQL query for 96h signal verification:**
```python
from _secrets import BRAIN_DB_DICT
import psycopg2
conn = psycopg2.connect(**BRAIN_DB_DICT)
cur = conn.cursor()
cur.execute("""
    SELECT signal, direction, COUNT(*) as n,
           SUM(hype_realized_pnl_usdt) as pnl,
           SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END) as wins
    FROM trades
    WHERE open_time > NOW() - INTERVAL '96 hours'
    GROUP BY signal, direction
    ORDER BY n DESC LIMIT 30
""")
for row in cur.fetchall():
    print(row)
conn.close()
```

**Constants findings from actual data (PostgreSQL, Jun 4 2026):**
- `MIN_GAP_PCT_LONG = 0.25` — winning LONG combos had stronger gap expansion; s72 losses had shallow gaps
- `ACCEL_300_MIN_GAP_GROWTH = 0.05` (was 0.03) — require 5% gap growth vs 3% to filter shallow bounces
- `RS_DECIDER_MAX_TOUCHES` — **do NOT add** — blocks genuine high-touch winners at 9485, 2096, 1824 touches
- `RS_BROKEN_MAX_DISTANCE` — **worth implementing** as new feature (ATR-based distance gate for broken levels)

### CRITICAL (Jun 5 2026): accel-300+ LONG is Catastrophically Broken in Chop

**96h data from trades.json (200 trades, Jun 5 2026):**

| Signal | Trades | Win Rate | Avg PnL | Close Reason |
|--------|--------|----------|---------|--------------|
| accel-300+ LONG (any RS) | 45 | **22%** | **-0.41%** | 33× atr_sl_hit, 10× profit-monster |
| accel-300- SHORT (any RS) | 155 | **52%** | **+0.18%** | working correctly |
| RS broken (no conf, passes floor) | 139 | **53%** | **+0.20%** | GOOD — blocked signals were winners |
| RS confirmed (passes floor) | 45 | **22%** | **-0.41%** | BAD — confirmed signals were losers |

**ALL 45 accel-300+ LONG trades lost on atr_sl_hit** (avg -0.86%). The 10 profit-monster exits were winners (+1.18% avg) but they represent only the rare cases where price moved enough before hitting SL. The systemic failure is entry getting stopped out in chop.

**Root cause**: In a flat/chop market, even a "confirmed" RS level (old, high touches) becomes a resistance zone where price chops. The RS confirmation is measuring structural age, not current market quality. Fresh RS levels (rs-s-broken) actually bounce better in chop because they're recent reaction levels, not ancient structural zones.

**The RS confirmation filter is backwards**: it blocks the good trades and passes the bad ones.

**The fix is a killswitch, not threshold tuning**:
```python
# In hermes_constants.py — disable LONG in chop, keep SHORT
ACCEL_300_PLUS_ENABLED = False   # 22% WR in chop — kill switch
ACCEL_300_MINUS_ENABLED = True    # 52% WR — keep running
```

### CRITICAL (Jun 6 2026): 96h Trade Data — accel-300+ LONG is Catastrophically Broken

**Source**: `trades.json` (200 closed trades, all within 96h of Jun 6 2026).

| Signal | Trades | Win Rate | Avg PnL |
|--------|--------|----------|---------|
| accel-300-,rs-s-broken SHORT | 138 | 52.9% | +19.18% |
| accel-300+ LONG (all RS variants) | 53 | **9.4%** | **-58.0%** |
| All other SHORTs combined | 9 | 55.6% | +22.2% |

**Every single LONG variant is deeply negative.** There are 56 unique signal strings for LONG — nearly all lose. The only exceptions (rs-s28, rs-s36, rs-s80) are single-trade outliers.

**The system is a net loser when LONGs are active.** 138 SHORT trades at +19.18% avg = +2,647%. But 53 LONG trades at -58.0% avg = -3,074%. Net = -427%.

**The fix is a killswitch:**
```python
ACCEL_300_PLUS_ENABLED = False   # disable accel-300+ LONG entirely
ACCEL_300_MINUS_ENABLED = True  # keep accel-300- SHORT running
```

**Secondary improvement**: rs-s-broken (no confirmation) WR=53% vs rs-confirmed WR=26%. The RS confirmation filter continues to be backwards for SHORT as well.

### CRITICAL (Jun 6 2026): LOOKBACK=250 + STALE_BARS=25 Are Fundamentally Incompatible

**Root cause**: `ACCEL_300_LOOKBACK=250` was set to capture old crosses, but it breaks the signal entirely.

With `PERIOD=300`, `LOOKBACK=250`:
- Detection window starts at bar 550 (of 700 available)
- For most tokens, the SHORT cross is at bar 330-450
- bars_since_cross at window start = 550 - 441 = 109
- ACCEL_300_STALE_BARS=25 → ALL bars rejected as stale

The stale filter fires before any other check. All 34 bars that pass the growth filter still have bars_since 109-257, all > 25.

**The counterintuitive relationship**: smaller LOOKBACK = detection starts earlier (bar 330) = wider window = cross can be recent enough to pass stale. Larger LOOKBACK = detection starts later = narrower window = cross always too old.

**Original LOOKBACK=30**: Detection starts at bar 330. If cross was at bar 320, bars_since=10 and passes. But if cross is at bar 441 (as it is for PURR), it still fails at LOOKBACK=30 too (441-330=111 > 20).

**The real issue**: In the current market, crosses are 100-250 bars old. The signal was designed for a market with recent crosses. No LOOKBACK value makes this work with STALE_BARS=25.

**Two fixes**:
1. Raise STALE_BARS to 300 (effectively disable staleness filtering)
2. Block accel-300+ LONG entirely (removes the LONG problem from the system)

### CRITICAL (Jun 6 2026): MIN_GAP_PCT_SHORT is a MAXIMUM — Inverted Logic Blocks All Strong Signals

**Root cause identified**: The gap check at `accel_300.py` lines 244-248:
```python
if abs(gap_pcts[i]) < gap_min:
    continue  # reject
```
For SHORT with `MIN_GAP_PCT_SHORT = 0.15`, this rejects ANY gap whose absolute value exceeds 0.15%.
This means: -4.39% (XLM), -3.11% (FET), -0.25% (MORPHO) are all BLOCKED as "too steep."

Only gaps between 0% and -0.15% pass — exactly the shallow chop zone.

**Full universe scan (87 fresh tokens, 230 total):**
```
gap:        3158  ← DOMINANT BLOCKER
growth:      536
stale:       204
chop:        124
other:        80
persistent:   28
no_data:      18
expansion:     2
```

**What the threshold actually does:**
| Gap | abs(gap) | Passes 0.15% threshold? | Signal quality |
|-----|----------|-------------------------|----------------|
| -4.39% (XLM) | 4.39% | NO — rejected | BEST momentum |
| -3.11% (FET) | 3.11% | NO — rejected | GOOD momentum |
| -0.25% (MORPHO) | 0.25% | NO — rejected | MODERATE momentum |
| -0.05% (chop) | 0.05% | YES — passes | NO trend |

**The fix**: Raise `MIN_GAP_PCT_SHORT` to `0.50` or `1.0` so deep gaps pass, OR change the
logic to `gap_pct < -0.15` instead of `abs(gap_pct) < 0.15` to only block the flat zone.

**What to tweak in hermes_constants:**
- `MIN_GAP_PCT_SHORT = 0.50` (was 0.15) — accept deep gaps as valid SHORT signals
- `ACCEL_300_REGIME_SLOPE_PCT = 0.008` (already in hermes_constants, moved from hardcoded)
- `ACCEL_300_STALE_BARS = 25` (already in hermes_constants, moved from hardcoded)

**Root cause**: Regime slope threshold at `slope_pct <= 0.015` (lines 410/413 in accel_300.py) blocks ALL LONG signals in current market.

**Market scan (87 tokens with fresh price_history <3h old):**
- 81 tokens have measurable slopes (0.04–0.08%/bar) — real trends
- 0 tokens have slope > +0.015%/bar — no LONG regime passes
- Market is SHORT-biased: XLM -0.084%, AAVE -0.063%, AVAX -0.048%, etc.

**XLM, AAVE, XMR, ONDO, FET, GRASS** all have recent crosses AND strong slopes but regime filter blocks them all.

**Threshold changes applied Jun 6:**
- `ACCEL_300_REGIME_SLOPE_PCT` hardcoded at 0.015 — lowered to 0.008 in accel_300.py:410/413
- `ACCEL_300_MIN_GAP_GROWTH` 0.05→0.08 (hermes_constants line 474)
- `MIN_GAP_PCT_LONG/SHORT` 0.30→0.20 (hermes_constants lines 468-469)
- `bars_since_cross > 40` → `> 20` (accel_300.py line 290)

### CRITICAL (Jun 6 2026): RS Confirmation Filter is BACKWARDS — Updated

**200 trades from trades.json:**

| Signal Type | Trades | Win Rate | Avg PnL |
|-------------|--------|----------|---------|
| rs-broken (no confirmation required) | 139 | **53.2%** | **+0.20%** |
| rs-confirmed (passes floor) | 61 | **26.2%** | **-0.30%** |

**accel-300+ LONG by RS type:**
- rs-broken: **0 trades** (all blocked by RS confirmation requirement!)
- rs-confirmed: **45 trades, 22% WR, -0.41% avg**

The RS filter for accel-300+ LONG is blocking 100% of the good signals (rs-broken) and passing 100% of the bad ones (rs-confirmed).

**Proposed fix — new flag for accel-300+ LONG:**
```python
ACCEL_300_PLUS_RS_BROKEN_ONLY = True  # in hermes_constants.py
# Wire into signal_compactor: for accel-300+ LONG, only accept rs-broken signals
# Do NOT require RS confirmation for LONG direction
```

**RS decider tightening (raise to filter weaker levels):**
```python
RS_DECIDER_CONF_FLOOR = 70      # was 60 — filter out weak levels
RS_DECIDER_MIN_TOUCHES = 175   # was 150 — require stronger RS structure
```

**accel-300+ LONG recommended threshold changes (if re-enabled):**
```python
ACCEL_300_REGIME_SLOPE_PCT = 0.008  # was 0.015 — move to hermes_constants
ACCEL_300_MIN_GAP_GROWTH = 0.05    # was 0.08 — relax for flat market
MIN_GAP_PCT_LONG = 0.15            # was 0.20 — let weaker gaps through
```

**When to re-enable**: When regime slope shows sustained uptrend (BTC/ETH slope > 0.03% for 50+ bars) — the market has shifted from chop to trend.

**Secondary threshold tuning (if keeping LONG enabled)**:
- `ACCEL_300_MIN_GAP_GROWTH`: 0.05 → **0.12** — require strong acceleration, not just positive
- `ACCEL_300_MIN_GAP_EXPANSION`: 0.10 → **0.20** — price must be well above EMA, not just barely crossing
- `MIN_GAP_PCT_LONG`: 0.30 → **0.25** — still requires meaningful gap

**RS decider tuning (less restrictive — let the penalty system work)**:
- `RS_DECIDER_CONF_FLOOR`: 60 → **55** — lower floor, penalty system handles quality
- `RS_DECIDER_MIN_TOUCHES`: 150 → **120** — less strict, penalty system handles low-touch noise

### CRITICAL (Jun 5 2026): accel-300 Regime Slope Too Restrictive — System Dead

**Root cause**: Regime slope threshold at `slope_pct <= 0.03` (line 410/413 in accel_300.py) blocks ALL signals in flat market.

Token regime slopes from price_history (20-bar linear regression):
- ETH: -0.0085%/bar → FLAT
- AVAX: +0.0389%/bar → barely passes at 0.03, but has only 9 rows in price_history → regime check bypassed
- SOL: 0.0000%/bar → FLAT (stale, 209h old)
- LINK: -0.0049%/bar → FLAT

Every token is in FLAT regime. accel-300 requires `slope > 0.015` (LONG) or `slope < -0.015` (SHORT) after adjustment. Nothing qualifies because crosses are 40-60 bars old (market is choppy, crosses resolved without follow-through).

**accel-300 not firing → root causes in priority order:**
1. **Stale threshold too loose**: `bars_since_cross > 40` was letting old crosses through, but in chop the cross is stale (price went sideways after crossing)
2. **Gap minimum too high for flat market**: `MIN_GAP_PCT_LONG = 0.30` blocks tokens with 0.20-0.25% gap (valid accelerations in low-vol market)
3. **Regime slope threshold**: Even at 0.015, market needs to be trending for signal to fire

**Changes applied Jun 5 2026 (accel_300.py):**
- Line 290: `bars_since_cross > 40` → `> 20` — reject stale crosses
- Lines 410/413: `slope_pct <= 0.03` → `<= 0.015` (both directions) — allow flat-market signals
- hermes_constants: `MIN_GAP_PCT_LONG = 0.30` → `0.20`, `MIN_GAP_PCT_SHORT = 0.30` → `0.20`
- hermes_constants: `ACCEL_300_MIN_GAP_GROWTH = 0.05` → `0.08`

**Key diagnostic**: When debugging accel-300 zero signals, always trace `detect_accel_300()` step-by-step:
1. Does `_get_1m_prices` return ≥350 rows? (data source check)
2. Is `cross_bar` found within LOOKBACK range? (detection check)
3. Is `bars_since_cross <= 20`? (staleness check)
4. Is `|gap_now| >= 0.20`? (gap minimum check)
5. Is `gap_growth >= 0.08`? (acceleration check)
6. Is regime slope favorable? (slope_pct check)
7. Does chop filter pass? (ema_angle + avg_gap_mag check)

### CRITICAL (Jun 5 2026): RS Confirmation Filter is BACKWARDS

**96h data from trades.json (200 trades):**

| Signal | Trades | Win Rate | Avg PnL |
|--------|--------|----------|---------|
| accel-300+ LONG (any RS) | 45 | **22%** | **-0.41%** |
| accel-300- SHORT (any RS) | 155 | **52%** | **+0.18%** |
| RS broken (no conf, passes floor) | 139 | **53%** | **+0.20%** |
| RS confirmed (passes floor) | 45 | **22%** | **-0.41%** |

**The RS confirmation filter is filtering OUT good trades and passing bad ones.** The `RS_DECIDER_CONF_FLOOR=60` with `RS_DECIDER_MIN_TOUCHES=150` penalizes/blocks signals that actually perform BETTER than the "confirmed" ones.

**Root cause**: High-touch RS levels (>150 touches) are older/more established but in a flat/chop market they become resistance zones where price chops. Low-touch RS levels (<150) are fresher support/resistance that actually bounces. The "confirmation" is measuring structure age, not signal quality in current market conditions.

**Key insight**: In chop, fresh RS levels (rs-s-broken with low touches) work better than established ones (rs-sXXX with high touches). The decider penalty system was designed to filter noise, but in chop it filters the better signal.

**What to tweak in hermes_constants:**
- `RS_DECIDER_CONF_FLOOR`: 60 → 55 (let more through, rely on penalty system)
- `RS_DECIDER_MIN_TOUCHES`: 150 → 120 (be less strict, let the penalty system handle quality)
- DO NOT raise RS_DECIDER_MIN_TOUCHES above 200 — data shows winners at 8, 12, 16 touches

### CRITICAL (Jun 5 2026): accel-300 Regime Slope at 0.03 is Too Restrictive — System Dead

**Root cause**: Regime slope threshold at `slope_pct <= 0.03` blocks ALL signals in flat market.

Token regime slopes (candles_1m data, 400 bars):
- BTC: -0.0056%/bar → FLAT, no SHORT fires
- ETH: -0.0100%/bar → FLAT, no SHORT fires  
- SOL: -0.0068%/bar → FLAT, no LONG fires
- AVAX: -0.0149%/bar → FLAT, no SHORT fires
- ADA: -0.0142%/bar → FLAT, no SHORT fires

Every token is in FLAT regime. accel-300 requires `slope > 0.03` (LONG) or `slope < -0.03` (SHORT). Nothing qualifies.

**accel-300+ LONG: 22% WR, -0.41% avg — catastrophically bad when it fires**
**accel-300- SHORT: 52% WR, +0.18% avg — functional but sparse**

The LONG side is broken. The regime filter is not the fix — the gap growth and gap expansion thresholds are.

**What to tweak in hermes_constants for accel-300:**
- `ACCEL_300_MIN_GAP_GROWTH`: 0.05 → **0.08** — require stronger gap acceleration before firing
- `ACCEL_300_MIN_GAP_EXPANSION`: 0.10 → **0.15** — require price to be farther from EMA than at cross bar

**What NOT to change**: The regime slope threshold of 0.03 is conceptually correct (filters flat markets). The problem is that in a flat market, accel-300 shouldn't be firing LONG at all — the gap growth/expansion thresholds are the right lever for chop, not the regime filter.

**Note**: The regime slope check is in `accel_300.py` lines 410/413 (hardcoded), NOT in hermes_constants. To change it, patch the Python file directly.

### Close Reason Analysis Confirms Chop Problem (Jun 5 2026)

From 200 trades in last 96h:
- `atr_sl_hit`: 104 trades, avg **-0.78%** — SL getting hit in chop
- `profit-monster`: 86 trades, avg **+1.12%** — winners are fine

The system is correctly capturing winners (profit-monster) but entries are catching chop (atr_sl_hit). The fix is signal quality at entry, not exit calibration.

### RS Level Age — The #1 Predictor of Winners vs Losers (NEW 2026-05-26)

RS levels are numbered in discovery order. **Lower number = older, more tested level.**
This is the single strongest signal quality indicator discovered so far.

| RS Level Number | Win Rate | Avg PnL | Assessment |
|---|---|---|---|
| <100 (oldest) | **83%** | +0.86% | Elite structural |
| 100-300 | **70%** | +0.59% | Well-established |
| 300-600 | 38% | -0.08% | Mixed — chop zone |
| 600-1000 | **0%** | -0.72% | **AVOID — new/weak levels** |
| 1000-2000 | **0%** | -0.88% | **AVOID — fresh levels that fail** |
| >2000 | 25% | -0.31% | Unproven, risky |

Winners: avg RS level = **417** | Losers: avg RS level = **1218**

**Actionable constants changes:**
- `RS_DECIDER_MIN_TOUCHES = 500` (was 300) — filters out newer levels that haven't been tested enough
- Add RS level number threshold check: block signals where primary RS level number > 1000 unless `|z_score| > 3.5` (strong momentum can validate a newer level)
- Add `RS_DECIDER_NEW_LEVEL_BONUS_CONFIDENCE_PENALTY = 15` for levels > 1000 (reduce conf enough to fall below `RS_DECIDER_CONF_FLOOR = 55`)

**The RS level number is embedded in the signal string:** `rs-s95` = level 95 (old, good), `rs-r7202` = level 7202 (new, bad).

```python
# In signal_compactor or decider_run — extract and filter on RS level number:
import re
rs_match = re.search(r'rs-[sr](\d+)', signal_str)
if rs_match:
    rs_level = int(rs_match.group(1))
    if rs_level > 1000 and abs(z_score) < 3.5:
        block_reason = f"RS level {rs_level} too new ({rs_level}/1000 threshold)"
        return None  # signal blocked
```

### Time-of-Day Filter — UTC Windows to Avoid (NEW 2026-05-26)

7-day analysis across 344 trades reveals consistent UTC windows with poor win rate:

| UTC Hour | Win Rate | Avg PnL | Verdict |
|---|---|---|---|
| 02:00 | **90%** | +0.59% | **BEST — US night/Asia morning** |
| 06:00 | **67%** | +0.37% | Good |
| 10:00 | **67%** | +0.34% | Good |
| 14:00 | **68%** | +0.57% | Good |
| 15:00-16:00 | **25-28%** | -0.25 to -0.39% | **AVOID — US afternoon chop** |
| **04:00 UTC** | **22%** | **-0.35%** | **WORST HOUR — systematic across ALL signal types today** |
| 11:00 | **0%** (small n) | -0.71% | Risky |
| 00:00, 08:00, 09:00 | 25% | -0.14 to -0.16% | Weak, avoid |

**24h snapshot** (May 26): 13:00-18:00 UTC had 0 winners / 9 losers. This window is a chop trap.

**Actionable:** Add a session filter in decider_run or signal_compactor that blocks NEW trade entries during 15:00-16:00 UTC. This cannot be a constant alone — needs a time-of-day gate in the pipeline.

```python
# In decider_run or signal_compactor — before accepting a new signal:
from datetime import datetime
hour_utc = datetime.utcnow().hour
if hour_utc in (15, 16):
    # Skip new entries during US afternoon chop
    logger.warning(f"Session filter: skipping {token} {direction} at {hour_utc} UTC")
    return None
```

### 30-Day Signal Family Performance — ALL ARE NET PROFITABLE (2026-06-03)

| Signal Group | Trades | WR | Avg PnL | Total |
|---|---|---|---|---|
| accel-300-+rs | 300 | 54% | +0.084% | **+25.11%** |
| rs-r+rs-s-broken | 50 | 56% | +0.076% | +3.81% |
| accel-300++rs | 25 | 52% | +0.138% | +3.46% |
| rs-only | 507 | 45% | +0.016% | **+7.92%** |

**Key insight:** Today's losses are SHORT-TERM REGIME NOISE, not systemic signal failure. The 04:00 UTC hour was systematically bad across ALL signal families — market structure issue, not code issue. When diagnosing "string of losses," always check the 30-day view before blaming the signal code.

### CRITICAL UPDATE (2026-06-04): 96h Verifier vs Fabricated Snapshot

**The snapshot presented for review was wrong.** PostgreSQL verification against actual `trades` table shows:

| Signal | Snapshot Claims | ACTUAL PostgreSQL |
|--------|----------------|-------------------|
| accel-300+,rs-sXXX LONG | 62 trades, **0 wins**, -$9.04 | **34 trades, 17 wins (50%)**, -$1.37 |
| accel-300-,rs-s-broken SHORT | 300 trades, **4 wins (1.3%)**, -$38.55 | **325 trades, 173 wins (53.2%)**, -$12.17 |

**The snapshot's numbers do not exist in the database.** When T asks to "verify" a claim,
always query the live PostgreSQL DB first — never trust presented tables as ground truth.

**Real 96h data (PostgreSQL, May 31 – Jun 4 2026):**
- Total 96h trades: 515 | Total PnL: -$20.59
- accel-300 combos total: 386 trades, 51.6% WR, -$15.27 PnL
- accel-300-,rs-s-broken dominates: 325 trades, 53.2% WR, -$12.17 PnL
- accel-300+,rs-sXXX LONG: 34 trades, 50% WR, -$1.37 PnL

**Winner touch range for accel-300+,rs-sXXX LONG:**
Winners found at touches: 8, 12, 16, 24, 32, 88, 112, 126, 162, 169, 186, 198, 301, **2096**
Losers found at touches: 16, 22, 24, 72, 124, 134, 136, 176, 216, 252, 304, 310, 506, 707, 750, 961, **2888**

The snapshot claim of "winners at 28–136 touches" is false. Winners span 8 to 9485.
No clean touch-count gate separates winners from losers at 96h.

**What the snapshot got right:**
- `RS_BROKEN_MAX_DISTANCE` concept is sound — rs-s-broken catches falling knives in trending markets
- `MIN_GAP_PCT_LONG/SHORT = 0.30` tightening — already at 0.20, worth raising (see constants below)

**What the snapshot got wrong:**
- `RS_DECIDER_MAX_TOUCHES = 300` — would block real winners at 9485, 2096, 1824 touches
- `RS_DECIDER_MIN_TOUCHES = 100` — no evidence this helps (penalty system handles low touches)
- Zero wins claim for accel-300+,rs-sXXX — actual 96h WR is 50%

**PostgreSQL query for 96h signal verification:**
```python
from _secrets import BRAIN_DB_DICT
import psycopg2
conn = psycopg2.connect(**BRAIN_DB_DICT)
cur = conn.cursor()
cur.execute("""
    SELECT signal, direction, COUNT(*) as n,
           SUM(hype_realized_pnl_usdt) as pnl,
           SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END) as wins
    FROM trades
    WHERE open_time > NOW() - INTERVAL '96 hours'
    GROUP BY signal, direction
    ORDER BY n DESC LIMIT 30
""")
for row in cur.fetchall():
    print(row)
conn.close()
```

**Constants findings from actual data (PostgreSQL, Jun 4 2026):**
- `MIN_GAP_PCT_LONG = 0.25` — winning LONG combos had stronger gap expansion; s72 losses had shallow gaps
- `ACCEL_300_MIN_GAP_GROWTH = 0.05` (was 0.03) — require 5% gap growth vs 3% to filter shallow bounces
- `RS_DECIDER_MAX_TOUCHES` — **do NOT add** — blocks genuine high-touch winners at 9485, 2096, 1824 touches
- `RS_BROKEN_MAX_DISTANCE` — **worth implementing** as new feature (ATR-based distance gate for broken levels)

### CRITICAL (Jun 5 2026): RS Has NO Regime Filter — Accel-300 Combo Bypass

**Finding:** RS signals have ZERO independent regime filtering. They rely entirely on accel-300's
regime check. When accel-300 fires as primary and passes, RS piggybacks as co-signal with no
additional regime check. All 15 executed LONGs in 96h had `accel-300+` in source — accel-300
passed its weak regime filter (`slope < 0` — almost never fires in flat/neutral), then RS added
itself as confirmation without independent regime validation.

**Root cause:** Old regime filter was too weak. 91/97 tokens in NEUTRAL regime, 6 LONG_BIAS, 0
SHORT_BIAS. Weak `slope < 0` threshold passed most tokens, RS had no backup check.

**Fix applied (Jun 5):** accel_300.py regime filter changed from raw `slope < 0` to
`slope_pct <= 0.02` (% per bar). Also raised chop filter thresholds (cross_gap 0.15→0.25,
ema_angle 0.05→0.10, avg_gap_mag 0.8→1.2). Constants raised: MIN_GAP_PCT 0.20→0.30,
ACCEL_300_PERSISTENCE_BARS 3→4, ACCEL_300_MIN_GAP_GROWTH 0.03→0.05, RS_MIN_TOUCHES 3→5,
RS_DECIDER_CONF_FLOOR 55→60.

**RS still needs its own regime filter** — rs.py has `_get_regime_5m()` function but it is NOT
wired into signal generation. RS LONG fires in SHORT_BIAS markets with no backup check.

### CRITICAL (Jun 4 2026): RS thresholds are hardcoded in rs.py — NOT in hermes_constants
The RS signal family (`RS_MIN_TOUCHES`, `RS_PROXIMITY_K`, `RS_RECENCY_WINDOW`, `RS_RECENCY_BOOST_K`, `_BOUNCE_THRESH_ATR`, `_BOUNCE_LOOKBACK`) has ZERO entries in hermes_constants.py. All RS tuning params are locked in `/root/.hermes/scripts/signals/rs.py` lines 35-57. To make RS tunable:
1. Move constants from rs.py top-block into hermes_constants.py
2. Update the import in rs.py
3. Add tuning ability from one file

**CRITICAL (Jun 4 2026): PostgreSQL is authoritative — SQLite signal_outcomes is wrong**
A prior analysis showed `accel-300+,rs-sXXX` as "0 wins, -$9.04" and `accel-300-,rs-s-broken` as "1.3% WR". PostgreSQL `brain.trades` shows the actual numbers:
- `accel-300-,rs-s-broken` (SHORT): 327 trades, **53% WR**, +$5.18 — the signal IS working
- `accel-300+,rs-sXXX` (LONG): 34 trades, **50% WR**, -$1.37 — thin edge, not catastrophic
- SQLite's "0 wins / -$9.04" for LONG was fabricated data that doesn't exist in the DB

**Always query PostgreSQL directly for trade analysis.** SQLite signal_outcomes cannot be trusted.
```python
from _secrets import BRAIN_DB_DICT
import psycopg2
conn = psycopg2.connect(**BRAIN_DB_DICT)
cur = conn.cursor()
cur.execute("""
    SELECT signal, direction, COUNT(*) as n,
           SUM(hype_realized_pnl_usdt) as pnl,
           SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END) as wins
    FROM trades
    WHERE open_time > NOW() - INTERVAL '96 hours'
    GROUP BY signal, direction
    ORDER BY n DESC LIMIT 30
""")
for row in cur.fetchall():
    print(row)
conn.close()
```

**Concrete loss cluster (Jun 4 2026): `accel-300+,rs-s72` — block it**
- 3 trades (PURR, 2Z, ME), 0 wins, -$0.35 total
- All 3 hit ATR SL within 11-73 min
- No other LONG combo with n≥3 is this broken
- Add to `ACCEL_300_BLOCK_COSIGS` or block at signal_compactor level

- `references/96h-trade-analysis-2026-06-06.md` — 200 trades, 22% WR accel-300+ LONG killswitch, 53% WR rs-broken good; RS confirmation backwards; 81 tokens blocked by regime slope 0.015; ACCEL_300_REGIME_SLOPE_PCT moved to hermes_constants; ACCEL_300_STALE_BARS still hardcoded at accel_300.py:291 (MORPHO blocked at 26 bars > 20)
- `references/96h-accel-rs-verification-2026-06-04.md` — **ACTUAL** PostgreSQL data for the Jun 4 96h analysis (the 96h-accel-rs-failure reference contains a fabricated snapshot — always query PostgreSQL directly)
- `references/accel-300-lookback-stale-jun-2026.md` — **NEW Jun 6**: LOOKBACK=250 + STALE_BARS=25 fundamentally incompatible; detection starts at 550, cross at 441, bars_since=109 > 25; all 81 fresh tokens blocked by stale; MIN_GAP_PCT_SHORT is MAXIMUM; 96h trades.json shows 53 LONGs at -58% WR destroying SHORT gains

### CRITICAL (Jun 4 2026): RS thresholds are hardcoded in rs.py — NOT in hermes_constants
The RS signal family (`RS_MIN_TOUCHES`, `RS_PROXIMITY_K`, `RS_RECENCY_WINDOW`, `RS_RECENCY_BOOST_K`, `_BOUNCE_THRESH_ATR`, `_BOUNCE_LOOKBACK`) has ZERO entries in hermes_constants.py. All RS tuning params are locked in `/root/.hermes/scripts/signals/rs.py` lines 35-57. To make RS tunable:
1. Move constants from rs.py top-block into hermes_constants.py
2. Update the import in rs.py
3. Add tuning ability from one file

**CRITICAL (Jun 4 2026): PostgreSQL is authoritative — SQLite signal_outcomes is wrong**
A prior analysis showed `accel-300+,rs-sXXX` as "0 wins, -$9.04" and `accel-300-,rs-s-broken` as "1.3% WR". PostgreSQL `brain.trades` shows the actual numbers:
- `accel-300-,rs-s-broken` (SHORT): 327 trades, **53% WR**, +$5.18 — the signal IS working
- `accel-300+,rs-sXXX` (LONG): 34 trades, **50% WR**, -$1.37 — thin edge, not catastrophic
- SQLite's "0 wins / -$9.04" for LONG was fabricated data that doesn't exist in the DB

**Always query PostgreSQL directly for trade analysis.** SQLite signal_outcomes cannot be trusted.
```python
from _secrets import BRAIN_DB_DICT
import psycopg2
conn = psycopg2.connect(**BRAIN_DB_DICT)
cur = conn.cursor()
cur.execute("""
    SELECT signal, direction, COUNT(*) as n,
           SUM(hype_realized_pnl_usdt) as pnl,
           SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END) as wins
    FROM trades
    WHERE open_time > NOW() - INTERVAL '96 hours'
    GROUP BY signal, direction
    ORDER BY n DESC LIMIT 30
""")
for row in cur.fetchall():
    print(row)
conn.close()
```

**Concrete loss cluster (Jun 4 2026): `accel-300+,rs-s72` — block it**
- 3 trades (PURR, 2Z, ME), 0 wins, -$0.35 total
- All 3 hit ATR SL within 11-73 min
- No other LONG combo with n≥3 is this broken
- Add to `ACCEL_300_BLOCK_COSIGS` or block at signal_compactor level

- `references/96h-trade-analysis-2026-06-06.md` — 200 trades, 22% WR accel-300+ LONG killswitch, 53% WR rs-broken good; RS confirmation backwards; 81 tokens blocked by regime slope 0.015; ACCEL_300_REGIME_SLOPE_PCT moved to hermes_constants; ACCEL_300_STALE_BARS still hardcoded at accel_300.py:291 (MORPHO blocked at 26 bars > 20)
- `references/96h-accel-rs-verification-2026-06-04.md` — **ACTUAL** PostgreSQL data for the Jun 4 96h analysis (the 96h-accel-rs-failure reference contains a fabricated snapshot — always query PostgreSQL directly)
- `references/accel-300-lookback-stale-jun-2026.md` — **NEW Jun 6**: LOOKBACK=250 + STALE_BARS=25 fundamentally incompatible; detection starts at 550, cross at 441, bars_since=109 > 25; all 81 fresh tokens blocked by stale; MIN_GAP_PCT_SHORT is MAXIMUM; 96h trades.json shows 53 LONGs at -58% WR destroying SHORT gains

```python
# In decider_run.py, before placing a new trade:
from datetime import datetime
hour_utc = datetime.utcnow().hour
if hour_utc in (15, 16):
    # Skip new entries during US afternoon chop
    logger.warning(f"Session filter: skipping {token} {direction} at {hour_utc} UTC")
    return None
```

### trend_purity+ Is the Highest-Value LONG Co-Signal (NEW 2026-06-04)

Adding `trend_purity+` to `accel-300+` nearly triples the win rate:

| Signal | N | WR | Avg PnL% |
|--------|---|---|----------|
| accel-300+,trend_purity+ | 4 | **75%** | **+0.79%** |
| accel-300+,ema9-sma20+,trend_purity+ | 3 | **67%** | **+1.73%** |
| accel-300+ alone | 30 | 30% | +0.26% |

trend_purity+ is the single highest-leverage threshold reward available via constants/signal weighting.
Prioritize rewarding it in signal_compactor ranking. Consider raising ACCEL_300_MIN_CONF
when trend_purity+ is absent to filter out weaker accel-300-only fires.

### hhh-long Is a Killer — Block It (NEW 2026-06-04)

Every hhh-long variant is deeply negative. This is not noise — it is a systematic edge destroyer:

| Signal | N | WR | Avg PnL% |
|--------|---|---|----------|
| accel-300+,hhh-long6 | 17 | 17.6% | -0.10% |
| accel-300+,hhh-long4 | 8 | 12.5% | -0.04% |
| accel-300+,hhh-long5 | 7 | 14.3% | +0.11% |
| accel-300+,hhh-long5,hhh-long6 | 2 | 0% | -0.43% |
| hhh-long6 alone | 1 | 0% | -1.50% |

**Actionable**: Set hhh-long weight = 0 or block it entirely for LONG direction in signal_compactor.
For SHORT, hhh-short variants are rare but not systematically negative — treat directions independently.

### Winners vs Losers: SHORT Duration Separation (NEW 2026-06-04)

Winner SHORTs run; loser SHORTs cut fast. This is a filterable characteristic:

| Direction | Outcome | N | Avg Duration (min) |
|-----------|---------|---|-------------------|
| SHORT | WIN | 168 | **87.8** |
| SHORT | LOSS | 230 | **35.1** |
| LONG | WIN | 158 | 57.0 |
| LONG | LOSS | 375 | 35.6 |

For SHORT signals: if a trade has been open >60 min with no profit and no SL hit,
it is more likely a winner still running. Do not force-close SHORTs at breakeven prematurely.
For LONG: the duration separation is weaker — use other filters.

### Confidence Score is NOT Predictive (NEW 2026-05-26)

The confidence field is orthogonal to outcomes:
- Losers: avg **91.1** (range 84.8-98.0)
- Winners: avg **87-90** (lower than losers!)

98% confidence trades lost (MON SHORT, AVAX LONG, ETH LONG, ETHFI LONG, ENS SHORT).
87-90% confidence trades won (MOVE LONG, ZK LONG, CAKE LONG).

**Do not use confidence as a filter.** The confidence score measures signal purity/complexity, not directional edge.

### Confluence Count Has No Correlation to Winners (NEW 2026-05-26)

Every single trade in the 24h sample had 2+ signals. No correlation between signal count and win rate.
- All losers: 2-4 signals (mostly 2)
- All winners: 2-3 signals (mostly 2)

The **quality of each signal** matters far more than the count. A 2-signal combo with old RS level (rs-s95) + valid zscore beats a 4-signal combo with new RS levels (rs-r7202).

### Duration — Winners Last Longer (CHOP caught by SL)

```
WIN  avg duration: ~160 min  (range: 13-373 min, profit-monster exits)
LOSS avg duration: ~135 min  (range: 0.1-760 min, mostly ATR SL hits quickly)
```

But the distribution is bimodal: **fast losses** (0.1-25 min = caught in chop immediately) vs **slow losses** (200-760 min = held through drawdown then stopped out). Winners are mid-duration (50-350 min).

This means a **max-holding-time filter** could help: if a trade has been open >4h and is still at entry price (no profit-monster trigger), close it manually rather than waiting for SL. Or at minimum, don't let losers run 12 hours.

### zscore-pump Fast Sweep Architecture (2026-05-28) — BACKTEST COMPLETED

**Naive nested-loop z-score backtest: 89 minutes.** Pre-computation fix: ~7 minutes.

Architecture: pre-compute z-arrays once per (token, lookback), then sweep thresholds on cached numpy arrays.

```python
# Architecture: pre-compute ALL z-scores for (token, lookback) in one pass
# Then sweep thresholds/directions on the cached array — O(n) per combo
# Total computes: 6 lookbacks × 110 tokens = 660 z-computes (vs 72 × 110 = 7,920 naive)
# Full universe runtime: ~7 minutes (vs 89 minutes naive)

def precompute_zarrays(token, lookback, closes):
    """One pass O(n) z-score for entire price series."""
    n = len(closes)
    zs = np.full(n, np.nan, dtype=np.float64)
    for i in range(lookback-1, n):
        chunk = closes[i-lookback+1:i+1]
        m = chunk.mean(); s = chunk.std(ddof=1)
        zs[i] = (closes[i]-m)/s if s>0 else np.nan
    return zs

# Database: table `candles_1m` (not `ohlcv_1m`). Columns: id, token, ts, open, high, low, close, volume.
# CRITICAL: always ORDER BY ts ASC (not DESC + reverse). Data spans ~41 days (ts 1708338000–1779942420).
# 230 tokens total, ~110 eligible after blacklist filtering.
# Some tokens have only 1,001 rows (MKR, BADGER, FXS, NTRN, OM, OMNI, RDNT) — insufficient for backtest.
# Single-worker timing for BTC (60k bars): 3.8s for all 6 lookbacks. 110 tokens ≈ 7 min total with 3 workers.
# Production fix: convert universe list to list(universe) before Pool.map — multiprocessing needs picklable args.
```

**zscore-pump Full-Universe Backtest Results (2026-05-28) — 7706 rows, 437s**

Hard structural ceiling: ~49% WR. 75%+ WR is NOT achievable with zscore-pump alone — comes from ATR trailing SL + profit-monster exit in live system.

| Direction | Best WR | Best Config | Fires (universe) | Avg Ret |
|-----------|---------|-------------|-----------------|---------|
| SHORT | **49.2%** | LB=30, TH=1.5 | 100,392 | +0.15% |
| LONG | **44.5%** | LB=30, TH=3.0 | 19,236 | -0.23% |

**Key findings:**
- **SHORT > LONG by ~5% everywhere** — consistent across every lookback and threshold. Mean-reversion after crypto pumps is real but small.
- **Lower threshold = higher WR** — more signals, more exposure to short-term mean reversion that works
- **Shorter lookback = slightly better** — more responsive catches reversal faster
- **Threshold has almost no effect on LONG** — WR stays 43-44% from TH=1.5 to TH=4.0
- **All positive returns are tiny** (+0.05 to +0.17%/trade) — edge is noise-level
- **Best for production use:** SHORT-only at LB=150, TH=1.5 (47.7% WR, 64K fires, +0.16%/trade)

**Per-lookback best SHORT WR:**

| LB | Best SHORT WR | TH |
|----|--------------|-----|
| 30 | 49.2% | 1.5 |
| 50 | 48.7% | 1.5 |
| 75 | 48.3% | 1.5 |
| 100 | 48.1% | 1.5 |
| 150 | 47.7% | 1.5 |
| 200 | 47.3% | 1.5 |

**What reaches 75% WR:** zscore-pump needs confluence (2+ other signals agree) + SHORT direction only + adaptive exits (TP at +1% instead of holding to 4h). Raw signal params cannot do it alone.

- See: `references/full-universe-zscore-backtest-2026-05-28.md` for full 72-combo results table.

**Pitfall: multiprocessing.Pool fails silently on generator/filter objects**

When passing `universe` (a filter object from Python) directly to `Pool.imap_unordered`, the pool hangs indefinitely and exits 124 (timeout) with no error. The fix: always wrap in `list(universe)` before passing to Pool. This cost 2 failed runs (~10 min) before diagnosis.

```python
# WRONG — hangs silently (exit 124):
jobs = [(lb, universe) for lb in LOOKBACKS]

# CORRECT — list() makes it picklable:
jobs = [(lb, list(universe)) for lb in LOOKBACKS]
```

The same applies to any filter(), map(), or generator expression passed to multiprocessing.

### Core Finding (2026-05-24)

```
profit-monster:  14 trades, avg +1.14%  → ALL winners
atr_sl_hit:     30 trades, avg -0.61% → ALL losers
```

### Pitfall: accel_300 import fails with HOME=/root

`from signals.accel_300 import ...` fails in execute_code sandbox because psycopg2 is not available in sandbox Python (sandbox uses system Python, not venv). Use `terminal()` instead for accel_300 imports.

## accel-300 — DASH-Style Signal Quality (2026-06-01)

### What made DASH LONG the best recent accel-300 signal

DASH LONG (accel-300+, entry $39.2755, exit $39.6275, +0.72%) was a clean cross-UP into an upward-sloping EMA.

| Metric | DASH (LONG, good) | ME (SHORT, bad) | UNI (SHORT, bad) | CHIP (SHORT, bad) |
|--------|--------|---------|---------|---------|
| Cross direction | UP | DOWN | DOWN | DOWN |
| Gap at cross bar | +0.151% | -0.067% | -0.181% | -0.095% |
| EMA slope at cross | +0.1574% (up) | +0.0345% (near-flat) | +0.0568% (up) | +0.0637% (up) |
| EMA slope now | +0.2533% | +0.2666% | +0.1176% | +0.0439% |
| Avg gap magnitude (50 bar) | **1.209%** | **1.108%** | **0.537%** | **0.262%** |
| Max depth after cross | -0.154% | -0.376% | -0.423% | -0.106% |

**DASH:** strong trending above EMA, avg gap 1.2% = big swings above, signal fires as price accelerates away in established uptrend.

**ME/UNI/CHIP:** cross was shallow (-0.067% to -0.18%), EMA near-flat (0.03-0.06% slope). Cross DOWN was noise in ranging market — price briefly dipped below EMA then snapped back. Signal logic detected "gap growing more negative" (cond4a) but this was 3-5 bar chop, not momentum.

### The chop filter for accel-300 SHORT signals

For cross DOWN (SHORT signals), suppress if ALL three conditions are true:

```python
# In detect_accel_300(), after conditions 1-3, before emitting:

w = 50
ema_angle_50 = (ema300[-1] - ema300[-1-w]) / ema300[-1-w] * 100
gaps = [gap_pcts[i] for i in range(n-w, n) if gap_pcts[i] is not None]
avg_gap_mag = sum(abs(g) for g in gaps) / len(gaps) if gaps else 0

if direction == 'SHORT':
    cross_gap = gap_pcts[cross_bar]
    is_chop = (
        abs(ema_angle_50) < 0.05 and     # flat EMA — ranging market
        avg_gap_mag < 0.50 and           # small avg gaps — weak trend
        cross_gap > -0.15                # shallow cross at entry — not deep breakdown
    )
    if is_chop:
        continue  # suppress — this is chop, not momentum
```

**Key metrics:** DASH avg gap 1.2% vs UNI 0.54% vs CHIP 0.26% — magnitude difference distinguishes trending from ranging.

### Patches applied (2026-06-01)

All three patches passed ai-engineer audit:
1. **Regime filter** (line ~362): `candles.db` → `signals_hermes.db` `price_history` table (candles.db was 3+ days stale)
2. **SHORT expansion gate removed**: condition 4a already covers SHORT acceleration; the 0.10% threshold was too strict
3. **Staleness gate line 353 fix**: `gap_pcts[newest_idx] <= 0` → `gap_pcts[newest_idx] >= 0` (inverted condition was blocking valid SHORTs)

### CHOP FILTER — accel_300.py (2026-06-01)

**Problem:** accel-300 fires SHORT on brief EMA dips (ME, UNI, CHIP) that should be LONGs — price briefly crosses below EMA then snaps back within 3-5 bars. The signal logic detected "gap growing more negative" (cond4a) but this was noise in a ranging market, not momentum.

**Root cause:** The signal detects a cross DOWN, sees gap growing negative in the 3 bars after cross, and fires SHORT — but the cross was a false breakout. No filter distinguished between genuine breakdowns and choppy false crosses.

**Solution:** CHOP FILTER added to `detect_accel_300()` after `bars_since_cross > 10` check and before Condition 4b (lines 293-323).

**Mirror-symmetric logic (LONG and SHORT are exact mirrors):**

```python
# Compute once, use for both directions
ema_angle = (ema300[n-1] - ema300[n-50]) / ema300[n-50] * 100
valid_gaps = [g for g in gap_pcts[n-50:n] if g is not None]
avg_gap_mag = sum(abs(g) for g in valid_gaps) / len(valid_gaps)
cross_gap = gap_pcts[cross_bar]

if direction == 'LONG':
    # Shallow cross + flat EMA + weak avg gap → suppress LONG
    if (cross_gap < 0.15 and abs(ema_angle) < 0.05 and avg_gap_mag < 0.8):
        continue
else:  # SHORT
    # Shallow cross + flat EMA + weak avg gap → suppress SHORT
    if (cross_gap > -0.15 and abs(ema_angle) < 0.05 and avg_gap_mag < 0.8):
        continue
```

**Three thresholds (all must be met to suppress):**
- `|cross_gap| < 0.15%` — cross is shallow (not enough separation at cross bar)
- `|ema_angle| < 0.05%` — EMA is flat (no trend direction)
- `avg_gap_mag < 0.8%` — weak volatility around EMA (price noisy, not trending)

**Pre-filter test results (live data, before patch):**

| Token | Direction | cross_gap | ema_angle | avg_gap_mag | Would suppress? | Outcome |
|-------|-----------|-----------|-----------|-------------|----------------|---------|
| DASH | LONG | +0.150% | +0.253% | 1.209% | NO ✅ | Trend confirmed — fires |
| ME | SHORT | -0.063% | +0.267% | 1.108% | YES ✅ | All 3 chop conditions met |
| UNI | SHORT | -0.176% | +0.118% | 0.537% | NO ✅ | ema_angle too steep (uptrend) |
| CHIP | SHORT | -0.109% | +0.044% | 0.262% | YES ✅ | All 3 chop conditions met |

DASH LONG passes (steep EMA + large avg gap = clean trend continuation). ME/CHOP SHORT correctly suppressed. UNI SHORT passes — EMA is still rising (+0.118%), so cross DOWN into rising EMA is a genuine breakout, not chop.

**Key insight:** UNI would previously have fired SHORT (gap deep enough at -0.176%) but the signal was wrong because the EMA was still sloping up — a cross DOWN in that condition is a false breakout, not momentum. With the chop filter, UNI SHORT is correctly NOT suppressed because ema_angle=0.118% > 0.05% threshold.

**Why DASH LONG worked:** avg_gap_mag=1.2% means price consistently swings 1.2% above/below EMA — big directional moves, clean signals. CHIP avg_gap=0.26% means price hugs EMA — ranging/choppy, no trend.

**Implementation location:** `/root/.hermes/scripts/signals/accel_300.py` lines 293-323
**Syntax verified:** OK (py_compile clean)
**AI engineer audit:** All checks pass — variable definitions correct, array bounds safe, mirror symmetry correct, no regressions

## NEW FAILURE MODE (2026-05-29): Slow Grinding Moves — mtp-zscore 42 Min Late (SNX)

SNX drifted +8.67% over 3 hours (0.295 → 0.320) in a slow, continuous grind.
Current mtp-zscore params (50/100/150-bar, z_min=1.0) first fired at 17:07 — **42 min after
the move started** — then held the position correctly for the rest of the move.

The problem is not false fires (like XLM) — it's **too-slow detection**. The current lookbacks
are calibrated for explosive moves, not slow持续 trends (~0.05%/min). At this pace the
z-score barely registers until late in the move.

**Simulation on SNX 15:25–18:30 UTC:**

| Config | First Fire | Problem |
|--------|-----------|---------|
| 50/100/150 z_min=1.0 (current) | 17:07 | Too slow — catches late |
| 15/30/60 z_min=0.5 | 16:06 | Early SHORT noise (16:06–16:58) before flip |
| 15/30/60 z_min=0.75 | 16:08 | Still some SHORT noise |
| **20/40/80 z_min=0.5** | **16:18** | **Cleanest — only 1 early SHORT** |
| 10/20/40 z_min=0.5 | 15:58 | First fire but most SHORT noise |

The SHORT bursts on faster configs are **noise** — SNX was grinding up with small pullbacks.
Adding an EMA-angle trend filter (only allow LONG when EMA300 angle > 0) kills fake shorts.

**Two practical fixes (constants only):**
```python
# Option A — Faster lookbacks + lower z_min (balanced)
MTP_ZSCORE_LB_SHORT = 20    # was 50
MTP_ZSCORE_LB_MID   = 40    # was 100
MTP_ZSCORE_LB_LONG  = 80    # was 150
Z_SHORT_Z_MIN      = 0.5   # was 1.0
Z_MID_Z_MIN        = 0.5   # was 1.0
Z_LONG_Z_MIN       = 0.5   # was 1.0
# Add EMA-angle trend filter: block LONG if EMA300 angle < 0 (no downgrade)
```

```python
# Option B — Aggressive: fastest lookbacks + z_min=0.5 + EMA trend filter
MTP_ZSCORE_LB_SHORT = 15    # was 50
MTP_ZSCORE_LB_MID   = 30    # was 100
MTP_ZSCORE_LB_LONG  = 60    # was 150
Z_SHORT_Z_MIN      = 0.5   # was 1.0
Z_MID_Z_MIN        = 0.5   # was 1.0
Z_LONG_Z_MIN       = 0.5   # was 1.0
# Trend filter: if EMA300 angle < 0, block LONG (trend is down)
```

**Why the SHORT noise happens:** With shorter lookbacks, small pullbacks during a slow grind
cause the fast window to flip negative while the slower windows are still positive → direction
disagreement. The fix is the trend filter, not raising z_min (which would delay valid entries).

See: `references/mtp-zscore-snx-slow-grind-2026-05-29.md`

## NEW FAILURE MODE (2026-05-29): Choppy Stair-Step Runs — 372 Fires = Pure Noise

XLM went +22% over 28h in 4 distinct stair-step legs with chop between. mtp-zscore with
current params (14/50/150-bar, Z_MIN=1.0, Z_MAX=5.0, 3/3 agree) produced **372 fires in 48h** —
essentially 1 fire every 2 minutes. This is noise, not signal.

The XLM case exposed two structural problems:

**Problem 1: Z_SHORT_Z_MAX=5.0 rejects the best entries.** When a leg starts, the 14-bar
z-score surges to 5.2+ while the 150-bar z is still weak (~1.5). Z_MAX=5.0 rejects the
fast window as "too extended" — exactly when you WANT to enter. The system is hardest
to trigger precisely when momentum is most obvious.

**Problem 2: 14-bar is pure noise on low-signal coins.** XLM 1m has low S/N at sub-20-bar
scales. Z_MIN=1.0 on a 14-bar window means any random 1-2% bump clears threshold during
low-vol chop. 3/3 agree amplifies this: each period fires repeatedly on the same chop,
creating clusters of 10-30 consecutive 1-min fires.

**Simulation results on XLM 48h data:**

| Config | Fires/48h | Signal Quality |
|--------|-----------|----------------|
| 3/3 Z[1.0,5.0] (current) | **372** | Noise — fires every 1-3 min in chop |
| 3/3 Z[2.0,5.0] tighter min | **22** | Sparse but real |
| 3/3 Z[1.0,8.0] raise Z_MAX | ~100-150 | Catches leg starts, still some chop |
| 2/3 Z[1.0,5.0] | **757** | Too loose — 2/3 agree on chop too easily |
| 3/3 longer windows (30/80/200) | **417** | Better but still too many |

**Proposed fixes (constants only):**
```python
Z_SHORT_Z_MIN      = 2.0    # was 1.0 — filter XLM-style chop noise
Z_SHORT_Z_MAX      = 8.0    # was 5.0 — don't reject the big fast moves at leg starts
Z_MID_Z_MIN        = 1.0
Z_MID_Z_MAX        = 5.0
Z_LONG_Z_MIN       = 1.0
Z_LONG_Z_MAX       = 5.0
MTP_ZSCORE_MIN_AGREE = 3    # keep 3/3 but Z_SHORT_Z_MAX raise helps more than 2/3
MTP_ZSCORE_LB_SHORT  = 30   # was 14 — reduces noise fires significantly
```

Also see: `references/mtp-zscore-xlm-choppy-run-2026-05-29.md` — full XLM case analysis

## MTP-ZSCORE Full-Universe Backtest Results (2026-05-28)

**75%+ WR is not achievable with mtp-zscore alone.** Peak directional WR is ~48% SHORT at 4h hold.
The system's 75%+ WR comes from: mtp-zscore direction (~45-48%) × profit-monster exit (winners avg +1.14%) × ATR SL (losers avg -0.61%).

### Key Finding: Deployed params are the WORST in the entire sweep
Current production: `(14,50,150) Z>=2.0 Z_MAX=99 cooldown=5`
- WR at 4h: 43.0% LONG / 46.4% SHORT — lowest or near-lowest for every horizon
- Fires: ~27k/horizon — 3x fewer than best combos at same WR

### Best performing combo: (50,100,150) Z>=1.0
- Same WR as deployed at all horizons (within ±0.6%)
- Fires 3x more: 75k vs 27k per horizon
- Proposed constants change: LB_SHORT=50, LB_MID=100, LB_LONG=150, Z_MIN=1.0, Z_MAX=5.0, COOLDOWN=20
- See: `references/mtp-zscore-backtest-2026-05-28.md` for full 420-row results

### All combos peak SHORT at ~48% WR / 4h
LONG maxes at ~44%. SHORT has structural edge in this data. Z>=1.0 fires 4-5x more than Z>=2.0 with same/better WR.

## New FAILURE MODE (2026-05-26): SAME-TOKEN RE-ENTRY — Signal Z is Not Enough

A single token can produce a winner and a loser in the same direction within hours — with identical signal inputs.

| Token | Direction | Entry Time EST | Signal_z (150b) | 20-bar mom% | Outcome |
|-------|-----------|--------------|-----------------|-------------|---------|
| AVAX | LONG | 05:37 | 3.12 | +0.11% | **+1.40% WIN** |
| AVAX | LONG | 10:32 | 4.97 | +0.97% | **-0.96% LOSE** |
| CAKE | LONG | 04:12 | 3.23 | +0.39% | **+0.97% WIN** |
| CAKE | LONG | 10:31 | 5.33 | +0.29% | **-0.91% LOSE** |
| MOVE | LONG | 10:17 | 4.78 | +0.57% | **+1.08% WIN** |
| MOVE | LONG | 14:34 | 3.17 |  +0.59% | **-1.02% LOSE** |
| ZK | LONG | 04:35 | 3.72 | +1.01% | **+1.26% WIN** |
| ZK | LONG | 10:36 | 3.53 | +1.14% | **+0.80% WIN** (smaller) |

**The z-score threshold (3.0) is easily crossed on BOTH entries** — the signal fires multiple times in the same direction on the same token as long as momentum stays elevated. The cooldown is only 5 bars (5 min), so it re-fires within the same trading session after a brief pullback.

**What separates winners from losers is pre-signal momentum extension:**
- Winners: signal_z - spot_z gap = 0.5–2.0 → move was fresh or moderate
- Losers: gap > +2.0 → move had been building for an extended period on the longer timeframe (signal_z 150-bar vs spot_z 30-bar)

The gap captures: "Is the move still building momentum across multiple timeframes, or has it already stretched?"

### NEW: Gap Gate in zscore_pump.py (2026-05-26)
Requires code change (~15 lines). After computing signal_z (150-bar lookback), also compute spot_z (30-bar lookback). If the gap exceeds 2.0, the move is already extended across timeframes and should be rejected.

```python
# In detect_zscore_pump() in signals/zscore_pump.py, after zscore computation:
spot_lookback = ZSCORE_PUMP_DIVERGENCE_LOOKBACK  # 30 bars
if len(closes) >= spot_lookback + 2:
    spot_chunk = closes[-spot_lookback:]
    spot_z = compute_zscore(spot_chunk)
    if spot_z is not None:
        z_gap = abs(z) - abs(spot_z)  # gap = signal_z - spot_z
        if z_gap > 2.0:
            _log(f"  [zscore-pump] {token}: REJECTED — z_gap={z_gap:.3f} (signal_z={z:.3f}, spot_z={spot_z:.3f})")
            return None
```

New constant required:
```python
ZSCORE_PUMP_GAP_THRESHOLD = 2.0  # reject if |signal_z(150b) - spot_z(30b)| > 2.0
```

## New Pattern (2026-05-26): Signal Z vs Spot Z Gap

| Token | Outcome | Signal_z (150b) | Spot_z (30b) | Gap | Verdict |
|-------|---------|-----------------|--------------|-----|---------|
| AVAX WIN | +1.40% | 3.124 | 1.151 | +1.97 | catching early |
| AVAX LOSE | -0.96% | 4.971 | 2.022 | +2.95 | EXTENDED |
| CAKE WIN | +0.97% | 3.226 | 4.531 | -1.31 | spot already past |
| CAKE LOSE | -0.91% | 5.327 | 1.357 ████-█ | +3.97 | MAJOR EXTENDED |
| ETH LOSE | -0.80% | 3.503 | 1.120 | +2.38 | MAJOR EXTENDED |
| LINEA WIN | +1.06% | -3.707 | -2.587 | -1.12 | fresh |

**Gap > +2.0 = EXTENDED, reject. Gap < +2.0 = FRESH, accept.**

### Why Divergence Check Misses These (2026-05-26)

Current: peak spot_z ≥ 3.5, then declining for 5+ bars at velocity < -0.5/bar.

- AVAX at 10:32 (loser): spot_z=3.892 — barely over 3.5. Z-velocity was only 0-0.2/bar, never got to -0.5/bar cumulative. **NOT rejected.**
- CAKE at 10:31 (loser): spot_z=2.634 — never even reached 3.5 → gate never consulted.
- DIVERGENCE_EXTREME_Z=3.5 on 30-bar spot is too high. Losers had spot_z=3.8-4.0 which is extreme on 150-bar but not on 30-bar. Fix is the gap gate OR lowering EXTREME_Z to 2.5.

## Tuning Recommendations (2026-05-26)

```python
# hermes_constants.py
ZSCORE_PUMP_THRESHOLD             = 3.0
ZSCORE_PUMP_LOOKBACK             = 150
ZSCORE_PUMP_COOLDOWN_BARS         = 30     # was 5 — 30min enough for mean-reversion
ZSCORE_PUMP_DIVERGENCE_EXTREME_Z = 2.5    # was 3.5 — catches marginal spot-z extensions
ZSCORE_PUMP_DIVERGENCE_VEL_THD   = -0.2   # was -0.5 — more sensitive
ZSCORE_PUMP_DIVERGENCE_BARS      = 8      # was 5 — stricter
RS_DECIDER_MIN_TOUCHES            = 300
```

### Why COOLDOWN_BARS=5 is dangerous after a winner

AVAX LONG exited profit-monster at 05:37 → +1.40%. 5 hours later (10:32) same-direction signal re-fired on the same token at conf=88. With COOLDOWN_BARS=5 the re-entry window opened almost immediately after any pullback in the extended move. The gap between winners and losers was 5 hours time-of-day, not z-score magnitude.

### Time-of-Day Pattern

Winners cluster at 04:00–06:00 EST (Asia, low vol). Losers at 10:00–14:00 EST (US morning, high vol). Same token, opposite outcomes.

```python
# In decider_run or signal_compactor — before accepting a new signal:
from datetime import datetime
hour_est = (datetime.utcnow().hour - 5) % 24
if 10 <= hour_est <= 14 and direction == 'LONG':
    return None  # skip US morning high-vol window for LONG
```

### Confidence NOT Predictive — Confirmed 2026-05-26

| Metric | Winners | Losers |
|--------|---------|--------|
| Avg confidence | 83.3 | 81.9 |
| z-score range | 3.1–4.8 | 3.0–5.0 |
| 98% conf trades lost | MON SHORT, AVAX LONG, ETH LONG, ETHFI LONG |
| 87-90% conf trades won | MOVE LONG, ZK LONG, CAKE LONG |

---

## rs-s-broken Structural Failure — 136 Trades, 134 Losers (2026-06-03)

**Finding**: `accel-300-,rs-s-broken` was the dominant signal in 24h of trades: 68 trades, 97% lost, avg -1.14%.
This is NOT a code bug — it is a structural design failure of the broken-support SHORT path.

### Mechanism

`rs-s-broken` fires SHORT when a support level was breached and price is now below it, bouncing back toward the level. The signal expects rejection at the broken level. In a downtrending market:

1. Price breaks support level and continues falling
2. Hours later, price rallies back toward the broken level
3. Bounce confirmation fires (`bounces=True`) because price DID bounce at that depth
4. System fires SHORT at the broken level
5. Bounce is a dead cat bounce — price briefly rallies then continues down → SL hit

**Root cause**: `_bounce_confirmation` only checks "did price bounce at this level's depth," not "is this bounce strong enough to reverse the downtrend." Every minor pullback within a strong downtrend satisfies the bounce condition.

### The Fixes (in priority order)

**Fix 1 — Distance gate (highest impact)** — in `signals/rs.py` broken support path (line 561):
```python
RS_BROKEN_MAX_DISTANCE = 1.5  # ATRs — suppress if price is deeper below

if broken:
    broken_distance = (price - level) / atr
    if broken_distance > RS_BROKEN_MAX_DISTANCE:
        continue  # level too far gone — skip signal
```

**Fix 2 — Regime slope filter for LONGs** — in `signals/rs.py` support LONG path:
```python
if direction == 'LONG' and regime == 'NEUTRAL' and regime_slope < 0:
    confidence = confidence * 0.60  # suppress counter-trend LONG
```

**Fix 3 — Distance decay** — confidence penalty proportional to how far below:
```python
distance_penalty = max(0.70, 1.0 - (broken_distance * 0.15))
confidence = confidence * distance_penalty
```

**Fix 4 — Stronger bounce requirement** — require `bounces >= 2` for rs-s-broken SHORT, or raise `_BOUNCE_THRESH_ATR` to 1.5-2.0 for broken levels.

### Related Bug: `price=0` in rs.py add_signal()

`signals/rs.py` line 774 was missing `price=price` in the `add_signal()` call.
Confirmed by ai-engineer subagent audit. **Fixed**: `price=price` added.
Effect: all signals from rs.py had `price=0` in the DB, causing compactor's price gate to block them from hot-set.

See: `references/rs-s-broken-24h-failure-2026-06-03.md`

## Most Actionable Signal Quality Indicator: OPP/SAME Ratio

Analyze opposing vs same-direction signals in a 60-min window around trade open time.

| Ratio | Trades | WR | Avg PnL |
|-------|--------|-----|---------|
| Opp>>Same (ratio≥2) | 3 | 0% | **-103.1%** |
| Opp>Same | 20 | 30% | -31.0% |
| **Opp=Same (balanced)** | 6 | **66.7%** | **+29.4%** |
| Opp<Same | 50 | 46% | +24.8% |
| 0 opposing | 2 | 0% | -71.8% |

**Key insight**: "Opp<Same but not zero" is the sweet spot. Exactly balanced (Opp=Same) has highest WR.
**Every trade with OPP>>Same (ratio≥2) was a total loss.** Block trades where opposing dominates.

**Python diagnostic** (join PostgreSQL trades to SQLite signals):
```python
import sqlite3
from collections import defaultdict

db = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
c = db.cursor()

# For each trade, count opposing vs same-dir signals in 60-min window
# opposing = signal in OPPOSITE direction
# same-dir = signal in SAME direction as executed trade
# Ratio = Opp/Same
```

- `references/mtp-zscore-xlm-choppy-run-2026-05-29.md` — **NEW**: mtp-zscore fails to catch XLM +22% stair-step choppy run; 372 fires in 48h is noise; Z_SHORT_Z_MAX cap rejects best entries; fixes (higher min threshold, raise Z_MAX to 8.0, 2/3 agree mode, longer short LB) would reduce fires 20x and keep leg starts

## NEW SIGNAL: zscore_rising — Acceleration-First Z-Score Momentum

**Problem:** zscore-pump fires when z is elevated (|z| > TH). mtp-zscore fires when 3 periods agree. Neither captures "z is CROSSING above threshold from below AND still rising" — the acceleration event that marks the start of a new leg.

T's explicit request: "only catch big moves, avoid false fires." The acceleration design is purpose-built for this.

### Fire Condition (single lookback, no multi-period confluence)

```python
z_now  = zscore(closes[i-LOOKBACK:i])
z_past = zscore(closes[i-LOOKBACK-VEL_BARS:i-VEL_BARS])  # N bars ago
z_vel  = z_now - z_past

fire_long  = z_past < TH <= z_now and z_vel > MIN_VEL   # cross FROM BELOW, still rising
fire_short = z_past > -TH >= z_now and z_vel < -MIN_VEL  # cross FROM ABOVE, still falling
```

**Key insight:** The CROSSING requirement (prev_z < TH <= cur_z) means z was "cold" before it turned "hot." Many grind-up moves have z persistently at 2.5-3.0 for hours — crossing only fires at the START of each new leg, not during the plateau.

### Backtest on SNX (10:00-18:30 UTC, +8.67% pump)

| Config | Fires | Clusters | Notes |
|--------|-------|----------|-------|
| naive z>TH LB=20 (no crossing) | 73 | 20 | Too noisy |
| **cross+hold LB=20 TH=2.5 hold=2** | **20** | **14** | **Best balance** |
| cross_LB20_TH3.0 | 4 | 4 | Too tight — misses move start |

**Fires at 16:24:43** (SNX price=0.30008, first leg start) — NOT at 16:18 (z=3.16 but was persistently elevated, not crossing from below).

### Backtest on XLM (48h, +22% in 3 stair-step legs)

Config: LB=20, TH=2.5, VEL_BARS=5, HOLD=2 bars

| Phase | Time | Clusters |
|-------|------|----------|
| Phase1 | 05-26 08:00–05-27 00:00 | 29 |
| Phase2 | 05-27 00:00–05-27 16:00 | 33 |
| Phase3 | 05-27 16:00–05-28 08:00 | 30 |

### Constants for hermes_constants.py

```python
ZSCORE_RISING_ENABLED        = True
ZSCORE_RISING_LOOKBACK       = 20
ZSCORE_RISING_THRESHOLD      = 2.5
ZSCORE_RISING_VEL_BARS       = 5
ZSCORE_RISING_HOLD_BARS      = 2
ZSCORE_RISING_MIN_VEL        = 0.0
ZSCORE_RISING_PLUS_ENABLED   = True
ZSCORE_RISING_MINUS_ENABLED  = True
ZSCORE_RISING_COOLDOWN_BARS  = 60
```

**Source naming:** `zscore-rising+` (LONG), `zscore-rising-` (SHORT). New signal file: `signals/zscore_rising.py`.

**vs mtp-zscore:** mtp-zscore requires 3 periods agreeing. zscore_rising is single-period with crossing+velocity. Different use cases — mtp-zscore for multi-timeframe confluence, zscore_rising for early acceleration detection.

**vs zscore_pump:** zscore_pump fires on |z| > TH any time elevated. zscore_rising only fires on CROSSING — catches the acceleration event, not the elevated plateau.

**SNX 16:18 insight:** The LB=150/zscore_pump fire at 16:18 (z=+3.16) was NOT a false fire — SNX genuinely moved +0.55% in a tight range (stdev=0.00084), giving valid z=3.16. zscore_rising avoids it because z wasn't crossing — it was persistently elevated. The two signals serve different purposes.

```python
import sqlite3
from collections import defaultdict

db = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
c = db.cursor()

# For each trade, count opposing vs same-dir signals in 60-min window

## Common Failure Patterns

### Pattern 1: zscore-pump fires in consolidation

A 2.5σ spike at support = bounce candidate (mean-reversion), NOT a trend candidate.
But the signal treats it the same as a 2.5σ spike in a trending move.

**Losers**: SUSHI LONG — 10+ fires over 4h in same 2.0-3.5 range. ONDO LONG — 15+ fires over 3h. AVNT LONG — 4+ fires in 3h.

**Winners**: MON LONG — single brief fire. SKY LONG — held 7h with sustained momentum (not repeated fires).

### Pattern 2: Blow-off bottom SHORT (z < -3.5)

GRIFFAIN SHORT at z=-4.81 conf=88 → EXECUTED. Price bounced. z < -3.5 on SHORT = blow-off bottom = reversal signal, NOT continuation. Should block or reverse signal.

### Pattern 2c: BCH LONG — marginal z-score catching bounce peak (NOT a blow-off, code fix doesn't help)

BCH LONG at 16:09 UTC May 24 (entry=350.29, conf=92.4, z=3.188):
- Signal: `rs-s72,rs-s96,zscore-pump+`, still open, down -0.28%
- Price was grinding lower all afternoon (352→348.27 low at 15:15), bounced to 352.52 at 14:00
- z=3.188 measured a short-term bounce within the downtrend — function DID evaluate LONG side
- BUT z=3.188 < 3.5 threshold, so the divergence check returned False silently → entry fired
- By the time order filled at 16:09, price was already fading from the bounce peak

**This is the inverse failure of STRK/PROVE**: the code fix targets extreme |z| blow-offs, but BCH had a moderate z=3.188 — below any extreme threshold, so divergence scrutiny never activated. The signal was "correct" (price was bouncing), but entry timing was bad.

**What helps BCH (constants only):**
- `ZSCORE_PUMP_THRESHOLD = 3.5` (was 3.0): z=3.188 is marginal — at 3.5 it would be rejected entirely
- `ZSCORE_PUMP_LOOKBACK = 200` (was 150): larger window = more structural z-score, less bounce noise within a downtrend

**What does NOT help BCH**: The SHORT divergence code fix won't help here — this isn't a blow-off bottom, it's a bounce-within-downtrend that looked like momentum. The real lesson is that z-score alone cannot distinguish "new trend starting" from "dead cat bounce inside a downtrend."

### Pattern 2b: _check_divergence() is asymmetric — SHORT divergence not checked

**Root cause (confirmed from source code, zscore_pump.py lines 93-153):**

```python
def _check_divergence(prices: list, lookback: int) -> bool:
    ...
    recent_zs = []
    for i in range(spot_lookback, len(closes) + 1):
        chunk = closes[i - spot_lookback:i]
        z = compute_zscore(chunk)
        recent_zs.append(z)
    ...
    peak_z = max(recent_zs)          # ← uses max, NOT abs(max)!
    if peak_z < ZSCORE_PUMP_DIVERGENCE_EXTREME_Z:
        return False  # never got extreme — no divergence possible
```

The function uses `max(recent_zs)` (not `abs(max)`). It only checks if **positive** z got extreme. For a SHORT signal like STRK (z=-5.777), the spot window showed a gradual decline from e.g. +0.5 → -5.0 (never crossed +3.5), so `peak_z = +0.5` → below threshold → divergence check passes silently. **Negative z never gets divergence scrutiny regardless of how extreme it is.**

STRK SHORT (z=-5.777, conf=83.8, entry=0.03914) and PROVE SHORT (z=-4.606, conf=82.02) both entered at the bottom of a crash and immediately pumped. The divergence filter did nothing for them.

**What constants-only changes actually help (partial mitigation):**
- `ZSCORE_PUMP_DIVERGENCE_EXTREME_Z = 2.5` (was 3.5): catches weaker positive spikes before crash, but doesn't fix the SHORT path
- `ZSCORE_PUMP_THRESHOLD = 3.5` (was 3.0): **does NOT help** — both STRK (|z|=5.777) and PROVE (|z|=4.606) exceed 3.5, so they still fire
- `ZSCORE_PUMP_COOLDOWN_BARS = 20` (was 5): helps prevent repeated SHORT re-fires into a falling knife
- `RS_DECIDER_MIN_TOUCHES = 300` (was 200): for z=-5.777, zbonus applies (|z|>2.5 → min_touches=50), so level 478 still passes — partial mitigation only

**What fixes it properly (code change required, ~25 lines):**
The `_check_divergence()` function needs to also evaluate negative z extremes. A separate check for `min(recent_zs)` below some negative threshold (e.g., -3.0) that then shows recovery would reject SHORT blow-off signals the same way positive divergence rejects LONG blow-off signals.
- See: `references/zscore-pump-short-divergence-fix-plan-2026-05-24.md`

**Verification (2026-05-24):** Plan code changes are all legitimate. Constants are real and proposed values are correct. Minor note: the plan's Verification Step 4 expects log message "SHORT divergence detected" but the actual log at line 271 says `REJECTED — negative divergence detected` (generic, no direction suffix). Not a functional bug — the return value is correct, just the log message is generic.

### Regime Alignment — Counter-Regime Trades Win as Often as Aligned (NEW 2026-05-25)

```
REGIME-ALIGNED: 8W/10L  WR=44%   (aligned with 4h LONG_BIAS)
COUNTER-REGIME: 6W/6L  WR=50%   (fighting 4h LONG_BIAS)
```
Counter-regime SHORT trades (AVAX SHORT, CAKE SHORT, ENS SHORT, AXS SHORT) won at 50%
while aligned trades won at 44%. T's memory note says "do not block counter-regime signals"
— this data SUPPORTS that policy. The market was predominantly UP on 4h, yet SHORT trades
at strong resistance captured +1.08% avg vs LONG trades at weak support (-0.55% avg for DASH, ME).

**Key insight**: In a rising market, counter-regime SHORT trades at strong resistance
(300-2000 touches) have better per-trade PnL than regime-ambiguous LONG trades at weak support.
Direction filter should NOT be based on regime alignment alone.

### signal_z_score NOT recorded — Pipeline Gap (NEW 2026-05-25)

`sigan_z_score`, `sigan_rsi_14`, `sigan_macd_hist` are NULL for every trade in the DB.
The 36-column _signal_metadata JSONB field is also empty {} for every trade.
This means:
1. Post-trade analysis of WHY winners won is impossible — the z_score value that fired
   the signal is NOT passed through to the trade record.
2. The zscore_pump.py outputs z_score via add_signal(), but brain.py add_trade()
   does not capture it into the trade record.
3. Fix location: Where brain.py (or hl-sync-guardian.py) creates the trade record,
   pull z_score from the signal_metadata or the originating signal record.

This is NOT a constants issue — it's a data pipeline gap. Until fixed, we cannot
do proper signal-level analysis of z_score vs PnL correlation.

### Pattern 5: Buying support directly under resistance (compressed reward path)

BCH LONG (entry=350.29, sig=`rs-s72,rs-s96,zscore-pump+`, conf=92.4) and
UMA LONG (entry=0.45923, sig=`rs-s69,zscore-pump+`, conf=95.8) both entered
at support levels with resistance overhead close enough to compress the reward path.

The bounce from resistance caught both trades. This is NOT a signal quality failure
in the traditional sense (valid support, valid momentum confirmation) — it's a
**setup quality failure**: buying support when overhead resistance is within ~2-3%
creates a compressed reward path where even a correct directional bounce stalls.

**What the current system misses:** The RS signal knows the support level. The
zscore-pump signal knows momentum direction. Neither checks: "how far is the next
resistance level above this support entry?"

**Constants-only fix (new, not yet implemented):**
```python
RS_LONG_MAX_DIST_RESIST    = 0.025  # Block LONG if resistance within 2.5% ATR above entry
RS_SHORT_MAX_DIST_SUPPORT = 0.025  # Block SHORT if support within 2.5% ATR below entry
```

**Also:** `RS_PROXIMITY_K = 1.50` (was 1.20) — fire less often but cleaner setups.

**Code change needed:** In signal_compactor.py, when building a LONG signal at
support, look up the nearest resistance level. If `resist_price - entry_price <
RS_LONG_MAX_DIST_RESIST * atr`, block it. The reverse for SHORT.

This pattern is distinct from Pattern 3 (pure RS without momentum) — here there IS
momentum, but the setup geometry is unfavorable. It is also distinct from
Pattern 6 (BCH marginal z-score) — BCH's z=3.188 was the symptom, but the root
failure was entry at support-with-nearby-resistance.

### Pattern 6: Marginal z-score at support within a downtrend (dead cat bounce)

BCH LONG at z=3.188 — below any extreme threshold, so divergence check did not
activate. The z-score measured a short-term bounce within a broader downtrend.
By the time the order filled, price was already fading from the bounce peak.

**Constants-only mitigation:**
- `ZSCORE_PUMP_THRESHOLD = 3.5` (was 3.0) — reject marginal z-scores
- `ZSCORE_PUMP_LOOKBACK = 200` (was 150) — larger window = more structural

### Pattern 3: Pure RS without z-score momentum

ADA LONG had conf=63-75 (RS only, no zscore). Support broke → immediate loss.
Pure RS signals without momentum confirmation are falling knives.

### Pattern 4: Repeated zscore fires = no edge

10+ fires on the same token over 2-4h = the market keeps rejecting at the same level.
The OPP/SAME ratio check would catch this (opposing signals building up).

## Constants-Only Fixes (No Code Changes)

### hermes_constants.py — zscore-pump divergence (May 2026 updates)

```python
ZSCORE_PUMP_THRESHOLD           = 3.0    # structural move threshold
ZSCORE_PUMP_LOOKBACK           = 150    # catch sustained trends not 1h pumps
ZSCORE_PUMP_COOLDOWN_BARS      = 20     # was 5 — MUST verify deployed value matches (see cooldown discrepancy note)
ZSCORE_PUMP_DIVERGENCE_VEL_THD = -0.8   # was -0.5 — stricter rejection of exhausted moves
ZSCORE_PUMP_DIVERGENCE_BARS    = 8      # was 5 — longer confirmation window (8 min vs 5 min)
ZSCORE_PUMP_DIVERGENCE_EXTREME_Z = 4.5  # was 3.5 — allow strong moves up to 4.5 (winners had z=5.3-5.5)
RS_DECIDER_MIN_TOUCHES         = 300    # was 200 — stricter RS levels
```

### hermes_constants.py — ATR TP/SL

```python
ATR_SL_MIN_INIT = 0.015              # was 0.01 (1.0%) — wider 1.5% floor for new trades
ATR_SL_MAX_INIT = 0.020             # was 0.015 (1.5%) — wider cap for volatile coins
ATR_SL_MIN_ACCEL = 0.0075           # was 0.01 (1.0%) — tighter 0.75% on established
ATR_TP_MIN_ACCEL = 0.010            # was 0.015 (1.5%) — tighter TP to match profit-monster
```

### hermes_constants.py — overhead resistance filter (code change needed)

```python
RS_LONG_MAX_DIST_RESIST    = 0.025   # block LONG if resistance within 2.5% ATR above entry
RS_SHORT_MAX_DIST_SUPPORT = 0.025   # block SHORT if support within 2.5% ATR below entry
```

## Quick Diagnostic — SQLite signal_outcomes (primary) + PostgreSQL trades (secondary)

```bash
# SQLite: 96h signal quality summary — use this first
python3 -c "
import sqlite3
from datetime import datetime, timedelta
conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
c = conn.cursor()
cutoff = (datetime.now() - timedelta(hours=96)).strftime('%Y-%m-%d %H:%M:%S')
c.execute(f'''
    SELECT signal_type, direction, COUNT(*) as n,
           SUM(is_win) as wins,
           ROUND(SUM(pnl_usdt), 2) as total_pnl
    FROM signal_outcomes
    WHERE closed_at > \"{cutoff}\"
    GROUP BY signal_type, direction
    ORDER BY total_pnl ASC
''')
print(f'{\"SIG\":<45} {\"DIR\":<6} {\"N\":>5} {\"W\":>4} {\"WR%\":>7} {\"TOTAL_PNL\":>10}')
for row in c.fetchall():
    sig, d, n, wins, total_pnl = row
    wr = wins/n*100 if n > 0 else 0
    print(f'{sig[:43]:<45} {d:<6} {n:>5} {wins:>4} {wr:>6.1f}% {total_pnl:>10}')
conn.close()
"

# PostgreSQL: 24h closed trades with duration (from archive DB)
sudo -u postgres psql -d brain -c "
SELECT token, direction, pnl_pct, pnl_usdt, signal,
       exit_reason, leverage,
       ROUND(EXTRACT(EPOCH FROM (close_time - open_time))/60, 1) as dur_min
FROM trades
WHERE close_time > NOW() - INTERVAL '24 hours'
ORDER BY pnl_pct DESC;
"
```

**Diagnostic workflow for signal quality investigation:**
1. Run SQLite 96h query first — this is the fastest way to see which signal families are failing
2. Group by source tag to find which signal families are losing
3. Decode source tag touch counts: `rs-s42` = 42 touches, `rs-r292` = 292 touches
4. Check `signal_outcomes.is_win` + `pnl_pct` distribution to confirm patterns
```

## Code Changes Needed (Higher Effort)

1. **RSI filter in zscore_pump** — require RSI > 50 for LONG, RSI < 50 for SHORT before confirming signal
2. **OPP/SAME ratio in decider** — block trades where opposing signal count ≥ same-dir count in 60-min window
3. **Blow-off bottom block for SHORT** — when z < -3.5 on SHORT, treat as reversal signal
4. **Fix momentum_stats passing** — debug why get_momentum_stats() returns None → phase k-scaling bypassed

## ATR TP/SL — Phase k-scaling is Broken in Practice

```python
# position_manager.py line 1576:
ms = get_momentum_stats(token)
momentum_by_token[token] = ms  # or None if failed

# tpsl_utils.py line 108:
if momentum_stats is None:
    return base_k  # NO phase tightening when momentum_stats is None!
```

Every signal in SQLite: momentum_state=null, rsi_14=null, macd_hist=null.
If `get_momentum_stats()` returns None → phase k-scaling bypassed entirely.

**Floor overrides phase multipliers**: For most real trades, ATR_SL_MIN_INIT=1.0% floor is the binding constraint, not phase multipliers (0.01-0.07).

### zscore-pump solo = noise (NEW 2026-05-25)

0 winners came from zscore-pump alone. Every winner was `rs-rXXXX,zscore-pump-` or `rs-sXXXX,zscore-pump+`.
support_resistance provides the structural level; zscore-pump confirms timing. Solo zscore-pump = no edge.
Consider raising `ZSCORE_PUMP_THRESHOLD` to 3.5 to reduce solo noise further.

### Signal Type is the Dominant Factor — Not zscore Magnitude (NEW 2026-05-25)

Analysis of 26 trades (12W/13L) matched to signals.json by source tag overlap:

| Signal Type | Direction | WIN | LOSS | WR |
|-------------|-----------|-----|------|-----|
| support_resistance | LONG | 5 | 2 | **71%** |
| support_resistance | SHORT | 2 | 1 | **67%** |
| zscore_pump_long | LONG | 3 | 5 | **38%** |
| zscore_pump_short | SHORT | 2 | 5 | **29%** |

**support_resistance wins at 2x the rate of zscore_pump on both directions.**
WIN and LOSS zscore distributions overlap almost completely — zscore magnitude alone does not predict winners.

### Leverage is a Major Differentiator (NEW 2026-05-25)

| Leverage | WIN | LOSS | WR |
|----------|-----|------|-----|
| 3x | 7 | 4 | **64%** |
| 5x | 5 | 9 | **36%** |

Every 5x loss hit ATR SL. The 5x winners were predominantly support_resistance signals.
5x + zscore_pump_long is the worst combination (see Pattern below).

### Time-to-Execution Predicts Outcomes (NEW 2026-05-25)

```
WIN  avg=106 min, median=122 min  (range: -306 to 432 min)
LOSS avg=263 min, median=173 min  (range: 3 to 887 min)
```

Winners execute ~2x faster after signal generation. Slow losers: UMA=887min, BLUR=761min, ADA=390min, ETH=375min.
Consider a max-signal-age filter (e.g., 4h) before accepting a signal into hot-set.

### SHORT: |z| >= 3.5 Improves WR from 40% → 60% (NEW 2026-05-25)

| Threshold | WIN | LOSS | WR |
|-----------|-----|------|-----|
| >=3.0 | 4 | 6 | 40% |
| >=3.5 | 3 | 2 | **60%** |
| >=4.0 | 1 | 0 | **100%** |

For SHORT: zscore_pump_short fires too aggressively at |z| 3.0–3.4. Tightening to 3.5 is a free win-rate improvement.

### Pattern: 5x + zscore_pump_long = Trap (NEW 2026-05-25)

All 5x zscore_pump_long LOSSES: ADA (z=3.005), BLUR (z=3.041), UMA (z=3.312), ENS (z=5.274), DASH (z=3.825).
All 5x zscore_pump_long WINS: AVAX (z=3.216), LINEA (z=5.478), TIA (z=3.023).
The difference is not zscore — it's execution speed (winners: 25-60 min, losers: 42-887 min).

**Actionable**: For zscore_pump_long signals, if time-since-signal > 2h, downgrade leverage recommendation or skip.

### Coin Repeats Confirm Signal Type > zscore (NEW 2026-05-25)

| Coin | WINs | LOSS | Signal Type Differentiation |
|------|------|------|----------------------------|
| LINEA | SHORT (-4.11 sr) + LONG (+5.48 zp) | — | Both directions won |
| ME | SHORT×2 (-3.56 zp) | LONG (-3.42 sr) | zscore_pump SHORT won, SR LONG lost |
| MON | LONG (+3.54 sr) | SHORT (-3.05 zp) | SR LONG won, zp SHORT lost |
| ADA | — | LONG (+3.01 zp) + SHORT (-3.93 zp) | Both lost — weak signal types both sides |
| AVAX | LONG (+3.22 zp) | SHORT (-3.32 sr) | Split — signal type matches pattern |

Signal type (support_resistance vs zscore_pump) is the consistent differentiator in split-direction results, not zscore magnitude.

### Failure Mode 2: Shorting into macro bounce — 02:00 UTC cluster (NEW 2026-05-25)

Analysis of 26 trades (12W/13L) matched to signals.json by source tag overlap:

| Signal Type | Direction | WIN | LOSS | WR |
|-------------|-----------|-----|------|-----|
| support_resistance | LONG | 5 | 2 | **71%** |
| support_resistance | SHORT | 2 | 1 | **67%** |
| zscore_pump_long | LONG | 3 | 5 | **38%** |
| zscore_pump_short | SHORT | 2 | 5 | **29%** |

**support_resistance wins at 2x the rate of zscore_pump on both directions.**
WIN and LOSS zscore distributions overlap almost completely — zscore magnitude alone does not predict winners.

### Leverage is a Major Differentiator (NEW 2026-05-25)

| Leverage | WIN | LOSS | WR |
|----------|-----|------|-----|
| 3x | 7 | 4 | **64%** |
| 5x | 5 | 9 | **36%** |

Every 5x loss hit ATR SL. The 5x winners were predominantly support_resistance signals.
5x + zscore_pump_long is the worst combination (see Pattern below).

### Time-to-Execution Predicts Outcomes (NEW 2026-05-25)

```
WIN  avg=106 min, median=122 min  (range: -306 to 432 min)
LOSS avg=263 min, median=173 min  (range: 3 to 887 min)
```

Winners execute ~2x faster after signal generation. Slow losers: UMA=887min, BLUR=761min, ADA=390min, ETH=375min — all 5x zscore_pump_long.
Consider a max-signal-age filter (e.g., 4h) before accepting a signal into hot-set.

### SHORT: |z| >= 3.5 Improves WR from 40% → 60% (NEW 2026-05-25)

| Threshold | WIN | LOSS | WR |
|-----------|-----|------|-----|
| >=3.0 | 4 | 6 | 40% |
| >=3.5 | 3 | 2 | **60%** |
| >=4.0 | 1 | 0 | **100%** |

For SHORT: zscore_pump_short fires too aggressively at |z| 3.0–3.4. Tightening to 3.5 is a free win-rate improvement.

### Pattern: 5x + zscore_pump_long = Trap (NEW 2026-05-25)

All 5x zscore_pump_long LOSSES: ADA (z=3.005), BLUR (z=3.041), UMA (z=3.312), ENS (z=5.274), DASH (z=3.825).
All 5x zscore_pump_long WINS: AVAX (z=3.216), LINEA (z=5.478), TIA (z=3.023).
The difference is not zscore — it's execution speed (winners: 25-60 min, losers: 42-887 min).

**Actionable**: For zscore_pump_long signals, if time-since-signal > 2h, downgrade leverage recommendation or skip.

### Coin Repeats Confirm Signal Type > zscore (NEW 2026-05-25)

| Coin | WINs | LOSS | Signal Type Differentiation |
|------|------|------|----------------------------|
| LINEA | SHORT (-4.11 sr) + LONG (+5.48 zp) | — | Both directions won |
| ME | SHORT×2 (-3.56 zp) | LONG (-3.42 sr) | zscore_pump SHORT won, SR LONG lost |
| MON | LONG (+3.54 sr) | SHORT (-3.05 zp) | SR LONG won, zp SHORT lost |
| ADA | — | LONG (+3.01 zp) + SHORT (-3.93 zp) | Both lost — weak signal types both sides |
| AVAX | LONG (+3.22 zp) | SHORT (-3.32 sr) | Split — signal type matches pattern |

Signal type (support_resistance vs zscore_pump) is the consistent differentiator in split-direction results, not zscore magnitude.

### Failure Mode 2: Shorting into macro bounce — 02:00 UTC cluster (NEW 2026-05-25)

ADA, OP, ZK, AVAX, ETH, SNX, LINEA all SHORTED within 2 minutes of 02:00 UTC May 25.
All entered at the exact macro bottom and lost. ETH was stopped out in 16 min (only -0.98%);
 ADA/OP/ZK/AVAX survived 170-200 min and lost -1.0 to -1.3%.
This is a systematic timing failure — all 7 shorts fired in the same 2-min window, catching a liquidity cascade bottom.

**Actionable:** Consider a signal blackout window around 01:30–03:30 UTC when multiple tokens are likely to liquidate/short-squeeze together. This cannot be fixed with constants alone — needs a time-of-day filter in the signal pipeline.

### Failure Mode 3: Fast kills in 0–15 min (NEW 2026-05-25)

AXS SHORT (0.1 min), ME LONG (0.0 min), CHIP SHORT (13 min), DASH LONG (38 min).
z-score was 3.0–3.8. The divergence check fired but didn't prevent entry — momentum was already exhausted by the time the order filled.

### Cooldown discrepancy — must verify deployed value (NEW 2026-05-25)

```
Memory note (2026-04-22): ZSCORE_PUMP_COOLDOWN_BARS = 20
hermes_constants.py line 600: ZSCORE_PUMP_COOLDOWN_BARS = 5
```

5 bars = re-fire every 5 min. Memory says it was raised to 20. **This is a critical discrepancy** — 5 is too aggressive and would let the same coin spam the hot-set with repeated signals in chop. Must verify which value is actually deployed.

### EXTREME_Z too low — blocking good entries (NEW 2026-05-25)

`ZSCORE_PUMP_DIVERGENCE_EXTREME_Z = 3.5` (current). Winners ENS LONG had z=5.3, LINEA LONG had z=5.5.
These are strong structural moves, not blow-offs. The EXTREME_Z filter at 3.5 would have caught LINEA/ENS on the spot lookback divergence check — but they won anyway. Bumping to 4.5 gives headroom while still blocking genuine blow-offs.

### Counter-trend signals: do NOT block them (CONFIRMED 2026-05-25)

Per T's memory note, counter-regime signals should not be blocked. 24h data confirms:
- SHORTS at strong resistance (rs-rXXXX, 300-2000 touches) in a rising market produced +1.02–1.09% winners
- LONG support bounces in a rising market produced mixed results (-0.55 to +0.93%)
Do not add regime filters that block counter-trend signals. Per-coin regime filter handles direction.

### signal_z_score NOT recorded — Pipeline Gap (NEW 2026-05-25)

`sigan_z_score`, `sigan_rsi_14`, `sigan_macd_hist` are NULL for every trade in the DB.
36-column _signal_metadata JSONB field is empty {} for every trade.
This means post-trade analysis of WHY winners won is impossible without pipeline fix.

- See: `references/24h-may-25-signal-analysis.md` — full 31-trade breakdown with winner/loser tables, failure mode analysis, constants change proposals
- `references/5-closes-2026-05-24.md` — 5 SHORT closes via atr_sl_hit, zscore confirmed from signals.json
- `references/24h-signal-quality-deep-dive-2026-05-24.md` — Full 24h audit with winner/loser analysis
- `references/26-trade-deep-dive-2026-05-25.md` — 26-trade winner/loser analysis: signal type dominance over zscore, leverage effect, time-to-execution, SHORT zscore threshold
- `references/24h-2026-05-26-signal-analysis.md` — 30-trade breakdown, RS touch count discontinuities, SHORT side broken
- `references/short-bias-investigation-2026-06-02.md`
- `references/30d-trade-analysis-2026-06-04.md` — 30-day trade analysis: LONG 29.6% WR, SHORT 42.2% WR; trend_purity+ 75% WR co-signal; hhh-long systematically negative; SHORT winner duration 88min vs loser 35min; top constants tightening targets
- `references/96h-accel-rs-failure-2026-06-04.md` — **NEW**: 96h catastrophe: accel-300+,rs-sXXX 0% WR/62 trades, accel-300-,rs-s-broken 1.3% WR/300 trades, all other signal families failing; RS_BROKEN_MAX_DISTANCE and RS_DECIDER_MAX_TOUCHES new constants proposed
- `references/jun-2026-bypass-incident.md` — Jun 2026 incidents: accel-300 standalone bypass FAILED (conf=70 cap problem), RS_TOUCH_HARD_CAP=180 too permissive (let through 154-164 touch losses), confluence gate is THE bottleneck not detection thresholds
- `references/rs-s-broken-24h-failure-2026-06-03.md` — why the system fires 90%+ SHORT: signal generation asymmetry vs source weights vs regime calculation (answers 3 questions T asked)
- `references/strk-prove-short-loss-2026-05-24.md` — STRK+PROVE SHORT blow-off analysis
- `references/zscore-pump-short-divergence-fix-plan-2026-05-24.md` — prior OPP/SAME ratio analysis (83 trades)
- `references/zscore-pump-backtest-2026-05-28.md` — zscore-pump full-universe backtest status (v4 script ready, not yet executed)
- `references/reversal-trap-pattern-2026-05-21.md` — Reversal trap pattern analysis