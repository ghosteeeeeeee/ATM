#!/usr/bin/env python3
"""Regime-signal alignment analysis:
1. 30d trades: signal-level bleed
2. Fees check (net vs gross)
3. Continuum regime at trade open vs outcome (entry_regime_4h is NULL everywhere)
4. 4h scanner slope-regime historical accuracy on BTC
"""
import sqlite3, os, sys, bisect
sys.path.insert(0, '/root/.hermes/scripts')
from _secrets import BRAIN_DB_DICT
import psycopg2

CONT_DB = '/root/.hermes/data/continuum.db'
CANDLES_DB = '/root/.hermes/data/candles.db'

def continuum_hourly_bias():
    conn = sqlite3.connect(CONT_DB)
    rows = conn.execute("""
        SELECT ts, state_score, linreg_direction, linreg_alignment
        FROM continuum_states WHERE token='BTC' ORDER BY ts
    """).fetchall()
    conn.close()
    hourly = {}
    for ts, score, d, a in rows:
        h = ts // 3600 * 3600
        score = score or 50.0
        a = a or 0.0
        if score >= 55: tb = min(1.0,(score-55)/45.0)
        elif score <= 45: tb = max(-1.0,(score-45)/45.0)
        else: tb = 0.0
        dm = {'BULL':1.0,'LEAN_BULL':0.5,'NEUTRAL':0.0,'LEAN_BEAR':-0.5,'BEAR':-1.0}
        lb = dm.get(d,0.0)*a
        hourly[h] = (tb, lb, score)
    return hourly

def main():
    conn = psycopg2.connect(**BRAIN_DB_DICT)
    cur = conn.cursor()

    # 1. Signal-level bleed (30d)
    cur.execute("""
        SELECT signal, direction, COUNT(*), SUM(pnl_usdt), AVG(pnl_usdt),
               SUM(CASE WHEN pnl_usdt>0 THEN 1 ELSE 0 END)
        FROM trades
        WHERE status='closed' AND close_time >= now() - interval '30 days'
        GROUP BY signal, direction
        HAVING COUNT(*) >= 5
        ORDER BY SUM(pnl_usdt) ASC
        LIMIT 20
    """)
    print("=== TOP 20 BLEEDING SIGNALS (30d, >=5 trades) ===")
    print(f"{'signal':38s} {'dir':5s} {'n':>4s} {'pnl':>8s} {'avg':>7s} {'WR%':>5s}")
    for r in cur.fetchall():
        wr = 100.0*r[5]/r[2] if r[2] else 0
        print(f"{str(r[0])[:38]:38s} {str(r[1])[:5]:5s} {r[2]:4d} {r[3]:8.2f} {r[4]:7.3f} {wr:5.0f}")

    # fees are JSON text — parse fee_total in python
    cur.execute("""
        SELECT fees, pnl_usdt FROM trades
        WHERE status='closed' AND close_time >= now() - interval '30 days'
    """)
    import json as _json
    fee_sum = 0.0
    n_fees = 0
    match_net = 0    # pnl_usdt == net_pnl
    match_gross = 0  # pnl_usdt == net_pnl + fee_total
    n_matched = 0
    for fees_raw, pnl in cur.fetchall():
        if not fees_raw:
            continue
        try:
            fj = _json.loads(fees_raw) if isinstance(fees_raw, str) else fees_raw
            ft = float(fj.get('fee_total') or fj.get('total_fee') or 0)
            fee_sum += ft
            np_ = fj.get('net_pnl')
            if np_ is not None and pnl is not None:
                np_ = float(np_)
                n_matched += 1
                if abs(float(pnl) - np_) < 0.005:
                    match_net += 1
                if abs(float(pnl) - (np_ + ft)) < 0.005:
                    match_gross += 1
            n_fees += 1
        except Exception:
            pass
    cur.execute("""
        SELECT SUM(pnl_usdt) FROM trades
        WHERE status='closed' AND close_time >= now() - interval '30 days'
    """)
    pnl_total = float(cur.fetchone()[0] or 0)
    print(f"\n30d fees total (parsed JSON fee_total, n={n_fees}): {fee_sum:.2f}")
    print(f"30d SUM(pnl_usdt): {pnl_total:.2f}")
    print(f"Matched rows n={n_matched}: pnl_usdt==net_pnl: {match_net} ({100*match_net/max(n_matched,1):.0f}%) | ==net+fees(gross): {match_gross} ({100*match_gross/max(n_matched,1):.0f}%)")
    if match_net > match_gross:
        print("VERDICT: pnl_usdt is NET of fees (json net_pnl matches)")
    else:
        print("VERDICT: pnl_usdt is GROSS — fees NOT deducted from reported pnl")

    # 2. Continuum bias at trade OPEN vs outcome
    hourly = continuum_hourly_bias()
    hs = sorted(hourly.keys())
    cur.execute("""
        SELECT open_time, direction, signal, pnl_usdt, volatility_regime
        FROM trades
        WHERE status='closed' AND close_time >= now() - interval '30 days'
          AND open_time IS NOT NULL
    """)
    trades = cur.fetchall()
    conn.close()

    buckets = {}
    for ot, direction, signal, pnl, vreg in trades:
        # open_time may be timestamptz or str
        if hasattr(ot, 'timestamp'):
            ts = int(ot.timestamp())
        else:
            import datetime as dt
            ts = int(dt.datetime.fromisoformat(str(ot).replace('Z','+00:00')).timestamp())
        i = bisect.bisect_right(hs, ts) - 1
        if i < 0:
            continue
        tb, lb, score = hourly[hs[i]]
        # bucket by score zone
        zone = 'bull' if score >= 55 else ('bear' if score <= 45 else 'neutral')
        key = (zone, direction)
        b = buckets.setdefault(key, {'n':0,'pnl':0.0,'wins':0})
        b['n'] += 1
        b['pnl'] += float(pnl or 0)
        if (pnl or 0) > 0: b['wins'] += 1

    print("\n=== CONTINUUM BTC ZONE AT TRADE OPEN vs OUTCOME (30d) ===")
    print(f"{'zone':8s} {'dir':5s} {'n':>4s} {'pnl':>8s} {'avg':>7s} {'WR%':>5s}")
    for zone in ('bull','neutral','bear'):
        for direction in ('LONG','SHORT'):
            b = buckets.get((zone,direction))
            if not b: continue
            wr = 100.0*b['wins']/b['n'] if b['n'] else 0
            print(f"{zone:8s} {direction:5s} {b['n']:4d} {b['pnl']:8.2f} {b['pnl']/b['n']:7.3f} {wr:5.0f}")

    # 3. 4h scanner historical accuracy on BTC
    sys.path.insert(0, '/root/.hermes/scripts')
    import importlib.util
    spec = importlib.util.spec_from_file_location("scan4h", "/root/.hermes/scripts/4h_regime_scanner.py")
    # Don't import (it runs psycopg2 imports fine but let's just re-implement threshold)
    conn = sqlite3.connect(CANDLES_DB)
    rows = conn.execute("""
        SELECT ts, close FROM candles_4h WHERE token='BTC' AND is_closed=1 ORDER BY ts
    """).fetchall()
    conn.close()
    cts = [int(r[0]) for r in rows]
    closes = [float(r[1]) for r in rows]

    def slope_pct(window):
        n = len(window)
        x_mean = (n-1)/2; y_mean = sum(window)/n
        num = sum((i-x_mean)*(window[i]-y_mean) for i in range(n))
        den = sum((i-x_mean)**2 for i in range(n))
        if den == 0: return 0.0
        return (num/den)/y_mean*100

    def r2_of(window, sl):
        n = len(window); y_mean = sum(window)/n
        x_mean = (n-1)/2
        y_pred = [y_mean + sl*(i-x_mean) for i in range(n)]
        ss_res = sum((window[i]-y_pred[i])**2 for i in range(n))
        ss_tot = sum((w-y_mean)**2 for w in window)
        return max(0, 1-ss_res/ss_tot) if ss_tot else 0

    def regime_of(window):
        sl = slope_pct(window); r2 = r2_of(window, sl)
        if sl > 0.35 and r2 > 0.5: return 'LONG_BIAS'
        if sl < -0.35 and r2 > 0.5: return 'SHORT_BIAS'
        if abs(sl) < 0.20: return 'NEUTRAL'
        if sl > 0 and r2 > 0.4: return 'LONG_BIAS'
        if sl < 0 and r2 > 0.4: return 'SHORT_BIAS'
        return 'NEUTRAL'

    # Walk forward: at each closed candle i (need 6), regime from window [i-5..i],
    # forward return over next 1 and 2 candles
    stats = {}
    for i in range(5, len(closes)-2):
        window = closes[i-5:i+1]
        reg = regime_of(window)
        fwd1 = (closes[i+1]-closes[i])/closes[i]*100
        fwd2 = (closes[i+2]-closes[i])/closes[i]*100
        for label, fwd in (('fwd1',fwd1),('fwd2',fwd2)):
            b = stats.setdefault((reg,label), {'n':0,'hit':0,'pnl_dir':0.0})
            b['n'] += 1
            if reg == 'LONG_BIAS':
                if fwd > 0: b['hit'] += 1
                b['pnl_dir'] += fwd
            elif reg == 'SHORT_BIAS':
                if fwd < 0: b['hit'] += 1
                b['pnl_dir'] -= fwd
            else:
                if abs(fwd) < 0.05: b['hit'] += 1

    print("\n=== 4H SCANNER REGIME ACCURACY ON BTC (full candles.db history) ===")
    print(f"{'regime':12s} {'horizon':7s} {'n':>6s} {'hit%':>6s} {'dirPnL%':>8s}")
    for reg in ('LONG_BIAS','SHORT_BIAS','NEUTRAL'):
        for label in ('fwd1','fwd2'):
            b = stats.get((reg,label))
            if not b: continue
            print(f"{reg:12s} {label:7s} {b['n']:6d} {100.0*b['hit']/b['n']:6.1f} {b['pnl_dir']:8.2f}")

if __name__ == '__main__':
    main()
