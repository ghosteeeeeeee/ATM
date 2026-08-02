# Cascade Flip + Post-Flip ATR Tightening — Implementation Plan

## Goal

Improve cascade flip effectiveness in two ways:
1. **Instant flip** — use a single reduce+open market order on HL instead of two separate API calls (close then open), eliminating the ~1s gap between close and open where price can move against us
2. **Post-flip ATR tightening** — after a cascade flip, the new position entered at a known bad moment; ATR should use the tightest k (1.0) and shortest cycle deadline so the position gets cut immediately if wrong
3. **Hot-set eviction** — after a cascade flip, exclude the token from the hot-set for ~10 minutes so signal_compactor doesn't add a redundant second position
4. **atr_managed sync** — the DB entry for the post-flip position should be created synchronously or flagged correctly so guardian doesn't fire a hard-stop on its own flipped position

---

## Current Behavior (Problem Summary)

```
cascade_flip() fires:
  1. close_paper_position(old_id)  → DB: old trade CLOSED
  2. exchange.market_close(coin)    → HL: old position CLOSED (reduce-only)
  3. exchange.market_open(side=opposite) → HL: new position OPENED
  4. cascade_sequences: records the CLOSE record (child_trade_id=None — new trade doesn't exist)
  5. cascade_sequences: tries to record OPEN → fails, new trade doesn't exist in DB yet
  6. flip_counts.json: updated with flip count + direction

[~60 second gap — guardian hasn't run yet]

Guardian sync (~60s later):
  7. Finds HL position with no DB entry
  8. Creates new DB trade with: atr_managed=NULL, guardian_closed=TRUE, entry_price=fill_price
  9. Position now visible to ATR pipeline
```

**Problems:**
- `atr_managed=NULL` on the new trade → guardian's hard-stop filter `atr_managed IS NULL OR atr_managed=FALSE` MATCHES IT → guardian could fire a hard-stop on its own just-flipped position
- Cascade sequences entry is incomplete (child_trade_id=None)
- Hot-set still has old direction signal for up to 5 minutes (signal_compactor gap)
- Post-flip ATR starts at normal k instead of k=1.0 (most conservative)

---

## Current Cascade Flip Order Logic

```python
# Step 1: close losing position
close_paper_position(trade_id, f"cascade_flip_{live_pnl:+.2f}%")
# → internally calls exchange.market_close()

# Step 2: open opposite direction
exchange.market_open(
    name=token,
    is_buy=(side == "BUY"),  # BUY for LONG, SELL for SHORT
    sz=sz,                    # position size
    px=price or 0,
    slippage=0.005,
)
# market_open internally calls order() with reduce_only=False
```

---

## Hyperliquid Order Behavior (Key Finding)

`exchange.market_open()` calls `order()` with `reduce_only=False`:

```python
def market_open(self, name, is_buy, sz, px, slippage, ...):
    return self.order(
        name, is_buy, sz, px,
        order_type={"limit": {"tif": "Ioc"}},
        reduce_only=False,  # <— NOT reduce-only!
    )
```

A single `market_open` with `is_buy=False` (for a SELL/short) on a existing LONG position:
- If sz >= LONG size: closes the LONG (reduces to 0) then opens a SHORT
- BUT: two separate fills happen — not atomic close-then-open

Similarly for closing a SHORT before opening a LONG:
- Two fills occur: SHORT close + LONG open

**There is no single-API-call atomic flip** — the two-step (close + open) is necessary regardless.

---

## Proposed Approach

### Fix 1 — Single Order Flip (No Change Needed)

The existing two-step (close then open) is the correct approach. A single `market_open` with `reduce_only=False` does two fills (close then open) but they happen in the same order packet. The current approach is fine.

**However:** the `market_open` for step 2 currently uses `sz=None` which means "use default size". This should be changed to explicitly pass the size of the closed position so the new position is the same notional size.

```python
# Current (step 2 of cascade_flip):
ok = place_order(name=token, side='BUY' if opposite_dir=='LONG' else 'SELL',
                 sz=None, price=current_price, order_type='Market')

# Proposed:
ok = place_order(name=token, side='BUY' if opposite_dir=='LONG' else 'SELL',
                 sz=old_amount, price=current_price, order_type='Market')
```

Where `old_amount` is the size of the just-closed position. This ensures the new position is exactly the same notional exposure.

---

### Fix 2 — Synchronous DB Entry for Post-Flip Position

Instead of waiting ~60s for guardian to create the DB entry, `cascade_flip()` should create the DB entry immediately after the HL order succeeds.

**Why:** Guardian's `mirror_open` uses `WHERE NOT EXISTS` — it won't create a duplicate if the trade already exists. So we can safely INSERT the new trade immediately.

**Implementation:**

After `exchange.market_open()` succeeds in `cascade_flip()`, add:

```python
# ── Create DB entry for post-flip position immediately ──────────────────
try:
    conn_flip = get_db_connection()
    cur_flip = conn_flip.cursor()
    cur_flip.execute("""
        INSERT INTO trades (token, direction, entry_price, hl_entry_price,
            amount_usdt, leverage, exchange, paper, status, open_time,
            stop_loss, target, atr_managed, signal, signal_source,
            sl_distance, trailing_activation, trailing_distance,
            guardian_closed, is_guardian_close)
        VALUES (%s, %s, %s, %s, %s, %s, 'Hyperliquid', true, 'open', NOW(),
                %s, %s, TRUE, %s, %s,
                0.03, 0.01, 0.01,
                FALSE, FALSE)
        WHERE NOT EXISTS (
            SELECT 1 FROM trades WHERE token=%s AND status='open' AND server='Hermes'
        )
        RETURNING id
    """, (token, opposite_dir, current_price, current_price,
          old_amount, leverage, sl, tp,
          source_tag, source_tag,  # signal and signal_source
          token))
    row = cur_flip.fetchone()
    conn_flip.commit()
    cur_flip.close(); conn_flip.close()
    if row:
        new_trade_id = row[0]
        # Record cascade ENTRY with correct child_trade_id
        _record_cascade_sequence(...)
except Exception as e:
    log(f"  [CASCADE FLIP] ⚠️ Failed to create post-flip DB entry: {e} — non-fatal, guardian will sync")
```

**Key fields:**
- `atr_managed = TRUE` → guardian ignores it (hard-stop filter correctly excludes it)
- `guardian_closed = FALSE, is_guardian_close = FALSE` → clearly not a guardian-managed position
- `signal = source_tag` (e.g. `cascade-reverse-mtf_macd_alignment`) → ATR can detect post-flip
- `stop_loss, target` → initial SL/TP from cascade (same as original, or tighter if desired)

**Fallback:** if the INSERT fails, guardian will pick it up in ~60s and set `atr_managed=NULL` — which is the existing bug. But the INSERT failure is non-fatal, so cascade flip still succeeds on HL.

---

### Fix 3 — Tighter ATR k for Post-Flip Positions

When `_collect_atr_updates()` computes SL/TP for a position, check if it's a post-flip position.

**Detection:** the `signal` field of post-flip trades will be set to `cascade-reverse-{source}` (set in Fix 2 above). ATR can check this.

**Implementation in `_collect_atr_updates()`:**

```python
# Check if this is a post-flip position — if so, use k=1.0 (tightest)
is_post_flip = pos.get('signal', '').startswith('cascade-reverse-')
if is_post_flip:
    k = 1.0  # Override: tightest SL/TP since we entered at a bad moment
    k_tp = 1.0  # Also tighten TP multiplier
```

**Alternative using flip_counts.json:**
```python
flip_counts = _load_flip_counts()
token_entry = flip_counts.get(token.upper(), {})
if token_entry.get('hotset_evicted'):
    deadline = token_entry.get('evicted_until_cycle', 0)
    if current_pipeline_cycle < deadline:
        k = 1.0  # Post-flip: tightest ATR
```

The flip_counts approach is cleaner because it's already being written by cascade_flip().

**But wait:** cascade_flip() currently writes to `flip_counts.json` but we haven't added `hotset_evicted` or `evicted_until_cycle` yet. We need to add those first (see Fix 4).

---

### Fix 4 — Hot-Set Eviction via flip_counts.json

When `cascade_flip()` saves flip counts, add eviction metadata:

```python
FLIP_EVICTION_CYCLES = 10  # ~10 minutes (1 cycle/min)

def _get_flip_cycle_deadline() -> int:
    """Return the pipeline cycle number after which eviction expires."""
    # Pipeline cycle is tracked in a simple counter file
    try:
        with open('/var/www/hermes/data/pipeline_cycle.json') as f:
            data = json.load(f)
            current = data.get('cycle', 0)
    except:
        current = 0
    return current + FLIP_EVICTION_CYCLES

# In cascade_flip(), when saving flip_counts:
flip_counts[token.upper()] = {
    'flips': entry.get('flips', 0) + 1,
    'last_flip_dir': opposite_dir,
    'last_flip_time': datetime.now().isoformat(),
    'hotset_evicted': True,
    'evicted_until_cycle': _get_flip_cycle_deadline(),
}
```

**Pipeline cycle tracker** — needs to be created:

```python
# In run_pipeline.py or check_and_manage_positions():
# Increment cycle counter each run
CYCLE_FILE = '/var/www/hermes/data/pipeline_cycle.json'
```

**signal_compactor.py reads flip_counts and excludes evicted tokens:**

```python
# At top of signal_compactor's hot-set builder:
flip_counts_path = '/var/www/hermes/data/flip_counts.json'
evicted_tokens = set()
try:
    with open(flip_counts_path) as f:
        fc = json.load(f)
        for token, entry in fc.items():
            if entry.get('hotset_evicted'):
                deadline = entry.get('evicted_until_cycle', 0)
                try:
                    with open('/var/www/hermes/data/pipeline_cycle.json') as cf:
                        current_cycle = json.load(cf).get('cycle', 0)
                except:
                    current_cycle = 0
                if current_cycle < deadline:
                    evicted_tokens.add(token.upper())
                else:
                    # Eviction expired — clear the flag
                    entry['hotset_evicted'] = False
                    entry.pop('evicted_until_cycle', None)
        if fc:
            with open(flip_counts_path, 'w') as f:
                json.dump(fc, f, indent=2)
except Exception:
    pass

# When building hot-set, skip evicted tokens:
for entry in hotset_candidates:
    if entry['token'].upper() in evicted_tokens:
        continue  # Recently flipped — let the position prove itself
```

---

## Step-by-Step Plan

### Step 1 — Pipeline cycle counter (new file + integration)

**File:** `/var/www/hermes/data/pipeline_cycle.json` (created by pipeline)
**Files changed:**
- `run_pipeline.py` — increment cycle on each run
- OR `check_and_manage_positions()` — increment on each call

```python
import json, os
CYCLE_FILE = '/var/www/hermes/data/pipeline_cycle.json'
def _get_current_cycle() -> int:
    try:
        with open(CYCLE_FILE) as f:
            return json.load(f).get('cycle', 0)
    except: return 0
def _increment_cycle():
    try:
        with open(CYCLE_FILE) as f:
            data = json.load(f)
    except: data = {}
    data['cycle'] = data.get('cycle', 0) + 1
    with open(CYCLE_FILE, 'w') as f:
        json.dump(data, f)
    return data['cycle']
```

### Step 2 — Add `_get_flip_cycle_deadline()` helper to position_manager.py

**File:** `position_manager.py` (new function near line ~111)

```python
def _get_flip_cycle_deadline() -> int:
    """Return pipeline cycle number after which flip eviction expires."""
    CYCLE_FILE = '/var/www/hermes/data/pipeline_cycle.json'
    try:
        with open(CYCLE_FILE) as f:
            data = json.load(f)
            return data.get('cycle', 0) + FLIP_EVICTION_CYCLES
    except:
        return 0  # Fail: no eviction
```

### Step 3 — Update `cascade_flip()` flip_counts save to include eviction metadata

**File:** `position_manager.py` (line ~2988)

```python
flip_counts[token.upper()] = {
    'flips': entry.get('flips', 0) + 1,
    'last_flip_dir': opposite_dir,
    'last_flip_time': datetime.now().isoformat(),
    'hotset_evicted': True,
    'evicted_until_cycle': _get_flip_cycle_deadline(),
}
```

### Step 4 — Add explicit size to post-flip order in `cascade_flip()`

**File:** `position_manager.py` (line ~2927)

```python
# Get position size — use the closed position's size for the new opposite position
old_amount = float(pos.get('amount_usdt', 50.0)) if 'pos' in dir() else 50.0
# Actually we already fetch old_amount above — just pass it to place_order
ok = place_order(
    name=token,
    side='BUY' if opposite_dir == 'LONG' else 'SELL',
    sz=old_amount,  # Same notional as the just-closed position
    price=current_price,
    order_type='Market',
)
```

### Step 5 — Create DB entry for post-flip position in `cascade_flip()` (Fix 2)

**File:** `position_manager.py` (after line ~2915, where order succeeds)

After `if ok and ok.get('success'):` block, add synchronous DB INSERT.

Note: This requires adding `get_db_connection` import and constructing proper INSERT with `atr_managed=TRUE`.

### Step 6 — Update `signal_compactor.py` to read flip_counts and evict tokens

**File:** `signal_compactor.py`

Add flip_counts read at the top of hot-set building logic. Skip tokens that are currently evicted.

### Step 7 — Update `_collect_atr_updates()` to use k=1.0 for post-flip

**File:** `position_manager.py` (in `_collect_atr_updates()`)

Check flip_counts for `hotset_evicted=True`. If token is in eviction window, use k=1.0 (tightest).

---

## Files Likely to Change

1. `/root/.hermes/scripts/position_manager.py`
   - `_get_flip_cycle_deadline()` (new helper)
   - `cascade_flip()` (flip_counts save + size param + DB INSERT)
   - `_collect_atr_updates()` (k=1.0 for post-flip)

2. `/root/.hermes/scripts/signal_compactor.py`
   - Hot-set builder (read flip_counts, skip evicted tokens)

3. `/root/.hermes/scripts/run_pipeline.py` (or `check_and_manage_positions()`)
   - Increment `pipeline_cycle.json` each run

---

## Tests / Validation

1. **Unit test — single order flip:** Manual check: place a SHORT on HL, trigger cascade flip, verify only 2 fills (close + open), no double-position
2. **Unit test — DB entry with atr_managed=TRUE:** After cascade flip, query DB: `SELECT * FROM trades WHERE token='XXX' AND status='open' AND atr_managed=TRUE` — should return the new trade
3. **Unit test — hot-set eviction:** After cascade flip, check flip_counts.json has `hotset_evicted=True` and `evicted_until_cycle > current_cycle`. Next signal_compactor run should not include that token in hot-set.
4. **Unit test — ATR k post-flip:** After cascade flip, check pipeline logs — ATR should show k=1.0 for the post-flip position for at least 10 cycles
5. **End-to-end:** Trigger a real cascade flip, verify position_manager processes the new position correctly with tight SL, verify hot-set doesn't add a second position on same token

---

## Risks and Tradeoffs

1. **Risk — cascade_flip DB INSERT race with guardian:** If cascade_flip creates the DB entry AND guardian also tries to create it (because guardian's NOT EXISTS check runs before cascade_flip's INSERT commits), one will be skipped. But this is fine — cascade_flip sets `atr_managed=TRUE`, guardian won't duplicate. **Mitigation:** use RETURNING to get the ID safely.

2. **Risk — pipeline_cycle.json doesn't exist yet:** If `_get_flip_cycle_deadline()` is called before the pipeline has run (cycle=0), eviction deadline would be `0 + 10 = 10`, which is fine. First cycle would be 1, so eviction would last until cycle 10. **Safe.**

3. **Risk — flip_counts.json written by cascade_flip but signal_compactor can't read it (permission):** Both files are in `/var/www/hermes/data/` which is readable. **Safe.**

4. **Tradeoff — synchronous DB INSERT adds latency to cascade_flip:** The INSERT adds ~50-100ms to the flip execution. For emergency exit this is acceptable. **Worth it** to close the atr_managed gap.

5. **Open question — what SL/TP to use for the new DB entry?** Options:
   - Same as original position's SL/TP (cascade keeps the same risk levels)
   - Tighter initial SL (cascade flip = higher conviction of reversal, but entered at bad moment)
   - Default values from `add_orphan_trade` (SL=3%, TP=None) — lets ATR recompute next cycle
   - **Recommendation:** Use same SL/TP as original (cascade_flip already tried to place HL SL/TP via `hl_place_sl/tp`). Let ATR recompute from there on the next cycle.

---

## Open Questions

1. Should the post-flip position's `signal_source` field indicate it was a cascade flip? (Yes — set to `cascade-reverse-{source}`)
2. Should we also increment the flip count in the new trade's record for A/B test tracking?
3. Should `cascade_sequences` be the authoritative record of flip history instead of flip_counts.json? (flip_counts.json is simpler for hot-set eviction, cascade_sequences is for analysis — keep both)
4. What happens if the market order for the new position fails (step 2 of cascade_flip)? Currently returns True (close succeeded). Should we retry or log an alert?
5. Should we also clear the flip count after CASCADE_FLIP_MAX flips and the token is locked? Or does eviction still apply during the lockout period?
