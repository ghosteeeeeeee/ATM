# CEO Action Plan — 2026-08-02 04:15 UTC

## Status: CRITICAL BLOCKER FOUND

## What's Working
- ✅ Infrastructure (pipeline, hl-sync, trailing_stops)
- ✅ Kill switches (bb-squeeze, squeeze_cross fixed)
- ✅ Dead hours filter (inv-accel-300- added to allowlist)
- ✅ Signal generation (16-20/hr from inv-accel-300-)

## What's Broken
- 🔴 **decider_run.py** marks ALL signals as SKIPPED — zero execution
- 🔴 0% WR in 24h (10 inv-accel-300- trades, all losses)
- 🔴 Hotset empty despite signals being generated

## Root Cause
Signals flow: Generated → Compaction → Hotset → Decider → **SKIPPED** → Dead

The decider_run.py is the bottleneck. It evaluates signals and marks them SKIPPED without logging why. Need to investigate lines 2200-2600.

## Priority Actions
1. **INVESTIGATE decider_run.py** — why are all signals SKIPPED?
2. **Check if signals need APPROVED status** — is there a missing approval step?
3. **Verify dead hours fix is taking effect** — next pipeline cycle should pass inv-accel-300- signals
4. **Monitor accel-300+** — re-enabled, watching for signal decay

## Parameter Status
| Parameter | Value | Status |
|-----------|-------|--------|
| ACCEL_300_ENABLED | True | ✅ Re-enabled |
| DEAD_HOURS allowlist | inv-accel-300- added | ✅ Fixed |
| TRAILING_ACTIVATION_PCT | 0.25% | ✅ Tuned |
| TRAILING_DISTANCE_PCT | 0.50% | ✅ Tuned |
| ATR_SL_MIN | 0.8% | ✅ Tuned |
| SIGNAL_FILTER_SPEED_MIN | 35 | ✅ Permissive |
| SPEED_MIN_THRESHOLD | 35 | ✅ Permissive |

## Signal Decay Tracking
| Signal | Peak WR | Current WR | Status |
|--------|---------|------------|--------|
| inv-accel-300- | 58.3% | 0% | DECAYED — monitoring |
| accel-300+ | 80% | ??? | RE-ENABLED — watching |
| tl_break | 40-48% | 0% | DISABLED — dead |
| vel+ | 27% | 0% | DISABLED — dead |

## 🔴 ROOT CAUSE ANALYSIS — Complete (04:25 UTC)

### Three Bugs Fixed This Session

**Bug 1: Dead hours inverted logic (decider_run.py:524)**
- `_should_block = True` when signal matched allowlist → should be `False`
- Fixed in BOTH dead-hours checks (lines 524 and 2467)

**Bug 2: Preserve filter confluence bypass (signal_compactor.py:1610)**
- Single-source signals filtered out during preserve step even when `CONFLUENCE_REQUIRED=False`
- Added bypass: `elif not CONFLUENCE_REQUIRED and len(sp) >= 1: pass`

**Bug 3: signals_runner not waited for (run_pipeline.py:187)**
- signals_runner was forked into background, decider_run started immediately
- Fixed: changed `run_bg(step)` to `run(step)` — signals_runner runs synchronously (~4s)

### Current State: System Working Correctly

The quality filter is blocking most signals — this is **correct behavior**, not a bug.

**Token WR Filter (PostgreSQL, 7d):**
- 20 tokens PASS (30%+ WR, 5+ trades): STX SHORT (66.7%), ORDI SHORT (60%), AAVE SHORT (50%), etc.
- 33 tokens BLOCKED (below 30% WR): AVNT SHORT (20%), TAO SHORT (28.6%), etc.

**inv-accel-300- fires on ALL tokens** — most fail the WR filter. This is expected.

### What's Happening Now (04:25 UTC)
- Dead hours (03:00-08:00 UTC) — low market activity
- inv-accel-300- fires on 16 tokens in last 2h
- Most blocked by WR filter (correct) or dead hours (now fixed)
- 1 PENDING signal (AVNT SHORT) — blocked by WR filter (20% WR < 30% threshold)

### What to Expect After Dead Hours (08:00 UTC)
- More tokens active → more signals on high-WR tokens
- Signals should flow through: STX, ORDI, AAVE, CAKE, ETH (all 50%+ WR)
- accel-300+ should start generating (re-enabled)
- Trade rate should increase from 0/hr to 5-15/hr

## ✅ KILL SWITCH BUG: RESOLVED (12:20 UTC)

**The "19th consecutive kill switch bypass" was STALE DATA, not an active bug.**

### Evidence
- inv-accel-300- signals from 04:00-05:24 UTC were generated BEFORE `INVERSE_ACCEL_300_ENABLED` was set to False
- After the flag was changed: **ZERO new inv-accel-300- signals** in last 2 hours
- accel-300-breakout signals (05:25-10:35 UTC) same pattern — generated before `ACCEL_300_BREAKOUT_ENABLED=False`
- All recent EXPIRED/SKIPPED signals are old entries, not new generations

### Kill Switch Architecture (3 layers)
1. **Registry** (`signals/__init__.py`): `enabled` flag filters signals before they run
2. **Module check** (e.g., `inverse_accel_300.py:341`): `if not INVERSE_ACCEL_300_ENABLED: return 0`
3. **Layer 2 guard** (`signal_schema.py`): `add_signal()` blocks if `*_ENABLED=False`

All three layers are now working correctly.

### Current State
- Kill switches: ✅ Working
- Pipeline: ✅ Synchronous (signals_runner completes before decider_run)
- Dead hours: ✅ Fixed (inv-accel-300- on allowlist)
- Preserve filter: ✅ Fixed (single-source allowed)
- Trading: 0 trades today — system correctly blocking disabled signals

## 🔒 LOCKED PARAMETERS (DO NOT REVERT)

These values were set based on MFE/MAE analysis and SL floor bug fix. Changing them without data evidence will cause losses.

| Parameter | Value | Rationale | Evidence |
|-----------|-------|-----------|----------|
| ATR_SL_MIN_INIT | 2.0% | Trades need room to breathe | MFE data shows 1-2% favorable moves before reversal |
| ATR_SL_MIN | 0.8% | Floor for established trades | SL floor bug fix — was being overridden |
| TRAILING_ACTIVATION_PCT | 0.25% | Wait for real move | 0.15% triggered on noise |
| TRAILING_DISTANCE_PCT | 0.50% | Survive normal retracements | 0.30% too tight — ZEN whipsaw from 0.84% MFE |
| SIGNAL_FILTER_SPEED_MIN | 45 | Balance signal quality vs quantity | 55 caused starvation, 35 too permissive |
| Staleness decay | 10min | Give signals time to execute | 5min killed signals before compaction |

**To change any of these, you must:**
1. Show data evidence that the current value is causing problems
2. Predict the impact of the change
3. Get T's approval
