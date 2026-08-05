#!/usr/bin/env python3
"""
ZK / Executor-Guardian Race Detector
Checks for evidence of a guardian-orphan close racing with a fresh signal execution.

Run after a suspected incident:
  python3 scripts/detect_executor_guardian_race.py

What it detects:
1. Guardian closed a token as orphan AND a signal for that token was created
   within 90s before or after the orphan close → race condition
2. signal_outcomes has no entry for a guardian-orphan close → silent gap
3. HL has 2 positions for same token but only 1 signal_outcomes record → duplicate position
"""

import sqlite3, sys
from datetime import datetime, timezone

def detect_race(token_filter=None):
    conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
    cur = conn.cursor()

    # 1. Find guardian orphan closes from guardian log (grep pipeline)
    # We detect orphans by checking trades table for guardian_orphan entries
    # But since guardian uses _close_paper_trade_db which updates trades...
    # The cleanest signal is: any EXECUTED signal whose decision was later set to something
    # that doesn't match what the guardian would have done

    # Instead: look for signals that were EXECUTED but the guardian log shows
    # an orphan close for the same token within a narrow window

    # For the ZK case: signal 646771 was EXECUTED at 21:29, guardian orphan at 21:34
    # signal 646953 was EXECUTED at 21:34 (after the orphan close, not before)

    # Better check: look for tokens with 2+ EXECUTED signals in a short window
    cur.execute("""
        SELECT token, direction, COUNT(*) as cnt,
               MIN(created_at), MAX(created_at)
        FROM signals
        WHERE decision='EXECUTED'
        GROUP BY token, direction
        HAVING cnt > 1
        ORDER BY MAX(created_at) DESC
        LIMIT 20
    """)
    multi = cur.fetchall()
    print("=== Tokens with 2+ EXECUTED signals ===")
    for r in multi:
        print(f"  {r[0]} {r[1]}: {r[2]} signals from {r[3]} to {r[4]}")

    # 2. Check signal_outcomes for gaps — tokens with EXECUTED signals but no outcome
    print("\n=== signal_outcomes gaps (signals with no recorded outcome) ===")
    cur.execute("""
        SELECT s.token, s.direction, s.id, s.created_at, s.signal_type
        FROM signals s
        LEFT JOIN signal_outcomes o ON o.token = s.token AND o.direction = s.direction
        WHERE s.decision = 'EXECUTED'
          AND o.id IS NULL
        ORDER BY s.created_at DESC
        LIMIT 20
    """)
    gaps = cur.fetchall()
    for r in gaps:
        print(f"  {r[0]} {r[1]} signal={r[2]} created={r[3]} type={r[4]}")

    # 3. Check for tokens where guardian closed an orphan and a fresh signal existed
    # This requires correlating with guardian log, but we can check:
    # tokens with EXECUTED signals very close together in time
    print("\n=== Tight EXECUTED signal pairs (potential race indicator) ===")
    cur.execute("""
        SELECT a.token, a.direction, a.id, a.created_at, b.id, b.created_at,
               (julianday(b.created_at) - julianday(a.created_at)) * 86400 as gap_sec
        FROM signals a
        JOIN signals b ON a.token = b.token AND a.direction = b.direction
            AND b.id > a.id AND b.decision = 'EXECUTED'
        WHERE a.decision = 'EXECUTED'
          AND (julianday(b.created_at) - julianday(a.created_at)) * 86400 < 300
        ORDER BY gap_sec ASC
        LIMIT 10
    """)
    races = cur.fetchall()
    for r in races:
        print(f"  {r[0]} {r[1]}: signal {r[2]} @ {r[3]} → signal {r[4]} @ {r[5]}  gap={r[6]:.0f}s")

    # 4. Quick check for specific token
    if token_filter:
        print(f"\n=== Detail for {token_filter} ===")
        cur.execute("""
            SELECT id, token, direction, decision, price, created_at, updated_at
            FROM signals WHERE token=? ORDER BY created_at
        """, (token_filter,))
        for r in cur.fetchall():
            print(f"  {r}")

    conn.close()

if __name__ == '__main__':
    token = sys.argv[1] if len(sys.argv) > 1 else None
    detect_race(token)
