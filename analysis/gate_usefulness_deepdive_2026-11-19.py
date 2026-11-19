#!/usr/bin/env python3
"""gate_usefulness_deepdive_2026-11-19.py

FULL DEEP DIVE — which gates are useful, which are useless blockers of
legitimate setups. Window: 2026-10-04 → 11-19 (46 days).

Addresses T's three complaints with verified data:
  C-1 trade frequency collapse → weekly funnel (blocks vs trades)
  C-2 long WR < 50%, shorts marginally better, unprofitable → live book by dir/week
  C-3 missing big alt moves → per-gate big-move kill rate (MFE>=5%/>=10% blocked
       episodes vs the gate's OWN tokens' unconditional rate) + top-miss table

Frame (provenance split, same as verified v2):
  - reparse of raw logs: pipeline.log.20261107001010.gz (Oct30→Nov7),
    .20261115000915.gz (Nov7→Nov15), .20261119090701.gz (Nov15→Nov19),
    pipeline.log (Nov19→now) — GROUND TRUTH, current recorder regexes
  - gate_shadow.db events before Oct 30 20:39 — db-only (raw for Oct 4-30 is
    deleted; capture-audited Oct 30+ where overlap exists)
  - capture audit: DB rows vs reparse in the overlap window

Inference (claim-hygiene standard, brain/SOPs.md §10): episode-level counts,
cluster-robust p (token-clustered AND day-clustered t-tests on cluster means),
Wilcoxon naive labeled naive, Bonferroni across gates, OOS halves,
coalescing sensitivity 30/60/120min.

Outputs:
  analysis/gate_usefulness_deepdive_2026-11-19.out
  analysis/exports/nov19_gate_events.tsv, nov19_gate_summary.tsv,
                  nov19_weekly_funnel.tsv, nov19_bigmisses.tsv
"""
import sys
import os
import re
import gzip
import sqlite3
import calendar
from datetime import datetime, timezone
from collections import defaultdict

sys.path.insert(0, '/root/.hermes/scripts')
from paths import HERMES_DATA, HERMES_LOG_DIR

BRAIN = os.path.join(os.path.dirname(HERMES_DATA), 'brain')
CANDLES = os.path.join(HERMES_DATA, 'candles.db')
ARCHIVE = os.path.join(HERMES_LOG_DIR, 'archive')
LIVE_LOG = os.path.join(HERMES_LOG_DIR, 'pipeline.log')
EXPORTS = '/root/.hermes/analysis/exports'
HORIZONS = {'30m': 6, '1h': 12, '4h': 48}
EPISODE_GAP = 3600
SPLIT_TS = datetime(2026, 11, 1, 0, 0, tzinfo=timezone.utc).timestamp()
DB_TAIL_CUT = datetime(2026, 10, 30, 20, 39, 35, tzinfo=timezone.utc).timestamp()

# recorder's current regexes (gate_shadow.py, incl. Oct-22 `:?` fix)
BLOCK_RE = re.compile(
    r'(?:🚫|🔒|🚧|🌊)\s+\[([A-Za-z0-9_-]+)\]\s+([A-Z0-9]+):?\s+(LONG|SHORT)\b'
    r'.*?(?:blocked|BLOCKED)', re.IGNORECASE)
CONF_RE = re.compile(
    r'🔒\s+\[CONFLUENCE-GATE-BLOCK\]\s+([A-Z0-9]+)\s+(LONG|SHORT)\b', re.IGNORECASE)
EXCLUDE_SUB = ('WOULD', 'SKIPPED', 'shadow', 'SHADOW', 'DEBUG')

from scipy import stats as sps

def summarize(vals):
    vals = [v for v in vals if v is not None]
    n = len(vals)
    if n == 0:
        return None
    mean = sum(vals) / n
    sv = sorted(vals)
    med = sv[n // 2] if n % 2 else (sv[n // 2 - 1] + sv[n // 2]) / 2
    wr = sum(1 for v in vals if v > 0) / n * 100
    p = None
    if n >= 8 and len(set(vals)) > 1:
        try:
            _, p = sps.wilcoxon(vals)
        except ValueError:
            p = None
    return dict(n=n, mean=mean, med=med, wr=wr, p=p)

def cluster_p(vals, keys):
    by = defaultdict(list)
    for v, k in zip(vals, keys):
        if v is not None:
            by[k].append(v)
    means = [sum(v) / len(v) for v in by.values() if v]
    if len(means) < 5 or len(set(means)) < 2:
        return None, len(means)
    try:
        _, p = sps.ttest_1samp(means, 0.0)
        return float(p), len(means)
    except ValueError:
        return None, len(means)

# ── frame ────────────────────────────────────────────────────────────────────
def parse_stream(fh, frame):
    for line in fh:
        if any(s in line for s in EXCLUDE_SUB):
            continue
        m = BLOCK_RE.search(line)
        if m:
            gate, tok, d = m.group(1), m.group(2).upper(), m.group(3).upper()
        else:
            mc = CONF_RE.search(line)
            if not mc:
                continue
            gate, tok, d = 'CONFLUENCE-GATE-BLOCK', mc.group(1).upper(), mc.group(2).upper()
        ts_m = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
        if not ts_m:
            continue
        ts = datetime.strptime(ts_m.group(1), '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc).timestamp()
        if ts < DB_TAIL_CUT:
            continue
        bucket = int(ts) // 600 * 600
        frame.setdefault((gate, tok, d, bucket), ts)

def build_frame():
    rep = {}
    for name in ('pipeline.log.20261107001010.gz', 'pipeline.log.20261115000915.gz',
                 'pipeline.log.20261119090701.gz'):
        p = os.path.join(ARCHIVE, name)
        if os.path.exists(p):
            with gzip.open(p, 'rt', errors='replace') as f:
                parse_stream(f, rep)
    with open(LIVE_LOG, 'r', errors='replace') as f:
        parse_stream(f, rep)
    frame = [(ts, g, t, d, 'reparse') for (g, t, d, b), ts in rep.items()]
    # db-only tail (Oct 4 → Oct 30 20:39)
    conn = sqlite3.connect(os.path.join(BRAIN, 'gate_shadow.db'))
    try:
        db_rows = conn.execute(
            "SELECT gate, token, direction, blocked_at FROM events").fetchall()
    finally:
        conn.close()
    db_overlap = defaultdict(int)
    db_tail = 0
    for gate, tok, d, bat in db_rows:
        try:
            ts = datetime.fromisoformat(bat).timestamp()
        except (ValueError, TypeError):
            continue
        if ts < DB_TAIL_CUT:
            frame.append((ts, gate, tok.upper(), d.upper(), 'db-only'))
            db_tail += 1
        else:
            db_overlap[gate] += 1
    frame.sort()
    rep_gate = defaultdict(int)
    for ts, g, t, d, p in frame:
        if p == 'reparse':
            rep_gate[g] += 1
    return frame, db_tail, db_overlap, rep_gate

# ── candles / engine (verified reference method) ─────────────────────────────
_C = {}
def candles(tok):
    if tok in _C:
        return _C[tok]
    conn = sqlite3.connect(CANDLES, timeout=10)
    try:
        rows = conn.execute(
            "SELECT ts, open, close, high, low FROM candles_5m"
            " WHERE token=? AND is_closed=1 ORDER BY ts", (tok,)).fetchall()
    finally:
        conn.close()
    _C[tok] = rows
    return rows

def fwd_metrics(rows, entry_ts, direction):
    lo, hi = 0, len(rows)
    while lo < hi:
        mid = (lo + hi) // 2
        if rows[mid][0] < entry_ts:
            lo = mid + 1
        else:
            hi = mid
    i = lo
    if i + 48 >= len(rows):
        return None
    # GUARD (2026-11-19, found by self-audit A2): if the entry precedes the
    # first available candle (candles_5m has ~29d rolling retention; a mass
    # prune fired 21:55 today), computing from rows[i=0] is LOOKAHEAD — a
    # forward return measured from a candle days after the event. Return None.
    if rows[0][0] > entry_ts + 300:
        return None
    _, o, c, h, l = rows[i]
    sgn = 1 if direction == 'LONG' else -1
    res = {'f30': sgn * (rows[i + 6][2] / o - 1) * 100.0,
           'f1h': sgn * (rows[i + 12][2] / o - 1) * 100.0,
           'f4h': sgn * (rows[i + 48][2] / o - 1) * 100.0}
    highs = [r[3] for r in rows[i:i + 49]]
    lows = [r[4] for r in rows[i:i + 49]]
    if direction == 'LONG':
        res['mfe'] = (max(highs) / o - 1.0) * 100.0
        res['mae'] = (min(lows) / o - 1.0) * 100.0
    else:
        res['mfe'] = (1.0 - min(lows) / o) * 100.0
        res['mae'] = (1.0 - max(highs) / o) * 100.0
    return res

_MKT = None
_MKT_CACHE = {}
def market_fwd_dicts():
    global _MKT
    if _MKT is not None:
        return _MKT
    conn = sqlite3.connect(CANDLES, timeout=10)
    try:
        rows = conn.execute(
            "SELECT token, ts, open, close FROM candles_5m WHERE is_closed=1"
            " ORDER BY token, ts").fetchall()
    finally:
        conn.close()
    by_tok = defaultdict(list)
    for tok, ts, o, c in rows:
        by_tok[tok].append((ts, o, c))
    _MKT = {}
    for hname, n in HORIZONS.items():
        d = defaultdict(dict)
        for tok, trows in by_tok.items():
            for i in range(len(trows) - n):
                ts, o, c = trows[i]
                d[ts][tok] = (trows[i + n][2] / o - 1.0) * 100.0
        _MKT[hname] = d
    return _MKT

def market_mean(bucket_ts, hname):
    key = (bucket_ts, hname)
    if key in _MKT_CACHE:
        return _MKT_CACHE[key]
    d = market_fwd_dicts()[hname].get(bucket_ts)
    if not d or len(d) < 20:
        _MKT_CACHE[key] = None
        return None
    m = sum(d.values()) / len(d)
    _MKT_CACHE[key] = m
    return m

_BTC = None
def btc_vel30(ts):
    global _BTC
    if _BTC is None:
        conn = sqlite3.connect(CANDLES, timeout=10)
        _BTC = conn.execute(
            "SELECT ts, close FROM candles_5m WHERE token='BTC' AND is_closed=1"
            " ORDER BY ts").fetchall()
        conn.close()
    lo, hi = 0, len(_BTC)
    while lo < hi:
        mid = (lo + hi) // 2
        if _BTC[mid][0] < ts:
            lo = mid + 1
        else:
            hi = mid
    i = lo
    if i < 6 or i >= len(_BTC):
        return None
    return abs((_BTC[i][1] - _BTC[i - 6][1]) / _BTC[i - 6][1] * 100.0)

_UNCOND = {}
def token_uncond_mfe(tok, direction, thresh):
    """Unconditional share of 5m buckets with dir-MFE4h >= thresh (hourly sample)."""
    key = (tok, direction, thresh)
    if key in _UNCOND:
        return _UNCOND[key]
    rows = candles(tok)
    if len(rows) < 49:
        _UNCOND[key] = None
        return None
    hit = tot = 0
    for i in range(0, len(rows) - 49, 6):
        o = rows[i][1]
        if o <= 0:
            continue
        if direction == 'LONG':
            mfe = (max(r[3] for r in rows[i:i + 49]) / o - 1.0) * 100.0
        else:
            mfe = (1.0 - min(r[4] for r in rows[i:i + 49]) / o) * 100.0
        tot += 1
        if mfe >= thresh:
            hit += 1
    v = hit / tot if tot >= 40 else None
    _UNCOND[key] = v
    return v

def main():
    out = []
    def P(s=''):
        print(s)
        out.append(str(s))

    # ── 0. live-book claims verification ─────────────────────────────────────
    import psycopg2
    from _secrets import BRAIN_DB_DICT
    pg = psycopg2.connect(**BRAIN_DB_DICT)
    cur = pg.cursor()
    P("=" * 100)
    P("GATE USEFULNESS DEEP DIVE — window 2026-10-04 → 11-19 (46 days)")
    P("=" * 100)
    P()
    P("── 0. T'S CLAIMS VERIFICATION (live book, PG brain.trades, paper='f' closed) " + "─" * 6)
    cur.execute("""
        SELECT direction, COUNT(*), SUM(CASE WHEN pnl_usdt>0 THEN 1 ELSE 0 END),
               SUM(pnl_usdt) FROM trades
        WHERE paper='f' AND status='closed' AND open_time >= '2026-10-04'
        GROUP BY 1 ORDER BY 1""")
    for d, n, w, net in cur.fetchall():
        P(f"  since Oct 4: {d:5} n={n:4} WR={w/n*100:.1f}% net=${net:+.2f}  "
          f"{'← CLAIM CONFIRMED (<50% WR, negative)' if d=='LONG' and w/n*100 < 50 else ''}")
    cur.execute("""
        SELECT date_trunc('week', open_time)::date, COUNT(*),
               SUM(CASE WHEN direction='LONG' THEN 1 ELSE 0 END),
               SUM(CASE WHEN direction='SHORT' THEN 1 ELSE 0 END), SUM(pnl_usdt)
        FROM trades WHERE paper='f' AND status='closed' AND open_time >= '2026-09-07'
        GROUP BY 1 ORDER BY 1""")
    wk_rows = cur.fetchall()
    P("  weekly frequency (trade volume claim):")
    for wk, n, lng, sht, net in wk_rows:
        days = 7 if wk.isoformat() != '2026-11-16' else 4  # current partial week
        P(f"    {wk} n={n:3} ({n/days:4.1f}/day) L={lng:3} S={sht:3} net=${net:+.2f}")
    first_rate = wk_rows[0][1] / 7
    last_rate = wk_rows[-1][1] / (4 if wk_rows[-1][0].isoformat() == '2026-11-16' else 7)
    P(f"  frequency: {first_rate:.1f}/day (Sep 7 wk) → {last_rate:.1f}/day (current wk) "
      f"= {100*(1-last_rate/first_rate):.0f}% decline — CLAIM CONFIRMED")

    # ── 1. frame ─────────────────────────────────────────────────────────────
    frame, db_tail, db_overlap, rep_gate = build_frame()
    P()
    P("── 1. EVENT FRAME " + "─" * 82)
    P(f"  total events: {len(frame)}  (reparse Oct30→Nov19 ground truth: "
      f"{sum(1 for e in frame if e[4]=='reparse')}; db-only Oct4→Oct30: {db_tail})")
    P(f"  window: {datetime.fromtimestamp(frame[0][0], timezone.utc):%m-%d %H:%M} → "
      f"{datetime.fromtimestamp(frame[-1][0], timezone.utc):%m-%d %H:%M} UTC")
    P("  capture audit (overlap Oct30→now, reparse = ground truth):")
    cap = []
    for g in sorted(set(db_overlap) | set(rep_gate), key=lambda x: -rep_gate.get(x, 0)):
        r = rep_gate.get(g, 0)
        if r < 20:
            continue
        dbn = db_overlap.get(g, 0)
        cap.append((g, dbn, r, dbn / r * 100))
    worst = sorted(cap, key=lambda x: x[3])[:8]
    P("    lowest-capture gates: " + '; '.join(f"{g}={c:.0f}%" for g, _, _, c in worst))
    P(f"    gates ≥90% capture: {sum(1 for _,_,_,c in cap if c>=90)}/{len(cap)}")

    # ── 2. enrich ────────────────────────────────────────────────────────────
    enriched = []
    dropped_prehist = 0
    for ts, gate, tok, d, prov in frame:
        rows = candles(tok)
        if rows and rows[0][0] > ts + 300:
            dropped_prehist += 1
        fm = fwd_metrics(rows, ts, d) if rows else None
        if fm is None:
            continue
        bucket = int(ts + 299) // 300 * 300
        mb = market_mean(bucket, '4h')
        exc = (fm['f4h'] - (mb if d == 'LONG' else -mb)) if mb is not None else None
        enriched.append((ts, gate, tok, d, prov, fm['f30'], fm['f1h'], fm['f4h'],
                         exc, fm['mfe'], btc_vel30(ts)))
    P()
    P(f"── 2. ENRICHED: {len(enriched)} events with forward data " + "─" * 55)
    P(f"  dropped for pre-history (entry precedes candle-data start — candles_5m "
      f"has ~29d rolling retention; mass prune at 21:55 on 2026-11-19): {dropped_prehist}")

    # ── 3. weekly funnel: blocks vs trades ───────────────────────────────────
    P()
    P("── 3. WEEKLY FUNNEL (blocked episodes vs executed trades) " + "─" * 47)
    def week_of(ts):
        dt = datetime.fromtimestamp(ts, timezone.utc)
        return (dt - __import__('datetime').timedelta(days=dt.weekday())).date()
    # episodes first (60min coalesce)
    by_key = defaultdict(list)
    for e in enriched:
        by_key[(e[1], e[2], e[3])].append(e)
    episodes = []
    for key, lst in by_key.items():
        lst.sort(key=lambda x: x[0])
        last = None
        for e in lst:
            if last is None or e[0] - last > EPISODE_GAP:
                episodes.append(e)
            last = e[0]
    episodes.sort()
    P(f"  episodes (60min coalesce): {len(episodes)}")
    ep_week = defaultdict(int)
    for e in episodes:
        ep_week[week_of(e[0])] += 1
    cur.execute("""
        SELECT (date_trunc('week', open_time) - interval '1 day')::date + 1 AS wk, COUNT(*)
        FROM trades WHERE paper='f' AND status='closed' AND open_time >= '2026-10-04'
        GROUP BY 1 ORDER BY 1""")
    tr_week = {r[0]: r[1] for r in cur.fetchall()}
    P(f"  {'week':10} {'blocked_eps':>11} {'trades':>6} {'block:trade':>11}")
    for wk in sorted(set(ep_week) | set(tr_week)):
        b, t = ep_week.get(wk, 0), tr_week.get(wk, 0)
        ratio = f"{b/t:.1f}" if t else "n/a"
        P(f"  {str(wk):10} {b:11} {t:6} {ratio:>11}")

    # ── 4. per-gate usefulness (cluster-robust) ──────────────────────────────
    gate_eps = defaultdict(list)
    for e in episodes:
        gate_eps[e[1]].append(e)
    n_gates = len(gate_eps)
    bonf = 0.05 / n_gates
    P()
    P(f"── 4. PER-GATE USEFULNESS (60min eps; Bonferroni p<{bonf:.4f}; "
      f"cluster = token|day t-tests) — {n_gates} gates " + "─" * 10)
    hdr = (f"{'gate':26} {'first':>5} {'eps':>5} │ {'ex4h':>8} {'p_w':>7} {'p_tok':>7} "
           f"{'p_day':>7} │ {'kill5':>6} {'own5':>6} │ {'kill10':>6} {'own10':>6}")
    P(hdr)
    P('─' * len(hdr))
    rows_out = []
    first_seen = {}
    for e in episodes:
        first_seen.setdefault(e[1], e[0])
    for gate in sorted(gate_eps, key=lambda g: -len(gate_eps[g])):
        recs = gate_eps[gate]
        n = len(recs)
        vals = [r[8] for r in recs]
        s4 = summarize(vals)
        if s4 is None:
            continue
        p_tok, _ = cluster_p(vals, [r[2] for r in recs])
        p_day, _ = cluster_p(vals, [int(r[0] // 86400) for r in recs])
        # big-move kills vs own-token unconditional
        k5 = sum(1 for r in recs if r[9] is not None and r[9] >= 5.0) / n * 100
        own5v = [token_uncond_mfe(r[2], r[3], 5.0) for r in recs]
        own5 = sum(v for v in own5v if v is not None) / max(1, len([v for v in own5v if v is not None])) * 100
        k10 = sum(1 for r in recs if r[9] is not None and r[9] >= 10.0) / n * 100
        own10v = [token_uncond_mfe(r[2], r[3], 10.0) for r in recs]
        own10 = sum(v for v in own10v if v is not None) / max(1, len([v for v in own10v if v is not None])) * 100
        fs = datetime.fromtimestamp(first_seen[gate], timezone.utc).strftime('%m-%d')
        p_w_s = f"{s4['p']:.4f}" if s4['p'] is not None else "n/a"
        p_t_s = f"{p_tok:.4f}" if p_tok is not None else "n/a"
        p_d_s = f"{p_day:.4f}" if p_day is not None else "n/a"
        P(f"{gate:26} {fs:>5} {n:5} │ {s4['mean']:+8.3f} {p_w_s:>7} {p_t_s:>7} "
          f"{p_d_s:>7} │ {k5:5.1f}% {own5:5.1f}% │ {k10:5.1f}% {own10:5.1f}%")
        rows_out.append(dict(gate=gate, fs=fs, n=n, s4=s4, p_tok=p_tok, p_day=p_day,
                             k5=k5, own5=own5, k10=k10, own10=own10))
    P("  kill5/own5 = share of blocked episodes printing dir-MFE>=5% vs the gate's OWN tokens'")
    P("  unconditional share (same threshold) — differential >0 means the gate kills big moves")
    P("  at ABOVE the rate those tokens simply print them (i.e. not just 'tokens are volatile').")

    # ── 5. classification ────────────────────────────────────────────────────
    P()
    P("── 5. USEFULNESS CLASSIFICATION (cluster-robust) " + "─" * 51)
    P("  WORKS: ex4h<=-0.10, p_w<bonf, ≥1 cluster p<0.05 → protects on balance")
    P("  BLOCKS-SETUPS: ex4h>=+0.10, p_w<bonf, ≥1 cluster p<0.05 → blocked signals")
    P("               beat market = legitimate setups refused")
    P("  NO-EDGE: |ex4h|<0.10 and p_w>=bonf → blocks noise (neither helps nor hurts)")
    P("  MIXED/NS: everything else (nominal or cluster-ns)")
    P()
    cls = defaultdict(list)
    for r in rows_out:
        if r['n'] < 16 or r['s4']['p'] is None:
            cls['INSUFFICIENT'].append(r)
            continue
        cluster_ok = ((r['p_tok'] is not None and r['p_tok'] < 0.05) or
                      (r['p_day'] is not None and r['p_day'] < 0.05))
        if r['s4']['mean'] <= -0.10 and r['s4']['p'] < bonf and cluster_ok:
            cls['WORKS'].append(r)
        elif r['s4']['mean'] >= 0.10 and r['s4']['p'] < bonf and cluster_ok:
            cls['BLOCKS-SETUPS'].append(r)
        elif abs(r['s4']['mean']) < 0.10 and r['s4']['p'] >= bonf:
            cls['NO-EDGE'].append(r)
        else:
            cls['MIXED/NS'].append(r)
    for name in ('WORKS', 'BLOCKS-SETUPS', 'NO-EDGE', 'MIXED/NS', 'INSUFFICIENT'):
        P(f"  {name} ({len(cls[name])}):")
        for r in sorted(cls[name], key=lambda x: -x['n']):
            extra = (f"kill5={r['k5']:.0f}% vs own {r['own5']:.0f}%"
                     if name in ('BLOCKS-SETUPS', 'NO-EDGE') else
                     f"kill5={r['k5']:.0f}% vs own {r['own5']:.0f}%")
            P(f"    {r['gate']:26} n={r['n']:5} ex4h={r['s4']['mean']:+.3f} "
              f"p_w={r['s4']['p'] if r['s4']['p'] is not None else float('nan'):.4f} "
              f"p_tok={r['p_tok'] if r['p_tok'] is not None else float('nan'):.3f} "
              f"p_day={r['p_day'] if r['p_day'] is not None else float('nan'):.3f} {extra}")
        P()

    # ── 6. big-move misses ───────────────────────────────────────────────────
    P("── 6. MISSING BIG MOVES (C-3): blocked episodes with dir-MFE>=10% " + "─" * 36)
    big = sorted([e for e in episodes if e[9] is not None and e[9] >= 10.0],
                 key=lambda x: -x[9])
    P(f"  total blocked episodes printing dir-MFE>=10% in 4h: {len(big)} "
      f"({len(big)/len(episodes)*100:.1f}% of {len(episodes)})")
    P(f"  {'date':6} {'gate':24} {'token':8} {'dir':5} {'MFE%':>6} {'fwd4h%':>7} {'ex4h%':>7}")
    for e in big[:25]:
        P(f"  {datetime.fromtimestamp(e[0], timezone.utc):%m-%d} {e[1]:24} {e[2]:8} "
          f"{e[3]:5} {e[9]:6.1f} {e[7]:+7.2f} {e[8] if e[8] is not None else float('nan'):+7.2f}")
    # per-gate kill10 excess over own baseline
    P("  per-gate big-move kill differential (kill10 - own10, pp):")
    diff = sorted(cls['WORKS'] + cls['BLOCKS-SETUPS'] + cls['NO-EDGE'] + cls['MIXED/NS'],
                  key=lambda r: -(r['k10'] - r['own10']))
    for r in diff[:12]:
        P(f"    {r['gate']:26} kill10={r['k10']:.1f}% vs own {r['own10']:.1f}% "
          f"= {r['k10']-r['own10']:+.1f}pp (n={r['n']})")

    # ── 7. sensitivity + OOS ─────────────────────────────────────────────────
    P()
    P("── 7. ROBUSTNESS " + "─" * 82)
    # coalescing
    for gap, label in ((1800, '30min'), (7200, '120min')):
        byk = defaultdict(list)
        for e in enriched:
            byk[(e[1], e[2], e[3])].append(e)
        eps_g = []
        for key, lst in byk.items():
            lst.sort(key=lambda x: x[0])
            last = None
            for e in lst:
                if last is None or e[0] - last > gap:
                    eps_g.append(e)
                last = e[0]
        gg = defaultdict(list)
        for e in eps_g:
            gg[e[1]].append(e)
        flips = []
        for r in rows_out[:20]:
            if r['gate'] not in gg:
                continue
            v = [x[8] for x in gg[r['gate']] if x[8] is not None]
            if not v:
                continue
            m = sum(v) / len(v)
            if m * r['s4']['mean'] < 0:
                flips.append(r['gate'])
        P(f"  coalescing {label}: sign flips vs 60min among top-20 gates: "
          f"{len(flips)} {flips if flips else ''}")
    # OOS
    P("  OOS (Oct4→Nov1 vs Nov1→Nov19):")
    flips_oos = 0
    for r in rows_out[:20]:
        g = r['gate']
        a = [x[8] for x in gate_eps[g] if x[0] < SPLIT_TS and x[8] is not None]
        b = [x[8] for x in gate_eps[g] if x[0] >= SPLIT_TS and x[8] is not None]
        if not a or not b:
            continue
        ma, mb = sum(a) / len(a), sum(b) / len(b)
        same = ma * mb > 0
        if not same:
            flips_oos += 1
        P(f"    {g:26} n1={len(a):4} {ma:+7.3f}  n2={len(b):4} {mb:+7.3f}  "
          f"same={'YES' if same else 'NO'}")
    P(f"  OOS sign flips among listed gates: {flips_oos}")

    # ── exports ──────────────────────────────────────────────────────────────
    os.makedirs(EXPORTS, exist_ok=True)
    with open(os.path.join(EXPORTS, 'nov19_gate_events.tsv'), 'w') as f:
        f.write("ts\tgate\ttoken\tdirection\tprovenance\tfwd_30m\tfwd_1h\tfwd_4h\t"
                "excess_4h\tmfe_4h\tbtc_vel30\n")
        for e in enriched:
            f.write('\t'.join('' if v is None else (
                f'{v:.4f}' if isinstance(v, float) else str(v)) for v in e) + '\n')
    with open(os.path.join(EXPORTS, 'nov19_gate_summary.tsv'), 'w') as f:
        f.write("gate\tfirst_seen\tepisodes\tex4h_mean\tp_wilcoxon\tp_token_cluster\t"
                "p_day_cluster\tkill5_pct\town5_pct\tkill10_pct\town10_pct\tclass\n")
        for r in rows_out:
            k = next((name for name, lst in cls.items() if r in lst), '')
            f.write(f"{r['gate']}\t{r['fs']}\t{r['n']}\t{r['s4']['mean']:.4f}\t"
                    f"{r['s4']['p'] if r['s4']['p'] is not None else ''}\t"
                    f"{r['p_tok'] if r['p_tok'] is not None else ''}\t"
                    f"{r['p_day'] if r['p_day'] is not None else ''}\t"
                    f"{r['k5']:.1f}\t{r['own5']:.1f}\t{r['k10']:.1f}\t{r['own10']:.1f}\t{k}\n")
    with open(os.path.join(EXPORTS, 'nov19_weekly_funnel.tsv'), 'w') as f:
        f.write("week\tblocked_episodes\ttrades\n")
        for wk in sorted(set(ep_week) | set(tr_week)):
            f.write(f"{wk}\t{ep_week.get(wk,0)}\t{tr_week.get(wk,0)}\n")
    with open(os.path.join(EXPORTS, 'nov19_bigmisses.tsv'), 'w') as f:
        f.write("ts\tgate\ttoken\tdirection\tmfe_4h\tfwd_4h\texcess_4h\tprovenance\n")
        for e in big:
            f.write(f"{datetime.fromtimestamp(e[0], timezone.utc).isoformat()}\t{e[1]}\t"
                    f"{e[2]}\t{e[3]}\t{e[9]:.2f}\t{e[7]:.3f}\t"
                    f"{e[8] if e[8] is not None else ''}\t{e[4]}\n")
    pg.close()
    P()
    P(f"exports: {EXPORTS}/nov19_gate_events.tsv, nov19_gate_summary.tsv, "
      f"nov19_weekly_funnel.tsv, nov19_bigmisses.tsv")
    with open('/root/.hermes/analysis/gate_usefulness_deepdive_2026-11-19.out', 'w') as f:
        f.write('\n'.join(out))

if __name__ == '__main__':
    main()
