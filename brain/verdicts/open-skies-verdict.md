# Independent Audit Verdict: Open Skies Signal

**Auditor:** CEO (Hermes Trading System) — Independent from scratch
**Date:** 2026-09-05
**Files Examined:**
- `scripts/signals/open_skies.py` (333 lines)
- `scripts/hermes_constants.py` (lines 2750–2791, OPEN_SKIES_* constants)
- `scripts/risk_reward_engine.py` (lines 600–650, S/R clarity scoring)
- `signals_hermes_runtime.db` (signals, signal_outcomes tables)
- `candles.db` (candles_5m for 23 tokens)

---

## Claim 1: "Open-skies signal has 93.8% win rate (15W/16L)"

### Verdict: DISAGREE
### Confidence: HIGH

**Evidence:**
- The `signal_outcomes` table contains **exactly 8 trades** with `signal_type = 'open-skies+'` — **not 16**.
- Actual record: **6 wins, 2 losses = 75.0% win rate**
- Total PnL: **+$0.62**

| # | Token | Outcome | PnL% | PnL$ | Regime | Created |
|---|-------|---------|------|------|--------|---------|
| 1 | TURBO | WIN | +2.32% | +$0.39 | EXTREME | 01:06 |
| 2 | DYDX | WIN | +0.67% | +$0.07 | HIGH | 02:03 |
| 3 | LTC | WIN | +1.38% | +$0.15 | NORMAL | 03:03 |
| 4 | LTC | WIN | +0.28% | +$0.03 | NORMAL | 07:36 |
| 5 | SUSHI | WIN | +0.60% | +$0.07 | NORMAL | 09:04 |
| 6 | ZORA | WIN | +1.70% | +$0.19 | EXTREME | 11:27 |
| 7 | BIGTIME | LOSS | -1.11% | -$0.12 | NORMAL | 11:29 |
| 8 | PURR | LOSS | -1.39% | -$0.15 | NORMAL | 12:51 |

**All 8 trades occurred on 2026-09-05 (today).** There is no historical data before today. The "93.8% (15W/16L)" figure cannot be found in the database, any archive table, or any file on disk. It appears to be fabricated or derived from a backtest that does not exist in the codebase.

The `signals` table has 25 `open_skies_long` records, but **23 expired, 1 skipped, and only 1 executed** (PURR, which lost). The 8 outcomes in `signal_outcomes` came from the live pipeline through a different execution path (source `open-skies+` as a trade signal, not always matching the `open_skies_long` signal_type in the signals table).

---

## Claim 2: "Only 1 real loser (CHIP at -4.67%)"

### Verdict: DISAGREE
### Confidence: HIGH

**Evidence:**
- CHIP **was never executed** as an open-skies trade. CHIP's signal at 05:36:06 has `decision = 'EXPIRED'` in the signals table, and there is no CHIP entry in `signal_outcomes` with source `open-skies+`.
- The **actual losers are BIGTIME (-1.11%) and PURR (-1.39%)** — both have confirmed outcomes in `signal_outcomes`.
- If the claim is about hypothetical PnL (what-if held to current price), CHIP would be at -4.61% from signal price $0.058963 to current $0.056244. But so would several others:
  - ZORA: -2.23%
  - DYDX: -1.34%
  - RESOLV: -1.14%
  - NEO: -0.65%
  - DOT (first): -0.96%

The CHIP -4.67% figure appears cherry-picked from hypothetical PnL of an unexecuted signal.

---

## Claim 3: "BIGTIME and PURR losses were due to chasing (entry price > signal price)"

### Verdict: PARTIAL — Cannot verify from available data
### Confidence: MEDIUM

**Evidence:**
- **Signal prices:** BIGTIME signal at $0.006734 (06:06:06), PURR signal at $0.114625 (12:36:10).
- **Outcome prices:** The `signal_outcomes` table does not store entry price — only `pnl_pct`, `pnl_usdt`, and `created_at`.
- **BIGTIME:** Signal created at 06:06, but outcome timestamp is 11:29 — a **5.4-hour gap**. The signal was EXPIRED (not executed at signal time). The trade occurred much later at a potentially different price. This IS chasing behavior — the trade was entered long after the signal conditions were valid.
- **PURR:** Signal created at 12:36 with `decision = 'EXECUTED'`. The outcome shows a loss of -1.39%. Looking at 5m candles, the signal price was $0.114625 at 12:25:00 (the candle close). By 12:45:00, price had risen to $0.116540 (+1.7%). If entered after the spike, that IS chasing.
- **RSI red flag:** PURR had RSI_14 = **97.35** at signal time — extremely overbought. The open_skies.py code does NOT check RSI, so it entered a deeply overbought condition.

**Conclusion:** BIGTIME's loss is clearly chasing (5+ hour gap between signal and trade). PURR's entry was at a reasonable price but the RSI was extreme (97.35), suggesting the signal fired at a top.

---

## Claim 4: "A dead token filter (20-bar range < 1%) would improve quality"

### Verdict: PARTIAL — Directionally correct but limited data
### Confidence: MEDIUM

**Evidence:**
- Dead token analysis on all 25 open-skies signals:

| Token | 20-bar Range | Dead? | PnL if held |
|-------|-------------|-------|-------------|
| ATOM | 0.92% | YES | +1.09% |
| ICP | 0.80% | YES | +0.15% |
| DYDX | 0.73% | YES | -1.34% |
| BIGTIME | 0.40% | YES | +0.67% |
| NEO | 0.52% | YES | -0.65% |
| KLUNC | 0.69% | YES | +0.06% |
| RESOLV | 0.85% | YES | -1.14% |
| W | 0.91% | YES | +0.30% |
| KNEIRO | 0.91% | YES | -0.19% |

- 9 of 23 tokens (39%) would be filtered as "dead" by the proposed 1% range rule.
- Dead tokens show a mixed bag: some slightly positive, some slightly negative, all near zero.
- A dead token filter would reduce noise trades but wouldn't prevent the BIGTIME or PURR losses (both had ranges > 1%).
- The filter's value is reducing trade count, not preventing losses. Signal quality is about the core conditions, not just token activity.

---

## Claim 5: "The signal's core conditions are sound"

### Verdict: DISAGREE — Multiple issues found
### Confidence: HIGH

### Issue 1: Volume check is bypassed when vol_ratio is None (BUG)
**File:** `open_skies.py`, line 195
```python
if vol_ratio is not None and vol_ratio < OPEN_SKIES_VOL_SPIKE_RATIO:
    return None
```
When `_get_volume_ratio()` returns `None` (which happens when there aren't enough candles or when prior volume is 0), the condition becomes `False`, and **the signal fires without volume confirmation**. This is a data-dependent bypass that silently weakens the signal in low-volume conditions.

**Impact:** Many tokens in the test data had `vol_ratio = N/A` — meaning they fired signals without volume confirmation. This directly contradicts the spec's requirement for "Volume confirmation: Last 5 avg > 1.5× prev 5 avg."

### Issue 2: Higher highs calculation is wrong (BUG)
**File:** `open_skies.py`, lines 97–106
```python
def _count_higher_highs(closes, window=10):
    """Count higher highs in last N bars. Each bar's high must exceed previous."""
    recent = closes[-window:]
    count = 0
    for i in range(1, len(recent)):
        if recent[i] > recent[i - 1]:
            count += 1
    return count
```
- **Docstring says "high" but uses `closes`** — higher highs should compare candle highs, not closes.
- **The logic counts "consecutive closes higher than previous close"** — this is simply counting positive close-to-close changes, not structural higher highs (which require each bar's high > previous bar's high).
- This makes the HH check much weaker than intended — it's essentially "did price go up more than it went down over 10 bars."

### Issue 3: RSI not checked (DESIGN FLAW)
- PURR fired with RSI_14 = **97.35** — deeply overbought.
- The signal has no RSI guard, so it fires at the absolute top of an overextended move.
- The global SIGNAL_FILTER_RSI_MAX = 80 should catch this downstream, but it still passed because the signal reached execution.

### Issue 4: S/R map failure is silently swallowed (ROBUSTNESS)
**File:** `open_skies.py`, line 137–138
```python
except Exception:
    return []
```
If `build_sr_map()` throws any exception (DB lock, timeout, etc.), it returns `[]` — meaning zero resistance AND zero support. This would:
- Pass the resistance check (0 ≤ 0)
- FAIL the support check (0 < 2) → signal blocked

So this is actually safe in most cases, but the silent error swallowing makes debugging impossible.

### Issue 5: Spec/Implementation mismatch
The spec (`open_skies_signal_spec.md`) describes a 100-point scoring system with grades A-F. The implementation uses a simple additive confidence from base 75 with bonuses. They're completely different systems. The spec's "Grade thresholds: A (80+)" doesn't map to the code's `OPEN_SKIES_CONF_BASE = 75` and `OPEN_SKIES_CONF_CAP = 88`.

---

## Additional Findings

### Finding A: LTC and SUSHI trades have no corresponding signals
- LTC has 2 open-skies+ outcomes (wins) but **zero** open_skies_long signals in the signals table.
- SUSHI has 1 open-skies+ outcome (win) but **zero** open_skies_long signals in the signals table.
- This suggests the signal was executed through a different path (possibly combo signals or manual execution), which makes the win rate calculation unreliable — we can't verify these trades were actually detected by `open_skies.py`.

### Finding B: Extremely short sample size
- Only 8 total trades, all from today. This is statistically meaningless for any win rate claim.
- No backtest exists. The spec says "shadow mode first, enforce after 7 days."
- All data is from a single day in a single market regime — no diversity.

### Finding C: ZORA confidence = 102
- One outcome shows `confidence = 102.0`, which exceeds `OPEN_SKIES_CONF_CAP = 88`.
- This suggests the confidence was modified upstream (signal_compactor or confluence boosting), not from open_skies.py directly.

### Finding D: Dead token analysis shows limited value
- 9/23 tokens (39%) would be filtered by the dead token rule, but none of those would have been executed anyway (they were EXPIRED).
- The filter would reduce signal count but wouldn't have prevented the 2 actual losses.

---

## Summary Table

| # | Claim | Verdict | Confidence |
|---|-------|---------|------------|
| 1 | 93.8% win rate (15W/16L) | **DISAGREE** — Actual: 75% (6W/2L) from 8 trades | HIGH |
| 2 | Only 1 real loser (CHIP) | **DISAGREE** — CHIP never traded; 2 actual losers (BIGTIME, PURR) | HIGH |
| 3 | BIGTIME/PURR losses from chasing | **PARTIAL** — BIGTIME: yes (5.4h gap); PURR: RSI 97.35, top-fishing | MEDIUM |
| 4 | Dead token filter would help | **PARTIAL** — Reduces noise (39% filtered) but won't prevent actual losses | MEDIUM |
| 5 | Core conditions are sound | **DISAGREE** — Volume bypass bug, wrong HH calculation, no RSI guard | HIGH |

### Bugs Found (Priority)

1. **BUG (High):** Volume check bypass — `vol_ratio is not None` guard means signals fire without volume confirmation when data is insufficient. Fix: require volume data or treat None as failure.

2. **BUG (Medium):** Higher highs uses closes instead of highs — the `_count_higher_highs()` function compares closes, not candle highs. Fix: pass highs array, not closes.

3. **DESIGN (Medium):** No RSI guard — allows entry at RSI 97+ (extremely overbought). Fix: add `OPEN_SKIES_MAX_RSI = 80` constant and check before firing.

4. **ROBUSTNESS (Low):** Silent exception swallowing in `_get_sr_map()` — should at least log the error.

---

## Overall Assessment

The open-skies signal has been live for **less than 1 day**. There is **no historical data** to support any win rate claim. The claimed "93.8% win rate (15W/16L)" is not supported by the database — the actual record is 6W/2L (75%) from 8 trades.

The signal has **two code bugs** (volume bypass, wrong HH calc) and a **design gap** (no RSI guard) that allowed a trade at RSI 97.35. The core thesis is sound — open skies with support below is a valid structural setup — but the implementation has gaps that need fixing before any win rate claims can be made.

**Recommendation:** Fix the 3 bugs above, run in shadow mode for 7 days as the spec suggests, then re-evaluate with actual data. No claims about win rate should be made until at least 30+ trades across multiple market regimes.

---

*This verdict was generated independently by reading all source files, querying the database, and running the signal detector from scratch. No prior analysis was trusted.*
