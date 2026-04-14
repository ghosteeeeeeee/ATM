# Plan: Fix Losing Trade Management — Get Out Fast When Wrong

**Date:** 2026-04-14  
**Author:** Hermes Agent  
**Status:** DRAFT — for discussion

---

## Problem Statement

> "We are wrong about a move and just want to get out ASAP, but incorrect calls hit SL and take away all our gains."

The system has a 50.4% win rate with tiny avg win (0.46%) vs avg loss (-0.41%). The losses that hurt most are `atr_sl_hit` closes averaging **-1.84%** each — these wipe multiple wins. The cascade flip mechanism that should exit wrong positions fast is **disabled**.

---

## Current State Analysis

### Signal Performance (all closed trades, sorted worst to best avg PnL)

| Signal | Dir | N | WinRate | Avg% | Worst% | Best% | Total% |
|--------|-----|---|---------|------|--------|-------|--------|
| hzscore,pct-hermes,rsi-hermes | LONG | 4 | 50% | **-0.35%** | -1.48% | +0.69% | -1.39% |
| hzscore,rsi-hermes | SHORT | 6 | 0% | **-0.21%** | -0.33% | -0.05% | -1.24% |
| hzscore,pct-hermes,rsi-hermes | SHORT | 36 | 47% | **-0.10%** | -1.66% | +0.58% | -3.47% |
| hzscore,vel-hermes | SHORT | 32 | 56% | -0.05% | -2.49% | +1.20% | -1.68% |
| hzscore | LONG | 34 | 44% | -0.04% | -2.25% | +2.73% | -1.46% |
| hzscore | SHORT | 25 | 60% | +0.01% | -1.69% | +1.12% | +0.23% |
| hzscore,pct-hermes | SHORT | 192 | 50% | +0.01% | -1.89% | +2.91% | +2.28% |
| hzscore,pct-hermes | LONG | 216 | 46% | +0.01% | -2.35% | +5.51% | +3.09% |
| hzscore,pct-hermes,vel-hermes | SHORT | 132 | 58% | +0.07% | -2.38% | +1.72% | +8.91% |
| hzscore,pct-hermes,vel-hermes | LONG | 33 | 64% | **+0.25%** | -0.51% | +5.06% | +8.25% |

**Key insight:** `hzscore,pct-hermes,vel-hermes` is the best signal combo (WR 58-64%, avg +0.07 to +0.25%). Adding `rsi-hermes` to `hzscore,pct-hermes` makes it significantly worse.

### Close Reason Breakdown (all time)

| Reason | Count | Avg PnL% | Total PnL% | Total $ |
|--------|-------|----------|------------|---------|
| HL_CLOSED | 669 | +0.053% | +35.47% | +$17.77 |
| HL_SL_CLOSED | 25 | **-0.992%** | -24.81% | -$12.41 |
| ORPHAN_PAPER | 17 | +1.436% | +24.41% | +$2.50 |
| guardian_orphan | 15 | +0.461% | +6.92% | +$0.69 |
| atr_sl_hit | 7 | **-1.838%** | -12.87% | -$6.44 |
| atr_tp_hit | 4 | +4.270% | +17.08% | +$8.54 |

**atr_sl_hit is the 2nd most expensive close reason** (7 trades, avg -1.84%, total -$6.44). These are the trades that went wrong and didn't recover.

### Current Open Positions (real-time losses)

| Token | Dir | Entry | Current | PnL% | Dist2SL% | Dist2TP% | Lev | Age |
|-------|-----|-------|---------|------|----------|----------|-----|-----|
| BIO | SHORT | 0.01954 | 0.02030 | **-4.4%** | -1.38% | +7.21% | 3x | ? |
| LINK | LONG | 9.2035 | 9.0517 | **-1.6%** | -0.84% | +1.72% | 5x | 6.8h |
| ETH | LONG | 2372 | 2339 | **-1.1%** | -0.81% | +1.92% | 5x | ? |
| PROVE | SHORT | 0.2254 | 0.2272 | **-1.1%** | -0.31% | +1.42% | 3x | 15.6h |
| XRP | LONG | 1.375 | 1.367 | -0.5% | -0.86% | +1.64% | 5x | 16.9h |
| BTC | SHORT | 74403 | 74662 | -0.8% | -0.51% | +1.29% | 5x | 5.6h |
| AVNT | SHORT | 0.1368 | 0.1309 | +4.3% | -0.52% | +1.64% | 5x | 17.8h |

---

## Root Causes

### 1. Cascade Flip is DISABLED
```
CASCADE_FLIP_ENABLED = False  # in position_manager.py line 79
```
This is the primary "get out fast when wrong" mechanism. It's currently turned off. When a trade goes against us beyond the arm threshold (-0.25%) and momentum flips, it should close the position and enter the opposite direction. Instead, it just holds and waits for the ATR SL to trigger at -1-2%.

**Cascade flip thresholds (even when re-enabled):**
- ARM_LOSS: -0.25% (armed but doesn't flip yet)
- TRIGGER_LOSS: -0.50% (flips if speed increasing + opposite signal)
- HF_TRIGGER_LOSS: -0.35% (fast flip if momentum percentile > 80)

### 2. ATR SL is Too Wide for Wrong Directions
The ATR-based SL is designed for "give winners room" — but for wrong-direction trades, it's giving too much room. Losses like COMP SHORT (-2.38%), DYDX LONG (-2.25%), SKY LONG (-2.35%) all hit `atr_sl_hit` at -1.8 to -2.5%.

A wrong call at 3-5x leverage should exit at -0.5% to -1%, not -2%.

### 3. Signal Combo RSI-hermes Makes Things Worse
`hzscore,pct-hermes,rsi-hermes` (36 trades, avg -0.10%) underperforms `hzscore,pct-hermes` (192 trades, avg +0.01%). The RSI filter is adding noise, not signal. Similarly `hzscore,pct-hermes,rsi-hermes` LONG is the worst signal combo (4 trades, avg -0.35%).

### 4. No Early Exit for Regime Mismatch
The `regime` field is not being recorded on trades (all NULL). Even if it were, there's no logic to exit early when the 4H regime flips against the trade direction.

### 5. MACD Cascade Flip Tokens Too Narrow
MACD cascade flip (MTF alignment reversal) only fires for `{'IMX', 'SOPH', 'SCR'}` — a tiny list. This is a very conservative trigger.

---

## Proposed Approach

### Phase 1: Re-enable and Tune Cascade Flip (High Priority)

**Re-enable cascade flip** with tighter thresholds. The goal: if we're wrong, we're out at -0.5% max instead of waiting for -2% ATR SL.

Changes to `position_manager.py`:

```python
# Change this:
CASCADE_FLIP_ENABLED = False
# To this:
CASCADE_FLIP_ENABLED = True

# Tighten thresholds:
CASCADE_FLIP_ARM_LOSS      = -0.15  # ARM earlier (was -0.25)
CASCADE_FLIP_TRIGGER_LOSS  = -0.30  # Flip faster (was -0.50)
CASCADE_FLIP_HF_TRIGGER_LOSS = -0.20  # Fast flip at -0.20% (was -0.35)

# Allow more tokens to use MACD cascade flip (currently only IMX, SOPH, SCR)
MACD_CASCADE_FLIP_TOKENS = {'IMX', 'SOPH', 'SCR', 'LINK', 'AVAX', 'ETH', 'BTC', 'SOL', 'ARB', 'OP'}
```

**Risk:** More frequent flips could increase fees and whipsaw in ranging markets. Mitigate by requiring higher speed percentile (> 75) for fast flip trigger.

### Phase 2: Separate SL Logic for Wrong vs Right Trades (Medium Priority)

The ATR SL is designed to let winners run. But for wrong trades, we want a faster exit. Add a "wrong trade" detection:

- If `pnl_pct < -0.20%` AND the opposite signal is now stronger than the entry signal → exit immediately (not wait for ATR SL)
- Add a `WRONG_DIRECTION_PCT = -0.30` constant — if loss exceeds this AND regime has flipped AND opposite signal exists → immediate market close

```python
# New: fast exit for clearly wrong trades
WRONG_TRADE_FAST_EXIT_PCT = -0.30  # If we're down 30 ticks and opposite signal fires, exit now
WRONG_TRADE_REGIME_EXIT_PCT = -0.20  # If regime flipped and we're down 20 ticks, exit
```

### Phase 3: Signal Combination Cleanup (Low Priority, Data-Driven)

The RSI-hermes inclusion is making signals worse. Consider:
- Removing RSI from the signal generation filter
- OR lowering RSI weight in the composite score

Based on data: `hzscore,pct-hermes,vel-hermes` is the best signal — consider making this the primary trigger.

### Phase 4: Hotset is Empty (BUG — Fix Immediately)

The hotset currently has 0 signals. This means the decider has nothing to act on. Check why `ai_decider.py` or `signal_gen.py` is producing empty hotset. This is likely related to the recent pipeline issues.

---

## Step-by-Step Implementation Plan

### Step 1: Re-enable Cascade Flip (5 min)
- Edit `/root/.hermes/scripts/position_manager.py` line 79
- Change `CASCADE_FLIP_ENABLED = False` → `True`
- Tighten thresholds as specified above
- Verify no syntax errors, no import issues

### Step 2: Add Wrong Trade Fast Exit (15 min)
- Add new constants in `position_manager.py`
- Add `_check_wrong_trade_exit()` function
- Call it from the main loop alongside `check_atr_tp_sl_hits()`
- Write to brain DB `close_reason = 'wrong_direction_fast_exit'`

### Step 3: Verify Signal Logic — Remove RSI from Primary Signals (20 min)
- Read `signal_gen.py` to understand how signals are composed
- Check if RSI filter can be removed or made optional
- Run backtest comparison if possible

### Step 4: Fix Empty Hotset (DEBUG)
- Run `python3 /root/.hermes/scripts/ai_decider.py` manually and capture output
- Check if `hotset.json` is being written correctly
- Check the price collector is working (needed for signal scoring)

### Step 5: Validate (10 min)
- Run the pipeline and check trades.json for correct open positions
- Check guardian log for cascade flip arming/firing events
- Verify no regression: wins should still be able to run

---

## Files Likely to Change

| File | Change |
|------|--------|
| `/root/.hermes/scripts/position_manager.py` | Re-enable cascade flip, tighten thresholds, add wrong-trade fast exit |
| `/root/.hermes/scripts/signal_gen.py` | Possibly remove RSI from primary signal combo |
| `/root/.hermes/scripts/ai_decider.py` | Debug why hotset is empty |
| `/root/.hermes/brain/trading.md` | Document cascade flip settings and wrong-trade exit rules |

---

## Tests / Validation

1. **Cascade flip re-enable:** Monitor guardian log for `[Cascade]` or `[Flip]` entries
2. **Wrong trade exit:** Monitor for `wrong_direction_fast_exit` in close_reason
3. **Win rate stability:** Win rate should stay > 50%, avg win should stay > avg loss in absolute value
4. **No regression:** Winners like AVNT SHORT (+4.3%) should NOT be flipped prematurely

---

## Risks and Tradeoffs

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Cascade flip causes whipsaw in ranging markets | Medium | Medium | Require speed confirmation, higher threshold for flip |
| Fast exit kicks in on volatile-but-recovering trades | Medium | Medium | Only exit if opposite signal is strong (conf > 65) |
| Removing RSI loses diversification benefit | Low | Low | Keep RSI as secondary filter, not primary |
| Fees increase from more frequent flips | Low | Low | Flips replace SL closes, net fee impact should be similar |

---

## Open Questions for T

1. **Is -0.30% fast exit too aggressive?** At 5x leverage that's -1.5% on the position — should we use -0.50% instead?
2. **Should we also flip when we're RIGHT** (i.e., when a winner hits TP, flip into the opposite direction)?
3. **Do you want to backtest** the tighter cascade flip thresholds before deploying live?
4. **What tokens** besides the MACD list should get the fast-flip treatment?
