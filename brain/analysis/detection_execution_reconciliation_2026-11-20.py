#!/usr/bin/env python3
"""Detection-vs-execution reconciliation — CEO deep run 20261120T145718Z (§E-SPEC).

Descriptive only: when a trade opens, how stale/drifted was its signal, and does
gap class associate with PnL? NO filter recommendations.

Window : last 30d closed trades, anchored MAX(close_time), psql brain.trades.
Joins  : trades <-> detection record (SQLite signals_hermes_runtime.db `signals`,
         coin+direction+closest created_at <= open_time; join rate reported)
         <-> _signal_metadata (PG jsonb, column on trades)
         <-> local candle DB (candles_1m / candles_5m, mode=ro). NO external APIs.
Gap classes (n, WR, avg pnl_usdt, total pnl_usdt each):
         G1 signal_age  = open_time - detection created_at -> P50/P90/P99 +
                          buckets <5m / 5-10m / 10-30m / >30m (10m = compaction_stale_10min)
         G2 condition_drift: RSI / momentum / gap detect->open drift buckets +
                          sign flips across v2 filter thresholds (imported from
                          hermes_constants, never hardcoded)
         G3 metadata_missing: absent/unjoinable detection record or metadata
         G0 clean: joined, age <10m, no sign-flip drift
Units  : money = pnl_usdt basis ONLY (never raw price move vs leveraged pnl_pct,
         landmine #193). trades.stop_loss is trail-mutated -> never read.
SELECT-only everywhere (PG SELECT, SQLite mode=ro); cursors/connections in finally.

Reproduce:
  python3 brain/analysis/detection_execution_reconciliation_2026-11-20.py
  python3 brain/analysis/detection_execution_reconciliation_2026-11-20.py --selfcheck
  python3 brain/analysis/detection_execution_reconciliation_2026-11-20.py \
      --report brain/analysis/detection-execution-reconciliation-2026-11-20.md
"""
import argparse
import math
import os
import sqlite3
import sys
from bisect import bisect_right
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'scripts'))
from paths import CANDLES_DB, RUNTIME_DB  # noqa: E402  (scripts/paths.py)

import psycopg2  # noqa: E402
from hermes_constants import (  # noqa: E402  — thresholds imported, NEVER hardcoded
    BB_BOUNCE_V2_RSI_MIN,
    BB_BOUNCE_V2_RSI_MAX,
    BB_BOUNCE_V2_SHORT_RSI_OVERBOUGHT,
    BB_BOUNCE_V2_MOM_MIN,
    BB_BOUNCE_V2_SHORT_MOM_MAX,
    BB_BOUNCE_V2_VEL_MIN,
    BB_BOUNCE_V2_SHORT_VEL_5M_MAX,
)

PG = {'host': '/var/run/postgresql', 'dbname': 'brain', 'user': 'postgres'}

# Spec-fixed age buckets (§E-SPEC; 10m aligns with compaction_stale_10min).
STALE_MIN = 10
# momentum_state recompute boundary — mirrored from signal_schema.py:533
# ('rising' if vel > 0.1 else 'falling' if vel < -0.1 else 'flat'); this is the
# state DEFINITION, not a v2 filter threshold (v2 thresholds come from imports).
MOM_STATE_VEL = 0.1

AGE_LABELS = ['<5m', '5-10m', '10-30m', '>30m']
# Drift-magnitude bucket edges (probe on this window: |rsi| P50 7.6 P90 25.2;
# |vel%| P50 0.24 P90 0.75; |mom| P50 0.020 P90 0.058; |gap pp| P50 0.46 P90 1.87).
RSI_EDGES, RSI_LABELS = [5, 10, 20], ['<5', '5-10', '10-20', '>=20']
VEL_EDGES, VEL_LABELS = [0.1, 0.5, 1.0], ['<0.1', '0.1-0.5', '0.5-1', '>=1']
MOM_EDGES, MOM_LABELS = [0.02, 0.05, 0.10], ['<0.02', '0.02-0.05', '0.05-0.1', '>=0.1']
GAP_EDGES, GAP_LABELS = [0.25, 0.5, 1.0, 2.0], ['<0.25', '0.25-0.5', '0.5-1', '1-2', '>=2']

SQL_LOG = []          # every statement executed (selfcheck asserts SELECT-only)
_CHK = [0]            # selfcheck assert counter


def chk(cond, msg):
    _CHK[0] += 1
    if not cond:
        raise AssertionError(f'selfcheck failed: {msg}')


def _log_sql(sql, params):
    SQL_LOG.append(sql)


def pg_select(sql, params=()):
    """SELECT-only PG helper; connection+cursor closed in finally; SQL+params printed."""
    _log_sql(sql, params)
    print(f'SQL(pg): {" ".join(sql.split())} | params={params!r}', file=sys.stderr)
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**PG)
        cur = conn.cursor()
        cur.execute(sql, params)
        return cur.fetchall()
    finally:
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()


def sq_select(db, sql, params=()):
    """SELECT-only SQLite helper (mode=ro); connection closed in finally."""
    _log_sql(sql, params)
    print(f'SQL(sq:{os.path.basename(db)}): {" ".join(sql.split())} | params={params!r}',
          file=sys.stderr)
    conn = None
    try:
        conn = sqlite3.connect(f'file:{db}?mode=ro', uri=True, timeout=10)
        return conn.execute(sql, params).fetchall()
    finally:
        if conn is not None:
            conn.close()


# ───────────────────────────── fetches ─────────────────────────────

def fetch_trades():
    """Last 30d closed trades anchored at MAX(close_time). SELECT-only."""
    sql = """
        SELECT id, token, direction, open_time, close_time, pnl_usdt, _signal_metadata
        FROM trades
        WHERE status = 'closed'
          AND close_time >= (SELECT max(close_time) - interval '30 days'
                             FROM trades WHERE status = 'closed')
        ORDER BY id
    """
    trades = []
    for tid, tok, direc, ot, ct, pnl, meta in pg_select(sql):
        if isinstance(meta, str):
            try:
                import json
                meta = json.loads(meta)
            except Exception:
                meta = {}
        if not isinstance(meta, dict):
            meta = {}
        trades.append({
            'id': tid, 'token': (tok or '').upper(), 'dir': (direc or '').upper(),
            'open': ot, 'close': ct, 'pnl': float(pnl or 0), 'meta': meta,
        })
    return trades


def fetch_detections():
    """All detection records -> {(token, dir): sorted [created_at, ...]} for bisect join."""
    rows = sq_select(RUNTIME_DB,
                     'SELECT token, direction, created_at FROM signals '
                     'ORDER BY token, direction, created_at')
    dets = {}
    for tok, direc, created in rows:
        dets.setdefault(((tok or '').upper(), (direc or '').upper()), []).append(created)
    return dets


def join_detections(trades, dets):
    """Spec join: coin+direction+closest created_at BEFORE open_time."""
    for t in trades:
        lst = dets.get((t['token'], t['dir']))
        t['det'] = None
        t['age_min'] = None
        if not lst:
            continue
        i = bisect_right(lst, t['open'].strftime('%Y-%m-%d %H:%M:%S')) - 1
        if i < 0:
            continue
        det = datetime.strptime(lst[i], '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
        t['det'] = det
        t['age_min'] = (t['open'].astimezone(timezone.utc) - det).total_seconds() / 60.0


# ───────────────────────── candle math (local DB, same formulas as source) ─────────────────────────────

def _closes(table, token, ts_epoch, limit):
    return [r[0] for r in reversed(sq_select(
        CANDLES_DB,
        f'SELECT close FROM {table} WHERE token = ? AND ts <= ? AND is_closed = 1 '
        'ORDER BY ts DESC LIMIT ?', (token, ts_epoch, limit)))]


def cutler_rsi(closes):
    """Equal-weight Cutler RSI(14) on 1m closes — mirrors signal_schema._enrich_indicators
    (the method that produced detection-time meta.rsi_14), so drift is same-method."""
    if len(closes) < 15:
        return None
    ch = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [c for c in ch[-14:] if c > 0]
    losses = [-c for c in ch[-14:] if c < 0]
    avg_g = sum(gains) / 14 if gains else 0
    avg_l = sum(losses) / 14 if losses else 0
    return 100.0 if avg_l == 0 else 100 - 100 / (1 + avg_g / avg_l)


def vel_pct(closes, span):
    """% change over `span` closes — mirrors bb_bounce_v2 velocity filters."""
    if len(closes) < span + 1 or closes[-(span + 1)] <= 0:
        return None
    return (closes[-1] - closes[-(span + 1)]) / closes[-(span + 1)] * 100


def linreg_mom(closes):
    """%/bar linear-regression slope — mirrors bb_bounce_v2 _get_30m_momentum."""
    if len(closes) < 10:
        return None
    c = closes[-30:]
    n = len(c)
    xm = (n - 1) / 2
    ym = sum(c) / n
    num = sum((i - xm) * (c[i] - ym) for i in range(n))
    den = sum((i - xm) ** 2 for i in range(n))
    return (num / den / ym * 100) if den > 0 and ym > 0 else 0.0


def ema_gap(closes):
    """(price - EMA)/EMA * 100 with decider's 300->100->50 fallback (decider_run:6242)."""
    if not closes:
        return None
    n = len(closes)
    period = 300 if n >= 300 else 100 if n >= 100 else 50 if n >= 50 else None
    if period is None:
        return None
    k = 2 / (period + 1)
    e = closes[0]
    for v in closes[1:]:
        e = v * k + e * (1 - k)
    return (closes[-1] - e) / e * 100 if e > 0 else None


def mom_state(closes):
    """rising/flat/falling from 5-bar velocity — mirrors signal_schema.py:533."""
    v = vel_pct(closes, 5)
    if v is None:
        return None
    return 'rising' if v > MOM_STATE_VEL else 'falling' if v < -MOM_STATE_VEL else 'flat'


# ───────────────────────── G2 legs ─────────────────────────────

def epoch(dt):
    return int(dt.astimezone(timezone.utc).timestamp())


def rsi_pass(v, direction):
    """v2 RSI filter verdict at value v (imported thresholds)."""
    if direction == 'LONG':
        return BB_BOUNCE_V2_RSI_MIN <= v <= BB_BOUNCE_V2_RSI_MAX
    return v >= BB_BOUNCE_V2_SHORT_RSI_OVERBOUGHT


def mom_pass(v, direction):
    if direction == 'LONG':
        return v >= BB_BOUNCE_V2_MOM_MIN
    return v <= BB_BOUNCE_V2_SHORT_MOM_MAX


def vel_pass(v, direction):
    if direction == 'LONG':
        return v >= BB_BOUNCE_V2_VEL_MIN
    return v <= BB_BOUNCE_V2_SHORT_VEL_5M_MAX


def eval_legs(t):
    """Evaluate G2 legs for one trade. Returns dict leg -> result or None (not evaluable).

    Detect side: RSI from meta.rsi_14 (true detection value, purge-immune);
    gap from meta.gap_at_entry (stamped at decision with the signal price — one
    method note in the report); momentum state from meta.momentum_state. The raw
    v2 momentum/velocity quantities are NOT stored in metadata, so their detect
    side is evaluated at the metadata-implied detection time
    (open_time - staleness_minutes) when available, else at the joined detection
    created_at (documented; join-created_at alone is a purge surrogate for ~96%).
    Open side: always recomputed from local candles at open_time.
    """
    m = t['meta']
    out = {}
    oe = epoch(t['open'])
    det_t = None
    stal = m.get('staleness_minutes')
    if stal is not None:
        det_t = oe - int(round(float(stal) * 60))
    elif t.get('det') is not None:
        det_t = epoch(t['det'])

    # ── RSI leg ──
    det_rsi = m.get('rsi_14')
    if det_rsi is None:
        det_rsi = m.get('rsi')
    if det_rsi is None:
        out['rsi'] = None
    else:
        o = cutler_rsi(_closes('candles_1m', t['token'], oe, 50))
        if o is None:
            out['rsi'] = None
        else:
            det_rsi = float(det_rsi)
            out['rsi'] = {
                'det': det_rsi, 'open': o, 'drift': o - det_rsi,
                'flip': rsi_pass(det_rsi, t['dir']) != rsi_pass(o, t['dir']),
            }

    # ── Momentum leg ──
    has_mom_meta = ('momentum_state' in m) or ('momentum_score' in m)
    if not has_mom_meta:
        out['mom'] = None
    else:
        st_open = mom_state(_closes('candles_1m', t['token'], oe, 6))
        st_det = m.get('momentum_state')
        state_flip = (st_det in ('rising', 'falling') and st_open in ('rising', 'falling')
                      and st_det != st_open)
        res = {'state_det': st_det, 'state_open': st_open, 'state_flip': state_flip}
        if det_t is not None:
            if t['dir'] == 'LONG':
                # bb_bounce_v2_long: 30x1m linreg momentum, 15m velocity (1x1m bars)
                md = linreg_mom(_closes('candles_1m', t['token'], det_t, 30))
                mo = linreg_mom(_closes('candles_1m', t['token'], oe, 30))
                vd = vel_pct(_closes('candles_1m', t['token'], det_t, 16), 15)
                vo = vel_pct(_closes('candles_1m', t['token'], oe, 16), 15)
            else:
                # bb_bounce_v2_short: linreg + velocity over 5m bars (its _get_candles)
                md = linreg_mom(_closes('candles_5m', t['token'], det_t, 10))
                mo = linreg_mom(_closes('candles_5m', t['token'], oe, 10))
                vd = vel_pct(_closes('candles_5m', t['token'], det_t, 5), 4)
                vo = vel_pct(_closes('candles_5m', t['token'], oe, 5), 4)
            if md is not None and mo is not None:
                res['mom'] = {'det': md, 'open': mo, 'drift': mo - md,
                              'flip': mom_pass(md, t['dir']) != mom_pass(mo, t['dir'])}
            if vd is not None and vo is not None:
                res['vel'] = {'det': vd, 'open': vo, 'drift': vo - vd,
                              'flip': vel_pass(vd, t['dir']) != vel_pass(vo, t['dir'])}
        # only evaluable if at least one measurement actually landed (no fail-open)
        out['mom'] = res if (res.get('state_open') is not None
                             or 'mom' in res or 'vel' in res) else None

    # ── Gap leg ──
    if m.get('gap_at_entry') is None:
        out['gap'] = None
    else:
        o = ema_gap(_closes('candles_5m', t['token'], oe, 310))
        if o is None:
            out['gap'] = None
        else:
            d = float(m['gap_at_entry'])
            out['gap'] = {
                'det': d, 'open': o, 'drift': o - d,
                'flip': (d * o) < 0,   # zero-cross = sign flip across the EMA
            }
    return out


# ───────────────────────── aggregation ─────────────────────────────

def bucketize(v, edges, labels):
    for lab, e in zip(labels, edges):
        if abs(v) < e:
            return lab
    return labels[-1]


def age_bucket(a):
    if a < 5:
        return '<5m'
    if a < 10:
        return '5-10m'
    if a <= 30:
        return '10-30m'
    return '>30m'


def pct(xs, p):
    if not xs:
        return None
    s = sorted(xs)
    return s[min(len(s) - 1, int(p * (len(s) - 1)))]


def wr_stats(rows):
    """n, wins, WR%, avg pnl_usdt, total pnl_usdt — money ALWAYS pnl_usdt."""
    n = len(rows)
    if n == 0:
        return 0, 0, None, None, 0.0
    wins = sum(1 for r in rows if r['pnl'] > 0)
    tot = sum(r['pnl'] for r in rows)
    return n, wins, 100.0 * wins / n, tot / n, tot


def fmt_stats(n, wins, wr, avg, tot):
    """Cells only — caller wraps with '| <label> | ... |'."""
    if n == 0:
        return '0 | — | — | —'
    return f'{n} | {wr:.1f}% | {avg:+.2f} | {tot:+.2f}'


def analyze():
    trades = fetch_trades()
    dets = fetch_detections()
    join_detections(trades, dets)

    n_total = len(trades)
    joined = [t for t in trades if t['det'] is not None]
    n_joined = len(joined)
    with_meta = [t for t in trades if t['meta']]
    # trades opened inside the signals-table retention era (archive cutoff 336h)
    sig_min = sq_select(RUNTIME_DB, 'SELECT min(created_at) FROM signals')[0][0]
    era = [t for t in trades if t['open'].strftime('%Y-%m-%d %H:%M:%S') >= sig_min]
    era_joined = [t for t in era if t['det'] is not None]

    # staleness cross-check (metadata stamp of exec-time signal age)
    stal_ages = [float(t['meta']['staleness_minutes']) for t in trades
                 if t['meta'].get('staleness_minutes') is not None]
    agree = [abs(t['age_min'] - float(t['meta']['staleness_minutes']))
             for t in joined if t['meta'].get('staleness_minutes') is not None]
    close_agree = sum(1 for d in agree if d <= 3.0)

    # ── G1: signal age ──
    join_ages = [t['age_min'] for t in joined]
    g1_join = {b: [] for b in AGE_LABELS}
    for t in joined:
        g1_join[age_bucket(t['age_min'])].append(t)
    g1_stal = {b: [] for b in AGE_LABELS}
    for t in trades:
        s = t['meta'].get('staleness_minutes')
        if s is not None:
            g1_stal[age_bucket(float(s))].append(t)

    # ── G2 legs over all trades (eligible = metadata has the detection-time field) ──
    legs = {'rsi': [], 'mom_state': [], 'mom_q': [], 'vel_q': [], 'gap': []}
    leg_elig = {k: 0 for k in legs}
    for t in trades:
        t['legres'] = eval_legs(t)
        r = t['legres']
        if r.get('rsi') is not None:
            leg_elig['rsi'] += 1
            legs['rsi'].append((t, r['rsi']))
        if r.get('mom') is not None:
            mm = r['mom']
            if mm.get('state_open') is not None and mm.get('state_det') is not None:
                leg_elig['mom_state'] += 1
                legs['mom_state'].append((t, mm))
            if mm.get('mom') is not None:
                leg_elig['mom_q'] += 1
                legs['mom_q'].append((t, mm['mom']))
            if mm.get('vel') is not None:
                leg_elig['vel_q'] += 1
                legs['vel_q'].append((t, mm['vel']))
        if r.get('gap') is not None:
            leg_elig['gap'] += 1
            legs['gap'].append((t, r['gap']))

    def any_flip(t):
        r = t['legres']
        if r.get('rsi') and r['rsi']['flip']:
            return True
        if r.get('gap') and r['gap']['flip']:
            return True
        mm = r.get('mom')
        if mm:
            if mm.get('state_flip'):
                return True
            if mm.get('mom') and mm['mom']['flip']:
                return True
            if mm.get('vel') and mm['vel']['flip']:
                return True
        return False

    def evaluable(t):
        r = t['legres']
        return any(v is not None for v in r.values())

    # ── G0-G3 partition (precedence G3 > G1 age>=10m > G2 flip > G0) ──
    classes = {'G0': [], 'G1': [], 'G2': [], 'G3': []}
    g3_reasons = {'no_detection_join': 0, 'no_metadata': 0, 'no_evaluable_fields': 0}
    for t in trades:
        if t['det'] is None:
            classes['G3'].append(t)
            g3_reasons['no_detection_join'] += 1
        elif not t['meta']:
            classes['G3'].append(t)
            g3_reasons['no_metadata'] += 1
        elif t['age_min'] >= STALE_MIN:
            classes['G1'].append(t)
        elif not evaluable(t):
            classes['G3'].append(t)
            g3_reasons['no_evaluable_fields'] += 1
        elif any_flip(t):
            classes['G2'].append(t)
        else:
            classes['G0'].append(t)

    # sensitivity partition: same rules but age from metadata staleness_minutes
    sens = {'G0': [], 'G1': [], 'G2': [], 'G3': []}
    for t in trades:
        s = t['meta'].get('staleness_minutes')
        if t['det'] is None or not t['meta'] or s is None:
            sens['G3'].append(t)
        elif float(s) >= STALE_MIN:
            sens['G1'].append(t)
        elif not evaluable(t):
            sens['G3'].append(t)
        elif any_flip(t):
            sens['G2'].append(t)
        else:
            sens['G0'].append(t)

    return dict(trades=trades, n_total=n_total, joined=joined, n_joined=n_joined,
                with_meta=with_meta, sig_min=sig_min, era=era, era_joined=era_joined,
                stal_ages=stal_ages, agree=agree, close_agree=close_agree,
                join_ages=join_ages, g1_join=g1_join, g1_stal=g1_stal,
                legs=legs, leg_elig=leg_elig, classes=classes,
                g3_reasons=g3_reasons, sens=sens)


# ───────────────────────── report ─────────────────────────────

def render(a):
    L = []
    w = L.append
    lo = min(t['close'] for t in a['trades']).strftime('%Y-%m-%d %H:%M:%S')
    hi = max(t['close'] for t in a['trades']).strftime('%Y-%m-%d %H:%M:%S')
    w('# Detection-vs-Execution Reconciliation — 2026-11-20')
    w('')
    w('Descriptive only (§E-SPEC): how stale/drifted was the signal when the trade')
    w('opened, and does gap class associate with PnL? No filter recommendations.')
    w('')
    w(f'- **Window**: last 30d closed trades anchored `MAX(close_time)` → '
      f'{lo} .. {hi}, **n={a["n_total"]}** (psql `brain.trades`, status=closed).')
    w('- **Reproduce**: `python3 brain/analysis/detection_execution_reconciliation_2026-11-20.py`')
    w('- **Units**: money = `pnl_usdt` only; `trades.stop_loss` (trail-mutated) never read;')
    w('  no `pnl_pct`-vs-price comparisons (landmine #193).')
    w('- **Thresholds**: all v2 filter thresholds imported from `hermes_constants`.')
    w('')

    w('## Joins & coverage')
    w('')
    w('| Join / coverage | n | % of window |')
    w('|---|---:|---:|')
    w(f'| detection record joined (`signals`, coin+dir+closest created_at ≤ open) '
      f'| {a["n_joined"]} | {100*a["n_joined"]/a["n_total"]:.1f}% |')
    w(f'| …of trades opened inside signals-table retention (≥ {a["sig_min"]}) '
      f'| {len(a["era_joined"])}/{len(a["era"])} '
      f'| {100*len(a["era_joined"])/max(1,len(a["era"])):.1f}% of era |')
    w(f'| `_signal_metadata` non-empty | {len(a["with_meta"])} '
      f'| {100*len(a["with_meta"])/a["n_total"]:.1f}% |')
    w(f'| `staleness_minutes` present (exec-time age stamp) | {len(a["stal_ages"])} '
      f'| {100*len(a["stal_ages"])/a["n_total"]:.1f}% |')
    for lab, key in [('RSI leg evaluable (meta rsi_14 + 1m candles at open)', 'rsi'),
                     ('momentum state evaluable', 'mom_state'),
                     ('v2 momentum qty evaluable (30x1m / 10x5m linreg)', 'mom_q'),
                     ('v2 velocity qty evaluable', 'vel_q'),
                     ('gap leg evaluable (meta gap_at_entry + 5m candles at open)', 'gap')]:
        w(f'| {lab} | {a["leg_elig"][key]} | {100*a["leg_elig"][key]/a["n_total"]:.1f}% |')
    w('')
    w(f'> **Join-quality caveat (data fact, not a recommendation):** executed detection')
    w(f'> rows are purged ~1h after execution (`signal_compactor._purge_executed_signals`),')
    w(f'> so for older trades the spec join lands on an *earlier surrogate* signal, not the')
    w(f'> true parent. Cross-check vs `_signal_metadata.staleness_minutes` (stamped live at')
    ag = a['agree']
    if ag:
        w(f'> exec): |join_age − staleness| P50={pct(ag,0.5):.1f}m '
          f'P90={pct(ag,0.9):.1f}m; only {a["close_agree"]}/{len(ag)} '
          f'({100*a["close_agree"]/len(ag):.1f}%) within ±3min.')
    else:
        w('> exec): no overlapping stamps to compare.')
    w('')

    # ── G1 ──
    w('## G1 — signal age (open_time − detection created_at)')
    w('')
    ja = a['join_ages']
    w(f'**Spec-literal (detection join), n={len(ja)}:** '
      f'P50={pct(ja,0.5):.1f}m  P90={pct(ja,0.9):.1f}m  P99={pct(ja,0.99):.1f}m')
    w('')
    w('| age bucket | n | WR | avg pnl_usdt | total pnl_usdt |')
    w('|---|---:|---:|---:|---:|')
    for b in AGE_LABELS:
        n, wins, wr, avg, tot = wr_stats(a['g1_join'][b])
        w(f'| {b} | ' + fmt_stats(n, wins, wr, avg, tot) + ' |')
    w('')
    sa = a['stal_ages']
    w(f'**Cross-check — `_signal_metadata.staleness_minutes` (exec-time stamp), '
      f'n={len(sa)}:** P50={pct(sa,0.5):.1f}m  P90={pct(sa,0.9):.1f}m  '
      f'P99={pct(sa,0.99):.1f}m')
    w('')
    w('| age bucket | n | WR | avg pnl_usdt | total pnl_usdt |')
    w('|---|---:|---:|---:|---:|')
    for b in AGE_LABELS:
        n, wins, wr, avg, tot = wr_stats(a['g1_stal'][b])
        w(f'| {b} | ' + fmt_stats(n, wins, wr, avg, tot) + ' |')
    w('')
    w('> The staleness stamp is the trustworthy age (purge-immune); the join-age table')
    w('> is reported because §E-SPEC defines G1 from the detection join. Both are shown;')
    w('> neither is used to propose anything.')
    w('')

    # ── G2 ──
    w('## G2 — condition drift (detection → open)')
    w('')
    w('Detect side: `meta.rsi_14` / `meta.gap_at_entry` / `meta.momentum_state` where')
    w('present; raw v2 momentum/velocity quantities (not stored in metadata) are evaluated')
    w('at the metadata-implied detection time (`open − staleness_minutes`, else joined')
    w('created_at). Open side recomputed from local candles at `open_time` (same formulas')
    w('as the source filters). Verdict flips use thresholds **imported from')
    w('`hermes_constants`**: LONG RSI band [`BB_BOUNCE_V2_RSI_MIN`, `BB_BOUNCE_V2_RSI_MAX`],')
    w('SHORT `≥ BB_BOUNCE_V2_SHORT_RSI_OVERBOUGHT`; momentum `BB_BOUNCE_V2_MOM_MIN` /')
    w('`BB_BOUNCE_V2_SHORT_MOM_MAX`; velocity `BB_BOUNCE_V2_VEL_MIN` /')
    w('`BB_BOUNCE_V2_SHORT_VEL_5M_MAX`. Gap has no v2 threshold → sign flip = zero-cross')
    w('(price crossing the EMA).')
    w('')

    def leg_bucket_table(title, rows, edges, labels, drift_key='drift'):
        w(f'### {title}')
        w('')
        w('| abs(drift) bucket | n | WR | avg pnl_usdt | total pnl_usdt |')
        w('|---|---:|---:|---:|---:|')
        agg = {lab: [] for lab in labels}
        for t, r in rows:
            agg[bucketize(r[drift_key], edges, labels)].append(t)
        for lab in labels:
            n, wins, wr, avg, tot = wr_stats(agg[lab])
            w(f'| {lab} | ' + fmt_stats(n, wins, wr, avg, tot) + ' |')
        flips = [t for t, r in rows if r.get('flip')]
        nofl = [t for t, r in rows if not r.get('flip')]
        w('')
        w('| threshold verdict | n | WR | avg pnl_usdt | total pnl_usdt |')
        w('|---|---:|---:|---:|---:|')
        n, wins, wr, avg, tot = wr_stats(flips)
        w('| SIGN FLIP across threshold | ' + fmt_stats(n, wins, wr, avg, tot) + ' |')
        n, wins, wr, avg, tot = wr_stats(nofl)
        w('| no flip | ' + fmt_stats(n, wins, wr, avg, tot) + ' |')
        w('')

    leg_bucket_table(f'RSI drift (detect `meta.rsi_14` → Cutler RSI(14) at open), '
                     f'evaluable n={len(a["legs"]["rsi"])}',
                     a['legs']['rsi'], RSI_EDGES, RSI_LABELS)

    # momentum state table
    w('### Momentum state flip (`meta.momentum_state` → recomputed at open)')
    w('')
    w('| state verdict | n | WR | avg pnl_usdt | total pnl_usdt |')
    w('|---|---:|---:|---:|---:|')
    ms = a['legs']['mom_state']
    flips = [t for t, r in ms if r['state_flip']]
    nofl = [t for t, r in ms if not r['state_flip']]
    n, wins, wr, avg, tot = wr_stats(flips)
    w('| rising↔falling flip | ' + fmt_stats(n, wins, wr, avg, tot) + ' |')
    n, wins, wr, avg, tot = wr_stats(nofl)
    w('| no direction flip | ' + fmt_stats(n, wins, wr, avg, tot) + ' |')
    w('')
    w(f'(evaluable n={len(ms)}; flat transitions counted as no direction flip)')
    w('')

    leg_bucket_table(f'v2 momentum quantity drift (LONG: 30×1m linreg; SHORT: 10×5m '
                     f'linreg), evaluable n={len(a["legs"]["mom_q"])}',
                     a['legs']['mom_q'], MOM_EDGES, MOM_LABELS)
    leg_bucket_table(f'v2 velocity quantity drift (LONG: 15m 1m-bars; SHORT: 4×5m bars), '
                     f'evaluable n={len(a["legs"]["vel_q"])}',
                     a['legs']['vel_q'], VEL_EDGES, VEL_LABELS)
    leg_bucket_table(f'gap drift (`meta.gap_at_entry` → EMA300/100/50 gap at open, pp), '
                     f'evaluable n={len(a["legs"]["gap"])}',
                     a['legs']['gap'], GAP_EDGES, GAP_LABELS)

    # ── G3 ──
    w('## G3 — metadata missing (coverage)')
    w('')
    g3 = a['classes']['G3']
    w(f'- **G3 n={len(g3)} ({100*len(g3)/a["n_total"]:.1f}% of window)** — '
      f'coverage = {100*(a["n_total"]-len(g3))/a["n_total"]:.1f}% classifiable.')
    w(f'  - no detection join: {a["g3_reasons"]["no_detection_join"]} '
      f'(signals table retains ~14d: min `{a["sig_min"]}` + 1h executed-row purge)')
    w(f'  - empty `_signal_metadata`: {a["g3_reasons"]["no_metadata"]}')
    w(f'  - joined+meta but zero evaluable drift fields (age<10m only): '
      f'{a["g3_reasons"]["no_evaluable_fields"]}')
    n, wins, wr, avg, tot = wr_stats(g3)
    w(f'- G3 outcome: n={n} WR={wr:.1f}% avg={avg:+.2f} total={tot:+.2f} pnl_usdt'
      if n else '- G3 outcome: n=0')
    w('')

    # ── key findings ──
    w('## Key findings — gap class × n / WR / pnl (pnl_usdt basis)')
    w('')
    w('Partition precedence: **G3** (unjoinable) > **G1** (age ≥10m) > **G2** '
      '(sign-flip drift, age <10m) > **G0** (clean). Drift tables above are computed '
      'over ALL evaluable trades, so drift×PnL is visible regardless of class.')
    w('')
    w('| class | definition | n | WR | avg pnl_usdt | total pnl_usdt |')
    w('|---|---|---:|---:|---:|---:|')
    defs = {'G0': 'joined, age<10m, no sign-flip drift',
            'G1': 'joined, signal age ≥10m',
            'G2': 'joined, age<10m, ≥1 sign-flip across v2 thresholds',
            'G3': 'absent/unjoinable detection record or metadata'}
    for c in ['G0', 'G1', 'G2', 'G3']:
        n, wins, wr, avg, tot = wr_stats(a['classes'][c])
        w(f'| **{c}** | {defs[c]} | ' + fmt_stats(n, wins, wr, avg, tot) + ' |')
    n = sum(len(a['classes'][c]) for c in ['G0', 'G1', 'G2', 'G3'])
    chk(n == a['n_total'], f'class partition {n} != {a["n_total"]}')
    w(f'| total | | {n} | | | |')
    w('')
    w('**Sensitivity** — same rules but age from `staleness_minutes` (purge-immune; '
      'only trades carrying the stamp):')
    w('')
    w('| class | n | WR | avg pnl_usdt | total pnl_usdt |')
    w('|---|---:|---:|---:|---:|')
    for c in ['G0', 'G1', 'G2', 'G3']:
        n, wins, wr, avg, tot = wr_stats(a['sens'][c])
        w(f'| {c} | ' + fmt_stats(n, wins, wr, avg, tot) + ' |')
    w('')
    w('## Method notes')
    w('')
    w('- Detection join: `SELECT token, direction, created_at FROM signals` (mode=ro),')
    w('  coin+direction, closest `created_at ≤ open_time` (bisect), deterministic by `id`.')
    w('- `meta.gap_at_entry` is stamped at decision time from the signal price vs a')
    w('  decision-time EMA (`decider_run.py:6233`); its detect→open drift therefore')
    w('  measures decision→fill gap movement — noted, not corrected (§E-SPEC fields).')
    w('- RSI method = Cutler equal-weight (matches how `meta.rsi_14` was produced,')
    w('  `signal_schema._enrich_indicators`); applying it against the v2 RSI thresholds')
    w('  follows the AGENTS.md CFX precedent (detect 44.6 vs `RSI_MIN=35`).')
    w('- All SQL SELECT-only; SQLite `mode=ro`; connections/cursors closed in `finally`.')
    w('')
    return '\n'.join(L) + '\n'


# ───────────────────────── selfcheck ─────────────────────────────

def selfcheck():
    a = analyze()
    n_total = a['n_total']

    # SELECT-only enforcement over everything actually executed
    for s in SQL_LOG:
        chk(s.lstrip().upper().startswith('SELECT'), f'non-SELECT executed: {s[:60]}')

    # join arithmetic
    chk(a['n_joined'] + (n_total - a['n_joined']) == n_total, 'join split')
    chk(all(t['age_min'] is None or t['age_min'] >= -1e-9 for t in a['joined']),
        'negative join age')
    chk(all(float(s) >= 0 for s in a['stal_ages']), 'negative staleness age')

    # G1 bucket coverage: every joined trade in exactly one age bucket
    bsum = sum(len(a['g1_join'][b]) for b in AGE_LABELS)
    chk(bsum == a['n_joined'], f'age buckets {bsum} != joined {a["n_joined"]}')
    for t in a['joined']:
        chk(age_bucket(t['age_min']) in AGE_LABELS, 'age bucket coverage')
    chk(len(a['g1_join']['<5m']) + len(a['g1_join']['5-10m'])
        == sum(1 for t in a['joined'] if t['age_min'] < 10), 'G1/G0 age boundary')
    ssum = sum(len(a['g1_stal'][b]) for b in AGE_LABELS)
    chk(ssum == len(a['stal_ages']), f'staleness buckets {ssum} != {len(a["stal_ages"])}')

    # class partition: exactly one class per trade, all four sum to window
    seen = []
    for c in ['G0', 'G1', 'G2', 'G3']:
        seen.extend(id(t) for t in a['classes'][c])
    chk(len(seen) == len(set(seen)) == n_total,
        f'class partition {len(seen)}/{len(set(seen))} != {n_total}')
    # G1 definition == joined ∧ meta ∧ age>=10
    exp_g1 = [t for t in a['trades']
              if t['det'] is not None and t['meta'] and t['age_min'] >= STALE_MIN]
    chk(len(exp_g1) == len(a['classes']['G1']), 'G1 definition')

    # per-leg arithmetic: bucket counts == evaluable == flip + noflip
    def chk_leg(name, rows, edges, labels, fkey='flip'):
        agg = {lab: 0 for lab in labels}
        for t, r in rows:
            agg[bucketize(r['drift'], edges, labels)] += 1
        chk(sum(agg.values()) == len(rows), f'{name} bucket coverage')
        nf = sum(1 for t, r in rows if r.get(fkey))
        chk(nf + (len(rows) - nf) == len(rows), f'{name} flip split')
        # pnl arithmetic: bucket totals sum to leg total
        tot = sum(t['pnl'] for t, r in rows)
        bt = sum(sum(t['pnl'] for t, r in rows
                     if bucketize(r['drift'], edges, labels) == lab) for lab in labels)
        chk(abs(tot - bt) < 0.005, f'{name} pnl sum {tot} vs {bt}')

    chk_leg('rsi', a['legs']['rsi'], RSI_EDGES, RSI_LABELS)
    chk_leg('mom_q', a['legs']['mom_q'], MOM_EDGES, MOM_LABELS)
    chk_leg('vel_q', a['legs']['vel_q'], VEL_EDGES, VEL_LABELS)
    chk_leg('gap', a['legs']['gap'], GAP_EDGES, GAP_LABELS)

    # bucket edge coverage (pure)
    chk(age_bucket(4.99) == '<5m' and age_bucket(5.0) == '5-10m'
        and age_bucket(9.99) == '5-10m' and age_bucket(10.0) == '10-30m'
        and age_bucket(30.0) == '10-30m' and age_bucket(30.01) == '>30m', 'age edges')
    chk(bucketize(4.99, RSI_EDGES, RSI_LABELS) == '<5'
        and bucketize(5.0, RSI_EDGES, RSI_LABELS) == '5-10'
        and bucketize(20.0, RSI_EDGES, RSI_LABELS) == '>=20', 'drift edges')

    # thresholds are the imported hermes_constants values (no local reassignment)
    import hermes_constants as hc
    chk(BB_BOUNCE_V2_RSI_MIN == hc.BB_BOUNCE_V2_RSI_MIN
        and BB_BOUNCE_V2_RSI_MAX == hc.BB_BOUNCE_V2_RSI_MAX
        and BB_BOUNCE_V2_SHORT_RSI_OVERBOUGHT == hc.BB_BOUNCE_V2_SHORT_RSI_OVERBOUGHT
        and BB_BOUNCE_V2_MOM_MIN == hc.BB_BOUNCE_V2_MOM_MIN
        and BB_BOUNCE_V2_SHORT_MOM_MAX == hc.BB_BOUNCE_V2_SHORT_MOM_MAX
        and BB_BOUNCE_V2_VEL_MIN == hc.BB_BOUNCE_V2_VEL_MIN
        and BB_BOUNCE_V2_SHORT_VEL_5M_MAX == hc.BB_BOUNCE_V2_SHORT_VEL_5M_MAX,
        'threshold import integrity')

    # units guard: money stats derive from pnl_usdt only (wr_stats reads r['pnl'])
    n, wins, wr, avg, tot = wr_stats(a['trades'])
    chk(abs(tot - sum(t['pnl'] for t in a['trades'])) < 0.005, 'total pnl arithmetic')
    chk(wins == sum(1 for t in a['trades'] if t['pnl'] > 0), 'win count arithmetic')
    chk(wr is None or 0 <= wr <= 100, 'wr range')

    print(f'SELFCHECK PASS ({_CHK[0]} asserts)')
    return a


def main():
    ap = argparse.ArgumentParser(
        description='Detection-vs-execution reconciliation (read-only, 30d, G0-G3).')
    ap.add_argument('--selfcheck', action='store_true',
                    help='assert join arithmetic + bucket coverage + SELECT-only, exit 0/1')
    ap.add_argument('--report', metavar='PATH',
                    help='also write the markdown report to PATH')
    args = ap.parse_args()

    if args.selfcheck:
        try:
            selfcheck()
        except AssertionError as e:
            print(f'SELFCHECK FAIL: {e}')
            sys.exit(1)
        return

    a = analyze()
    md = render(a)
    sys.stdout.write(md)
    if args.report:
        with open(args.report, 'w') as f:
            f.write(md)
        print(f'[report written: {args.report}]', file=sys.stderr)


if __name__ == '__main__':
    main()
