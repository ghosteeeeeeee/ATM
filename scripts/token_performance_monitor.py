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

# R:R-blind-spot shadow leg (brain_auditor #243, 2026-11-09) — REPORT-ONLY.
# The WR leg (<35%) structurally cannot see R:R bleeds: HYPE was the book's
# biggest single-token bleed (jup mirror LONG 48T 59%WR net -$0.82, losses
# riding 2x wins) yet passed every WR check until T blacklisted manually
# 2026-11-03. Trailing-7d net-leg would have flagged it the same day
# (n=51, WR 54.9%, net -$0.54). Validation: 21 daily snapshots -> 2 flags
# (BTC both, forward-7d ~flat) = too noisy for auto-blacklist as-is.
# PROMOTION CRITERIA (CEO sign-off required; auto-blacklist = trading behavior):
#   during a >=7d collect window, a non-major flagged token (a) n>=10 at flag,
#   (b) forward-7d net <= -$0.75, (c) not already blacklisted at flag time,
#   (d) majors (BTC/ETH/SOL) excluded -> then wire into add_to_blacklist path.
RR_MIN_TRADES = 5
RR_MAX_NET = -0.50

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

def report_rr_blindspot():
    """Shadow-only: tokens passing the WR leg but bleeding on net PnL.
    Never blacklists — prints for audit collection (see promotion criteria
    in the RR_MAX_NET comment block above)."""
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
            HAVING COUNT(*) >= {RR_MIN_TRADES}
               AND ROUND(100.0*SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END)/COUNT(*),1) >= {MAX_WR}
               AND SUM(pnl_usdt) <= {RR_MAX_NET}
            ORDER BY SUM(pnl_usdt) ASC
        """)
        flags = cur.fetchall()
    except Exception as e:
        print(f"Error querying DB (rr-blindspot): {e}")
        return
    finally:
        if conn:
            conn.close()

    if flags:
        print(f"  RR-BLINDSPOT (shadow, NO action): {len(flags)} token(s) pass WR leg but net <= {RR_MAX_NET}")
        for token, trades, wr, pnl in flags:
            print(f"    {token}: {trades}T, {wr}% WR, ${pnl} net (R:R bleed — monitor)")
    else:
        print("  RR-BLINDSPOT (shadow): none")


def main():
    print("Token Performance Monitor — checking 7d performance...")
    results = get_token_performance()

    report_rr_blindspot()

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
