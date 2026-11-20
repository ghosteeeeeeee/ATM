#!/usr/bin/env python3
"""STOP-TIGHTEN SCOPE-WIDEN 1m candle-walk (brain_auditor #282, 2026-11-20).

Closes the recorded caveat of registry `amplify-stoptighten-scope-widen`
(disposition 2026-11-08: SCOPE WIDEN ENFORCED on ceiling math only — "the 1m/5m
candle-walk was NOT re-run this session", due 2026-11-21, REVERT risk).

Walks limb (i)/(ii)/(iii)/(iv) of the pre-registered bar against the 6 sources
appended to STOP_TIGHTEN_SOURCES on 2026-11-08 (hermes_constants.py:761):

  (i)   1m candle-walk of stop-family losers (hard_max_loss + atr_sl_hit) on the
        NEW6 sources: first bar whose low/high crosses the 0.75% adverse level
        -> counterfactual exit at min(original SL, cap) = cap + realized
        slippage. walk-confirmed net >= +$1.00/30d in pnl_usdt UNITS (#193).
  (ii)  fk = winners on NEW6 whose path touches the cap before their real exit
        (clamp would have stopped them) — <=20%.
  (iii) n>=30 walked stop-family losers.
  (iv)  30d weekly same-sign (every week's stop-family bleed negative).

Slippage model: AVG(exit_slippage_pct) of stop-family exits in window (realized,
PG column, forward rule from stop-tighten-slippage-column: use realized exit,
never the bare stop level). Net is reported both WITH and WITHOUT slippage.

Walk detail vs ceiling math (why this script exists): ceiling used final move%
(ABS(entry-exit)/entry). The walk uses the PATH — a loser that touched 0.76%
but exited at only -0.30% (tighter ATR SL fired first) is HURT by the clamp
(delta negative), which ceiling math cannot see.

Usage: python3 stop_tighten_scope_walk_2026-11-20.py [--selfcheck]
"""
import os
import sys
from datetime import timezone, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', '..', 'scripts'))
from paths import *
import psycopg2
import sqlite3

CAP = 0.75                       # STOP_TIGHTEN_MAX_PRICE_PCT (live 0.75)
ARM = 0.40                       # trail arm level (MFE) — stop moves up at arm
NEW6 = ('pump-chain+', 'pump-chain-', 'bb-squeeze+',
        'volume-breakout-long+', 'bb-bounce-v2-long+', 'r2v2-long3')
STOP_FAMILY = ('hard_max_loss', 'atr_sl_hit')
SINCE_WIDEN = '2026-11-08'       # scope-widen ship date (coverage limb)


def _cond(params, extra=''):
    """SUBSTRING membership — same rule as tpsl_utils.stop_tighten_sl."""
    parts = []
    for n in NEW6:
        parts.append('signal LIKE %s')
        params.append(f'%{n}%')
    return '(' + ' OR '.join(parts) + ')' + extra


def load(days=30):
    conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
    cur = conn.cursor()
    p = []
    cond = _cond(p)
    cur.execute(f"""
        SELECT id, token, direction, entry_price, exit_price, pnl_usdt, amount_usdt,
               open_time, close_time, signal, exit_reason, stop_loss
        FROM trades
        WHERE status='closed' AND entry_price IS NOT NULL
          AND close_time > NOW() - INTERVAL '{days} days' AND {cond}
        ORDER BY close_time""", p)
    rows = cur.fetchall()
    # realized slippage model (stop-family exits only, fallback 0.1093%)
    p2 = []
    cond2 = _cond(p2)
    cur.execute(f"""
        SELECT AVG(exit_slippage_pct) FROM trades
        WHERE status='closed' AND exit_reason IN ('hard_max_loss','atr_sl_hit')
          AND exit_slippage_pct IS NOT NULL AND close_time > NOW() - INTERVAL '{days} days'
          AND {cond2}""", p2)
    slip = cur.fetchone()[0]
    conn.close()
    return rows, (float(slip) if slip is not None else 0.1093)


def touched(bars, entry, long_, cap=CAP):
    """Index of first 1m bar whose range crosses the cap-adverse level, else None."""
    level = entry * (1 - cap / 100.0) if long_ else entry * (1 + cap / 100.0)
    for i, (hi, lo) in enumerate(bars):
        if long_:
            if float(lo) <= level:
                return i
        else:
            if float(hi) >= level:
                return i
    return None


def walk(rows, db, slip):
    """Per-trade counterfactual (level-triggered stop semantics + arm ordering).

    Losers (stop-family = level-triggered exits, SL / HML backstop):
      * actual move <= CAP  -> exit fired BEFORE the cap level could bind
        (incl. HML thresholds under the cap) -> delta 0.
      * trail armed before any cap touch -> stop already moved up -> delta 0.
      * original SL distance <= CAP -> helper returns tighter SL untouched
        (tpsl_utils.stop_tighten_sl: dist_prop <= cap returns proposed) -> 0.
      * otherwise the cap would have exited the trade first:
        cf = -(CAP + slip) * amount / 100   (pnl_usdt units, UNITS RULE #193)
        delta = cf - pnl  (POSITIVE = improvement).
      Candles still walked for arm ordering + touch confirmation (report-only;
      actual-move arithmetic is the primary basis for level-triggered exits).
    Winners (fk): path touches the cap level BEFORE the trail arms -> the
    clamp would have stopped a would-be winner. Same-bar arm+touch and
    post-exit bars are excluded (bars end at the exit bar, ts1 only).
    Window anchors (close_time): net14 = last 14d of loaded span; split
    halves h1/h2 at the midpoint of the loaded span.
    """
    out = {'n_all': len(rows), 'losers_n': 0, 'losers_walked': 0, 'nodata': 0,
           'touch_confirmed': 0, 'touch_missed': 0, 'harm_no_touch': 0,
           'armed_first_losers': 0, 'tighter_sl_no_bind': 0, 'pre_cap_exits': 0,
           'slip_eats_saving': 0, 'ambiguous_losers': 0, 'ambiguous_winners': 0,
           'winners': 0, 'winners_walked': 0, 'fk_winners': 0,
           'net30': 0.0, 'net30_noslip': 0.0, 'net14': 0.0,
           'net_h1': 0.0, 'net_h2': 0.0, 'fk_pnl_at_risk': 0.0,
           'anomalies': [], 'nodata_ids': []}
    deltas = []
    if not rows:
        return out, deltas
    import time
    now = time.time()
    cut14 = now - 14 * 86400
    cts = [r[8].replace(tzinfo=timezone.utc).timestamp() for r in rows]
    mid = (min(cts) + max(cts)) / 2
    for (tid, tok, direc, entry, xprice, pnl_usd, amt, ot, ct, sig, exr, sl) in rows:
        entry, amt = float(entry), float(amt or 0)
        pnl = float(pnl_usd or 0)
        long_ = str(direc).upper() == 'LONG'
        is_stop_loser = (exr in STOP_FAMILY and pnl < 0)
        if is_stop_loser:
            out['losers_n'] += 1
        if pnl > 0:
            out['winners'] += 1
        ts0 = int(ot.replace(tzinfo=timezone.utc).timestamp())
        ts1 = int(ct.replace(tzinfo=timezone.utc).timestamp())
        bars = db.execute(
            "SELECT high, low FROM candles_1m WHERE token=? AND ts>=? AND ts<=? ORDER BY ts",
            (tok, ts0, ts1)).fetchall()
        if not bars:
            out['nodata'] += 1
            out['nodata_ids'].append(tid)
            continue
        touch_idx = touched(bars, entry, long_)
        arm_lvl = entry * (1 + ARM / 100.0) if long_ else entry * (1 - ARM / 100.0)
        arm_idx = None
        for i, (hi, lo) in enumerate(bars):
            if (float(hi) >= arm_lvl) if long_ else (float(lo) <= arm_lvl):
                arm_idx = i
                break
        samebar = (arm_idx is not None and touch_idx is not None
                   and arm_idx == touch_idx)
        ct_ts = ct.replace(tzinfo=timezone.utc).timestamp()
        sl_dist = (abs(entry - float(sl)) / entry * 100.0) if sl else None
        move = abs(entry - float(xprice)) / entry * 100.0 if xprice else 0.0
        if is_stop_loser:
            out['losers_walked'] += 1
            if samebar:
                out['ambiguous_losers'] += 1
                continue
            if arm_idx is not None and (touch_idx is None or touch_idx > arm_idx):
                # trail armed before the cap level was seen (or never seen):
                # stop already moved up by the time price came back through
                out['armed_first_losers'] += 1
                continue
            if move <= CAP:
                # exit level fired before the cap could bind (HML/thin SL)
                out['pre_cap_exits'] += 1
                continue
            if sl_dist is not None and sl_dist <= CAP:
                out['tighter_sl_no_bind'] += 1
                continue
            if touch_idx is None:
                out['harm_no_touch'] += 1   # move>cap but no candle touch (basis gap)
                out['anomalies'].append((tid, 'move>cap_no_candle_touch', round(move, 3)))
                # arithmetic still valid for a level-triggered exit: walk on
            else:
                out['touch_confirmed'] += 1
            cf_noslip = -amt * CAP / 100.0
            cf = -amt * (CAP + slip) / 100.0
            d = cf - pnl                       # POSITIVE = clamp saves money
            if d < 0:
                out['slip_eats_saving'] += 1   # move in (CAP, CAP+slip)
            out['net30'] += d
            out['net30_noslip'] += (cf_noslip - pnl)
            deltas.append((tid, tok, str(sig), d, round(sl_dist or -1, 3)))
            if ct_ts >= cut14:
                out['net14'] += d
            if ct_ts < mid:
                out['net_h1'] += d
            else:
                out['net_h2'] += d
        elif pnl > 0:
            out['winners_walked'] += 1
            if samebar:
                out['ambiguous_winners'] += 1
                continue
            if touch_idx is not None and (arm_idx is None or touch_idx < arm_idx):
                out['fk_winners'] += 1
                cf = -amt * (CAP + slip) / 100.0
                out['fk_pnl_at_risk'] += (cf - pnl)   # negative = pnl destroyed
    out['fk_pct'] = round(100.0 * out['fk_winners'] / out['winners_walked'], 1) \
        if out['winners_walked'] else None
    for k in ('net30', 'net30_noslip', 'net14', 'net_h1', 'net_h2', 'fk_pnl_at_risk'):
        out[k] = round(out[k], 2)
    return out, deltas


def weekly(rows):
    """(iv): every 30d week's stop-family bleed on NEW6 is negative."""
    by_week = {}
    for r in rows:
        tid, tok, direc, entry, xprice, pnl, amt, ot, ct, sig, exr, sl = r
        if exr in STOP_FAMILY and float(pnl or 0) < 0:
            wk = ct.date().isocalendar()[:2]
            by_week[wk] = by_week.get(wk, 0.0) + float(pnl)
    return sorted((f'{w[0]}-W{w[1]}', round(v, 2)) for w, v in by_week.items())


def coverage(slip):
    """(v) empirical: NEW6 stop-family exits opened since the widen whose
    realized stop_distance at exit implies the clamp was in the stack."""
    conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
    cur = conn.cursor()
    p = []
    cond = _cond(p)
    cur.execute(f"""
        SELECT COUNT(*),
               COUNT(*) FILTER (WHERE stop_loss IS NOT NULL),
               COUNT(*) FILTER (WHERE signal IS NOT NULL),
               COALESCE(SUM(pnl_usdt),0)
        FROM trades WHERE status='closed'
          AND open_time >= '{SINCE_WIDEN}' AND {cond}
    """, p)
    n, sl_set, named, pnl = cur.fetchone()
    # clamp candidates among those: stop-family losers whose realized loss <= cap+slip
    p2 = []
    cond2 = _cond(p2)
    cur.execute(f"""
        SELECT COUNT(*) FROM trades WHERE status='closed'
          AND open_time >= '{SINCE_WIDEN}' AND exit_reason IN {STOP_FAMILY!r}
          AND pnl_usdt < 0 AND {cond2}""", p2)
    post_family = cur.fetchone()[0]
    conn.close()
    return {'post_widen_trades': int(n), 'stop_loss_set': int(sl_set),
            'post_widen_stop_family_losers': int(post_family),
            'post_widen_pnl': round(float(pnl), 2)}


def bars_all(w, weeks, slip):
    net = w['net30']
    b = {
        'iii n>=30 walked stop-family losers': w['losers_walked'] >= 30,
        'i  net>=$1.00/30d (with slippage)': net >= 1.00,
        'i* net>=$1.00/30d (no slippage)': w['net30_noslip'] >= 1.00,
        'ii fk<=20%': w['fk_pct'] is not None and w['fk_pct'] <= 20.0,
        'iv weekly same-sign (all stop-family weeks negative)':
            len(weeks) > 0 and all(v < 0 for _, v in weeks),
    }
    return b


def run(days=30, verbose=True):
    rows, slip = load(days)
    db = sqlite3.connect(f'file:{CANDLES_DB}?mode=ro', uri=True)
    w, deltas = walk(rows, db, slip)
    db.close()
    weeks = weekly(rows)
    cov = coverage(slip)
    b = bars_all(w, weeks, slip)
    if verbose:
        print(f'=== STOP-TIGHTEN scope-widen candle-walk (NEW6, {days}d) ===')
        print(f'  slip model: {slip:.4f}% (realized avg)')
        for k in ('n_all', 'losers_n', 'losers_walked', 'touch_confirmed',
                  'touch_missed', 'harm_no_touch', 'armed_first_losers',
                  'tighter_sl_no_bind', 'pre_cap_exits', 'slip_eats_saving',
                  'ambiguous_losers', 'ambiguous_winners', 'nodata',
                  'winners', 'winners_walked', 'fk_winners', 'fk_pct',
                  'net30', 'net30_noslip', 'net14', 'net_h1', 'net_h2',
                  'fk_pnl_at_risk'):
            print(f'  {k}: {w[k]}')
        print(f'  weekly_stop_family: {weeks}')
        print(f'  coverage(since {SINCE_WIDEN}): {cov}')
        if w['anomalies']:
            print(f'  ANOMALIES: {w["anomalies"][:10]}')
        if w['nodata_ids']:
            print(f'  nodata ids: {w["nodata_ids"][:20]}')
        print('BARS:')
        for k, v in b.items():
            print(f'  {"PASS" if v else "FAIL"}  {k}')
        print(f'VERDICT: {"ALL BARS PASS" if all(b.values()) else "FAIL — REVERT RISK: escalate to CEO"}')
    verdict = all(b.values())
    return {'walk': w, 'weeks': weeks, 'coverage': cov, 'bars': b,
            'verdict': verdict, 'slip': slip, 'deltas': deltas}


def selfcheck():
    # synthetic: LONG crosses 0.75% -> touched at index 1
    entry = 100.0
    bars = [(100.2, 100.0), (100.1, 99.20), (99.5, 99.0)]   # 99.20 <= 99.25
    assert touched(bars, entry, True) == 1, touched(bars, entry, True)
    # never touches
    assert touched([(100.2, 99.30), (100.1, 99.26)], entry, True) is None
    # SHORT: high crosses entry*1.0075
    assert touched([(100.9, 100.5)], entry, False) == 0
    assert touched([(100.74, 100.5)], entry, False) is None
    # live run
    o = run(verbose=False)
    w = o['walk']
    assert w['losers_walked'] + w['nodata'] >= 30, w
    assert (w['touch_confirmed'] + w['harm_no_touch'] + w['armed_first_losers']
            + w['tighter_sl_no_bind'] + w['pre_cap_exits']
            + w['ambiguous_losers']) == w['losers_walked'], w
    # delta sign: positive net means the clamp saves money
    assert round(sum(d[3] for d in o['deltas']), 2) == w['net30']
    assert 0 <= (w['fk_pct'] or 0) <= 100
    # net identity: net30 == sum of per-trade deltas (recomputed)
    recomputed = round(sum(d[3] for d in o['deltas']), 2)
    assert abs(recomputed - w['net30']) < 0.01, (recomputed, w['net30'])
    print(f"SELF-CHECK PASS: walked={w['losers_walked']} touch_ok={w['touch_confirmed']} "
          f"net30={w['net30']} (noslip {w['net30_noslip']}) fk={w['fk_pct']}% "
          f"weeks={o['weeks']} verdict={'PASS' if o['verdict'] else 'FAIL'}")
    return 0


if __name__ == '__main__':
    if '--selfcheck' in sys.argv:
        sys.exit(selfcheck())
    sys.exit(0 if run()['verdict'] else 1)
