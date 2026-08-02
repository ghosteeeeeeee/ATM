# Plan: Fix Trades Not Reaching Hyperliquid — HL First + Signal Rollback on Failure

## Goal
Fix the bug where approved signals are marked `executed=1` but never reach Hyperliquid because `brain.py` writes to the local DB before calling HL — if HL fails, the signal is permanently consumed with no trade anywhere.

**Core fix two parts:**
1. **HL-first ordering** in `brain.py add_trade()` — write to local DB only after HL confirms
2. **Signal rollback on HL failure** in `decider_run` — if HL fails, restore `executed=0` so the signal stays alive in the hot-set for retry

---

## Current Flow (Broken)

```
decider_run._process_approved_signals()
  1. mark_signal_executed(token, direction)   ← executed=1 immediately
  2. execute_trade() → brain.py trade add
  3. brain.py add_trade():
     a. INSERT into trades DB               ← trade written
     b. mirror_open() to HL
     c. IF mirror_open FAILS → DELETE from trades DB
     d. IF live_trading OFF → DELETE from trades DB
  4. Signal is executed=1 → permanently consumed
  5. No trade in DB, no position on HL → ghost slot
```

---

## New Flow (Fixed)

```
decider_run._process_approved_signals()
  1. mark_signal_executed(token, direction)   ← executed=1 immediately
  2. execute_trade() → brain.py trade add
  3. brain.py add_trade():
     a. Pre-checks: is_live_trading, not delisted, not blacklisted, not duplicate open
     b. mirror_open() on HL FIRST
        - IF HL fails → return None immediately (no DB write)
     c. IF HL confirms → INSERT into trades DB (paper=False)
     d. Place SL + TP on HL
     e. Return trade_id
  4. decider_run receives result:
     - trade_id returned → ✅ HL has position, DB has record, done
     - None returned → ❌ HL failed
       → rollback_signal_executed() → signal stays APPROVED, retries next cycle
```

**Key property:** HL failure = signal stays alive, retry next pipeline cycle. No ghost slots.

---

## File Changes

### File 1: `/root/.hermes/scripts/brain.py`

**Function:** `add_trade()` — lines 282 through 488

**Replace the entire function body** with the HL-first version below.

```python
def add_trade(token: str, side_type: str, amount_usdt: float, entry_price: float,
               exchange: str = "Hyperliquid", strategy: str = None, paper: bool = False,
               stop_loss: float = None, target: float = None, server: str = "Hermes",
               signal: str = None, confidence: float = None, address: str = None,
               sl_group: str = "control", sl_distance: float = None,
               trailing_activation: float = None, trailing_distance: float = None,
               trailing_phase2_dist: float = None,
               leverage: int = 1, experiment: str = None,
               flipped_from_trade: bool = False):
    """
    Add a new trade. HL-first: open on Hyperliquid FIRST, write to local DB only
    if HL confirms. This eliminates phantom trades (DB writes that get deleted when
    HL fails, leaving consumed signals with no corresponding position).
    """
    # ── Normalize direction ──────────────────────────────────────────────
    side_type = side_type.lower() if side_type else 'long'
    direction = 'LONG' if side_type == 'long' else 'SHORT'

    # ── Step 1: Pre-flight checks (before any HL call) ─────────────────

    # Block conf-1s at the trade entry level
    if strategy and strategy.startswith('Hermes-conf-'):
        try:
            num = int(strategy.split('-')[-1].rstrip('s'))
            if num == 1:
                print(f"✗ REJECTED: {token} {side_type} — conf-1s (single-source, min 2 required)")
                print(f"  Signal: '{signal}' | Strategy: '{strategy}'")
                return None
        except (ValueError, IndexError):
            pass
    if signal == 'conf-1s':
        print(f"✗ REJECTED: {token} {side_type} — conf-1s (single-source, min 2 required)")
        return None

    # Block noisy signal sources
    NOISE_SIGNALS = {'pct-hermes', 'vel-hermes', 'rsi-hermes'}
    if signal in NOISE_SIGNALS:
        print(f"✗ REJECTED: {token} {side_type} — noisy signal source '{signal}' blocklisted")
        return None

    # ── Step 2: HL-first — open on Hyperliquid before any DB write ─────
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from hyperliquid_exchange import (mirror_open, hype_coin,
                                       is_live_trading_enabled, is_delisted)

    if not is_live_trading_enabled():
        print(f"[brain.py] Live trading OFF — rejecting {token} {direction}")
        return None

    if is_delisted(token):
        print(f"[brain.py] {token} is delisted on Hyperliquid — rejecting")
        return None

    hype_token = hype_coin(token)

    # Blacklist check
    from hermes_constants import SHORT_BLACKLIST, LONG_BLACKLIST
    blocked = (direction == 'SHORT' and hype_token in SHORT_BLACKLIST) or \
              (direction == 'LONG'  and hype_token in LONG_BLACKLIST)
    if blocked:
        bl = 'SHORT_BLACKLIST' if direction == 'SHORT' else 'LONG_BLACKLIST'
        print(f"[brain.py] {hype_token}: blocked by {bl} — rejecting")
        return None

    # Duplicate open check (still query DB for this — it's a local constraint)
    conn_check = get_db_connection()
    cur_check = conn_check.cursor()
    cur_check.execute(
        "SELECT id FROM trades WHERE token=%s AND server=%s AND status='open'",
        (token, server))
    if cur_check.fetchone():
        print(f"[brain.py] {token} already open on {server} — rejecting duplicate")
        return None
    cur_check.close(); conn_check.close()

    # A/B params (needed for HL order sizing)
    import random
    if sl_distance is None:
        groups = {"control": 0.03, "test_a": 0.015, "test_b": 0.01}
        sl_group = random.choice(list(groups.keys()))
        sl_distance = groups[sl_group]
    if trailing_activation is None:
        trailing_activation = 0.01
    if trailing_distance is None:
        trailing_distance = 0.01

    leverage = max(1, min(int(leverage), 5))  # cap at 5x

    # ── Step 3: mirror_open on HL ────────────────────────────────────────
    result = mirror_open(hype_token, direction, float(entry_price), leverage=leverage)
    if not result.get("success"):
        print(f"[brain.py] mirror_open FAILED for {hype_token}: {result.get('message')}")
        return None   # ← NO DB write, signal stays alive for retry

    # ── Step 4: HL confirmed — write to local DB ────────────────────────
    hl_entry = result.get("hl_entry_price") or result.get("entry_price")
    sz = result.get("size")

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO trades (token, direction, amount_usdt, entry_price,
                  exchange, strategy, paper, stop_loss, target, server, status, open_time,
                  signal, confidence, token_address, pnl_usdt, pnl_pct,
                  sl_distance, trailing_activation, trailing_distance,
                  trailing_phase2_dist, leverage, experiment,
                  flipped_from_trade, flip_variant,
                  hl_entry_price)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW(),%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        RETURNING id
    """, (token, direction, amount_usdt, hl_entry,
          exchange, strategy, False, stop_loss, target, server, 'open',
          signal, confidence, address, 0, 0,
          sl_distance, trailing_activation, trailing_distance,
          trailing_phase2_dist, leverage, experiment,
          int(flipped_from_trade) if flipped_from_trade else 0, 'signal-flip',
          hl_entry))
    trade_id = cur.fetchone()[0]
    conn.commit()
    cur.close(); conn.close()

    # ── Step 5: Place SL + TP on HL ─────────────────────────────────────
    if sz and stop_loss:
        from hyperliquid_exchange import place_sl as hl_place_sl, place_tp as hl_place_tp
        sl_result = hl_place_sl(hype_token, direction, float(stop_loss), float(sz))
        tp_result = hl_place_tp(hype_token, direction, float(target), float(sz)) \
                    if target else {"success": True}
        if sl_result.get("success"):
            conn_oid = get_db_connection()
            cur_oid = conn_oid.cursor()
            cur_oid.execute("""
                UPDATE trades SET hl_sl_order_id=%s, hl_tp_order_id=%s WHERE id=%s
            """, (sl_result.get("order_id"),
                  tp_result.get("order_id") if tp_result.get("success") else None,
                  trade_id))
            conn_oid.commit(); cur_oid.close(); conn_oid.close()

    print(f"[brain.py] ✅ {hype_token} {direction} trade #{trade_id} confirmed on HL @ ${hl_entry:.6f}")
    return trade_id
```

**What was removed from the old `add_trade()`:**
- Lines 340–361: DB-first INSERT (replaced by Step 4 above)
- Lines 363–369: `is_live_trading_enabled()` guard wrapping the whole HL block (now at top)
- Lines 370–390: HOT-SET GUARD in HL block (no longer needed — hot-set discipline is handled at decider_run level)
- Lines 446–486: All phantom deletion / cleanup code (no longer needed — nothing to delete)

**What changed:**
- `paper=True` → `paper=False` default (line 283)
- Pre-checks (blacklist, delisted, duplicate) are now BEFORE the HL call
- `paper=True` path (lines 384-389 old) and live-trading-OFF path (lines 461-473 old) are gone

---

### File 2: `/root/.hermes/scripts/decider_run.py`

**Function:** `_process_approved_signals()` — find the block after `execute_trade()` returns

Current code (approximate, lines 1627–1649):
```python
success, msg = execute_trade(
    token, direction, price, confidence, source,
    leverage=lev, paper=paper, ...
)

if success:
    log(f'  → ENTERED: {token} {direction} ({msg})')
    entered += 1
    open_count += 1
    ...
else:
    log(f'  ❌ FAILED: {token} {direction}: {msg}')
    _record_hotset_failure(token, direction, failures)
```

**Add rollback logic** in the `else` branch (after `execute_trade` returns failure):

```python
success, msg = execute_trade(
    token, direction, price, confidence, source,
    leverage=lev, paper=paper, ...
)

if success:
    log(f'  → ENTERED: {token} {direction} ({msg})')
    entered += 1
    open_count += 1
    ...
else:
    log(f'  ❌ FAILED: {token} {direction}: {msg}')
    _record_hotset_failure(token, direction, failures)
    # ── Option A: Roll back signal so it stays alive for retry ──────
    # brain.py returned None = HL rejected the trade (rate limit, balance,
    # delisted, etc.). The signal is still marked executed=1 from step 1.
    # Restore it to APPROVED/executed=0 so ai_decider's next compaction
    # can re-rank it and decider_run can retry.
    if sig_id:
        try:
            from signal_schema import rollback_signal_executed
            rolled = rollback_signal_executed(token, direction, signal_id=sig_id)
            if rolled:
                log(f'  🔁 SIGNAL ROLLED BACK: {token} {direction} (sig#{sig_id}) — stays in hot-set for retry')
            else:
                log(f'  ⚠️ ROLLBACK FAILED (signal already claimed by another process)')
        except Exception as rb_err:
            log(f'  ⚠️ ROLLBACK ERROR: {rb_err}')
```

**Add to `signal_schema.py`:**

```python
def rollback_signal_executed(token: str, direction: str, signal_id=None) -> bool:
    """
    Restore executed=0 on a signal so it can be retried.
    Uses the same atomic claim mechanism as mark_signal_executed —
    only rolls back if signal_id matches (prevents race conditions).
    Returns True if rollback succeeded, False if signal was already
    claimed by another process.
    """
    conn = get_db_connection()
    if conn is None:
        return False
    try:
        cur = conn.cursor()
        if signal_id is not None:
            # Atomic: only update if this exact signal_id is marked executed
            cur.execute("""
                UPDATE signals
                SET executed = 0, decision = 'APPROVED', updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND executed = 1
                RETURNING id
            """, (signal_id,))
        else:
            # Fallback: match by token + direction (may affect multiple rows)
            cur.execute("""
                UPDATE signals
                SET executed = 0, decision = 'APPROVED', updated_at = CURRENT_TIMESTAMP
                WHERE token = %s AND direction = %s AND executed = 1
                RETURNING id
            """, (token.upper(), direction.upper()))
        row = cur.fetchone()
        conn.commit()
        cur.close(); conn.close()
        return row is not None
    except Exception:
        return False
```

**What changed in decider_run.py:**
- 1 new `if sig_id:` block in the `else` branch after execute_trade fails
- 1 new helper function in signal_schema.py

---

### File 3: `/root/.hermes/scripts/signal_schema.py`

**Add:** `rollback_signal_executed()` function (see above, ~25 lines)

Place it near `mark_signal_executed()` (around line 893).

---

## Implementation Order

```
1. signal_schema.py  — add rollback_signal_executed()
2. brain.py          — replace add_trade() with HL-first version
3. decider_run.py    — add rollback call in execute_trade failure branch
4. Restart pipeline   — hermmes-pipeline.timer restart or manual run
```

---

## Verification Checklist

- [ ] `paper=False` is the only mode — no more `paper=True` path in brain.py
- [ ] `add_trade()` returns `None` when HL fails (no DB write, no deletion)
- [ ] `add_trade()` returns `trade_id` only after HL confirms + DB written
- [ ] decider_run rollback fires when brain.py returns None
- [ ] signal stays `executed=0` after rollback → next pipeline cycle can retry
- [ ] DOGE trade: check signals DB for DOGE signal state, confirm it can be retried
- [ ] Guardian: confirm paper=False trades reconcile correctly (no orphan false positives)

---

## Behavior Summary

| Scenario | brain.py return | Signal state | DB trade | HL position |
|----------|----------------|--------------|----------|-------------|
| HL succeeds | `trade_id` | `executed=1` | ✅ | ✅ |
| HL fails (rate limit) | `None` | `executed=0` (rolled back) | ❌ | ❌ |
| HL fails (balance/delisted/blacklist) | `None` | `executed=0` (rolled back) | ❌ | ❌ |
| Live trading OFF | `None` | `executed=0` (rolled back) | ❌ | ❌ |
| Guardian sees paper=False trade | — | — | ✅ | ✅ (reconciles) |

**No more ghost slots. No more phantom deletions. Every HL failure = signal stays alive for retry.**

---

## DOGE Trade Specific

The DOGE trade from the bug report (source=`hzscore,pct-hermes+`, status=`HL_CLOSED`) is already closed — either as a phantom close or a real HL close. Its signal is already `executed=1`.

**It will re-enter the pipeline naturally** if:
1. It still has a valid signal in the signals DB (check: `decision='APPROVED'`, `executed=0`)
2. It survives ai_decider's next compaction into the hot-set
3. A slot opens

Run this to check its current state:
```sql
SELECT token, direction, decision, executed, confidence, source, updated_at
FROM signals WHERE token='DOGE' ORDER BY updated_at DESC LIMIT 5;
```
