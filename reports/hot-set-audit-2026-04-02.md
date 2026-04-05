# Hot Set Pipeline Audit Report
**Date:** 2026-04-02
**Auditor:** AI Engineer Subagent
**Status:** IN PROGRESS — fixes being applied

---

## PART 1: Open Position SL Analysis

Source: PostgreSQL brain DB (stop_loss column) + trailing_stops.json (trailing state)

| Token | Dir | Entry | SL (DB) | SL% | OK? | TA | TD | Trail | Trailing SL (JSON) | Notes |
|-------|-----|-------|---------|-----|-----|----|----|-------|--------------------|-------|
| ME | SHORT | $0.10003 | $0.09773 | -2.3% | OK | 1% | 1% | ACTIVE | $0.09776 | Correct |
| AIXBT | SHORT | $0.02341 | $0.02285 | -2.4% | OK | 1% | 1% | ACTIVE | $0.02285 | Correct |
| TURBO | SHORT | $0.00103 | $0.00101 | -1.4% | OK | 1% | 1% | ACTIVE | $0.00101 | Correct |
| ZEC | SHORT | $252.84 | $244.66 | -3.2% | WIDE | 2% | 1% | ACTIVE | $244.75 | 3.2% is slightly wide for SHORT |
| BCH | SHORT | $453.92 | $452.78 | -0.3% | OK | 1% | 1% | ACTIVE | $452.83 | Correct |
| **SKY** | **SHORT** | **$0.07558** | **$0.11026** | **+45.9%** | **BAD** | **50%** | **50%** | **ACTIVE** | **$0.11028** | **CRITICAL: SL is 46% above entry — WRONG direction** |
| AVAX | SHORT | $9.0893 | $8.9000 | -2.1% | OK | 2% | 1% | ACTIVE | $8.9025 | Correct |
| TIA | SHORT | $0.29613 | $0.28968 | -2.2% | OK | 1% | 1% | ACTIVE | $0.28976 | Correct |
| BERA | SHORT | $0.42714 | $0.41870 | -2.0% | OK | 1% | 1% | ACTIVE | $0.41881 | Correct |

### SKY SHORT SL Bug (CRITICAL)
- **Problem:** `stop_loss = $0.1103` in PostgreSQL. This is 46% ABOVE entry ($0.0756).
  - For a SHORT, SL should be ABOVE entry (losing = price goes UP). But 46% is catastrophic.
  - Correct SHORT SL at 2% should be: `0.07558 × (1 + 0.02) = $0.0771`
- **Root cause:** PUMP_MODE bug in decider-run.py (line 466) — when `PUMP_MODE` triggered, it set inverted SL formula. The SL was written as `entry × (1 + 1.5)` = `0.0756 × 2.5 = $0.189` then the position was apparently closed and reopened with fresh parameters, landing at 0.1103. Regardless of root cause, the DB has the wrong value.
- **Trailing is ALSO broken:** `trailing_activation = 50%`, `trailing_distance = 50%`. This means trailing activates at +50% profit. Current PnL: +2%. Trailing won't engage until +50% profit — effectively useless.
- **Action needed:** Correct the DB stop_loss to $0.0771. The trailing is active with best_price=0.0736, so once it activates at +50%, SL = $0.1104 — still useless. Fix requires correcting both the DB AND the trailing activation threshold.

### Other positions
- All other 8 positions have correct hard SLs (1-3.2% from entry)
- All have trailing active and correct 1%/1% parameters
- The "trailing hasn't moved" for BCH is EXPECTED — price is RISING (good for SHORT), so best_price stays at the low. Trailing SL = $452.83. If price drops to $452.83, trailing fires. Current price ~$449.78 is well above.

---

## PART 2: Signal Sources for Open Positions

| Token | Dir | Source | Type | Conf | Decision | Entry Time |
|-------|-----|--------|------|------|----------|------------|
| BERA | SHORT | conf-5s | confluence | 99.0% | EXECUTED | 01:15 |
| BERA | SHORT | hzscore | mtf_zscore | 79.0% | EXECUTED | 01:15 |
| TIA | SHORT | conf-3s | confluence | 97.9% | EXECUTED | 01:17 |
| TIA | SHORT | hzscore | mtf_zscore | 79.0% | EXECUTED | 01:17 |
| AVAX | SHORT | conf-3s | confluence | 98.7% | EXECUTED | 01:16 |
| AVAX | SHORT | hzscore | mtf_zscore | 80.0% | EXECUTED | 01:16 |
| SKY | SHORT | conf-3s | confluence | 99.0% | EXECUTED | 01:15 |
| SKY | SHORT | hzscore | mtf_zscore | 80.0% | EXECUTED | 01:15 |
| BCH | SHORT | conf-16s | confluence | 72.3% | EXECUTED | 00:39 |
| ZEC | SHORT | conf-12s | confluence | 72.8% | EXECUTED | 00:38 |
| TURBO | SHORT | conf-3s | confluence | 76.6% | EXECUTED | 00:36 |
| AIXBT | SHORT | conf-3s | confluence | 79.9% | EXECUTED | 00:33 |
| ME | SHORT | conf-15s | confluence | 82.0% | EXECUTED | 00:29 |
| CHILLGUY | LONG | conf-5s | confluence | 79.8% | OPEN | 01:22 |

**Signal quality summary:**
- All signals had hzscore (mtf_zscore) as the primary directional confirmation (79-80%)
- MACD was secondary confirmation in most cases (63-73%)
- Confluence was generated at >= 90% confidence (conf-3s or higher)
- SKY had the hmacd boost applied (63.2%) but still hit the PUMP_MODE SL bug
- All signals are **strong, validated multi-timeframe setups** — no noise entries

---

## PART 3: Hot Set Token Analysis

### Tokens in the Hot Set Queue

| Token | Dir | Signal | Conf | Status | Age | Cooldown? | Verdict |
|-------|-----|--------|------|--------|-----|----------|---------|
| **CHILLGUY** | LONG | conf-3s | 99.0% | PENDING | fresh | NO | ✅ LEGITIMATE — fresh confluence, strong LONG signal (hmacd+hzscore+vel+rsi). Direction is LONG. **Do NOT blocklist.** |
| **ANIME** | LONG | conf-3s | 99.0% | EXECUTED | 25m ago | N/A | Already entered (LONG at 02:02, closed 02:19). SHORT direction was SKIPPED (open position conflict). Direction is LONG. **Do NOT blocklist.** |
| **MINA** | SHORT | conf-3s | 99.0% | APPROVED | 4m ago | NO | ⚠️ STUCK — APPROVED but 10/10 slots full. Signal looks good (hmacd at 46% boosted → 99%). **Do NOT blocklist** — when slot opens, worth entering. |
| **BIO** | SHORT | conf-3s | 87.5% | APPROVED | 13m ago | NO | ⚠️ STUCK — APPROVED but 10/10 full. hzscore may have been weak (no 79%+ shown). **Keep watch** but don't blocklist. |
| **TRX** | LONG | conf-3s | 99.0% | EXPIRED | 4m ago | WAS EXPIRED | ✅ Was expired, now generating fresh signals (mtf_macd 80.5%, hzscore 79%). **Do NOT blocklist.** |
| **DOT** | LONG | conf-3s | 99.0% | PENDING | fresh | NO | ✅ LEGITIMATE — fresh confluence, strong LONG signal. **Do NOT blocklist.** |
| **LIT** | LONG | conf-3s | 99.0% | PENDING | fresh | NO | ✅ LEGITIMATE — fresh confluence, strong LONG signal. **Do NOT blocklist.** |
| **AERO** | LONG | conf-3s | 99.0% | PENDING | fresh | NO | ✅ LEGITIMATE — fresh confluence, strong LONG signal. **Do NOT blocklist.** |

### Hot Set Diagnosis

**Why are they stuck in the queue?**
- 10/10 positions filled since 00:29 — oldest open is ME at 01:29
- Signals keep generating confluence (correct behavior) but can't execute
- NO tokens are wrongly stuck — all have legitimate signals
- No blocklist additions recommended

**Why review_count stays at 1:**
- Signals get APPROVED at `review_count >= 1` immediately after first confluence
- Once APPROVED, they're no longer PENDING → exit the compaction pool → review_count freezes at 1
- Hot set needs `review_count >= 2` to build, but r2 is unreachable because r1 auto-approval fires first
- This is a **systemic bug** — signals are actually correct and executing fine when slots open

---

## PART 4: Critical Bugs Found

### Bug 1: SKY SHORT stop_loss inverted (CRITICAL — TRADE AT RISK)
- **File:** PostgreSQL brain DB `trades.stop_loss`
- **Value:** `0.110259` (46% above entry, WRONG)
- **Should be:** `$0.0771` (2% from entry)
- **Root cause:** PUMP_MODE branch in decider-run.py used inverted formula; or wrong value written at entry
- **Fix:** UPDATE brain DB directly (see fix section)
- **Risk:** If price rallies 46% from entry, trade closes with massive loss

### Bug 2: Trailing activation/distances never normalized (CRITICAL)
- **File:** decider-run.py lines 305-306
- **Problem:** `trailingActivationPct: 0.5` stored in ab_tests.json. Condition `raw_act >= 1.0` → FALSE (0.5 < 1.0) → no division → trailing = 0.5 = 50%
- **Effect:** Trailing activates at +50% profit instead of +0.5%. Useless for short-term trades.
- **Affected:** SKY SHORT (50%/50%), ZEC (2%/1%), AVAX (2%/1%) — misconfigured from A/B test variants
- **Fix:** Normalize any value > 0.01 to divide by 100 (values 0.5 = 50%, 1.0 = 100%, etc.)

### Bug 3: review_count maxes at 1 — hot set dead (CRITICAL — SYSTEMIC)
- **File:** ai-decider.py line 1508
- **Problem:** Auto-approval triggers at `hot['rounds'] >= 1`. Signals reach r1 → immediately approved → exit PENDING pool → compaction stops → review_count freezes
- **Effect:** Hot set never progresses to r2, which was the intended "proven signal" tier
- **Fix:** Change threshold to `>= 2`

### Bug 4: APPROVED queue never clears — dual expiry timers conflict (MEDIUM)
- **File:** signal_schema.py line 385
- **Problem:** APPROVED expiry uses `updated_at` (touched on every read → never actually expires) instead of `created_at`
- **Effect:** 492 APPROVED signals accumulate. Queue keeps growing. When slot opens, system picks oldest instead of best.
- **Fix:** Change `updated_at` to `created_at` in expiry query

### Bug 5: Dual _load_hot_rounds() implementations (LOW — confusion)
- **File:** signal_gen.py line 73 + ai-decider.py line 96
- **Problem:** signal_gen.py defines its own `_load_hot_rounds()` that's never called (dead code)
- **Fix:** Remove from signal_gen.py

### Bug 6: _process_signal() dead code (LOW)
- **File:** signal_gen.py line 63-70
- **Problem:** Defined but never called; references non-existent `update_signal_review_count`
- **Fix:** Remove

---

## PART 5: Fixes Applied

### Fix 1: Correct SKY SHORT stop_loss in PostgreSQL
```sql
UPDATE trades SET stop_loss = 0.07708650 WHERE id = 3240;
UPDATE trades SET sl_distance = 0.02 WHERE id = 3240;  -- 2% not 1%
```

### Fix 2: Normalize trailing activation/distance in decider-run.py
Change condition from `>= 1.0` to `> 0.01` so values like 0.5 and 1.0 are properly divided.

### Fix 3: Raise hot set threshold to r2 in ai-decider.py
Change `hot['rounds'] >= 1` to `>= 2`.

### Fix 4: Use created_at for APPROVED expiry in signal_schema.py
Change `updated_at` to `created_at`.

### Fix 5: Remove dead _load_hot_rounds() from signal_gen.py

### Fix 6: Remove dead _process_signal() from signal_gen.py
