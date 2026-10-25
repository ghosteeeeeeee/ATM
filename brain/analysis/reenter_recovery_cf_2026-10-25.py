#!/usr/bin/env python3
"""Re-enter-on-recovery counterfactual — pre-registered 2026-10-22 (#72), Oct-25 batch.

POLICY UNDER TEST
    After a losing trade closes, place a LIMIT re-entry at the ORIGINAL entry price
    in the ORIGINAL direction. It only fills if price trades back through entry
    (confirmation). Bracket = the trade's stop_loss/target AS STORED AT CLOSE —
    which for managed trades is the FINAL trailed/ATR stop, NOT the entry-time
    bracket (position_manager rewrites these columns while the trade is open, and
    _signal_metadata does not keep the entry-time values). That biases losses low
    on managed-bracket trades, so results are reported for BOTH the full set and a
    RAW-bracket scope (exit_reason not at a manager-moved stop) and the VERDICT
    requires both scopes to pass. Walk 1m candles from the candle AFTER the fill
    candle; SL wins same-bar ties (conservative). Hold horizon is measured from the
    FILL bar, not from whichever bar happens to be next (gaps must not extend it).

    Trigger search window: 60m after the original close. Walk window: 60m after the
    re-entry fill. The candle CONTAINING close_time is skipped — its post-exit path
    is unknown, and using it would leak the exit print into the recovery test (the
    same class of bug as the open-anchored recovery vacuity, #85).

BASELINE = do nothing extra (0 pnl). The question is whether the ADDED round trip
has positive expectancy AFTER a full round-trip fee.

UNITS (AGENTS UNITS RULE): pnl_usdt = amount_usdt * price_move_pct / 100
(unleveraged on notional). Stored trades.pnl_usdt is GROSS of fees — verified
2026-10-25: fees JSON `net_pnl + fee_total` == pnl_usdt on 6/8 probe rows. The
counterfactual therefore reports BOTH gross and net-of-fee; BARS ARE JUDGED ON
NET-OF-FEE, because the re-entry is an extra round trip the book does not pay today.

BARS (locked pre-data, house rules)
    n_reentries >= 20
    net_after_fees > 0
    both 15d halves same sign (>0 each)
    p < 0.05 (standing AGENTS significance rule: two-sided t-test on per-trade
              net AND two-sided sign test — both must pass; this bar always
              applied, it is listed here so it cannot be dropped after the fact)
Baseline for an ADDED trade is 0, so fk (winner-kill) does not apply; the analog
— how often the re-entry ADDS a new loss — is (100% - WR) on the printed line.

Self-check: python3 brain/analysis/reenter_recovery_cf_2026-10-25.py --selfcheck
"""
import datetime as dt
import json
import sqlite3
import sys

import psycopg2

CANDLES = '/root/.hermes/data/candles.db'
FEE_RATE = 0.00045          # per side, TAKER_FEE (position_manager.py:1168)
TRIGGER_HORIZON_S = 3600    # recovery must be seen within 60m of the exit
WALK_HORIZON_S = 3600       # re-entry held at most 60m


# ---------------------------------------------------------------- pure helpers
def find_trigger(bars, entry, direction, mode):
    """Index of the first bar that trades back through `entry`, else None.

    mode='through'       : bar spans entry (low <= E <= high)
    mode='through_close' : spans entry AND closes on the recovery side
                           (LONG: close >= E, SHORT: close <= E)
    Caller must have already dropped the bar containing the exit print.
    """
    long_ = direction == 'LONG'
    for i, (ts, o, h, l, c) in enumerate(bars):
        if not (l <= entry <= h):
            continue
        if mode == 'through':
            return i
        if (c >= entry) if long_ else (c <= entry):
            return i
    return None


def walk(bars, entry, direction, sl, tp, start_idx, horizon_s, anchor_ts=None):
    """Walk from bars[start_idx] for horizon_s after `anchor_ts`. SL wins ties.

    Returns (kind, exit_price, exit_ts) with kind in {'sl', 'tp', 'timeout'}.
    Path starts at the fill-bar's NEXT bar: the intra-bar path between the
    fill at `entry` and that bar's close is unknowable, so BOTH the first
    favourable and first adverse move of the fill bar are ignored (symmetric).

    anchor_ts defaults to the first walked bar, but the caller MUST pass the FILL
    bar's ts: anchoring on whatever bar comes next lets a candle gap silently
    stretch a 60m hold to 70m (code review MED, 2026-10-25).
    """
    long_ = direction == 'LONG'
    if start_idx >= len(bars):
        raise IndexError('walk: start_idx past end (caller must pre-check)')
    anchor = anchor_ts if anchor_ts is not None else bars[start_idx][0]
    last_close = float(bars[start_idx][4])
    last_ts = bars[start_idx][0]
    for ts, o, h, l, c in bars[start_idx:]:
        if ts > anchor + horizon_s:
            break
        last_close, last_ts = float(c), ts
        if long_:
            if l <= sl:                       # adverse first
                return 'sl', float(sl), ts
            if h >= tp:
                return 'tp', float(tp), ts
        else:
            if h >= sl:
                return 'sl', float(sl), ts
            if l <= tp:
                return 'tp', float(tp), ts
    return 'timeout', last_close, last_ts


def fee_for(fees_json):
    """Round-trip fee in USDT from the trade's own record; None if unavailable.

    A recorded fee_total of 0.0 is a real value and must NOT fall through to the
    estimate (code review LOW, 2026-10-25).
    """
    if fees_json:
        try:
            v = json.loads(fees_json).get('fee_total')
            if v is not None:
                return float(v)
        except Exception:
            pass
    return None


def gross_pnl(amount, entry, exit_px, direction):
    move = (exit_px - entry) / entry * 100.0
    if direction == 'SHORT':
        move = -move
    return amount * move / 100.0


# ------------------------------------------------------------------ simulation
def simulate(con, token, close_ts, entry, direction, sl, tp, mode):
    """Returns dict or None (no data / invalid bracket)."""
    cur = con.cursor()
    try:
        # skip the bar containing close_time: floor + one minute
        first_ts = (int(close_ts.timestamp()) // 60) * 60 + 60
        last_ts = int(close_ts.timestamp()) + TRIGGER_HORIZON_S + WALK_HORIZON_S + 120
        cur.execute(
            'SELECT ts, open, high, low, close FROM candles_1m '
            'WHERE token=? AND ts>=? AND ts<=? AND is_closed=1 ORDER BY ts',
            (token, first_ts, last_ts))
        bars = cur.fetchall()
    finally:
        cur.close()
    if not bars:
        return {'status': 'nodata'}
    # trigger only within 60m of the exit
    trig_win = [b for b in bars if b[0] <= first_ts - 60 + TRIGGER_HORIZON_S]
    if not trig_win:
        return {'status': 'nodata'}
    ti = find_trigger(trig_win, entry, direction, mode)
    if ti is None:
        return {'status': 'no_recovery'}
    fill_bar = trig_win[ti]
    # the walk starts at the bar after the fill bar, within the full fetched set
    after = [b for b in bars if b[0] > fill_bar[0]]
    if not after:
        return {'status': 'nodata'}
    kind, exit_px, exit_ts = walk(after, entry, direction, sl, tp, 0,
                                  WALK_HORIZON_S, anchor_ts=fill_bar[0])
    return {
        'status': 'simulated',
        'fill_ts': fill_bar[0],
        'exit_kind': kind,
        'exit_price': exit_px,
        'exit_ts': exit_ts,
        'hold_min': (exit_ts - fill_bar[0]) / 60.0,
    }


def load_candidates(days):
    conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, token, direction, amount_usdt, entry_price, stop_loss, target,
                   close_time, exit_reason, signal, fees, pnl_usdt, volatility_regime
            FROM trades
            WHERE status='closed' AND pnl_usdt < 0
              AND close_time > NOW() - INTERVAL '%d days'
              AND entry_price IS NOT NULL AND stop_loss IS NOT NULL AND target IS NOT NULL
              -- a trade closed <125m ago has an incomplete 60m trigger + 60m walk
              -- window; letting it in would score it as no_recovery / early timeout
              -- on truncated data (code review MED, 2026-10-25)
              AND close_time < NOW() - INTERVAL '125 minutes'
            ORDER BY close_time
        """ % int(days))
        rows = cur.fetchall()
        cur.close()
        return rows
    finally:
        conn.close()


def bracket_ok(entry, direction, sl, tp):
    if direction == 'LONG':
        return sl < entry < tp
    return sl > entry > tp


def near_touch_rate(rows, con, window=TRIGGER_HORIZON_S):
    """Fill-rate of the LOOSER +-0.2%-of-entry convention used by recovery_replay,
    reported ONLY to reconcile counts against the #72 census — not a policy
    candidate, because a limit order sitting AT entry cannot fill 0.2% away.

    ADVERSE-FIRST (same vacuity guard as recovery_replay #85): a bar must first
    put price beyond +-0.2%, and only a LATER bar reaching back counts. A bar
    that simply stays just under the band on the first poll is not a recovery.
    """
    hit = valid = never_adverse = nodata = 0
    for (tid, tok, direction, amount, entry, sl, tp, close_ts, exr, sig, fees, orig_pnl, vol) in rows:
        if not bracket_ok(float(entry), direction.upper(), float(sl), float(tp)):
            continue
        entry = float(entry)
        long_ = direction.upper() == 'LONG'
        thr = entry * 0.998 if long_ else entry * 1.002
        first_ts = (int(close_ts.timestamp()) // 60) * 60 + 60
        last_ts = first_ts - 60 + window
        cur = con.cursor()
        try:
            cur.execute('SELECT low, high FROM candles_1m WHERE token=? AND ts>=? AND ts<=? AND is_closed=1',
                        (tok, first_ts, last_ts))
            bars = cur.fetchall()
        finally:
            cur.close()
        if not bars:
            # a token missing from candles.db is a DATA gap, not a behaviour:
            # keep it out of the denominator instead of blaming price action
            nodata += 1
            continue
        valid += 1
        if long_:
            adverse = [i for i, (lo, hi) in enumerate(bars) if lo < thr]
            if not adverse:
                never_adverse += 1
                continue
            i0 = adverse[0]
            if any(hi >= thr for lo, hi in bars[i0 + 1:]):
                hit += 1
        else:
            adverse = [i for i, (lo, hi) in enumerate(bars) if hi > thr]
            if not adverse:
                never_adverse += 1
                continue
            i0 = adverse[0]
            if any(lo <= thr for lo, hi in bars[i0 + 1:]):
                hit += 1
    return hit, valid, never_adverse, nodata


# exit_reasons whose stored stop was MOVED by position_manager while the trade was
# open — their as-stored bracket is tighter than the entry-time bracket the policy
# describes (code review HIGH, 2026-10-25). Reported as a separate scope.
MANAGED_STOP_EXITS = {
    'atr_sl_hit', 'atr_trail_hit', 'profit-monster-trail', 'trail_sl',
    'manual_trail_hit', 'rr_engine_trail_hit', 'atr_trail',
}


def scope_of(exit_reason):
    return 'managed' if exit_reason in MANAGED_STOP_EXITS else 'raw'


def report(days=30, mode='through_close'):
    # PG column is `timestamp without time zone` storing UTC; .timestamp() on a naive
    # datetime reads it in the HOST tz, so refuse to run anywhere but UTC (code
    # review LOW, 2026-10-25) — a tz shift would silently misalign every window.
    import time as _time
    assert _time.tzname[0] in ('UTC', 'GMT'), f'host tz must be UTC, got {_time.tzname}'
    rows = load_candidates(days)
    con = sqlite3.connect(CANDLES)
    now = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)   # naive UTC, matches PG
    half_cut = now - dt.timedelta(days=days / 2.0)

    res = []
    counts = {'nodata': 0, 'no_recovery': 0, 'bad_bracket': 0}
    for (tid, tok, direction, amount, entry, sl, tp, close_ts, exr, sig, fees, orig_pnl, vol) in rows:
        entry, sl, tp = float(entry), float(sl), float(tp)
        direction = direction.upper()
        if not bracket_ok(entry, direction, sl, tp):
            counts['bad_bracket'] += 1
            continue
        out = simulate(con, tok, close_ts, entry, direction, sl, tp, mode)
        if out['status'] != 'simulated':
            counts[out['status']] = counts.get(out['status'], 0) + 1
            continue
        g = gross_pnl(float(amount), entry, out['exit_price'], direction)
        ft = fee_for(fees)
        fee = ft if ft is not None else float(amount) * FEE_RATE * 2
        res.append({
            'id': tid, 'token': tok, 'direction': direction, 'signal': sig,
            'exit_reason': exr, 'vol': vol, 'amount': float(amount),
            'orig_pnl': float(orig_pnl), 'close_time': close_ts,
            'scope': scope_of(exr),
            'kind': out['exit_kind'], 'gross': g, 'fee': fee, 'net': g - fee,
            'hold_min': out['hold_min'], 'recovery_min': (out['fill_ts'] - int(close_ts.timestamp())) / 60.0,
        })
    hit, valid, never_adv, nt_nodata = near_touch_rate(rows, con)
    con.close()
    n = len(res)
    print(f'=== RE-ENTER-ON-RECOVERY CF ({days}d, mode={mode}) ===')
    print(f'losers with bracket: {len(rows)} | simulated: {n} | {counts}')
    if not n:
        return res, counts
    recovery_rate = 100.0 * n / max(len(rows) - counts.get('bad_bracket', 0), 1)
    print(f'recovery (fill) rate: {recovery_rate:.1f}% of valid-bracket losers '
          f'[{mode} = limit order AT entry]')
    loose = 100.0 * hit / max(valid, 1)
    repro = 'reproduces' if abs(loose - 71.0) < 5.0 else 'does NOT reproduce'
    print(f'  reconciliation vs #72 census premise (~71% "trade back through entry '
          f'within 60m"): +-0.2%-band adverse-first touch = {hit}/{valid} ({loose:.1f}%) '
          f'{repro}; never went +-0.2% adverse = {never_adv}; no candle data = {nt_nodata}. '
          f'A limit order AT entry only fills {recovery_rate:.1f}% of losers, so cite the '
          f'measurable fillable rate, not 71%.')

    def agg(label, sub):
        if not sub:
            return
        nn = len(sub)
        w = sum(1 for r in sub if r['net'] > 0)
        gross = sum(r['gross'] for r in sub)
        net = sum(r['net'] for r in sub)
        print(f'  {label:28s} n={nn:4d} WR={100.0*w/nn:5.1f}% gross={gross:+.3f} '
              f'net={net:+.3f} avg_net={net/nn:+.4f} '
              f'max_loss={min(r["net"] for r in sub):+.3f}')

    # ---- verdict machinery: run on the full set AND on the RAW-bracket scope, and
    # require BOTH to pass (the managed-bracket scope is optimistically biased by
    # trailed stops, so it must not be the thing that ships a policy).
    def score(label, sub, half_cut):
        nn = len(sub)
        if not nn:
            print(f'  [{label}] empty')
            return {'n>=20': False, 'net>0': False, 'older>0': False,
                    'newer>0': False, 'p<0.05': False}
        xs = [r['net'] for r in sub]
        mu = sum(xs) / nn
        sd = (sum((x - mu) ** 2 for x in xs) / (nn - 1)) ** 0.5 if nn > 1 else 0.0
        se = sd / nn ** 0.5
        t = mu / se if se else float('inf')
        w = sum(1 for x in xs if x > 0)
        try:
            from scipy import stats as _st
            p_t = float(2 * _st.t.sf(abs(t), nn - 1))
            p_sign = float(_st.binomtest(w, nn, 0.5).pvalue)
        except Exception:
            p_t = p_sign = float('nan')
        older = sum(r['net'] for r in sub if r['close_time'] < half_cut)
        newer = sum(r['net'] for r in sub if r['close_time'] >= half_cut)
        ex3 = sum(sorted(xs, reverse=True)[3:])
        bars = {
            'n>=20': nn >= 20,
            'net_after_fees>0': mu > 0,
            'older_half>0': older > 0,
            'newer_half>0': newer > 0,
            'p<0.05': (p_t < 0.05) and (p_sign < 0.05),
        }
        marks = ' | '.join(
            f'{k} {"PASS" if v else "FAIL"}' for k, v in bars.items())
        print(f'  [{label}] n={nn} net={sum(xs):+.3f} | {marks}')
        print(f'    t={t:+.2f} p_t={p_t:.4f} WR={100.0 * w / nn:.1f}% '
              f'p_sign={p_sign:.4f} older={older:+.3f} newer={newer:+.3f} '
              f'ex-top3={ex3:+.3f}')
        return bars

    agg('ALL', res)
    agg('scope raw (stop not manager-moved)', [r for r in res if r['scope'] == 'raw'])
    agg('scope managed (trailed bracket)', [r for r in res if r['scope'] == 'managed'])
    agg('older half', [r for r in res if r['close_time'] < half_cut])
    agg('newer half', [r for r in res if r['close_time'] >= half_cut])
    agg('LONG', [r for r in res if r['direction'] == 'LONG'])
    agg('SHORT', [r for r in res if r['direction'] == 'SHORT'])
    print('  by exit_reason (worst first):')
    byx = {}
    for r in res:
        byx.setdefault(r['exit_reason'], []).append(r)
    for k in sorted(byx, key=lambda k: sum(x['net'] for x in byx[k])):
        agg('  ' + k, byx[k])
    tk = sum(1 for r in res if r['kind'] == 'timeout')
    sl = sum(1 for r in res if r['kind'] == 'sl')
    tp = sum(1 for r in res if r['kind'] == 'tp')
    print(f'  exit mix: sl={sl} tp={tp} timeout={tk} ({100.0*tk/n:.1f}% timed out)')
    print(f'  median recovery time: {sorted(r["recovery_min"] for r in res)[n//2]:.1f} min | '
          f'median hold: {sorted(r["hold_min"] for r in res)[n//2]:.1f} min')

    print('  PRE-LOCKED BARS (stated in the header before any run) + standing '
          'AGENTS p<0.05 rule (stricter, never looser):')
    bars_all = score('ALL', res, half_cut)
    bars_raw = score('RAW-bracket scope', [r for r in res if r['scope'] == 'raw'], half_cut)
    verdict = ('SHIP-CANDIDATE (needs CEO GO)'
               if all(bars_all.values()) and all(bars_raw.values())
               else 'REJECTED-WITH-DATA')
    print(f'  VERDICT (needs ALL-SET and RAW-SCOPE bars all PASS): {verdict}')
    return res, counts


# ------------------------------------------------------------------ self-check
def _selfcheck():
    def bar(ts, o, h, l, c):
        return (ts, o, h, l, c)

    # 1. LONG trigger + SL
    bars = [bar(60, 100, 100.6, 99.4, 100.4),
            bar(120, 100.4, 100.8, 97.5, 98.0),
            bar(180, 98, 99, 97, 99)]
    i = find_trigger(bars, 100.0, 'LONG', 'through_close')
    assert i == 0, i
    k, px, ts = walk(bars, 100.0, 'LONG', 98.0, 102.0, i + 1, 3600)
    assert (k, px) == ('sl', 98.0), (k, px)

    # 2. same-bar tie -> SL wins
    bars = [bar(60, 100, 100.6, 99.4, 100.4),
            bar(120, 100.4, 102.5, 97.9, 101.0)]
    i = find_trigger(bars, 100.0, 'LONG', 'through_close')
    k, px, _ = walk(bars, 100.0, 'LONG', 98.0, 102.0, i + 1, 3600)
    assert (k, px) == ('sl', 98.0), (k, px)

    # 3. LONG TP
    bars = [bar(60, 100, 100.6, 99.4, 100.4),
            bar(120, 100.4, 102.2, 99.9, 101.5)]
    i = find_trigger(bars, 100.0, 'LONG', 'through_close')
    k, px, _ = walk(bars, 100.0, 'LONG', 98.0, 102.0, i + 1, 3600)
    assert (k, px) == ('tp', 102.0), (k, px)

    # 4. timeout at last close
    bars = [bar(60, 100, 100.6, 99.4, 100.4),
            bar(120, 100.4, 100.7, 100.0, 100.3),
            bar(180, 100.3, 100.6, 100.1, 100.5)]
    i = find_trigger(bars, 100.0, 'LONG', 'through_close')
    k, px, _ = walk(bars, 100.0, 'LONG', 98.0, 102.0, i + 1, 50)   # horizon cuts bar 3
    assert k == 'timeout' and px == 100.3, (k, px)

    # 5. no recovery: price never trades through entry
    bars = [bar(60, 99, 99.9, 98.5, 99.2), bar(120, 99.2, 99.8, 98.9, 99.5)]
    assert find_trigger(bars, 100.0, 'LONG', 'through') is None
    assert find_trigger(bars, 100.0, 'LONG', 'through_close') is None

    # 6. SHORT mirror: falls back through entry, then stops us out
    bars = [bar(60, 100, 100.4, 99.6, 99.7),
            bar(120, 99.7, 102.4, 99.5, 101.0)]
    i = find_trigger(bars, 100.0, 'SHORT', 'through_close')
    assert i == 0, i
    k, px, _ = walk(bars, 100.0, 'SHORT', 102.0, 98.0, i + 1, 3600)
    assert (k, px) == ('sl', 102.0), (k, px)

    # 7. mode separation: spans entry but CLOSES on the adverse side
    bars = [bar(60, 100, 100.6, 99.4, 99.8)]   # LONG, close 99.8 < entry
    assert find_trigger(bars, 100.0, 'LONG', 'through') == 0
    assert find_trigger(bars, 100.0, 'LONG', 'through_close') is None

    # 8. fee math: 11.10 notional, +1% move, round trip 0.045%x2
    g = gross_pnl(11.10, 100.0, 101.0, 'LONG')
    assert abs(g - 0.111) < 1e-9, g
    fee = 11.10 * FEE_RATE * 2
    assert abs(fee - 0.00999) < 1e-9, fee
    # SHORT sign
    assert abs(gross_pnl(11.10, 100.0, 99.0, 'SHORT') - 0.111) < 1e-9

    # 9. bracket validation
    assert bracket_ok(100.0, 'LONG', 98.0, 102.0)
    assert not bracket_ok(100.0, 'LONG', 102.0, 98.0)     # ratcheted through entry
    assert bracket_ok(100.0, 'SHORT', 102.0, 98.0)
    assert not bracket_ok(100.0, 'SHORT', 98.0, 102.0)

    # 10. the fill bar's own path is never walked (index must advance past fill)
    # fill bar touches SL 100.2 with its low; the NEXT bar does not -> must time out
    bars = [bar(60, 100, 100.6, 99.4, 100.4),
            bar(120, 100.4, 100.5, 100.3, 100.4)]
    i = find_trigger(bars, 100.0, 'LONG', 'through_close')
    assert i == 0
    k, px, _ = walk(bars, 100.0, 'LONG', 100.2, 102.0, i + 1, 3600)
    assert k == 'timeout' and px == 100.4, (k, px)

    # 11. INTEGRATION: simulate() must skip the candle containing close_time.
    # If that candle were used as the fill, the walk would start at f+60 and stop
    # out; skipping it fills at f+120 and takes the TP instead.
    con = sqlite3.connect(':memory:')
    con.execute('CREATE TABLE candles_1m (token TEXT, ts INTEGER, open REAL, high REAL, '
                'low REAL, close REAL, volume REAL, is_closed INTEGER, PRIMARY KEY(token, ts))')
    f = int(dt.datetime(2026, 1, 1, 0, 0, 30, tzinfo=dt.timezone.utc).timestamp()) // 60 * 60
    seq = [(f, 100, 100.5, 99.0, 100.4),      # candle CONTAINING close_time (must be skipped)
           (f + 60, 100.4, 99.8, 97.5, 98.0),  # no entry span; would SL if wrongly walked
           (f + 120, 99.8, 100.6, 99.9, 100.4),  # recovery fill
           (f + 180, 100.4, 102.5, 100.1, 101.5)]  # TP
    for ts, o, h, l, c in seq:
        con.execute('INSERT INTO candles_1m VALUES (?,?,?,?,?,?,1,1)', ('T', ts, o, h, l, c))
    close_ts = dt.datetime(2026, 1, 1, 0, 0, 30, tzinfo=dt.timezone.utc)
    out = simulate(con, 'T', close_ts, 100.0, 'LONG', 98.0, 102.0, 'through_close')
    assert out['status'] == 'simulated', out
    assert out['exit_kind'] == 'tp', out
    assert out['fill_ts'] == f + 120, out

    # 12. INTEGRATION: a recovery bar just past the 60m trigger window must not count.
    con.execute('DELETE FROM candles_1m')
    for ts, o, h, l, c in [(f + 60, 99, 99.8, 98.5, 99.2),            # in window, no span
                           (f + 3660, 99.8, 100.6, 99.7, 100.5)]:     # out of window, spans
        con.execute('INSERT INTO candles_1m VALUES (?,?,?,?,?,?,1,1)', ('U', ts, o, h, l, c))
    out = simulate(con, 'U', close_ts, 100.0, 'LONG', 98.0, 102.0, 'through_close')
    assert out['status'] == 'no_recovery', out
    con.close()

    # 13. walk horizon is measured from the FILL bar, so a candle gap cannot extend it
    gap_walk = [(1060, 100, 100.5, 99.5, 100.4),
                (4650, 100.4, 100.5, 97.0, 97.5)]     # 3650s after fill 1000
    k_anchor, _, _ = walk(gap_walk, 100.0, 'LONG', 98.0, 102.0, 0, 3600, anchor_ts=1000)
    k_default, _, _ = walk(gap_walk, 100.0, 'LONG', 98.0, 102.0, 0, 3600)
    assert k_anchor == 'timeout', k_anchor      # 4650 > 1000+3600 -> excluded
    assert k_default == 'sl', k_default         # without anchor it leaks in: the bug

    # 14. INTEGRATION: simulate() must anchor the walk to the FILL bar — a candle
    # gap right after the fill must not stretch the 60m hold (mutation-tested:
    # dropping `anchor_ts=` from the simulate() call makes exactly this assert fail).
    con = sqlite3.connect(':memory:')
    con.execute('CREATE TABLE candles_1m (token TEXT, ts INTEGER, open REAL, high REAL, '
                'low REAL, close REAL, volume REAL, is_closed INTEGER, PRIMARY KEY(token, ts))')
    for ts, o, h, l, c in [(f + 60, 99, 99.8, 98.5, 99.2),          # in window, no span
                           (f + 120, 99.8, 100.6, 99.9, 100.4),     # fill
                           (f + 300, 100.4, 100.5, 100.3, 100.4),   # gap after fill
                           (f + 3780, 100.4, 100.5, 97.0, 97.5)]:   # fill+3660s -> outside
        con.execute('INSERT INTO candles_1m VALUES (?,?,?,?,?,?,1,1)', ('G', ts, o, h, l, c))
    out = simulate(con, 'G', close_ts, 100.0, 'LONG', 98.0, 102.0, 'through_close')
    assert out['status'] == 'simulated' and out['fill_ts'] == f + 120, out
    assert out['exit_kind'] == 'timeout', out      # fill-anchored: 3660s > 60m
    con.close()

    # 15. fee_for: recorded 0.0 is a value, not a fallback trigger
    assert fee_for('{"fee_total": 0.010224}') == 0.010224
    assert fee_for('{"fee_total": 0.0}') == 0.0
    assert fee_for(None) is None
    assert fee_for('nonsense') is None
    assert fee_for('{"other": 1}') is None
    assert scope_of('atr_sl_hit') == 'managed'
    assert scope_of('hard_max_loss') == 'raw'
    assert scope_of('trail_arm_timeout') == 'raw'

    print('reenter_recovery_cf --selfcheck PASS (15 cases: SL, tie, TP, timeout, '
          'no-recovery, SHORT, mode separation, fees, bracket validation, fill-bar skip, '
          'simulate() close-candle skip, simulate() trigger-window bound, walk '
          'fill-anchor, simulate() fill-anchor, fee_for/scope)')


if __name__ == '__main__':
    if '--selfcheck' in sys.argv:
        _selfcheck()
    else:
        mode = 'through_close'
        days = 30
        for a in sys.argv[1:]:
            if a.startswith('--mode='):
                mode = a.split('=', 1)[1]
            elif a.startswith('--days='):
                days = int(a.split('=', 1)[1])
        report(days, mode)
