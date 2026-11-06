#!/usr/bin/env python3
"""Own-conclusions: indicator parity (claim 1) + eyeball rows + event counts.
Independent: imports the spec's functions ONLY to test them against talib,
and separately re-implements the definitions from scratch."""
import sys, os, sqlite3, datetime
sys.path.insert(0, '/root/.hermes/scripts')
import numpy as np, talib
import backtest_atr60_momentum as B   # the spec's implementation under test

conn = sqlite3.connect('/root/.hermes/data/candles.db')
rows = conn.execute("SELECT ts, open, high, low, close FROM candles_1m WHERE token='BTC' ORDER BY ts ASC").fetchall()
conn.close()
ts = [r[0] for r in rows]; o = np.array([r[1] for r in rows]); h = np.array([r[2] for r in rows])
l = np.array([r[3] for r in rows]); c = np.array([r[4] for r in rows])
n = len(c)
print(f'BTC 1m bars: {n}  {datetime.datetime.fromtimestamp(ts[0], datetime.UTC)} -> {datetime.datetime.fromtimestamp(ts[-1], datetime.UTC)}')

# ---- my own independent ATR (RMA/Wilder, written from the definition) ----
def my_atr(h, l, c, p=14):
    tr = np.maximum.reduce([h - l, np.abs(h - np.roll(c, 1)), np.abs(l - np.roll(c, 1))])
    tr[0] = h[0] - l[0]
    out = np.full(len(c), np.nan)
    # Wilder RMA seeded with SMA of first p TRs (TR[1..p] in 1-based bar terms)
    seed = tr[1:p+1].mean()
    out[p] = seed
    a = seed
    for i in range(p + 1, len(tr)):
        a = (a * (p - 1) + tr[i]) / p
        out[i] = a
    return out

def my_rsi(c, p=14):
    d = np.diff(c, prepend=c[0]); d[0] = 0.0
    g = np.where(d > 0, d, 0.0); ls = np.where(d < 0, -d, 0.0)
    out = np.full(len(c), np.nan)
    ag, al = g[1:p+1].mean(), ls[1:p+1].mean()
    out[p] = 100.0 if al == 0 else 100 - 100/(1+ag/al)
    for i in range(p + 1, len(d)):
        ag = (ag*(p-1) + g[i]) / p
        al = (al*(p-1) + ls[i]) / p
        out[i] = 100.0 if al == 0 else 100 - 100/(1+ag/al)
    return out

atr_spec = np.array([np.nan if a is None else a for a in B.tv_atr(list(h), list(l), list(c), 14)])
atr_talib = talib.ATR(h, l, c, 14)
atr_mine  = my_atr(h, l, c)
rsi_spec  = np.array([np.nan if a is None else a for a in B.tv_rsi(list(c), 14)])
rsi_talib = talib.RSI(c, 14)
rsi_mine  = my_rsi(c)
macd_spec = np.array([np.nan if a is None else a for a in B.tv_macd_hist(list(c))])
macd_talib = talib.MACD(c, 12, 26, 9)[2]   # hist = macd - signal

m = ~(np.isnan(atr_spec) | np.isnan(atr_talib))
print(f'ATR  spec vs talib : max|diff| over {m.sum()} bars = {np.abs(atr_spec[m]-atr_talib[m]).max():.3e}   exact-zero count={int((atr_spec[m]==atr_talib[m]).sum())}/{m.sum()}')
m2 = ~(np.isnan(atr_mine) | np.isnan(atr_talib))
print(f'ATR  mine vs talib : max|diff| over {m2.sum()} bars = {np.abs(atr_mine[m2]-atr_talib[m2]).max():.3e}')
m3 = ~(np.isnan(rsi_spec) | np.isnan(rsi_talib))
print(f'RSI  spec vs talib : max|diff| = {np.abs(rsi_spec[m3]-rsi_talib[m3]).max():.3e}')
m4 = ~(np.isnan(rsi_mine) | np.isnan(rsi_talib))
print(f'RSI  mine vs talib : max|diff| = {np.abs(rsi_mine[m4]-rsi_talib[m4]).max():.3e}')
m5 = ~(np.isnan(macd_spec) | np.isnan(macd_talib))
d = np.abs(macd_spec[m5]-macd_talib[m5])
idx = np.where(m5)[0]
print(f'MACD spec vs talib : max|diff| full = {d.max():.3e} (at bar {idx[d.argmax()]}); after bar 100: {d[idx>100].max():.3e}; after bar 200: {d[idx>200].max():.3e}')
sgn = np.sign(macd_spec[m5]) != np.sign(macd_talib[m5])
bad = idx[sgn]
print(f'MACD sign disagreements: {len(bad)} at bars {bad[:20].tolist()}')

# ---- event counts (my own cross detector) ----
def my_events(a, thr, hy=0.9):
    ev, armed = [], True
    for i in range(1, len(a)):
        a0, a1 = a[i-1], a[i]
        if np.isnan(a0) or np.isnan(a1): continue
        if armed and a0 < thr <= a1:
            ev.append(i); armed = False
        if not armed and a1 < thr*hy:
            armed = True
    return ev
raw = my_events(atr_spec, 60, 1.0)
dec = my_events(atr_spec, 60, 0.9)
print(f'my raw crosses={len(raw)}  declustered={len(dec)}   (spec claims 201 -> 109 fresh 207/110)')

# ---- eyeball rows ----
def at(ts_str):
    t = int(datetime.datetime.strptime(ts_str, '%Y-%m-%d %H:%M').replace(tzinfo=datetime.UTC).timestamp())
    i = ts.index(t)
    return i
for tstr, cl in [('2026-11-06 04:55', 75802.0), ('2026-11-05 18:56', 76204.6), ('2026-10-29 20:54', 79101.5)]:
    i = at(tstr)
    sma = None
    print(f'  {tstr}: close={c[i]:.2f} (spec says {cl}) ATRspec={atr_spec[i]:.2f} ATRtalib={atr_talib[i]:.2f} RSI={rsi_spec[i]:.1f} MACDhist={macd_spec[i]:+.2f}')
# does 75802.0 appear anywhere?
print('close==75802.0 rows:', int((c==75802.0).sum()))
# ATR max in window
imax = np.nanargmax(atr_spec)
print(f'ATR max = {atr_spec[imax]:.2f} at {datetime.datetime.fromtimestamp(ts[imax], datetime.UTC)} (spec says 245.02 @ 2026-10-29 20:54)')
