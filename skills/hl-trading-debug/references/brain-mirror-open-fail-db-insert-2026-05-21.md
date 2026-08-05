# brain.py: mirror_open FAIL → Phantom DB Record (DOT #10226)

**Date:** 2026-05-20
**Severity:** CRITICAL — phantom DB record, corrupt trade history
**Status:** ROOT CAUSE IDENTIFIED — fix pending

## What Happened (Full Timeline)

```
22:06:08  decider_run calls brain.py → add_trade(DOT, SHORT, 50.0, 1.2511)
           brain.py INSERT trade #10226 into PostgreSQL → COMMITTED ✅
           brain.py calls mirror_open(DOT, SHORT, 1.2511, leverage=5)
           → HL replied: {"success": false, "message": "Insufficient margin to place order. asset=48"}
           brain.py prints error but DOES NOT ROLLBACK the DB record ❌
22:06:11  guardian orphan detection cycle:
           → saw no HL position for DOT (mirror_open never succeeded)
           → saw DOT in DB as "open" (phantom record)
           → treated as orphan, closed DB record as guardian_orphan
           → HL side: no position existed, nothing to close
22:06:20  Position Manager cycle:
           → refresh_current_prices: sees DOT in DB as "open"
           → check_atr_tp_sl_hits: DOT SL=1.2084, current=1.2459 → SHORT: cur>=SL = TRUE (but price never touched SL!)
           → close_paper_position(trade_id=10226, reason="atr_sl_hit")
           → DB: exit=1.2459, pnl=+0.0481%, pnl_usdt=0.02
22:07:11  Next Position Manager cycle: 5 open | 0 closed (DOT gone)
```

## Root Cause

**brain.py inserts a trade record into PostgreSQL BEFORE calling mirror_open**, then does NOT rollback if mirror_open fails.

The DB INSERT was designed to run first (to get the trade_id before HL call), but when `mirror_open` fails with `success=False`, brain.py prints the error and returns — but the DB record was already committed.

Result: a phantom DB record (trade exists in PostgreSQL, no corresponding HL position).

## DB Record at Close (trade #10226)

```
id:             10226
token:          DOT
direction:      SHORT
entry_price:    1.246500
stop_loss:      1.208400
target:         1.186800
current_price:  1.245900
highest_price:  1.245900
lowest_price:   1.200000
atr_managed:    0.02
pnl_pct:        0.0481
pnl_usdt:       0.02
hl_entry_price: 1.200000    ← stale from prior cycle (not from this entry)
hl_exit_price:  0E-8        ← no fill
hl_notional:    None        ← mirror_open never got a fill
open_time:      2026-05-20 22:06:08
close_time:     2026-05-20 22:06:11
close_reason:   atr_sl_hit
is_guardian_close: False
guardian_reason: None
hype_realized_pnl: -0.0033  ← guardian fallback on close
hype_realized_pnl_pct: -0.0066
```

## Why atr_sl_hit Was Wrong

`check_atr_tp_sl_hits` logic for SHORT:
- SL = 1.2084 (3.06% below entry)
- current_price = 1.2459 (at time of check)
- Condition: `current_price >= SL` → `1.2459 >= 1.2084 = TRUE`
- **BUT price never actually touched 1.2084** — the position was opened and closed within 3 seconds

The SL was a stale value from a prior cycle. The position manager evaluated it against a price that was never near the SL.

## Fix Required

In `brain.py` `add_trade()`, after `mirror_open` fails at ~line 490:

```python
result = mirror_open(hype_token, direction, float(entry_price), leverage=leverage)
print(f"[brain.py] ← mirror_open returned: success={result.get('success')}, "
      f"message={result.get('message')}")

if not result.get('success'):
    print(f"[brain.py] ❌ mirror_open FAILED for {hype_token}: {result.get('message')}")
    # ROLLBACK the DB record that was inserted above
    if conn and trade_id is not None:
        conn.rollback()
        print(f"[brain.py] → Rolled back DB record trade_id={trade_id}")
    return None  # don't proceed
```

Key: the rollback must use the `trade_id` captured from the INSERT, and must happen before the function returns.

## Diagnostic Query

```python
# Find all phantom trades (DB record but no real HL position)
python3 << 'EOF'
import sys; sys.path.insert(0, '/root/.hermes/scripts')
from _secrets import BRAIN_DB_DICT
import psycopg2
conn = psycopg2.connect(**BRAIN_DB_DICT)
cur = conn.cursor()
cur.execute("""
    SELECT id, token, direction, entry_price, hl_entry_price, hl_notional_usdt,
           open_time, close_time, close_reason, hype_realized_pnl
    FROM trades
    WHERE status='closed'
      AND hl_notional_usdt IS NULL
      AND close_time > NOW() - INTERVAL '1 day'
    ORDER BY open_time DESC
""")
for r in cur.fetchall():
    print(f"trade_id={r[0]} {r[1]} {r[2]} entry={r[3]} hl_entry={r[4]} "
          f"hl_notional={r[5]} opened={r[6]} closed={r[7]} reason={r[8]} hype_pnl={r[9]}")
EOF
```

## Prevention

Before calling `mirror_open`, check that the position size is above `HL_MIN_NOTIONAL_USDT` to avoid the "Insufficient margin" failure path entirely:

```python
effective_amount = amount_usdt / leverage
if effective_amount < HL_MIN_NOTIONAL_USDT:
    print(f"[brain.py] ❌ {token} position size ${effective_amount:.2f} below "
          f"HL minimum ${HL_MIN_NOTIONAL_USDT} — skipping")
    return None
```

`HL_MIN_NOTIONAL_USDT` ≈ $11 (minimum notional on HL for 5x leverage on a ~$1 token).
