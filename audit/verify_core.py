#!/usr/bin/env python3
"""Independent audit core — re-derive population, coverage, and the T=30/-0.5 backtest
WITHOUT reusing the analysis script. Own SQL, own bucketing, own code.

Auditor conventions:
  checkpoint time  = open_time + T minutes (elapsed seconds), exit price =
  the close of the FIRST 1m candle whose CLOSE time (ts+60) is >= checkpoint time.
  (Equivalent to the analyst's `first m>=T`, verified independently.)
"""
import sqlite3, psycopg2, statistics, json, datetime as dt

CAND = sqlite3.connect("file:/root/.hermes/data/candles.db?mode=ro", uri=True)
PG = psycopg2.connect(host="/var/run/postgresql", dbname="brain", user="postgres")
pc = PG.cursor()

pc.execute("""
  SELECT id, token, direction, entry_price, exit_price, pnl_usdt, pnl_pct, amount_usdt,
         leverage, exit_reason, strategy, open_time, close_time
  FROM trades
  WHERE status='closed' AND paper='f' AND pnl_usdt IS NOT NULL AND entry_price>0
    AND amount_usdt>0 AND open_time >= '2026-08-21'
  ORDER BY open_time""")
rows = pc.fetchall()
print(f"[T1] population (own SQL): {len(rows)}")

hr = [r for r in rows if r[6] is not None and float(r[6]) >= 10]
big = [r for r in rows if r[6] is not None and float(r[6]) >= 5]
print(f"[T1] HR (pnl_pct>=10): {len(hr)}   big(>=5): {len(big)}")

# --------------------------------------------------------------- candle fetch (own)
TMAX = 130
def path(token, ots):
    """candles for token in [ots-90, ots+TMAX*60+90]; return list of dicts."""
    cur = CAND.execute(
        "SELECT ts,open,high,low,close,is_closed FROM candles_1m WHERE token=? AND ts>=? AND ts<=? ORDER BY ts",
        (token.upper(), ots - 90, ots + TMAX * 60 + 90))
    return [dict(ts=r[0], o=r[1], h=r[2], l=r[3], c=r[4], ic=r[5]) for r in cur.fetchall()]

def checkpoint_close(pth, ots, T):
    """First candle whose close-time >= ots+T*60. Returns (candle, elapsed_min) or (None,None)."""
    target = ots + T * 60
    for k in pth:
        if k['ts'] + 60 >= target:
            return k, (k['ts'] + 60 - ots) / 60.0
    return None, None

TR = []
nocov = []
for (tid, tok, dire, entry, xit, pnlu, pnlp, amt, lev, xr, strat, ot, ct) in rows:
    ots = int(ot.replace(tzinfo=dt.timezone.utc).timestamp())
    pth = path(tok, ots)
    hold = (ct - ot).total_seconds() / 60.0
    TR.append(dict(id=tid, tok=tok, dire=dire, entry=float(entry), xit=float(xit or 0),
                   pnlu=float(pnlu), pnlp=float(pnlp or 0), amt=float(amt), lev=float(lev or 0),
                   xr=str(xr), sig=str(strat).replace('Hermes-', ''), ot=ot, ct=ct, ots=ots,
                   hold=hold, pth=pth))
    if not pth:
        nocov.append(tid)

print(f"[T1] any-candle coverage: {len(TR)-len(nocov)} covered / {len(nocov)} missing {nocov[:12]}")
print(f"[T1] HRs with any candles: {sum(1 for t in TR if t['pth'] and t['pnlp']>=10)}/{len(hr)}")

# T=30 checkpoint coverage (stricter than the analyst's "any candle" test)
cov30 = [t for t in TR if checkpoint_close(t['pth'], t['ots'], 30)[0] is not None]
print(f"[T1] T=30 checkpoint coverage: {len(cov30)} / {len(TR)}")

# --------------------------------------------------------------- simulation
def sim(T, theta, pop, exit_mode='close_T', slippage_bps=0.0, dry=False):
    """exit_mode: 'close_T' = close of checkpoint candle; 'open_next' = open of the
    following candle (1-bar delay). slippage_bps in basis points applied to exit."""
    trig = 0; delta = 0.0; saved = 0.0; given = 0.0; kills = []; rows_out = []
    actual = sum(t['pnlu'] for t in pop)
    for t in pop:
        if t['hold'] < T:
            continue
        ck, el = checkpoint_close(t['pth'], t['ots'], T)
        if ck is None:
            continue
        if exit_mode == 'close_T':
            px = ck['c']
        else:  # open of the next candle after the checkpoint candle
            idx = t['pth'].index(ck)
            px = t['pth'][idx + 1]['o'] if idx + 1 < len(t['pth']) else None
            if px is None:
                continue
        sgn = 1 if t['dire'] == 'LONG' else -1
        move = (px - t['entry']) / t['entry'] * 100 * sgn
        if move < theta:
            trig += 1
            px_eff = px * (1 - slippage_bps / 10000.0 * sgn)  # pay slippage against you
            sim_usd = (px_eff - t['entry']) / t['entry'] * t['amt'] * sgn
            d = sim_usd - t['pnlu']
            delta += d
            if t['pnlu'] < 0:
                saved += d
            else:
                given += d
            if t['pnlp'] >= 10:
                kills.append((t['id'], t['tok'], round(move, 2), round(t['pnlp'], 1)))
            rows_out.append((t, move, sim_usd, d))
    return dict(n=len(pop), trig=trig, delta=delta, saved=saved, given=given,
                kills=kills, actual=actual, rows=rows_out)

mid = TR[len(TR) // 2]['ot']
h1 = [t for t in TR if t['ot'] < mid]
h2 = [t for t in TR if t['ot'] >= mid]
print(f"[T2] split at {mid} h1={len(h1)} h2={len(h2)}")

r = sim(30, -0.5, TR)
r1 = sim(30, -0.5, h1)
r2 = sim(30, -0.5, h2)
print(f"[T2] REPLICATION  trig={r['trig']}  delta=${r['delta']:+.2f}  h1=${r1['delta']:+.2f}  h2=${r2['delta']:+.2f}")
print(f"[T2]  HR kills={len(r['kills'])} {r['kills']}  saved=${r['saved']:+.2f} givenup=${r['given']:+.2f}")
print(f"[T2]  actual book (unleveraged $) = ${r['actual']:+.2f}")

# died/recovered split
died = [x for x in r['rows'] if x[0]['pnlu'] < 0]
rec = [x for x in r['rows'] if x[0]['pnlu'] >= 0]
print(f"[T2]  triggered losers={len(died)} (saved ${sum(x[3] for x in died):+.2f})  "
      f"winners cut={len(rec)} (givenup ${sum(x[3] for x in rec):+.2f})")

# --------------------------------------------------------------- hold logic audit (3e)
holds = sorted(t['hold'] for t in r['rows'] and [x[0] for x in r['rows']])
print(f"[T3e] triggered trades: n={len(holds)} min hold={holds[0]:.2f}m  p5={holds[len(holds)//20]:.2f}  "
      f"median={statistics.median(holds):.1f}m  max={holds[-1]:.1f}m")
print(f"[T3e] triggered with hold<30: {sum(1 for h in holds if h < 30)}   "
      f"hold<30.01: {sum(1 for h in holds if h < 30.01)}   hold<31: {sum(1 for h in holds if h < 31)}")
# exit-reason mix of triggered
from collections import Counter
print("[T3e] triggered exit_reason mix:", Counter(x[0]['xr'] for x in r['rows']).most_common(10))

# --------------------------------------------------------------- hand checks (2)
print("\n[T2] hand checks — 8 random triggered trades:")
import random
random.seed(11)
for (t, move, sim_usd, d) in random.sample(r['rows'], 8):
    ck, el = checkpoint_close(t['pth'], t['ots'], 30)
    # recorded implied move
    imp_move = t['pnlu'] / t['amt'] * 100 * (1 if t['dire'] == 'LONG' else -1)
    print(f"  id={t['id']} {t['tok']:<6} {t['dire']:<5} entry={t['entry']:.6g} min30close={ck['c']:.6g} "
          f"(+{el:.1f}m) move={move:+.2f}% sim=${sim_usd:+.3f} | actual exit={t['xit']:.6g} "
          f"actual_move={imp_move:+.2f}% pnl_usdt={t['pnlu']:+.2f} pnl_pct={t['pnlp']:+.2f} lev={t['lev']:.0f} "
          f"hold={t['hold']:.1f}m xr={t['xr']} delta={d:+.3f}")

# --------------------------------------------------------------- stale-price fallback (3a-ish)
fallback = []
for t in TR:
    if t['hold'] < 30:
        continue
    ck, el = checkpoint_close(t['pth'], t['ots'], 30)
    if ck is None:
        fallback.append(t)
print(f"\n[T3e] trades with hold>=30 but NO candle closing >=30min after open: {len(fallback)}")
for t in fallback[:10]:
    last = t['pth'][-1]
    print(f"   id={t['id']} {t['tok']} last candle elapsed={(last['ts']+60-t['ots'])/60:.1f}m "
          f"n_candles={len(t['pth'])} hold={t['hold']:.1f}m xr={t['xr']}")

json.dump({'trig': r['trig'], 'delta': r['delta']}, open('/root/.hermes/audit/_core.json', 'w'))
CAND.close(); PG.close()
print("DONE core")
