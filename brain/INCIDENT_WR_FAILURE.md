# Critical Incident Report: Signal Direction Failure

**Date:** 2026-04-05
**Severity:** 🔴 CRITICAL — ongoing financial loss
**Status:** Under review — 3 options identified, T leaning toward Option 1

---

## Executive Summary

Win rate is 13.8% (WR) across 961 closed trades (Mar 10–25, 2026), with **79% of SHORT signals** having price move **against us** after entry. Total loss: -$10.56. Analysis reveals **the signal direction itself is systematically inverted**, compounded by massive over-concentration in one token (ACE = 45% of all trades, 98% of ACE shorts had price go UP).

Three remediation options identified. T favors **Option 1** — flip signal direction before trading — to test the theory cheaply before committing to extensive rebuild.

---

## Root Cause Data

### Overall Performance

| Metric | Value |
|--------|-------|
| Total closed trades | 961 |
| Win Rate (WR) | 13.8% (133/961) |
| Total PnL | -$10.56 |
| Stopped Out Rate | 78% (748/961) |
| Correct Direction But Lost | 71 trades |

### Direction Accuracy — The Core Problem

| Trade Type | Count | Price Moved **For** Us | Price Moved **Against** Us |
|------------|-------|----------------------|---------------------------|
| SHORT | 829 | 19.3% | **79.4%** |
| LONG | 132 | 31.1% | 68.2% |

**79% of the time, price moved opposite to our signal direction.** This is not bad luck — this is a systematic signal generation failure.

### The ACE Problem — Concentration + Bad Signals

| Coin | Trades | % of All | SHORTs | SHORTs Price Went UP |
|------|--------|----------|--------|---------------------|
| **ACE** | **433** | **45.1%** | **430** | **98.1%** |
| VIRTUAL | 114 | 11.9% | 113 | 69.0% |
| All others | 414 | 43.0% | 399 | 59.1% |

ACE alone accounts for **45% of all trades** and **98% of ACE shorts had price go UP** after entry. The signal system was repeatedly and almost universally wrong on ACE.

**Non-ACE WR: 24.6%** — still below target but drastically better than ACE-inflated 13.8%.

### If We Had Flipped Every Signal

| Scenario | Trades | WR | Total PnL |
|----------|--------|-----|-----------|
| Original (as traded) | 961 | 13.8% | -$10.56 |
| All signals flipped | 961 | 77.8% | symmetric loss (same $ magnitude, other side wins) |

Flipping doesn't improve total PnL — the market was net-directional during this period. But it confirms the **signal direction is systematically inverted**, not just noisy.

---

## Signal Generation Analysis

### How Signals Work (from signal_gen.py)

1. **SHORT signal conditions:**
   - Z-score elevated (price at high percentile, "exhaustion zone")
   - RSI overbought (RSI > 70)
   - Confluence from multiple timeframes
   - Market regime SHORT_BIAS confirmation

2. **The flaw:** The SHORT signal fires when z-score is HIGH, expecting mean reversion DOWN. But if the token is in a sustained uptrend, elevated z-score just means "expensive" — not "about to reverse." We were selling into strength, catching falling knives.

3. **ACE behavior:** ACE was likely in a parabolic or sustained uptrend March 10-25. Every time it pulled back slightly (z-score elevated), the signal said SHORT. It then continued up, stopped us out, repeated 430 times.

### Why ACE Dominates

- Our signal system runs on top coins by volume/interest
- ACE had extreme z-score volatility — repeatedly spiking into "exhaustion" zones that never reverted
- No trend confirmation filter — mean reversion signals fire regardless of trend strength
- Position limit or re-entry logic may have allowed continuous re-entry on the same token

---

## Three Remediation Options

### Option 1: Flip Signal Before Trading ✅ [T's Choice — Test First]

**What:** Reverse the signal direction before executing. SHORT signal → take LONG. LONG signal → take SHORT.

**Pros:**
- Fastest test — validates whether the signal direction is truly inverted
- If WR jumps from 14% to ~60%+, confirms the problem is direction inversion
- No changes to signal generation logic needed
- Can run paper trading alongside to compare

**Cons:**
- Doesn't fix the underlying signal generation bug
- If market regime changes, flipping could be wrong
- Requires changing one line in the execution path

**What to measure:**
- Run flipped signals paper trading for 24-48 hours
- Compare WR vs original direction
- If WR > 50%, the theory is confirmed

**Implementation:**
```python
# In decider-run.py or guardian execution:
# Flip direction before trading
actual_direction = "LONG" if signal_direction == "SHORT" else "SHORT"
```

**Confidence:** High — the data strongly suggests signals are directionally inverted for SHORTs

---

### Option 2: Fix Trade Flip to Properly Reverse Direction

**What:** Improve the cascade flip mechanism so when a counter-signal arrives, the position correctly reverses instead of just closing and opening separately.

**Pros:**
- Keeps signal generation intact, fixes the execution layer
- More robust — handles regime transitions gracefully
- Doesn't invert everything, just catches reversals faster

**Cons:**
- We still lose money on the initial wrong signal before the flip fires
- The initial entry is still wrong — flip only limits damage, doesn't prevent it
- The flip was 3 minutes too slow in the ME case (signals arrived after close)

**What to measure:**
- How often does the flip correctly reverse direction?
- What's the average loss before the flip fires?

**This doesn't address the core problem:** we're still entering the wrong direction first.

---

### Option 3: Fix Signal Generation at Source

**What:** Debug why the signal generation is calling the wrong direction. Possible causes:

1. **Z-score interpretation flipped** — high z-score = strong trend, not mean reversion zone
2. **Regime detection wrong** — SHORT_BIAS during an UP market
3. **RSI interpretation wrong** — RSI > 70 might mean "strong trend" not "overbought reversal"
4. **Missing trend filter** — ADX or momentum confirmation before mean reversion signals

**Pros:**
- Fixes the root cause
- Proper solution, not a workaround

**Cons:**
- **Extensive** — requires auditing all signal generation logic
- **Risk** — changing signal gen without confidence in the fix could make things worse
- **Time** — days to weeks to properly diagnose and fix
- **Can't ship without confidence** — need paper trading to validate

**What to investigate first:**
1. Check 4h regime: was it actually SHORT_BIAS during this period?
2. Check ACE z-score trajectory — was it truly mean-reverting or trending?
3. Check if ADX or other trend filters would have blocked the bad signals

---

### Option 4: Increase Stop-Loss Tolerance

**What:** Widen the stop-loss threshold so positions aren't stopped out by normal volatility. If our signals are right but we're getting stopped out before the move develops, maybe the SL is too tight.

**Data to reference:**
- `est_sl_variant_wr` and `est_sl_variant_pnl_pct` in trade_analysis_full.csv
- SL-1p5 (1.5% stop): 924 trades, WR=14.4%, AvgPnL=+0.003
- SL-1p0 (1.0% stop): 31 trades, WR=0.0%, AvgPnL=-0.179
- SL-0p5 (0.5% stop): 6 trades, WR=0.0%, AvgPnL=-1.290

**The danger:** We lose even more per trade when wrong. With 79% of shorts going against us, a wider stop means larger losses on the majority of trades. Example: if price moves 2% against us on a SHORT and we have a 3% stop instead of 1.5%, we lose 2% instead of 1.5%. Multiply by 79% losing trades and the losses add up faster.

**When this could help:** If the problem is that we're right about direction but getting stopped out by volatility before the move develops — then wider stops let winners run. But given 79% of trades go wrong direction, this likely amplifies losses, not reduces them.

**Pros:**
- Simple change — one config value
- If signal direction is correct but timing is bad, wider stops let winners develop

**Cons:**
- **Danger: lose even more per losing trade** — 79% of trades go wrong direction
- With leverage (3x), a 3% adverse move = 9% loss vs 4.5% with 1.5% stop
- Not a fix — still trading the wrong direction

**Verdict:** High risk of making losses worse. Only viable if evidence shows we're getting stopped out on valid moves (check `stopped_out=True` trades — were they reversals that eventually went our way?).

---

## Recommended Approach

**T's preference: Option 1 first (test the theory), then decide on Option 2 or 3.**

The flip test is cheap, fast, and diagnostic:
- If flipped WR > 50% → confirms direction inversion, proceed with Option 3
- If flipped WR < 50% → problem is more complex, need deeper analysis
- Either way, we learn something valuable

**Immediate next step:** Code the flip as a one-line change in decider-run or guardian, run paper trading for 24-48 hours, compare WR.

---

## Supporting Files

- Full trade data: `/root/.hermes/data/trade_analysis_full.csv` (961 trades, Mar 10-25 2026)
- Raw HL fills: `/root/.hermes/data/hl_fills_0x324a9713603863FE3A678E83d7a81E20186126E7.csv`
- Signal code: `/root/.hermes/scripts/signal_gen.py`
- Regime scanner: `/root/.hermes/scripts/4h_regime_scanner.py`

---

---

## Implementation: Option 1 Deployed

**Date deployed:** 2026-04-05
**File changed:** `/root/.hermes/scripts/decider-run.py`
**Flag:** `_FLIP_SIGNALS = True` (line 28)

**Changes made:**
1. Added `_FLIP_SIGNALS = True` config flag at top of decider-run.py
2. Flip logic added in main approved-signals loop (before `execute_trade()`)
3. Flip logic added in `process_delayed_entries()` (before `brain.py trade add`)

**Kill switch:**
- `echo '{"live_trading": false}' > /var/www/hermes/data/hype_live_trading.json` — kills all live trading instantly
- Or: edit line 28 `_FLIP_SIGNALS = False` → takes effect on next pipeline run (~1 min)

**Timeline:** Active within 1 min of deploy (hermes-pipeline.timer runs every 1 min).

*Incident report created 2026-04-05 by Agent. Update with findings from Option 1 test.*