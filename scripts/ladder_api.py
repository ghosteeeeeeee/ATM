#!/usr/bin/env python3
"""ladder_api.py — the Ladder dashboard feed (CEO 2026-11-23).

Emits /var/www/hermes/data/ladder.json:
  price/age      live BTC from prices.json (the collector, ~5s fresh)
  candles[]      last 180 CLOSED 15m bars (the chart)
  rungs[]        armed BTC ladder rungs from pending_orders.json + states
  stats          ai-trader-pending: totals, windows, MFE split, recents

Refresh: hermes-ladder-api.timer (60s); the page polls every 30s.
Stdlib + local DB only (the local-data-first SOP).
"""
import json
import os
import sqlite3
import sys
import time

sys.path.insert(0, '/root/.hermes/scripts')
from paths import HERMES_DATA  # noqa: E402

OUT = '/var/www/hermes/data/ladder.json'


def live_price():
    try:
        d = json.load(open(os.path.join(HERMES_DATA, 'prices.json')))
        p = d.get('prices', {}).get('BTC')
        age = time.time() - float(d.get('updated') or 0)
        return (float(p) if p else None), age
    except Exception:
        return None, None


def candles(n=180):
    con = sqlite3.connect(
        f"file:{os.path.join(HERMES_DATA, 'candles.db')}?mode=ro", uri=True)
    try:
        cur = con.cursor()
        cur.execute(
            "SELECT ts, open, high, low, close, volume FROM candles_15m "
            "WHERE token='BTC' AND is_closed=1 ORDER BY ts DESC LIMIT ?",
            (n,))
        rows = list(reversed(cur.fetchall()))
    finally:
        con.close()
    return [{'t': int(r[0]), 'o': float(r[1]), 'h': float(r[2]),
             'l': float(r[3]), 'c': float(r[4]),
             'v': float(r[5] or 0)} for r in rows]


def rungs():
    try:
        cfg = json.load(open(os.path.join(HERMES_DATA, 'pending_orders.json')))
        st = json.load(open(
            os.path.join(HERMES_DATA, 'pending_orders_state.json')))
    except Exception:
        return []
    out = []
    for o in cfg.get('orders', []):
        if o.get('coin') != 'BTC':
            continue
        s = st.get(o.get('id'), {}).get('status', 'UNFIRED')
        if s in ('fired', 'error'):
            continue  # consumed — not a planned entry anymore
        out.append({
            'id': o.get('id'), 'dir': o.get('direction'),
            'trig': float(o.get('trigger_price') or 0),
            'sl': float(o.get('sl') or 0) or None,
            'tp': float(o.get('target') or 0) or None,
            'style': o.get('entry_style', 'retest'),
            'state': s,
            'amt': o.get('amount_usdt'), 'lev': o.get('leverage'),
        })
    out.sort(key=lambda r: r['trig'])
    return out


def _net_of(fees, pnl_usdt):
    """HL's own net (the fees JSON blob) — falls back to pnl−fee_total."""
    if fees:
        try:
            f = json.loads(fees) if isinstance(fees, str) else fees
            if isinstance(f, dict) and f.get('net_pnl') is not None:
                return float(f['net_pnl'])
        except Exception:
            pass
    return float(pnl_usdt or 0)


def stats():
    try:
        from brain import get_db_connection
    except Exception as e:
        return {'error': f'brain import: {e}'}
    out = {}
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, direction, entry_price, exit_price, exit_reason, "
            "pnl_usdt, fees, amount_usdt, leverage, open_time, close_time, "
            "highest_price, lowest_price "
            "FROM trades WHERE status='closed' AND signal='ai-trader-pending' "
            "AND close_time > (now() - interval '14 days') "
            "ORDER BY close_time DESC")
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]

        now = time.time()
        recs = []
        for r in rows:
            d = dict(zip(cols, r))
            entry = float(d['entry_price'] or 0)
            hi = float(d['highest_price'] or 0)
            lo = float(d['lowest_price'] or 0)
            if entry and hi and lo:
                mfe = ((hi / entry - 1) if d['direction'] == 'LONG'
                       else (1 - lo / entry)) * 100
            else:
                mfe = 0.0
            hold = 0.0
            if d['open_time'] and d['close_time']:
                hold = (d['close_time'] - d['open_time']).total_seconds() / 60
            ct = d['close_time']
            recs.append({
                'id': d['id'], 'dir': d['direction'],
                'entry': entry,
                'exit': float(d['exit_price'] or 0) if d['exit_price'] else None,
                'reason': d['exit_reason'],
                'net': _net_of(d['fees'], d['pnl_usdt']),
                'mfe': round(mfe, 2), 'hold': int(hold),
                'ts': ct.isoformat() if ct else None,
                'ts_epoch': ct.timestamp() if ct else 0,
            })

        n = len(recs)
        net = sum(r['net'] for r in recs)
        wins = sum(1 for r in recs if r['net'] > 0)
        fees_paid = 0.0
        for r in rows:
            try:
                f = json.loads(r[6]) if isinstance(r[6], str) else (r[6] or {})
                fees_paid += float((f or {}).get('fee_total') or 0)
            except Exception:
                pass

        def window(hours):
            cut = now - hours * 3600
            w = [r for r in recs if r['ts_epoch'] >= cut]
            return len(w), round(sum(x['net'] for x in w), 4)

        # recency-weighted (half-life 3d) — the CEO's training tilt
        wnet = 0.0
        for r in recs:
            if not r['ts_epoch']:
                continue
            age_d = (now - r['ts_epoch']) / 86400.0
            wnet += (0.5 ** (age_d / 3.0)) * r['net']

        buckets = {'ran': [0, 0.0], 'mid': [0, 0.0], 'never': [0, 0.0]}
        for r in recs:
            k = ('ran' if r['mfe'] >= 1.0
                 else 'mid' if r['mfe'] >= 0.3 else 'never')
            buckets[k][0] += 1
            buckets[k][1] += r['net']

        cur.execute(
            "SELECT id, direction, entry_price, stop_loss, pnl_pct, amount_usdt "
            "FROM trades WHERE status='open' AND signal='ai-trader-pending'")
        opens = cur.fetchall()

        out = {
            'n': n, 'net': round(net, 4),
            'wr': round(wins / n * 100, 1) if n else 0,
            'wins': wins,
            'fees': round(fees_paid, 4),
            'per_trade': round(net / n, 4) if n else 0,
            'w24': window(24), 'w72': window(72), 'w168': window(168),
            'weighted_net_3d': round(wnet, 4),
            'closes_per_day': round(n / 14.0, 1),
            'mfe_split': {
                k: {'n': v[0], 'net': round(v[1], 4)}
                for k, v in buckets.items()},
            'open': [{'id': o[0], 'dir': o[1], 'entry': float(o[2] or 0),
                      'sl': float(o[3] or 0) if o[3] else None,
                      'pnl_pct': float(o[4] or 0),
                      # psycopg2 returns Decimal for numeric columns —
                      # float() it or the feed dies the moment an open
                      # row exists (it was latent while the list was empty)
                      'amt': float(o[5] or 0)}
                     for o in opens],
            'recent': recs[:25],
        }
        cur.close()
        conn.close()
    except Exception as e:
        out = {'error': str(e)}
    return out


def indicators(bars):
    """RSI(14) Wilder · MACD line (EMA12-EMA26) · ADX(14) Wilder ·
    ATR(14) Wilder — computed from the same closed 15m bars (stdlib).
    Returns per-bar arrays aligned to `bars` (None = warmup) + currents.
    """
    n = len(bars)
    rsi = [None] * n
    macd = [None] * n
    adx = [None] * n
    atr = [None] * n
    if n < 32:
        return {'rsi': rsi, 'macd': macd, 'adx': adx, 'atr': atr}
    closes = [b['c'] for b in bars]

    # RSI(14), Wilder smoothing
    ag = al = None
    for i in range(1, n):
        ch = closes[i] - closes[i - 1]
        g, l = max(ch, 0.0), max(-ch, 0.0)
        if i <= 14:
            if i == 14:
                ag = sum(max(closes[j] - closes[j - 1], 0.0)
                         for j in range(1, 15)) / 14.0
                al = sum(max(closes[j - 1] - closes[j], 0.0)
                         for j in range(1, 15)) / 14.0
                rsi[i] = 100.0 - 100.0 / (1.0 + (ag / al if al else 100.0))
        else:
            ag = (ag * 13 + g) / 14.0
            al = (al * 13 + l) / 14.0
            rsi[i] = 100.0 - 100.0 / (1.0 + (ag / al if al else 100.0))

    # MACD line (EMA12 - EMA26); the line is the plotted series
    e12 = e26 = closes[0]
    for i, c in enumerate(closes):
        e12 += (c - e12) * (2.0 / 13.0)
        e26 += (c - e26) * (2.0 / 27.0)
        if i >= 26:
            macd[i] = e12 - e26

    # TR / +DM / -DM with Wilder smoothing -> ATR(14), +DI/-DI, DX, ADX(14)
    tr_s = pdm_s = ndm_s = None
    dxs = []
    adx_v = None
    prev = bars[0]
    for i in range(1, n):
        h, l, pc = bars[i]['h'], bars[i]['l'], bars[i - 1]['c']
        ph, pl = prev['h'], prev['l']
        tr = max(h - l, abs(h - pc), abs(l - pc))
        up, dn = h - ph, pl - l
        pdm_i = up if (up > dn and up > 0.0) else 0.0
        ndm_i = dn if (dn > up and dn > 0.0) else 0.0
        if i <= 14:
            tr_s = (tr_s or 0.0) + tr
            pdm_s = (pdm_s or 0.0) + pdm_i
            ndm_s = (ndm_s or 0.0) + ndm_i
            if i == 14:
                atr[i] = tr_s / 14.0
        else:
            tr_s = tr_s - tr_s / 14.0 + tr
            pdm_s = pdm_s - pdm_s / 14.0 + pdm_i
            ndm_s = ndm_s - ndm_s / 14.0 + ndm_i
            atr[i] = tr_s / 14.0
            pdi = 100.0 * pdm_s / tr_s if tr_s else 0.0
            ndi = 100.0 * ndm_s / tr_s if tr_s else 0.0
            dx = 100.0 * abs(pdi - ndi) / (pdi + ndi) if (pdi + ndi) else 0.0
            dxs.append(dx)
            if len(dxs) == 14:
                adx_v = sum(dxs) / 14.0
                adx[i] = adx_v
            elif len(dxs) > 14:
                adx_v = (adx_v * 13.0 + dx) / 14.0
                adx[i] = adx_v
        prev = bars[i]

    def last_valid(a):
        for v in reversed(a):
            if v is not None:
                return round(v, 4)
        return None
    return {'rsi': [None if v is None else round(v, 3) for v in rsi],
            'macd': [None if v is None else round(v, 2) for v in macd],
            'adx': [None if v is None else round(v, 3) for v in adx],
            'atr': [None if v is None else round(v, 2) for v in atr],
            'cur': {'rsi': last_valid(rsi), 'macd': last_valid(macd),
                    'adx': last_valid(adx), 'atr': last_valid(atr)}}


def chart_trades():
    """BTC fills with their open/close times for the chart markers
    (buy/sell icons at the entries + the exit dots). 48h window —
    covers the 180x15m chart (45h) with margin. Includes open rows."""
    try:
        from brain import get_db_connection
    except Exception:
        return []
    out = []
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, direction, entry_price, exit_price, open_time, "
            "close_time, status, pnl_usdt, fees, signal "
            "FROM trades WHERE token='BTC' "
            "AND open_time > (now() - interval '48 hours') "
            "ORDER BY open_time")
        for r in cur.fetchall():
            net = _net_of(r[8], r[7])
            out.append({
                'id': r[0], 'dir': r[1], 'entry': float(r[2] or 0),
                'exit': float(r[3] or 0) if r[3] else None,
                'open_ts': r[4].timestamp() if r[4] else None,
                'close_ts': r[5].timestamp() if r[5] else None,
                'status': r[6], 'net': round(net, 4),
                'reason': r[9],
            })
        cur.close()
        conn.close()
    except Exception:
        return out
    return out


def continuum_series(bars):
    """Continuum state_score AND zscore_val aligned to the candle bars:
    for each 15m bar, the last continuum tick inside that bar (local
    continuum_data.json). Returns (score[], score_cur, z[], z_cur) —
    None = no tick in coverage."""
    n = len(bars)
    out = [None] * n
    zout = [None] * n
    cur_val = None
    z_cur = None
    try:
        d = json.load(open('/var/www/hermes/data/continuum_data.json'))
        hist = d.get('history') or []
        by_bar = {}
        for h in hist:
            ts = h.get('ts')
            sc = h.get('state_score')
            zs = h.get('zscore_val')
            if ts is None or (sc is None and zs is None):
                continue
            bar_t = ts - (ts % 900)          # the 15m bucket
            slot = by_bar.setdefault(bar_t, {})
            if sc is not None:
                slot['s'] = float(sc)
            if zs is not None:
                slot['z'] = float(zs)
        for i, b in enumerate(bars):
            v = by_bar.get(b['t']) or {}
            if 's' in v:
                out[i] = round(v['s'], 3)
            if 'z' in v:
                zout[i] = round(v['z'], 3)
        newest_s = newest_z = None
        for h in hist:
            if h.get('state_score') is not None:
                newest_s = h
            if h.get('zscore_val') is not None:
                newest_z = h
        if newest_s:
            cur_val = round(float(newest_s['state_score']), 3)
        if newest_z:
            z_cur = round(float(newest_z['zscore_val']), 4)
    except Exception:
        pass
    return out, cur_val, zout, z_cur


def main():
    price, age = live_price()
    # One shared window: 48h of candles (192 x 15m), indicators computed
    # over a PADDED history (192 + 120 warmup bars) then sliced back to
    # the window — RSI/MACD/ADX/ATR warmups (14/26/~40 bars) are absorbed
    # so every displayed bar carries a value (CEO: "the full window").
    _N = 192
    _WARM = 120
    _full = candles(_N + _WARM)
    _ind_full = indicators(_full)
    _bars = _full[-_N:] if len(_full) >= _N else _full
    _ind = {k: (v[-len(_bars):] if isinstance(v, list) else v)
            for k, v in _ind_full.items()}
    feed = {
        'ts': int(time.time()),
        'price': price,
        'price_age_s': round(age, 1) if age is not None else None,
        'candles': _bars,
        'ind': _ind,
        'rungs': rungs(),
        'trades': chart_trades(),
        'stats': stats(),
    }
    _cont, _cont_cur, _z, _z_cur = continuum_series(_bars)
    feed['ind']['cont'] = _cont
    feed['ind']['cur']['cont'] = _cont_cur
    feed['ind']['z'] = _z
    feed['ind']['cur']['z'] = _z_cur
    tmp = OUT + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(feed, f)
    os.replace(tmp, OUT)
    print(f"[ladder_api] price={price} candles={len(feed['candles'])} "
          f"ind={feed['ind'].get('cur')} rungs={len(feed['rungs'])} "
          f"trades={len(feed['trades'])} stats_n={feed['stats'].get('n')}")


if __name__ == '__main__':
    main()
