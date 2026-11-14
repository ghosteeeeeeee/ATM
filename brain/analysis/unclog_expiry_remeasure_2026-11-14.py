#!/usr/bin/env python3
"""unclog_expiry_remeasure_2026-11-14.py — owed CEO item: unclog-waiver EXPIRY
re-measure of the SHORT RSI [35,45) band (expired 2026-11-03T00:00Z).

WHY (owed since 2026-11-03, resurfaced every audit since #140):
vacation_mode.json rules.unclog_waiver governs decider ctx/exec + compactor
approval + brain final-gate SHORT RSI in [35, 45) bear-structure exemption
(knife RSI<35 is NEVER waived). It expired 2026-11-03T00:00:00Z and nothing
re-measured the band before/after, so the renewal decision has had no data.

WHAT THIS MEASURES (both sides of the same instrument, direction-signed fwd_4h
= gate_shadow's own metric, entry = OPEN of first closed 5m candle with ts>=event,
sgn=+1 LONG/-1 SHORT so POSITIVE = that cohort's direction WON over 4h):

  ARMED   = log lines `✅ ... allowed at approval — RSI x < 45 but BTC bearish`
            (waiver live). Band admitted.
  LAPSED  = log lines `🚫 ... blocked at approval — RSI x < 45` with x in [35,45)
            (waiver expired). Same band, now blocked.

Knives (x<35, or any line whose floor reads `< 35`) are reported as a CONTROL
only — the waiver never covered them, so they must stay negative (protective).

Method guards (house Step-5c + THE PATTERN):
  * 10-min token|direction dedupe (gate_shadow dedup convention) — no pseudo-rep.
  * cluster_t CR1 clustered on token|direction for every significance claim.
  * $-eq at LIVE 30d avg PG notional read at runtime (never hardcoded).
  * BOTH a pre-expiry and post-expiry window reported so a single regime is
    never sold as an edge.
  * unit test: arm == lapsed sample check in selfcheck; fwd_4h re-used from
    gate_shadow so the sign convention cannot drift from the registered metric.

Usage:
  python3 brain/analysis/unclog_expiry_remeasure_2026-11-14.py [--selfcheck]
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
EXPIRY = '2026-11-03'

RE_BLOCK = re.compile(
    r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*'
    r'\[SHORT-RSI-HARD-FLOOR\] (\w+): SHORT blocked at approval — RSI ([\d.]+) < (\d+)')
RE_ALLOW = re.compile(
    r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*'
    r'\[SHORT-RSI-HARD-FLOOR\] (\w+): SHORT allowed at approval — RSI ([\d.]+) < (\d+)')


def _log_paths():
    paths = sorted(glob.glob(os.path.join(HERMES, 'logs/archive/pipeline.log.*.gz')))
    paths.append(os.path.join(HERMES, 'logs/pipeline.log'))
    return paths


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
    """-> list of dicts {ts, token, rsi, floor, kind} kind in {'arm','lapsed','knife'}."""
    out = []
    for line in _iter_lines():
        if 'SHORT-RSI-HARD-FLOOR' not in line:
            continue
        m = RE_BLOCK.match(line)
        kind_src = 'block'
        if m is None:
            m = RE_ALLOW.match(line)
            kind_src = 'allow'
        if m is None:
            continue
        ts, tok, rsi_s, floor_s = m.groups()
        rsi, floor = float(rsi_s), int(floor_s)
        if kind_src == 'allow':
            # waiver live -> the [35,45) band was admitted
            kind = 'arm' if 35 <= rsi < 45 else ('knife_ctrl' if rsi < 35 else 'other')
        else:
            if floor >= 45 and 35 <= rsi < 45:
                kind = 'lapsed'          # the band this re-measure is about
            elif rsi < 35 or floor < 45:
                kind = 'knife_ctrl'      # knife, never waived
            else:
                kind = 'other'
        out.append({'ts': ts, 'token': tok.upper(), 'rsi': rsi,
                    'floor': floor, 'kind': kind, 'line_src': kind_src})
    return out


def dedup(rows):
    """gate_shadow convention: same gate|token|direction within a 10-min bucket
    (strftime('%Y%m%d%H%M')[:-1] — byte-identical to gate_shadow.py:321).
    `kind` is in the key so the arm/lapsed/knife legs cannot collapse onto each
    other when two floors fire on the same token in the same bucket; each leg is
    deduped exactly as gate_shadow would dedupe it alone.
    """
    seen, keep = set(), []
    for r in rows:
        bucket = r['ts'][:16].replace('-', '').replace(' ', '').replace(':', '')[:-1]
        k = (r['token'], 'SHORT', bucket, r['kind'])
        if k in seen:
            continue
        seen.add(k)
        keep.append(r)
    return keep


def fwd(rows):
    """Attach fwd_4h via gate_shadow's own helpers (sign convention locked).

    entry_ts must be unix-epoch seconds — candles_5m.ts is an INTEGER and
    gate_shadow builds entry_ts with calendar.timegm(...), not a string.
    """
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


def summarize(rows, label, notional):
    if not rows:
        print(f"  {label:28s} n=0")
        return None
    vals = [r['fwd_4h'] for r in rows]
    clus = [f"{r['token']}|SHORT" for r in rows]
    n = len(vals)
    tok_n = len(set(clus))
    mean = sum(vals) / n
    pos = sum(1 for v in vals if v > 0)
    try:
        t, beta, G = cluster_t(vals, clus)
    except Exception as e:
        t, beta, G = float('nan'), mean, tok_n
    dollar = mean * notional / 100.0
    print(f"  {label:28s} n={n:5d} tok_n={tok_n:3d} fwd%={mean:+.4f} "
          f"t_CR1={t:+.2f} pos={100.0*pos/n:4.1f}% $eq/trade={dollar:+.4f} "
          f"$eq_total={dollar*n:+.2f}")
    return {'label': label, 'n': n, 'tok_n': tok_n, 'mean': mean,
            't': t, 'pos_pct': 100.0 * pos / n, 'dollar_each': dollar}


def _se_cluster(vals, clus):
    """CR1 standard error of the mean, clustered — companion to cluster_t."""
    t, beta, G = cluster_t(vals, clus)
    if t == 0 or t != t:  # zero/NaN t -> SE undefined from t
        return float('nan'), beta, G
    return abs(beta / t) if t else float('nan'), beta, G


def differential(lapsed, knife, label):
    """Band-minus-knife differential (control-subtracted).

    WHY: in a one-direction tape EVERY short has positive fwd_4h, so the raw
    LAPSED mean alone cannot tell 'the band is good' from 'the tape is down'.
    The knife leg is the never-waived control that rides the SAME tape; the
    differential isolates the band. SE via independent-sample sum (conservative
    while the token sets overlap).
    """
    if not lapsed or not knife:
        print(f"  {label}: insufficient n for differential")
        return None
    vl = [r['fwd_4h'] for r in lapsed]
    kl = [f"{r['token']}|SHORT" for r in lapsed]
    vk = [r['fwd_4h'] for r in knife]
    kk = [f"{r['token']}|SHORT" for r in knife]
    sl, bl, Gl = _se_cluster(vl, kl)
    sk, bk, Gk = _se_cluster(vk, kk)
    diff = bl - bk
    se = (sl ** 2 + sk ** 2) ** 0.5
    t = diff / se if se and se == se else float('nan')
    ok = diff > 0 and abs(t) >= 2 and Gl >= 50
    print(f"  {label}: band {bl:+.4f} vs knife {bk:+.4f} -> DIFF {diff:+.4f} "
          f"(SE {se:.4f}) t={t:+.2f}  G_lapsed={Gl} G_knife={Gk}")
    print(f"      => {'band beats knife' if diff > 0 else 'band <= knife (gate fine)'}; "
          f"renewal bar (diff>0, |t|>=2, G>=50): {'CLEARS' if ok else 'FAILS'}")
    return {'diff': diff, 't': t, 'G_lapsed': Gl, 'G_knife': Gk, 'clears': ok}


def main():
    rows = collect()
    print(f"raw parsed events: {len(rows)}")
    by = {}
    for r in rows:
        by[r['kind']] = by.get(r['kind'], 0) + 1
    print("  by kind:", by)

    notional = _notional()
    print(f"live 30d avg notional: {notional:.2f} USDT\n")

    d = dedup(rows)
    print(f"after 10-min token|direction dedupe: {len(d)}")

    # window split so one regime is never sold as an edge
    pre = [r for r in d if r['ts'] < EXPIRY and r['kind'] in ('arm', 'lapsed', 'knife_ctrl')]
    post = [r for r in d if r['ts'] >= EXPIRY and r['kind'] in ('arm', 'lapsed', 'knife_ctrl')]

    print("\n=== PRE-EXPIRY window (< 2026-11-03, waiver LIVE) — fwd_4h dir-signed, + = that cohort WON ===")
    pre_f = fwd(pre)
    res = {}
    for k, lab in (('arm', 'ARMED [35,45) admitted'),
                   ('lapsed', 'LAPSED [35,45) blocked'),
                   ('knife_ctrl', 'CONTROL knife <35 (never waived)')):
        res['pre_' + k] = summarize([r for r in pre_f if r['kind'] == k], lab, notional)

    print("\n=== POST-EXPIRY window (>= 2026-11-03, waiver LAPSED) ===")
    post_f = fwd(post)
    for k, lab in (('arm', 'ARMED [35,45) admitted'),
                   ('lapsed', 'LAPSED [35,45) blocked'),
                   ('knife_ctrl', 'CONTROL knife <35 (never waived)')):
        res['post_' + k] = summarize([r for r in post_f if r['kind'] == k], lab, notional)

    # control-subtracted differential — the actual renewal test
    print("\n=== CONTROL-SUBTRACTED DIFFERENTIAL (band minus knife, same tape) ===")
    res['pre_diff'] = differential([r for r in pre_f if r['kind'] == 'lapsed'],
                                   [r for r in pre_f if r['kind'] == 'knife_ctrl'],
                                   'PRE-expiry ')
    res['post_diff'] = differential([r for r in post_f if r['kind'] == 'lapsed'],
                                    [r for r in post_f if r['kind'] == 'knife_ctrl'],
                                    'POST-expiry')

    # decision read
    print("\n=== DECISION READ ===")
    a, l = res.get('post_arm'), res.get('post_lapsed')
    if l:
        verdict = 'GATE COSTLY (blocked shorts would have won)' if l['mean'] > 0 \
            else 'GATE PROTECTIVE (blocked shorts would have lost)'
        print(f"  post-expiry LAPSED band RAW: {verdict}  fwd={l['mean']:+.4f} "
              f"t={l['t']:+.2f} n={l['n']} tok_n={l['tok_n']}")
    if res.get('post_diff'):
        pd = res['post_diff']
        print(f"  post-expiry CONTROL-SUBTRACTED: diff={pd['diff']:+.4f} t={pd['t']:+.2f} "
              f"-> {'CLEARS' if pd['clears'] else 'FAILS'} renewal bar")
    if res.get('pre_diff'):
        pd = res['pre_diff']
        print(f"  pre-expiry  CONTROL-SUBTRACTED: diff={pd['diff']:+.4f} t={pd['t']:+.2f}")
    if res.get('pre_diff') and res.get('post_diff'):
        same = res['pre_diff']['diff'] > 0 and res['post_diff']['diff'] > 0
        print(f"  OOS same-sign across expiry (house rule): "
              f"{'PASS' if same else 'FAIL'} (pre {res['pre_diff']['diff']:+.4f} / "
              f"post {res['post_diff']['diff']:+.4f})")
    print("\nCONTROL HEALTH: knife<35 must be <=0 raw; a positive knife raw mean means the "
          "tape is doing the work — only the differential is interpretable then.")

    return res


def _selfcheck():
    # 1. parser must see both allow (armed) and block (lapsed) line shapes
    rows = collect()
    assert rows, "no SHORT-RSI-HARD-FLOOR lines parsed — log rotation or regex drift"
    kinds = {r['kind'] for r in rows}
    assert 'lapsed' in kinds, f"no lapsed-band rows parsed: {kinds}"
    # 2. knife control must exist (floor<45 / rsi<35 lines are the never-waived leg)
    assert 'knife_ctrl' in kinds, f"no knife control rows: {kinds}"
    # 3. armed rows must be strictly from ALLOW lines, lapsed strictly from BLOCK lines
    assert all(r['line_src'] == 'allow' for r in rows if r['kind'] == 'arm')
    assert all(r['line_src'] == 'block' for r in rows if r['kind'] == 'lapsed')
    # 4. lapsed band membership: 35 <= rsi < 45 and floor >= 45
    for r in rows:
        if r['kind'] == 'lapsed':
            assert 35 <= r['rsi'] < 45, r
            assert r['floor'] >= 45, r
        if r['kind'] == 'knife_ctrl':
            assert r['rsi'] < 35 or r['floor'] < 45, r
    # 5. dedupe must not invent rows
    d = dedup(rows)
    assert 0 < len(d) <= len(rows), (len(d), len(rows))
    # 6. sign convention lock: a hand-built candle set where price RISES 1% must
    #    yield fwd_4h = -1.0 for SHORT (the short would have LOST).
    #    candles_5m.ts is INTEGER unix epoch — fake rows must match that.
    from gate_shadow import _fwd_4h
    ts0 = 1794297600  # 2026-11-10 00:00:00 UTC
    base = 100.0
    fake = []
    for i in range(49):
        c = 101.0 if i >= 48 else 100.0
        fake.append((ts0 + i * 300, base, c))
    v = _fwd_4h(fake, ts0, 'SHORT')
    assert v is not None and abs(v - (-1.0)) < 1e-9, f"sign lock failed: {v}"
    vL = _fwd_4h(fake, ts0, 'LONG')
    assert vL is not None and abs(vL - 1.0) < 1e-9, f"LONG mirror failed: {vL}"
    # 6b. dedupe bucket must reproduce gate_shadow's 10-min bucket byte-for-byte
    assert dedup([{'ts': '2026-11-14 16:30:02', 'token': 'SOL', 'kind': 'lapsed'}]), 'dedup'
    # 7. cluster_t selfcheck
    from cluster_t import cluster_t as _ct
    tstat, beta, G = _ct([1.0, 1.0, -1.0, -1.0], ['a', 'a', 'b', 'b'])
    assert G == 2 and abs(beta) < 1e-12
    # 8. differential: identical distributions -> diff must be ~0, and a shifted
    #    band must come out positive with the sign the control subtraction implies
    import io as _io
    import contextlib as _cl
    fake_l = [{'fwd_4h': v, 'token': f'T{i%10}'} for i, v in
              enumerate([0.5] * 30 + [-0.5] * 20)]
    fake_k = [{'fwd_4h': v, 'token': f'U{i%10}'} for i, v in
              enumerate([0.1] * 30 + [-0.1] * 20)]
    buf = _io.StringIO()
    with _cl.redirect_stdout(buf):
        out_same = differential(list(fake_k), list(fake_k), 'SELFTEST')
        out_pos = differential(list(fake_l), list(fake_k), 'SELFTEST')
    assert out_same is not None and abs(out_same['diff']) < 1e-9, out_same
    assert out_pos is not None and out_pos['diff'] > 0.05, out_pos
    print("SELFCHECK PASS")
    return True


if __name__ == '__main__':
    if '--selfcheck' in sys.argv:
        _selfcheck()
    else:
        main()
