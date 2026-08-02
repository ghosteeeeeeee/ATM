# Cascade-Wave Implementation Analysis & Plan

## Goal

Understand the existing cascade-wave close implementation, assess what is/isn't active, and plan what to re-enable or improve.

---

## What Exists

There are **two separate cascade mechanisms** in the system:

### 1. Cascade Direction Flip (position_manager.py)
**Purpose:** Close a position when an aggressive move in the opposite direction is detected across timeframes.

**How it works (`position_manager.py` ~line 2182):**
- Smaller TFs (15m, 1h) flip direction BEFORE larger TFs (4h) confirm
- If `cascade['cascade_active']` = True AND `cascade['cascade_direction']` ≠ current position direction → FLIP
- Cascade detected via `macd_rules.cascade_entry_signal()`:
  - 15m flips first (lead TF)
  - 1h follows
  - 4h confirms

**Logic from `candle_db.detect_cascade_direction()`:**
```
Bearish cascade: 15m flips FIRST → 1h follows → 4h confirms
Bullish cascade:  15m flips FIRST → 1h follows → 4h confirms
Cascade ACTIVE = lead TF (smallest) has flipped + at least one larger TF still in old direction
```

**Status: DISABLED** — `CASCADE_FLIP_ENABLED = False` at line 80 of position_manager.py

---

### 2. MACD MTF Alignment Cascade Flip (position_manager.py)
**Purpose:** Ultra-confirmed reversal when ALL 3 TFs (4H/1H/15m) unanimously flip direction.

**How it works (line ~2145):**
- Only active for tokens in `MACD_CASCADE_FLIP_TOKENS = ['IMX', 'SOPH', 'SCR']`
- For these tokens only, if `compute_mtf_macd_alignment()` shows all 3 TFs are now bearish (for LONG) or bullish (for SHORT) → immediate cascade flip at 95% confidence
- This is the most aggressive form — all TFs agree = extremely rare = high conviction

**Status: DISABLED** — `CASCADE_FLIP_ENABLED = False`

---

### 3. Cascade in Signal Generation (signal_gen.py)
**Purpose:** Boost signal confidence when cascade is confirmed.

**How it works (line ~1702-1712):**
- `cascade_entry_signal()` is called for every token during signal generation
- If cascade direction matches the signal direction → +10 confidence bonus
- If cascade direction is OPPOSITE → signal is BLOCKED
- This is the **entry-time** cascade filter — prevents you from entering against an active cascade

**Status: ✅ ACTIVE (not gated by CASCADE_FLIP_ENABLED)**

---

### 4. Cascade CLI / Debug Tool (candle_db.py)
- `detect_cascade_direction()` — the core detection function
- CLI: `python3 candle_db.py --cascade <TOKEN>` — shows cascade state for any token

---

## Current Gaps

### Gap 1: `CASCADE_FLIP_ENABLED = False`
The exit-time cascade flip is completely disabled. This means even when the system correctly detects a cascade, it won't act on it.

**Question:** Why was it disabled? Was there a cascade flip that went wrong?

---

### Gap 2: `MACD_CASCADE_FLIP_TOKENS` is only 3 tokens
Only `['IMX', 'SOPH', 'SCR']` get the ultra-confirmed all-TF cascade flip. This should probably cover more tokens or be configurable.

---

### Gap 3: Cascade flip losses aren't tracked well
The cascade flip mechanism doesn't update the trade's PnL history or record that a cascade flip occurred. `cascade-reverse-` source prefix exists in code (used in ATR updates and SL handling) but the flip itself may not be logged correctly.

---

## Proposed Plan

### Step 1: Diagnose why `CASCADE_FLIP_ENABLED` was disabled
Search trading history and logs for cascade flip events to understand why it was turned off.

**Action:** `grep -r "CASCADE_FLIP" /root/.hermes/logs/` — look for disable/enable events

---

### Step 2: Re-enable cascade flip with safeguards

**Change `position_manager.py` line 80:**
```python
CASCADE_FLIP_ENABLED = True   # re-enable
```

**Add a conservative loss guard** (currently cascade flip can fire even on small losses):
- Only flip if loss >= `CASCADE_FLIP_ARM_LOSS` (-0.25%) AND speed is INCREASING in the opposite direction
- This ensures the cascade has momentum behind it, not just a noise spike

---

### Step 3: Extend `MACD_CASCADE_FLIP_TOKENS`
Add high-conviction tokens based on recent cascade performance. Tokens that have shown clean multi-TF reversals.

**Default to:** All tokens that have `speed_percentile >= 70` and have demonstrated clean TF cascades in backtesting.

---

### Step 4: Add cascade flip logging
- Log every cascade flip attempt (armed, triggered, succeeded, failed)
- Track cascade flip PnL separately from normal closes
- Add to brain/trading.md

---

### Step 5: Verify cascade detection is working correctly
Test the cascade detection on recent trades that had reversals.

**Action:** Run `python3 candle_db.py --cascade <TOKEN>` on tokens that reversed recently:
```bash
python3 candle_db.py --cascade ORDI   # showed wave_turn_bottom exit
python3 candle_db.py --cascade DYM    # was in hot-set during regime shift
python3 candle_db.py --cascade SAGA   # showed "bottoming" wave_phase
```

---

## Files Likely to Change

| File | Change |
|------|--------|
| `position_manager.py` | Set `CASCADE_FLIP_ENABLED = True`, add speed guard, add logging |
| `macd_rules.py` | Potentially extend `MACD_CASCADE_FLIP_TOKENS` list |
| `brain/trading.md` | Document cascade flip performance and re-enablement |

---

## Validation Steps

1. `python3 candle_db.py --cascade ORDI` — verify cascade detection works
2. Check pipeline log for `[CASCADE FLIP]` entries after re-enable
3. Monitor that cascade flips are not generating duplicates (the DASH phantom close issue)
4. Compare cascade flip PnL vs holding through the reversal

---

## Risks

1. **Cascade flip creates phantom closes** — if cascade closes the position but HL doesn't confirm the close, guardian might re-open. Need to verify the cascade flip path uses the same `close_position()` → `mirror_open()` → DB insert pattern that was fixed for profit-monster.
2. **Cascade flip during high volatility** — might flip back immediately if it's just a quick spike. The speed-increasing guard addresses this.
3. **Re-enabling without understanding why it was disabled** — must check logs first.

---

## Open Questions

1. Why was `CASCADE_FLIP_ENABLED = False`? Need to check logs before re-enabling.
2. Should cascade flip be a hard-close (just close, no re-entry) or a flip (close + enter opposite)?
3. Should `MACD_CASCADE_FLIP_TOKENS` be expanded to all tokens or kept selective?
