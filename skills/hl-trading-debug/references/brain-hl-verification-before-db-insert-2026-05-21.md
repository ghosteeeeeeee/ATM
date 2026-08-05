# Brain HL Verification Before DB Insert (2026-05-21)

## The Bug

brain.py calls `mirror_open()` on Hyperliquid. When HL returns `success=True`, brain.py assumes the position exists and writes to the PostgreSQL DB. But `success=True` from HL's exchange API only means the order was SENT — not that it filled. If the market order fails mid-fill (margin insufficient, delisted asset, slippage rejection), HL can report a fill failure with a success wrapper. Result: phantom DB record, no HL position, "trade opened and closed immediately."

## Symptoms

- "Trade opened and closed in the same cycle"
- "Position not mirrored in local DB"
- `close_reason=atr_sl_hit` but price was nowhere near SL
- DB has `status=closed` record with exit near entry, small PnL

## DOT #10226 Timeline (Real Example)

```
22:06:08  brain.py: mirror_open(DOT, SHORT) → HL fills at ~1.2465
           DB INSERT succeeds: trade #10226 written (status=open, entry=1.2465)
22:06:08  Position Manager runs → sees DOT in open positions
22:06:20  Position Manager runs again → DOT not in open positions
           → close_paper_position(DOT, "atr_sl_hit")
           → DB closed: exit=1.2459, close_reason=atr_sl_hit (market price, NOT SL)
           → SHORT was +0.048% profit — SL was 3% away, NOT hit
22:06:27  Guardian runs → sees DOT on HL but not in DB → mirror_close(DOT)
22:06:27  HL:4 DB:4 — consistent, no orphan reported
```

**Key insight:** `atr_sl_hit` is catch-all when PM can't find the real reason a position left the open list.

## The Fix (brain.py lines 493-514, implemented 2026-05-21)

After `mirror_open` returns `success=True` and before DB INSERT:

```python
if not result.get("success"):
    print(f"[brain.py] ❌ mirror_open FAILED for {hype_token}: {result.get('message')}")
    return None   # ← NO DB write

# ── VERIFY: Confirm HL actually has the position before writing to DB ────
try:
    from hyperliquid_exchange import get_open_hype_positions
    verify_positions = get_open_hype_positions()
    if not any(p.get('coin', '').upper() == hype_token.upper() and float(p.get('size', 0)) != 0
               for p in verify_positions):
        print(f"[brain.py] ❌ mirror_open reported success but {hype_token} not in HL positions")
        try:
            from hyperliquid_exchange import close_position
            close_position(hype_token)  # clean up any partial fill
        except Exception:
            pass
        return None
    print(f"[brain.py]    ✅ {hype_token} confirmed on HL (verification passed)")
except Exception as verify_err:
    # Proceed if verification fails — mirror_open already succeeded, guardian will catch orphans
    print(f"[brain.py] ⚠️ HL verification error: {verify_err}")
```

## Diagnostic Query — Check for Phantom DB Records

```python
from _secrets import BRAIN_DB_DICT
import psycopg2
conn = psycopg2.connect(**BRAIN_DB_DICT)
cur = conn.cursor()
cur.execute("""
    SELECT id, token, direction, entry_price, exit_price, stop_loss,
           pnl_pct, close_reason, hl_notional_usdt
    FROM trades
    WHERE status='closed'
      AND close_reason='atr_sl_hit'
      AND close_time IS NOT NULL
    ORDER BY close_time DESC
    LIMIT 20
""")
for r in cur.fetchall():
    id_, tok, dir_, entry, exit_px, sl, pnl, reason, hl_not = r
    # For SHORT: if exit < entry (profit) and exit > sl (nowhere near SL), it's a phantom
    if dir_ == 'SHORT':
        real_sl_hit = (exit_px >= sl) if sl else False
    else:
        real_sl_hit = (exit_px <= sl) if sl else False
    profit = (dir_ == 'SHORT' and exit_px < entry) or (dir_ == 'LONG' and exit_px > entry)
    print(f"#{id_} {tok} {dir_}: entry={entry:.4f} exit={exit_px:.4f} SL={sl:.4f} "
          f"pnl={pnl:.4f}% profit={profit} real_sl_hit={real_sl_hit} "
          f"hl_notional={hl_not}")
conn.close()
```

## Monitoring Pattern

When T reports "trade opened and closed immediately":
1. Check `pipeline.log` — `✅ confirmed on HL` = verification passed; `❌ FAILED` = mirror_open rejected
2. Check `sync-guardian.log` — HL count vs DB count at same timestamp
3. Query trade record — exit vs SL vs entry to determine if SL was actually hit
4. For SHORT: profit if exit < entry; SL hit only if exit >= sl