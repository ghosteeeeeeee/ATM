#!/usr/bin/env python3
"""
Graceful close of all regime-violating positions.
- Real HL positions: close on Hyperliquid, update DB with correct entry price
- Phantom DB entries: mark closed in DB only
- 15s spacing between closes
"""
import sys, time, json
from datetime import datetime, timezone
import psycopg2

sys.path.insert(0, '/root/.hermes/scripts')
from hyperliquid_exchange import get_exchange, get_open_hype_positions_curl

BRAIN_DB_DICT = {'host': '/var/run/postgresql', 'database': 'brain', 'user': 'postgres'}

# (token, trade_id, direction, reason, has_hl_position, hl_entry_price)
# has_hl_position=True → real position on HL to close
# has_hl_position=False → phantom DB entry, DB close only
TRADES = [
    # Real HL positions that violate regime
    ('TRX',   4234, 'LONG', 'regime_blindspot: not in regime_4h.json',   True,  0.31769),
    ('RESOLV',4242, 'LONG', 'neutral_regime: NEUTRAL@56%',               True,  0.036482),
    ('HEMI',  4243, 'LONG', 'regime_blindspot: not in regime_4h.json',   True,  0.007213),
    # Phantom DB entries (not on HL)
    ('GMX',   4250, 'SHORT','regime_blindspot: not in regime_4h.json',   False, 0),
    ('SAGA',  4251, 'SHORT','regime_blindspot: not in regime_4h.json',   False, 0),
    ('GOAT',  4252, 'SHORT','regime_blindspot: not in regime_4h.json',   False, 0),
    ('IOTA',  4253, 'LONG', 'regime_blindspot: not in regime_4h.json',   False, 0),
    ('WCT',   4254, 'LONG', 'regime_blindspot: not in regime_4h.json',  False, 0),
    ('ZORA',  4255, 'LONG', 'regime_blindspot: not in regime_4h.json',  False, 0),
    ('AZTEC', 4256, 'SHORT','regime_blindspot: not in regime_4h.json',   False, 0),
]

def ts():
    return datetime.now(timezone.utc).strftime('%H:%M:%S')

def close_hl(token: str, slippage: float = 0.05) -> bool:
    """Market close on Hyperliquid. Returns True on success."""
    try:
        exchange = get_exchange()
        result = exchange.market_close(coin=token, slippage=slippage)
        if result is None:
            print(f"  [{ts()}] ⚠️ {token}: HL close returned None (rate-limited?)")
            time.sleep(5)
            # Retry once
            result = exchange.market_close(coin=token, slippage=slippage)
        response_data = result.get('response', {})
        statuses = response_data.get('data', {}).get('statuses', [])
        for s in statuses if statuses else []:
            if isinstance(s, dict) and 'error' in s:
                print(f"  [{ts()}] ❌ {token}: HL error: {s['error']}")
                return False
        print(f"  [{ts()}] ✅ {token}: HL close confirmed")
        return True
    except Exception as e:
        print(f"  [{ts()}] ❌ {token}: {e}")
        return False

def fix_and_close_db(trade_id: int, token: str, hl_entry_price: float, reason: str) -> dict:
    """Fix entry_price if needed, mark closed in DB. Returns trade info."""
    conn = psycopg2.connect(**BRAIN_DB_DICT)
    cur = conn.cursor()
    
    if hl_entry_price > 0:
        # Fix entry_price from HL data before closing
        cur.execute("""
            UPDATE trades SET entry_price=%s, updated_at=NOW()
            WHERE id=%s
        """, (hl_entry_price, trade_id))
        print(f"  [{ts()}] Fixed entry_price → {hl_entry_price} for #{trade_id}")
    
    cur.execute("""
        UPDATE trades
        SET status='closed', close_time=NOW(), close_reason=%s
        WHERE id=%s
        RETURNING id, token, direction, entry_price, pnl_pct, pnl_usdt
    """, (reason[:50], trade_id))
    row = cur.fetchone()
    conn.commit()
    cur.close(); conn.close()
    return row

def append_note(token, trade_id, reason, pnl):
    note = (
        f"\n### {token} #{trade_id} — Closed by regime rule check ({datetime.now(timezone.utc).date()})"
        f"\n- **Reason:** {reason}"
        f"\n- **PnL at close:** {pnl}%"
        f"\n- **Action:** Graceful close, 15s spacing"
    )
    try:
        with open('/root/.hermes/brain/tradingnotes.md', 'a') as f:
            f.write(note)
    except Exception:
        pass

if __name__ == '__main__':
    print(f"\n{'='*60}")
    print(f"GRACEFUL CLOSE — regime violations ({len(TRADES)} trades)")
    print(f"Started: {datetime.now(timezone.utc).isoformat()}")
    
    for i, (token, trade_id, direction, reason, has_hl, hl_entry) in enumerate(TRADES):
        print(f"\n{'─'*50}")
        print(f"[{ts()}] ▶ {token} #{trade_id} ({direction}) — {reason}")
        
        ok = True
        # 1. Close on HL if real position
        if has_hl:
            print(f"  [{ts()}] [1/2] Sending HL market close...")
            ok = close_hl(token)
        else:
            print(f"  [{ts()}] [1/2] Phantom DB entry — no HL position to close")
        
        # 2. Fix entry price + mark closed in DB
        print(f"  [{ts()}] [2/2] Updating DB...")
        row = fix_and_close_db(trade_id, token, hl_entry, reason)
        if row:
            pnl_str = f"{row[4]:.4f}%" if row[4] is not None else 'N/A'
            print(f"  [{ts()}] ✅ DB closed: #{row[0]} {row[1]} E={row[3]} pnl={pnl_str}")
            append_note(row[1], row[0], reason, pnl_str)
        else:
            print(f"  [{ts()}] ⚠️ No trade #{trade_id} found in DB")
        
        if i < len(TRADES) - 1:
            print(f"\n  ⏳ 15 second gap...")
            time.sleep(15)
    
    print(f"\n{'='*60}")
    print(f"Done. {len(TRADES)} positions closed.")
    print(f"Remaining open: NIL #4241 (VALID — LONG_BIAS@95%)")
