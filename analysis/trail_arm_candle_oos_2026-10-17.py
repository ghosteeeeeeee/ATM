#!/usr/bin/env python3
"""Candle-level as-coded OOS for trail-arm-timeout — USDT units (brain_auditor 2026-10-17 11:55Z).

As-coded condition (position_manager.py:3589): still open at age>=T AND
live_pnl (unleveraged price %) < 0.40 => close now.

Units: pnl_pct in PG is LEVERAGED % (price_move * lev). live_pnl is unleveraged.
Counterfactual $ if fired at T: amount_usdt * (lp/100) * lev.
Benefit of firing = actual pnl_usdt - cf_usdt.
"""
import sqlite3
from datetime import datetime, timezone
import psycopg2

ARM = 0.40  # % unleveraged
COHORTS = [
    ("pump-chain-LIVE45", "pump-chain", 45),
    ("bb-squeeze-LIVE60", "bb-squeeze", 60),
    ("bb-bounce-SHD55",   "bb-bounce",  55),
    ("ai-trader-SHD55",   "ai-trader",  55),
]

conn = psycopg2.connect(host="/var/run/postgresql", database="brain", user="postgres")
cur = conn.cursor()
cur.execute("""
    SELECT id, token, signal, direction, entry_price, pnl_usdt, pnl_pct, amount_usdt, leverage,
           open_time, close_time, exit_reason
    FROM trades
    WHERE status='closed' AND close_time > NOW() - INTERVAL '30 days' AND direction='LONG'
      AND amount_usdt IS NOT NULL AND leverage IS NOT NULL AND leverage > 0
""")
rows = cur.fetchall()
conn.close()

cdb = sqlite3.connect("file:/root/.hermes/data/candles.db?mode=ro", uri=True)

def to_dt(x):
    if isinstance(x, str):
        x = datetime.fromisoformat(x.replace("Z", "+00:00"))
    if x.tzinfo is None:
        x = x.replace(tzinfo=timezone.utc)
    return x

def live_pnl_at(token, entry, t_min, open_time):
    target = int(to_dt(open_time).timestamp()) + t_min * 60
    r = cdb.execute(
        "SELECT close FROM candles_1m WHERE token=? AND ts<=? ORDER BY ts DESC LIMIT 1",
        (token, target),
    ).fetchone()
    if r is None:
        return None
    entry = float(entry)
    return (r[0] - entry) / entry * 100.0

print(f"30d LONG closed: {len(rows)}\n")
summary = {}
for name, sig, T in COHORTS:
    cohort = [r for r in rows if sig in (r[2] or "").lower()]
    fired = fk = miss = early = 0
    net_usdt = save_usdt = cost_usdt = 0.0
    winners_n = 0
    details = []
    for (tid, token, signal, direc, entry, pnl_usdt, pnl_pct, amt, lev, ot, ct, xr) in cohort:
        end_u = float(pnl_pct) / float(lev)  # unleveraged end %
        if end_u > 0:
            winners_n += 1
        hm = (to_dt(ct) - to_dt(ot)).total_seconds() / 60.0
        if hm < T:
            early += 1
            continue
        lp = live_pnl_at(token, entry, T, ot)
        if lp is None:
            miss += 1
            continue
        if lp < ARM:
            fired += 1
            end_u = float(pnl_pct) / float(lev)
            # pnl_usdt = amount_usdt * end_u/100 (amount is NOTIONAL; lev is margin metadata)
            cf = float(amt) * (lp / 100.0)  # $ if closed at T
            benefit = cf - float(pnl_usdt)  # + = firing helps
            net_usdt += benefit
            if end_u > 0:
                fk += 1
                cost_usdt += benefit
                kind = "FK"
            else:
                save_usdt += benefit
                kind = "SAVE"
            details.append((token, f"T{lp:+.2f}%", f"end_u{end_u:+.2f}%", f"usdt{float(pnl_usdt):+.2f}",
                            f"cf{cf:+.2f}", f"ben{benefit:+.2f}", kind, xr))
    alive = len(cohort) - early
    print(f"=== {name} (T={T}m, arm<{ARM}% unleveraged) ===")
    print(f"  cohort={len(cohort)} closed_before_T={early} alive_at_T={alive} no_candle={miss}")
    print(f"  FIRED={fk+fired-fk} (winners_FK={fk}, losers_saved={fired-fk})")
    print(f"  NET if fired = ${net_usdt:+.2f}/30d | saves ${save_usdt:+.2f} | costs ${cost_usdt:+.2f}")
    if alive - miss > 0:
        print(f"  fire_rate_of_alive={100.0*fired/(alive-miss):.1f}%")
    if fired:
        print(f"  fk_rate_of_fires={100.0*fk/fired:.1f}%")
    if winners_n:
        print(f"  fk_pct_of_cohort_winners={100.0*fk/winners_n:.1f}% ({fk}/{winners_n})")
    # sort by |benefit|
    details.sort(key=lambda d: abs(float(d[5][3:])), reverse=True)
    for d in details[:10]:
        print(f"    {d}")
    if len(details) > 10:
        print(f"    ... +{len(details)-10} more")
    print()
    summary[name] = dict(cohort=len(cohort), fired=fired, fk=fk,
                         net_usdt=round(net_usdt, 2), save=round(save_usdt, 2),
                         cost=round(cost_usdt, 2), fk_of_winners=round(100.0*fk/max(winners_n,1), 1))
print("SUMMARY:", summary)
