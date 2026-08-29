# Wave Pattern Classification — CORRECTED

**Last updated:** 2026-08-29 (post bug fix — see verdict in `brain/verdicts/`)

---

## Critical Bug Fixed

`find_peaks_troughs()` used `>=`/`<=` instead of strict `>`/`<`. Flat-price regions (35-44% of close transitions for low-liquidity tokens) always classified as peaks, creating a 5-7:1 peak bias and inflating "fast wave" counts.

**Impact:** All 6 former "HIGH_FREQ_OSCILLATOR" tokens were misclassified.

---

## Corrected Pattern Buckets (20 tokens)

### 1. MEDIUM_FREQ_TREND (19 tokens)
**All major tokens fall here.** The dominant pattern.

**Characteristics:**
- 67-84% of waves are 2-8 hours
- Average period: 4-19 hours (varies by token)
- Rideable trends with clear swing structure

**Tokens by amplitude:**

| Sub-bucket | Tokens | Avg Amp | Notes |
|------------|--------|---------|-------|
| **LOW_AMP** (<1.5%) | BTC, ETH | 1.0-1.1% | Tightest ranges, most stable |
| **MED_AMP** (1.5-2.5%) | SOL, LINK, HYPE, DOGE, AAVE, ONDO, POPCAT, KAS, XRP | 1.8-2.5% | Standard swing targets |
| **HIGH_AMP** (>2.5%) | ARB, ZRO, TRUMP, SUI, WLD, TURBO, SPX, FET | 2.6-4.4% | Wide swings, volatile |

**Trading implications:**
- ✅ Swing trade with trend-following (accel-300-v2 works here)
- ✅ Use 1h/4h timeframes
- ✅ Standard position sizing for MED_AMP
- ⚠️ Wider stops for HIGH_AMP (3-5%)
- ⚠️ Tighter stops for LOW_AMP (1-2%)

---

### 2. CHAOTIC (1 token)
**WIF only** — no dominant wave frequency.

**Characteristics:**
- 59.6% in 2-8h, but 39.3% in 8h+ (high tail)
- Very high CV (6.90) — unpredictable wave lengths
- HIGH amplitude (4.36%)

**Trading implications:**
- ❌ Avoid systematic strategies
- ⚠️ Reduce position size
- ✅ Discretionary only, wider stops

---

## What We Learned From The Bug

1. **Low-liquidity tokens have flat close prices** — many candles close at the same price as previous, creating `price[i] == price[i±j]` situations
2. **`>=`/`<=` biases toward peaks** — checked first in if/elif, so flat regions always become "peaks"
3. **This inflated "fast wave" counts** — flat regions spanning 1-2 candles appeared as rapid peak-trough-peak cycles
4. **Data gaps compound the problem** — missing candles create artificial long periods that distort CV and averages

---

## Key Corrected Findings

| Token | BEFORE (buggy) | AFTER (fixed) | Change |
|-------|----------------|---------------|--------|
| ZRO | HIGH_FREQ (78% fast) | MEDIUM_FREQ (67.5% med) | **Reclassified** |
| ARB | HIGH_FREQ (77% fast) | MEDIUM_FREQ (76.3% med) | **Reclassified** |
| HYPE | HIGH_FREQ (77% fast) | MEDIUM_FREQ (83.5% med) | **Reclassified** |
| WLD | HIGH_FREQ (78% fast) | MEDIUM_FREQ (76.2% med) | **Reclassified** |
| TURBO | HIGH_FREQ (74% fast) | MEDIUM_FREQ (67.1% med) | **Reclassified** |
| FET | HIGH_FREQ (72% fast) | MEDIUM_FREQ (73.1% med) | **Reclassified** |
| BTC | MEDIUM_FREQ | MEDIUM_FREQ | Same |
| WIF | CHAOTIC | CHAOTIC | Same |

---

## Practical Takeaway

**ZRO's problem was never "high-frequency noise" — it's HIGH amplitude (4.28%) in a MEDIUM frequency pattern.**

The choppy SHORT trades weren't because ZRO has fast 2h waves. They were because:
1. ZRO moves 4%+ per swing (HIGH_AMP) — stops get hit easily
2. The trades entered at bad wave positions (near troughs for SHORT)
3. Wave frequency was accelerating at entry time

**This means the fix isn't "reduce size for high-freq tokens" — it's "use wider stops and better entry timing for HIGH_AMP tokens."**

---

## Cross-Classification Matrix (Corrected)

| Pattern | LOW_AMP | MED_AMP | HIGH_AMP |
|---------|---------|---------|----------|
| **MEDIUM_FREQ_TREND** | BTC, ETH | SOL, LINK, HYPE, DOGE, AAVE, ONDO, POPCAT, KAS, XRP | ARB, ZRO, TRUMP, SUI, WLD, TURBO, SPX, FET |
| **CHAOTIC** | — | — | WIF |

---

## Revised Trading Rules by Amplitude

| Amplitude | Stop Loss | Take Profit | Position Size | Timeframe |
|-----------|-----------|-------------|---------------|-----------|
| **LOW_AMP** (<1.5%) | 1-2% | 2-4% | Standard | 1h/4h |
| **MED_AMP** (1.5-2.5%) | 2-3% | 4-6% | Standard | 1h/4h |
| **HIGH_AMP** (>2.5%) | 3-5% | 6-10% | 75% size | 1h/4h |
| **CHAOTIC** | 5%+ | Discretionary | 50% size | 4h only |
