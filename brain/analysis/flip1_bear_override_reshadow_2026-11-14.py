#!/usr/bin/env python3
"""flip1_bear_override_reshadow_2026-11-14.py — EARLY read of the owed
`flip1-bear-override-reshadow` eval (deadline 2026-11-17) and the CEO-owed
"unclog-waiver EXPIRY re-measure [35,45)" (expired 2026-11-03, owed since).

WHY THIS IS THE DECISIVE INSTRUMENT (not the raw SHORT-RSI-HARD-FLOOR join):
when the waiver is expired the floor blocks EVERY [35,45) SHORT regardless of
structure, so the blocked cohort mixes 'would have been admitted under the
bear-condition' with 'would have been blocked anyway'. [FLIP1-OVERRIDE-SHADOW]
is emitted only when the bear-structure override conditions THEMSELVES hold
(RSI >= 35, BTC continuum LEAN_BEAR/BEAR fresher than 600s) and flip1_active()
is False — i.e. exactly the trades a renewed waiver would have admitted. It
ships SHADOW (FLIP1_BEAR_OVERRIDE_SHADOW=True, ENFORCE=False) so it is
zero-behavior and joins cleanly.

Pre-registered threshold (data/shadow_disposition.json):
  14d shadow n>=20, net >= +$1.00, leave-one-out positive
  + TAPE-SPLIT AMENDMENT (CEO 20261113T040327Z): report trend-day subset vs
    chop subset separately — sign flipping by tape = regime dependence, and the
    11-03..11-14 crash sits INSIDE the window so it must not select the window.

Method guards: 10-min token|SHORT dedupe (gate_shadow convention), fwd_4h
direction-signed via gate_shadow's own helpers, cluster_t CR1 for every
significance claim, $-eq at LIVE 30d avg PG notional, leave-one-out over tokens.

Usage:
  python3 brain/analysis/flip1_bear_override_reshadow_2026-11-14.py [--selfcheck]
"""
import glob
import gzip
import io
import os
import re
import sys

sys.path.insert(0, '/root/.hermes/scripts')
sys.path.insert(0, '/root/.hermes/brain/analysis')

from cluster_t import cluster_t  # noqa: E402

HERMES = '/root/.hermes'
RE = re.compile(
    r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+.*'
    r'\[FLIP1-OVERRIDE-SHADOW\] (\w+) SHORT WOULD-ALLOW — rsi=([\d.]+) < (\d+) '
    r'but BTC-bear structure \(linreg=(\w+), age=(\d+)s')


def _log_paths():
    return sorted(glob.glob(os.path.join(HERMES, 'logs/archive/pipeline.log.*.gz'))) + \
        [os.path.join(HERMES, 'logs/pipeline.log')]


def _iter_lines():
    for p in _log_paths():
        try:
            if p.endswith('.gz'):
                with gzip.open(p, 'rt', errors='replace') as f:
                    for line in f:
                        yield line
            else:
                with io.open(p, 'r', errors='replace') as f:
                    for line in f:
                        yield line
        except OSError:
            continue


def collect():
    """-> [{ts, token, rsi, floor, linreg, age_s}]."""
    out = []
    for line in _iter_lines():
        if '[FLIP1-OVERRIDE-SHADOW]' not in line:
            continue
        m = RE.match(line)
        if not m:
            continue
        ts, tok, rsi, floor, linreg, age = m.groups()
        out.append({'ts': ts, 'token': tok.upper(), 'rsi': float(rsi),
                    'floor': int(floor), 'linreg': linreg, 'age_s': int(age)})
    return out


def dedup(rows, bucket_min=10):
    """gate_shadow convention: same token|direction within a 10-min bucket."""
    seen, keep = set(), []
    for r in rows:
        # bucket = strftime('%Y%m%d%H%M')[:-1]  -> 10-min granularity
        b = r['ts'][:16].replace('-', '').replace(' ', '').replace(':', '')[:-1]
        k = (r['token'], 'SHORT', b)
        if k in seen:
            continue
        seen.add(k)
        keep.append(r)
    return keep


def tape_of(ts, conn):
    """Trend vs chop at the shadow instant (CEO tape-split amendment).

    TREND  = BTC 1m ema300_position=='BELOW' with a sustained streak
             (consecutive_below/ema300_duration >= 60 ~ 1h of 1m closes) —
             an established downtrend where 'oversold = continuation'.
    CHOP   = AT/ABOVE, or a streak shorter than 60m (direction not established).
    Returns 'trend' | 'chop' | 'unknown'.
    """
    import calendar
    from datetime import datetime
    try:
        epoch = calendar.timegm(datetime.strptime(ts, '%Y-%m-%d %H:%M:%S').utctimetuple())
    except ValueError:
        return 'unknown'
    row = conn.execute(
        "SELECT ema300_position, COALESCE(consecutive_below,0), COALESCE(ema300_duration,0) "
        "FROM continuum_states WHERE token='BTC' AND timeframe='1m' AND ts <= ? "
        "ORDER BY ts DESC LIMIT 1", (epoch,)).fetchone()
    if not row:
        return 'unknown'
    pos, cbelow, dur = row
    streak = max(cbelow, dur) if pos == 'BELOW' else 0
    if pos == 'BELOW' and streak >= 60:
        return 'trend'
    return 'chop'


def fwd(rows):
    """Attach fwd_4h (direction-signed SHORT) via gate_shadow helpers."""
    import calendar
    from datetime import datetime
    from gate_shadow import _fwd_4h, _load_fwd_candles
    got = []
    for r in rows:
        try:
            cr = _load_fwd_candles(r['token'])
        except Exception:
            continue
        if not cr:
            continue
        try:
            entry_ts = calendar.timegm(
                datetime.strptime(r['ts'], '%Y-%m-%d %H:%M:%S').utctimetuple())
        except ValueError:
            continue
        v = _fwd_4h(cr, entry_ts, 'SHORT')
        if v is None:
            continue
        r = dict(r)
        r['fwd_4h'] = v
        got.append(r)
    return got


def _notional():
    import psycopg2
    conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
    cur = conn.cursor()
    cur.execute("SELECT AVG(amount_usdt) FROM trades WHERE status='closed' "
                "AND close_time > NOW() - INTERVAL '30 days'")
    n = cur.fetchone()[0]
    conn.close()
    return float(n or 0.0)


def stats(rows, notional):
    if not rows:
        return None
    vals = [r['fwd_4h'] for r in rows]
    clus = [f"{r['token']}|SHORT" for r in rows]
    n = len(vals)
    tok_n = len(set(clus))
    mean = sum(vals) / n
    net_pp = sum(vals)
    net_usd = net_pp * notional / 100.0
    try:
        t, beta, G = cluster_t(vals, clus)
    except Exception:
        t, beta, G = float('nan'), mean, tok_n
    pos = sum(1 for v in vals if v > 0)
    return {'n': n, 'tok_n': tok_n, 'mean': mean, 'net_pp': net_pp,
            'net_usd': net_usd, 't': t, 'pos_pct': 100.0 * pos / n}


def leave_one_out(rows, notional):
    """Net after dropping each token in turn — 'leave-one-out positive' bar."""
    toks = sorted({r['token'] for r in rows})
    worst, worst_tok = None, None
    for tk in toks:
        sub = [r for r in rows if r['token'] != tk]
        if not sub:
            continue
        s = stats(sub, notional)
        if worst is None or s['net_usd'] < worst:
            worst, worst_tok = s['net_usd'], tk
    return worst, worst_tok


def _print(label, rows, notional):
    s = stats(rows, notional)
    if not s:
        print(f"  {label:34s} n=0")
        return None
    print(f"  {label:34s} n={s['n']:4d} tok_n={s['tok_n']:3d} "
          f"fwd={s['mean']:+.4f}% net={s['net_pp']:+.3f}pp "
          f"${s['net_usd']:+.2f} t_CR1={s['t']:+.2f} pos={s['pos_pct']:4.1f}%")
    return s


def main():
    rows = collect()
    print(f"raw [FLIP1-OVERRIDE-SHADOW] lines: {len(rows)}")
    if rows:
        print(f"  window: {rows[0]['ts']} -> {rows[-1]['ts']}")
    d = dedup(rows)
    print(f"after 10-min token|SHORT dedupe: {len(d)}")

    notional = _notional()
    print(f"live 30d avg notional: {notional:.2f} USDT\n")

    import sqlite3
    cont = sqlite3.connect(os.path.join(HERMES, 'data/continuum.db'), timeout=5)
    for r in d:
        r['tape'] = tape_of(r['ts'], cont)
    cont.close()
    print("tape split at shadow instant:")
    from collections import Counter
    print("  ", dict(Counter(r['tape'] for r in d)))

    f = fwd(d)
    print(f"joined to fwd_4h: {len(f)}\n")

    print("=== THRESHOLD READ (14d, n>=20, net >= +$1.00, LOO positive) ===")
    overall = _print('ALL shadow WOULD-ALLOW', f, notional)

    print("\n=== TAPE SPLIT (CEO amendment 2026-11-13: sign flip by tape = regime dep.) ===")
    tr = [r for r in f if r['tape'] == 'trend']
    ch = [r for r in f if r['tape'] == 'chop']
    st_ = _print('TREND (BELOW streak >=60m)', tr, notional)
    sc = _print('CHOP (AT/ABOVE/short streak)', ch, notional)

    print("\n=== WEEKLY (window-selection guard) ===")
    from collections import defaultdict
    isowk = defaultdict(list)
    for r in f:
        import datetime as _dt
        y, m, dd = (int(x) for x in r['ts'][:10].split('-'))
        isowk[_dt.date(y, m, dd).isocalendar()[:2]].append(r)
    for k in sorted(isowk):
        s = stats(isowk[k], notional)
        print(f"  ISO{k[0]}-W{k[1]:02d}: n={s['n']:4d} net={s['net_pp']:+.3f}pp ${s['net_usd']:+.2f} "
              f"pos={s['pos_pct']:4.1f}%")

    loo, loo_tok = (None, None)
    if f:
        loo, loo_tok = leave_one_out(f, notional)
        print(f"\n=== LEAVE-ONE-OUT ===\n  worst-case net after dropping one token: "
              f"${loo:+.2f} (dropping {loo_tok}) -> "
              f"{'PASS' if loo is not None and loo > 0 else 'FAIL'}")

    print("\n=== VERDICT ===")
    if not overall:
        print("  no data")
        return
    n_ok = overall['n'] >= 20
    net_ok = overall['net_usd'] >= 1.00
    loo_ok = loo is not None and loo > 0  # bar: leave-one-out POSITIVE
    sign_flip = (st_ and sc and (st_['net_pp'] > 0) != (sc['net_pp'] > 0))
    print(f"  n>=20            : {'PASS' if n_ok else 'FAIL'} (n={overall['n']}, tok_n={overall['tok_n']})")
    print(f"  net >= +$1.00    : {'PASS' if net_ok else 'FAIL'} (${overall['net_usd']:+.2f})")
    print(f"  leave-one-out    : {'PASS' if loo_ok else 'FAIL'} (worst ${loo:+.2f})" if loo is not None else "  leave-one-out    : n/a")
    print(f"  tape-split sign  : {'SAME-SIGN' if not sign_flip else 'SIGN FLIPS BY TAPE -> regime-dependent'}")
    verdict = 'CLEAR (re-arm candidate -> CEO act via waiver_expiry)' \
        if (n_ok and net_ok and loo_ok and not sign_flip) else 'DOES NOT CLEAR -> stay blocked'
    print(f"  => {verdict}")
    if overall['t'] == overall['t']:
        print(f"  (cluster CR1 t on the full cohort: {overall['t']:+.2f} — "
              f"point estimate only if |t|<2)")


def _selfcheck():
    # 1. parser sees the shadow line shape from BOTH sources
    rows = collect()
    assert rows, "no FLIP1-OVERRIDE-SHADOW lines parsed — regex/rotation drift"
    for r in rows[:5] + rows[-5:]:
        assert 35 <= r['rsi'] < 45, f"shadow cohort must be [35,45): {r}"
        assert r['floor'] >= 45, r
        assert r['linreg'] in ('LEAN_BEAR', 'BEAR'), r
    # 2. dedupe shrinks (lines repeat every minute) and never grows
    dd = dedup(rows)
    assert 0 < len(dd) <= len(rows), (len(dd), len(rows))
    # 3. dedupe is bucket-identical to gate_shadow for the same stamp
    one = dedup([{'ts': '2026-11-14 16:30:02', 'token': 'SOL'}])
    two = dedup([{'ts': '2026-11-14 16:30:02', 'token': 'SOL'},
                 {'ts': '2026-11-14 16:39:59', 'token': 'SOL'},
                 {'ts': '2026-11-14 16:41:00', 'token': 'SOL'}])
    assert len(one) == 1 and len(two) == 2, (len(one), len(two))
    # 4. sign lock: price +1% over the horizon must be -1.0 for SHORT
    from gate_shadow import _fwd_4h
    ts0 = 1794297600
    fake = [(ts0 + i * 300, 100.0, 101.0 if i >= 48 else 100.0) for i in range(49)]
    v = _fwd_4h(fake, ts0, 'SHORT')
    assert v is not None and abs(v - (-1.0)) < 1e-9, v
    # 5. tape_of must not raise on an unknown stamp
    import sqlite3
    conn = sqlite3.connect(os.path.join(HERMES, 'data/continuum.db'), timeout=5)
    try:
        assert tape_of('not-a-date', conn) == 'unknown'
        assert tape_of('2026-11-14 12:00:00', conn) in ('trend', 'chop', 'unknown')
    finally:
        conn.close()
    # 6. cluster_t + leave_one_out arithmetic on a synthetic set
    fake_rows = [{'fwd_4h': 1.0, 'token': 'A'}, {'fwd_4h': 1.0, 'token': 'B'},
                 {'fwd_4h': -1.0, 'token': 'C'}, {'fwd_4h': 1.0, 'token': 'A'}]
    loo, tok = leave_one_out(fake_rows, 100.0)
    assert loo is not None and tok in ('A', 'B', 'C'), (loo, tok)
    print("SELFCHECK PASS")


if __name__ == '__main__':
    if '--selfcheck' in sys.argv:
        _selfcheck()
    else:
        main()
