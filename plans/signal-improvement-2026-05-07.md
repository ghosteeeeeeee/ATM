# Signal Improvement Plan — 2026-05-07

## Context

System WR collapsed from 25% (Mar) → 13.9% (Apr) → 6.7% (May 1-4) → ~0% (May 5-7).
Market flipped bullish May 5+: LONG avg peak +9.92%, SHORT avg peak -8.40%.
Top winners from archive (signal_outcomes): ORDI SHORT +873%, APE LONG +858%, GRIFFAIN +526%, AVNT SHORT +508%, ETH LONG +506%.
4 critical bugs found: GOOD_STANDALONE_SIGNALS naming mismatch, RS ATR band filter, hwave removed, confluence collapse.

---

## PRIORITY 1: Fix GOOD_STANDALONE_SIGNALS — naming mismatch (5 min)

### Problem
`signal_compactor.py` line ~517:
```python
base_type = _signal_type_key(source_parts[0])  # 'accel-300+' → 'accel_300_long'
```
GOOD_STANDALONE_SIGNALS uses **hyphen format**:
```python
'accel-300+':  {'wr': 42, 'avg': 0.438, 'dir': 'LONG'},
'pct-hermes-': {'wr': 35, 'avg': 0.221, 'dir': 'SHORT'},
```
`_signal_type_key('accel-300+')` → `'accel_300_long'` → **never matches** → bypass is dead code → all single-source signals held to 2-signal confluence gate.

### Fix Options
**Option A** (preferred): Add underscore-format mirror keys to GOOD_STANDALONE_SIGNALS:
```python
GOOD_STANDALONE_SIGNALS = {
    'accel_300_long':  {'alt': 'accel-300+',  ...},
    'accel_300_short': {'alt': 'accel-300-',  ...},
    'percentile_rank_long':  {'alt': 'pct-hermes+', ...},
    'percentile_rank_short': {'alt': 'pct-hermes-', ...},
    'velocity_long':   {'alt': 'vel-hermes+',  ...},
    'velocity_short':   {'alt': 'vel-hermes-',  ...},
    'mtf_zscore_long':  {'alt': 'hzscore-',   ...},  # note: hzscore is mtf_zscore
    'mtf_zscore_short': {'alt': 'hzscore+',   ...},
    ...
}
```

**Option B**: Make `_signal_type_key()` return hyphen format for known signal types.

### Files
- `/root/.hermes/scripts/signal_compactor.py` — GOOD_STANDALONE_SIGNALS dict, `_signal_type_key()` function

---

## PRIORITY 2: Remove RS ATR band filter — rs.py (15 min)

### Problem
`rs.py` lines 210-211, 379, 406:
```python
_RS_ATR_BAND_SOFT_MIN  = 0.30  # below this: too close to call
_RS_ATR_BAND_SOFT_MAX  = 0.60  # above this: comfortably outside, safe
```
If price is 0.30–0.60 ATRs from a level → **REJECTED**. In a trending market, price is usually within 0.30–0.60 ATR of a structural level. This is filtering out most valid RS signals.

Distance from level is **not** a quality indicator — it's the opposite. Price bouncing precisely off a level at 0.20 ATR distance is a **better** signal than drifting to 0.80 ATR.

### Fix
Remove the 0.30–0.60 ATR band rejection entirely. Keep the `_RS_ATR_BAND_SOFT_MIN/MAX` as **confidence modifiers only** (closer = higher confidence bonus), not as a binary accept/reject gate.

### Files
- `/root/.hermes/scripts/signals/rs.py` — `_check_atr_proximity()` and `detect_rs_signal()` lines ~379, ~406

---

## PRIORITY 3: Re-enable hwave signals (10 min)

### Problem
`hwave+,hzscore+` was the **best SHORT combo** in the dataset: 50% WR, avg +27.4% peak, hit AXS +153% (Apr 17).
hwave appears to have been removed from `compute_score` around Apr 18.
No hwave signals exist in the DB (0 rows for hwave signal_type).

### Fix
Check if `hwave` was intentionally disabled or accidentally removed. Re-enable if appropriate. If `compute_score` in signal_compactor.py or decider_run.py removed hwave, add it back with proper SHORT co-signal pairing.

### Files
- `/root/.hermes/scripts/signal_compactor.py` — `compute_score()` function
- `/root/.hermes/scripts/signals/hwave*.py` — hwave signal modules

---

## PRIORITY 4: Reduce counter_flip frequency / make regime-dependent (20 min)

### Problem
DASH: counter_flip_short fired 14x while accel_300_long fired 2x. In bullish regime, counter_flip keeps blocking SHORTs unnecessarily.
counter_flip is a counter-regime signal — it should NOT fire in a confirmed bullish regime.

### Fix
Add regime check to counter_flip signal:
- If `regime='BULL'` → reduce counter_flip_short penalty by 80%
- If `regime='BEAR'` → full counter_flip_short penalty
- Or: make counter_flip fire every 15 min instead of every 5 min (reduce spam)

### Files
- `/root/.hermes/scripts/signals/counter_flip_signal.py` — signal generation
- `/root/.hermes/scripts/signal_compactor.py` — counter_flip penalty in `compute_score()`

---

## PRIORITY 5: Speed up RS signal scanning (10 min)

### Problem
With 4-hour RS cooldown and 191 tokens, RS can only fire ~1,146 times/day. If scan runs every 15 min, most cooldown windows expire without a valid signal opportunity.

### Fix
Reduce RS cooldown from 4 hours to 2 hours, OR increase scan frequency to every 5 min.

### Files
- `/root/.hermes/scripts/signals/rs.py` — `RS_COOLDOWN_HOURS = 4.0`
- `/root/.hermes/scripts/signals/__init__.py` — RS scan interval

---

## PRIORITY 6: Fix accel-300+ premature close problem (20 min)

### Problem
accel-300+ winners are being closed at +4-5% (PM profit target) while price continues to +250-500%. Position manager is cutting winners short.

Example: GRIFFAIN accel-300+,rs-s150 had +526% peak but was closed at +4%.

### Fix
Add a "strong co-signal" override to PM:
- If signal contains `rs-s{touch}` where touch >= 16 → increase TP from k_tp × 1.25 to k_tp × 3.0
- If signal contains `trend_purity+` → increase TP multiplier
- Or: add `is_mega_win=True` flag when RS touch count >= 16

### Files
- `/root/.hermes/scripts/position_manager.py` — TP logic
- `/root/.hermes/scripts/signal_compactor.py` — pass co-signal info to PM

---

## PRIORITY 7: Add RS touch count to signal type for merge sorting (10 min)

### Problem
`rs-s48` and `rs-s150` have the same signal_type `'support_resistance'` and same direction. The touch count (signal quality) is lost in the merge.

### Fix
Modify `rs.py` `detect_rs_signal()` to encode touch count in the source field:
- Current: `source = 'rs-s48'`
- Already correct! The issue is signal_compactor needs to **read** touch count from source and use it for co-signal quality scoring.

Add a `touch_count` field to the signal dict that signal_compactor reads:
```python
signal = {
    'source': 'rs-s48',
    'touch_count': 48,  # ADD THIS
    'direction': 'LONG',
    ...
}
```

### Files
- `/root/.hermes/scripts/signals/rs.py` — `detect_rs_signal()` return dict
- `/root/.hermes/scripts/signal_compactor.py` — co-signal scoring that reads touch_count

---

## CONFLUENCE COLLAPSE — why hot-set stays empty

**Root cause chain:**
1. GOOD_STANDALONE_SIGNALS bypass broken → single-source signals held to 2-signal gate
2. Different signal generators fire at different intervals (pct-hermes 1m, hzscore 5m, accel-300 5m)
3. Merging requires simultaneous occurrence → very rare in practice
4. 141 signals SKIPPED with empty rejection_reason → signals reaching the gate but failing silently
5. 0 signals ever reached APPROVED → all 35 EXECUTED bypassed hot-set entirely

**Fix priorities 1-5 above** should resolve confluence collapse by:
- Letting strong single signals bypass (Priority 1)
- More RS signals firing as co-signals (Priority 2)
- hwave back as SHORT co-signal (Priority 3)
- counter_flip less aggressive (Priority 4)
- RS firing more often (Priority 5)

---

## TESTING PLAN

For each priority fix:
1. Run signal scan for 1 token manually → verify signal appears in DB
2. Check signal_compactor log output → verify merge/approval logic
3. Check hot-set.json → verify token appears
4. Compare before/after WR for affected signal types

**Key metrics to track:**
- `signal_outcomes` WR per signal type (target: >40% WR)
- `signal_outcomes` avg_pnl per signal type (target: >0)
- hot-set.json age and count (target: <5 min age, 5-10 tokens)
- APPROVED signal count (target: >0/day)
