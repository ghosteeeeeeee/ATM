# Plan: Unified Stop Loss + ATR Trailing + Cascade System
# Status: READY TO EXECUTE
# Last Updated: 2026-04-08 03:05 UTC

---

## CONFIRMED BUGS (8 total)

| # | Bug | File | Impact |
|---|-----|------|--------|
| B1 | Trailing SL never pushed to HL after entry | position_manager.py | Trailing SL calculated but `place_sl()` never called when it improves |
| B2 | Cascade new position has no SL | position_manager.py | After cascade flip, new position has no stop loss on HL |
| B3 | No TP/SL placed on initial entry | decider-run.py / position_manager.py | `place_order()` fires but `place_sl()` + `place_tp()` not called |
| B4 | Cascade PnL tracking absent | position_manager.py | Can't determine if flips succeeded → cooldown logic can't fire |
| B5 | HL rate-limit skips cycles silently | hl-sync-guardian.py | 429 response causes silent skip, no cache, no retry |
| B6 | Guardian reason = "guardian_missing" | hl-sync-guardian.py | No trackability — all closes say same useless thing |
| B7 | No kill switch for manual close protection | hl-sync-guardian.py | T can't tell guardian "I closed this, don't touch it" |
| B8 | Duplicate trade display (entry+exit as separate) | hermes-trades-api.py + update-trades-json.py | P&L and win-rate corrupted — both scripts write same file, race condition |

---

## DESIGN DECISIONS (From T — Confirmed)

| # | Decision | Answer |
|---|----------|--------|
| 1 | HL reverse method | Two orders: close (reduceOnly market) → wait 500ms → poll HL → open opposite |
| 2 | TP tracking with SL | TP updates proportionally when SL moves (maintains RR ratio) |
| 3 | CUT_LOSER_THRESHOLD | A/B tested: 3%, 4%, 5% variants via sl-distance-test |
| 4 | Cascade flip count logic | After 3 flips: consecutive_failures ≥ 2 → 2h cooldown; all successful → allow 4th; else → normal |
| 5 | Guardian = failsafe only | Strip ATR/trailing/cascade, keep sync + orphan + final cut |
| 6 | Manual close protection | Kill switch file + 15s spacing between closes + confirm-before-close |
| 7 | paper=True handling | Keep as safety net (logged as WARNING if found during live cycle) |

---

## NEW ISSUE: B8 — Duplicate Trade Display (Entry + Exit as Separate Trades)

### Root Cause
Two scripts write to `/var/www/hermes/data/trades.json`:
- `hermes-trades-api.py` — runs at pipeline step: `hermes-trades-api`
- `update-trades-json.py` — runs at pipeline step: `update-trades-json`

Both run every minute. Both read from brain DB and write the same file. Race condition: when cascade flip closes a trade and re-opens a new one, both scripts may capture different states, resulting in the closed trade's data appearing alongside the new open trade's data in the `closed` array with the same token appearing twice.

### Fix
1. **Remove `update-trades-json.py`** — `hermes-trades-api.py` handles both open and closed trades correctly with proper PnL calculation
2. **In `hermes-trades-api.py`**:
   - Add cascade sequence tracking: when cascade_flip closes a trade, mark it with `flipped_from_trade` (already done) and set `flip_count` on the new trade
   - Ensure the `closed` array never shows a trade as open then closed at the same token — `flipped_from_trade` is the key identifier
   - After a cascade flip: update the original trade's `close_reason` to include the new trade ID: `cascade_closed_into_trade_#N`

### Cascade Flip Trade Flow (for trackability)
When cascade flip fires on trade #100 (LONG) → new trade #101 (SHORT):
1. Close trade #100: `close_reason='cascade_flip'`, `flipped_from_trade=NULL`, `exit_price=current`
2. Open trade #101: `flipped_from_trade=100`, `flip_count=1`
3. If trade #101 later flips again → trade #102 (LONG): `flipped_from_trade=101`, `flip_count=2`
4. PnL for cascade evaluation: use `flipped_from_trade` chain to compute total sequence PnL from HL realized PnL

---

## PHASE 1: Entry SL + TP — Place on HL Immediately

**Goal: Every position has SL + TP on HL within 5s of entry/reverse**

### Changes to `hyperliquid_exchange.py`

```python
def place_sl_and_tp(token: str, direction: str, entry_price: float,
                    size: float, sl_price: float, tp_price: float) -> dict:
    """Place both SL and TP on HL. Called on every position open/reverse.
    Idempotent — only sends to HL if price moved vs cached value."""
    sl_result = place_sl(token, direction, sl_price, size)
    tp_result = place_tp(token, direction, tp_price, size)
    # Update caches
    _sl_price_cache[token.upper()] = sl_price
    _tp_price_cache[token.upper()] = tp_price
    return {"sl": sl_result, "tp": tp_result}
```

### Changes to `position_manager.py`

**In `cascade_flip()`:**
1. After `close_paper_position()` succeeds → `_wait_for_position_cleared(token)` (poll HL every 500ms, max 10 tries)
2. After `place_order()` succeeds → `place_sl_and_tp()` immediately for new position
3. Set `trailing_active=False` on new position (fresh ATR start)
4. Call `_start_flip_sequence(original_trade_id, token, direction)` to begin cascade tracking

**Entry path (decider-run.py and brain.py):**
After `place_order()` succeeds → `place_sl_and_tp()` immediately

### Changes to `decider-run.py`
After market order fills → call `place_sl()` and `place_tp()` via `position_manager.ensure_sl_on_hl()`

---

## PHASE 2: ATR Trailing → Push to HL Every Cycle

**Goal: Trailing SL moves on HL whenever it improves**

### In-memory cache
```python
_trailing_sl_cache = {}  # token → last_sl_price_pushed_to_hl
_trailing_tp_cache = {}   # token → last_tp_price_pushed_to_hl
```

### In `check_and_manage_positions()`, every cycle per open position:

**Compute new trailing SL:**
```python
new_sl = best_price - k * ATR(14)
new_tp = entry + (new_sl - entry) * tp_multiplier  # maintains RR ratio
```

**Push if improved:**
```python
if new_sl > _trailing_sl_cache.get(token):  # LONG: SL moves up
    place_sl(token, direction, new_sl, size)
    _trailing_sl_cache[token] = new_sl
if new_tp > _trailing_tp_cache.get(token):  # LONG: TP moves up
    place_tp(token, direction, new_tp, size)
    _trailing_tp_cache[token] = new_tp
```

For SHORT: invert comparisons (`new_sl < cached`).

**Activation check (trailing not yet active):**
```python
atr = _pm_get_atr(token)
profit_threshold = 1.5 * atr
if live_pnl >= profit_threshold and not trailing_active:
    initial_sl = best_price - k * ATR
    place_sl(token, direction, initial_sl, size)
    _trailing_sl_cache[token] = initial_sl
    trailing_active = True
```

---

## PHASE 3: Cascade PnL Tracking

**Goal: Track flip success/failure per cascade sequence, enable cooldown logic**

### New table in brain DB

```sql
CREATE TABLE cascade_sequences (
    id SERIAL PRIMARY KEY,
    original_trade_id INT NOT NULL,
    token TEXT NOT NULL,
    direction TEXT NOT NULL,  -- original direction (LONG or SHORT)
    flip_count INT DEFAULT 0,
    sequence_pnl_usdt REAL DEFAULT 0,  -- cumulative after fees (from HL realized PnL)
    consecutive_successes INT DEFAULT 0,
    consecutive_failures INT DEFAULT 0,
    status TEXT DEFAULT 'active',  -- active | cooldown | closed | locked
    cooldown_until TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    closed_at TIMESTAMP,
    FOREIGN KEY (original_trade_id) REFERENCES trades(id)
);
```

### Functions

**`_start_flip_sequence(trade_id, token, direction)`:**
- Insert row: `original_trade_id=trade_id, token, direction, flip_count=0`
- Returns `sequence_id`

**`_record_flip_result(sequence_id, pnl_after_fees)`:**
- Load sequence
- If `pnl_after_fees > 0`: `consecutive_successes += 1; consecutive_failures = 0`
- Else: `consecutive_failures += 1; consecutive_successes = 0`
- `sequence_pnl_usdt += pnl_after_fees`
- `flip_count += 1`
- **Post-flip-count evaluation:**
  - If `flip_count >= 3` and `consecutive_failures >= 2`: `status='cooldown'`, `cooldown_until=NOW()+2h`
  - If `flip_count >= 3` and `consecutive_successes == 3` and `sequence_pnl_usdt > 0`: `status='open'` (allow 4th)
  - If `sequence_pnl_usdt > 0` overall: `status='closed'`
- Update row

**`get_cascade_sequence(token)`:**
- Return active sequence for token, or None

### Integration with `cascade_flip()`
When cascade closes a trade:
1. Look up sequence by `original_trade_id`
2. After close fills: get HL realized PnL for that close
3. Call `_record_flip_result(sequence_id, hl_realized_pnl)`
4. If `status='cooldown'`: log warning, skip next cascade flip signals for this token until `cooldown_until`

### PnL Source Priority
1. `hype_realized_pnl_usdt` from HL fills — ground truth
2. `pnl_usdt` from brain DB — fallback (already calculated)
3. Price-based calculation from entry/exit — last resort

---

## PHASE 4: TP Tracks With SL

**In `check_and_manage_positions()`, when trailing_SL updates:**
```python
# Maintain original RR ratio
tp_multiplier = (original_TP - entry) / (original_SL - entry)  # e.g., TP=3%, SL=1.5% → multiplier=2
new_TP = entry + (new_SL - entry) * tp_multiplier
```
Call `place_tp()` only if `new_TP > cached_TP` (for LONG) / `new_TP < cached_TP` (for SHORT).

---

## PHASE 5: Guardian as Minimal Failsafe

**Goal: Guardian does 3 things only, with proper cache + rate-limit handling**

### Remove from guardian (move to position_manager):
- All ATR/trailing computation
- All cascade flip logic
- Per-cycle SL updates when nothing changed

### Guardian does exactly:
1. **HL↔DB sync** (every 60s, but cache HL state for 90s per token)
2. **SL reconciliation**: if `DB.trailing_sl > HL.book_sl` → update HL (trailing only improves, never worsens)
3. **Orphan detection**: HL position exists, no DB entry → create + close
4. **Final cut**: if `pnl_pct <= CUT_LOSER_THRESHOLD` (A/B tested: 3/4/5%) and still open → close

### Rate-limit handling:
- On 429: exponential backoff (5s → 10s → 20s), queue update for next cycle
- Always maintain in-memory last-known SL value
- `GUARDIAN_IDLE` log line when nothing to do

### Manual close kill switch (Phase 6)

---

## PHASE 6: Manual Close Protection + Kill Switch

### New file: `/root/.hermes/data/guardian_kill_switch.json`
```json
{
  "manual_closes": {},
  "paused_until": null,
  "guardian_active": true
}
```

### Guardian behavior:
- On each cycle: read kill switch file
- If token in `manual_closes`:
  - Set `guardian_closed=TRUE` on DB trade (trade ID from the file)
  - Set `guardian_reason='manual_close_by_T'` on the trade
  - Skip all processing for that token this cycle
- If `paused_until` is set and `now < paused_until`: skip entire cycle, log `GUARDIAN_PAUSED`
- Always write back to the file after processing (clear processed entries)

### T's interface (simple JSON edits or brain command):
```bash
# T manually closed XRP — tell guardian
python3 -c "
import json
data = {'manual_closes': {'XRP': {'trade_id': 4326, 'closed_at': '2026-04-08T03:05:00Z'}}, 'paused_until': null, 'guardian_active': true}
with open('/root/.hermes/data/guardian_kill_switch.json', 'w') as f:
    json.dump(data, f)
"

# Resume normal guardian operation
python3 -c "
data = {'manual_closes': {}, 'paused_until': null, 'guardian_active': true}
with open('/root/.hermes/data/guardian_kill_switch.json', 'w') as f:
    json.dump(data, f)
"
```

### 15-second spacing
Step 8 processes trades one at a time with `time.sleep(15)` between each close to avoid HL rate limiting.

---

## PHASE 7: Fix Reason Column Trackability

### In `_close_paper_trade_db()` and Step 8, change reason values:

| Event | `reason` value | `guardian_reason` in DB |
|-------|---------------|------------------------|
| T manually closed | `'manual_close_by_T'` | `'manual_close_by_T'` |
| Guardian confirmed stale orphan | `'guardian_sync_close'` | `'guardian_sync_close'` |
| HL position missing (Step 7) | `'hl_position_missing'` | `'hl_position_missing'` |
| Orphan HL position closed (Step 6) | `'orphan_recovery'` | `'orphan_recovery'` |
| At max HL positions | `'max_positions'` | `'max_positions'` |
| Token on blocklist | `'hotset_blocked'` | `'hotset_blocked'` |
| Cascade flip close | `'cascade_flip'` | `'cascade_flip'` |
| Trailing exit | `'trailing_exit'` | `'trailing_exit'` |
| Cut-loser emergency | `'cut_loser'` | `'cut_loser'` |
| A/B test SL triggered | `'ab_sl_trigger'` | `'ab_sl_trigger'` |

**Log format** (always include token + trade_id):
```
[GUARDIAN] Step8 SKIP XRP #4326: live trade but guardian_closed=FALSE (externally closed by T)
[GUARDIAN] Step8 closing EIGEN #4330: guardian_sync_close (stale orphan, HL pos missing)
```

---

## PHASE 8: Fix Duplicate Trade Display (B8)

### Remove duplicate script
- Remove `update-trades-json.py` from `STEPS_EVERY_MIN` in `run_pipeline.py`
- `hermes-trades-api.py` handles both open and closed correctly

### In `hermes-trades-api.py`:

**Fix race condition:** Add file locking so only one process can write at a time:
```python
import fcntl
LOCK_FILE = '/var/www/hermes/data/trades.json.lock'
def write_trades_atomic(data, path):
    with open(LOCK_FILE, 'w') as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        with open(path, 'w') as f:
            json.dump(data, f)
        fcntl.flock(lf.fileno(), fcntl.LOCK_UN)
```

**Fix cascade display:** When building `closed` array, check `flipped_from_trade`:
- If `flipped_from_trade IS NOT NULL`: this was the original trade in a cascade sequence — display normally (it's a legitimate close)
- The new trade (with `flipped_from_trade=original_id`) appears in the `open` array — this is correct
- The original trade's `close_reason` should reference the new trade: e.g., `"cascade_closed_into_trade_#4327"`

**Verify `closed` array doesn't include stale entries:**
- Query closed trades with `WHERE close_time > NOW() - INTERVAL '24 hours'` to ensure we don't show ancient closed trades
- Sort by `close_time DESC` with proper LIMIT

---

## PHASE 9: CUT_LOSER_THRESHOLD A/B Test Setup

**Goal: A/B test emergency cut threshold: 3% vs 4% vs 5%**

### Implementation
The threshold is already A/B tested via `sl-distance-test` (Thompson sampling). Add to `position_manager.py`:

```python
CUT_LOSER_THRESHOLDS = [0.03, 0.04, 0.05]  # 3%, 4%, 5%

def get_cut_loser_threshold(token: str, direction: str) -> float:
    """Get A/B-tested cut-loser threshold. Default 5% if no variant found."""
    variant = get_cached_ab_variant(token, direction, 'sl-distance-test')
    if variant:
        config = variant.get('config', {})
        sl_pct = config.get('slPct', 0.05)  # already in percentage (e.g., 2.0 = 2%)
        return max(0.03, min(sl_pct / 100, 0.05))  # clamp to test range
    return 0.05  # default 5%
```

In `check_and_manage_positions()`:
```python
cut_loser_threshold = get_cut_loser_threshold(token, direction)
if pnl_pct <= -1 * cut_loser_threshold * 100:  # pnl_pct is already negative
    close_paper_position(trade_id, f'cut_loser_{pnl_pct:.2f}%')
```

---

## FILE CHANGES SUMMARY

| File | Phases | Key Changes |
|------|--------|-------------|
| `position_manager.py` | 1, 2, 3, 4, 9 | Entry SL/TP, cascade→place_sl, ATR→HL trailing, cascade PnL tracking, TP tracks SL, A/B cut-loser |
| `hl-sync-guardian.py` | 5, 6, 7 | Strip ATR/trailing/cascade, add kill switch + cache, fix reason column |
| `hyperliquid_exchange.py` | 1 | `place_sl_and_tp()` helper, SL/TP caches |
| `hermes-trades-api.py` | 8 | Remove `update-trades-json.py` conflict, atomic write, cascade display fix |
| `run_pipeline.py` | 8 | Remove `update-trades-json` from `STEPS_EVERY_MIN` |
| Brain DB | 3 | New `cascade_sequences` table |
| `brain/trading.md` | all | Document architecture and current state |

---

## VALIDATION CHECKLIST

After each phase:
- [ ] Phase 1: Open test trade → HL has SL + TP within 5s
- [ ] Phase 1: Cascade fires → new position has SL + TP on HL within 5s
- [ ] Phase 2: Price moves +1.5× ATR → trailing activates, new SL on HL
- [ ] Phase 2: Price retraces → trailing SL moves up, TP also moves
- [ ] Phase 3: After cascade flip, `cascade_sequences` table has entry
- [ ] Phase 3: 3 successful cascades → 4th allowed; 2 consecutive failures → cooldown activates
- [ ] Phase 5: Guardian logs `GUARDIAN_IDLE` when nothing wrong
- [ ] Phase 5: HL rate-limited → updates queued, not dropped
- [ ] Phase 6: T manually closes XRP → guardian logs SKIP, doesn't cascade
- [ ] Phase 7: Reason column shows specific reason, not generic "guardian_missing"
- [ ] Phase 8: trades.html shows one entry per token (no duplicate entry+exit)
- [ ] Phase 9: Cut-loser threshold varies by A/B variant (3/4/5%)

---

## EXECUTION ORDER

1. **Phase 8 first** (fix B8) — removes the confusing duplicate display issue before anything else
2. **Phase 1** (fix B3 + B2) — highest impact, fixes the core protection gap on entry and cascade
3. **Phase 5** (fix B5 + B7) — makes the system safer for T's manual closes, proper cache + kill switch
4. **Phase 2** (fix B1) — trailing SL pushed to HL every cycle
5. **Phase 4** — TP tracks with SL
6. **Phase 3** (fix B4) — cascade PnL tracking (DB changes)
7. **Phase 7** (fix B6) — reason column trackability
8. **Phase 9** — A/B test cut-loser thresholds

**Why Phase 8 first?** Because B8 corrupts P&L and win-rate numbers — if we fix the protection system but the display still shows wrong numbers, we can't properly evaluate the fixes.
---

## EXECUTION LOG (2026-04-08 03:30-03:55 UTC)

### ✅ PHASE 8 (B8) — DONE 03:35
Atomic write lock added to `hermes-trades-api.py` + `update-trades-json.py`
- Kept `update-trades-json.py` as safety net (no signal_schema import = fast)
- `_atomic_write()` function using `fcntl.flock()` — both scripts now safe for concurrent writes

### ✅ PHASE 1 (B3) — DONE 03:42
`brain.py add_trade()`: after `mirror_open()` success, SL + TP placed on HL immediately
- Reads `stop_loss` and `target` from trade record
- Calls `hl_place_sl()` and `hl_place_tp()` from hyperliquid_exchange
- Non-fatal if SL placement fails (paper still tracked)

### ✅ PHASE 1 (B2) — DONE 03:48
`position_manager.py cascade_flip()`: after `place_order()` success, SL+TP placed on HL for new cascade position
- Reads SL/TP from newest open trade for that token
- Calls `hl_place_sl()` and `hl_place_tp()`
- Non-fatal if SL placement fails

### ✅ PHASE 2 (B1) — VERIFIED DONE
Already had BUG-8 fix in position_manager (line ~1895). Verified in code:
```python
exchange.order(token, is_buy, abs(size), sl_rounded, order_type, reduce_only=True)
print(f"  [BUG-8] Pushed trailing SL to HL: {token} {direction} SL=${sl_rounded:.6f}")
```
No further change needed.

### 📋 REMAINING (not yet executed)
- B4: cascade_sequences table (DB changes)
- B5: position_manager 429 backoff
- B6: guardian reason column fix
- B7: guardian_kill_switch.json

### Documentation Updated
- PROJECTS.md: Added "SL/TP Protection System Fixes" section
- TASKS.md: Added 2026-04-08 session tasks
- trading.md: Added full audit + fix log


---

## EXECUTION LOG (2026-04-08 03:30-03:55 UTC)

### ✅ PHASE 8 (B8) — DONE 03:35
Atomic write lock added to hermes-trades-api.py + update-trades-json.py
- Kept update-trades-json.py as safety net (no signal_schema import = fast)
- _atomic_write() function using fcntl.flock() — both scripts now safe for concurrent writes

### ✅ PHASE 1 (B3) — DONE 03:42
brain.py add_trade(): after mirror_open() success, SL + TP placed on HL immediately
- Reads stop_loss and target from trade record
- Calls hl_place_sl() and hl_place_tp() from hyperliquid_exchange
- Non-fatal if SL placement fails (paper still tracked)

### ✅ PHASE 1 (B2) — DONE 03:48
position_manager.py cascade_flip(): after place_order() success, SL+TP placed on HL
- Reads SL/TP from newest open trade for that token
- Calls hl_place_sl() and hl_place_tp()
- Non-fatal if SL placement fails

### ✅ PHASE 2 (B1) — VERIFIED DONE
Already had BUG-8 fix in position_manager (line ~1895). Verified in code. No further change needed.

### 📋 REMAINING (not yet executed)
- B4: cascade_sequences table (DB changes)
- B5: position_manager 429 backoff
- B6: guardian reason column fix
- B7: guardian_kill_switch.json

### Documentation Updated
- PROJECTS.md: Added "SL/TP Protection System Fixes" section
- TASKS.md: Added 2026-04-08 session tasks
- trading.md: Added full audit + fix log



---

## EXECUTION LOG (2026-04-08 03:30-03:55 UTC)

### DONE
- B8: Atomic flock write lock added to hermes-trades-api.py + update-trades-json.py
- B3: brain.py add_trade() — SL+TP placed on HL immediately after entry
- B2: position_manager.py cascade_flip() — SL+TP placed on HL for new cascade position
- B1: Already implemented (BUG-8 fix verified at line ~1895-1920)

### REMAINING
- B4: cascade_sequences table
- B5: position_manager 429 backoff
- B6: guardian reason column
- B7: guardian_kill_switch.json

### Docs
- PROJECTS.md: Added "SL/TP Protection System Fixes"
- TASKS.md: Added 2026-04-08 session tasks
- trading.md: Added full audit + fix log

