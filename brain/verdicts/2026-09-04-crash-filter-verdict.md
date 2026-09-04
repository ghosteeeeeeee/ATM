# Independent Audit Verdict — Sep 4, 2026 BTC Crash Filter

**Auditor:** Independent code auditor (fresh-eyes, no priming)
**Date:** 2026-09-04
**Files audited:**
- `btc_crash_filter.py` (734 lines, complete)
- `hermes_constants.py` (lines 888-967, 1160-1168)
- `decider_run.py` (lines 1920-2019)
- `cut_loser.py` (lines 298-397)
- `volatility_gate.py` (280 lines, complete)

---

## === INDEPENDENT VERDICT ===

---

### Claim 1: "The BTC crash filter v2 with ATR-scaled thresholds would have caught this crash"

**Verdict: AGREE** (with minor inaccuracy in the claimed ATR value)

**Evidence:**
- Actual BTC ATR(14)% at crash time: **0.7102%** (not 0.6357% as claimed)
- Dynamic threshold: `-1.5 × (0.7102 / 0.8) = -1.3317%`
- After clamping to MIN_THRESHOLD: **-1.0000%** ← this is what the claim reports
- BTC 5m drop (close-to-close from 12:25→12:30): **-1.290%**
- 12:30 candle: 81340.0 → 80186.41 = **-1.418%** (single candle)

The clamping formula `max(-1.0, min(-2.5, -1.332))` yields -1.0%, which is exactly what the claim states. The -1.290% 5m drop exceeds the -1.0% threshold, so the filter WOULD have triggered.

**Layer-by-layer at 12:30:**
| Layer | Triggered? | Value | Threshold |
|-------|-----------|-------|-----------|
| PRICE (Layer 1) | ✅ YES | -1.290% 5m | -1.0% (clamped) |
| VOLUME (Layer 2) | ✅ YES | 75.8x | 3.0x |
| CONTAGION (Layer 3) | ❌ NO | eth_div = -0.691% | > +0.30% (**BUG**) |
| ACCEL (Layer 4) | ✅ YES | vel = -1.418% | < -0.15% |

**Result:** PRICE + VOLUME + ACCEL = 3 layers triggered → **CRITICAL severity** (would have blocked entries for 5 min).

**Note:** The claimed ATR value of 0.6357% is inaccurate; actual was 0.7102%. The threshold result (-1.0%) is the same due to clamping, so the conclusion is correct.

**Confidence: HIGH**

---

### Claim 2: "The contagion score (3+ tokens dropping >0.5% in 5min) is NOT a reliable standalone SHORT signal — claimed 3-4% win rate across 7000+ signals"

**Verdict: PARTIAL — cannot verify the backtest numbers; code logic has a separate bug**

**Evidence:**
- The "3+ tokens dropping >0.5%" formulation does not directly match any single layer in btc_crash_filter.py.
- Layer 3 (contagion) uses ETH/SOL divergence from BTC, not a token-count metric.
- Layer 6 (multi-alt divergence) counts alts with >0.3% divergence below BTC, but requires BTC to be falling first (`MULTI_ALT_BTC_5M_THRESHOLD = -0.5%`).
- The 3-4% win rate across 7000+ signals is a backtest claim that cannot be verified from code inspection alone.
- During the actual crash, only 6 tokens dropped >0.3% at 12:20 (not 17 as claimed in Claim 4), suggesting the "contagion score" premise may be overstated.

**Confidence: LOW** (backtest data not accessible)

---

### Claim 3: "BCH was the only position significantly in profit at 12:29 (+2.68% / +13.4% leveraged)"

**Verdict: PARTIAL — cannot fully verify without trade entry data**

**Evidence:**
- trades.db is empty (no trade records available for verification).
- From candle data, BCH price at 12:29 = $259.20. At 11:30 = $259.80 → **-0.23% from 11:30**.
- BCH peak in the 12:00-12:29 window = $260.70. At 12:29 = $259.20 → **-0.58% from peak**.
- ALT was at $0.006380 at 12:29, up +0.63% from 11:30.
- Without knowing the actual entry prices for each position, the "+2.68% in profit" claim for BCH cannot be verified or refuted.
- ALT was actually UP from its 11:30 level, contradicting the implication that only BCH was profitable.

**Confidence: LOW** (missing trade data)

---

### Claim 4: "17 tokens crashed before BTC (at 12:20, 10 minutes early) — CHIP dropped -4.14%, CAKE -1.13%, ZEN -1.00%"

**Verdict: DISAGREE**

**Evidence:**
At 12:20, the actual data from candles_1m:
| Token | Claimed Drop | Actual Drop | Status |
|-------|-------------|-------------|--------|
| CHIP | -4.14% | **-0.091%** | ❌ WRONG (off by 45x) |
| CAKE | -1.13% | **+0.099%** (went UP) | ❌ WRONG |
| ZEN | -1.00% | **-0.828%** | ❌ Close but wrong |

- Only **6 tokens** dropped >0.3% at 12:20, not 17.
- The biggest drop at 12:20 was MET at -0.924%.
- CHIP actually went UP +2.25% in the 12:15-12:25 window.
- CAKE went UP +0.50% in the same window.
- The specific numbers in this claim appear fabricated or from a different incident.

**Confidence: HIGH**

---

### Claim 5: "If the MAE guard was enabled at 2.0% threshold, all 6 positions would have been cut before reaching 4-6% losses"

**Verdict: AGREE**

**Evidence:**
From peak (12:29) to lowest point (12:30-12:47), each position's drop:
| Token | Peak (12:29) | Lowest | Drop from Peak |
|-------|-------------|--------|----------------|
| BCH | $259.20 | $248.10 | **4.28%** |
| ALT | $0.006380 | $0.006190 | **2.98%** |
| NXPC | $0.2083 | $0.2031 | **2.50%** |
| BABY | $0.01110 | $0.01076 | **3.06%** |
| YGG | $0.02288 | $0.02214 | **3.23%** |
| GMT | $0.00739 | $0.00716 | **3.11%** |

All 6 positions exceeded 2.0% from peak. A 2.0% MAE guard threshold would have cut all of them.

**Note on current settings:** The current `CL_MAE_GUARD_BASE_THRESHOLD` is 3.0% (widened from 2.0% on 2026-08-26). With the BTC crash multiplier (0.6x), the effective threshold would be 1.8%, which would also have caught all positions. The question is whether the MAE guard was enabled at the time of the crash.

**Confidence: HIGH**

---

### Claim 6: "The btc_crash_filter.py module has no SQLite connection leaks"

**Verdict: AGREE**

**Evidence:**
- `_get_candles()` (line 68-90): Uses `conn = None` → `try` → `conn = sqlite3.connect(...)` → `finally: if conn: conn.close()`. **Properly handles all code paths** including exceptions.
- `_get_atr_pct()` (line 93-113): Delegates to `volatility_gate.get_atr_pct()` which also has proper try/finally with conn.close().
- `volatility_gate.get_atr_pct()` (line 153-193): Uses `conn = None` → `try` → `conn = sqlite3.connect(...)` → `finally: if conn: conn.close()`. **Properly handles all code paths.**
- No other direct SQLite connections exist in btc_crash_filter.py.

**Edge cases verified:**
- Empty candle lists: returns safe defaults (1.0, 0.0, 0.0, False) ✅
- Zero prices: properly guarded by `if prev <= 0: return 0.0` and `if btc_5m_ago <= 0: return False` ✅
- Zero volumes: `if avg_vol <= 0: return 1.0` ✅
- Short candle lists: `if len < N: return safe_default` ✅

**One observation:** The `_get_candles()` function uses `except Exception: return []` which silently swallows all errors including `KeyboardInterrupt` (via `Exception`). This is a minor concern but not a connection leak.

**Confidence: HIGH**

---

### Claim 7: "The decider_run.py integration properly handles both crash-block and accel-block with time-based expiry"

**Verdict: AGREE**

**Evidence:**
The integration at lines 1926-1992 properly separates two block types:

1. **Crash-block** (`_btc_crash_blocked`):
   - Set `True` when `PRICE` is in the triggered layers (or any multi-layer trigger)
   - Blocks ALL entries for the entire pipeline run (no expiry within the run)
   - Direction-specific blocking via `_btc_block_direction` (line 1974)

2. **Accel-block** (`_btc_accel_blocked`):
   - Set `True` when `ACCEL` is triggered WITHOUT `PRICE` (accel-only scenario)
   - Uses time-based expiry: `_btc_block_until = _crash_signal.block_until` (line 1945)
   - Checked per-token in the loop: `if time.time() < _btc_block_until` (line 1986)
   - Auto-expires: `_btc_accel_blocked = False` when time is up (line 1992)

3. **Variable scoping:**
   - `_crash_signal` is defined at line 1934 (before the for loop at line 1962)
   - Used safely at lines 1938, 1978, 1979 (all within the same function scope)
   - Protected by try/except at line 1949 (import failure handled gracefully)
   - `_crash_signal` defaults to `None` (line 1934) and is checked before use (line 1978)

**Confidence: HIGH**

---

## BUGS DISCOVERED

### BUG: Contagion Check Has Inverted Logic (Layer 3)

**Severity: HIGH** — Prevented the contagion layer from firing during the Sep 4 crash.

**File:** `btc_crash_filter.py`, line 243
**Code:**
```python
is_contagion = eth_div > BTC_CRASH_CONTAGION_THRESHOLD  # threshold = 0.30
```

**The problem:**
- `eth_div = eth_chg - btc_chg`
- When ETH falls MORE than BTC (actual contagion), eth_chg is MORE negative than btc_chg
- Example: ETH = -1.98%, BTC = -1.29% → eth_div = -1.98 - (-1.29) = **-0.69**
- The check requires `eth_div > +0.30`, which is **FALSE** for actual contagion
- The check would only trigger when ETH falls LESS than BTC (NOT contagion)

**Impact on Sep 4 crash:**
- ETH fell -1.98% vs BTC -1.29% → clear contagion signal
- But eth_div = -0.691%, which fails the `> 0.30` check
- Contagion layer did NOT fire
- Severity was CRITICAL (3 layers) instead of EMERGENCY (4 layers would have been PRICE+VOLUME+CONTAGION+ACCEL)

**Fix:** Change line 243 to:
```python
is_contagion = eth_div < -BTC_CRASH_CONTAGION_THRESHOLD  # negative = ETH fell more
```
Or equivalently, negate the divergence computation at line 153:
```python
return btc_chg - eth_chg  # positive = ETH fell more = contagion risk
```

**Note:** This bug was NOT introduced recently — the docstring at line 143 says "Positive = ETH leading BTC down (ETH fell more than BTC = contagion risk)" but the math at line 153 computes the opposite sign. The docstring describes the intended behavior; the implementation has the wrong sign.

---

## SUMMARY TABLE

| # | Claim | Verdict | Confidence |
|---|-------|---------|------------|
| 1 | Crash filter would have caught this crash | **AGREE** | HIGH |
| 2 | Contagion score unreliable standalone SHORT signal | **PARTIAL** | LOW (can't verify backtest) |
| 3 | BCH only position in profit at 12:29 | **PARTIAL** | LOW (no trade data) |
| 4 | 17 tokens crashed before BTC at 12:20 | **DISAGREE** | HIGH |
| 5 | MAE guard at 2.0% would have cut all 6 | **AGREE** | HIGH |
| 6 | No SQLite connection leaks | **AGREE** | HIGH |
| 7 | decider_run.py handles crash/accel properly | **AGREE** | HIGH |

**Bugs found:** 1 critical (contagion logic inversion)

---

*Generated by independent auditor — no external analysis was referenced or trusted.*
