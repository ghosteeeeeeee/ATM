#!/usr/bin/env python3
"""Family-scoped MFE-CUT candle OOS — bb-bounce-v2-long+ (pre-reg #837 blocker, Oct 25 batch).

Rule under test (trade-level shadow numbers were selection-on-outcome; this is the
candle replay): for trades STILL OPEN at T=55m (MFE_CUT_SHADOW_MIN window aligned
with TAT-C), if MFE since entry < 0.20% -> exit at the 1m close at T.
Units: pnl_usdt basis (amount_usdt * price_move / 100, unleveraged on notional).
Self-check: python3 brain/analysis/mfe_cut_bb_bounce_oos_2026-10-25.py --selfcheck
"""
import sys, json, sqlite3, argparse, datetime as dt
import psycopg2

T_MIN = 55          # minutes (aligns family scope with TAT-C window)
MFE_MAX = 0.0020    # 0.20% unleveraged


def load_trades(cur, days, signal):
    cur.execute("""
        SELECT id, token, direction, amount_usdt, entry_price, pnl_usdt, exit_reason,
               open_time, close_time, signal, volatility_regime, confidence
        FROM trades
        WHERE status='closed' AND signal=%s
          AND close_time > NOW() - INTERVAL %s
          AND pnl_usdt IS NOT NULL AND entry_price IS NOT NULL
    """, (signal, f'{days} days'))
    return cur.fetchall()


def eval_trade(con, token, ot, ct, entry, direction, amount, tmin=T_MIN, mfe_max=MFE_MAX):
    """Returns None (not eligible), or (mfe_pct, cf_pnl, actual_pnl_unused_flag)."""
    hold_m = (ct - ot).total_seconds() / 60
    if hold_m < tmin:
        return None  # closed before the check window -> policy never fires
    t_cut = ot + dt.timedelta(minutes=tmin)
    cur = con.cursor()
    cur.execute(
        "SELECT ts, high, low, close FROM candles_1m WHERE token=? AND ts>=? AND ts<=? ORDER BY ts",
        # upper bound = t_cut itself. t_cut+60 admits the NEXT 1m candle, whose high/low
        # is entirely AFTER the cut -> MFE inflated -> fire wrongly downgraded to no_fire
        # (bug_hunter HIGH). The candle containing t_cut (ts=floor(t_cut)) stays in.
        (token, int(ot.timestamp()) // 60 * 60 - 60, int(t_cut.timestamp())))
    raw = cur.fetchall()
    cur.close()
    rows = [(ts, hi, lo, cl) for ts, hi, lo, cl in raw
            if ts >= int(ot.timestamp())]
    if not rows:
        return 'no_candles', None, None
    e = float(entry)
    if direction == 'LONG':
        mfe = (max(float(r[1]) for r in rows) / e - 1.0)
    else:
        mfe = (1.0 - min(float(r[2]) for r in rows) / e)
    if mfe >= mfe_max:
        return 'no_fire', None, None   # had momentum -> policy holds
    # exit at 1m close at/just before t_cut
    px = None
    for ts, hi, lo, cl in rows:
        if ts <= int(t_cut.timestamp()):
            px = float(cl)
    if px is None:
        return 'no_candles', None, None
    move = (px - e) / e * 100 if direction == 'LONG' else (e - px) / e * 100
    cf = float(amount) * move / 100
    return 'fire', mfe * 100, cf


def run(signal='bb-bounce-v2-long+', days_list=(7, 14, 30)):
    pg = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
    candles = sqlite3.connect('/root/.hermes/data/candles.db')
    out = {}
    try:
        cur = pg.cursor()
        all_tr = load_trades(cur, max(days_list), signal)
        cur.close()
        now = dt.datetime.now(dt.UTC).replace(tzinfo=None)
        for days in days_list:
            cutoff = now - dt.timedelta(days=days)
            trades = [t for t in all_tr if t[8] > cutoff]
            fires = 0
            save = harm = 0.0
            killed_winners = saved_losers = 0
            cohort = cohort_winners = all_winners = 0
            nocandle = 0
            detail = []
            for (tid, token, direction, amount, entry, pnl, exitr, ot, ct, sig, vol, conf) in trades:
                pnl = float(pnl)
                if pnl > 0:
                    all_winners += 1
                res_ = eval_trade(candles, token, ot, ct, entry, direction, amount)
                if res_ is None:
                    continue  # closed before T -> policy cannot fire
                status, mfe, cf = res_
                if status == 'no_candles':
                    nocandle += 1
                    continue
                cohort += 1  # open at T with candle data -> policy could have fired
                if pnl > 0:
                    cohort_winners += 1
                if status == 'no_fire':
                    continue
                fires += 1
                delta = cf - pnl
                # save/harm are the DELTA (true improvement), so save+harm == net
                # (bar the pnl==0 rows). Old code credited the whole pnl -> overstates.
                if pnl < 0 and delta > 0:
                    save += delta
                    saved_losers += 1
                elif pnl > 0 and delta < 0:
                    harm += delta  # negative
                    killed_winners += 1
                detail.append(dict(trade=tid, token=token, mfe=round(mfe, 3), cf=round(cf, 3),
                                   actual=round(pnl, 3), delta=round(delta, 3), exit=exitr))
            net = sum(d['delta'] for d in detail)
            out[days] = dict(n=len(trades), no_candles=nocandle, cohort=cohort, fired=fires,
                             saved_losers=saved_losers, killed_winners=killed_winners,
                             gross_save=round(save, 2), gross_harm=round(harm, 2),
                             net=round(net, 2),
                             # HOUSE BAR: fk as % of COHORT winners (open at T, could fire),
                             # not all window winners — the dilute denominator always reads lower.
                             winner_kill_pct=round(100.0 * killed_winners / cohort_winners, 1)
                                             if cohort_winners else 0.0,
                             winner_kill_all_pct=round(100.0 * killed_winners / all_winners, 1)
                                                 if all_winners else 0.0,
                             cohort_winners=cohort_winners, detail=detail)
    finally:
        pg.close()
        candles.close()
    return out


def selfcheck():
    con = sqlite3.connect(':memory:')
    con.execute("CREATE TABLE candles_1m (token TEXT, ts INT, high REAL, low REAL, close REAL)")
    # 60m of flat candles, never reaching +0.20% -> fire; exit price known
    base = 1000000
    rows = [('T', base + i * 60, 100.1, 99.9, 100.0) for i in range(60)]
    con.executemany("INSERT INTO candles_1m VALUES (?,?,?,?,?)", rows)
    ot = dt.datetime.fromtimestamp(base, dt.UTC).replace(tzinfo=None)
    ct = ot + dt.timedelta(minutes=90)
    st, mfe, cf = eval_trade(con, 'T', ot, ct, 100.0, 'LONG', 10.0)
    assert st == 'fire' and abs(mfe - 0.1) < 1e-6, (st, mfe)
    assert abs(cf - 0.0) < 1e-9, cf  # exit at flat 100.0 -> 0 move
    # momentum case -> no_fire
    rows2 = [('T2', base + i * 60, 100.5, 99.9, 100.4) for i in range(60)]
    con.executemany("INSERT INTO candles_1m VALUES (?,?,?,?,?)", rows2)
    st, mfe, cf = eval_trade(con, 'T2', ot, ct, 100.0, 'LONG', 10.0)
    assert st == 'no_fire', (st, mfe)
    # candle AFTER the T=55m cut must not feed MFE (bug_hunter HIGH): spike only
    # happens after the cut -> policy still fires. Old bound (t_cut+60) said no_fire.
    rows3 = [('T4', base + i * 60, 100.1, 99.9, 100.0) for i in range(56)]
    rows3.append(('T4', base + 56 * 60, 100.6, 100.0, 100.5))
    con.executemany("INSERT INTO candles_1m VALUES (?,?,?,?,?)", rows3)
    st, mfe, cf = eval_trade(con, 'T4', ot, ct, 100.0, 'LONG', 10.0)
    assert st == 'fire' and abs(mfe - 0.1) < 1e-6, (st, mfe)
    # SHORT direction: profit when price FALLS below entry
    rows4 = [('S1', base + i * 60, 100.1, 99.95, 99.98) for i in range(60)]
    con.executemany("INSERT INTO candles_1m VALUES (?,?,?,?,?)", rows4)
    st, mfe, cf = eval_trade(con, 'S1', ot, ct, 100.0, 'SHORT', 10.0)
    assert st == 'fire', (st, mfe)
    assert cf > 0, cf  # 100 -> 99.98 is +0.02% for a SHORT
    # closed before T -> None
    ct2 = ot + dt.timedelta(minutes=10)
    assert eval_trade(con, 'T', ot, ct2, 100.0, 'LONG', 10.0) is None
    con.close()
    print("selfcheck PASS: fire/no_fire/short-hold + post-cut candle excluded + SHORT direction")


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--selfcheck', action='store_true')
    ap.add_argument('--signal', default='bb-bounce-v2-long+')
    a = ap.parse_args()
    if a.selfcheck:
        selfcheck()
        sys.exit(0)
    res = run(signal=a.signal)
    for d, r in sorted(res.items()):
        print(f"=== {d}d {a.signal}: n={r['n']} no_candles={r['no_candles']} cohort={r['cohort']} "
              f"cohort_W={r['cohort_winners']} fired={r['fired']} "
              f"savedL={r['saved_losers']} (+{r['gross_save']}) killedW={r['killed_winners']} "
              f"({r['gross_harm']}) NET={r['net']} fk_cohort={r['winner_kill_pct']}% (HOUSE BAR <20%) "
              f"fk_all={r['winner_kill_all_pct']}% (diluted)")
        for x in r['detail']:
            print(f"    {x}")
