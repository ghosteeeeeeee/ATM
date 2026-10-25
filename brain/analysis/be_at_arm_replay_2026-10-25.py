#!/usr/bin/env python3
"""BE-at-arm 1m replay — pre-registered #785 (Oct 25 batch), escalation #17 measurement.

Policy under test: once the trail arms (MFE >= arm threshold, default +0.40%),
move stop to entry (breakeven). Trade exits at entry on any post-arm touch.

Counterfactual is price-based on candles_1m. Units: pnl_usdt (unleveraged on
notional) both sides — fee round-trip identical in both scenarios, cancels.
Self-check: python3 brain/analysis/be_at_arm_replay_2026-10-25.py --selfcheck
"""
import sys, json, sqlite3, argparse, datetime as dt
import psycopg2

ARM_DEFAULT = 0.004  # TRAILING_ACTIVATION_PCT / PM_TRAIL_ACTIVATE_PCT


def load_trades(cur, days):
    cur.execute("""
        SELECT id, token, direction, amount_usdt, entry_price, exit_price, pnl_usdt,
               exit_reason, open_time, close_time, signal, fees,
               COALESCE(trailing_activation, %s), mfe_pct, volatility_regime
        FROM trades
        WHERE status='closed' AND close_time > NOW() - INTERVAL '%d days'
          AND pnl_usdt IS NOT NULL AND entry_price IS NOT NULL AND open_time IS NOT NULL
    """ % (ARM_DEFAULT, days))
    return cur.fetchall()


def replay(con, token, open_ts, close_ts, entry, direction, arm, be_thr=None):
    """Returns (armed, be_touched, arm_ts). No candles -> (None, None, None).

    be_thr (price-fraction): extra gate — BE only becomes active once the
    running peak-fav reaches be_thr. None/<=arm = arm-at-BE (pre-reg #785).
    """
    cur = con.cursor()
    cur.execute(
        "SELECT ts, high, low, close FROM candles_1m WHERE token=? AND ts>=? AND ts<=? ORDER BY ts",
        # upper bound = close_ts itself: close_ts+60 admits the NEXT 1m candle,
        # which lies entirely after the real exit -> phantom arm/touch (bug_hunter HIGH).
        # NOTE: the entry candle is deliberately skipped (ts < open_ts) — its pre-entry
        # wick would arm/touch on price the trade never saw (conservative, documented).
        (token, int(open_ts.timestamp()) // 60 * 60 - 60, int(close_ts.timestamp())))
    rows = cur.fetchall()
    if not rows:
        cur.close()
        return None, None, None
    armed_ts = None
    entry_f = float(entry)
    thr = float(arm) if arm else ARM_DEFAULT
    for ts, hi, lo, cl in rows:
        if ts < int(open_ts.timestamp()):
            continue
        if direction == 'LONG':
            if float(hi) >= entry_f * (1 + thr):
                armed_ts = ts
                break
        else:
            if float(lo) <= entry_f * (1 - thr):
                armed_ts = ts
                break
    if armed_ts is None:
        cur.close()
        return False, None, None
    # BE touch only on candles strictly after the arm candle closes.
    # wick = intrabar touch; close_ts = 1m close through entry (unambiguous for live fills too)
    wick = close_thru = None
    be_active_ts = armed_ts
    if be_thr is not None and be_thr > thr:
        # BE activates at the first post-arm candle whose running peak-fav >= be_thr
        peak = 0.0
        for ts, hi, lo, cl in rows:
            if ts <= armed_ts:
                continue
            if direction == 'LONG':
                peak = max(peak, float(hi) / entry_f - 1.0)
            else:
                peak = max(peak, 1.0 - float(lo) / entry_f)
            if peak >= be_thr:
                be_active_ts = ts
                break
        else:
            cur.close()
            return True, None, armed_ts  # never reached the higher gate -> no BE
    for ts, hi, lo, cl in rows:
        if ts <= be_active_ts:
            continue
        if direction == 'LONG':
            if wick is None and float(lo) <= entry_f:
                wick = ts
            if close_thru is None and float(cl) <= entry_f:
                close_thru = ts
        else:
            if wick is None and float(hi) >= entry_f:
                wick = ts
            if close_thru is None and float(cl) >= entry_f:
                close_thru = ts
        if wick is not None and close_thru is not None:
            break
    cur.close()
    return True, (wick, close_thru), armed_ts


def run(days_list=(7, 14, 30), scoped=False, be_thr=None):
    pg = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
    candles = sqlite3.connect('/root/.hermes/data/candles.db')
    out = {}
    try:
        cur = pg.cursor()
        all_tr = load_trades(cur, max(days_list))
        cur.close()
        now = dt.datetime.now(dt.UTC).replace(tzinfo=None)
        for days in days_list:
            cutoff = now - dt.timedelta(days=days)
            trades = [t for t in all_tr if t[9] > cutoff]
            if scoped:
                trades = [t for t in trades
                          if (t[14] or '') != 'EXTREME' and 'volume-' not in (t[10] or '').lower()]
            n = len(trades)
            missing = armed_n = armed_winners = 0
            V = {v: dict(touched=0, save=0.0, harm=0.0, losers=0, hw=0, by_exit={})
                 for v in ('wick', 'close')}
            winners = 0
            for (tid, token, direction, amt, entry, exitp, pnl, exitr, ot, ct, sig, fees, arm, mfe, vol) in trades:
                pnl = float(pnl)
                if pnl > 0:
                    winners += 1
                armed, touch, ats = replay(candles, token, ot, ct, entry, direction, arm, be_thr)
                if armed is None:
                    missing += 1
                    continue
                if armed:
                    armed_n += 1
                    if pnl > 0:
                        armed_winners += 1
                if not touch:
                    continue
                wick_ts, close_ts_ = touch
                for v, tsel in (('wick', wick_ts), ('close', close_ts_)):
                    if tsel is None:
                        continue
                    d = V[v]
                    d['touched'] += 1
                    if pnl < 0:
                        d['save'] += -pnl
                        d['losers'] += 1
                    elif pnl > 0:
                        d['harm'] += pnl
                        d['hw'] += 1
                    key = exitr or 'None'
                    c = d['by_exit'].setdefault(key, [0, 0.0])
                    c[0] += 1
                    c[1] += -pnl
            var = {}
            for v, d in V.items():
                # HOUSE BAR (2026-10-17 verdict): fk <=20% of ARMED winners.
                # fk_all (all window winners) is printed too — it is the DILUTED
                # denominator and always reads lower; never quote it as the bar.
                var[v] = dict(touched=d['touched'], losers_saved=d['losers'], save=round(d['save'], 2),
                              harmed_winners=d['hw'], harm=round(d['harm'], 2),
                              net=round(d['save'] - d['harm'], 2),
                              fk_armed_pct=round(100.0 * d['hw'] / armed_winners, 1) if armed_winners else 0.0,
                              fk_all_pct=round(100.0 * d['hw'] / winners, 1) if winners else 0.0,
                              by_exit={k: (x[0], round(x[1], 2)) for k, x in sorted(d['by_exit'].items())})
            out[days] = dict(n=n, no_candles=missing, armed=armed_n, winners=winners,
                             armed_winners=armed_winners, variants=var)
    finally:
        pg.close()
        candles.close()
    return out


def selfcheck():
    # synthetic: entry 100, long, arm at +0.40% then 1m close below entry -> BE touch
    con = sqlite3.connect(':memory:')
    con.execute("CREATE TABLE candles_1m (token TEXT, ts INT, high REAL, low REAL, close REAL)")
    rows = [('T1', 1000, 100.1, 99.8, 99.9),   # pre-arm wick below entry: must be IGNORED (pre-arm)
            ('T1', 1060, 100.5, 100.0, 100.4),  # arm candle (high 100.5 >= 100.4), touch in it ignored
            ('T1', 1120, 100.6, 99.9, 100.0)]   # post-arm dip: wick AND 1m close through entry
    con.executemany("INSERT INTO candles_1m VALUES (?,?,?,?,?)", rows)
    open_ts = dt.datetime.fromtimestamp(900, dt.UTC).replace(tzinfo=None)
    close_ts = dt.datetime.fromtimestamp(1200, dt.UTC).replace(tzinfo=None)
    armed, touch, ats = replay(con, 'T1', open_ts, close_ts, 100.0, 'LONG', 0.004)
    assert (armed, touch, ats) == (True, (1120, 1120), 1060), (armed, touch, ats)
    # never-armed: threshold far away -> policy never applies, cf == actual
    armed, touch, ats = replay(con, 'T1', open_ts, close_ts, 100.0, 'LONG', 0.5)
    assert (armed, touch) == (False, None), (armed, touch)
    # short arm: low <= entry*(1-thr); post-arm high >= entry = touch
    armed, touch, ats = replay(con, 'T1', open_ts, close_ts, 100.4, 'SHORT', 0.004)
    assert (armed, touch, ats) == (True, (1060, 1060), 1000), (armed, touch, ats)
    # no candles token
    assert replay(con, 'NOPE', open_ts, close_ts, 100.0, 'LONG', 0.004) == (None, None, None)
    # be_thr gate: BE active only after running peak >= 0.6%, touch on a later candle
    con.execute("INSERT INTO candles_1m VALUES ('T1',1180,100.7,100.5,100.6)")
    con.execute("INSERT INTO candles_1m VALUES ('T1',1240,100.5,99.9,100.0)")
    armed, touch, ats = replay(con, 'T1', open_ts, dt.datetime.fromtimestamp(1300, dt.UTC).replace(tzinfo=None),
                               100.0, 'LONG', 0.004, be_thr=0.006)
    assert (armed, touch) == (True, (1240, 1240)), (armed, touch)
    # be_thr never reached -> policy never applies
    armed, touch, ats = replay(con, 'T1', open_ts, dt.datetime.fromtimestamp(1300, dt.UTC).replace(tzinfo=None),
                               100.0, 'LONG', 0.004, be_thr=0.020)
    assert (armed, touch) == (True, None), (armed, touch)
    # post-close candle must NOT arm or touch (bug_hunter HIGH): trade closes at 1200,
    # the 1260 candle lies entirely after the exit -> under the old close_ts+60 bound
    # this counted as a touch and invented a save.
    con.execute("INSERT INTO candles_1m VALUES ('T3',1060,100.5,100.0,100.4)")
    con.execute("INSERT INTO candles_1m VALUES ('T3',1260,100.6,99.9,100.0)")
    armed, touch, ats = replay(con, 'T3', open_ts, close_ts, 100.0, 'LONG', 0.004)
    assert (armed, touch) == (True, (None, None)), (armed, touch)
    con.close()
    print("selfcheck PASS: arm detection + post-arm touch + never-armed + missing-token + be_thr gate + post-close excluded")


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--selfcheck', action='store_true')
    ap.add_argument('--be-thr', type=float, default=None,
                    help='BE activation peak-fav in %% (e.g. 0.8 = 0.8%%); default = arm')
    ap.add_argument('--scoped', action='store_true',
                    help='non-EXTREME + exclude volume- (same scope as 2026-10-17 ARM-BE verdict)')
    a = ap.parse_args()
    if a.selfcheck:
        selfcheck()
        sys.exit(0)
    be_thr = (a.be_thr / 100.0) if a.be_thr is not None else None
    if be_thr is not None and be_thr <= ARM_DEFAULT:
        print(f"WARNING: --be-thr {a.be_thr}% <= arm {ARM_DEFAULT*100}% -> gate disabled (behaves as arm-level)")
    res = run(scoped=a.scoped, be_thr=be_thr)
    print(json.dumps(res, indent=1, default=str))
    for d, r in sorted(res.items()):
        for v, m in r['variants'].items():
            print(f"=== {d}d [{v}]: n={r['n']} no_candles={r['no_candles']} armed={r['armed']} "
                  f"armed_W={r['armed_winners']} touched={m['touched']} | saves {m['losers_saved']}L +{m['save']} | "
                  f"harms {m['harmed_winners']}W -{m['harm']} | NET {m['net']} | "
                  f"fk_armed {m['fk_armed_pct']}% (HOUSE BAR <20%) | fk_all {m['fk_all_pct']}% (diluted)")
            print(f"    by_exit (net +save/-harm): {m['by_exit']}")
