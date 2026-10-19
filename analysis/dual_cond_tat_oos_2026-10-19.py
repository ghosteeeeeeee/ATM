#!/usr/bin/env python3
"""Dual-condition TAT candle OOS for bb-bounce-v2 LONG (brain_auditor 2026-10-19).

Last-run creative (Oct 18): single-condition T=55 fails TAT-eligibility meta-rule
(median winner hold ~190m >> 55). Dual-condition candidate: fire at age>=T only if
peak-high MFE(unlev %) < 0.20 AND live close pnl(unlev %) < -0.20.

Bar (pre-registered): net benefit > 0 AND false-kill <= 20% of cohort winners AND n>=15 fires.
Units: cf$ = amount_usdt * lp/100; benefit = cf - actual pnl_usdt (+ = helps).
"""
import sqlite3
from datetime import datetime, timezone
import psycopg2

T = 55
MFE_MAX = 0.20   # peak since entry must stay below this
LIVE_MAX = -0.20 # live pnl at T must be below this (underwater filter)

conn = psycopg2.connect(host="/var/run/postgresql", database="brain", user="postgres")
cur = conn.cursor()
cur.execute("""
    SELECT id, token, signal, direction, entry_price, pnl_usdt, pnl_pct, amount_usdt, leverage,
           open_time, close_time, exit_reason
    FROM trades
    WHERE status='closed' AND close_time > NOW() - INTERVAL '30 days'
      AND signal = 'bb-bounce-v2-long+' AND direction='LONG'
      AND amount_usdt IS NOT NULL AND leverage IS NOT NULL AND leverage > 0
""")
rows = cur.fetchall()
conn.close()
print(f"bb-bounce-v2-long+ 30d closed: {len(rows)}")

cdb = sqlite3.connect("file:/root/.hermes/data/candles.db?mode=ro", uri=True)

def to_dt(x):
    if isinstance(x, str):
        x = datetime.fromisoformat(x.replace("Z", "+00:00"))
    if x.tzinfo is None:
        x = x.replace(tzinfo=timezone.utc)
    return x

fired = fk = miss = early = 0
net = save = cost = 0.0
details = []
for (tid, token, signal, direc, entry, pnl_usdt, pnl_pct, amt, lev, ot, ct, xr) in rows:
    entry = float(entry)
    amt = float(amt)
    lev = float(lev)
    end_u = float(pnl_pct) / lev
    ot_u = to_dt(ot).timestamp()
    ct_u = to_dt(ct).timestamp()
    hm = (ct_u - ot_u) / 60.0
    if hm < T:
        early += 1
        continue
    # MFE from 1m highs since entry to T
    t_end = ot_u + T * 60
    hi = cdb.execute(
        "SELECT MAX(high) FROM candles_1m WHERE token=? AND ts>=? AND ts<=?",
        (token, ot_u, t_end),
    ).fetchone()[0]
    close_row = cdb.execute(
        "SELECT close FROM candles_1m WHERE token=? AND ts<=? ORDER BY ts DESC LIMIT 1",
        (token, t_end),
    ).fetchone()
    if hi is None or close_row is None:
        miss += 1
        continue
    mfe_u = (float(hi) - entry) / entry * 100.0
    lp = (float(close_row[0]) - entry) / entry * 100.0
    if mfe_u < MFE_MAX and lp < LIVE_MAX:
        fired += 1
        cf = amt * (lp / 100.0)
        benefit = cf - float(pnl_usdt)
        net += benefit
        if benefit > 0:
            save += benefit
        else:
            cost += benefit
        is_win = end_u > 0
        if is_win:
            fk += 1
        details.append((tid, token, round(lp, 3), round(mfe_u, 3), round(float(pnl_usdt), 3),
                        round(benefit, 3), "FK" if is_win else "save", round(hm, 0), xr))

print(f"early(<{T}m)={early} miss={miss} fired={fired}")
print(f"net=${net:+.2f} save=${save:+.2f} cost=${cost:+.2f}")
winners = sum(1 for r in rows if float(r[6])/float(r[8]) > 0)
print(f"cohort winners={winners} false_kills={fk} fk_rate={100*fk/winners if winners else 0:.1f}%")
print("\nfires:")
for d in details:
    print(" ", d)
