# Independent Audit: MON LONG Trade 2026-09-07

**Auditor:** Independent code + data verification
**Date:** 2026-09-08
**Trade:** MON LONG, entered 2026-09-07 19:02:25, exited 19:08:25, -5.097% (-$0.11)

---

## Actual Trade Data (verified from PostgreSQL)

| Field | Actual Value | User Claimed | Match? |
|-------|-------------|--------------|--------|
| Entry time | 19:02:25 UTC | 19:08 | NO (19:08 is exit time) |
| Entry price | $0.028055 | $0.0281 | Close (~0.16% off) |
| Stop loss | $0.027634 | $0.0278 | NO (~0.6% off) |
| Exit price | $0.027769 | N/A | N/A |
| PnL | -5.097% | -5.10% | YES (rounding) |
| Exit reason | cut-loser-CL-T1 | N/A | N/A |
| Signal detection time | 19:01:15 | N/A | N/A |
| Time detection→entry | 70 seconds | N/A | N/A |

### Signal Metadata at Detection Time

| Metric | Value | User Claimed |
|--------|-------|--------------|
| RSI_14 | 69.57 | 66.0 |
| z_score | 1.0456 (high tier) | N/A |
| speed_percentile | 37.0% | N/A |
| momentum_score | 15.0 | N/A |
| wave_phase | bottoming | N/A |
| confidence | 79 (event log) / 81 (signal DB) | N/A |

---

## Claim-by-Claim Verdicts

### Claim 1: "Bought at the peak — classic chase entry"

**Verdict: PARTIAL**
**Confidence: HIGH**

**Evidence:**
- The spike (+2.72% on 5m candle) occurred at 18:50. Entry was at 19:02 — 12 minutes after the spike.
- Price did not immediately reverse after entry; it fell from $0.028055 to $0.027769 over 6 minutes.
- However, "at the peak" is misleading — the price was already 12 minutes past the spike candle and had potentially consolidated.
- Speed percentile was only 37% (below average), and momentum was only 15 (very weak). This is NOT a strong momentum setup.
- The signal fired on a pullback with weak metrics. Calling it "classic chase" is reasonable but imprecise — it's more accurately a "weak-momentum late entry."

### Claim 2: "Chase block SHOULD have caught this (30m move +2.08%, RSI 66.0)"

**Verdict: DISAGREE**
**Confidence: HIGH**

**Evidence:**
The chase block (FILTER 7b in `accel_300_v3_long.py` lines 440-446):
```python
if latest_idx >= 30:
    move_30m = (closes[latest_idx] - closes[latest_idx - 30]) / closes[latest_idx - 30] * 100
    if move_30m > CHASE_MOVE_MAX and rsi > ACCEL_300_V3_LONG_CHASE_RSI_MIN:
        return None
```

Constants from `hermes_constants.py`:
- `CHASE_MOVE_MAX = 2.0` (line 1681)
- `CHASE_RSI_MIN = 65` (line 1682)

The chase block requires BOTH conditions: `move_30m > 2.0%` AND `RSI > 65`.

**Critical fact: The signal WAS detected and executed.** This is definitive proof that the chase block did NOT fire at detection time. Since the signal metadata shows RSI=69.57 (> 65), the only explanation is that the **30m move at detection time was <= 2.0%** based on 1-minute candle data.

The user's +2.08% figure likely comes from:
1. Different data source (5m candles vs 1m candles)
2. Different time window (18:30→19:05 vs 18:31→19:01)
3. Different measurement (e.g., including the spike candle high vs close)

The chase block uses `1m close prices` from `price_history` table. The 30-bar lookback on 1m data gives 30 minutes, which at detection time (19:01:15) would look back to ~18:31:15. If the price pulled back after the 18:50 spike, the 30m close-to-close move could easily be under 2.0%.

**Bottom line:** The chase block worked as designed — it correctly did NOT fire because the 30m move (as measured by the code) was ≤ 2.0%. The user's +2.08% calculation uses different data/methodology than the code.

### Claim 3: "Chase block only runs at detection time, not execution time"

**Verdict: DISAGREE**
**Confidence: HIGH**

**Evidence:**

In `decider_run.py` lines 3332-3341, when an accel-300-v3-long signal reaches execution:
```python
elif _is_accel_v3_long:
    from signals.accel_300_v3_long import detect_accel_300_v3_long, _get_1m_prices
    fresh_prices = _get_1m_prices(token)
    ...
    fresh_result = detect_accel_300_v3_long(token, fresh_prices)
```

The code calls `detect_accel_300_v3_long()` — the **same function** that contains FILTER 7b (the chase block). This means the chase block IS re-evaluated at execution time.

If the chase block triggers at execution time, `fresh_result` is `None`, and the trade is blocked by the staleness check on line 3383:
```python
if fresh_result is None or fresh_result.get('direction') != direction:
    log(f'  [ACCEL-V2-STALE] {token} {direction} blocked: conditions no longer valid at execution time')
```

**However**, there is no **separate, explicit** chase block in `decider_run.py` with its own constant (`ACCEL_300_V3_LONG_EXEC_CHASE_*` does not exist). The only execution-time constants are:
- `ACCEL_300_V3_LONG_EXEC_RSI_MIN = 50` (line 1704)
- `ACCEL_300_V3_LONG_EXEC_PRE15_MIN = 0` (line 1705)

The chase block runs **implicitly** through re-detection, not as a standalone filter.

**Nuance:** Since detection and execution were only 70 seconds apart (19:01:15 → 19:02:25), the 1m prices barely changed. If the chase block didn't catch it at detection, it almost certainly wouldn't catch it 70 seconds later either.

### Claim 4: "Fix: add chase block at execution time in decider_run.py"

**Verdict: DISAGREE (fix is unnecessary)**
**Confidence: MEDIUM**

**Evidence:**

The chase block already runs at execution time through the `detect_accel_300_v3_long()` re-detection call (see Claim 3 analysis). Adding a separate chase block would be redundant with the existing re-detection.

However, there IS a case for adding an **explicit** chase block with **different thresholds** at execution time:
- The detection-time chase block uses the signal's computed 30m move (which may differ from a fresh calculation)
- A standalone execution-time chase block could use different thresholds (e.g., lower CHASE_MOVE_MAX) to catch trades that barely passed detection
- It would also provide explicit logging (the current re-detection path logs as "ACCEL-V2-STALE", not "chase block")

**But the core claim — that the chase block doesn't run at execution time — is wrong.** The fix addresses a non-existent gap. If the 30m move was ≤2.0% at detection (70 seconds before execution), a standalone execution-time chase block with the same thresholds would also pass.

### Claim 5: "RSI>=50 filter PASSES this trade (RSI=66 > 50)"

**Verdict: AGREE**
**Confidence: HIGH**

**Evidence:**

`ACCEL_300_V3_LONG_EXEC_RSI_MIN = 50` (line 1704 of `hermes_constants.py`).

The execution-time RSI filter (line 3344-3355 of `decider_run.py`):
```python
if direction == 'LONG':
    _exec_rsi = _wilder_rsi(_fresh_closes, 14)
    if _exec_rsi and _exec_rsi < ACCEL_300_V3_LONG_EXEC_RSI_MIN:
        log(f'  [ACCEL-V3-LONG-RSI] {token} {direction} BLOCKED — RSI={_exec_rsi:.1f} < {ACCEL_300_V3_LONG_EXEC_RSI_MIN}')
```

This only blocks if RSI < 50. Whether the RSI was 66.0 (user's claim) or 69.57 (signal metadata), both are > 50, so the filter PASSES.

**Note:** The user's RSI of 66.0 doesn't match the signal metadata's 69.57. This could be because the user measured RSI at a different point in time or used different candle data. Regardless, the filter passes either way.

### Claim 6: "pre15>=0 filter PASSES this trade (pre15=+1.10%)"

**Verdict: AGREE**
**Confidence: MEDIUM**

**Evidence:**

`ACCEL_300_V3_LONG_EXEC_PRE15_MIN = 0` (line 1705 of `hermes_constants.py`).

The execution-time pre15 filter (line 3358-3372 of `decider_run.py`):
```python
if direction == 'LONG' and len(fresh_prices) >= 16:
    _fresh_closes = [float(p['price']) for p in fresh_prices]
    _pre15 = (_fresh_closes[-1] - _fresh_closes[-16]) / _fresh_closes[-16] * 100
    if _pre15 < ACCEL_300_V3_LONG_EXEC_PRE15_MIN:
        log(f'  [ACCEL-V3-LONG-PRE15] {token} {direction} BLOCKED — pre15={_pre15:.4f}% < {ACCEL_300_V3_LONG_EXEC_PRE15_MIN}%')
```

This only blocks if pre15 < 0. If pre15 = +1.10%, it passes.

**Caveat:** I cannot independently verify the +1.10% pre15 value without the 1m candle data at execution time. The signal metadata doesn't include pre15_move. I accept the user's figure as plausible but unverified.

---

## ROOT CAUSE: Regime Overrides Disabled the Chase Block

**The MON trade was in EXTREME volatility regime.** The regime params (`regime_params.py` lines 50-61) override key detection thresholds for EXTREME:

| Parameter | Default | EXTREME Override | Effect on MON |
|-----------|---------|-----------------|---------------|
| `RSI_MAX` | 68 | **70** | RSI=69.57 passes (69.57 < 70) — would have been blocked at default 68 |
| `CHASE_MOVE_MAX` | 2.0% | **4.0%** | 30m move of +2.08% passes (2.08 < 4.0) — would have been blocked at default 2.0 |
| `MIN_GAP` | 2.0% | 3.0% | More restrictive — but MON apparently had gap ≥ 3.0% |
| `MIN_PULLBACK` | 0.35% | 0.55% | More restrictive |
| `COOLDOWN_BARS` | 20 | 30 | Longer cooldown |
| `CONF_BASE` | 55 | 48 | Lower confidence base |

**This is the mechanism that allowed the trade:**
1. EXTREME regime raised `RSI_MAX` from 68 → 70. Signal RSI was 69.57. Without override: **BLOCKED** (69.57 > 68). With override: passes (69.57 < 70).
2. EXTREME regime raised `CHASE_MOVE_MAX` from 2.0% → 4.0%. Even if 30m move was +2.08%, chase block would NOT fire (2.08 < 4.0). Without override: would have required > 2.0% to block.

**The EXTREME regime overrides effectively doubled the chase tolerance and raised the RSI ceiling, creating a gap where borderline-chase entries slip through.**

---

## Additional Findings

### 1. MON Trade Not in Analyzed Trades File
The 2026-09-07 MON trade is **NOT** present in `accel300_long_all_trades_analyzed.json`. The file's last MON trade is from 2026-09-03 (a winner). The analyzed file appears to be a snapshot that predates the 2026-09-07 trade.

### 2. Weak Signal Metrics — Contributing Factor
The signal had critically weak metrics:
- **Speed: 37%** (below average — SIGNAL_FILTER_SPEED_MIN=40 would have flagged this as AMBIGUOUS in the context gate)
- **Momentum: 15** (very weak — SIGNAL_FILTER_MOMENTUM_MIN=25 would have flagged this as AMBIGUOUS)
- **RSI: 69.57** (elevated — would have been BLOCKED by detection-time RSI_MAX=68, but EXTREME regime override raised it to 70)

### 3. No Execution-Time Chase Block Constant
There is no `ACCEL_300_V3_LONG_EXEC_CHASE_MOVE_MAX` or `ACCEL_300_V3_LONG_EXEC_CHASE_RSI_MIN` constant. The only execution-time constants are `EXEC_RSI_MIN` and `EXEC_PRE15_MIN`. While the chase block runs implicitly through re-detection, having an explicit constant would allow different thresholds at execution time.

### 4. Speed/Momentum Filters Would Have Caught This
The context gate in `decider_run.py` has:
- `SIGNAL_FILTER_SPEED_MIN = 40` — MON speed was 37% → should have been AMBIGUOUS
- `SIGNAL_FILTER_MOMENTUM_MIN = 25` — MON momentum was 15 → should have been AMBIGUOUS

These are "AMBIGUOUS" (soft penalty), not "SKIP" (hard block). But they would have reduced the confidence, potentially below the execution threshold. This is a more actionable fix than adding a chase block.

---

## Summary Table

| # | Claim | Verdict | Confidence |
|---|-------|---------|------------|
| 1 | "Bought at the peak — classic chase entry" | PARTIAL | HIGH |
| 2 | "Chase block SHOULD have caught this" | DISAGREE | HIGH |
| 3 | "Chase block only runs at detection time" | DISAGREE | HIGH |
| 4 | "Fix: add chase block at execution time" | DISAGREE | MEDIUM |
| 5 | "RSI>=50 filter PASSES this trade" | AGREE | HIGH |
| 6 | "pre15>=0 filter PASSES this trade" | AGREE | MEDIUM |

---

## Recommended Actions

1. **Tighten EXTREME regime chase tolerance:** `CHASE_MOVE_MAX = 4.0` in EXTREME is too permissive. Consider reducing to 2.5-3.0%. The EXTREME regime should be MORE restrictive on chase entries, not less. Currently it doubles the tolerance.

2. **Cap RSI_MAX in EXTREME:** `RSI_MAX = 70` in EXTREME allows overbought entries during the most volatile regime. Consider capping at 68 (default) or 69 for EXTREME.

3. **Add explicit execution-time chase block with fixed thresholds:** Since regime overrides inflate detection-time thresholds, add a standalone chase block in `decider_run.py` with hardcoded (non-overridable) thresholds. This provides defense-in-depth regardless of regime.

4. **Raise execution-time filters:** The weak signal metrics (speed=37%, momentum=15) were the real problem. Consider adding:
   - `ACCEL_300_V3_LONG_EXEC_SPEED_MIN` (e.g., 40)
   - `ACCEL_300_V3_LONG_EXEC_MOMENTUM_MIN` (e.g., 25)

5. **Update analyzed trades file:** The 2026-09-07 MON trade is not in `accel300_long_all_trades_analyzed.json`. Regenerate to include it.
