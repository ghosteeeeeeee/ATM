#!/usr/bin/env python3
"""
token_performance_monitor.py — Auto-re-blacklist tokens that start losing.

Runs hourly via systemd timer. Checks closed trades for each token.
If any token has <35% WR with 5+ trades in 7d, adds it to both blacklists.

Thresholds (conservative):
- 5+ trades minimum (avoid noise from small samples)
- <35% WR (worse than random)
- 7d window (recent data only)
"""
import sys, os, datetime
sys.path.insert(0, os.path.dirname(__file__))

from paths import *
import psycopg2

MIN_TRADES = 5
MAX_WR = 35.0
WINDOW = "7 days"

def get_token_performance():
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
    const_file = os.path.join(os.path.dirname(__file__), 'hermes_constants.py')
    with open(const_file, 'r') as f:
        content = f.read()

    today = datetime.date.today().isoformat()
    comment = f"    # AUTO-BLACKLISTED {today} — {MAX_WR}% WR threshold ({MIN_TRADES}+ trades, 7d)\n    '{token}',\n"

    # Add to SHORT_BLACKLIST
    short_end = content.index('LONG_BLACKLIST = {')
    short_section = content[content.index('SHORT_BLACKLIST = {'):short_end]
    if f"'{token}'" in short_section:
        print(f"  {token} already in SHORT_BLACKLIST — skipping")
        return False

    # Find last entry before closing brace in SHORT_BLACKLIST
    content = content.replace(
        "    'MEGA',\n}",
        f"    'MEGA',\n{comment}}}",
        1
    )

    # Add to LONG_BLACKLIST
    long_start = content.index('LONG_BLACKLIST = {')
    long_section = content[long_start:]
    if f"'{token}'" in long_section.split('}')[0]:
        print(f"  {token} already in LONG_BLACKLIST — skipping")
        return False

    # Find last entry before closing brace in LONG_BLACKLIST
    content = content.replace(
        "    'MEGA',\n}",
        f"    'MEGA',\n{comment}}}",
        1
    )

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
