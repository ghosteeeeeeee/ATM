#!/usr/bin/env python3
"""coin_analysis — multi-coin spin-off of the full-analysis skill (CEO
2026-11-10: "start making a spin off of the full-analysis for more coins,
start with the jup yolo listed coins").

Runs the SAME engines the BTC skill uses — auto_analysis.build_decision
(token= parameter), structure_summary, ADX/ATR lifecycle (adx_atr_analysis),
chop regime (BTC's continuum = the market's regime for alts, labeled) —
plus the piece the CEO asked for: **BTC-coupling analysis**, because "their
trends would be very similar to btc... other coins might go up/down
independently". Each coin gets a Pearson correlation of 15m log-returns
vs BTC (last ~18h), a beta, and 24h relative strength, labeled:
    OWN-TREND  (|corr| < 0.6)  — moves on its own story
    BTC-DRIVEN (|corr| >= 0.6) — a leveraged BTC echo, treat BTC's
                                 read as the primary context

Usage:
    python3 coin_analysis.py               # jup_yolo list (PG fills):
                                           # HYPE, SOL, BTC, ETH
    python3 coin_analysis.py HYPE SOL ...  # explicit coins

Data: LOCAL candles.db + continuum only (data-source rule). Screening
output only — execution still goes through manual-trade-override.
"""
import json
import math
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA
import auto_analysis as AA
import adx_atr_analysis as AX

JUP_COINS = ['HYPE', 'SOL', 'BTC', 'ETH']   # jup_yolo fills (PG, 2026-10-30→)


def _closes_15m(token, n=110):
    con = sqlite3.connect(f'file:{HERMES_DATA}/candles.db?mode=ro', uri=True)
    try:
        cur = con.cursor()
        cur.execute("SELECT ts, close FROM candles_15m WHERE token=? "
                    "AND is_closed=1 ORDER BY ts DESC LIMIT ?",
                    (token, n))
        return list(reversed(cur.fetchall()))
    finally:
        con.close()


def btc_coupling(coin):
    """Correlation of 15m log-returns vs BTC + beta + 24h relative
    strength. Returns None when the overlap is too thin to claim."""
    a = dict(_closes_15m(coin, 115))
    b = dict(_closes_15m('BTC', 115))
    ts = sorted(set(a) & set(b))
    if len(ts) < 40:
        return None
    ts = ts[-73:]                       # 72 return windows ≈ 18h
    ra, rb = [], []
    for i in range(1, len(ts)):
        ca, cb = a[ts[i - 1]], b[ts[i - 1]]
        if ca <= 0 or cb <= 0:
            continue
        ra.append(math.log(a[ts[i]] / ca))
        rb.append(math.log(b[ts[i]] / cb))
    n = len(ra)
    if n < 40:
        return None
    ma, mb = sum(ra) / n, sum(rb) / n
    cov = sum((x - ma) * (y - mb) for x, y in zip(ra, rb)) / n
    va = sum((x - ma) ** 2 for x in ra) / n
    vb = sum((y - mb) ** 2 for y in rb) / n
    if va <= 0 or vb <= 0:
        return None
    corr = max(-1.0, min(1.0, cov / math.sqrt(va * vb)))
    beta = cov / vb
    old = ts[0]
    coin24 = a[ts[-1]] / a[old] - 1
    btc24 = b[ts[-1]] / b[old] - 1
    return {'corr': corr, 'beta': beta, 'coin24h': coin24,
            'btc24h': btc24, 'rs24h': coin24 - btc24,
            'label': 'BTC-DRIVEN' if abs(corr) >= 0.6 else 'OWN-TREND'}


def analyze(coin):
    dec = AA.build_decision(f'coin-{coin}', [], {'mode': 'live', 'phase': 1},
                            token=coin)
    coup = btc_coupling(coin)
    adx = {tf: AX.lifecycle(tf, coin) for tf in ('15m', '1h')}
    return dec, coup, adx


def _adx_line(r):
    if not r:
        return 'n/a'
    return (f"ADX {r['adx']:.1f} (peak {r['adx_peak']:.1f} {r['adx_peak_bars']}b "
            f"{'PEAKED' if r['adx_peaked'] else 'ago/run'}) | "
            f"ATR {r['atr']:.1f} ({r['atr_pct']:.2f}%) → {r['state']}")


def main():
    coins = [c.upper() for c in sys.argv[1:]] or JUP_COINS
    print(f"COIN ANALYSIS — full-analysis spin-off · {', '.join(coins)}")
    print("regime/chop = market (BTC continuum); structure/ADX/RSI = the coin's own\n")
    rows = []
    for coin in coins:
        try:
            dec, coup, adx = analyze(coin)
        except Exception as e:
            print(f"══ {coin}: ERROR {e}")
            continue
        p = dec.get('price')
        st = dec.get('structure') or {}
        print(f"══ {coin} @ {p} · {dec.get('regime_state')} "
              f"({dec.get('flips_24h')} flips, src {dec.get('regime_source')}) "
              f"· scores L{dec.get('score_long'):+d}/S{dec.get('score_short'):+d} "
              f"· {dec.get('decision')}")
        if coup:
            print(f"   BTC-coupling: {coup['label']} — corr {coup['corr']:+.2f} "
                  f"beta {coup['beta']:.2f} | 24h {coup['coin24h']*100:+.1f}% vs "
                  f"BTC {coup['btc24h']*100:+.1f}% (RS {coup['rs24h']*100:+.1f}%)")
        else:
            print("   BTC-coupling: n/a (thin overlap)")
        print(f"   structure: " + " · ".join(f"{tf} {st.get(tf)}" for tf in
                                             ('5m', '15m', '1h', '4h') if tf in st))
        print(f"   15m ADX/ATR: {_adx_line(adx.get('15m'))}")
        print(f"   1h  ADX/ATR: {_adx_line(adx.get('1h'))}")
        br = dec.get('bracket') or {}
        if dec.get('decision') == 'BRACKET' and br:
            legs = ", ".join(f"{k} {v.get('trigger_dir','?')} {v.get('trigger')}"
                             f" (SL {v.get('sl')} TP {v.get('tp')})"
                             for k, v in br.items())
            print(f"   bracket: {legs}")
        ind = {tf: AA.tf_indicators(coin, tf) for tf in ('15m', '1h', '4h')}
        ind = {k: v for k, v in ind.items() if v}
        rsi = " · ".join(f"{tf} RSI {v['rsi']:.0f}{'🔥' if v['macd_bull'] else ''}"
                         for tf, v in ind.items())
        print(f"   {rsi}")
        rows.append((coin, dec, coup))
        print()
    # screening summary
    print("══ SUMMARY ══")
    print(f"{'coin':6s} {'label':11s} {'corr':>6s} {'24h RS':>8s} {'L/S score':>10s} {'decision':11s}")
    for coin, dec, coup in rows:
        c = coup or {'label': 'n/a', 'corr': 0, 'rs24h': 0}
        print(f"{coin:6s} {c['label']:11s} {c['corr']:+6.2f} {c['rs24h']*100:+7.1f}% "
              f"{dec.get('score_long'):>+5d}/{dec.get('score_short'):<+4d} {dec.get('decision'):11s}")
    print("\nOWN-TREND rows trade their own story (BTC read = context only); "
          "BTC-DRIVEN rows are echoes — lead with the BTC full-analysis there.")


if __name__ == '__main__':
    main()
