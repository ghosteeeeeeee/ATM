#!/usr/bin/env python3
"""goal_metrics_check.py — the goal-704ed65e verifier. Run every goal round.

Prints the 5 pinned CEO metrics vs targets + net-of-fees book windows.
Target source: registry entry harvest-ship-2026-11-04 + CEO verdict 20261104.
All numbers from PG (source of truth); fees = 0.09% RT of amount_usdt (BUG-073).
"""
import sys
import psycopg2

FEE = 0.0009

def main():
    c = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
    cur = c.cursor()
    out = []
    ok = True

    def chk(cond, label):
        nonlocal ok
        ok = ok and bool(cond)
        out.append(f"{'PASS' if cond else 'FAIL'}  {label}")

    # 1. jup share of rolling-50 closed (target < 35%)
    cur.execute("""SELECT COUNT(*) FILTER (WHERE signal LIKE '%jup_yolo%'), COUNT(*)
        FROM (SELECT * FROM trades WHERE status='closed' ORDER BY close_time DESC LIMIT 50) t""")
    j, n = cur.fetchone()
    chk(j / n < 0.35 if n else False,
        f"jup share rolling-50: {j}/{n} = {100*j/n:.0f}% (target <35%)")

    # 2. HML 7d (target <15 hits AND net > -$2.00)
    cur.execute("""SELECT COUNT(*), COALESCE(SUM(pnl_usdt),0), COALESCE(SUM(pnl_usdt - amount_usdt*%s),0)
        FROM trades WHERE status='closed' AND exit_reason='hard_max_loss'
        AND close_time > NOW()-INTERVAL '7 days'""", (FEE,))
    hn, hp, hnet = cur.fetchone()
    chk(hn < 15, f"HML 7d count: {hn} (target <15)")
    chk(float(hnet) > -2.00, f"HML 7d net-of-fees: {float(hnet):+.2f} (target >-2.00)")

    # 3. net daily (24h and 72h, net-of-fees; target >=0 sustained 72h)
    for hrs in (24, 72):
        cur.execute(f"""SELECT COALESCE(SUM(pnl_usdt - amount_usdt*{FEE}),0), COUNT(*)
            FROM trades WHERE status='closed' AND close_time > NOW()-INTERVAL '{hrs} hours'""")
        s, n = cur.fetchone()
        if hrs == 24:
            chk(float(s) >= 0, f"net 24h (fees in): {float(s):+.2f} over {n}T (target >=0)")
        else:
            chk(float(s) >= 0, f"net 72h (fees in): {float(s):+.2f} over {n}T (target >=0 = sustained)")

    # 4. direction ratio of fills last 48h LONG:SHORT (target <2:1)
    cur.execute("""SELECT COUNT(*) FILTER (WHERE direction='LONG'), COUNT(*) FILTER (WHERE direction='SHORT')
        FROM trades WHERE status='closed' AND close_time > NOW()-INTERVAL '48 hours'""")
    nl, ns = cur.fetchone()
    ratio = (nl / ns) if ns else float('inf')
    chk(ratio < 2.0, f"fill ratio 48h LONG:SHORT = {nl}:{ns} = {ratio:.1f}:1 (target <2:1)")

    # 5. non-jup fleet WR 14d (target >=55% at n>=10)
    cur.execute("""SELECT COUNT(*), 100.0*SUM(CASE WHEN pnl_usdt>0 THEN 1 ELSE 0 END)/COUNT(*)
        FROM trades WHERE status='closed' AND close_time > NOW()-INTERVAL '14 days'
        AND signal NOT LIKE '%jup_yolo%'""")
    fn, fwr = cur.fetchone()
    chk(fn >= 10 and float(fwr) >= 55.0,
        f"non-jup fleet WR 14d: {float(fwr):.1f}% over {fn}T (target >=55% at n>=10)")

    # book context (informational, not gated)
    for w in ('24 hours', '7 days', '30 days'):
        cur.execute(f"""SELECT COUNT(*), ROUND(SUM(pnl_usdt)::numeric,2),
            ROUND(SUM(pnl_usdt - amount_usdt*{FEE})::numeric,2)
            FROM trades WHERE status='closed' AND close_time > NOW()-INTERVAL '{w}'""")
        b = cur.fetchone()
        out.append(f"info  book {w}: {b[0]}T gross {b[1]} net {b[2]}")
    cur.close(); c.close()

    print("GOAL-704ed65e METRICS", "-" * 50)
    for line in out:
        print(" ", line)
    print("RESULT:", "ALL PASS" if ok else "NOT YET (goal active)")
    return 0 if ok else 1

if __name__ == '__main__':
    sys.exit(main())
