#!/usr/bin/env python3
"""ARMED-TRAIL-DISTANCE 1m replay — escalation #17 leg 2, pre-registered 2026-10-25 (#134).

POLICY UNDER TEST (single variable D):
    Once the trail arms (MFE >= ARM, default +0.40%), run a trailing stop D behind the
    running peak of favorable price. Exit at the first post-arm candle whose 1m CLOSE
    is through the floor. If the floor is never touched before the real close, the
    counterfactual keeps the ACTUAL exit -> delta 0 (no free information).

WHY THIS LEG: BE-at-arm (#134, leg 1) only pays when price round-trips all the way
back to ENTRY. The round-trip giveback ledger ceiling is +$8.28/14d vs BE's +$2.14/30d,
so most giveback never reaches entry — it dies on the way down at the leash distance.
The book runs two different leashes: TRAILING_DISTANCE_PCT = 1.20% (brain/HL) and
PM_TRAIL_DISTANCE_PCT = 0.20% (profit-monster, CEO-protected). The armed half sits on
the wider, asymmetric one. This sweeps D.

FILL VARIANT (house primary = CLOSE-through, matches the BE-at-arm verdict):
    close   1m close is through the floor  -> exit at that close  (conservative)
    floor   intrabar touch, fill AT floor  (optimistic stop-limit)
    worst   intrabar touch, fill at the extreme (stop-market gap; lower bound)

UNITS (AGENTS units rule): pnl_usdt = amount_usdt * price_move_fraction, unleveraged
on notional — identical formula both sides, so the DELTA is fee-neutral (same trade,
same round trip, only the exit print differs).

BARS (locked before running, pre-reg #134 + standing AGENTS p<0.05 rule):
    n>=20 AND net>0 AND both 15d halves>0 AND p<0.05 AND fk_armed<20%.

Self-check: python3 brain/analysis/trail_distance_oos_2026-10-25.py --selfcheck
"""
import sys, json, sqlite3, argparse, datetime as dt
import psycopg2

ARM_DEFAULT = 0.0040
DEFAULT_DISTS = (0.002, 0.003, 0.005, 0.008, 0.012, 0.016)  # 0.20 / 0.30 / 0.50 / 0.80 / 1.20 / 1.60 %


def load_trades(cur, days):
    cur.execute("""
        SELECT id, token, direction, amount_usdt, entry_price, exit_price, pnl_usdt,
               exit_reason, open_time, close_time, signal, volatility_regime,
               COALESCE(trailing_activation, %s), mfe_pct
        FROM trades
        WHERE status='closed' AND close_time > NOW() - INTERVAL '%d days'
          AND pnl_usdt IS NOT NULL AND entry_price IS NOT NULL
          AND amount_usdt IS NOT NULL AND open_time IS NOT NULL
    """ % (ARM_DEFAULT, days))
    return cur.fetchall()


def pnl_from(amount, entry, exitp, direction):
    """AGENTS units: pnl_usdt = amount_usdt * price_move_fraction, unleveraged on notional."""
    e, x = float(entry), float(exitp)
    frac = (x / e - 1.0) if direction == 'LONG' else (1.0 - x / e)
    return float(amount) * frac


def run(days_list=(7, 14, 30), dists=DEFAULT_DISTS, scoped=False, arm_on='high'):
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
                          if (t[11] or '') != 'EXTREME' and 'volume-' not in (t[10] or '').lower()]
            mid = cutoff + (now - cutoff) / 2
            n = len(trades)
            missing = armed_n = armed_winners = winners = 0
            V = {d: dict(fills=0, save=0.0, harm=0.0, saved_l=0, harmed_w=0, zeroed_w=0,
                         net=0.0, old=0.0, new=0.0, ds=[]) for d in dists}
            for (tid, token, direction, amt, entry, exitp, pnl, exitr, ot, ct, sig, vol, arm, mfe) in trades:
                pnl = float(pnl)
                if pnl > 0:
                    winners += 1
                armed, ats, res = _replay(candles, token, ot, ct, entry, direction, arm, dists, arm_on)
                if armed is None:
                    missing += 1
                    continue
                if armed:
                    armed_n += 1
                    if pnl > 0:
                        armed_winners += 1
                if not armed:
                    continue
                for d in dists:
                    ex = res.get(d)
                    if ex is None:
                        continue
                    cf_pnl = pnl_from(amt, entry, ex, direction)
                    delta = cf_pnl - pnl
                    v = V[d]
                    if pnl > 0 and cf_pnl <= 0:
                        v['zeroed_w'] += 1   # HOUSE fk: armed winners the policy turns non-positive
                    v['fills'] += 1
                    v['net'] += delta
                    v['ds'].append(delta)
                    if ct > mid:
                        v['new'] += delta
                    else:
                        v['old'] += delta
                    if delta < 0:
                        v['harm'] += -delta
                        if pnl > 0:
                            v['harmed_w'] += 1
                    else:
                        v['save'] += delta
                        if pnl < 0:
                            v['saved_l'] += 1
            var = {}
            for d in dists:
                v = V[d]
                ds = v['ds']
                if len(ds) > 1:
                    mu = sum(ds) / len(ds)
                    var_ = sum((x - mu) ** 2 for x in ds) / (len(ds) - 1)
                    t = mu / ((var_ / len(ds)) ** 0.5) if var_ > 0 else 0.0
                else:
                    t = 0.0
                try:
                    from scipy import stats
                    pval = round(float(2 * stats.t.sf(abs(t), len(ds) - 1)), 4) if len(ds) > 1 else 1.0
                except Exception:
                    pval = None
                var[d] = dict(fills=v['fills'], net=round(v['net'], 3), p=pval,
                              save=round(v['save'], 3), harm=round(v['harm'], 3),
                              saved_losers=v['saved_l'], harmed_winners=v['harmed_w'],
                              zeroed_winners=v['zeroed_w'],
                              fk_armed_pct=round(100.0 * v['harmed_w'] / armed_winners, 1) if armed_winners else 0.0,
                              fk_zeroed_pct=round(100.0 * v['zeroed_w'] / armed_winners, 1) if armed_winners else 0.0,
                              old_half=round(v['old'], 3), new_half=round(v['new'], 3),
                              t=round(t, 3))
            out[days] = dict(n=n, no_candles=missing, armed=armed_n, winners=winners,
                             armed_winners=armed_winners, variants=var)
    finally:
        pg.close()
        candles.close()
    return out


def _replay(con, token, open_ts, close_ts, entry, direction, arm, dists, arm_on='high'):
    """arm_on='high' -> arms on the 1m extreme (only a resting order sees this);
    arm_on='close'  -> arms on the 1m close (a poll-based sampler, e.g. PM_TRAIL,
    observes prices of this class — the sampling robustness test)."""
    cur = con.cursor()
    o = int(open_ts.timestamp())
    c = int(close_ts.timestamp())
    cur.execute(
        "SELECT ts, high, low, close FROM candles_1m WHERE token=? AND ts>=? AND ts<=? ORDER BY ts",
        (token, o // 60 * 60 - 60, c))
    rows = [r for r in cur.fetchall() if r[0] >= o]
    cur.close()
    if not rows:
        return None, None, {}
    thr = float(arm) if arm else ARM_DEFAULT
    ef = float(entry)
    long_ = direction == 'LONG'
    arm_ts = None
    for ts, hi, lo, cl in rows:
        px = float(cl) if arm_on == 'close' else (float(hi) if long_ else float(lo))
        if (px >= ef * (1 + thr)) if long_ else (px <= ef * (1 - thr)):
            arm_ts = ts
            break
    if arm_ts is None:
        return False, None, {}
    res = {d: None for d in dists}
    touch = {}
    peak = None
    for ts, hi, lo, cl in rows:
        if ts < arm_ts:
            continue
        fav = (float(hi) / ef - 1.0) if long_ else (1.0 - float(lo) / ef)
        peak = fav if peak is None else max(peak, fav)
        if ts == arm_ts:
            # peak STARTS at the arm candle's own extreme (a live trail locks from
            # peak-at-arm: floor = arm - D), but the trade cannot exit inside the
            # candle that armed it — same convention as be_at_arm_replay.
            continue
        for d in dists:
            if res[d] is not None:
                continue
            floor = ef * (1 + peak - d) if long_ else ef * (1 - (peak - d))
            if (float(cl) <= floor) if long_ else (float(cl) >= floor):
                res[d] = float(cl)            # house primary: close-through
            elif (float(lo) <= floor) if long_ else (float(hi) >= floor):
                touch[d] = floor              # recorded, not used for the bar
    for d, p in touch.items():
        if res[d] is None:
            res[d] = p                        # only fills if no close-through ever happens
    return True, arm_ts, res


def selfcheck():
    con = sqlite3.connect(':memory:')
    con.execute("CREATE TABLE candles_1m (token TEXT, ts INT, high REAL, low REAL, close REAL)")
    # LONG entry 100, arm at +0.40% on candle 1060 (high 100.5), then peak 100.8, then
    # a close through peak-0.30% (=100.5) at 1180, and a deep close at 1240.
    rows = [('T1', 1000, 100.2, 99.7, 99.9),    # pre-arm candle: must not arm (high < 100.4)
            ('T1', 1060, 100.5, 100.3, 100.4),  # arm candle
            ('T1', 1120, 100.8, 100.5, 100.7),  # peak 100.8, floor(d=0.30)=100.50 -> close 100.7 no
            ('T1', 1180, 100.7, 100.4, 100.45), # close 100.45 <= 100.5 -> close-through for 0.30
            ('T1', 1240, 100.6, 99.4, 99.5)]    # close-through for 1.20 (floor 99.6)
    con.executemany("INSERT INTO candles_1m VALUES (?,?,?,?,?)", rows)
    open_ts = dt.datetime.fromtimestamp(900, dt.UTC).replace(tzinfo=None)
    close_ts = dt.datetime.fromtimestamp(1300, dt.UTC).replace(tzinfo=None)
    armed, ats, res = _replay(con, 'T1', open_ts, close_ts, 100.0, 'LONG', 0.004, (0.003, 0.012, 0.005))
    assert armed is True and ats == 1060, (armed, ats)
    assert abs(res[0.003] - 100.45) < 1e-9, res          # 0.30% trail hit at 1180 close
    assert abs(res[0.012] - 99.5) < 1e-9, res            # 1.20% trail hit at 1240 close
    assert res[0.005] is not None and res[0.005] <= 100.45, res  # 0.50 floor=100.4 -> same candle
    # never-armed -> policy never applies
    armed, ats, res = _replay(con, 'T1', open_ts, close_ts, 100.0, 'LONG', 0.5, (0.003,))
    assert armed is False and ats is None, (armed, ats)
    # SHORT arm + touch: entry 100.4, arm when low <= 100.0, peak down to 99.0,
    # floor for d=0.30 = 100.4*(1-(0.1453-0.003))... use direct numbers below.
    con.execute("INSERT INTO candles_1m VALUES ('S1',1000,100.5,100.4,100.45)")
    con.execute("INSERT INTO candles_1m VALUES ('S1',1060,100.1,99.9,100.0)")   # arm
    con.execute("INSERT INTO candles_1m VALUES ('S1',1120,99.6,99.3,99.4)")     # peak fav 100.4/99.3-1
    # peak fav = 1-99.3/100.4 = 1.0956% -> floor for d=1.0% sits at 100.304; bounce must close >= it
    con.execute("INSERT INTO candles_1m VALUES ('S1',1180,100.4,99.7,100.35)")
    armed, ats, res = _replay(con, 'S1', open_ts, close_ts, 100.4, 'SHORT', 0.004, (0.010,))
    assert armed is True and ats == 1060, (armed, ats)
    assert abs(res[0.010] - 100.35) < 1e-9, res
    # no candles token -> (None, ...)
    assert _replay(con, 'NOPE', open_ts, close_ts, 100.0, 'LONG', 0.004, (0.003,))[0] is None
    # post-close candle must NOT arm or touch (bug_hunter HIGH class): bound is close_ts.
    con.execute("INSERT INTO candles_1m VALUES ('T3',1060,100.5,100.0,100.4)")
    con.execute("INSERT INTO candles_1m VALUES ('T3',1320,98.0,97.0,97.5)")   # ts > close_ts(1300)
    armed, ats, res = _replay(con, 'T3', open_ts, close_ts, 100.0, 'LONG', 0.004, (0.012,))
    assert armed is True and res[0.012] is None, (armed, res)
    # ...but an in-trade candle BEFORE close_ts must be able to trigger (1260 < 1300)
    con.execute("INSERT INTO candles_1m VALUES ('T4',1060,100.5,100.0,100.4)")
    con.execute("INSERT INTO candles_1m VALUES ('T4',1260,98.0,97.0,97.5)")
    armed, ats, res = _replay(con, 'T4', open_ts, close_ts, 100.0, 'LONG', 0.004, (0.012,))
    assert armed is True and abs(res[0.012] - 97.5) < 1e-9, (armed, res)
    # units rule: LONG 100 -> 101 on 1000 notional = +10; SHORT 100 -> 99 = +10
    assert abs(pnl_from(1000, 100.0, 101.0, 'LONG') - 10.0) < 1e-9
    assert abs(pnl_from(1000, 100.0, 99.0, 'SHORT') - 10.0) < 1e-9
    # probe the live DB that pnl_from reproduces stored pnl_usdt (units landmine guard)
    pg = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
    cur = pg.cursor()
    cur.execute("""SELECT amount_usdt, entry_price, exit_price, direction, pnl_usdt
                   FROM trades WHERE status='closed' AND pnl_usdt IS NOT NULL
                     AND entry_price IS NOT NULL AND exit_price IS NOT NULL
                   ORDER BY close_time DESC LIMIT 40""")
    rows = cur.fetchall()
    pg.close()
    errs, wrong = [], []
    for amt, e, x, d, p in rows:
        amt, e, x, p = float(amt), float(e), float(x), float(p)
        errs.append(abs(pnl_from(amt, e, x, d) - p))
        wrong.append(abs(pnl_from(amt, e, x, d) * 5 - p))   # leverage-scaled (the landmine)
    med = sorted(errs)[len(errs) // 2]
    med_wrong = sorted(wrong)[len(wrong) // 2]
    frac_ok = sum(1 for x in errs if x < 0.02) / len(errs)
    # 2 known outliers (BTC #16382/#16384, stored pnl 2x formula = notional/partial bookkeeping)
    assert med < 0.005 and frac_ok >= 0.90, f"pnl_from mismatch med={med:.4f} frac_ok={frac_ok}"
    assert med_wrong > 3 * med, f"units guard weak: lev-scaled med={med_wrong:.4f} vs {med:.4f}"
    con.close()
    print(f"selfcheck PASS: arm gate + close-through trail sweep + never-armed + post-close "
          f"excluded + SHORT + units rule (med_err {med:.4f}, {frac_ok:.0%} rows <0.02, "
          f"lev-scaled rejected med {med_wrong:.4f})")


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--selfcheck', action='store_true')
    ap.add_argument('--arm-close', action='store_true', help='arm on 1m CLOSE instead of HIGH (poll-sampler model)')
    ap.add_argument('--scoped', action='store_true',
                    help='non-EXTREME + exclude volume- (same scope as the 2026-10-17 ARM-BE verdict)')
    ap.add_argument('--dists', type=str, default=None, help='comma list in %% e.g. 0.2,0.3,1.2')
    a = ap.parse_args()
    if a.selfcheck:
        selfcheck()
        sys.exit(0)
    dists = tuple(float(x) / 100.0 for x in a.dists.split(',')) if a.dists else DEFAULT_DISTS
    res = run(scoped=a.scoped, dists=dists, arm_on='close' if a.arm_close else 'high')
    print(json.dumps(res, indent=1, default=str))
    for d, r in sorted(res.items()):
        aw = r['armed_winners']
        print(f"=== {d}d n={r['n']} no_candles={r['no_candles']} armed={r['armed']} armed_W={aw} "
              f"winners={r['winners']}")
        for dist, m in sorted(r['variants'].items()):
            verdict = []
            verdict.append('n>=20' if m['fills'] >= 20 else 'n FAIL')
            verdict.append('net>0' if m['net'] > 0 else 'net FAIL')
            verdict.append('halves>0' if (m['old_half'] > 0 and m['new_half'] > 0) else 'halves FAIL')
            verdict.append('fk<20' if m['fk_zeroed_pct'] < 20 else 'fk FAIL')
            if m.get('p') is not None:
                verdict.append('p<0.05' if m['p'] < 0.05 else 'p FAIL')
            print(f"   D={dist*100:.2f}%  fills={m['fills']:3d} NET {m['net']:+.3f} "
                  f"(save {m['save']:+.3f} / harm -{m['harm']:.3f}) "
                  f"savedL={m['saved_losers']} zeroedW={m['zeroed_winners']} dmgW={m['harmed_winners']} "
                  f"fk_zeroed={m['fk_zeroed_pct']}% (HOUSE <20%) fk_delta={m['fk_armed_pct']}%  "
                  f"halves old {m['old_half']:+.3f} new {m['new_half']:+.3f} "
                  f"t={m['t']} p={m.get('p')}  [{' | '.join(verdict)}]")
