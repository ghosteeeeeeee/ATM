"""Pre-entry momentum: does 5m/15m move BEFORE entry predict arming (mfe>=0.40)?
Pre-ship check for a chop-entry quality filter. selfcheck: asserts row counts + no lookahead."""
import sqlite3, statistics, math, sys
from datetime import datetime, timezone
import psycopg2

C5 = '/root/.hermes/data/candles.db'

def load_trades(days):
    conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
    cur = conn.cursor()
    cur.execute("""SELECT id, token, direction, entry_price, open_time, pnl_usdt, mfe_pct, signal
        FROM trades WHERE status='closed' AND open_time > NOW() - INTERVAL %s
          AND mfe_pct IS NOT NULL AND entry_price IS NOT NULL""", (f'{days} days',))
    rows = cur.fetchall()
    conn.close()
    return rows

def feats(c5, token, ts, entry_price, direction):
    cur = c5.cursor()
    # last 5m close strictly before entry ts
    cur.execute("SELECT close FROM candles_5m WHERE token=? AND ts<? ORDER BY ts DESC LIMIT 1", (token, ts))
    r1 = cur.fetchone()
    cur.execute("SELECT close FROM candles_5m WHERE token=? AND ts<? ORDER BY ts DESC LIMIT 4", (token, ts))
    r4 = cur.fetchall()
    cur.execute("SELECT high, low FROM candles_5m WHERE token=? AND ts>=? AND ts<?", (token, ts-900, ts))
    rng = cur.fetchall()
    if not r1 or len(r4) < 4:
        return None
    c0 = r1[0]; c4 = r4[-1][0]
    ret5 = (entry_price / c0 - 1) * 100
    ret15 = (entry_price / c4 - 1) * 100
    rng_pct = ((max(h for h, _ in rng) - min(l for _, l in rng)) / c0 * 100) if rng else None
    sgn = 1 if direction == 'LONG' else -1
    return ret5 * sgn, ret15 * sgn, rng_pct

def bucketize(vals):
    s = sorted(vals)
    n = len(s)
    return s[n//3], s[2*n//3]

def main(days=14):
    trades = load_trades(days)
    c5 = sqlite3.connect(C5)
    rows = []
    miss = 0
    for tid, tok, d, ep, ot, pnl, mfe, sig in trades:
        ts = int(ot.replace(tzinfo=timezone.utc).timestamp()) if ot.tzinfo is None else int(ot.timestamp())
        ts = int(datetime(ot.year, ot.month, ot.day, ot.hour, ot.minute, ot.second).replace(tzinfo=timezone.utc).timestamp())
        f = feats(c5, tok, ts, float(ep), d)
        if f is None:
            miss += 1; continue
        a5, a15, rng = f
        rows.append(dict(id=tid, sig=sig, dir=d, pnl=float(pnl), armed=float(mfe) >= 0.40, a5=a5, a15=a15, rng=rng))
    print(f'{days}d trades={len(trades)} with_feats={len(rows)} missing={miss}')
    for name in ('a5', 'a15'):
        vals = [r[name] for r in rows if r[name] is not None]
        q1, q3 = bucketize(vals)
        print(f'\n== {name} (direction-signed % move in window before entry) cut {q1:.3f} / {q3:.3f}')
        bands = [('<q1', lambda v, a=q1: v < a), ('mid', lambda v, a=q1, b=q3: a <= v <= b), ('>q3', lambda v, b=q3: v > b)]
        for label, fn in bands:
            sub = [r for r in rows if r[name] is not None and fn(r[name])]
            if not sub: continue
            n = len(sub); w = sum(1 for r in sub if r['armed']); pnl = sum(r['pnl'] for r in sub)
            wins = sum(1 for r in sub if r['pnl'] > 0)
            print(f'  {label:5s} n={n:4d} arm={100*w/n:5.1f}% WR={100*wins/n:5.1f}% pnl={pnl:+.2f}')
        # extremes: strongly against us
        against = [r for r in rows if r[name] is not None and r[name] < -0.3]
        forus = [r for r in rows if r[name] is not None and r[name] > 0.3]
        for lbl, sub in (('move-against>0.3%', against), ('move-for-us>0.3%', forus)):
            if len(sub) < 5: 
                print(f'  {lbl}: n={len(sub)} (too small)'); continue
            n=len(sub); w=sum(1 for r in sub if r['armed']); wins=sum(1 for r in sub if r['pnl']>0)
            print(f'  {lbl}: n={n} arm={100*w/n:.1f}% WR={100*wins/n:.1f}% pnl={sum(r["pnl"] for r in sub):+.2f}')
    # two-proportion z: unarmed-vs-armed on a5 high vs rest
    hi = [r for r in rows if r['a5'] is not None and r['a5'] > 0.3]
    lo = [r for r in rows if r['a5'] is not None and r['a5'] <= 0.3]
    if hi and lo:
        p1 = sum(1 for r in hi if r['armed'])/len(hi); p0 = sum(1 for r in lo if r['armed'])/len(lo)
        p = (sum(1 for r in hi if r['armed'])+sum(1 for r in lo if r['armed']))/(len(hi)+len(lo))
        se = math.sqrt(p*(1-p)*(1/len(hi)+1/len(lo)))
        print(f'\nz(a5>0.3 arm vs rest): {((p1-p0)/se):.2f}  p1={p1:.3f} p0={p0:.3f}')
    return rows

def selfcheck():
    rows = main(7)
    assert len(rows) > 50, f'row count {len(rows)}'
    assert all('armed' in r for r in rows)
    print('SELF CHECK PASS')

if __name__ == '__main__':
    if '--selfcheck' in sys.argv:
        selfcheck()
    else:
        main(int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 14)
