# EMA Angle Signal Audit — 2026-05-16

## Bugs Fixed

### Bug 1 — `is_closed=1` filter excluded 42 tokens entirely
**File:** `ema_angle.py`, line 93 (`_get_1m_prices`)
**Before:** `WHERE token=? AND is_closed=1`
**After:** `WHERE token=?`

**Root cause:** PURR had 17,340 rows ALL with `is_closed=0` — completely invisible. 42 tokens had only open (unclosed) candles.

**Also fixed:** Token scan query at line 332 — `WHERE is_closed=1 AND ts > ?` → `WHERE ts > ?` (inconsistent after Bug 1 fix)

**Note:** Consistent with rs.py, ma_cross.py, guppy.py — all read all rows. `15m_regime_scanner.py` uses `is_closed=1` intentionally for completed-candle slopes.

---

### Bug 2 — `ABS_ANGLE_FLOOR = 0.003°` hard floor blocked LONG signals
**File:** `ema_angle.py`, line 191 (was)
**Before:** `angle_meets_minimum = latest_angle >= max(p75, ABS_ANGLE_FLOOR)` where `ABS_ANGLE_FLOOR = 0.003`
**After:** `angle_meets_minimum = latest_angle >= p75`

**Root cause:** PURR p75=0.002° < 0.003° floor. SHORT has no equivalent floor. LONG should mirror SHORT pattern.

**PURR reference trace:**
- p25=-0.002403°, p75=0.002003°
- First signal fires May 14 05:44 UTC: angle=0.002083°, price=0.060455, above EMA300, speed=0.0018401 (>0.0005)
- Without fix: all blocked by 0.003° floor

---

### Bug 3 — In-memory cooldown before DB write (P2)
**File:** `ema_angle.py`, lines 293-299, 412
**Before:** `_cooldown_ok()` wrote `_last_signal_ts` before `add_signal()` confirmed
**After:** `_cooldown_ok()` read-only; `_mark_signal()` called only after `add_signal()` succeeds

## Verified No Bugs

Angle/speed computation ✅ | LONG price_above_ema guard ✅ | SHORT `angle <= p25` (no floor) ✅ | Confidence continuous bonuses ✅ | Thread safety ✅

## Constants Check (main session)
```
grep -n "SIGNAL_SOURCE_BLACKLIST|CONFLUENCE_REQUIRED|LONG_BLACKLIST|SHORT_BLACKLIST" /root/.hermes/scripts/hermes_constants.py
```
All non-empty ✓