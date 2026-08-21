#!/usr/bin/env python3
"""
HL Copy Trading - Fill Monitor
Tracks real-time fills from monitored wallets.
"""
import json
import time
import os
import urllib.request
from hl_copy_db import get_db, init_db
from paths import HERMES_DATA, CANDLES_DB, PRICES_FILE

BASE_URL = "https://api.hyperliquid.xyz/info"
LAST_FILLS_FILE = os.path.join(HERMES_DATA, 'hl_copy_last_fills.json')

def _hl_info(payload: dict):
    """Make a POST request to HL info endpoint. Returns dict or list."""
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        BASE_URL,
        data=data,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"[hl_info] Error: {e}")
        return None

def load_last_fills() -> dict:
    """Load last known fill times per wallet."""
    try:
        with open(LAST_FILLS_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}

def save_last_fills(data: dict):
    """Save last known fill times (atomic write)."""
    tmp_path = LAST_FILLS_FILE + '.tmp'
    try:
        with open(tmp_path, 'w') as f:
            json.dump(data, f)
        os.replace(tmp_path, LAST_FILLS_FILE)
    except Exception as e:
        print(f"[save_last_fills] Error: {e}")
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def get_fills_since(wallet: str, since: int) -> list:
    """Get fills since a specific timestamp."""
    result = _hl_info({
        "type": "userFills",
        "user": wallet
    })
    if not isinstance(result, list):
        return []
    
    return [f for f in result if f.get('time', 0) > since]

def detect_new_trades(wallet: str, current_fills: list, last_known_time: int) -> list:
    """Detect new trades from a wallet."""
    new_fills = []
    
    for fill in current_fills:
        fill_time = fill.get('time', 0)
        if fill_time > last_known_time:
            # Determine if this is an open or close
            direction = fill.get('dir', '')
            is_open = direction.startswith('Open')
            
            new_fills.append({
                'wallet': wallet,
                'coin': fill.get('coin', ''),
                'side': fill.get('side', ''),
                'px': float(fill.get('px', 0)),
                'sz': float(fill.get('sz', 0)),
                'time': fill_time,
                'closed_pnl': float(fill.get('closedPnl', 0)),
                'is_open': 1 if is_open else 0,
                'hash': fill.get('hash', '')
            })
    
    return new_fills

def log_fills_batch(fills: list):
    """Log multiple fills to the database in one connection."""
    if not fills:
        return
    
    conn = get_db()
    try:
        for fill in fills:
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO trader_fills 
                    (wallet, coin, side, px, sz, time, closed_pnl, is_open)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    fill['wallet'],
                    fill['coin'],
                    fill['side'],
                    fill['px'],
                    fill['sz'],
                    fill['time'],
                    fill['closed_pnl'],
                    fill['is_open']
                ))
            except Exception as e:
                print(f"[log_fills_batch] Error inserting fill: {e}")
        conn.commit()
    finally:
        conn.close()

def update_positions(wallet: str):
    """Update current positions for a wallet."""
    result = _hl_info({
        "type": "clearinghouseState",
        "user": wallet
    })
    
    if not isinstance(result, dict) or 'assetPositions' not in result:
        return
    
    conn = get_db()
    try:
        now = int(time.time())
        
        # Clear old positions for this wallet
        conn.execute("DELETE FROM trader_positions WHERE wallet = ?", (wallet,))
        
        # Insert current positions
        for pos in result['assetPositions']:
            p = pos.get('position', {})
            coin = p.get('coin', '')
            if not coin:
                continue
            
            sz = float(p.get('szi', 0))
            if sz == 0:
                continue
            
            # Handle leverage which can be a dict or number
            leverage_raw = p.get('leverage', 1)
            if isinstance(leverage_raw, dict):
                leverage = float(leverage_raw.get('value', 1))
            else:
                leverage = float(leverage_raw)
            
            conn.execute("""
                INSERT INTO trader_positions 
                (wallet, coin, sz, entry_px, unrealized_pnl, leverage, liquidation_px, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                wallet,
                coin,
                sz,
                float(p.get('entryPx', 0)),
                float(p.get('unrealizedPnl', 0)),
                leverage,
                float(p.get('liquidationPx', 0)) if p.get('liquidationPx') else None,
                now
            ))
        
        conn.commit()
    finally:
        conn.close()

def get_active_traders() -> list:
    """Get all active tracked traders."""
    conn = get_db()
    try:
        traders = conn.execute(
            "SELECT wallet, score FROM traders WHERE active = 1"
        ).fetchall()
        return [{'wallet': t['wallet'], 'score': t['score']} for t in traders]
    finally:
        conn.close()

def monitor_once() -> list:
    """Run one monitoring cycle. Returns list of new fills."""
    last_fills = load_last_fills()
    active = get_active_traders()
    all_new_fills = []
    
    for trader in active:
        wallet = trader['wallet']
        last_time = last_fills.get(wallet, 0)
        
        # Get new fills
        fills = get_fills_since(wallet, last_time)
        new_fills = detect_new_trades(wallet, fills, last_time)
        
        if new_fills:
            # Log to database (batch)
            log_fills_batch(new_fills)
            all_new_fills.extend(new_fills)
            
            # Update last known time
            last_fills[wallet] = max(f['time'] for f in new_fills)
            
            # Update positions
            update_positions(wallet)
            
            print(f"[monitor] {wallet[:10]}... new fills: {len(new_fills)}")
        
        time.sleep(0.3)  # Rate limit
    
    save_last_fills(last_fills)
    return all_new_fills

def get_recent_fills(limit: int = 50) -> list:
    """Get recent fills from all tracked traders."""
    conn = get_db()
    try:
        fills = conn.execute("""
            SELECT f.*, t.score 
            FROM trader_fills f
            JOIN traders t ON f.wallet = t.wallet
            ORDER BY f.time DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(f) for f in fills]
    finally:
        conn.close()

def get_trader_positions(wallet: str) -> list:
    """Get current positions for a trader."""
    conn = get_db()
    try:
        positions = conn.execute(
            "SELECT * FROM trader_positions WHERE wallet = ?",
            (wallet,)
        ).fetchall()
        return [dict(p) for p in positions]
    finally:
        conn.close()


# ── Copy Trader Exit Correlation ──────────────────────────────────────────────

def get_open_copy_trade(wallet: str, coin: str) -> dict | None:
    """Find open copy trade for this wallet+coin in trader_performance."""
    conn = get_db()
    try:
        row = conn.execute("""
            SELECT * FROM trader_performance
            WHERE wallet = ? AND token = ? AND status = 'open'
            LIMIT 1
        """, (wallet, coin.upper())).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def is_trader_full_exit(wallet: str, coin: str) -> bool:
    """Check if trader has no remaining position (not just partial close)."""
    conn = get_db()
    try:
        row = conn.execute("""
            SELECT sz FROM trader_positions
            WHERE wallet = ? AND coin = ?
        """, (wallet, coin.upper())).fetchone()
        if not row:
            return True  # No position record = fully exited
        return abs(float(row['sz'])) < 0.0001  # Effectively zero
    finally:
        conn.close()


def get_current_price(coin: str) -> float | None:
    """Get current price from candles DB or prices cache."""
    try:
        import sqlite3
        conn = sqlite3.connect(CANDLES_DB, timeout=5)
        row = conn.execute("""
            SELECT close FROM candles
            WHERE token = ? ORDER BY ts DESC LIMIT 1
        """, (coin.upper(),)).fetchone()
        conn.close()
        if row:
            return float(row[0])
    except Exception:
        pass

    # Fallback: prices.json cache
    try:
        with open(PRICES_FILE) as f:
            prices = json.load(f)
        return float(prices.get(coin.upper(), {}).get('price', 0))
    except Exception:
        return None


def _update_trader_aggregates(conn, wallet: str):
    """Recompute copy_trades, copy_wins, copy_pnl, copy_weight for a trader."""
    try:
        from hermes_constants import COPY_TRADE_WEIGHT_MIN, COPY_TRADE_WEIGHT_MAX, COPY_TRADE_WEIGHT_MIN_TRADES
    except ImportError:
        COPY_TRADE_WEIGHT_MIN, COPY_TRADE_WEIGHT_MAX, COPY_TRADE_WEIGHT_MIN_TRADES = 0.1, 2.0, 5

    stats = conn.execute("""
        SELECT COUNT(*) as total,
               SUM(CASE WHEN status = 'closed_win' THEN 1 ELSE 0 END) as wins,
               SUM(COALESCE(pnl_pct, 0)) as total_pnl
        FROM trader_performance
        WHERE wallet = ? AND status LIKE 'closed_%'
    """, (wallet,)).fetchone()

    total = stats['total'] or 0
    wins = stats['wins'] or 0
    total_pnl = stats['total_pnl'] or 0
    wr = wins / total if total > 0 else 0.5

    # Weight calculation
    weight = 1.0
    if total >= COPY_TRADE_WEIGHT_MIN_TRADES:
        wr_bonus = (wr - 0.5) * 2.0
        pnl_bonus = max(-0.5, min(0.5, total_pnl / 10))
        sample_adj = max(0, 1.0 - total / 20)
        weight = max(COPY_TRADE_WEIGHT_MIN, min(COPY_TRADE_WEIGHT_MAX,
                      1.0 + wr_bonus + pnl_bonus + sample_adj))

    conn.execute("""
        UPDATE traders SET copy_weight = ?, copy_trades = ?, copy_wins = ?, copy_pnl = ?
        WHERE wallet = ?
    """, (weight, total, wins, total_pnl, wallet))


def update_trader_performance(trade_id: int, exit_price: float, close_reason: str):
    """Close a trader_performance row and update trader stats."""
    conn = get_db()
    try:
        row = conn.execute("""
            SELECT * FROM trader_performance WHERE trade_id = ? AND status = 'open'
        """, (trade_id,)).fetchone()
        if not row:
            return

        entry = float(row['entry_price'])
        direction = row['direction']
        wallet = row['wallet']

        # Compute PnL
        if direction == 'LONG':
            pnl_pct = ((exit_price - entry) / entry) * 100 if entry > 0 else 0
        else:
            pnl_pct = ((entry - exit_price) / entry) * 100 if entry > 0 else 0

        status = ('closed_win' if pnl_pct > 0.1
                  else 'closed_loss' if pnl_pct < -0.1
                  else 'closed_breakeven')

        conn.execute("""
            UPDATE trader_performance
            SET exit_price = ?, pnl_pct = ?, status = ?, close_reason = ?, closed_at = ?
            WHERE trade_id = ? AND status = 'open'
        """, (exit_price, pnl_pct, status, close_reason, int(time.time()), trade_id))

        _update_trader_aggregates(conn, wallet)
        conn.commit()
        print(f"[copy_exit] trade #{trade_id} {row['token']} {direction} → {status} "
              f"({pnl_pct:+.2f}%) reason={close_reason}")
    finally:
        conn.close()


def check_trader_exits(new_fills: list):
    """When a tracked trader FULLY CLOSES a position, close our corresponding copy trade."""
    try:
        from hermes_constants import COPY_TRADE_EXIT_ENABLED
    except ImportError:
        COPY_TRADE_EXIT_ENABLED = False

    if not COPY_TRADE_EXIT_ENABLED:
        return

    closed_fills = [f for f in new_fills if f.get('is_open') == 0]

    for fill in closed_fills:
        wallet = fill['wallet']
        coin = fill['coin']

        # Verify full exit (not partial close)
        if not is_trader_full_exit(wallet, coin):
            continue

        # Find our open trade
        perf = get_open_copy_trade(wallet, coin)
        if not perf:
            continue

        # Prevent race with profit_monster/cut_loser
        try:
            from cut_loser import is_token_being_closed_by_profit_monster
            if is_token_being_closed_by_profit_monster(coin):
                continue
        except ImportError:
            pass

        # Get current market price
        current_price = get_current_price(coin)
        if not current_price or current_price <= 0:
            print(f"[copy_exit] {coin}: no price available, skipping")
            continue

        # Close our trade
        try:
            from brain import close_trade
            close_trade(
                trade_id=perf['trade_id'],
                exit_price=current_price,
                close_reason='trader_exit',
                notes=f"Trader {wallet[:10]}... exited {coin}"
            )
            update_trader_performance(perf['trade_id'], current_price, 'trader_exit')
        except Exception as e:
            print(f"[copy_exit] Error closing trade #{perf['trade_id']}: {e}")

if __name__ == "__main__":
    init_db()
    print("[fill_monitor] Starting monitor...")
    
    # Add a test wallet
    conn = get_db()
    try:
        conn.execute("""
            INSERT OR IGNORE INTO traders (wallet, score, active) 
            VALUES (?, 75, 1)
        """, ("0x324a9713603863FE3A678E83d7a81E20186126E7",))
        conn.commit()
    finally:
        conn.close()
    
    # Run one cycle
    new_fills = monitor_once()
    print(f"\n[fill_monitor] Found {len(new_fills)} new fills")
    
    # Show recent fills
    recent = get_recent_fills(10)
    for f in recent:
        print(f"  {f['wallet'][:10]}... | {f['coin']} {f['side']} @ {f['px']} | {f['sz']}")
