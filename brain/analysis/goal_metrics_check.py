#!/usr/bin/env python3
"""goal_metrics_check.py — the goal-704ed65e verifier. Run every goal round.

RESTRUCTURED metrics 2026-11-22 (CEO verdict 20261122T194418Z + T approval 2026-11-22):
expectancy set replaces the WR target — "we want net positive". WR is diagnostic only.
Target source: CEO edge-diagnosis verdict 20261122T194418Z + registry goal-metric-restructure.
All numbers from PG (source of truth); fees = synthetic 0.09% RT of amount_usdt (BUG-073/099).
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

    # 5. EXPECTANCY SET (RESTRUCTURED — CEO verdict 20261122T194418Z, T approval 2026-11-22:
    #    the old "fleet WR >=55%" target optimized the losing population (payoff<1.0 group =
    #    23 signals -$9.21 at WR 54.7%); WR is now DIAGNOSTIC ONLY, never a target.)
    # 5a. net $/trade fee-adj 7d (baseline -$0.0124; target >0 sustained 7d)
    cur.execute("""SELECT COUNT(*), COALESCE(SUM(pnl_usdt - amount_usdt*%s),0)
        FROM trades WHERE status='closed' AND close_time > NOW()-INTERVAL '7 days'""", (FEE,))
    n7, s7 = cur.fetchone()
    chk(n7 > 0 and float(s7) / n7 > 0,
        f"net $/trade 7d: {float(s7)/n7 if n7 else 0:+.4f} over {n7}T (target >0 sustained; baseline -0.0124)")
    # 5b. fleet payoff ratio 14d (baseline ~1.05; target >=1.2)
    cur.execute("""SELECT COALESCE(AVG(pnl_usdt - amount_usdt*%s) FILTER (WHERE pnl_usdt > 0),0),
        COALESCE(AVG(pnl_usdt - amount_usdt*%s) FILTER (WHERE pnl_usdt < 0),0), COUNT(*)
        FROM trades WHERE status='closed' AND close_time > NOW()-INTERVAL '14 days'""", (FEE, FEE))
    aw, al, np_ = cur.fetchone()
    payoff = (float(aw) / abs(float(al))) if float(al) else 0.0
    chk(np_ >= 30 and payoff >= 1.2,
        f"fleet payoff 14d: {payoff:.2f} (aw {float(aw):+.3f} / al {float(al):+.3f}) over {np_}T (target >=1.2; baseline ~1.05)")
    # 5c. cost % notional RT 14d = synthetic fee + atr_sl stop-overshoot (exit_slippage_pct)
    #     (baseline ~0.22% = 0.10 fee + 0.12 overshoot; target <=0.15%)
    cur.execute("""SELECT COALESCE(SUM(amount_usdt),0),
        COALESCE(SUM(amount_usdt*0.0009),0),
        COALESCE(SUM(CASE WHEN exit_reason='atr_sl_hit' THEN amount_usdt*COALESCE(exit_slippage_pct,0) ELSE 0 END),0)
        FROM trades WHERE status='closed' AND close_time > NOW()-INTERVAL '14 days'""", ())
    tot_not, fee_sum, over_sum = cur.fetchone()
    cost_pct = (float(fee_sum) + float(over_sum)) / float(tot_not) * 100 if float(tot_not) else 99.0
    chk(cost_pct <= 0.15,
        f"cost % notional RT 14d: {cost_pct:.3f}% (fee {float(fee_sum)/float(tot_not)*100 if float(tot_not) else 0:.3f}% + overshoot {float(over_sum)/float(tot_not)*100 if float(tot_not) else 0:.3f}%) (target <=0.15%; baseline ~0.22%)")
    # WR = DIAGNOSTIC ONLY (no target) — reported, never gated
    cur.execute("""SELECT COUNT(*), 100.0*SUM(CASE WHEN pnl_usdt>0 THEN 1 ELSE 0 END)/COUNT(*)
        FROM trades WHERE status='closed' AND close_time > NOW()-INTERVAL '14 days'""")
    wn, w = cur.fetchone()
    out.append(f"info  WR 14d (diagnostic, NO target): {float(w):.1f}% over {wn}T")

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
