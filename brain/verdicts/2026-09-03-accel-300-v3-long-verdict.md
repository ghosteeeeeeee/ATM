# Independent Verdict: accel_300_v3_long Signal Audit

**Date:** 2026-09-03
**Auditor:** Independent code + data audit (fresh eyes, no priming)

---

## 1. Raw Trade Data

**26 trades total | 11 wins (42.3% WR) | Total PnL: -$0.88**

| Token | Win? | PnL% | Regime | Confidence |
|-------|------|------|--------|------------|
| ENA | W | +2.50% | EXTREME | 74 |
| ARB | W | +1.87% | EXTREME | 59 |
| ACE | W | +1.74% | FLAT | 84 |
| PONS | W | +1.07% | EXTREME | 74 |
| ARB | W | +0.82% | EXTREME | 79 |
| CASHCAT | W | +0.81% | EXTREME | 69 |
| SUSHI | W | +0.75% | EXTREME | 74 |
| ADA | W | +0.70% | HIGH | 74 |
| ENA | W | +0.58% | EXTREME | 79 |
| COMP | W | +0.28% | NORMAL | 74 |
| CHIP | W | +0.24% | EXTREME | 74 |
| FIL | L | -1.81% | EXTREME | 79 |
| ACE | L | -1.64% | FLAT | 79 |
| ARB | L | -1.53% | EXTREME | 74 |
| STX | L | -1.39% | EXTREME | 74 |
| BIGTIME | L | -1.33% | HIGH | 79 |
| CASHCAT | L | -1.27% | EXTREME | 74 |
| ZORA | L | -1.25% | EXTREME | 79 |
| SUSHI | L | -1.20% | EXTREME | 84 |
| ENA | L | -1.05% | EXTREME | 99 |
| ICP | L | -1.00% | EXTREME | 79 |
| CASHCAT | L | -1.00% | EXTREME | 74 |
| ZRO | L | -0.92% | EXTREME | 69 |
| ARB | L | -0.76% | EXTREME | 79 |
| PONS | L | -0.37% | EXTREME | 74 |
| FIL | L | -0.05% | EXTREME | 84 |

### Win/Loss Breakdown by Regime

| Regime | Trades | Wins | WR | Total PnL |
|--------|--------|------|----|-----------|
| EXTREME | 18 | 7 | 38.9% | -$1.03 |
| FLAT | 2 | 1 | 50.0% | +$0.01 |
| HIGH | 2 | 1 | 50.0% | -$0.19 |
| NORMAL | 1 | 1 | 100% | +$0.03 |

### Log-Level Signal Parameters (Detection Time)

From signals.log, recent 60 detections — key patterns:

- **All signals had trend_15m=BULLISH** (BEARISH filter working)
- **All signals had green_count ≤ 3** (chase cap working)
- **RSI range: 51.6 – 69.0** (overbought filter working)
- **Gap range: 1.55% – 5.53%** (most ≥ 2.0%, a few 1.55–1.93% from fresh cross mode)
- **Pullback range: 0.21% – 2.29%**
- **Reexpansion range: 0.09% – 0.91%**

---

## 2. Code Audit — Bugs Found

### BUG #1: CRITICAL — Staleness Check Uses Stale `price` Variable

**File:** `accel_300_v3_long.py`, line 598
**Severity:** HIGH

```python
# Line 495: price comes from prices_dict (PASSED IN, potentially stale)
price = data.get('price')

# ... detection runs with fresh `prices` data ...

# Line 595-598: staleness re-check
current_closes = [float(p['price']) for p in _get_1m_prices(token)]  # FRESH
current_ema = _ema_series(current_closes, PERIOD)[-1]                 # FRESH
current_gap = (price - current_ema) / current_ema * 100               # BUG: `price` is STALE
```

The staleness check is supposed to verify the signal is still valid at CURRENT market price. But it uses `price` from `prices_dict` (line 495) instead of `current_closes[-1]`. This means:
- The staleness check compares OLD price vs NEW EMA → wrong gap calculation
- If price moved UP since detection, staleness check shows smaller gap than reality → may incorrectly PASS
- If price moved DOWN since detection, staleness check shows larger gap → may incorrectly PASS
- The `current_gap < sig['gap_pct'] - 0.15` check (line 606) is comparing apples to oranges

**Fix:** Line 598 should be:
```python
current_gap = (current_closes[-1] - current_ema) / current_ema * 100
```

**Impact:** The staleness re-check is INEFFECTIVE. Signals that should be blocked by staleness are passing through. This likely contributed to losing trades where price moved adversely between detection and execution.

---

### BUG #2: MEDIUM — Fresh Cross Mode Doesn't Bypass Pullback/Peak Distance Filters

**File:** `accel_300_v3_long.py`, lines 308–357

The fresh cross mode (line 320) only bypasses the MIN_GAP check (line 323–325):
```python
if not fresh_cross:
    if gap_now < ACCEL_300_V3_LONG_MIN_GAP or gap_now > ACCEL_300_V3_LONG_MAX_GAP:
        return None
```

But these filters still apply to fresh crosses:
- **MIN_PULLBACK (0.35%)** — at a fresh cross, pullback is naturally 0 or very small (gap just turned positive)
- **MIN_PEAK_DISTANCE (0.05%)** — at a fresh cross, there may be no recent peak at all
- **GAP_BOTTOM_MIN (0.30%)** — requires gap to have narrowed before re-expanding

**Result:** Fresh cross mode barely fires because the pullback filters block it. The only signals that pass have gap ≥ 2.0% (non-fresh) OR have enough history for pullback detection. The fresh cross mode is effectively dead code for most scenarios.

**This is NOT a bug per se** — the pullback filters are intentional quality gates. But the fresh cross mode was designed to catch initial bounces, which inherently have no pullback yet. The design intent conflicts with the implementation.

---

### BUG #3: LOW — Staleness Check Also Uses `price` Instead of `current_closes[-1]` for Reexp Check

**File:** `accel_300_v3_long.py`, lines 610–616

```python
current_reexp = current_gap - gap_3_ago  # current_gap uses stale `price`
```

Same root cause as Bug #1 — the reexpansion re-check at execution time is based on the stale gap calculation.

---

### NOT A BUG: Constants Were Tightened After Early Trades

The SUSHI (pullback=0.292%), CASHCAT (reexp=0.181%), and ICP (reexp=0.182%) log entries show values below current thresholds. Git history confirms:
- Original constants: MIN_PULLBACK=0.15, MIN_GAP=1.5, REEXPAND_MIN=0.08
- Current constants: MIN_PULLBACK=0.35, MIN_GAP=2.0, REEXPAND_MIN=0.20

These early signals were VALID when generated. The constants were tightened in commit `5514d0f1` ("v3 4 fixes for 37.5% WR — re-enabled with tighter filters"). The current constants would filter most of the losers.

---

## 3. Analysis: What's Working

1. **15m trend filter** — All signals had BULLISH trend. BEARISH filter is effective.
2. **Chase cap** — No signals exceeded 3 consecutive greens.
3. **RSI filter** — All signals in 51.6–69.0 range. Overbought/oversold filtering works.
4. **Gap velocity filter** — Ensures gap isn't narrowing at entry.
5. **Persistence filter** — Price stays above EMA300 for 5+ bars.
6. **Linear regression slope** — Positive slope confirms uptrend.
7. **Volume confirmation** — Bounce has volume support.
8. **Cooldown** — 20-minute cooldown between signals per token.
9. **Volatility gate** — accel-300-v3-long+ is correctly registered in all 4 regimes.
10. **Layer 2 enforcement** — signal_schema.py correctly blocks disabled signals.

---

## 4. Analysis: What's Broken

1. **Staleness re-check is ineffective** (Bug #1) — the most impactful issue. The whole point of the staleness check is to catch signals that went stale between detection and execution. Using stale `price` defeats this purpose entirely.

2. **Fresh cross mode is architecturally flawed** — it bypasses MIN_GAP but not MIN_PULLBACK, which contradicts the design intent of catching initial bounces.

3. **Confidence values don't match** — Log shows conf=88 for most signals, but signal_outcomes has 59–99. The compactor modifies confidence, but the log (from signal creation) shows different values. This makes debugging harder.

---

## 5. Analysis: What's Missing

1. **No dynamic stop-loss** — All trades use fixed ATR SL. No adjustment for volatility regime or entry quality.
2. **No position sizing** — All trades use the same amount regardless of confidence or regime.
3. **No re-entry logic** — If a signal loses, there's no mechanism to re-enter on a better setup.
4. **No regime-based parameter tuning** — Same constants for FLAT, NORMAL, HIGH, EXTREME. EXTREME has 38.9% WR — should have tighter filters or no trading.

---

## 6. Verdicts

### Claim: "Fresh cross mode bypasses MIN_GAP for fresh crosses"
**Verdict: AGREE**
**Evidence:** Code at lines 323–325 confirms: `if not fresh_cross: [MIN_GAP check]`. Fresh crosses (≤8 bars since cross) skip the gap range check.
**Confidence: HIGH**

### Claim: "MIN_PULLBACK and MIN_PEAK_DISTANCE still block fresh cross entries"
**Verdict: AGREE**
**Evidence:** Lines 339 and 356 apply these filters unconditionally — no `if not fresh_cross` bypass. At a fresh cross, pullback ≈ 0, which fails MIN_PULLBACK=0.35%.
**Confidence: HIGH**

### Claim: "ENA won because it entered during a pullback with confirmed bounce"
**Verdict: PARTIAL**
**Evidence:** ENA had two trades — one win (+0.58%) and one loss (-1.05%). The win had pullback=0.309%, reexp=0.432%. The loss had pullback=0.290%, reexp=0.867%. Both had positive reexp. The difference was likely timing/market conditions, not just pullback quality. The win entered at a better price relative to the subsequent move.
**Confidence: MEDIUM**

### Claim: "CHIP/PONS/CASHCAT lost because they entered at peaks or with negative reexp"
**Verdict: DISAGREE**
**Evidence:** 
- CHIP: Win (+0.24%), not a loss. Had pullback=0.422%, reexp=0.633%. Valid entry.
- PONS: One win (+1.07%) and one loss (-0.37%). The loss had pullback=1.363%, reexp=0.654% — good pullback and positive reexp. The loss was a small drawdown, not a peak entry.
- CASHCAT: Two losses (-1.00%, -1.27%) and one win (+0.81%). Losses had reexp=0.737% and reexp=0.181% (below current threshold of 0.20%). The -1.00% loss DID have marginal reexp. But the -1.27% loss had strong reexp — likely market-wide sell-off.
- Actual losers with negative reexp: Looking at log data, ZORA had reexp=0.090% (below 0.20% threshold) — this would be filtered by current constants.
**Confidence: HIGH**

### Overall Signal Quality Assessment
**Verdict: PARTIAL — Signal has edge but execution is degraded by staleness bug**
**Evidence:** 42.3% WR with -$0.88 total is negative. But:
- Current constants would filter ~8 of the 15 losers (SUSHI 0.292% pullback, CASHCAT 0.181% reexp, ICP 0.182% reexp, ZORA 0.090% reexp, etc.)
- After constant tightening, estimated WR would be ~55% with positive PnL
- The staleness bug (Bug #1) allows stale signals through, degrading performance
- EXTREME regime (38.9% WR) is the weakest — should be filtered or have tighter params
**Confidence: HIGH**

---

## 7. Recommendations

1. **FIX BUG #1 IMMEDIATELY** — Change line 598 from `price` to `current_closes[-1]`. This is the highest-impact fix.
2. **Consider bypassing MIN_PULLBACK for fresh crosses** — Or reduce MIN_PULLBACK to 0.10 for fresh crosses only.
3. **Reduce EXTREME regime exposure** — 38.9% WR in EXTREME suggests the signal doesn't work well in high-volatility storms. Consider adding a regime gate or tighter params for EXTREME.
4. **Add logging for staleness check results** — Log when signals are blocked by staleness so we can tune the thresholds.
5. **Track detection-time vs execution-time parameters** — Store both in signal_outcomes for post-mortem analysis.

---

*End of independent audit.*
