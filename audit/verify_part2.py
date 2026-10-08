#!/usr/bin/env python3
"""Audit part 2: pnl_pct convention audit, hidden home-runs, entry-price fidelity,
exit-timing (double-count) audit, and the exact replication variants."""
import sqlite3, psycopg2, datetime as dt, statistics, json, math
from collections import Counter, defaultdict

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

def q60(x):
    return int(x) // 60 * 60

TMAX = 130
TR = []
for (tid, tok, dire, entry, xit, pnlu, pnlp, amt, lev, xr, strat, ot, ct) in rows:
    ots = int(ot.replace(tzinfo=dt.timezone.utc).timestamp())
    cur = CAND.execute(
        "SELECT ts,open,high,low,close FROM candles_1m WHERE token=? AND ts>=? AND ts<=? ORDER BY ts",
        (tok.upper(), ots - 90, ots + TMAX * 60 + 90))
    pth = [dict(ts=r[0], o=r[1], h=r[2], l=r[3], c=r[4]) for r in cur.fetchall()]
    sgn = 1 if dire == 'LONG' else -1
    raw_move = (float(xit or 0) - float(entry)) / float(entry) * 100 if xit else None
    TR.append(dict(id=tid, tok=tok, dire=dire, sgn=sgn, entry=float(entry), xit=float(xit or 0),
                   pnlu=float(pnlu), pnlp=float(pnlp or 0), amt=float(amt), lev=float(lev or 0),
                   xr=str(xr), sig=str(strat).replace('Hermes-', ''), ot=ot, ct=ct, ots=ots,
                   hold=(ct - ot).total_seconds() / 60.0, pth=pth, raw=raw_move))
print(f"population n={len(TR)}")

# ---------------------------------------------------------------- A. convention audit
ok = unlev = other = 0
hidden_hr = []
for t in TR:
    if t['raw'] is None or t['raw'] == 0:
        continue
    k = abs(t['pnlp']) / abs(t['raw'])
    t['k'] = k
    if abs(k - t['lev']) < 0.15 * t['lev']:
        t['conv'] = 'leveraged'; ok += 1
    elif abs(k - 1) < 0.20:
        t['conv'] = 'unlevered'; unlev += 1
    else:
        t['conv'] = 'other'; other += 1
    # profit sign sanity
    t['pnl_sign_ok'] = (t['pnlp'] >= 0) == (t['raw'] * t['sgn'] >= 0)
    # hidden HR: leveraged-equivalent profit >= 10%
    lev_move = t['raw'] * t['sgn'] * t['lev']
    t['lev_move'] = lev_move
    if lev_move >= 10 and t['pnlp'] < 10:
        hidden_hr.append(t)
print(f"[A] pnl_pct convention: leveraged-ok={ok}  unlevered-style={unlev}  other={other}")
print(f"[A] trades where pnl_pct sign disagrees with price move: "
      f"{sum(1 for t in TR if t.get('pnl_sign_ok') is False)}")
print(f"[A] hidden HRs (raw move x leverage >= 10% but pnl_pct < 10): {len(hidden_hr)}")
for t in hidden_hr[:15]:
    print(f"     id={t['id']} {t['tok']} {t['dire']} raw={t['raw']:+.2f}% lev={t['lev']:.0f} "
          f"levmove={t['lev_move']:+.1f}% pnl_pct={t['pnlp']:+.2f} pnl_usdt={t['pnlu']:+.2f} conv={t['conv']}")

HR = {t['id'] for t in TR if t['pnlp'] >= 10}
HR2 = HR | {t['id'] for t in hidden_hr}
print(f"[A] HR set: stated={len(HR)}  corrected(incl hidden)={len(HR2)}")

# ---------------------------------------------------------------- checkpoint helpers
def ckpt(pth, ots, T):
    target = ots + T * 60
    for i, k in enumerate(pth):
        if k['ts'] + 60 >= target:
            return i
    return None

def move_at(t, T):
    i = ckpt(t['pth'], t['ots'], T)
    if i is None:
        return None, None
    return (t['pth'][i]['c'] - t['entry']) / t['entry'] * 100 * t['sgn'], i

def run(T, theta, pop, hrset, exit_mode='close', slip_bps=0.0, lag_bars=0):
    """exit_mode: 'close' = close of the checkpoint candle; 'open' = open of the NEXT
    candle. lag_bars: exit at the close of the checkpoint candle lag_bars bars later.
    slip_bps: slippage applied to the EXIT PRICE as a fraction of NOTIONAL."""
    trig = []; delta = 0.0; saved = 0.0; given = 0.0; kills = []
    for t in pop:
        if t['hold'] < T:
            continue
        mv, i = move_at(t, T)
        if mv is None:
            continue
        if mv < theta:
            j = i + lag_bars
            if exit_mode == 'open':
                j = i + 1 + lag_bars
            if j >= len(t['pth']):
                continue
            px = t['pth'][j]['o'] if exit_mode == 'open' else t['pth'][j]['c']
            sim_usd = (px - t['entry']) / t['entry'] * t['amt'] * t['sgn']
            sim_usd -= t['amt'] * slip_bps / 10000.0   # slippage on notional
            d = sim_usd - t['pnlu']
            delta += d
            if t['pnlu'] < 0: saved += d
            else: given += d
            if t['id'] in hrset: kills.append((t['id'], t['tok'], round(mv, 2), round(t['pnlp'], 1)))
            trig.append((t, mv, sim_usd, d))
    return trig, delta, saved, given, kills

mid = TR[len(TR) // 2]['ot']
h1 = [t for t in TR if t['ot'] < mid]; h2 = [t for t in TR if t['ot'] >= mid]
trig, delta, saved, given, kills = run(30, -0.5, TR, HR)
print(f"\n[B] replication: trig={len(trig)} delta=${delta:+.2f} saved=${saved:+.2f} givenup=${given:+.2f} HRkills={len(kills)}")
_, d1, *_ = run(30, -0.5, h1, HR); _, d2, *_ = run(30, -0.5, h2, HR)
print(f"    h1=${d1:+.2f} h2=${d2:+.2f}   (analyst: +1.85 / +1.39 / +0.46)")
_, d2c, *_ = run(30, -0.5, h2, HR2)
print(f"    HR kills under CORRECTED HR set: {len(run(30,-0.5,TR,HR2)[4])}")

# ---------------------------------------------------------------- 3a variants
print("\n[C] exit-price variants for T=30/theta=-0.5:")
variants = [('close', 0.0, 0), ('open', 0.0, 0), ('close', 0.0, 1), ('close', 0.0, 2),
            ('close', 0.0, 5), ('close', 5.0, 0), ('close', 10.0, 0), ('close', 5.0, 1)]
for mode, slip, lag in variants:
    tg, dl, sv, gn, kl = run(30, -0.5, TR, HR, exit_mode=mode, slip_bps=slip, lag_bars=lag)
    _, d1, *_ = run(30, -0.5, h1, HR, exit_mode=mode, slip_bps=slip, lag_bars=lag)
    _, d2, *_ = run(30, -0.5, h2, HR, exit_mode=mode, slip_bps=slip, lag_bars=lag)
    print(f"    exit={mode:<5} lag={lag}bar slip={slip:>4.1f}bp  trig={len(tg):>3}  delta=${dl:>+6.2f}  "
          f"h1=${d1:>+5.2f} h2=${d2:>+5.2f}  HRkills={len(kl)}")

# per-trade: how much does the min-31 open differ from min-30 close?
dd = [(t, t['pth'][i + 1]['o'] - t['pth'][i]['c']) for (t, mv, s, d) in trig
      for i in [ckpt(t['pth'], t['ots'], 30)] if i is not None and i + 1 < len(t['pth'])]
print(f"    min31-open minus min30-close (triggered): median={statistics.median(x[1]/x[0]['entry']*100*x[0]['sgn'] for x in dd):+.4f}%")

# ---------------------------------------------------------------- 3d entry fidelity
print("\n[D] entry-price fidelity (entry vs candle covering open_time):")
bad = []; miss_entry_candle = []
for t in TR:
    bucket = q60(t['ots'])
    c = [k for k in t['pth'] if k['ts'] == bucket]
    if not c:
        miss_entry_candle.append(t); continue
    c = c[0]
    dev_open = (t['entry'] - c['o']) / c['o'] * 100 * t['sgn']
    dev_close = (t['entry'] - c['c']) / c['c'] * 100 * t['sgn']
    t['dev_open'] = dev_open; t['dev_close'] = dev_close; t['dev_rng'] = (c['h'] - c['l']) / c['o'] * 100
    if abs(dev_close) > 1.0 or (t['dev_rng'] > 0 and abs(dev_close) > t['dev_rng']):
        bad.append(t)
print(f"    trades with NO candle covering the open minute: {len(miss_entry_candle)} "
      f"({[ (t['id'],t['tok']) for t in miss_entry_candle[:8] ]})")
devs = [abs(t['dev_close']) for t in TR if 'dev_close' in t]
devs.sort()
print(f"    |entry - open-minute close| %: median={devs[len(devs)//2]:.3f} p90={devs[int(len(devs)*0.9)]:.3f} "
      f"p99={devs[int(len(devs)*0.99)]:.3f} max={devs[-1]:.3f}")
print(f"    trades with >1% entry deviation from open-minute close: {len(bad)}")
for t in sorted(bad, key=lambda x: -abs(x['dev_close']))[:10]:
    print(f"      id={t['id']} {t['tok']} {t['dire']} entry={t['entry']:.6g} dev_close={t['dev_close']:+.2f}% "
          f"candle_range={t['dev_rng']:.2f}% hold={t['hold']:.0f}m conv={t.get('conv')}")
# among triggered
tbad = [(t, mv) for (t, mv, s, d) in trig if abs(t.get('dev_close', 0)) > 1.0]
print(f"    of the 179 triggered, how many have >1% entry deviation: {len(tbad)}")

# ---------------------------------------------------------------- 3e exit timing
print("\n[E] exit-timing / double-count audit:")
trig_sorted = sorted(trig, key=lambda x: x[0]['hold'])
print(f"    min hold among triggered = {trig_sorted[0][0]['hold']:.2f}m "
      f"(id={trig_sorted[0][0]['id']} {trig_sorted[0][0]['tok']})")
print(f"    triggered with hold<30: {sum(1 for x in trig if x[0]['hold']<30)}")
# implied actual exit price & when the market first traded there
def first_touch(t, price, upto_min):
    """first candle within hold where high/low spans the implied actual exit price"""
    end = t['ots'] + upto_min * 60
    for k in t['pth']:
        if k['ts'] > end: break
        if t['sgn'] > 0:
            if k['l'] <= price <= k['h']: return (k['ts'] + 60 - t['ots']) / 60.0
        else:
            if k['l'] <= price <= k['h']: return (k['ts'] + 60 - t['ots']) / 60.0
    return None
early = []
for (t, mv, s, d) in trig:
    imp = t['entry'] * (1 + t['sgn'] * t['pnlu'] / t['amt'])
    ft = first_touch(t, imp, t['hold'])
    t['first_touch'] = ft
    if ft is not None and ft < 30:
        early.append((t, ft, imp))
print(f"    triggered trades whose RECORDED exit price was first reachable BEFORE min30: {len(early)}")
for t, ft, imp in early[:12]:
    print(f"      id={t['id']} {t['tok']} {t['dire']} hold={t['hold']:.1f}m first_touch={ft:.1f}m "
          f"implied_exit={imp:.6g} xr={t['xr']} pnlu={t['pnlu']:+.2f}")
# trades actually exited by an exit rule that would have fired before min30
xr30 = Counter(t['xr'] for (t, mv, s, d) in trig if t['hold'] < 60)
print(f"    triggered & closed within 60m: exit reasons {xr30.most_common(8)}")

# ---------------------------------------------------------------- 3f baseline
print("\n[F] baseline T=120/theta=2.0 on pump-chain+:")
pcpop = [t for t in TR if t['sig'].startswith('pump-chain')]
tg, dl, sv, gn, kl = run(120, 2.0, pcpop, HR)
print(f"    n={len(pcpop)} trig={len(tg)} delta=${dl:+.2f} saved=${sv:+.2f} givenup=${gn:+.2f} HRkills={len(kl)}")
for t, mv, s, d in tg:
    if t['id'] in HR:
        mv120, i = move_at(t, 120)
        # best profit in the first 120 min
        best = max(((k['c'] - t['entry']) / t['entry'] * 100 * t['sgn'], (k['ts'] + 60 - t['ots']) / 60)
                   for k in t['pth'] if k['ts'] + 60 <= t['ots'] + 120 * 60)
        print(f"      HRkill id={t['id']} {t['tok']} {t['sig']} move@120={mv:+.2f}% actual={t['pnlp']:+.1f}% "
              f"pnl_usdt={t['pnlu']:+.2f} hold={t['hold']:.0f}m xr={t['xr']} best_first120={best[0]:+.2f}%@{best[1]:.0f}m")

json.dump({'n': len(TR)}, open('/root/.hermes/audit/_p2.json', 'w'))
CAND.close(); PG.close()
print("DONE part2")
