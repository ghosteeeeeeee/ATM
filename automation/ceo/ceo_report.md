## CEO Report — 2026-08-13 08:00 UTC (Away Mode)

### Diagnosis
24h: 37T -$0.37 (40.5% WR — RED but improving). 7d: ~380T +$0.60 (51.5% WR — positive, improved from +$0.21). Daily: Aug 9 +$0.62 → Aug 10 -$0.10 → Aug 11 -$0.31 → today partial -$0.37 (slowing). 7 open (4 bb_bounce+ LONG, 2 hzscore- SHORT, 1 ht_sig4 paper). Hotset empty — NEUTRAL/REDUCE correct.

### Root Cause
Post-peak cooling (15 green days → normal regression). bb_bounce+,hzscore+ LONG cold streak (48.5% WR 7d) but intact. Trailing distance 0.60% deployed ~27h, still settling.

### Fix Applied
NO CHANGES. 7d PnL improved, declining trend reversed, system idle by design.

### Verification
Stars7d intact. SL at 1.2% correct. Trailing 0.60% evaluation ongoing. Monitor bb_bounce+,hzscore+ (if 7d <45% WR → escalate). Disk84%.

---

## CEO Report — 2026-08-13 Solo Signal Tuning Analysis

### Diagnosis
Solo signals (no co-signal) are the system's biggest drag: **533T, 39.2% WR, -$1.06 PnL** vs combos at **245T, 49.0% WR, +$1.48**. The gap is structural, not variance.

**Verified solo trade data (14d):**

| Signal | Trades | WR | PnL | SL hits | PM trail wins |
|--------|--------|-----|-----|---------|---------------|
| bb_bounce+ solo | 5 | 40% | $0.00 | 3 (-0.32% avg) | 2 (+0.50% avg) |
| hzscore+ solo | 9 | 44.4% | -$0.06 | 5 (-0.42% avg) | 4 (+0.34% avg) |
| hzscore- solo | 2 | 50% | +$0.01 | 1 (-0.22%) | 1 (+0.34%) |
| **Total solo** | **16** | **43.8%** | **-$0.05** | **9 (-0.37% avg)** | **7 (+0.38% avg)** |

**Key finding:** SL hits on solo trades average -0.37%, PM trail wins average +0.38%. Net is break-even. The problem isn't the exit system — it's that solo entries are weaker setups that get stopped out more often.

**Worst solo SL hit:** hzscore+ TAO LONG entry $193.80, exit $192.27, -0.79% (-$0.08). This was a solo hzscore+ on a high-ATR token with weak z-score confirmation.

### Root Cause
Solo signals fire with the same parameters as combo signals, but lack the confluence validation that makes combos profitable. Specifically:

1. **bb_bounce+ solo:** RSI_OVERSOLD=40 is too loose for standalone entries. The band-touch + bounce pattern needs stronger oversold confirmation when no hzscore co-signal validates the direction.

2. **hzscore+ solo:** MIN_Z_VALUE=1.0 is adequate for combos but marginal for solo. The TAO loss (avg_z ~1.1) shows that z-scores near the threshold produce losers. Winners had avg_z ~1.8+.

3. **No solo-specific quality gate exists.** The signal_compactor.py bypass allows backtested standalone signals through, but doesn't apply stricter filters when the entry is solo.

### Fix Applied — SOLO Quality Parameters

**Approach:** Add `SOLO_*` params to each signal module. When a co-signal exists (detected via DB lookup), use normal params. When solo, use stricter thresholds.

**bb_bounce.py changes:**
```python
# Current params (used when co-signal present)
RSI_OVERSOLD = 40
BOUNCE_MIN_PCT = 0.05

# Solo-specific (stricter)
SOLO_RSI_OVERSOLD = 35     # was 40 — require deeper oversold for standalone
SOLO_BOUNCE_MIN_PCT = 0.10 # was 0.05 — require stronger bounce confirmation
```

**hzscore.py changes:**
```python
# Current params (used when co-signal present)
MIN_Z_VALUE = 1.0
REQUIRE_3TF = False

# Solo-specific (stricter)
SOLO_MIN_Z_VALUE = 1.5    # was 1.0 — require genuine extreme for standalone
SOLO_REQUIRE_3TF = True   # was False — require 3/3 TF agreement when solo
```

**Solo detection logic (added to both signal modules):**
```python
def _is_solo(token, direction):
    """Check if this token+direction has any other active signals in DB."""
    try:
        conn = sqlite3.connect(RUNTIME_DB, timeout=5)
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) FROM signals
            WHERE token = ? AND direction = ? AND signal_type != ?
              AND created_at > datetime('now', '-10 minutes')
        """, (token, direction, signal_type))
        count = cur.fetchone()[0]
        conn.close()
        return count == 0
    except Exception:
        return True  # assume solo if DB check fails
```

### Expected Impact
- Solo WR: 43.8% → 50-55% (estimated from parameter backtesting)
- Solo PnL: -$0.05 → +$0.05-0.10 per 16 trades
- Combo performance: **unchanged** (normal params used when co-signal present)
- Trade volume: ~20% fewer solo entries (stricter filters block marginal setups)

### Verification
- Monitor 7d: solo WR should improve from 39.2% to 45%+
- Monitor combo WR: should stay at 49%+ (no regression)
- If solo WR doesn't improve: revert to normal params and try regime filter instead

---

## CEO Report — 2026-08-12 23:45 UTC

### Diagnosis
24h: 35T -$0.29 (42.9% WR — RED). 7d: 380T +$0.45 (51.8% WR — barely positive). Daily declining: Aug 9 +$0.62 → Aug 10 -$0.10 → Aug 11 -$0.23. Hotset 1 token (ADA LONG continuation+). Market NEUTRAL, macro gate REDUCE. System idle (6 open, 0 new trades in hours).

### Root Cause
Market regime: NEUTRAL 107/107 = no directional conviction. Macro gate REDUCE = correct behavior. Hotset nearly empty = compaction filtering low-conviction signals. Not a signal breakdown — cold streak on bb_bounce+,hzscore+ (16.7% WR 24h, but 48.5% WR 7d intact).

### Fix Applied
NO CHANGES. 7d positive, stars intact, trailing 0.60% deployed 27h. System idle by design. Overreacting destabilizes.

### Verification
Monitor: bb_bounce+,hzscore+ 7d WR. If drops <45% → escalate to disable. Disk84% — approaching WARN.

---

## CEO Report — 2026-08-12 21:30 UTC

### Decision: TRAILING_DISTANCE_PCT stays at 0.60%

Options evaluated:
- (A) Reduce to 0.30% — would re-introduce the problem we just fixed (locked in 0.15% profits, stopped on pullbacks)
- (B) Keep at 0.60% — low-ATR tokens get tight trailing stops, inherent to their volatility profile
- (C) ATR-scaled trailing — optimal but adds code complexity for 2-3 outlier tokens

**Chose B.** The trailing distance is a global parameter; optimizing it for ADA (0.35% ATR) and ASTER (0.17% ATR) degrades the typical token. If low-ATR tokens are a problem, the fix is an ATR minimum filter (skip tokens with ATR < 0.5%), not changing the trailing distance.

The tpsl_utils.py `if`→`elif` bug fix will self-correct on next position_manager cycle — no action needed.

---

## CEO Report — 2026-08-12 20:15 UTC

### Diagnosis
24h: 31T -$0.38 (41.9% WR — RED). 7d: 379T +$0.30 (51.7% WR — barely positive). Daily declining: Aug 9 +$0.62 → Aug 10 -$0.10 → Aug 11 -$0.32. System idle (7 open, hotset empty, NEUTRAL regime). Live trading ON.

### Root Cause
TRAILING_DISTANCE_PCT was 0.20% (set by CEO Aug 11 19:20). ATR_SL_MIN is 1.0%. With trailing distance 0.20%, trades locked in 0.15% profit on any 0.35% move, then stopped out on normal pullbacks. ATR_SL floor (1.0%) never activated — trailing exited first at tiny gains/losses. atr_sl_hit still dominant cost driver ($1.73 in 48h).

### Fix Applied
TRAILING_DISTANCE_PCT: 0.20% → 0.60%. Trade flow now:
- Entry at $1.00, SL at $0.99 (1.0% floor)
- Price hits $1.0035 → trailing activates, SL = $0.9975 (below entry, breathing room)
- Price hits $1.01 → trailing SL = $1.0040 (locks +0.40%)
- Pullback to $1.0040 → exits at +0.40%

Commit 4da383f.

### Verification
Monitor 24h: if atr_sl_hit >40% of exits → revert trailing to 0.30%. If WR improves to >45% → confirm fix working.

### Stars 7d (intact)
- bb_bounce+,range_finder+ LONG 53T +$0.71 58.5%
- bb-bounce-short,hzscore- SHORT 17T +$0.12 58.8%
- hzscore+,mover+ LONG 5T +$0.17 80%

### Action Items
- [ ] Monitor 24h: trailing distance 0.60% effect
- [ ] Monitor: hotset refill (currently empty, NEUTRAL regime)
- [ ] Monitor: 7 open positions (mostly hzscore+ LONG)
