#!/usr/bin/env python3
"""
audit_own_mfe_mae.py — INDEPENDENT re-derivation of the MFE/MAE 8h claims
(own-conclusions audit, 2026-10-26). Written from scratch; deliberately does NOT
import or reuse analysis/mfe_mae_8h.py.

Cohort: last 100 closed trades in brain PG, open_time DESC, 30d cap.

Independent definitional choices (documented so any divergence vs the original
report can be attributed):
  * Window W      = [open_epoch, open_epoch + 8h). A 1m candle belongs to W iff
                    its START ts satisfies o <= ts < o+8h (no candle may extend
                    past the window end; the original allowed ts == w1).
  * Primary series: 1m candles when 1m coverage >= 50%, else 5m. A "union of
                    1m+5m" variant is computed as well, plus a feed-agreement
                    check (5m extremes vs enclosing 1m extremes).
  * MFE/MAE       : LONG fav=(p-entry)/entry, adv=(entry-p)/entry, applied to
                    candle high/low. Standard.
  * MAE_to_peak   : adverse from window start through the peak. Two variants:
                    first-touch (stop at the FIRST candle attaining max fav —
                    matches the original) and last-touch (you ride between the
                    first and LAST candle attaining the max — the true max
                    drawdown endured while "riding to the peak"). Both reported.
  * fav_after     : best favorable among candles that START at or after the
                    exit minute CEILed to the next full minute — this EXCLUDES
                    the candle straddling the exit (strict "after exit"). The
                    original truncates the exit time to seconds, which keeps the
                    straddling candle (up to 5 min of pre-exit price action for
                    5m candles) — computed as the "loose" variant for contrast.
  * stop distance: two variants — stop_loss column at close (what the original
                    used; CONTAMINATED by ATR/profit trailing rewrites) and
                    sl_distance column (the initial SL% at open).
  * Dollars       : amount_usdt verified to be NOTIONAL (pnl_usdt ~= price move
                    x amount_usdt across the cohort; pnl_pct = move x leverage).
"""
import os
import sys
import math
import sqlite3
import datetime as dt

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts'))
from paths import HERMES_DATA  # noqa: E402

import psycopg2  # noqa: E402
from _secrets import BRAIN_DB_DICT  # noqa: E402

WIN_S = 8 * 3600
N_TRADES = 100
from hermes_constants import CUT_LOSER_PNL  # live value (review MED-1 2026-10-27: was hardcoded 4.0, stale after coupled trial)
CUT_LOSER_ACCT_PCT = abs(CUT_LOSER_PNL)          # % account
COV_MIN = 0.50


# ────────────────────────────── data loading ─────────────────────────────────

def epoch(t):
    """Naive DB timestamp (UTC on this box) -> int epoch seconds."""
    if t.tzinfo is None:
        t = t.replace(tzinfo=dt.timezone.utc)
    return int(t.timestamp())


def load_trades():
    conn = psycopg2.connect(**BRAIN_DB_DICT)
    cur = conn.cursor()
    cur.execute(
        """SELECT id, token, direction, entry_price, exit_price, open_time,
                  close_time, leverage, pnl_pct, pnl_usdt, amount_usdt,
                  exit_reason, stop_loss, sl_distance, atr_managed
           FROM (
             SELECT * FROM trades
             WHERE status = 'closed' AND entry_price > 0 AND exit_price > 0
               AND open_time > NOW() - INTERVAL '30 days'
             ORDER BY open_time DESC LIMIT 100) q
           ORDER BY open_time ASC""")
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return rows


def load_candles(conn, token, t0, t1, minutes):
    """Closed candles of `minutes` granularity with start ts in [t0, t1)."""
    table = f"candles_{minutes}m"
    step = minutes * 60
    cur = conn.cursor()
    cur.execute(
        f"SELECT ts, high, low FROM {table} "
        f"WHERE token = ? AND ts >= ? AND ts < ? AND is_closed = 1 ORDER BY ts",
        (token, t0, t1))
    rows = cur.fetchall()
    cur.close()
    return rows  # (ts, high, low)


# ─────────────────────────── per-trade analysis ──────────────────────────────

def analyze(tr, sq):
    tok = tr['token']
    d = tr['direction'].upper()
    entry = float(tr['entry_price'])
    o = epoch(tr['open_time'])
    w = o + WIN_S
    exit_t = epoch(tr['close_time']) if tr['close_time'] else None
    in_win = exit_t is not None and exit_t <= w

    c1 = load_candles(sq, tok, o, w, 1)
    c5 = load_candles(sq, tok, o, w, 5)
    cov1 = len(c1) / (WIN_S // 60)
    cov5 = len(c5) / (WIN_S // 300)
    cov = max(cov1, cov5)
    if cov < COV_MIN:
        return {'ok': False, 'token': tok, 'dir': d, 'cov': cov,
                'n1': len(c1), 'n5': len(c5)}

    long_ = (d == 'LONG')

    def fav(p):
        return (p - entry) / entry if long_ else (entry - p) / entry

    def adv(p):
        return (entry - p) / entry if long_ else (p - entry) / entry

    def extremes(series):
        """-> (mfe, mae, first_peak_ts, last_peak_ts, mae_to_peak_first,
               mae_to_peak_last, mfe_ts_series)"""
        mfe = -9e9
        mae = -9e9
        for ts, hi, lo in series:
            f = max(fav(hi), fav(lo))
            a = max(adv(hi), adv(lo))
            if f > mfe:
                mfe = f
            if a > mae:
                mae = a
        if mfe <= -9e8:
            return None
        first_ts = None
        last_ts = None
        for ts, hi, lo in series:
            if max(fav(hi), fav(lo)) >= mfe - 1e-12:
                if first_ts is None:
                    first_ts = ts
                last_ts = ts
        mae_first = -9e9
        for ts, hi, lo in series:
            if ts > first_ts:
                break
            mae_first = max(mae_first, max(adv(hi), adv(lo)))
        mae_last = -9e9
        for ts, hi, lo in series:
            if ts > last_ts:
                break
            mae_last = max(mae_last, max(adv(hi), adv(lo)))
        return mfe, mae, first_ts, last_ts, mae_first, mae_last

    # primary = dominant series (1m when coverage allows)
    prim = c1 if cov1 >= COV_MIN else c5
    union = sorted(c1 + c5, key=lambda r: r[0])

    e_prim = extremes(prim)
    e_union = extremes(union)
    if e_prim is None or e_union is None:
        return {'ok': False, 'token': tok, 'dir': d, 'cov': cov,
                'n1': len(c1), 'n5': len(c5), 'reason': 'no extremes'}

    (mfe, mae, pk1, pkL, mae_pk_first, mae_pk_last) = e_prim
    (mfe_u, mae_u, _, _, mae_pk_first_u, _) = e_union

    # fav_after, two variants, on the primary series (and union for loose):
    fav_after_strict = None
    fav_after_loose = None
    adv_after_strict = None
    if in_win:
        # strict: candles starting at/after the NEXT full minute after exit
        ceil_t = int(math.ceil(exit_t / 60.0) * 60)
        floor_t = int(math.floor(exit_t / 60.0) * 60)
        for ts, hi, lo in prim:
            if ts >= ceil_t:
                v = max(fav(hi), fav(lo))
                fav_after_strict = max(fav_after_strict if fav_after_strict is not None else -9e9, v)
                av = max(adv(hi), adv(lo))
                adv_after_strict = max(adv_after_strict if adv_after_strict is not None else -9e9, av)
        for ts, hi, lo in union:
            if ts >= floor_t:  # original's truncation -> straddling candle kept
                fav_after_loose = max(fav_after_loose if fav_after_loose is not None else -9e9,
                                      max(fav(hi), fav(lo)))
        if fav_after_strict is None:
            fav_after_strict = 0.0
        if fav_after_loose is None:
            fav_after_loose = 0.0
        if adv_after_strict is None:
            adv_after_strict = 0.0

    fav_exit = None
    if in_win:
        fav_exit = fav(float(tr['exit_price']))

    lev = int(tr['leverage'] or 1)
    sl_close = abs(float(tr['stop_loss']) - entry) / entry * 100 if tr['stop_loss'] else None
    sl_init = float(tr['sl_distance']) * 100 if tr['sl_distance'] else None

    return {
        'ok': True, 'token': tok, 'dir': d, 'entry': entry,
        'open': tr['open_time'], 'close': tr['close_time'],
        'open_epoch': o, 'exit_epoch': exit_t, 'win_end': w,
        'lev': lev, 'amount': float(tr['amount_usdt'] or 0),
        'pnl_usdt': float(tr['pnl_usdt'] or 0),
        'pnl_pct': float(tr['pnl_pct'] or 0),
        'exit_reason': (tr['exit_reason'] or '?'),
        'cov1': cov1, 'cov5': cov5, 'cov': cov,
        'n1': len(c1), 'n5': len(c5),
        'mfe': mfe, 'mae': mae, 'mfe_u': mfe_u, 'mae_u': mae_u,
        'peak_ts': pk1, 'peak_ts_last': pkL,
        'mae_pk_first': mae_pk_first, 'mae_pk_last': mae_pk_last,
        'mae_pk_first_u': mae_pk_first_u,
        'fav_exit': fav_exit, 'in_win': in_win,
        'fav_after_strict': fav_after_strict, 'fav_after_loose': fav_after_loose,
        'adv_after_strict': adv_after_strict,
        'sl_close': sl_close, 'sl_init': sl_init,
        'atr_managed': bool(tr['atr_managed']),
    }


def q(sorted_list, p):
    """nearest-rank percentile, same convention as original for comparability."""
    if not sorted_list:
        return float('nan')
    i = min(len(sorted_list) - 1, int(p * len(sorted_list)))
    return sorted_list[i]


# ──────────────────────────────── main ───────────────────────────────────────

def main():
    trades = load_trades()
    # AUDIT_EXCLUDE="TOK1,TOK2" forces the same skips as the original run
    # (their candle coverage drifted up as the collector appended, so a
    # like-for-like comparison needs their exact 96-trade cohort).
    excl = {t.strip().upper() for t in os.environ.get('AUDIT_EXCLUDE', '').split(',') if t.strip()}
    if excl:
        before = len(trades)
        trades = [t for t in trades if t['token'].upper() not in excl]
        print(f"[matched mode] excluded {before - len(trades)} trades: {sorted(excl)}\n")
    # AUDIT_MIN_WINDOW_AGE_S=N: only trades opened >= N seconds ago, i.e. whose
    # full 8h window has elapsed (their run included partial windows; recency
    # truncates MFE/fav_after).
    min_age = int(os.environ.get('AUDIT_MIN_WINDOW_AGE_S', '0'))
    if min_age:
        now = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
        before = len(trades)
        trades = [t for t in trades
                  if (now - t['open_time']).total_seconds() >= min_age]
        print(f"[clean mode] dropped {before - len(trades)} trades with window "
              f"age < {min_age/3600:.1f}h\n")
    # AUDIT_SKIP_FIRST=N: the original run skipped the N OLDEST trades of the
    # last-100 (low-coverage DOT/BLUR/INJ/ALT); reproduce that cohort exactly.
    skip_first = int(os.environ.get('AUDIT_SKIP_FIRST', '0'))
    if skip_first:
        print(f"[matched mode] dropping the {skip_first} oldest trades "
              f"(original-run coverage skips)\n")
        trades = sorted(trades, key=lambda t: t['open_time'])[skip_first:]
    sq = sqlite3.connect(os.path.join(HERMES_DATA, 'candles.db'), timeout=15)
    res, skip = [], []
    for tr in trades:
        a = analyze(tr, sq)
        (res if a['ok'] else skip).append(a)
    sq.close()

    print(f"# INDEPENDENT AUDIT — last {len(trades)} closed trades, 8h window\n")
    print(f"analyzed={len(res)} skipped={len(skip)}")
    for s in skip:
        print(f"  SKIP {s['token']} {s['dir']} cov={s['cov']:.0%} "
              f"(1m={s.get('n1')} 5m={s.get('n5')})")
    covs = sorted(r['cov'] for r in res)
    print(f"coverage: min={covs[0]:.0%} p50={q(covs, .5):.0%} max={covs[-1]:.0%}")
    print(f"low-cov(<80%): {[(r['token'], round(r['cov'])) for r in res if r['cov'] < 0.8]}")

    # feed agreement: does a 5m candle ever show extremes beyond its 1m bucket?
    # (checks whether 'union' can invent extremes)
    import collections
    sq = sqlite3.connect(os.path.join(HERMES_DATA, 'candles.db'), timeout=15)
    disagreements = 0
    checked = 0
    for r in res:
        if r['cov1'] < 0.95:
            continue
        cur = sq.cursor()
        cur.execute("SELECT ts, high, low FROM candles_5m WHERE token=? AND ts>=? AND ts<? AND is_closed=1",
                    (r['token'], r['open_epoch'], r['win_end']))
        fives = cur.fetchall()
        cur.execute("SELECT ts, high, low FROM candles_1m WHERE token=? AND ts>=? AND ts<? AND is_closed=1",
                    (r['token'], r['open_epoch'], r['win_end']))
        ones = cur.fetchall()
        cur.close()
        for ts, hi, lo in fives:
            bucket = [(h, l) for t2, h, l in ones if ts <= t2 < ts + 300]
            if not bucket:
                continue
            checked += 1
            if hi > max(b[0] for b in bucket) * 1.0001 or lo < min(b[1] for b in bucket) * 0.9999:
                disagreements += 1
    sq.close()
    print(f"\nfeed agreement (5m extremes vs enclosing 1m): {disagreements}/{checked} disagree")

    # ── claim 1 extras: union vs primary differences ──
    diff_mfe = [r for r in res if abs(r['mfe'] - r['mfe_u']) > 1e-9]
    print(f"union-vs-primary MFE differences: {len(diff_mfe)} "
          f"(max diff {max((abs(r['mfe']-r['mfe_u']) for r in res), default=0)*100:.3f}pp)")

    # ── claim 5: exit census ──
    print("\n## Exit census (analyzed n=%d)" % len(res))
    reasons = {}
    for r in res:
        reasons.setdefault(r['exit_reason'], []).append(r)
    for k in sorted(reasons, key=lambda k: -len(reasons[k])):
        sub = reasons[k]
        wins = sum(1 for r in sub if r['pnl_usdt'] > 0)
        print(f"  {k:28s} n={len(sub):3d} win={wins:2d} pnl=${sum(r['pnl_usdt'] for r in sub):+.2f}")

    # ── claim 2 & 3: in-window exits, bigger-move ──
    exitable = [r for r in res if r['in_win'] and r['fav_exit'] is not None]
    held = [r for r in res if not r['in_win']]
    winners = [r for r in exitable if r['fav_exit'] >= 0]
    losers = [r for r in exitable if r['fav_exit'] < 0]
    win_net_pos = sum(1 for r in exitable if r['pnl_usdt'] > 0)
    print(f"\n## In-window exits n={len(exitable)} (held past 8h: {len(held)})")
    print(f"  price-based: profitable={len(winners)} negative={len(losers)}  "
          f"(net-USDT-based positive={win_net_pos})")

    for label, fa_key in (("STRICT (straddle candle excluded)", 'fav_after_strict'),
                          ("LOOSE  (original-style, straddle kept)", 'fav_after_loose')):
        print(f"  -- fav_after variant: {label}")
        for T in (0.2, 0.3, 0.5):
            early = [r for r in exitable
                     if r[fa_key] >= max(r['fav_exit'], 0.0) + T / 100.0]
            wl = sum(1 for r in early if r['fav_exit'] < 0)
            print(f"     T={T:.1f}pp: {len(early)}/{len(exitable)} "
                  f"({100*len(early)/len(exitable):.0f}%)  [winners {len(early)-wl}, losers {wl}]")

    # losers continuation and winners tail, strict (primary)
    print("  losers — post-exit continuation (strict):")
    for T in (0.3, 0.5, 1.0, 2.0):
        n = sum(1 for r in losers if r['fav_after_strict'] >= T / 100.0)
        nloose = sum(1 for r in losers if r['fav_after_loose'] >= T / 100.0)
        print(f"     fav_after >= {T:.1f}%: strict {n}/{len(losers)}  loose {nloose}/{len(losers)}")
    print("  winners — tail beyond capture (strict):")
    for T in (0.3, 0.5, 1.0):
        n = sum(1 for r in winners if r['fav_after_strict'] >= r['fav_exit'] + T / 100.0)
        nloose = sum(1 for r in winners if r['fav_after_loose'] >= r['fav_exit'] + T / 100.0)
        print(f"     fav_after >= cap+{T:.1f}pp: strict {n}/{len(winners)}  loose {nloose}/{len(winners)}")

    # by exit reason @T=0.3 strict
    T = 0.3
    early = [r for r in exitable if r['fav_after_strict'] >= max(r['fav_exit'], 0.0) + 0.003]
    print("  early-group by exit reason @T=0.3 (strict):")
    rc = {}
    for r in early:
        rc[r['exit_reason']] = rc.get(r['exit_reason'], 0) + 1
    for k in sorted(rc, key=lambda k: -rc[k]):
        print(f"     {k:28s} {rc[k]}")

    # ── claim 4: magnitude + dollars ──
    misses = sorted((r['fav_after_strict'] - r['fav_exit']) * 100 for r in early)
    print(f"\n  foregone magnitude (strict, n={len(early)}): "
          f"p50 {q(misses,.5):.2f}pp p75 {q(misses,.75):.2f}pp p90 {q(misses,.9):.2f}pp "
          f"max {misses[-1]:.2f}pp")
    forg = sum((r['fav_after_strict'] - r['fav_exit']) * r['amount'] for r in early)
    real = sum(r['pnl_usdt'] for r in early)
    print(f"  foregone gross ${forg:+.2f} vs realized net ${real:+.2f} -> gap ${forg-real:+.2f}")

    # notional check: pnl_usdt vs price-move x amount
    errs = []
    for r in res:
        if r['amount'] > 0 and r['fav_exit'] is not None:
            implied = r['fav_exit'] * r['amount']
            errs.append(abs(implied - r['pnl_usdt']))
    if errs:
        print(f"  notional check |pnl_usdt - fav_exit*amount|: median ${sorted(errs)[len(errs)//2]:.3f} "
              f"max ${max(errs):.3f} (small => amount_usdt is NOTIONAL)")

    # ── claim 6: MFE>=0.8 cohort ──
    coh = [r for r in res if r['mfe'] >= 0.008]
    print(f"\n## Big-MFE cohort (MFE>=0.8%): n={len(coh)}")
    mae_f = sorted(r['mae_pk_first'] * 100 for r in coh)
    mae_l = sorted(r['mae_pk_last'] * 100 for r in coh)
    print(f"  MAE_to_peak first-touch: p50 {q(mae_f,.5):.2f} p75 {q(mae_f,.75):.2f} "
          f"p90 {q(mae_f,.9):.2f} max {mae_f[-1]:.2f}")
    print(f"  MAE_to_peak last-touch : p50 {q(mae_l,.5):.2f} p75 {q(mae_l,.75):.2f} "
          f"p90 {q(mae_l,.9):.2f} max {mae_l[-1]:.2f}")
    slc = sorted(r['sl_close'] for r in coh if r['sl_close'] is not None)
    sli = sorted(r['sl_init'] for r in coh if r['sl_init'] is not None)
    print(f"  SL distance close-time (trailing-contaminated): p50 {q(slc,.5):.2f} "
          f"p75 {q(slc,.75):.2f} p90 {q(slc,.9):.2f} max {slc[-1]:.2f}")
    print(f"  SL distance initial (sl_distance col):          p50 {q(sli,.5):.2f} "
          f"p75 {q(sli,.75):.2f} p90 {q(sli,.9):.2f} max {sli[-1]:.2f}")
    n_atr = sum(1 for r in coh if r['atr_managed'])
    print(f"  atr_managed (SL rewritten during trade): {n_atr}/{len(coh)}")

    def kill_counts(sl_key, mae_key='mae_pk_first'):
        by_sl = set()
        by_hml = set()
        for i, r in enumerate(coh):
            mae_p = r[mae_key] * 100
            hml = CUT_LOSER_ACCT_PCT / r['lev']
            if r[sl_key] is not None and mae_p > r[sl_key]:
                by_sl.add(r['token'] + str(r['open_epoch']))
            if mae_p > hml:
                by_hml.add(r['token'] + str(r['open_epoch']))
        both = by_sl & by_hml
        union = by_sl | by_hml
        surv = len(coh) - len(union)
        # "first killer" attribution
        sl_first = 0
        hml_first = 0
        for r in coh:
            mae_p = r[mae_key] * 100
            hml = CUT_LOSER_ACCT_PCT / r['lev']
            sl = r[sl_key]
            if sl is None:
                if mae_p > hml:
                    hml_first += 1
                continue
            k_sl = mae_p > sl
            k_hml = mae_p > hml
            if k_sl and k_hml:
                if sl <= hml:
                    sl_first += 1
                else:
                    hml_first += 1
            elif k_sl:
                sl_first += 1
            elif k_hml:
                hml_first += 1
        print(f"  kills [{sl_key}/mae-first]: SL {len(by_sl)} HML {len(by_hml)} "
              f"overlap {len(both)} | SL-first {sl_first} HML-first {hml_first} "
              f"survivable {surv}/{len(coh)}")

    kill_counts('sl_close')
    kill_counts('sl_init')
    kill_counts('sl_close', 'mae_pk_last')
    kill_counts('sl_init', 'mae_pk_last')

    # ── claim 7: leverage math ──
    print("\n  HML max-leverage (4% acct / MAE price%):")
    for p in (0.5, 0.75, 0.9):
        m = q(mae_f, p)
        print(f"     MAE@p{int(p*100)}={m:.2f}% -> max lev {CUT_LOSER_ACCT_PCT/m:.1f}x")

    # ── claim 8: peak timing ──
    ttp = sorted((r['peak_ts'] - r['open_epoch']) / 60.0 for r in coh)
    print(f"\n  minutes open->peak: p50 {q(ttp,.5):.0f} p75 {q(ttp,.75):.0f} "
          f"p90 {q(ttp,.9):.0f} max {ttp[-1]:.0f}")

    # ── claim 9: scenario ──
    actual = sum(r['pnl_usdt'] for r in coh)
    print(f"\n  scenario (cohort n={len(coh)}, gross of fees):")
    print(f"    actual as traded (net): ${actual:+.2f}")
    for W in (0.8, 1.17, 1.62):
        out = []
        stops = 0
        for r in coh:
            if r['mae_pk_first'] * 100 <= W:
                out.append(r['mfe'] * r['amount'])
            else:
                out.append(-(W / 100.0) * r['amount'])
                stops += 1
        print(f"    SL={W:.2f}%: gross ${sum(out):+.2f} stops {stops}/{len(coh)} "
              f"worst ${min(out):+.2f}")
    # variant: last-touch MAE (more conservative stop triggering)
    print("  scenario variant (last-touch MAE):")
    for W in (0.8, 1.17, 1.62):
        out = []
        stops = 0
        for r in coh:
            if r['mae_pk_last'] * 100 <= W:
                out.append(r['mfe'] * r['amount'])
            else:
                out.append(-(W / 100.0) * r['amount'])
                stops += 1
        print(f"    SL={W:.2f}%: gross ${sum(out):+.2f} stops {stops}/{len(coh)}")

    # ── claim 11: split-half (strict & loose) ──
    ordered = sorted(exitable, key=lambda r: r['open_epoch'])
    half = len(ordered) // 2
    for name, part in (("older", ordered[:half]), ("newer", ordered[half:])):
        e_s = sum(1 for r in part if r['fav_after_strict'] >= max(r['fav_exit'], 0) + 0.003)
        e_l = sum(1 for r in part if r['fav_after_loose'] >= max(r['fav_exit'], 0) + 0.003)
        print(f"\n  split-half {name}: strict {e_s}/{len(part)}  loose {e_l}/{len(part)}")

    # ── claim 10: outliers — raw candle evidence ──
    print("\n## Outlier verification (raw candles)")
    sq = sqlite3.connect(os.path.join(HERMES_DATA, 'candles.db'), timeout=15)
    for tok, when, direction in (("GRASS", '2026-10-21 12:38', 'LONG'),
                                 ("WLD", '2026-10-23 14:36', 'SHORT')):
        cand = [r for r in res if r['token'] == tok
                and r['open'].strftime('%Y-%m-%d %H:%M') == when]
        if not cand:
            print(f"  {tok} {when}: NOT FOUND in cohort")
            continue
        r = cand[0]
        n1 = r['n1']
        # extremes with timestamps
        cur = sq.cursor()
        cur.execute("SELECT ts, high, low FROM candles_1m WHERE token=? AND ts>=? AND ts<? AND is_closed=1",
                    (tok, r['open_epoch'], r['win_end']))
        ones = cur.fetchall()
        cur.close()
        entry = r['entry']
        if direction == 'LONG':
            best = max(ones, key=lambda x: x[1])
            fav_best = (best[1] - entry) / entry * 100
            worst = min(ones, key=lambda x: x[2])
            adv_worst = (entry - worst[2]) / entry * 100
        else:
            best = min(ones, key=lambda x: x[2])
            fav_best = (entry - best[2]) / entry * 100
            worst = max(ones, key=lambda x: x[1])
            adv_worst = (worst[1] - entry) / entry * 100
        bt = dt.datetime.utcfromtimestamp(best[0]).strftime('%H:%M')
        wt = dt.datetime.utcfromtimestamp(worst[0]).strftime('%H:%M')
        # gap check: minutes missing
        tss = sorted(t for t, _, _ in ones)
        gaps = sum(1 for a, b in zip(tss, tss[1:]) if b - a > 60)
        print(f"  {tok} {when} {direction}: 1m candles={n1}/480 gaps>1m={gaps} "
              f"exit_in_win={r['in_win']} exit={r['close'].strftime('%H:%M')}")
        print(f"     MFE={r['mfe']*100:+.2f}% (best candle {bt} high/low) "
              f"MAE={r['mae']*100:.2f}% (worst {wt}) "
              f"fav_exit={r['fav_exit']*100:+.2f}% fav_after_strict={r['fav_after_strict']*100:+.2f}% "
              f"fav_after_loose={r['fav_after_loose']*100:+.2f}%")
    sq.close()

    # ── extra: exits BEFORE exit-minute vs the straddle-candle impact list ──
    changed = [r for r in exitable
               if (r['fav_after_loose'] - max(r['fav_exit'], 0) >= 0.003)
               != (r['fav_after_strict'] - max(r['fav_exit'], 0) >= 0.003)]
    print(f"\n  trades whose T=0.3 classification flips between loose/strict: {len(changed)}")
    for r in changed[:15]:
        print(f"     {r['open'].strftime('%m-%d %H:%M')} {r['token']:6s} {r['dir']:5s} "
              f"{r['exit_reason'][:20]:20s} cap={r['fav_exit']*100:+.2f}% "
              f"strict={r['fav_after_strict']*100:+.2f}% loose={r['fav_after_loose']*100:+.2f}%")

    print("\nDONE")


if __name__ == '__main__':
    main()
