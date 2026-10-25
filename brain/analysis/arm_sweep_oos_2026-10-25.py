#!/usr/bin/env python3
"""ARM-LINE SWEEP — 1m replay, single variable ARM (D fixed at the pre-registered 0.20%).

QUESTION
    #141 closed "lower-arm rescue" for the CHOP cohort only (hard_max_loss trades
    never reach +0.30%: 4/68 at 14d). It never measured the complementary slice —
    trades that DID move into [0.30,0.40) and gave it all back. Measured on PG:
        near-arm (0.30<=mfe<0.40): 7d 8T -0.36 | 14d 25T -1.95 | 30d 49T -3.33
    every window negative, n>=20 at 14d+30d. Those trades never arm, so no trail
    ever protects them; they ride to the stop. Does a lower ARM line pay for itself
    once you also count the harm done to trades that would be cut on the way up?

POLICY UNDER TEST (single variable ARM, D locked 0.20%)
    Arm when 1m high/low (arm_on='high') reaches entry*(1+/-ARM). From the arm
    candle on, run a D=0.20% trailing floor off the running peak; exit at the first
    post-arm 1m CLOSE through the floor. Trades that never reach ARM are untouched
    (delta 0 = no free information). Reproduces trail_distance_oos at ARM=0.004.

UNITS (AGENTS): pnl_usdt = amount_usdt * price_move_fraction both sides -> fee-neutral.

BARS (locked BEFORE running, pre-reg #134/#135 pattern + standing p<0.05 rule):
    fills n>=20 AND net>0 AND both 15d halves>0 AND p<0.05 AND fk_zeroed<20%
    AND same-sign at 14d and 30d AND net >= the ARM=0.40 baseline at the same D.

SCOPE: two populations are run — ALL TRADES, and the #135 scope the pending D=0.20
    GO ask was measured on (non-EXTREME, no volume-*). A ship requires the full bar
    set in BOTH; picking the scope that passes after seeing results is the pattern
    trap. all-trades executed first; --scoped run added afterwards, both reported.

PAIRED LEG (added after the first two runs — a STRICTER test, never a looser one):
    per-trade delta(ARM) - delta(0.40) on the trades where the two policies disagree,
    split into the older / newer half of the window. Absolute-policy p<0.05 alone
    does not ship a CHANGE: the current ARM=0.40 baseline itself passes 14d and fails
    30d unscoped, so a policy that "passes" can be inheriting the trend.

SHIP BAR for lowering ARM (locked before the paired run):
    1. paired diff > 0 at 7d, 14d AND 30d (same-sign, all three windows)
    2. paired full-window p<0.05 at 14d AND 30d
    3. paired older-half of 30d net > 0  (the half nobody tuned on)
    4. fk_zeroed < 20% at every window
    5. absolute-policy bars pass at 14d AND 30d in BOTH scopes
    fail any one -> REJECTED-WITH-DATA and the question is closed.

Self-check: python3 brain/analysis/arm_sweep_oos_2026-10-25.py --selfcheck
"""
import sys, os, json, sqlite3, importlib.util, datetime as dt
import psycopg2

HERE = os.path.dirname(os.path.abspath(__file__))
ARMS = (0.002, 0.003, 0.004, 0.005)   # 0.20 / 0.30 / 0.40 / 0.50 %
D = 0.002                              # pre-registered trail distance, NOT swept here


def _load_base():
    spec = importlib.util.spec_from_file_location(
        "tdist", os.path.join(HERE, "trail_distance_oos_2026-10-25.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _ttest(xs):
    if len(xs) > 1:
        mu = sum(xs) / len(xs)
        sv = sum((x - mu) ** 2 for x in xs) / (len(xs) - 1)
        t = mu / ((sv / len(xs)) ** 0.5) if sv > 0 else 0.0
        try:
            from scipy import stats
            pval = round(float(2 * stats.t.sf(abs(t), len(xs) - 1)), 4)
        except Exception:
            pval = None
    else:
        mu, t, pval = 0.0, 0.0, None
    return mu, t, pval


def paired_stats(pairs, base_a=0.004, mid=None):
    """Paired ARM-vs-current test on trades where the two policies disagree.

    diffs = delta(ARM) - delta(base); trades where both policies do the same thing
    are excluded (they add zeros, not evidence). When `mid` is given the diff is also
    split old/new, which is the out-of-sample leg (the newer half is what everyone
    looks at first; the older half is where a tuning artifact shows up).
    """
    out = {}
    for a in ARMS:
        if a == base_a:
            continue
        rows = [(d.get(a, 0.0) - d.get(base_a, 0.0), ct) for d, ct in pairs
                if abs(d.get(a, 0.0) - d.get(base_a, 0.0)) > 1e-12]
        diffs = [r[0] for r in rows]
        mu, t, pval = _ttest(diffs)
        rec = dict(n=len(diffs), mean_diff=round(mu, 4),
                   total=round(sum(diffs), 3), t=round(t, 3), p=pval)
        if mid is not None:
            old = [r[0] for r in rows if r[1] <= mid]
            new = [r[0] for r in rows if r[1] > mid]
            mo, to, po = _ttest(old)
            mn, tn, pn = _ttest(new)
            rec.update(old_n=len(old), old_total=round(sum(old), 3), old_p=po,
                       new_n=len(new), new_total=round(sum(new), 3), new_p=pn)
        out[a] = rec
    return out


def run(days_list=(7, 14, 30), arm_on='high', scoped=False):
    mod = _load_base()
    pg = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
    candles = sqlite3.connect('/root/.hermes/data/candles.db')
    out = {}
    try:
        cur = pg.cursor()
        all_tr = mod.load_trades(cur, max(days_list))
        cur.close()
        now = dt.datetime.now(dt.UTC).replace(tzinfo=None)
        for days in days_list:
            cutoff = now - dt.timedelta(days=days)
            trades = [t for t in all_tr if t[9] > cutoff]
            if scoped:
                # same scope trail_distance_oos published its D=0.20 GO numbers on (#135)
                trades = [t for t in trades
                          if (t[11] or '') != 'EXTREME' and 'volume-' not in (t[10] or '').lower()]
            mid = cutoff + (now - cutoff) / 2
            winners = sum(1 for t in trades if float(t[6]) > 0)
            V = {a: dict(fills=0, save=0.0, harm=0.0, saved_l=0, harmed_w=0,
                         zeroed_w=0, net=0.0, old=0.0, new=0.0, ds=[]) for a in ARMS}
            pairs = []          # per-trade {arm: delta} for the paired ARM-vs-0.40 test
            armed_n = {a: 0 for a in ARMS}
            armed_win = {a: 0 for a in ARMS}
            missing = 0
            for (tid, token, direction, amt, entry, exitp, pnl, exitr, ot, ct,
                 sig, vol, arm_db, mfe) in trades:
                pnl = float(pnl)
                pdelta = {}
                for a in ARMS:
                    armed, ats, res = mod._replay(candles, token, ot, ct, entry,
                                                  direction, a, (D,), arm_on)
                    if armed is None:
                        if a == ARMS[0]:
                            missing += 1
                        continue
                    if not armed:
                        continue
                    armed_n[a] += 1
                    if pnl > 0:
                        armed_win[a] += 1
                    ex = res.get(D)
                    if ex is None:
                        continue
                    cf = mod.pnl_from(amt, entry, ex, direction)
                    delta = cf - pnl
                    pdelta[a] = delta
                    v = V[a]
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
                    if pnl > 0 and cf <= 0:
                        v['zeroed_w'] += 1
                if pdelta:
                    pairs.append((pdelta, ct))
            paired = paired_stats(pairs, 0.004, mid)
            var = {}
            for a in ARMS:
                v, ds = V[a], V[a]['ds']
                if len(ds) > 1:
                    mu = sum(ds) / len(ds)
                    sv = sum((x - mu) ** 2 for x in ds) / (len(ds) - 1)
                    t = mu / ((sv / len(ds)) ** 0.5) if sv > 0 else 0.0
                else:
                    t = 0.0
                try:
                    from scipy import stats
                    pval = round(float(2 * stats.t.sf(abs(t), len(ds) - 1)), 4) if len(ds) > 1 else 1.0
                except Exception:
                    pval = None
                var[a] = dict(
                    fills=v['fills'], net=round(v['net'], 3), p=pval,
                    save=round(v['save'], 3), harm=round(v['harm'], 3),
                    saved_losers=v['saved_l'], harmed_winners=v['harmed_w'],
                    zeroed_winners=v['zeroed_w'],
                    fk_zeroed_pct=round(100.0 * v['zeroed_w'] / armed_win[a], 1) if armed_win[a] else 0.0,
                    fk_harmed_pct=round(100.0 * v['harmed_w'] / armed_win[a], 1) if armed_win[a] else 0.0,
                    old_half=round(v['old'], 3), new_half=round(v['new'], 3),
                    armed=armed_n[a], armed_winners=armed_win[a], t=round(t, 3))
            out[days] = dict(n=len(trades), no_candles=missing, winners=winners,
                             variants=var, paired=paired)
    finally:
        pg.close()
        candles.close()
    return out


def bars(res):
    """Apply the pre-locked bars per window/ARM. Baseline = ARM 0.004."""
    verdict = {}
    for days, blk in sorted(res.items()):
        base = blk['variants'].get(0.004, {}).get('net', 0.0)
        for a, v in blk['variants'].items():
            ok = (v['fills'] >= 20 and v['net'] > 0 and v['old_half'] > 0
                  and v['new_half'] > 0 and (v['p'] is not None and v['p'] < 0.05)
                  and v['fk_zeroed_pct'] < 20.0
                  and (days == 7 or v['net'] >= base))
            verdict[(days, a)] = dict(
                pass_all=bool(ok),
                checks=dict(n=v['fills'] >= 20, net=v['net'] > 0,
                            halves=v['old_half'] > 0 and v['new_half'] > 0,
                            p=(v['p'] is not None and v['p'] < 0.05),
                            fk=v['fk_zeroed_pct'] < 20.0,
                            beats_baseline=(days == 7 or v['net'] >= base)))
    return verdict


def ship_verdict():
    """Evaluate the locked SHIP BAR across BOTH scope runs (reads the two .out files)."""
    import json as _json
    res = {}
    for tag, fn in (('all', 'arm_sweep_oos_2026-10-25.out'),
                    ('scoped', 'arm_sweep_oos_2026-10-25_scoped.out')):
        path = os.path.join(HERE, fn)
        if not os.path.exists(path):
            print(f"MISSING {path} — run plain and --scoped first")
            return 1
        res[tag] = _json.load(open(path))['result']
    fails = []
    print("SHIP BAR (locked): lower ARM vs current 0.40%")
    for a in (0.002, 0.003, 0.005):
        if a == 0.004:
            continue
        print(f"\n-- ARM={a*100:.2f}% --")
        # 1+2: paired same-sign + p<0.05 at 14d/30d, per scope
        for scope in ('all', 'scoped'):
            blk = res[scope]
            pr = {d: blk[str(d)]['paired'].get(str(a)) for d in (7, 14, 30)}
            pr = {d: v for d, v in pr.items() if v}
            sign_ok = all(pr[d]['total'] > 0 for d in (7, 14, 30) if d in pr)
            p14 = pr.get(14, {}).get('p')
            p30 = pr.get(30, {}).get('p')
            p_ok = (p14 is not None and p14 < 0.05 and p30 is not None and p30 < 0.05)
            tot = ", ".join("%sd %+.3f" % (d, pr[d]['total']) for d in sorted(pr))
            print("  [%s] paired sign(7/14/30)=%s (%s)" %
                  (scope, 'OK' if sign_ok else 'FAIL', tot))
            print("           paired p14=%s p30=%s -> %s" %
                  (p14, p30, 'OK' if p_ok else 'FAIL'))
            if not sign_ok:
                fails.append(f"ARM {a} paired sign {scope}")
            if not p_ok:
                fails.append(f"ARM {a} paired p {scope}")
        # 3: older half of 30d
        for scope in ('all', 'scoped'):
            pr = res[scope]['30']['paired'].get(str(a))
            ok3 = bool(pr and pr.get('old_total', -1) > 0)
            if pr:
                print(f"  [{scope}] 30d OLD-half paired {pr.get('old_total'):+.3f} "
                      f"(n={pr.get('old_n')}) -> {'OK' if ok3 else 'FAIL'}")
            if not ok3:
                fails.append(f"ARM {a} old-half {scope}")
        # 4: fk
        fk_ok = all(res[sc][str(d)]['variants'][str(a)]['fk_zeroed_pct'] < 20.0
                    for sc in ('all', 'scoped') for d in (7, 14, 30))
        print(f"  fk_zeroed<20% all windows/scopes -> {'OK' if fk_ok else 'FAIL'}")
        if not fk_ok:
            fails.append(f"ARM {a} fk")
        # 5: absolute bars at 14d/30d in both scopes (JSON round-trips keys to str)
        ab_ok = True
        for sc in ('all', 'scoped'):
            norm = {}
            for d in (7, 14, 30):
                blk = dict(res[sc][str(d)])
                blk['variants'] = {float(k): v for k, v in blk['variants'].items()}
                norm[d] = blk
            v = bars(norm)
            for d in (14, 30):
                if not v[(d, a)]['pass_all']:
                    ab_ok = False
        print(f"  absolute bars 14d+30d, both scopes -> {'OK' if ab_ok else 'FAIL'}")
        if not ab_ok:
            fails.append(f"ARM {a} absolute")
        print(f"  => {'SHIP-ELIGIBLE' if not [f for f in fails if f.startswith(f'ARM {a} ')] else 'REJECTED'}")
    print("\nFAILURES:", fails if fails else "none")
    print("BASELINE SANITY (ARM=0.40 absolute bars, same test):")
    for sc in ('all', 'scoped'):
        norm = {}
        for d in (7, 14, 30):
            blk = dict(res[sc][str(d)])
            blk['variants'] = {float(k): v for k, v in blk['variants'].items()}
            norm[d] = blk
        v = bars(norm)
        print("  [%s] 14d=%s 30d=%s" % (sc, 'PASS' if v[(14, 0.004)]['pass_all'] else 'FAIL',
                                         'PASS' if v[(30, 0.004)]['pass_all'] else 'FAIL'))
    return 0 if not fails else 2


def selfcheck():
    """Fixture: trade arms only under a LOWER arm line and is then trailed out."""
    mod = _load_base()
    con = sqlite3.connect(':memory:')
    con.execute("CREATE TABLE candles_1m (token TEXT, ts INT, high REAL, low REAL, close REAL)")
    # LONG entry 100. Never reaches +0.40 (high 100.35 max), reaches +0.30 (100.30)
    # once, then falls back through peak-0.20 = 100.10.
    rows = [('T1', 1000, 100.10, 99.90, 100.00),
            ('T1', 1060, 100.30, 100.20, 100.25),   # arms at ARM=0.003, not at 0.004
            ('T1', 1120, 100.35, 100.28, 100.30),   # peak 0.35 -> floor(d=0.20)=100.15
            ('T1', 1180, 100.20, 100.05, 100.08),   # close 100.08 <= 100.15 -> exit
            ('T1', 1240, 100.30, 99.50, 99.60)]
    con.executemany("INSERT INTO candles_1m VALUES (?,?,?,?,?)", rows)
    ot = dt.datetime.fromtimestamp(900, dt.UTC).replace(tzinfo=None)
    ct = dt.datetime.fromtimestamp(1300, dt.UTC).replace(tzinfo=None)
    armed_hi, _, res_hi = mod._replay(con, 'T1', ot, ct, 100.0, 'LONG', 0.003, (D,), 'high')
    armed_lo, _, res_lo = mod._replay(con, 'T1', ot, ct, 100.0, 'LONG', 0.004, (D,), 'high')
    assert armed_hi is True and res_hi[D] is not None and abs(res_hi[D] - 100.08) < 1e-9, res_hi
    assert armed_lo is False and res_lo.get(D) is None, (armed_lo, res_lo)
    # arms <= entry*(1-ARM) for SHORT
    con.execute("INSERT INTO candles_1m VALUES ('S1',1000,100.2,99.9,100.0)")
    con.execute("INSERT INTO candles_1m VALUES ('S1',1060,100.0,99.68,99.7)")   # low 99.68 = -0.32%
    con.execute("INSERT INTO candles_1m VALUES ('S1',1120,99.9,99.6,99.8)")
    con.execute("INSERT INTO candles_1m VALUES ('S1',1180,100.3,100.2,100.25)")
    a, _, r = mod._replay(con, 'S1', ot, ct, 100.0, 'SHORT', 0.003, (D,), 'high')
    assert a is True, a
    # bars() must fail an underpowered/no-p cell and pass a locked passing cell
    fake = {14: {'variants': {
        0.004: dict(fills=30, net=1.0, p=0.01, old_half=0.6, new_half=0.4, fk_zeroed_pct=5.0),
        0.003: dict(fills=30, net=1.5, p=0.01, old_half=0.9, new_half=0.6, fk_zeroed_pct=5.0),
        0.002: dict(fills=12, net=9.0, p=0.01, old_half=5.0, new_half=4.0, fk_zeroed_pct=5.0),
    }}}
    v = bars(fake)
    assert v[(14, 0.004)]['pass_all'] is True
    assert v[(14, 0.003)]['pass_all'] is True
    assert v[(14, 0.002)]['pass_all'] is False and v[(14, 0.002)]['checks']['n'] is False
    # paired_stats: identical policies -> n=0; a strictly better ARM -> positive total
    p0 = paired_stats([({0.003: 0.5, 0.004: 0.5}, 10), ({0.003: -0.1, 0.004: -0.1}, 20)])
    assert p0[0.003]['n'] == 0 and p0[0.003]['total'] == 0.0, p0
    p1 = paired_stats([({0.003: 0.30, 0.004: 0.10}, 10), ({0.003: 0.20, 0.004: -0.20}, 30),
                       ({0.003: 0.05, 0.004: -0.15}, 40)], 0.004, 20)
    assert p1[0.003]['old_total'] == 0.20 and p1[0.003]['new_total'] == 0.60, p1
    assert p1[0.003]['n'] == 3 and abs(p1[0.003]['total'] - 0.80) < 1e-9, p1
    assert p1[0.003]['mean_diff'] > 0, p1
    print("SELFCheck PASS: replay arms at lower ARM / not at higher, SHORT arm, "
          "bars() logic, paired_stats() zero-exclusion + sign")


if __name__ == '__main__':
    if '--selfcheck' in sys.argv:
        selfcheck()
        sys.exit(0)
    if '--verdict' in sys.argv:
        sys.exit(ship_verdict())
    scoped = '--scoped' in sys.argv
    res = run(scoped=scoped)
    verdict = bars(res)
    tag = 'SCOPED (non-EXTREME, no volume-*)' if scoped else 'ALL TRADES'
    print(f"ARM-LINE SWEEP [{tag}]  D={D*100:.2f}% (locked)  arm_on=high  bars: n>=20, net>0, "
          f"halves>0, p<0.05, fk_zeroed<20%, net>=baseline@0.40 (14d/30d)")
    for days in sorted(res):
        blk = res[days]
        print(f"\n=== {days}d n={blk['n']} winners={blk['winners']} no_candles={blk['no_candles']} ===")
        for a in ARMS:
            v = blk['variants'][a]
            vd = verdict[(days, a)]
            checks = ''.join(k[0].upper() if ok else '-' for k, ok in vd['checks'].items())
            print(f"  ARM={a*100:.2f}%  fills={v['fills']:4d} net={v['net']:+.3f} "
                  f"(save {v['save']:+.3f}/harm -{v['harm']:.3f}) savedL={v['saved_losers']} "
                  f"harmW={v['harmed_winners']} zeroedW={v['zeroed_winners']} "
                  f"fk_zeroed={v['fk_zeroed_pct']}% halves {v['old_half']:+.3f}/{v['new_half']:+.3f} "
                  f"t={v['t']:.3f} p={v['p']}  [{checks}] {'PASS' if vd['pass_all'] else 'FAIL'}")
        for a in sorted(blk.get('paired', {})):
            pr = blk['paired'][a]
            line = (f"    paired ARM={a*100:.2f}% vs 0.40%: n={pr['n']} "
                    f"mean={pr['mean_diff']:+.4f} total={pr['total']:+.3f} p={pr['p']}")
            if 'old_total' in pr:
                line += (f" | OLD(old-half OOS) n={pr['old_n']} {pr['old_total']:+.3f} "
                         f"p={pr['old_p']} | NEW {pr['new_n']} {pr['new_total']:+.3f} "
                         f"p={pr['new_p']}")
            print(line)
    outp = os.path.join(HERE, 'arm_sweep_oos_2026-10-25%s.out' % ('_scoped' if scoped else ''))
    with open(outp, 'w') as f:
        json.dump({'scope': 'scoped' if scoped else 'all',
                   'result': {str(k): v for k, v in res.items()},
                   'verdict': {f"{k[0]}|{k[1]}": val for k, val in verdict.items()}},
                  f, indent=1)
    print("\nWrote", outp)
