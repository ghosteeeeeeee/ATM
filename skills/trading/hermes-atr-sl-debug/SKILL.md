---
name: hermes-atr-sl-debug
description: Debug why ATR TP/SL is not catching profits or tightening stops on Hermes positions. Investigates trailing stop disable, TP/SL computation gaps, and cascade flip eligibility.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [trading, debug, atr, trailing-stop, position-manager]
    input_files: []
---

# Hermes ATR SL/TP Debug

Investigate why ATR-based stop loss or take profit is not firing on a position, or why trailing SL is not tightening as position moves into profit.

## Investigation Pattern

### Step 1: Gather Position State (DB + Logs)

```python
# Check current position state in brain DB
SELECT id, token, direction, entry_price, stop_loss, target,
       pnl_pct, trailing_stop_pct, trailing_stop_price,
       trailing_activation, highest_price, hl_sl_order_id, hl_tp_order_id,
       stop_loss, target, current_price
FROM trades WHERE token='COIN' AND status='open' ORDER BY id DESC LIMIT 2;

# Check pipeline ATR computation logs (shows computed SL/TP each cycle)
grep -a "COIN" /root/.hermes/logs/pipeline.log | grep -a "ATR"

# Check guardian logs for position management
grep -a "COIN" /root/.hermes/logs/sync-guardian.log | head -20
```

### Step 2: Check Trailing Stop Status (position_manager.py)

Trailing stop is the mechanism that tightens SL as position moves into profit.

```python
# In position_manager.py line ~2298:
trailing_active = False  # HARD-CODED DISABLED
```

If `trailing_active` is always False, the trailing SL mechanism is **completely disabled** — SL only moves via `_collect_atr_updates()` which uses a fixed k multiplier, NOT a trailing approach.

### Step 3: Check TP/SL Computation — ANIME Edge Case

ANIME entry had `entry_price=0E-8` (null) because HL returned 0 at entry time. This causes:
- TP computed as `entry - k * ATR` → 0 (TP unset, 0E-8 in DB)
- SL computed as `entry + k * ATR` → WRONG (SL above entry, not below)

```python
# ANIME entry log shows:
[WARN] SL sanity check triggered for SHORT ANIME, reset to 1%
```

Always verify `target` and `stop_loss` are non-zero in DB after entry.

### Step 4: Check Cascade Flip Eligibility

Cascade flip is a faster exit path that can close positions before ATR SL.

```python
# In position_manager.py:
MACD_CASCADE_FLIP_TOKENS = ['IMX', 'SOPH', 'SCR']
```

If token is NOT in this list, cascade flip cannot fire for it.

```python
CASCADE_FLIP_ARM_LOSS = -0.0025  # -0.25% — position must be at this loss to arm
```

### Step 5: Check ATR HL Orders Kill Switch

```python
# In position_manager.py:
ATR_HL_ORDERS_ENABLED = False
```

When False, no HL stop-loss or take-profit orders are placed on Hyperliquid — only internal DB tracking.

## Key Findings (2026-04-18)

1. **Trailing stop is hardcoded to False** (position_manager.py:2298) — trailing SL that tightens in profit is disabled
2. **ANIME TP was 0E-8** because entry price was null at time of entry — always verify TP/SL after entry
3. **COMP TP was $22.76** (far from $25.35 current) — TP was distant target, not trailing. SL was $25.59, still above current price (SL was protective, not profit-taking)
4. **COMP not in MACD_CASCADE_FLIP_TOKENS** — cascade flip not eligible
5. **hl_sl_order_id and hl_tp_order_id are None** for these trades — ATR_HL_ORDERS_ENABLED=False means no HL order placed

## Exit Priority Race Condition (2026-04-18)

Exit priority order in `position_manager.py` (line 2260-2265):
1. ATR TP/SL hit — checked FIRST (line 2288)
2. MACD cascade flip
3. Cascade flip
4. Wave turn — checked FOURTH (line 2451)

**Problem:** If wave_turn conditions exist AND ATR SL is also hit in the same cycle, ATR fires first and closes the position BEFORE wave_turn is ever evaluated. wave_turn never gets a chance.

**Code evidence:**
- Line 2288: `atr_hits = check_atr_tp_sl_hits([pos])`
- Line 2289-2295: ATR closes position and `continue` — skips ALL subsequent exit checks
- Line 2451: `if SPEED_TRACKER is not None:` — wave_turn check never runs for this position this cycle

**Real example:** Trade 6422 (APE LONG) closed at 18:39:12 with `exit_reason=atr_sl_hit` — wave_turn conditions existed but ATR fired first.

**Why this matters:** wave_turn is documented as "higher conviction" than stale winner/loser exits, but ATR always wins because it's checked first.

**Fix options:**
1. Move wave_turn check BEFORE ATR TP/SL check (reorder lines 2283-2295 and 2434-2507)
2. In ATR hit check: if wave_turn is imminent AND position is in profit, skip ATR this cycle
3. Add a "pending exit signal" flag that ATR respects before firing

## Expected vs Actual Behavior

- Expected: SL tightens as position goes into profit (trailing)
- Actual: SL is recomputed each cycle via fixed-k ATR only; when k increases, SL actually WIDENS (moves away from price)
- TP: computed at entry only, never updates

## Expected vs Actual Behavior

- Expected: SL tightens as position goes into profit (trailing)
- Actual: SL is recomputed each cycle via fixed-k ATR only; when k increases, SL actually WIDENS (moves away from price)
- TP: computed at entry only, never updates

## Fix Direction

To make SL catch profits: implement a trailing SL that uses `highest_price` (for LONG) or `lowest_price` (for SHORT) to tighten stop as position moves in profit direction. For LONG: best price = highest (the peak — SL trails UP from it). For SHORT: best price = lowest (the trough — SL trails DOWN from it). Currently `highest_price`/`lowest_price` fields exist in DB but were being used incorrectly (reversed). The fix (2026-04-19) corrects the anchor in `_collect_atr_updates()`.

---

## Root Cause Found: `ref_price = current_price` Bug (2026-04-19)

**Affected function:** `_collect_atr_updates()` in `position_manager.py` (~line 1551)

**The bug:**
```python
# OLD (WRONG):
ref_price = current_price if (current_price and float(current_price) > 0) else _entry
```

When price moves favorably (e.g., SHORT: price drops), `current_price` also drops. This means:
- SHORT entry at 0.026301, price drops to 0.025618
- `ref_price = 0.025618` (current price — the DROP, not the PEAK)
- SL = `0.025618 + 2.25 * ATR` → SL stays near entry-level, never tightens
- The SL actually WIDENS because current_price IS the drop

**The fix — 3 coordinated changes:**

1. **SELECT peaks** in `get_open_positions()` (~line 260):
   Add `highest_price, lowest_price` to the SELECT so they're available in the position dict.

2. **Write peaks** in `refresh_current_prices_from_hl()` (~line 2159):
   Track and persist to DB each cycle:
   - SHORT: `highest_price = max(highest_price, current)`
   - LONG: `lowest_price = min(lowest_price, current)`
   This ensures peak accumulates across ALL cycles (not cycle-local).

3. **Use peaks as anchor** in `_collect_atr_updates()` (~line 1590):
   ```python
   # NEW (CORRECT — fixed 2026-04-19):
   if direction == "SHORT":
       # SHORT wins when price falls — use the lowest price seen as profit anchor
       ref_price = _peak_low if _peak_low > 0 else (current_price or _entry)
   elif direction == "LONG":
       # LONG wins when price rises — use the highest price seen as profit anchor
       ref_price = _peak_high if _peak_high > 0 else (current_price or _entry)
   ```
   **Key insight:** For SHORT, best price = lowest (price fell to our favor). For LONG, best price = highest (price rose to our favor). The old code had it reversed — SHORT used highest_price and LONG used lowest_price, which made the trailing SL completely broken.

**Why the fix is durable:** `highest_price`/`lowest_price` are already DB columns — nothing was writing to them. The fix wires up the existing columns instead of adding new ones. `refresh_current_prices_from_hl` runs every cycle so the peak grows, and `_collect_atr_updates` runs after so it reads the current peak.

**Key symptom to detect:** For a SHORT position that dropped from entry 0.026301 to 0.025618:
- OLD (wrong): `ref=0.025618` (current_price = the drop, not the peak — SL barely tightens)
- NEW (correct): `ref=0.025618` for SHORT now means `lowest_price=0.025618` (the best price seen = the trough) — SL computed as `0.025618 + ATR*k` trails down from the trough, catching profits properly.

For a SHORT that pumped first to 0.027 then dropped to 0.025:
- OLD (wrong): `ref=0.025` (current = the drop, peak wasn't tracked correctly)
- NEW (correct): `ref=0.027` = `highest_price` — SL trails down from the peak of 0.027

**Verification query:**
```sql
SELECT token, direction, entry_price, highest_price, lowest_price, current_price, stop_loss
FROM positions WHERE token='COIN';
-- For SHORT: lowest_price should be non-null and reflect the lowest price seen
-- For LONG: highest_price should be non-null and reflect the highest price seen
-- stop_loss should be closer to the BEST price (lowest for SHORT, highest for LONG) than to entry

---

## Finding 2: Exit Price = 0 When ATR SL Closes (2026-04-19)

**Symptom:** Position closed via `atr_sl_hit` but `exit_price=0` in DB and `pnl_pct=0`. PnL not recorded.

**Root cause:** `_get_hl_exit_price()` in `guardian.py` has no fill data after the close order executes. Falls back to `0.0`. The guardian never re-queries for fill price after close.

**Evidence:**
```
GRIFFAIN SHORT entry=0.022005 exit=0 pnl=0% reason=atr_sl_hit
XRP      SHORT entry=1.4344 exit=0 pnl=0% reason=atr_sl_hit
ASTER    SHORT entry=0.67376 exit=0 pnl=0% reason=atr_sl_hit
```

All three ATR stops fired correctly (SL was hit), but the exit fill was never captured. The positions are closed, the SL worked — only the PnL recording failed.

**Fix:** After a successful close order, the guardian should:
1. Query `get_fills()` with a small time window around the close timestamp
2. If no fills found, use the SL trigger price (`stop_loss` from DB) or current market price as fallback
3. Never write `0.0` as exit_price — at minimum use `current_price`

**Code location:** `hl-sync-guardian.py` `_get_hl_exit_price()` — the fallback to `0.0` should be replaced with `current_market_price` (available via the `coin` parameter).

---

## Finding 3: HL Request Rate Limit Blocks close_position (2026-04-19)

**Symptom:** Guardian attempts `close_position` but HL returns:
```
"Too many cumulative requests sent (85608 > 84537)"
```
Error: `HL error: 500 - Internal error. {"code":-10002,"msg":"Too many cumulative requests sent..."}`

**Root cause:** HL rate-limits by cumulative request count over the session. Guardian uses ~60 requests/min during active trading. At 84537/84537 credits, no new write operations (close, open, modify) are allowed until more volume trades.

**Impact:** Positions that should close (ATR hit, manual close) stay open. Guardian keeps retrying but fails. Request credits only increase when the account executes real trades.

**No programmatic fix available** — this is an HL account-level limit. Workarounds:
1. Reduce guardian polling frequency (fewer `get_open_positions` + `get_trade_history` calls per cycle)
2. Use batched queries instead of per-position queries
3. For paper trading: accept that rate limit will periodically block closes; the next successful trade after rate limit clears will close the stuck position
4. For live trading: pre-allocate more request budget by ensuring the account has sufficient trading volume

**Detection:**
```bash
grep "Too many cumulative requests" /root/.hermes/logs/sync-guardian.log
```

---

## Finding 4: trades.json Has Stale ATR Values — Step10 Disabled (2026-04-19)

**Symptom:** `trades.json` shows SL/TP values that don't match the fresh values in PostgreSQL. Frontend or other consumers see outdated stop-loss levels.

**Root cause:** In `hl-sync-guardian.py`, `Step 10` of the reconcile loop calls `_update_trades_json_atr()` but it was intentionally disabled:
```python
# Line ~2727:
# Step 10: ATR reconcile DISABLED — position_manager is sole ATR engine
# _update_trades_json_atr()  # DISABLED
```

Meanwhile, `position_manager` correctly writes fresh SL/TP to PostgreSQL every cycle via `_collect_atr_updates()`. But `trades.json` (written by `signal_compactor.py`) is never updated with these values.

**Fix options:**
1. **Re-enable `_update_trades_json_atr()`** — read fresh values from postgres and copy into `trades.json` open array. This is the minimal fix.
2. **Direct write from position_manager** — have `position_manager` write directly to `trades.json` after updating postgres, bypassing the guardian entirely.

**Key files:**
- `hl-sync-guardian.py` line ~2727 — `_update_trades_json_atr()` disabled, needs re-enabling
- `position_manager.py` `_collect_atr_updates()` — correctly computes and writes ATR to postgres
- `/var/www/hermes/data/trades.json` — the stale file that needs syncing
- `hermes-trades-api.py` `get_trades()` — reads from postgres (correct values), so API consumers get fresh data

**Note:** `hermes-trades-api.py` reads from postgres, so any API consumer gets correct values. `trades.json` is a separate file that may be consumed by other processes (e.g., frontend dashboards). Both need to be kept in sync.

**Relevant context:** "position_manager is sole ATR engine" was set to avoid duplicate ATR writes. But the side effect is that `trades.json` ATR values go stale. The proper architecture is: `position_manager` writes ATR to postgres → `_update_trades_json_atr()` reads from postgres and updates `trades.json`. This was the intended design before Step10 was disabled.

---

## Finding 5: Counter-Regime Signals Pass Through — LONGs in SHORT_BIAS (2026-04-19)

**Symptom:** GAS (LONG), INIT (LONG), AVNT (LONG) opened while market regime is SHORT_BIAS. These are counter-regime signals that may be unwanted.

**Root cause:** Per memory: "Counter-regime signals: DO NOT block them. Let per-coin regime filter decide." The regime filter does NOT hard-block counter-regime signals — it passes them through with possibly lower confidence, but they can still trigger entries.

**Evidence:**
```
GAS      LONG signal: hzscore-,pct-hermes-,vel-hermes-  (in SHORT_BIAS regime)
INIT     LONG signal: hzscore+,pct-hermes+,vel-hermes+  (in SHORT_BIAS regime)
AVNT     LONG signal: hzscore+,pct-hermes+,vel-hermes+  (in SHORT_BIAS regime)
```

**Memory says:** "Counter-regime signals: DO NOT block them. Let per-coin regime filter decide. Low-conf counter-trend = de-escalation (weaker signal). Strong enough counter-trend = escalation (replaces original direction). Never hard-block anti-regime signals."

**This is working as designed** — the system intentionally allows counter-regime signals through. If T wants to block them entirely in SHORT_BIAS, that would be a new decision. The `regime_filter.py` (or wherever regime checking happens) would need a hard-block flag added.

**If blocking is desired:** Add a `HARD_BLOCK_COUNTER_REGIME = True` flag and set it to True during SHORT_BIAS. When False (current behavior): de-escalate by reducing size or skipping entry entirely.

---

## Finding 6: MIN_ATR_PCT Floor Too Loose When in Profit (2026-04-21)

**Symptom:** Open positions in profit (+1-10%) have SL 0.5-1% away from current price — too much giveback when you're up. For ICP (ATR% = 0.44%), the floor was binding above the actual ATR%.

**Root cause:** `MIN_ATR_PCT` acts as a floor — computed ATR SL% can't go below this even if ATR is tiny. Two definitions in position_manager.py:
- Line 1406 in `_compute_dynamic_sl()`: `MIN_ATR_PCT = 0.005` (0.50%)
- Line 1919 in `get_trade_params()`: `MIN_ATR_PCT = 0.010` (1.0%)

When ATR% < floor, the floor "wins" and the SL is wider than ATR would otherwise dictate.

**Diagnosis query:**
```python
# Compute effective SL% for each open position
atr = ATR_cache[token]['atr']
current = position['current_price']
atr_pct = atr / current
k = _atr_multiplier(atr_pct)  # 1.0 if <1%, 2.0 if 1-3%, 2.5 if >3%
atr_dist = k * atr
eff_sl_pct = atr_dist / current
is_floor_binding = eff_sl_pct < MIN_ATR_PCT  # True = floor is forcing wider SL
```

**Tokens where floor was binding (2026-04-21):**
- ICP: ATR% = 0.44% < 0.50% floor → floor forced SL to 0.50% instead of actual 0.44%
- Lowering floor to 0.30% let ICP use its actual ( ATR% = 0.44%

**Fix applied:** Changed both `MIN_ATR_PCT` from 0.50% → 0.30% (and the 1.0% one from get_trade_params to 0.30%).

```python
# Line 1406 and 1919 in position_manager.py:
MIN_ATR_PCT = 0.003  # was 0.005 (0.50%), now 0.30%

# Also update MIN_ATR_PCT_TP at line 1437 if TP floor needs tightening:
MIN_ATR_PCT_TP = 0.003  # was 0.0075 (0.75%)
```

**Effect:** For ICP (ATR% = 0.44%, ATR = $0.01077, current $2.445):
- Old: SL = $2.4329 (0.50% floor)
- New: SL = $2.4344 (0.44% actual ATR) → saves $0.0015/coin

**Key insight:** `MIN_ATR_PCT` is T's "book profit fast" lever — lower = tighter stops for all tokens, especially meaningful when up 3-10%. The floor exists to prevent noise-triggered stops on low-volatility tokens. When ATR% itself is below the floor, the floor is the stop — lowering it directly tightens the stop.

**Note:** `_atr_sl_k_scaled()` can return k < 1.0 in ACCELERATING phase, but the floor still caps how tight effective_sl_pct can go. For ACCELERATING phase with speed_percentile >= 70: mult = 1.0 already. To go tighter than ATR% requires lowering MIN_ATR_PCT.

---

## Finding 7: T's "Book Profit Fast" SL Philosophy — Final Parameters (2026-04-22)

**T's philosophy:** "first candle against us we're out, book profit fast." Tight stops (SL floor 0.75%), quick profit-taking (TP floor 0.75%). Aggressive short-term exits. After empirical testing across ORDI, PEOPLE, ICP, BTC, LIT:

**Final parameter changes applied:**

1. **`MIN_ATR_PCT`** in `_compute_dynamic_sl()` (line 1406) and `get_trade_params()` (line 1919):
   - 0.50% (original) → 0.30% → 0.10% → **0.05%** (final)
   - 0.05% = $5 on $10K, $0.05 on $100 — "if we're wrong, we're out fast"

2. **ACCELERATING phase k multipliers** in `_atr_sl_k_scaled()` (line 1241-1249):
   ```python
   elif phase == 2:  # ACCELERATING
       if stalling:
           mult = 0.25    # was 0.5
       elif speed_percentile >= 70:
           mult = 0.15    # was 0.5
       else:
           mult = 0.10    # was 0.25
   ```
   - All mults < 1.0 → SL distance is fraction of ATR, not multiple of ATR
   - Combined with floor 0.05%: BTC (ATR% 0.41%) gets exactly 0.05% floor at k=0.1

3. **Effect on open positions (2026-04-22):**
   | Token | ATR% | Old SL | New SL (k=0.1 + floor) | Locked in |
   |-------|------|--------|------------------------|-----------|
   | BTC | 0.41% | 0.69% ($523) | 0.05% ($38) | 93% |
   | ICP | 0.44% | 0.50% (floor) | 0.05% (floor) | ~90% |
   | ORDI | 0.83% | 0.87% | 0.10% (ATR) | ~88% |
   | PEOPLE | 0.61% | 0.63% | 0.10% (ATR) | ~84% |
   | LINK | 0.46% | 0.47% | 0.05% (floor) | ~90% |

---

## Finding 9: SHORT SL Formula Was Inverted — Dead Code + Wrong Path (2026-04-23)

**Two critical bugs found when T complained DOT SHORT SL was "too loose":**

### Bug 1: `_compute_dynamic_sl()` is DEAD CODE

The function at `position_manager.py` line ~1406 is **never called** anywhere in the codebase. The actual ATR SL computation is inline inside `_collect_atr_updates()` (line ~1593-1635). Any fix applied to `_compute_dynamic_sl()` has ZERO effect.

**Verification:**
```bash
grep -rn "_compute_dynamic_sl\|_compute_dynamic_tp" /root/.hermes/scripts/ --include="*.py" | grep -v "def _compute_dynamic"
```
Only the definition lines appear — zero call sites.

### Bug 2: SHORT SL Formula Was Treating SHORT Like LONG

In `_collect_atr_updates()` lines ~1630-1637, the SHORT branch computed:
```python
new_sl = round(ref_price * (1 + effective_sl_pct), 8)
```
For a SHORT position: `ref_price = lowest_price = current_price` (when profitable).
So `new_sl = current_price * (1 + sl_pct)` — SL is BELOW current price.

This means for DOT SHORT (entry=1.2495, current=1.23555):
- SL = 1.242235 — **below current price** — a further drop would trigger the stop!
- The formula was treating SHORT the same as LONG (SL below price = catch the drop).

**Correct SHORT behavior:** SL should be ABOVE current price (catches rallies against the short). As price falls favorably, SL trails down with it.

### Bug 3: SHORT Trailing Lock Compared Wrong Values

Lines ~1697-1706 had a trailing lock that compared `sl_at_ref = ref_price * (1 + sl_pct)` against `current_sl`. But `new_sl` (the actual computed SHORT SL) was `current_price * (1 + MIN_SL_PCT_TRAILING)`. These aren't the same formula — the comparison was meaningless and always evaluated to "loosening" because the new formula produced a different number.

### Fix Applied

**In `_collect_atr_updates()` lines ~1631-1637:**
```python
# SHORT: SL = current_price + MIN_SL_PCT buffer (trailing buffer above current price)
# As price falls, SL falls proportionally — locks in profit on each dip
new_sl = round(current_price * (1 + MIN_SL_PCT_TRAILING), 8)
```
And the trailing lock (lines ~1691-1708) was simplified to:
```python
if new_sl >= current_sl:
    new_sl = current_sl    # would loosen — block it
    needs_sl = False
else:
    needs_sl = True        # new_sl < current_sl — tighten, accept
```

**MIN_SL_PCT_TRAILING raised** from 0.15% → **0.50%** (T's "acceleration phase" philosophy).

**Result for DOT SHORT:**
- OLD SL: 1.242235 (below current — WRONG)
- NEW SL: 1.241728 (0.5% above current — correct, trails with price)

### Architecture Note: Two ATR Updaters (one defunct)

| Script | Timer | Writes to | Status |
|--------|-------|-----------|--------|
| `position_manager.py` | `hermes-pipeline.timer` (1 min) | brain DB | ACTIVE — sole ATR engine |
| `update-trades-json.py` | standalone (cron?) | `trades.json` | ACTIVE — reads DB, copies to JSON |
| `hermes-atr-sl-updater.timer` | orphaned | — | DEFUNCT — service deleted, symlink remains |

No conflict — `position_manager` writes to DB, `update-trades-json.py` reads DB and writes JSON. `hermes-atr-sl-updater.timer` is a stale symlink that can be cleaned up (`/etc/systemd/system/timers.target.wants/hermes-atr-sl-updater.timer` → points to deleted service).

## Finding 8: Cascade Flip Not Firing on LINK — ARM/TRIGGER Threshold Gap

**Symptom:** LINK SHORT at -0.32% loss, signal clearly wrong. Cascade flip didn't fire.

**Root cause — cascade flip state machine is too slow:**
```
CASCADE_FLIP_ARM_LOSS        = -0.25%  # must be at THIS loss to arm
CASCADE_FLIP_TRIGGER_LOSS     = -0.50%  # fires at this loss (normal momentum)
CASCADE_FLIP_HF_TRIGGER_LOSS  = -0.35%  # fires at this loss (speed pctl > 80)
```

LINK at -0.32% is:
- ARMED: loss (-0.32%) < arm (-0.25%) ✓
- WAITING: loss (-0.32%) > trigger (-0.35%) → NOT FIRED yet ✗

**The gap:** Position is wrong at -0.32%, but cascade flip waits until -0.35% to fire. That's only 0.03% more loss before it flips — too slow.

**Also needed:** Valid opposite-direction signal in DB with conf >= 60% within last 30 min. If no LONG signal for LINK in the DB, cascade flip won't fire even when trigger hits.

**Fix applied (T approved):** Cascade flip arm and trigger thresholds still need tightening — suggested values:
```python
CASCADE_FLIP_ARM_LOSS        = -0.10   # was -0.25% — arm immediately if wrong
CASCADE_FLIP_TRIGGER_LOSS    = -0.15    # was -0.50% — flip at -0.15% if armed + speed up
CASCADE_FLIP_HF_TRIGGER_LOSS = -0.12    # was -0.35%
```

**Code location:** `position_manager.py` lines 90-92.

**Note:** These thresholds are per-position loss on the account, not per-trade. A -0.10% loss on one 5x leveraged trade = -0.50% on that trade's capital.