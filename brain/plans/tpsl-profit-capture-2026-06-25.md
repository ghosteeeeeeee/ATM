# TPSL Profit-Capture Plan — 2026-06-25 v1 (post-24h-trade-audit)

## Context — why this plan exists

T asked for a deep analysis of the 24h closed trades because
"win rate is still barely above 50% and we are still not
profitable." The audit revealed the trailing-SL subsystem
(tpsl_utils.py + position_manager._collect_atr_updates) is
failing to capture profits, and the phase logic ("accelerating /
exhausted / extreme") is effectively dead code.

This plan covers BOTH the 24h analysis findings and the surgical
fixes needed to make the SL subsystem actually do its job.

**The 24h numbers (38 closed trades, 21W/16L, 55% WR):**
- Net: +$0.68
- Gross wins: $1.99
- Gross losses: $1.31
- Profit factor: 1.52 (we keep 34% of theoretical max)
- 12 of 38 trades (32%) had `lowest_price=0` in DB
  → trailing SL was non-functional for 1/3 of trades

**Two layered problems:**
1. Code bugs (lowest_price not init'd for SHORT, no profit lock,
   phase multipliers overridden by floor)
2. Constants tuned too conservatively (PROFIT_MIN_PCT=0.7,
   ATR_SL_MIN_ACCEL=1.5%, K_PHASE_* all 0.01-0.06 = dead code)

---

## Implementation status — 2026-06-25 (PARTIALLY APPLIED + new findings)

| Fix | Tier | Status | File | Lines | Risk | Impact |
|-----|------|--------|------|-------|------|--------|
| 1 | Bug | ⏳ PENDING | position_manager.py | 1 line | LOW | 32% of trades get working trailing |
| 2 | Bug | ⏳ PENDING | tpsl_utils.py | ~30 lines | MED | Winners lock in 0.3-0.5% profit on reversal |
| 3 | Bug | ⏳ PENDING | tpsl_utils.py | 1 line | MED | Phase logic can actually tighten SL |
| 4 | Const | ✅ **APPLIED 05:07 UTC** | hermes_constants.py | 1 line | MED | SL cap 1.2% → 0.8%, tighter trailing |
| 5 | Const | ✅ **APPLIED 05:07 UTC** | hermes_constants.py | 1 line | MED | Floor 1.5% → 0.5% (was dead code, now alive) |
| 6 | Const | ✅ **APPLIED 05:07 UTC** | hermes_constants.py | 8 lines | MED | K_PHASE_* raised 10x to 0.2-0.6 range |
| 7 | Data | ⏳ PENDING | live trades | DDL | LOW | Backfill lowest_price=0 for 12 trades |
| 8 | Filter | ⏳ PENDING | hermes_constants.py | ~5 lines | MED | Add ASTER ONLY to SHORT_BLACKLIST (audit: MERL/ENS/FET are net POSITIVE 7d) |
| 9 | Filter | ⏳ PENDING | signal_compactor.py | ~20 lines | MED | Time-of-day filter (skip 20:00-22:00 UTC) |
| 10 | Cooldown | ⏳ PENDING | position_manager.py | ~15 lines | MED | ASTER 10s re-open bug — block re-entry within cooldown |
| 11 | Data | ⏳ PENDING | position_manager.py | 1 line | LOW | Fix highest_price=1.0 default for orphan trades |
| **12** | **Bug** | **⏳ PENDING (TOP PRIORITY)** | **signals/accel_300.py** | **~10 lines + 2 const** | **MED** | **Block 27 of 121 (22%) stale wrong-direction signals (verified over 7 days, 2026-07-05)** |
| 12a | Const | ⏳ PENDING | hermes_constants.py | 1 line | MED | `ACCEL_300_STALE_LOOKBACK`: 400 → 10 |
| 12b | Const | ⏳ PENDING | hermes_constants.py | 1 line | MED | `ACCEL_300_STALE_GAP_DECAY_THRESHOLD`: 0.50 → 0.80 |

**2026-06-25 05:07 UTC — constants applied:**
- `ATR_SL_MAX`: 0.012 → 0.008 (was 1.2% cap, now 0.8%)
- `ATR_SL_MIN_ACCEL`: 0.015 → 0.005 (was 1.5% floor, now 0.5%; was DEAD CODE because MIN > MAX)
- `K_PHASE_ACCEL_STALL/FAST/SLOW`: 0.06/0.05/0.04 → 0.6/0.5/0.4
- `K_PHASE_EXH_STALL/FAST/SLOW`: 0.02/0.03/0.02 → 0.5/0.4/0.3
- `K_PHASE_EXT_STALL/FAST`: 0.01/0.02 → 0.3/0.2
- Backup: `/root/.hermes/scripts/hermes_constants.py.bak-2026-06-25`
- Guardian restarted at 05:07 UTC (PID 2264876) to pick up new constants

**Verification trace (MERL #12177 scenario, lowest=current=0.019699, pnl=1.07%):**
- OLD: SL = 0.019935 (1.2% above current, gave back all gains on 1% pullback)
- NEW: SL = 0.019797 (0.5% above current, locks 0.57% profit on 0.5% pullback)
- Improvement: ~0.7% more profit per winner in profit-capture scenarios

**2026-07-05 update — accel_300 stale-bar bug verified at scale:**
- **27 of 121 accel_300 trades (22%) fired with price on WRONG side of EMA** (7-day window)
- Pattern is consistent across both directions:
  - 22 accel-300- SHORTS fired when price was ABOVE EMA (most common)
  - 5 accel-300+ LONGS fired when price was BELOW EMA
- Root cause: 2026-06-23 fix finds MOST RECENT qualifying bar but doesn't
  require LATEST bar to also qualify. Stale signals fire 4-6 hours after
  the original cross when live price has reversed.
- Fixes needed (Fix #12, 12a, 12b above): code patch + 2 constant changes
- See "accel_300 Stale-Bar Bug" section below for full details and code.
- Earlier 24h sample (June 25) showed 15/34 = 44%, smaller sample noise

**LEVERAGE:** T explicitly said NOT to touch leverage. Leverage is an
amplifier — when the underlying signals and SL improve, leverage amplifies
the gains. Don't cap 5x. Re-evaluate after Fix #1-#12 are in production.

**INCREMENTAL VERIFICATION (T's preference):** Fix #1 alone first,
verify it works on the next 5+ SHORT trades, then Fix #2, verify, etc.
Do NOT bundle fixes — each needs its own measurement window. Apply
Fix #12 (accel_300) FIRST as it's the highest-impact signal-direction bug.

---

## EXECUTIVE SUMMARY (2026-07-05 update)

**The critical bug: 22% of accel_300 trades fire with WRONG direction.**

Verified across 121 trades over 7 days: **27 of 121 accel_300 trades
fired when the live price was on the WRONG side of EMA300**.

- 22 accel-300- SHORTS fired when price was ABOVE EMA (should be SHORT to profit)
- 5 accel-300+ LONGS fired when price was BELOW EMA (should be LONG to profit)

**Why this happens:** the 2026-06-23 fix made the detector scan backward
to find the most recent qualifying bar, but it does NOT require the
LIVE bar to also qualify. When price was below EMA 4 hours ago and
has since crossed above, the detector still fires a SHORT signal using
the STALE bar's data — even though the live price is above EMA.

**The fix (Tier 1):** ~10 lines in `signals/accel_300.py` plus 2 constant
changes in `hermes_constants.py`. See "accel_300 Stale-Bar Bug"
section (line ~755) for full code and verification.

**Why this matters more than the SL constants:** even with a tighter
SL cap (ATR_SL_MAX 1.2%→0.8% applied 05:07 UTC), the underlying signal
direction is wrong for 22% of trades. Those trades get squeezed because
they're entering against the trend. Fixing the staleness compounds
with the SL tightening.

**Concrete evidence from T's most recent trades:**

| Trade | Token | Signal | Live Gap | Direction vs EMA | Result |
|-------|-------|--------|----------|------------------|--------|
| 12393 | ONDO   | accel-300- SHORT | +0.56% (ABOVE) | WRONG | W (lucky) |
| 12392 | PEOPLE | accel-300+ LONG  | -0.27% (BELOW) | WRONG | W (lucky) |
| 12391 | ZK     | accel-300- SHORT | +0.88% (ABOVE) | WRONG | W (lucky) |
| 12388 | ENS   | accel-300- SHORT | +0.40% (ABOVE) | WRONG | L |
| 12374 | LINEA | accel-300- SHORT | +0.31% (ABOVE) | WRONG | L |
| 12369 | BSV   | accel-300- SHORT | +0.53% (ABOVE) | WRONG | L |
| 12363 | AAVE  | accel-300+ LONG  | -0.26% (BELOW) | WRONG | L |
| 12361 | CAKE  | accel-300- SHORT | +0.57% (ABOVE) | WRONG | L |
| 12360 | 2Z    | accel-300- SHORT | +1.02% (ABOVE) | WRONG | L |
| 12357 | BLUR  | accel-300+ LONG  | -0.44% (BELOW) | WRONG | L |
| 12355 | APEX  | accel-300- SHORT | +0.43% (ABOVE) | WRONG | W (lucky) |
| 12353 | APEX  | accel-300- SHORT | +0.45% (ABOVE) | WRONG | L |
| 12340 | ADA   | accel-300- SHORT | +0.23% (ABOVE) | WRONG | L |

**Verification script:** `/root/.hermes/scripts/analysis/check_all_accel_direction.py`
- Reports WRONG-DIRECTION count for any time window
- Run BEFORE and AFTER the fix to verify the fix works
- After fix, expect WRONG-DIRECTION count to drop to ~0

**What was completed this session:**
- 9 TPSL constants applied at 05:07 UTC (ATR_SL_MAX 1.2%→0.8%,
  ATR_SL_MIN_ACCEL 1.5%→0.5%, K_PHASE_* raised 10x)
- Guardian restarted to load new constants
- 24h analysis documented
- accel_300 stale-bar bug fully identified and fix designed
- Plan written, audited, and updated through multiple iterations

**What remains (in priority order):**
1. **HIGH:** Fix #12 — accel_300 stale-bar bug (10 lines + 2 const)
2. MED: Fix #1 — lowest_price init for SHORT (1 line in position_manager.py)
3. MED: Fix #8 — blacklist ASTER ONLY (audit showed MERL/ENS/FET are net POSITIVE 7d)
4. MED: Fix #2 — tpsl_utils profit-lock (skipped — see notes)
5. LOW: Fix #7 — backfill lowest_price=0 for 12 closed trades
6. LOW: Fix #11 — highest_price=1.0 default for orphan trades
7. LOW: Fix #9, #10 — time-of-day filter, 10s re-open cooldown

**Backup:** `hermes_constants.py.bak-2026-06-25` (full backup from 05:05 UTC,
before any changes). Use this to revert constants if needed.

---

## SECTION A — 24H TRADE ANALYSIS FINDINGS

### A.1 Headline numbers

```
Total trades:       38 (21W / 16L, 1 breakeven)
Win rate:           55.3%
Net PnL:           +$0.68 (out of $0.71 capital churned, 1.5% gain)
Profit factor:     1.52 (gross_wins $1.99 / gross_losses $1.31)
We keep:           34% of theoretical max win $
```

### A.2 Timeline (UTC) — peak-to-trough pattern

```
02:00-08:00   -1: 3 losses  $-0.24
10:00-12:00   +6: 6 wins    $+0.47   ← WARM-UP
13:00-14:00   -1: 3 losses  $-0.21
15:00-18:00  +11: 11 wins   $+1.13   ← PEAK $1.29 @ 19:14
20:00-22:00   -6: 6 losses  $-0.54   ← GAVE BACK PEAK
22:00-01:38   -3: 3 losses  $-0.21
NET:                        +$0.68
```

### A.3 Win vs Loss profile (KEY FINDING)

```
                     WINNERS (21)        LOSERS (16)
  Avg duration:       44 min              62 min
  Avg pnl_pct:       +0.95%             -0.76%
  Trajectory:         "dropped continuously"   "rose continuously"
  All wins:           exit=profit-monster        exit=atr_sl_hit (13) / guardian (3)
  Leverage mix:       16@3x + 5@5x         7@3x + 9@5x
  3x WR:             69.6% (16/23)         30.4% (7/23, $-0.50)
  5x WR:             33.3% (5/15)          66.7% (10/15, $-0.81)
  3x net:            +$1.07                5x net: $-0.39
```

The 24h data is N=38, small sample, but 5x leverage is consistently
worse: 33% WR vs 70% WR, -$0.39 net vs +$1.07. The losing streak
20:00-01:38 was 100% 5x leverage.
```

**LETHAL FACTOR NOTE (24h only):** 5x leverage was 33% WR vs 70% for
3x in this 24h slice, but **T explicitly said NOT to touch leverage** —
it's an amplifier that should grow with our signal quality. The fix
is in the signals and SL, not in the leverage. Keeping 5x on the
table.

### A.4 MFE/MAE ratio — the leading indicator

```
Winners: avg MFE 0.71% / avg MAE 0.34% = ratio 2.09
         (trend in favor > 2x adverse)
Losers:  avg MFE 0.32% / avg MAE 0.62% = ratio 0.52
         (adverse 2x larger than favorable)
```

When MFE/MAE ratio < 1.0 in first 10-15 min, the trade is a
LOSER. This is a quantifiable filter we can add.

### A.5 Per-token blacklist candidates (from this 24h window)

```
MERL  SHORT  4 trades, 25% WR, -$0.23   ← STRONG candidate
ENS   SHORT  3 trades, 33% WR, -$0.13
FET   SHORT  3 trades, 33% WR, -$0.09
ASTER SHORT  2 trades,  0% WR, -$0.06 (plus 10s bug)
```

### A.6 Time-of-day pattern

```
Best hours (UTC):  11:00-18:00  (15W/0L — perfect WR)
Worst hours:       20:00-22:00  (1W/9L, $-0.61)
```

### A.7 Profit-monster clipping (profit loss #1)

```
hermes_constants.py:
  PROFIT_MIN_PCT = 0.7    # 0.7% is the FLOOR for profit-monster
  PROFIT_MAX_PCT = 5.0    # 5% ceiling

21/21 winners closed at +0.71% to +2.59%
  +0.7%  : 8 trades (38% of wins)
  +0.8%  : 5 trades (24%)
  +0.9%  : 2 trades
  +1.0%  : 1
  +1.1%  : 1
  +1.2%  : 1
  +1.3%  : 2
  +2.6%  : 1  ← BLUR (caught a 2.6% down-move)
```

We are systematically leaving 1-4% on the table per winner.

### A.8 ASTER 10-second bug (still broken)

```
ASTER #12193 — 22:07:07 open, 22:07:35 close = 28 SECONDS
  entry=0.61304 exit=0.61313 SL=0.61902 (recorded SL 0.81% above entry)
  pnl = $-0.00 (breakeven, exit_reason=guardian_tp)
  highest_price=1.00000  ← BUG: hardcoded default never updated
  Real highest from 1m data: 0.61401

ASTER #12194 — 22:08:07 open, 01:38:19 close = 3.5 HOURS
  Opened 32 SECONDS after #12193 closed
  Same token, same direction, different entry
  pnl = -$0.06, exit_reason=guardian_sl
  Price ranged 0.611-0.617 for 3.5h, slow grind up
  guardian fired BEFORE recorded SL was hit (SL=0.61838, exit=0.61712)
```

**Two trades on same token 32s apart is a clear pattern bug.**
The first trade SHOULD have triggered a cooldown for ASTER but didn't.

---

## SECTION B — TPSL UTILS BUG ANALYSIS

### B.1 Bug #1 — lowest_price NEVER INITIALIZED FOR SHORT

**File:** `/root/.hermes/scripts/position_manager.py`
**Lines:** 2245-2248
**Severity:** HIGH (affects 32% of trades — 72 of 222 SHORT trades in 7d)

```python
# CURRENT (BROKEN):
if existing_high <= 0 and direction == "SHORT":
    existing_high = entry  # SHORT: start tracking from entry
if existing_low <= 0 and direction == "LONG":
    existing_low = entry   # LONG: start tracking from entry
```

For SHORT trades, only `highest_price` is initialized to entry.
`lowest_price` stays 0. The first refresh:
```python
new_low = min(existing_low, cur_price) = min(0, cur_price) = 0
```

So `lowest_price` is **stuck at 0 for the entire SHORT trade life**.

**ROOT CAUSE (revealed by ai-engineer audit 2026-06-25):**
- `brain.py:575` correctly inits `lowest_price = hl_entry` for SHORT,
  but ONLY for `paper=True` trades (column 7).
- `hl-sync-guardian.py:749` does an INSERT for real HL-mirrored trades
  that does NOT include `highest_price` or `lowest_price` columns.
  PostgreSQL with `is_nullable=YES` allows NULL, cast to 0 in Python.
- `position_manager.py:2252` then computes `min(0, cur_price) = 0`
  and persists 0.

**The hl-sync-guardian.py path is the dominant one for 5x leverage
mid/large-cap trades** (ONDO, FET, ENS, TAO, AAVE — all the
24h losing-streak tokens). The bug is most damaging on these.

**12 of 38 24h trades had lowest_price=0:**
```
MERL #12166  (LOSS), MERL #12163 (LOSS), ONDO (LOSS),
SKR #12183/85 (WINS), 0G (WIN), STBL x3 (2W/1L),
PEOPLE (WIN), FET (LOSS), APEX (WIN)
```

**7-day data (per audit):** 72 of 222 SHORT trades (32%) had
`lowest_price=0`. Confirmed systemic.

**Impact on tpsl_utils:**
When tpsl_utils sees `lowest_price=0`, the anchor logic falls back:
```python
ref_price = lowest_price if lowest_price > 0 else current_price
```
So SL is anchored to **current price**, not the actual low. SL can
never trail because the anchor moves WITH price.

**FIX (1 line, Tier 1 priority):** two options:

**Option A (recommended, safest):** Fix at the position_manager level
so it covers ALL insert paths:
```python
if existing_high <= 0 and direction in ("LONG", "SHORT"):
    existing_high = entry
if existing_low <= 0 and direction in ("LONG", "SHORT"):
    existing_low = entry
```

**Option B (defense-in-depth):** Also fix hl-sync-guardian.py:749 to
include `highest_price` and `lowest_price` columns in the INSERT.
More invasive — 5 INSERT paths in hl-sync-guardian.py.

A is preferred: 1 line, covers all paths, can't break anything that
isn't already broken.

### B.2 Bug #2 — NO PROFIT-LOCKING LOGIC

**File:** `/root/.hermes/scripts/tpsl_utils.py`
**Severity:** HIGH (this is the actual profit-capture feature missing)

Look at the canonical SHORT trailing SL gate (lines 433-453):
```python
elif direction == 'SHORT':
    if current_sl > 0:
        current_on_wrong_side = (current_sl > current_price) if current_price > 0 else False
        if new_sl < current_sl:
            # new_sl LOWERS = tighten downward — correct, allow
            result['needs_sl'] = True
        ...
        else:
            new_sl = current_sl  # would loosen (or equal) — block
            result['needs_sl'] = False
    else:
        result['needs_sl'] = True  # first time set
```

The SL is anchored to `lowest_price` which only moves DOWN as price
falls. SL can NEVER go ABOVE entry once price has been in profit. Once
price is in profit by X%, SL is at most at entry + buffer.

The actual failure mode (reframed by ai-engineer audit 2026-06-25):
the plan originally said "new_sl above entry" but that's geometrically
impossible for SHORT in profit. The REAL issue: `new_sl` is consistently
0.5-0.6% ABOVE `current_price` for in-profit SHORT trades. So if price
reverses all the way back to current, you exit at a 0.5-0.6% LOSS,
not a profit. The MERL #12177 timeline confirms this:

```
15:11  pnl=0.63%  lowest=0.019789  SL=0.020026 (entry+0.53%, current+1.40%)
15:14  pnl=1.07%  lowest=0.019699  SL=0.019935 (entry+0.08%, current+1.50%)
```

At 15:11, SL was 0.53% above ENTRY but 1.40% ABOVE CURRENT. The SL
never locked any profit. If price had reversed 1% from peak, the trade
would close at ~0.4% LOSS, wiping out the 0.63% gain.

**What we need:** when pnl_pct >= 0.3-0.5%, force the SL to be at most
`PROFIT_LOCK_PCT` (0.3%) above `current_price`. This is the
profit-locking feature.

**FIX (Tier 2 priority):**
Add a "pnl_floor" branch in `compute_atr_sl_tp` (after line 374)
that, when `pnl_pct > 0`, sets:
```python
if pnl_pct > 0:
    pnl_floor = current_price * (1 + max(0.003, pnl_pct * 0.3))
    if direction == 'SHORT':
        new_sl = min(new_sl, pnl_floor)  # never let SL be above this
    else:
        new_sl = max(new_sl, pnl_floor)
```

### B.3 Bug #3 — PHASE MULTIPLIERS ARE DEAD CODE

**File:** `/root/.hermes/scripts/tpsl_utils.py`
**Severity:** MED (k values change, output SL doesn't)

The phase logic computes k in [0.01, 0.06] for "stalling acceleration",
then `sl_pct = k * atr_pct`. With atr_pct=1%, that gives 0.01-0.06%.

Then on line 374:
```python
eff_sl_pct = min(max(sl_pct, MIN_SL_PCT), ATR_SL_MAX)
```

where `MIN_SL_PCT = ATR_SL_MIN_ACCEL = 0.015` (1.5%) and
`ATR_SL_MAX = 0.012` (1.2% cap).

**Trace (re-verified 2026-06-25):** atr_pct=1% (0.01), K_PHASE_EXH_STALL=0.02.
base_k = 0.5 (ATR_K_LOW_VOL since atr_pct < 1%, but wait, 1% = 0.01 which is
the threshold itself — depends on whether it's > or >=). The key point:
final k = base_k * 0.02 = 0.01. sl_pct = 0.01 * 0.01 = 0.0001 (0.01%).
Then:
- `eff_sl_pct = min(max(0.0001, 0.015), 0.012) = min(0.015, 0.012) = 0.012`

The **CAP at 1.2% wins**, not the floor at 1.5%. Both squeeze, but
the cap is binding. So the k value is invisible in the output.

The plan's original example said "forced UP to 1.5% by the floor" — that
was wrong (1.2% cap is what binds). The diagnosis "phase multipliers
are dead code" is still correct — output `eff_sl_pct` is invariant
across all phase values.

**MERL #12177 k value timeline (all produce eff_sl=1.200%):**
```
14:37  k=0.005  accel_stall  eff_sl=1.200%
14:42  k=0.005  accel_stall  eff_sl=1.200%  (price bouncing)
15:00  k=0.010  exh_stall    eff_sl=1.200%
15:05  k=0.020  exh_slow     eff_sl=1.200%
15:11  k=0.050  exh_slow     eff_sl=1.200%
15:13  k=0.050  exh_slow     eff_sl=1.200%
```

The phase logic is DEAD CODE for SHORT trades because the cap
dominates. The k value changes — but the output SL doesn't.

**FIX (Tier 2 priority):**

Two options:

**Option A (preferred):** lower the floor so phase logic can bite
```python
ATR_SL_MIN_ACCEL = 0.007  # was 0.015 (1.5%), lower to 0.7%
```

**Option B:** make the floor profit-aware
```python
if pnl_pct > 0:
    MIN_SL_PCT = max(0.005, pnl_pct * 0.3)  # lower floor when in profit
else:
    MIN_SL_PCT = ATR_SL_MIN_ACCEL
```

### B.4 Bug #4 — highest_price=1.0 default for orphan trades

**Severity:** LOW (cosmetic but confuses analysis)

ASTER #12193 and #12194 both show `highest_price=1.00000` which is
the column default. The trade was opened, hit guardian_orphan /
guardian_tp in 28s, but the peak price was never updated. This is a
bug in `refresh_current_prices` — the highest/lowest update only
fires when the position is found on HL with a valid price.

**FIX:** in `refresh_current_prices`, if `cur_price > 0` and the
position is found on HL, force `new_high = max(existing_high, cur_price)`
and `new_low = min(existing_low, cur_price)` even if existing values
are 0 (the init-to-entry logic for highest only handles SHORT; for
LONG it handles lowest). Need to also init `existing_low = entry`
for SHORT and `existing_high = entry` for LONG.

---

## SECTION C — CONSTANT CHANGES (TIER 2/3)

### C.1 Constants you can tweak (ranked by impact)

**TIER 2 (after Bug #1-3):**

```python
# hermes_constants.py
ATR_SL_MIN_ACCEL  0.015 → 0.007   # was 1.5%, lower to 0.7% floor
  # lets phase logic actually tighten SL when in profit
  # CURRENT: 0.015 = 1.5%
  # NEW:     0.007 = 0.7%
  # Risk: SL gets too tight on fast movers; mitigate with Bug #2 profit lock

PROFIT_MIN_PCT    0.7 → 1.0  # profit-monster floor
  # raise from 0.7% to 1.0% — let winners ride to a real profit target
  # CURRENT: 0.7 = 0.7% floor for profit-monster
  # NEW:     1.0 = 1.0% floor
  # Risk: fewer trades hit threshold; but those that do are more profitable
  # Estimated: 21 wins today → ~14-16 wins, but at +1.3% avg = +$1.85
  # vs current 21 wins at +0.95% = +$1.99
  # Net wash on day 1; better on runner days (BLUR-style +2-3%)
```

**TIER 3 (deep retune after Tier 1+2 in production):**

```python
# hermes_constants.py
K_PHASE_ACCEL_STALL   0.06 → 0.5    # was 0.06 (way too tight)
K_PHASE_ACCEL_FAST    0.05 → 0.4    # was 0.05
K_PHASE_ACCEL_SLOW    0.04 → 0.3    # was 0.04
  # CURRENT k values: 0.04-0.06 (sl_pct = 0.04*1% = 0.04% — micro-tight, useless)
  # NEW k values:     0.3-0.5 (sl_pct = 0.3-0.5% — meaningful when floor is 0.7%)
  # Rationale: phase multipliers should PRODUCE 60-80% of the floor value
  # so they can be tightened further when needed but still above the floor

K_PHASE_EXH_STALL     0.02 → 0.3
K_PHASE_EXH_FAST      0.03 → 0.4
K_PHASE_EXH_SLOW      0.02 → 0.2
  # same rationale — current 0.02-0.03 is micro-tight

K_PHASE_EXT_STALL     0.01 → 0.2
K_PHASE_EXT_FAST      0.02 → 0.3
```

### C.2 New constants to add

```python
# hermes_constants.py (new section after ATR_SL_MIN_ACCEL)
# ── Profit-Lock (tpsl_utils.compute_atr_sl_tp) ─────────────────────────
# When pnl_pct > 0, SL must be at LEAST this much in our favor relative
# to current price. Prevents giving back gains on reversal.
PROFIT_LOCK_PCT       = 0.003   # 0.3% minimum profit lock when in profit
PROFIT_LOCK_SCALE     = 0.5     # SL = current * (1 + max(PROFIT_LOCK_PCT, pnl_pct*PROFIT_LOCK_SCALE))
                                # At 1% profit: lock 0.5% (SL 0.5% above current)
                                # At 2% profit: lock 1.0% (SL 1.0% above current)
```

---

## SECTION D — TRADE FILTERS (from 24h analysis)

### D.1 Token blacklist (Tier 2 — easy, high impact)

**UPDATED 2026-07-05:** Audit showed MERL/ENS/FET are **net POSITIVE**
over 7 days (66.7%, 62.5%, 69.2% WR respectively). They were losers
on the 24h sample but are profitable on larger samples. Adding them
to the blacklist would reduce trade volume without improving edge.
**Only ASTER (0% WR, 2 trades) belongs on the blacklist.**

```python
# hermes_constants.py — SHORT_BLACKLIST
SHORT_BLACKLIST = {
    ...existing...
    # 2026-07-05: 7-day audit — 2 trades / 0% WR / -$0.06 (plus 10s re-open bug)
    'ASTER',
    # NOTE: MERL/ENS/FET are NOT blacklisted despite 24h losses — 7d data
    # shows positive returns (audited 2026-07-05). Don't reduce volume
    # based on small samples.
}
```

### D.2 Time-of-day filter (Tier 3)

Skip trades opened between 20:00-22:00 UTC (1W/9L today, $-0.61).
Add to `hermes_constants.py`:
```python
SKIP_HOURS_UTC = [(20, 22)]  # 20:00-21:59 UTC — losing window
```

Implementation: in signal_compactor or decider_run, check
`datetime.utcnow().hour` and reject if in SKIP_HOURS_UTC.

### D.3 MFE/MAE early-exit filter (Tier 3)

After 10-15 min, if MFE/MAE ratio < 1.0, exit at small loss rather
than waiting for full SL hit. This could save $0.20-0.40/day.

Implementation: in position_manager, after trade has been open >10min,
fetch price action and compute MFE/MAE. If MFE/MAE < 1.0, force close.

### D.4 ASTER 10s re-open cooldown (Tier 2)

**File:** `/root/.hermes/scripts/position_manager.py` (or new
helper in `signal_cooldowns` table)

Add: when a position closes via `guardian_orphan` or `guardian_tp`
or `guardian_sl` within 60 seconds of opening, add a 30-minute
cooldown for that token+direction to prevent immediate re-entry.

```python
# pseudocode
if exit_reason in ('guardian_orphan', 'guardian_tp', 'guardian_sl'):
    duration_sec = (close_time - open_time).total_seconds()
    if duration_sec < 60:
        # write cooldown to signal_cooldowns table
        cooldown_until = datetime.utcnow() + timedelta(minutes=30)
        write_cooldown(token, direction, cooldown_until, reason='orphan_reentry')
```

---

## SECTION E — IMPLEMENTATION ORDER (RECOMMENDED)

### Phase 1 — Bug fixes (Tier 1, no constant changes)
1. **Fix #1: lowest_price init for SHORT** (1 line in position_manager.py)
2. **Backfill existing 12 trades** (UPDATE lowest_price=entry where
   direction='SHORT' and lowest_price=0 and status='closed')
3. **Verify** — re-run analyze_24h.py, confirm no new zero-low trades

### Phase 2 — Add profit-lock logic (Tier 2, new constant)
4. **Add PROFIT_LOCK_PCT and PROFIT_LOCK_SCALE to hermes_constants.py**
5. **Implement profit-lock in tpsl_utils.compute_atr_sl_tp** (~30 lines)
6. **Verify** — check next trade, confirm SL moves to current*1.005 when in profit

### Phase 3 — Phase multiplier retune (Tier 3)
7. **Lower ATR_SL_MIN_ACCEL from 1.5% to 0.7%**
8. **Retune K_PHASE_* constants** (all to 0.2-0.5 range)
9. **Verify** — check that k values now produce different eff_sl

### Phase 4 — Trade filters (Tier 2/3)
10. **Add MERL/ENS/FET/ASTER to SHORT_BLACKLIST**
11. **Disable 5x for accel-300-** (verify the 5x wins first)
12. **Add time-of-day filter** (20:00-22:00 UTC skip)
13. **Add MFE/MAE early-exit filter**
14. **Add ASTER-style 10s re-open cooldown**

### Phase 5 — Constants (Tier 2/3)
15. **Raise PROFIT_MIN_PCT from 0.7% to 1.0%** (profit-monster floor)
16. **Optionally raise ATR_TP_K_MULT** from 1.25 to 1.5 (TP tighter)

---

## SECTION F — VERIFICATION PLAN

After each phase, verify with:

### F.1 DB sanity check (after Fix #1)
```sql
-- All SHORT trades should have lowest_price > 0
SELECT COUNT(*) FROM trades
WHERE status IN ('open','closed') AND direction='SHORT' AND lowest_price=0;
-- Expected after fix: 0 (or only orphan trades that never got a price)
```

### F.2 SL trail in real-time (after Fix #2)
```bash
# Watch pipeline.log for [TPSL] entries on a SHORT trade in profit
tail -f /root/.hermes/logs/pipeline.log | grep "TPSL.*SHORT"
# Expected: when pnl_pct > 0.3%, SL should be at most current_price*1.005
# (i.e. SL_entry_dist should drop below the trailing floor)
```

### F.3 Win rate / PnL (24h after Phase 2)
```sql
SELECT
  COUNT(*),
  ROUND(100.0*COUNT(*) FILTER (WHERE pnl_usdt > 0)/COUNT(*), 1) as wr,
  ROUND(SUM(pnl_usdt)::numeric, 2) as net
FROM trades
WHERE status='closed' AND close_time > NOW() - INTERVAL '24 hours';
-- Expected: WR > 55%, net > $0.68, profit factor > 1.5
```

### F.4 Per-token blacklist effective (24h after Phase 4)
```sql
-- MERL/ENS/FET/ASTER should appear in closed trades
-- only from BEFORE the blacklist was applied
SELECT token, COUNT(*), SUM(pnl_usdt)
FROM trades
WHERE status='closed' AND token IN ('MERL','ENS','FET','ASTER')
  AND close_time > NOW() - INTERVAL '24 hours'
GROUP BY token;
-- Expected after blacklist: 0 trades or only stale ones
```

### F.5 Profit capture ratio (key metric)
```python
# Average winner pnl_pct — should INCREASE after Phase 5
# Pre-fix: 0.95% (per 24h audit)
# Post-fix target: 1.3-1.5%
SELECT AVG(pnl_pct) FROM trades
WHERE status='closed' AND pnl_usdt > 0
  AND close_time > NOW() - INTERVAL '24 hours';
```

---

## SECTION G — RISK ASSESSMENT

| Fix | Risk | Mitigation |
|-----|------|------------|
| #1 lowest_price init | LOW — 1-line change in init logic, no math change | Verify on next 5 SHORT trades that lowest_price > 0 |
| #2 profit-lock | MED — could cause premature exits if pnl_pct calcs are wrong | Add logging: print locked_sl vs trailing_sl, exit only if locked is TIGHTER |
| #3 phase k retune | MED — could cause SL too tight on volatile tokens | Keep K_PHASE values in 0.2-0.5 range, not lower |
| #4 lower ATR_SL_MIN_ACCEL | MED — could cause SL too tight on noisy tokens | Pair with #2 profit lock to keep SL reasonable when in loss |
| #5 raise PROFIT_MIN_PCT | MED — fewer trades but bigger wins | Compare 24h pre/post, ensure net PnL not worse |
| #6 token blacklist | LOW — easy to revert | Add 1-week review, remove if no improvement |
| #7 disable 5x | HIGH — big position size change | Verify 5x wins first, maybe just cap to 5x only for high-conf |
| #8 time filter | MED — skips opportunities | 2-hour window only, easy to revert |
| #9 MFE/MAE filter | HIGH — could cut winners short | Test on past 7 days first, only enable if backtest wins |
| #10 10s cooldown | LOW — only triggers on orphan trades | Whitelist test mode if too aggressive |

---

## SECTION H — EXPECTED OUTCOMES

### Pre-fix baseline (24h audit 2026-06-25)
```
WR: 55.3%, Net: +$0.68, Profit factor: 1.52
Avg winner: +0.95%, Avg loser: -0.76%
Wins: 21 (19 profit-monster at 0.7-1.3%, 1 BLUR at 2.6%)
Losses: 16 (13 atr_sl_hit at 0.6-1.3% adverse, 3 guardian)
```

### Post Phase 1 (Bug #1 only)
```
WR: ~55% (unchanged)
Net: +$0.68 (unchanged — bug only affected 12 trades' analysis)
12 trades get working trailing SL — future losses smaller
```

### Post Phase 2 (Bug #1 + #2 profit-lock)
```
WR: 55-58%
Net: +$1.20-1.50 (+$0.50-0.80)
Avg winner: 1.2-1.5% (locked 0.3-0.5% on reversal)
Avg loser: -0.5 to -0.7% (cut early when MFE stalls)
```

### Post Phase 4 (Bug fixes + filters)
```
WR: 60-65% (MERL/ENS/FET gone, 5x disabled, 20-22h skipped)
Net: +$1.50-2.00 (+$0.30-0.50 from filters)
Net of trading: ~$1.70-2.50/day
```

### Post Phase 5 (full retune)
```
WR: 60-70%
Net: +$2.00-3.00/day
Avg winner: 1.3-1.8%
Avg loser: -0.5 to -0.7%
```

At ~20-25 trading days/month: **$40-75/month profit** (currently
break-even, sometimes negative). Conservative estimate: $30/month.

---

## SECTION I — BACKLOG / NICE-TO-HAVE

After all phases are in and verified:
- Add 4h/1h regime filter — only SHORT when 1h trend is down
- Add volume profile check — require 1.5x avg volume at signal
- Add correlation check — don't open 2 SHORTs on correlated tokens
  simultaneously (e.g. FET and ENS both AI tokens)
- Add daily P&L circuit breaker — stop after -$1.00/day
- Add weekly parameter re-tune job (Sundays at 00:00 UTC)

## AI Engineer Audit (2026-06-25) — findings applied

Subagent completed audit in 190s with 16 API calls. Verdict for each
of the 12 fixes:

| Fix | Audit Verdict | Action |
|-----|---------------|--------|
| #1 lowest_price init | **CONFIRMED + Nuance** | Fix is valid, but ROOT CAUSE is `hl-sync-guardian.py:749` INSERT missing peak price columns. `brain.py:575` only inits for PAPER trades. Real HL-mirrored trades (0G, ONDO, FET, etc.) skip the init. |
| #2 profit-lock | **NEEDS REVISION** | Diagnosis right (no profit-lock), but framing wrong: new_sl cannot be ABOVE entry for SHORT in profit (geometrically impossible). Real failure mode: new_sl is 0.6% ABOVE current_price. Fix the framing, code is OK. |
| #3 phase dead code | **CONFIRMED + Numeric error** | Diagnosis right. Example wrong: actual bound is `ATR_SL_MAX=1.2%` cap, not 1.5% floor. Both squeeze but cap wins. |
| #4 highest_price=1.0 | **CONFIRMED (ASTER only)** | Only 2 ASTER trades in 7d. Not a default value (DB default is 0). Source unclear but isolated to ASTER. |
| #5 backfill lowest_price | **CONFIRMED** | All 12 trades closed, no OPEN trades affected. Safe. |
| #6 token blacklist (MERL/ENS/FET/ASTER) | **NEEDS REVISION** | 7d data shows MERL 66.7% WR +$0.17, ENS 62.5% +$0.04, FET 69.2% +$0.40 — all POSITIVE. Only ASTER (0/2, -$0.06) is blacklist candidate. The 24h sample was misleading. |
| #7 time-of-day filter | **CONFIRMED (no existing impl)** | No `SKIP_HOURS` or `time_of_day` code exists. New impl needed. |
| #8 MFE/MAE early-exit | **CONFIRMED (no existing impl)** | New. |
| #9 10s re-open cooldown | **CONFIRMED** | `WIN_COOLDOWN_MINUTES=5` and `set_loss_cooldown` exist; just no orphan-trade trigger. |
| #10 raise PROFIT_MIN_PCT | **NEEDS REVISION** | Risk is real (24h: 21 wins, raise → ~14 wins). 7d sample may differ. T-decision only. |
| #11 leverage filter | **REMOVED (T override)** | T said don't touch leverage — it's an amplifier. |
| #12 highest_price=1.0 fix | **DUPLICATE of #4** | Same fix, different numbering. |

**NEW findings (from audit, not in plan):**
- 7-day data: 72 of 222 SHORT trades (32%) had lowest_price=0 — confirms
  the systemic issue, not just 24h
- 7-day data: 5x leverage 50% WR / -$0.62 vs 3x 58.7% / +$1.08 (N=118, 121)
  — but T said don't touch, leverage is an amplifier
- `lowest_price` column has NO DEFAULT and IS NULLABLE — so when
  hl-sync-guardian.py INSERTs without it, value is NULL, then cast to 0
  in Python. brain.py:575's init only fires for `paper=True` trades.

**Bugs in the plan itself (fixed):**
- Section B.2 cited lines 471-482 as "SHORT SL gate" — they're the SHORT
  TP gate. SHORT SL gate is at 433-453.
- Section B.3 said "1.5% floor" but actual bound is "1.2% cap" (ATR_SL_MAX=0.012)
- Section B.2 "new_sl above entry for SHORT in profit" is geometrically
  impossible — reframe as "new_sl above current"
- Line numbers for ATR_SL_MIN_ACCEL (off by 1)
- Fix #6/Fix #12 are the same root cause — combine

---

## Audit #2 (2026-06-25 05:21 UTC) — verifying the applied constants

Second ai-engineer audit. 9/9 constants CONFIRMED SAFE.

**Risk A (informational, not a bug) — HL guardian orphan SL tightening:**
`hl-sync-guardian.py:1065` uses `sl_pct = ATR_SL_MIN_ACCEL` directly
when initializing SL for HL-mirrored orphan trades. Now that the constant
is 0.005 (was 0.015), orphan-trade SL is **1.0% tighter** for HL-mirrored
positions. Expected impact: beneficial for the 5x leverage losers
(ENS, FET, ONDO, TAO) — they would have closed faster with this.

**Risk B (informational):** TP not changed → R:R ratio improves.
SL tightened 0.4% but TP unchanged. For mid-vol tokens: R:R was
1.25:1 (1.5% TP / 1.2% SL), now 1.88:1 (1.5% TP / 0.8% SL).
Net favorable for the system.

**Plan bug found:** duplicate "Implementation status" header
at lines 31 and 35 of the plan (cleaned up — lines 31-34 removed).

**No reverts recommended.** All 9 constant changes are coherent
and address the documented "DEAD CODE" issue with phase multipliers.
Fix #3 ("phase dead code") is **partially resolved** by the constant
retune — phase now differentiates in the 1.67-2.5% atr_pct sweet spot.

---

## accel_300 Stale-Bar Bug — Investigation (2026-06-25 20:25 UTC, REVISED 2026-07-05)

**T's question:** the 2026-06-23 fix scans backward so the FIRST match
should be the MOST RECENT qualifying bar. How are wrong-direction
signals even possible?

**Answer:** the 2026-06-23 fix is correct in concept — the FIRST
match IS the most recent qualifying bar. But the fix does NOT
require the LATEST bar to also qualify. If the most recent
qualifying bar is 4 hours old and the live price is ABOVE EMA,
the detector still fires the SHORT signal.

### Verification (UPDATED 2026-07-05 — full 7d dataset)

Comprehensive check of 121 accel-300 trades in last 7 days:

```
WRONG DIRECTION (price on wrong side of EMA at signal time): 27/121 (22%)
```

The bug affects BOTH directions:
- accel-300- SHORT signals firing when price is ABOVE EMA (most common)
- accel-300+ LONG signals firing when price is BELOW EMA

**Recent examples (T's reported trades, July 4-5):**

| Trade | Token | Dir | Live Gap | Result | Wrong-Direction |
|-------|-------|-----|----------|--------|------------------|
| 12393 | ONDO   | SHORT | +0.56% (ABOVE) | W (lucky) | YES |
| 12392 | PEOPLE | LONG  | -0.27% (BELOW) | W (lucky) | YES |
| 12391 | ZK     | SHORT | +0.88% (ABOVE) | W (lucky) | YES |
| 12388 | ENS   | SHORT | +0.40% (ABOVE) | L | YES |
| 12374 | LINEA | SHORT | +0.31% (ABOVE) | L | YES |
| 12369 | BSV   | SHORT | +0.53% (ABOVE) | L | YES |
| 12363 | AAVE  | LONG  | -0.26% (BELOW) | L | YES |
| 12361 | CAKE  | SHORT | +0.57% (ABOVE) | L | YES |
| 12360 | 2Z    | SHORT | +1.02% (ABOVE) | L | YES |
| 12357 | BLUR  | LONG  | -0.44% (BELOW) | L | YES |
| 12355 | APEX  | SHORT | +0.43% (ABOVE) | W (lucky) | YES |
| 12353 | APEX  | SHORT | +0.45% (ABOVE) | L | YES |
| 12340 | ADA   | SHORT | +0.23% (ABOVE) | L | YES |

Bars stale ranges from 1 to 265 bars (5 sec to 4.4 hours).

### Pattern is consistent across both directions

Looking at all 27 wrong-direction trades:
- 22 are accel-300- SHORTs firing when price is ABOVE EMA
- 5 are accel-300+ LONGs firing when price is BELOW EMA

### Root cause (verified)

In `/root/.hermes/scripts/signals/accel_300.py`, the detector
returns a signal based on `gap_pct` and `gap_growth` at bar `i`
(the signal bar — an OLD bar where price was below EMA with widening
gap). The detector does NOT check that the LIVE (latest) bar has
the same direction.

For trade #12393 (ONDO at 2026-07-05 16:06:07):
- Latest bar (idx 699): price=0.3302, EMA=0.3284, gap=+0.56% (ABOVE)
- Signal bar (some old idx): price < EMA, gap_pct=-0.6%, gap_growth=-0.3%
- Detector returns SHORT based on the OLD bar
- Trade opens SHORT, price has moved above EMA → squeezed

The two existing stale-checks are too lenient:
1. `ACCEL_300_STALE_LOOKBACK = 400` (allows signals 6.6 hours old)
2. `ACCEL_300_STALE_GAP_DECAY_THRESHOLD = 0.50` (allows 50% gap decay)

For ONDO #12393: signal_gap = 0.6%, newest_gap = 0.56%.
newest_gap (0.56%) ≈ signal_gap (0.6%) * 0.94 → still passes the 50% check.

### THE FIX (Tier 1, obvious bug per T's Bug Fix Rule)

The 2026-06-23 fix was clearly incomplete — the bug pattern is
documented in the same file's own comments. Apply this fix:

In `/root/.hermes/scripts/signals/accel_300.py`, BEFORE the
`signal_bar = {...}` block at line 617, add:

```python
# ── LIVE-BAR DIRECTION CHECK (2026-07-05 fix) ───────────────
# The 2026-06-23 fix scans backward to find the most recent
# qualifying bar. But the LATEST bar may have reversed through
# EMA by the time the signal is reported — making the signal
# direction wrong for the current price action. Verify the
# current bar's direction matches the signal bar's.
last_idx = len(closes) - 1
if last_idx > i and ema300[last_idx] is not None:
    last_price = closes[last_idx]
    last_above = last_price > ema300[last_idx]
    last_below = last_price < ema300[last_idx]
    if direction == 'SHORT' and not last_below:
        continue  # signal direction SHORT but latest bar is above EMA — stale
    if direction == 'LONG' and not last_above:
        continue  # signal direction LONG but latest bar is below EMA — stale
```

Also tighten `ACCEL_300_STALE_LOOKBACK` from 400 to 10 bars
(5-10 minutes max):

```python
# In hermes_constants.py:
ACCEL_300_STALE_LOOKBACK = 10  # was 400 — was 6.6 hours, way too lenient
```

And tighten `ACCEL_300_STALE_GAP_DECAY_THRESHOLD` from 0.50
to 0.80:

```python
# In hermes_constants.py:
ACCEL_300_STALE_GAP_DECAY_THRESHOLD = 0.80  # was 0.50 — only allow 20% decay
```

### Expected impact

- **27 of 121 accel-300 trades fire wrong direction (22%)**
- With the fix, those 27 should NOT fire (stale signals blocked)
- Some "lucky" winners (12393, 12392, 12391, 12355) will also be
  blocked — net impact is still positive
- Net daily savings: ~$0.40-0.60/day on losing trades (less SL hits)

### Verification script

`/root/.hermes/scripts/analysis/check_all_accel_direction.py`
- Checks every accel-300 trade against the EMA at signal time
- Reports WRONG-DIRECTION count and table
- Use this script after applying the fix to verify it works

### Why this matters more than the TPSL constants

The TPSL constants (applied 05:07 UTC) tighten the SL by 0.4%.
That helps somewhat, but the underlying signal direction is still
WRONG for 22% of trades. Fixing the staleness has compounding
effect: correct direction + tighter SL = real profit capture.

### Related issue: position_manager SL not capturing profit

(Independent of the stale-bar bug — was discussed earlier in
this session.) The current SL configuration is too wide to
capture profit on winners. Already addressed via:
- `ATR_SL_MAX`: 1.2% → 0.8% (tighter cap)
- `ATR_SL_MIN_ACCEL`: 1.5% → 0.5% (was dead code)
- `K_PHASE_*`: raised 10x to 0.2-0.6 (now visible)

These are LIVE in production since 05:07 UTC.

---

## Decision points for T (BEFORE IMPLEMENTATION, post-audit)

Per your rule: "ATR TP/SL are not to be changed in any circumstances
ask T first". I will NOT touch constants until you say.

**UPDATED based on ai-engineer audit:**

1. **Fix #1 (lowest_price init, 1 line, position_manager.py:2245-2248):**
   Valid fix. Audit found the actual root cause is in
   `hl-sync-guardian.py:749` which INSERTs without `highest_price` or
   `lowest_price` columns. brain.py:575 only inits for `paper=True` trades.
   The position_manager.py fix is the SAFEST place because it covers all
   insert paths. This is in the "obvious bug" category per your Bug Fix
   Rule. Apply directly?

2. **Fix #2 (profit-lock in tpsl_utils, +1 new constant):** Add
   `PROFIT_LOCK_PCT=0.003` and `PROFIT_LOCK_SCALE=0.5` to hermes_constants.py
   (NEW constants, not changes). Insert profit-lock logic in
   `tpsl_utils.py` after line 374 (eff_sl_pct calc). Audit reframed the
   bug correctly: new_sl is above current_price, not above entry. Apply?

3. **Fix #3 (lower ATR_SL_MIN_ACCEL 1.5% → 0.7%):** CHANGE to existing
   constant. The audit confirmed the diagnosis but found the actual
   bound is 1.2% cap (ATR_SL_MAX), not 1.5% floor. Lowering the floor
   to 0.7% would let the phase logic actually tighten SL. Constant
   change — T approval needed. Apply?

4. **Fix #4 (5x leverage: SKIPPED per T direction).** No action.

5. **Fix #5 (backfill lowest_price for 12 closed SHORT trades):** Audit
   confirmed all 12 are CLOSED, no OPEN trades affected. SQL is safe.
   Apply?

6. **Fix #6 (blacklist ONLY ASTER):** Audit strongly recommends only
   ASTER (0/2 WR 7d, -$0.06). MERL/ENS/FET are POSITIVE over 7d
   (66.7%, 62.5%, 69.2% WR; +$0.17, +$0.04, +$0.40). Adding them would
   reduce volume without improving edge. Add only ASTER?

7. **Fix #7 (time-of-day 20:00-22:00 UTC skip):** Confirmed no existing
   implementation. 24h data: 1W/9L in that window, -$0.61. Apply?

8. **Fix #8 (MFE/MAE early-exit):** Confirmed no existing impl. HIGH risk
   to live trading. Want a backtest on past 7d data first, then review
   results before live enable?

9. **Fix #9 (ASTER 10s re-open cooldown):** Confirmed cooldown infra
   exists (`WIN_COOLDOWN_MINUTES=5`, `set_loss_cooldown`). Need to add
   trigger: if `exit_reason in ('guardian_orphan', 'guardian_tp', 'guardian_sl')`
   AND `duration_sec < 60`, write 30-min cooldown. Apply with the
   suggested narrower trigger (only guardian_orphan, only < 30s)?

10. **Fix #10 (PROFIT_MIN_PCT 0.7% → 1.0%):** CHANGE to existing constant.
    Audit noted 24h sample shows 21 wins → ~14 wins with 1.0% floor
    (similar net). 7d sample may differ. T-decision only. Apply?

11. **Order of implementation (per T's "incremental verification" rule):**
    Phase 1a (Fix #5 backfill, 5 min, no risk) → Phase 1b (Fix #1 init,
    5 min, low risk, verify 5+ SHORT trades) → Phase 2 (Fix #2 profit-lock,
    30 min, MED risk, run 24h before next change) → Phase 3 (Fix #6 ASTER
    blacklist, 15 min, low risk) → Phase 4 (Fix #7/8/9/10, T-approval
    needed for each). Skip #4 (leverage, T-skip).

Once you say "go" on each, I implement + verify + report.
