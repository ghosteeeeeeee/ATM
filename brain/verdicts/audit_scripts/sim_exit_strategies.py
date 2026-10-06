#!/usr/bin/env python3
"""
Independent audit — exit strategy simulation (ride_it vs current exit).

Loads LONG trades closed in last 30d from PostgreSQL brain DB, then replays
forward 5m candles from candles.db to compare:
  CUR-A : task-spec current exit  — SL -1.5%, trail act 0.4%, dist 1.2%
  CUR-B : realistic default       — SL -1.5%, PM trail tiers (0.4% act,
          0.2/0.5/0.8/1.2% tiers by peak profit)
  RIDE-A: task-spec ride_it       — SL entry*(1-clamp(2*ATR1h,1.3%,2.5%)),
          no trail <2% profit, trail 1.2% at >=2% profit, max hold 24h
  RIDE-B: full ride_it impl       — RIDE-A + momentum exit (2h+, profit>1%,
          2 consecutive 5m closes < -0.5%) + vol-spike override (>=5x avg20
          vol AND |profit|>=3% -> 0.5% trail)

Candle rules (conservative, no look-ahead within a candle):
  - SL/trail checked against candle LOW first; trail updated from candle HIGH
    applies from the NEXT candle.
  - Candle OPEN below SL -> exit at open (gap).
  - Max hold: exit at close of first candle with ts >= open+24h.
  - Data runs out before resolution -> exit at last close (censored).
"""
import sys, os, json, sqlite3
from datetime import datetime, timezone, timedelta
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), 'scripts'))
from paths import HERMES_DATA, CANDLES_DB
from _secrets import BRAIN_DB_DICT

CANDLES = os.path.join(HERMES_DATA, 'candles.db')
OUT_DIR = os.path.dirname(os.path.abspath(__file__))

SIGNALS = ['pump-chain+','bb-squeeze+','pump_chain','bb-bounce-v2-long+',
           'bb_bounce_v2_long','volume-breakout-long+','mover+','bb-bounce-v3-long+',
           'sma20_dip','grind-trend+','coiled_spring','doji-bottom-long',
           'slow_grind','rr-struct+','trend-ride+']

# ── 1. Pull trades from PostgreSQL ────────────────────────────────────────────
def load_trades():
    import psycopg2
    conn = psycopg2.connect(**BRAIN_DB_DICT)
    cur = conn.cursor()
    q = """
    SELECT id, token, signal, entry_price, open_time, close_time, exit_price,
           pnl_usdt, pnl_pct, exit_reason, sl_distance
    FROM trades
    WHERE direction='LONG' AND status='closed'
      AND close_time >= CURRENT_TIMESTAMP - interval '30 days'
      AND signal = ANY(%s)
    ORDER BY open_time
    """
    cur.execute(q, (SIGNALS,))
    rows = cur.fetchall()
    conn.close()
    trades = []
    for r in rows:
        tid, token, signal, entry, ot, ct, xp, pnl, pnl_pct, er, sl_d = r
        if entry is None or ot is None or token is None:
            continue
        trades.append({
            'id': tid, 'token': token.upper(), 'signal': signal,
            'entry': float(entry), 'open_time': ot, 'close_time': ct,
            'exit_price': float(xp) if xp else None,
            'pnl_usdt': float(pnl) if pnl else None,
            'pnl_pct': float(pnl_pct) if pnl_pct else None,
            'exit_reason': er, 'sl_distance': float(sl_d) if sl_d else None,
        })
    return trades

# ── 2. Load candles ───────────────────────────────────────────────────────────
def load_candles(trades):
    tokens = sorted({t['token'] for t in trades})
    t_min = min(t['open_time'] for t in trades)
    t_max = max(t['open_time'] for t in trades)
    lo = int((t_min - timedelta(hours=48)).timestamp())
    hi = int((t_max + timedelta(hours=26)).timestamp())

    conn = sqlite3.connect(CANDLES, timeout=10)
    cur = conn.cursor()
    f5 = defaultdict(list)   # token -> [(ts,o,h,l,c,v)]
    f1h = defaultdict(list)  # token -> [(ts,o,h,l,c)]
    for tok in tokens:
        cur.execute("""SELECT ts, open, high, low, close, volume FROM candles_5m
                       WHERE token=? AND is_closed=1 AND ts>=? AND ts<=?
                       ORDER BY ts""", (tok, lo, hi))
        f5[tok] = cur.fetchall()
        cur.execute("""SELECT ts, open, high, low, close FROM candles_1h
                       WHERE token=? AND is_closed=1 AND ts>=? AND ts<=?
                       ORDER BY ts""", (tok, lo, hi))
        f1h[tok] = cur.fetchall()
    conn.close()
    return f5, f1h

# ── 3. ATR(14) on 1h at entry time (chronological = correct Wilder pairing) ──
def atr1h_at_entry(rows_1h, open_epoch):
    avail = [r for r in rows_1h if r[0] < open_epoch]
    if len(avail) < 15:
        return 0.0
    trs = []
    for i in range(1, len(avail)):
        h, l, pc = avail[i][1], avail[i][2], avail[i-1][3]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    return sum(trs[-14:]) / 14.0

# ── 4. Simulation engines ─────────────────────────────────────────────────────
def sim_current(candles, entry, open_epoch, sl_pct, act, dist_tiers,
                max_hold_h=None):
    """Generic trailing sim. dist_tiers: float OR list[(min_profit, dist)] ratchet."""
    sl = entry * (1 - sl_pct)
    peak = entry
    trail = None
    end_epoch = open_epoch + (max_hold_h * 3600 if max_hold_h else None) \
        if max_hold_h else None
    for (ts, o, h, l, c, v) in candles:
        # SL check first (initial SL or trailed SL)
        eff_sl = trail if (trail is not None and trail > sl) else sl
        if o <= eff_sl:
            return dict(exit=eff_sl, ts=ts, reason='sl')
        if l <= eff_sl:
            return dict(exit=eff_sl, ts=ts, reason='sl')
        peak = max(peak, h)
        peak_profit = peak / entry - 1
        if peak_profit >= act:
            if isinstance(dist_tiers, list):
                d = next((dp for mp, dp in reversed(dist_tiers)
                          if peak_profit >= mp), dist_tiers[0][1])
            else:
                d = dist_tiers
            new_trail = peak * (1 - d)
            trail = max(trail, new_trail) if trail else new_trail
        if end_epoch is not None and ts >= end_epoch:
            return dict(exit=c, ts=ts, reason='max_hold')
    return dict(exit=candles[-1][3], ts=candles[-1][0], reason='data_end') \
        if candles else None

def sim_current_cutloser(candles, entry, open_epoch, sl_pct, act, dist_tiers,
                         cut_pct=-0.010, max_hold_h=8.0):
    """CUR-C: realistic current default — PM tiers trail + cut_loser T1 at
    -1.0% (CL_TIER1 shallow edge, fires every 2-4 min) + 8h universal max hold."""
    sl = entry * (1 - sl_pct)
    peak = entry
    trail = None
    end_epoch = open_epoch + max_hold_h * 3600
    for (ts, o, h, l, c, v) in candles:
        eff_sl = trail if (trail is not None and trail > sl) else sl
        if o <= eff_sl:
            return dict(exit=eff_sl, ts=ts, reason='sl')
        if l <= eff_sl:
            return dict(exit=eff_sl, ts=ts, reason='sl')
        # cut_loser T1: close at candle close if pnl <= -1.0%
        if (c / entry - 1) <= cut_pct:
            return dict(exit=c, ts=ts, reason='cut_loser')
        peak = max(peak, h)
        peak_profit = peak / entry - 1
        if peak_profit >= act:
            if isinstance(dist_tiers, list):
                d = next((dp for mp, dp in reversed(dist_tiers)
                          if peak_profit >= mp), dist_tiers[0][1])
            else:
                d = dist_tiers
            new_trail = peak * (1 - d)
            trail = max(trail, new_trail) if trail else new_trail
        if ts >= end_epoch:
            return dict(exit=c, ts=ts, reason='max_hold8h')
    return dict(exit=candles[-1][3], ts=candles[-1][0], reason='data_end') \
        if candles else None

def sim_ride_it_live(candles, entry, open_epoch, atr):
    """RIDE-C: pure ride_it spec BUT under live overlay — cut_loser cuts at
    -1.0% (cut_loser.py does NOT exempt ride_it signals) and UNIVERSAL_MAX_HOLD
    (8h) force-closes before ride_it's 24h max hold can fire."""
    atr_pct = (atr / entry) if (atr and entry) else 0.013
    sl_dist = min(max(2.0 * atr_pct, 0.013), 0.025)
    sl = entry * (1 - sl_dist)
    peak = entry
    trail = None
    for (ts, o, h, l, c, v) in candles:
        eff_sl = trail if (trail is not None and trail > sl) else sl
        if o <= eff_sl:
            return dict(exit=eff_sl, ts=ts, reason='sl', sl_pct=sl_dist)
        if l <= eff_sl:
            return dict(exit=eff_sl, ts=ts, reason='sl', sl_pct=sl_dist)
        if (c / entry - 1) <= -0.010:
            return dict(exit=c, ts=ts, reason='cut_loser', sl_pct=sl_dist)
        elapsed_h = (ts - open_epoch) / 3600.0
        peak = max(peak, h)
        if elapsed_h >= 2.0 and (peak / entry - 1) >= 0.02:
            new_trail = peak * (1 - 0.012)
            trail = max(trail, new_trail) if trail else new_trail
        if ts >= open_epoch + 8 * 3600:
            return dict(exit=c, ts=ts, reason='max_hold8h', sl_pct=sl_dist)
    return dict(exit=candles[-1][3], ts=candles[-1][0], reason='data_end',
                sl_pct=sl_dist) if candles else None

def sim_ride_it(candles, entry, open_epoch, atr, full_impl=False):
    """Ride-it: wide ATR SL phase1, trail at 2% profit, 24h max hold.
    full_impl=True adds momentum exit + volume-spike override."""
    atr_pct = (atr / entry) if (atr and entry) else 0.013
    sl_dist = min(max(2.0 * atr_pct, 0.013), 0.025)
    sl = entry * (1 - sl_dist)
    peak = entry
    trail = None
    neg_run = 0
    prev_close = None
    for idx, (ts, o, h, l, c, v) in enumerate(candles):
        eff_sl = trail if (trail is not None and trail > sl) else sl
        if o <= eff_sl:
            return dict(exit=eff_sl, ts=ts, reason='sl', sl_pct=sl_dist)
        if l <= eff_sl:
            return dict(exit=eff_sl, ts=ts, reason='sl', sl_pct=sl_dist)
        elapsed_h = (ts - open_epoch) / 3600.0
        profit = c / entry - 1
        peak = max(peak, h)
        peak_profit = peak / entry - 1

        if full_impl:
            # Volume-spike override (any phase): >=5x 20-bar avg vol, |profit|>=3%
            if idx >= 20:
                avg_vol = sum(x[5] for x in candles[idx-20:idx]) / 20.0
                if avg_vol > 0 and v >= 5.0 * avg_vol and abs(profit) >= 0.03:
                    new_trail = peak * (1 - 0.005)
                    trail = max(trail, new_trail) if trail else new_trail

        if elapsed_h >= 2.0:
            # Momentum exit: 2 consecutive closes < -0.5% and profit > 1%
            if full_impl and prev_close is not None:
                ret = (c - prev_close) / prev_close
                neg_run = neg_run + 1 if ret < -0.005 else 0
                if neg_run >= 2 and profit > 0.01:
                    return dict(exit=c, ts=ts, reason='momentum', sl_pct=sl_dist)
            # Trail activation at 2% peak profit
            if peak_profit >= 0.02:
                new_trail = peak * (1 - 0.012)
                trail = max(trail, new_trail) if trail else new_trail

        prev_close = c
        if ts >= open_epoch + 24 * 3600:
            return dict(exit=c, ts=ts, reason='max_hold', sl_pct=sl_dist)
    return dict(exit=candles[-1][3], ts=candles[-1][0], reason='data_end',
                sl_pct=sl_dist) if candles else None

# ── 5. Run ────────────────────────────────────────────────────────────────────
def main():
    trades = load_trades()
    print(f"Loaded {len(trades)} LONG trades (14 signals, 30d)")
    f5, f1h = load_candles(trades)
    no_candles = 0
    results = []
    for t in trades:
        tok = t['token']
        rows5 = f5.get(tok, [])
        open_epoch = int(t['open_time'].replace(tzinfo=timezone.utc).timestamp())
        fwd = [r for r in rows5 if r[0] >= open_epoch]
        if len(fwd) < 6:
            no_candles += 1
            continue
        atr = atr1h_at_entry(f1h.get(tok, []), open_epoch)
        entry = t['entry']
        res = {'trade': t, 'atr1h': atr, 'n_fwd_candles': len(fwd)}
        res['CUR-A'] = sim_current(fwd, entry, open_epoch, 0.015, 0.004, 0.012)
        res['CUR-B'] = sim_current(fwd, entry, open_epoch, 0.015, 0.004,
                                   [(0.0, 0.002), (0.015, 0.005),
                                    (0.030, 0.008), (0.050, 0.012)])
        res['CUR-C'] = sim_current_cutloser(fwd, entry, open_epoch, 0.015, 0.004,
                                            [(0.0, 0.002), (0.015, 0.005),
                                             (0.030, 0.008), (0.050, 0.012)])
        res['RIDE-A'] = sim_ride_it(fwd, entry, open_epoch, atr, full_impl=False)
        res['RIDE-B'] = sim_ride_it(fwd, entry, open_epoch, atr, full_impl=True)
        res['RIDE-C'] = sim_ride_it_live(fwd, entry, open_epoch, atr)
        for strat in ('CUR-A', 'CUR-B', 'CUR-C', 'RIDE-A', 'RIDE-B', 'RIDE-C'):
            r = res[strat]
            if r:
                r['pnl_pct'] = (r['exit'] / entry - 1) * 100
                r['hold_h'] = (r['ts'] - open_epoch) / 3600.0
                r['win'] = r['pnl_pct'] > 0
        results.append(res)
    print(f"Simulated {len(results)} trades ({no_candles} skipped: <6 fwd candles)")

    # Per-signal aggregation
    agg = defaultdict(lambda: defaultdict(list))
    for res in results:
        sig = res['trade']['signal']
        agg[sig]['actual'].append(res['trade'])
        for strat in ('CUR-A', 'CUR-B', 'CUR-C', 'RIDE-A', 'RIDE-B', 'RIDE-C'):
            if res[strat]:
                agg[sig][strat].append(res[strat])

    hdr = (f"{'signal':24s} {'n':>3s} | {'ACT_WR':>6s} {'ACT_pnl':>7s} | "
           f"{'C-A_WR':>6s} {'C-A_pnl':>7s} | {'C-C_WR':>6s} {'C-C_pnl':>7s} | "
           f"{'R-A_WR':>6s} {'R-A_pnl':>7s} | {'R-C_WR':>6s} {'R-C_pnl':>7s}")
    print(hdr); print('-' * len(hdr))
    summary = {}
    all_strats = defaultdict(list)
    for sig in sorted(agg, key=lambda s: -len(agg[s]['actual'])):
        g = agg[sig]
        line = {'signal': sig, 'n': len(g['actual'])}
        cells = [f"{sig:24s} {len(g['actual']):>3d} "]
        act = g['actual']
        act_wr = 100 * sum(1 for t in act if (t['pnl_pct'] or 0) > 0) / len(act)
        act_pnl = sum((t['pnl_pct'] or 0) for t in act) / len(act)
        cells.append(f"| {act_wr:6.1f} {act_pnl:7.2f} ")
        line['actual'] = {'wr': round(act_wr, 1), 'avg_pnl_pct': round(act_pnl, 2)}
        for strat in ('CUR-A', 'CUR-B', 'CUR-C', 'RIDE-A', 'RIDE-B', 'RIDE-C'):
            s = g[strat]
            wr = 100 * sum(1 for r in s if r['win']) / len(s)
            pnl = sum(r['pnl_pct'] for r in s) / len(s)
            hold = sum(r['hold_h'] for r in s) / len(s)
            reasons = defaultdict(int)
            for r in s:
                reasons[r['reason']] += 1
            if strat in ('CUR-A', 'CUR-C', 'RIDE-A', 'RIDE-C'):
                cells.append(f"| {wr:6.1f} {pnl:7.2f} ")
            line[strat] = {'wr': round(wr, 1), 'avg_pnl_pct': round(pnl, 2),
                           'avg_hold_h': round(hold, 2), 'reasons': dict(reasons)}
            all_strats[strat].extend(s)
        print(' '.join(cells))
        summary[sig] = line

    print()
    print("Overall (all signals combined):")
    for strat in ('CUR-A', 'CUR-B', 'CUR-C', 'RIDE-A', 'RIDE-B', 'RIDE-C'):
        s = all_strats[strat]
        wr = 100 * sum(1 for r in s if r['win']) / len(s)
        pnl = sum(r['pnl_pct'] for r in s) / len(s)
        hold = sum(r['hold_h'] for r in s) / len(s)
        reasons = defaultdict(int)
        for r in s:
            reasons[r['reason']] += 1
        print(f"  {strat}: n={len(s)} WR={wr:.1f}% avg_pnl={pnl:+.2f}% "
              f"hold={hold:.2f}h reasons={dict(reasons)}")

    # ride_it SL distance distribution (how often floor binds -> inert)
    sl_pcts = [res['RIDE-A']['sl_pct'] for res in results if res.get('RIDE-A')]
    floor_n = sum(1 for x in sl_pcts if abs(x - 0.013) < 1e-9)
    print(f"\nRide-it phase1 SL: n={len(sl_pcts)}, floored at 1.3%: {floor_n} "
          f"({100*floor_n/len(sl_pcts):.0f}%), "
          f"avg={100*sum(sl_pcts)/len(sl_pcts):.2f}%, "
          f"max={100*max(sl_pcts):.2f}%")
    atrs = [res['atr1h'] / res['trade']['entry'] for res in results if res.get('RIDE-A')]
    print(f"1h ATR% at entry: avg={100*sum(atrs)/len(atrs):.3f}%, "
          f"2xATR avg={200*sum(atrs)/len(atrs):.3f}%")

    with open(os.path.join(OUT_DIR, 'sim_results.json'), 'w') as f:
        json.dump({'summary': summary, 'n_trades': len(results)}, f, indent=1)
    print(f"\nSaved -> {OUT_DIR}/sim_results.json")

if __name__ == '__main__':
    main()
