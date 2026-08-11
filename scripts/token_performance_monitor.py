#!/usr/bin/env python3
"""
token_performance_monitor.py — Auto-re-blacklist tokens that start losing.

Runs periodically (hourly via systemd or pipeline). Checks closed trades
for each token. If any token has <35% WR with 5+ trades in 7d, adds it
to SHORT_BLACKLIST and LONG_BLACKLIST in hermes_constants.py.

Thresholds (conservative — we just unblacklisted 75 tokens):
- 5+ trades minimum (avoid noise from small samples)
- <35% WR (worse than random)
- 7d window (recent data only)
"""
import sys, os, re
sys.path.insert(0, os.path.dirname(__file__))

from paths import *
import psycopg2

# Thresholds
MIN_TRADES = 5
MAX_WR = 35.0  # re-blacklist if WR < 35%
WINDOW = "7 days"

def get_token_performance():
    """Query DB for per-token performance in last 7d."""
    conn = None
    try:
        conn = psycopg2.connect("dbname=brain user=postgres")
        cur = conn.cursor()
        cur.execute(f"""
            SELECT token,
                   COUNT(*) as trades,
                   ROUND(100.0*SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END)/COUNT(*),1) as wr,
                   ROUND(SUM(pnl_usdt),2) as pnl
            FROM trades
            WHERE status = 'closed'
              AND close_time > NOW() - INTERVAL '{WINDOW}'
            GROUP BY token
            HAVING COUNT(*) >= {MIN_TRADES}
            ORDER BY wr ASC
        """)
        return cur.fetchall()
    except Exception as e:
        print(f"Error querying DB: {e}")
        return []
    finally:
        if conn:
            conn.close()

def add_to_blacklist(token):
    """Add token to both blacklists in hermes_constants.py."""
    const_file = os.path.join(os.path.dirname(__file__), 'hermes_constants.py')
    with open(const_file, 'r') as f:
        content = f.read()

    # Check if already blacklisted
    if f"'{token}'" in content.split('SHORT_BLACKLIST')[1].split('}')[0]:
        print(f"  {token} already in SHORT_BLACKLIST — skipping")
        return False

    # Find the end of SHORT_BLACKLIST (before the closing brace)
    # Add token before the last entry's closing
    short_section = content[content.index('SHORT_BLACKLIST = {'):content.index('LONG_BLACKLIST = {')]

    # Find the last entry before the closing brace
    # Add after the MEGA line (last entry)
    old = "    'MEGA',\n}"
    new = f"    'MEGA',\n    # AUTO-BLACKLISTED {__import__('datetime').date.today()} — {MAX_WR}% WR threshold ({MIN_TRADES}+ trades, 7d)\n    '{token}',\n}}"
    content = content.replace(old, new, 1)

    # Also add to LONG_BLACKLIST
    long_start = content.index('LONG_BLACKLIST = {')
    long_section = content[long_start:]
    # Find the last entry in LONG_BLACKLIST
    long_entries_end = long_section.rindex('}')
    # Find the last token line before the closing brace
    lines = long_section[:long_entries_end].rstrip().split('\n')
    last_line = lines[-1].rstrip()

    # Add after the last line
    insert_line = f"    # AUTO-BLACKLISTED {__import__('datetime').date.today()} — {MAX_WR}% WR threshold\n    '{token}',"
    lines.append(insert_line)
    new_long = '\n'.join(lines) + '\n}'
    content = content[:long_start] + new_long

    with open(const_file, 'w') as f:
        f.write(content)

    print(f"  AUTO-BLACKLISTED {token}")
    return True

def main():
    print("Token Performance Monitor — checking 7d performance...")
    results = get_token_performance()

    if not results:
        print("  No tokens with 5+ trades in 7d window")
        return

    losers = [(token, trades, wr, pnl) for token, trades, wr, pnl in results if wr < MAX_WR]

    print(f"  {len(results)} tokens with 5+ trades, {len(losers)} below {MAX_WR}% WR")

    if not losers:
        print("  All tokens above threshold — no blacklisting needed")
        return

    print(f"\n  Losers to auto-blacklist:")
    blacklisted = 0
    for token, trades, wr, pnl in losers:
        print(f"    {token}: {trades}T, {wr}% WR, ${pnl}")
        if add_to_blacklist(token):
            blacklisted += 1

    if blacklisted > 0:
        print(f"\n  {blacklisted} tokens auto-blacklisted. Restart pipeline to apply.")
    else:
        print("\n  No new tokens blacklisted")

if __name__ == '__main__':
    main()
