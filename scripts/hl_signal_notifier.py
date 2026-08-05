#!/usr/bin/env python3
"""
HL Copy Trading - Signal Notifier
Fires signals when pro traders execute trades.
"""
import json
import os
import time
from datetime import datetime
from hl_copy_db import get_db
from paths import HERMES_DATA, WWW_DATA

def get_new_trades(since_minutes: int = 5) -> list:
    """Get trades from the last N minutes."""
    conn = get_db()
    try:
        cutoff = int(time.time()) - (since_minutes * 60)
        trades = conn.execute("""
            SELECT f.*, t.score, t.alias
            FROM trader_fills f
            JOIN traders t ON f.wallet = t.wallet
            WHERE f.time > ? AND f.time > 1000000000000
            ORDER BY f.time DESC
        """, (cutoff * 1000,)).fetchall()  # Convert to milliseconds
        return [dict(t) for t in trades]
    finally:
        conn.close()

def format_signal(trade: dict) -> str:
    """Format a trade as a signal message."""
    wallet_short = trade['wallet'][:10] + "..."
    side = "🟢 LONG" if trade['side'] == 'B' else "🔴 SHORT"
    coin = trade['coin']
    price = f"${trade['px']:,.2f}"
    size = f"{trade['sz']:.4f}"
    score = trade.get('score', 0)
    pnl = trade.get('closed_pnl', 0)
    
    # Convert timestamp
    ts = trade['time']
    if ts > 1e12:
        ts = ts / 1000
    time_str = datetime.fromtimestamp(ts).strftime("%H:%M:%S")
    
    signal = f"""
🚨 **PRO TRADER SIGNAL**

**Trader:** {wallet_short} (Score: {score})
**Time:** {time_str}
**Action:** {side}
**Coin:** {coin}
**Price:** {price}
**Size:** {size}
"""
    
    if pnl != 0:
        pnl_str = f"+${pnl:.2f}" if pnl > 0 else f"-${abs(pnl):.2f}"
        signal += f"**PnL:** {pnl_str}\n"
    
    return signal

def save_signal(signal: str, trade: dict):
    """Save signal to file for dashboard."""
    signal_file = f"{WWW_DATA}/hl_signals.json"
    
    try:
        with open(signal_file) as f:
            signals = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        signals = []
    
    signals.insert(0, {
        'time': trade['time'],
        'wallet': trade['wallet'],
        'coin': trade['coin'],
        'side': trade['side'],
        'price': trade['px'],
        'size': trade['sz'],
        'score': trade.get('score', 0),
        'signal': signal,
        'read': False
    })
    
    # Keep last 100 signals
    signals = signals[:100]
    
    # Atomic write
    tmp_path = signal_file + '.tmp'
    with open(tmp_path, 'w') as f:
        json.dump(signals, f, indent=2)
    os.replace(tmp_path, signal_file)

def check_for_signals():
    """Check for new trades and fire signals."""
    trades = get_new_trades(since_minutes=2)
    
    if not trades:
        return []
    
    signals = []
    for trade in trades:
        # Only signal for high-score traders (>= 70)
        if trade.get('score', 0) >= 70:
            signal = format_signal(trade)
            save_signal(signal, trade)
            signals.append(signal)
            print(signal)
    
    return signals

if __name__ == "__main__":
    print("[signal] Checking for pro trader signals...")
    signals = check_for_signals()
    
    if not signals:
        print("[signal] No new signals from pro traders")
    else:
        print(f"\n[signal] {len(signals)} signal(s) fired!")
