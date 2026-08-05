#!/usr/bin/env python3
"""
HL Copy Trading - Terminal UI
Live terminal view of tracked traders and copy activity.
"""
import curses
import time
import json
from datetime import datetime
from hl_copy_db import get_db, init_db

def get_traders():
    """Get active traders from DB."""
    conn = get_db()
    try:
        traders = conn.execute("""
            SELECT * FROM traders 
            WHERE active = 1
            ORDER BY score DESC
            LIMIT 10
        """).fetchall()
        return [dict(t) for t in traders]
    finally:
        conn.close()

def get_recent_fills(limit=15):
    """Get recent fills."""
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

def get_stats():
    """Get overall statistics."""
    conn = get_db()
    try:
        traders_count = conn.execute(
            "SELECT COUNT(*) as cnt FROM traders WHERE active = 1"
        ).fetchone()['cnt']
        
        cutoff_ms = int(time.time() * 1000) - 86_400_000
        today_fills = conn.execute(
            "SELECT COUNT(*) as cnt FROM trader_fills WHERE time > ?",
            (cutoff_ms,)
        ).fetchone()['cnt']
        
        today_pnl = conn.execute(
            "SELECT SUM(closed_pnl) as pnl FROM trader_fills WHERE time > ?",
            (cutoff_ms,)
        ).fetchone()['pnl'] or 0
        
        total_fills = conn.execute(
            "SELECT COUNT(*) as cnt FROM trader_fills"
        ).fetchone()['cnt']
        
        return {
            'traders': traders_count,
            'today_fills': today_fills,
            'today_pnl': today_pnl,
            'total_fills': total_fills
        }
    finally:
        conn.close()

def draw_header(stdscr, stats):
    """Draw header section."""
    height, width = stdscr.getmaxyx()
    
    # Title
    title = "HL COPY TRADING"
    stdscr.addstr(0, 0, "=" * width, curses.color_pair(1))
    stdscr.addstr(1, (width - len(title)) // 2, title, curses.color_pair(1) | curses.A_BOLD)
    
    # Stats
    stats_line = f" Traders: {stats['traders']} | Today: {stats['today_fills']} fills | PnL: ${stats['today_pnl']:+.2f} | Total: {stats['total_fills']} "
    stdscr.addstr(2, 0, stats_line.center(width), curses.color_pair(2))
    stdscr.addstr(3, 0, "=" * width, curses.color_pair(1))

def draw_traders(stdscr, traders, start_y=5):
    """Draw traders table."""
    height, width = stdscr.getmaxyx()
    
    # Header
    header = f"{'WALLET':<12} {'SCORE':>6} {'PnL':>12} {'WR':>6} {'TRADES':>7} {'PATTERN':<12} {'LAST':>6}"
    stdscr.addstr(start_y, 0, header, curses.A_BOLD)
    stdscr.addstr(start_y + 1, 0, "-" * (width - 1))
    
    # Rows
    for i, t in enumerate(traders[:10]):
        y = start_y + 2 + i
        if y >= height - 20:  # Leave room for fills
            break
        
        wallet_short = t['wallet'][:8] + ".."
        score = f"{t['score']:.1f}"
        pnl = f"${t['pnl_all_time']:+,.0f}"
        wr = f"{t['win_rate']:.0%}"
        trades = str(t['trade_count'])
        pattern = t['pattern'][:12] if t['pattern'] else 'N/A'
        
        if t['last_updated']:
            last_active = datetime.fromtimestamp(t['last_updated']).strftime("%H:%M")
        else:
            last_active = "N/A"
        
        # Color based on score
        if t['score'] >= 80:
            color = curses.color_pair(3)  # Green
        elif t['score'] >= 60:
            color = curses.color_pair(4)  # Yellow
        else:
            color = curses.color_pair(5)  # Red
        
        line = f"{wallet_short:<12} {score:>6} {pnl:>12} {wr:>6} {trades:>7} {pattern:<12} {last_active:>6}"
        stdscr.addstr(y, 0, line, color)
    
    return start_y + 2 + min(len(traders), 10) + 1

def draw_fills(stdscr, fills, start_y):
    """Draw recent fills table."""
    height, width = stdscr.getmaxyx()
    
    if start_y + 2 >= height:
        return
    
    # Header
    stdscr.addstr(start_y, 0, "RECENT FILLS", curses.A_BOLD)
    stdscr.addstr(start_y + 1, 0, "-" * (width - 1))
    
    header = f"{'TIME':<8} {'TRADER':<12} {'COIN':<8} {'SIDE':<6} {'SIZE':>10} {'PRICE':>12} {'PNL':>10}"
    stdscr.addstr(start_y + 2, 0, header)
    
    # Rows
    for i, f in enumerate(fills[:12]):
        y = start_y + 3 + i
        if y >= height - 2:
            break
        
        ts = f['time'] / 1000 if f['time'] > 1e12 else f['time']
        time_str = datetime.fromtimestamp(ts).strftime("%H:%M")
        wallet_short = f['wallet'][:8] + ".."
        coin = f['coin'][:8]
        side = "LONG" if f['side'] == 'B' else "SHORT"
        size = f"{f['sz']:.4f}"
        price = f"${f['px']:,.2f}"
        
        if f['closed_pnl'] > 0:
            pnl = f"+${f['closed_pnl']:.2f}"
            color = curses.color_pair(3)  # Green
        elif f['closed_pnl'] < 0:
            pnl = f"-${abs(f['closed_pnl']):.2f}"
            color = curses.color_pair(5)  # Red
        else:
            pnl = "-"
            color = curses.color_pair(4)  # Yellow
        
        line = f"{time_str:<8} {wallet_short:<12} {coin:<8} {side:<6} {size:>10} {price:>12} {pnl:>10}"
        stdscr.addstr(y, 0, line, color)

def draw_footer(stdscr, last_update):
    """Draw footer."""
    height, width = stdscr.getmaxyx()
    
    footer = f" Last update: {last_update} | Press 'q' to quit | 'r' to refresh "
    stdscr.addstr(height - 1, 0, footer.center(width), curses.color_pair(1))

def main(stdscr):
    """Main TUI loop."""
    # Setup colors
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)    # Header
    curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)   # Stats
    curses.init_pair(3, curses.COLOR_GREEN, -1)                   # Good
    curses.init_pair(4, curses.COLOR_YELLOW, -1)                  # Neutral
    curses.init_pair(5, curses.COLOR_RED, -1)                     # Bad
    
    # Setup
    curses.curs_set(0)  # Hide cursor
    stdscr.nodelay(True)  # Non-blocking input
    stdscr.timeout(5000)  # Refresh every 5 seconds
    
    last_update = "Never"
    
    while True:
        try:
            # Clear screen
            stdscr.clear()
            height, width = stdscr.getmaxyx()
            
            # Get data
            traders = get_traders()
            fills = get_recent_fills()
            stats = get_stats()
            
            # Draw
            draw_header(stdscr, stats)
            fills_start = draw_traders(stdscr, traders)
            draw_fills(stdscr, fills, fills_start)
            
            last_update = datetime.now().strftime("%H:%M:%S")
            draw_footer(stdscr, last_update)
            
            # Refresh
            stdscr.refresh()
            
            # Check for input
            key = stdscr.getch()
            if key == ord('q'):
                break
            elif key == ord('r'):
                continue  # Force refresh
            
        except curses.error:
            # Terminal too small
            pass
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    init_db()
    curses.wrapper(main)
