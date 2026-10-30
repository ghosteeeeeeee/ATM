#!/usr/bin/env python3
"""shadow_redundancy_deepdive_v2_2026-10-30.py

V2 — corrections per own-conclusions verdict
(brain/verdicts/2026-10-30_shadow-redundancy-own-conclusions.md, commit 5ed3bcf8).
V1 arithmetic was verified faithful; v2 fixes INFERENCE, PROVENANCE, FRAMING:

  C1  Cluster-robust statistics: every per-gate test also reported as
      token-clustered and day-clustered t-tests (episodes are dependent).
  C2  F3 reworked: singles vs multi-source split (comma in source); excess
      RECOMPUTED from current candles (17% of stored expiry_shadow values did
      not reproduce); no more "protects at every band" narrative.
  C3  F1 runner baseline: per-token unconditional MFE≥2% share (the gate's own
      tokens), plus baseline-sensitivity (cross-mean / median / BTC).
  C4  Sensitivity disclosure: coalescing 30/60/120min and solo windows
      ±5/±10/±15min; knife-edge labels flagged explicitly.
  C5  Provenance: event frame = fresh reparse of SURVIVING pipeline.log
      (Oct 10 20:49 → Oct 30, current regexes incl. the Oct-22 `:?` fix)
      UNION gate_shadow.db rows before the log start (Oct 4-10 20:49, marked
      db-only — raw archives no longer exist, unverifiable). Recorder-capture
      gaps Oct 11-22 quantified by comparing DB rows vs reparse in overlap.
  C6  t5_shadow queries moved into this engine (single-script reproducibility).

Outputs: analysis/exports/v2_gate_events.tsv, v2_gate_summary.tsv,
         v2_expiry_summary.tsv; stdout → analysis/shadow_redundancy_deepdive_v2.out
"""
import sys
import os
import re
import sqlite3
from datetime import datetime, timezone
from collections import defaultdict

sys.path.insert(0, '/root/.hermes/scripts')
from paths import HERMES_DATA, HERMES_LOG_DIR

BRAIN = os.path.join(os.path.dirname(HERMES_DATA), 'brain')
CANDLES = os.path.join(HERMES_DATA, 'candles.db')
PIPELINE_LOG = os.path.join(HERMES_LOG_DIR, 'pipeline.log')
EXPORTS = '/root/.hermes/analysis/exports'
HORIZONS = {'30m': 6, '1h': 12, '4h': 48}
EPISODE_GAP = 3600
OOS_SPLIT = datetime(2026, 10, 20, 0, 0, tzinfo=timezone.utc).timestamp()
LOG_START = datetime(2026, 10, 10, 20, 49, 1, tzinfo=timezone.utc).timestamp()

# recorder's CURRENT regexes, verbatim from scripts/gate_shadow.py (Oct-22 `:?` fix)
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
    """t-test on cluster means (token / day). Returns (p, n_clusters)."""
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

# ── C5: event frame = reparse(surviving log) ∪ db-only tail ──────────────────
def build_frame():
    reparse = {}
    with open(PIPELINE_LOG, 'r', errors='replace') as f:
        for line in f:
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
            if ts < LOG_START:
                continue
            bucket = int(ts) // 600 * 600
            reparse.setdefault((gate, tok, d, bucket), ts)
    frame = [(ts, gate, tok, d, 'log-reparse') for (gate, tok, d, b), ts in reparse.items()]
    # db-only tail: DB rows before log start (raw archives gone)
    conn = sqlite3.connect(os.path.join(BRAIN, 'gate_shadow.db'))
    try:
        db_rows = conn.execute(
            "SELECT gate, token, direction, blocked_at FROM events ORDER BY blocked_at").fetchall()
    finally:
        conn.close()
    db_only = 0
    for gate, tok, d, bat in db_rows:
        try:
            ts = datetime.fromisoformat(bat).timestamp()
        except (ValueError, TypeError):
            continue
        if ts < LOG_START:
            frame.append((ts, gate, tok.upper(), d.upper(), 'db-only'))
            db_only += 1
    frame.sort()
    return frame, len(reparse), db_only

# ── candles / engine (unchanged from verified v1) ────────────────────────────
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

def market_mean(bucket_ts, hname, mode='mean'):
    key = (bucket_ts, hname, mode)
    if key in _MKT_CACHE:
        return _MKT_CACHE[key]
    d = market_fwd_dicts()[hname].get(bucket_ts)
    if not d or len(d) < 20:
        _MKT_CACHE[key] = None
        return None
    vals = list(d.values())
    m = sum(vals) / len(vals) if mode == 'mean' else (
        sorted(vals)[len(vals) // 2] if mode == 'median' else d.get('BTC'))
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

def token_uncond_mfe2(tok, direction):
    """C3: token's UNCONDITIONAL share of 5m buckets with dir-MFE4h >= 2% (window)."""
    rows = candles(tok)
    if len(rows) < 49:
        return None
    hit = tot = 0
    for i in range(0, len(rows) - 49, 6):  # hourly sample of buckets
        o = rows[i][1]
        if o <= 0:
            continue
        if direction == 'LONG':
            mfe = (max(r[3] for r in rows[i:i + 49]) / o - 1.0) * 100.0
        else:
            mfe = (1.0 - min(r[4] for r in rows[i:i + 49]) / o) * 100.0
        tot += 1
        if mfe >= 2.0:
            hit += 1
    return hit / tot if tot >= 40 else None

def main():
    out = []
    def P(s=''):
        print(s)
        out.append(str(s))

    frame, n_rep, n_dbo = build_frame()
    P(f"frame: {len(frame)} events (reparse {n_rep} from surviving log Oct10-30; "
      f"db-only {n_dbo} from Oct 4-10 — raw archives no longer exist, UNVERIFIABLE)")
    from datetime import datetime as dt
    P(f"window: {dt.fromtimestamp(frame[0][0], timezone.utc):%m-%d %H:%M} → "
      f"{dt.fromtimestamp(frame[-1][0], timezone.utc):%m-%d %H:%M}")

    # C5b: capture-rate audit — DB rows in overlap vs reparse in overlap
    conn = sqlite3.connect(os.path.join(BRAIN, 'gate_shadow.db'))
    db_overlap = defaultdict(int)
    db_all = defaultdict(int)
    for gate, tok, d, bat in conn.execute("SELECT gate, token, direction, blocked_at FROM events"):
        try:
            ts = datetime.fromisoformat(bat).timestamp()
        except (ValueError, TypeError):
            continue
        db_all[gate] += 1
        if ts >= LOG_START:
            db_overlap[gate] += 1
    conn.close()
    rep_all = defaultdict(int)
    for ts, gate, tok, d, prov in frame:
        if prov == 'log-reparse':
            rep_all[gate] += 1
    P()
    P("── RECORDER CAPTURE AUDIT (overlap window Oct 10 20:49+; reparse = ground truth) " + "─" * 8)
    P(f"  {'gate':26} {'db_in_overlap':>13} {'reparse':>8} {'capture%':>9}")
    cap_rows = []
    for gate in sorted(rep_all, key=lambda g: -rep_all[g])[:20]:
        dbn = db_overlap.get(gate, 0)
        repn = rep_all[gate]
        cap = dbn / repn * 100 if repn else 100
        cap_rows.append((gate, dbn, repn, cap))
        P(f"  {gate:26} {dbn:13} {repn:8} {cap:8.0f}%")

    # enrich frame
    enriched = []
    for ts, gate, tok, d, prov in frame:
        rows = candles(tok)
        fm = fwd_metrics(rows, ts, d) if rows else None
        if fm is None:
            continue
        bucket = int(ts + 299) // 300 * 300
        exc = {}
        for h in HORIZONS:
            mb = market_mean(bucket, h, 'mean')
            exc[h] = (fm[{'30m': 'f30', '1h': 'f1h', '4h': 'f4h'}[h]]
                      - (mb if d == 'LONG' else -mb)) if mb is not None else None
        exc_med = None
        mbm = market_mean(bucket, '4h', 'median')
        if mbm is not None:
            exc_med = fm['f4h'] - (mbm if d == 'LONG' else -mbm)
        regime = btc_vel30(ts)
        enriched.append((ts, gate, tok, d, prov, fm['f30'], fm['f1h'], fm['f4h'],
                         exc['30m'], exc['1h'], exc['4h'], exc_med, fm['mfe'], regime))
    P(f"enriched (with forward data): {len(enriched)} / {len(frame)}")

    os.makedirs(EXPORTS, exist_ok=True)
    with open(os.path.join(EXPORTS, 'v2_gate_events.tsv'), 'w') as f:
        f.write("ts\tgate\ttoken\tdirection\tprovenance\tfwd_30m\tfwd_1h\tfwd_4h\t"
                "excess_4h_mean_base\texcess_4h_med_base\texcess_1h\texcess_30m\tmfe_4h\tbtc_vel30\n")
        for e in enriched:
            f.write('\t'.join('' if v is None else (
                f'{v:.4f}' if isinstance(v, float) else str(v)) for v in e) + '\n')

    # episodes at 60min + C4 sensitivity at 30/120
    def coalesce(gap):
        by_key = defaultdict(list)
        for e in enriched:
            by_key[(e[1], e[2], e[3])].append(e)
        eps = []
        for key, lst in by_key.items():
            lst.sort(key=lambda x: x[0])
            last = None
            for e in lst:
                if last is None or e[0] - last > gap:
                    eps.append(e)
                last = e[0]
        eps.sort()
        return eps
    episodes = coalesce(EPISODE_GAP)
    eps30 = coalesce(1800)
    eps120 = coalesce(7200)
    P(f"episodes: 30min={len(eps30)}  60min={len(episodes)}  120min={len(eps120)}")

    # C4 solo windows
    def solo_flags(eps, win):
        td = defaultdict(list)
        for e in eps:
            td[(e[2], e[3])].append((e[0], e[1]))
        flags = []
        for e in eps:
            flags.append(all(g == e[1] or abs(t2 - e[0]) > win
                             for t2, g in td[(e[2], e[3])]))
        return flags
    solo10 = solo_flags(episodes, 600)
    solo5 = solo_flags(episodes, 300)
    solo15 = solo_flags(episodes, 900)

    gate_eps = defaultdict(list)
    gate_meta = defaultdict(lambda: {'solo10': [], 'solo5': [], 'solo15': []})
    for e, s10, s5, s15 in zip(episodes, solo10, solo5, solo15):
        gate_eps[e[1]].append(e)
        gate_meta[e[1]]['solo10'].append(s10)
        gate_meta[e[1]]['solo5'].append(s5)
        gate_meta[e[1]]['solo15'].append(s15)
    eps30_by = defaultdict(list)
    for e in eps30:
        eps30_by[e[1]].append(e)
    eps120_by = defaultdict(list)
    for e in eps120:
        eps120_by[e[1]].append(e)

    n_gates = len(gate_eps)
    bonf = 0.05 / n_gates
    P()
    P(f"── PER-GATE TABLE v2 (60min eps; cluster p = token|day t-tests; "
      f"Bonferroni p<{bonf:.4f}) — {n_gates} gates " + "─" * 20)
    hdr = (f"{'gate':26} {'eps':>5} {'solo10':>6} │ {'ex4h':>8} {'p_w':>7} "
           f"{'p_tok':>7} {'p_day':>7} │ {'ex_med':>8} │ {'mfe2':>6} {'own_mfe2':>8}")
    P(hdr)
    P('─' * len(hdr))
    rows_out = []
    for gate in sorted(gate_eps, key=lambda g: -len(gate_eps[g])):
        recs = gate_eps[gate]
        n = len(recs)
        vals = [r[10] for r in recs]
        s4 = summarize(vals)
        if s4 is None:
            continue
        p_tok, k_tok = cluster_p(vals, [r[2] for r in recs])
        p_day, k_day = cluster_p(vals, [int(r[0] // 86400) for r in recs])
        smed = summarize([r[11] for r in recs])
        mfe2 = sum(1 for r in recs if r[12] is not None and r[12] >= 2.0) / n * 100
        # C3: own-token unconditional mfe2 (weighted by episodes)
        own = [token_uncond_mfe2(r[2], r[3]) for r in recs]
        own_vals = [v for v in own if v is not None]
        own_w = sum(own_vals) / len(own_vals) * 100 if own_vals else float('nan')
        solo = sum(gate_meta[gate]['solo10']) / n * 100
        p_w_s = f"{s4['p']:.4f}" if s4['p'] is not None else "n/a"
        p_t_s = f"{p_tok:.4f}" if p_tok is not None else "n/a"
        p_d_s = f"{p_day:.4f}" if p_day is not None else "n/a"
        P(f"{gate:26} {n:5} {solo:5.0f}% │ {s4['mean']:+8.3f} {p_w_s:>7} "
          f"{p_t_s:>7} {p_d_s:>7} │ {smed['mean'] if smed else float('nan'):+8.3f} │ "
          f"{mfe2:5.1f}% {own_w:7.1f}%")
        rows_out.append(dict(gate=gate, n=n, solo=solo, s4=s4, smed=smed, mfe2=mfe2,
                             own=own_w, p_tok=p_tok, p_day=p_day, k_tok=k_tok, k_day=k_day))

    # C4 sensitivity
    P()
    P("── C4 SENSITIVITY (ex4h mean / solo%) — coalescing × solo window " + "─" * 35)
    P(f"  {'gate':26} {'60m/10':>14} {'30m/10':>14} {'120m/10':>14} {'solo5/15':>12}")
    sens_watch = []
    for r in rows_out[:20]:
        g = r['gate']
        def em(eps):
            v = [e[10] for e in eps if e[10] is not None]
            return sum(v) / len(v) if v else float('nan')
        s5 = sum(gate_meta[g]['solo5']) / len(gate_meta[g]['solo5']) * 100
        s15 = sum(gate_meta[g]['solo15']) / len(gate_meta[g]['solo15']) * 100
        P(f"  {g:26} {r['s4']['mean']:+7.3f}/{r['solo']:3.0f}% "
          f"{em(eps30_by[g]):+7.3f}/{r['solo']:3.0f}% {em(eps120_by[g]):+7.3f}/{r['solo']:3.0f}% "
          f"{s5:3.0f}%/{s15:3.0f}%")
        # knife-edge flags
        if abs(r['solo'] - 25) < 3 or abs(s5 - 25) < 3 or abs(s15 - 25) < 3:
            sens_watch.append((g, 'solo-cutoff', r['solo'], s5, s15))
        p30 = summarize([e[10] for e in eps30_by[g]])
        if p30 and p30['p'] is not None and p30['p'] < bonf and (r['s4']['p'] is None or r['s4']['p'] >= bonf):
            sens_watch.append((g, 'p-flips@30m', r['s4']['p'], p30['p'], None))
    if sens_watch:
        P("  KNIFE-EDGE FLAGS:")
        for g, kind, a, b, c in sens_watch:
            P(f"    {g:26} {kind}: {a} / {b} / {c}")

    # verdicts with cluster stats (C1)
    P()
    P("── VERDICTS v2 (cluster-robust) " + "─" * 73)
    P("WORKS = |ex4h|>=0.10 AND (p_w<p_bonf AND at least one cluster p<0.05).")
    P("NO-EDGE = |ex4h|<0.10 AND p_w>=bonf.")
    P("HARM-CANDIDATE = ex4h>+0.10 AND cluster-consistent; PROTECTIVE-CANDIDATE = <−0.10 similarly.")
    P()
    works, harm, noedge, knife, insuff = [], [], [], [], []
    for r in rows_out:
        if r['n'] < 16 or r['s4']['p'] is None:
            insuff.append(r)
            continue
        clusters_ok = ((r['p_tok'] is not None and r['p_tok'] < 0.05) or
                       (r['p_day'] is not None and r['p_day'] < 0.05))
        if abs(r['s4']['mean']) >= 0.10 and r['s4']['p'] < bonf:
            if clusters_ok:
                (harm if r['s4']['mean'] > 0 else works).append(r)
            else:
                knife.append((r, 'cluster-ns'))
        elif abs(r['s4']['mean']) < 0.10 and r['s4']['p'] >= bonf:
            noedge.append(r)
        else:
            knife.append((r, 'nominal'))
    P("WORKS — blocks below-market signals (cluster-robust):")
    for r in works:
        P(f"  {r['gate']:26} n={r['n']:5} ex4h={r['s4']['mean']:+.3f} p_w={r['s4']['p']:.4f} "
          f"p_tok={r['p_tok'] if r['p_tok'] is not None else float('nan'):.4f} "
          f"p_day={r['p_day'] if r['p_day'] is not None else float('nan'):.4f} solo={r['solo']:.0f}%")
    if not works:
        P("  (none)")
    P("HARM-CANDIDATES — blocked signals beat market (cluster-consistent):")
    for r in harm:
        P(f"  {r['gate']:26} n={r['n']:5} ex4h={r['s4']['mean']:+.3f} p_w={r['s4']['p']:.4f} "
          f"p_tok={r['p_tok'] if r['p_tok'] is not None else float('nan'):.4f} "
          f"p_day={r['p_day'] if r['p_day'] is not None else float('nan'):.4f} "
          f"own_mfe2={r['own']:.1f}% vs blocked {r['mfe2']:.1f}%")
    if not harm:
        P("  (none)")
    P("NO-EDGE (|ex|<0.10, p>=bonf):")
    for r in sorted(noedge, key=lambda x: -x['n']):
        P(f"  {r['gate']:26} n={r['n']:5} ex4h={r['s4']['mean']:+.3f} solo={r['solo']:.0f}%")
    P(f"KNIFE-EDGE / NOMINAL: {len(knife)} — " +
      '; '.join(f"{r['gate']}({why})" for r, why in knife[:12]))
    P(f"INSUFFICIENT (n<16): {len(insuff)}")

    # OOS
    P()
    P("── OOS (Oct 10-20 vs Oct 20-30, 60min eps) " + "─" * 56)
    for r in rows_out[:20]:
        g = r['gate']
        a = [e[10] for e in gate_eps[g] if e[0] < OOS_SPLIT and e[10] is not None]
        b = [e[10] for e in gate_eps[g] if e[0] >= OOS_SPLIT and e[10] is not None]
        if not a or not b:
            continue
        ma, mb = sum(a) / len(a), sum(b) / len(b)
        P(f"  {g:26} n1={len(a):4} {ma:+7.3f}  n2={len(b):4} {mb:+7.3f}  "
          f"same={'YES' if ma * mb > 0 else 'NO'}")

    # C2: expiry recompute — singles vs multi
    P()
    P("── C2 EXPIRY RECOMPUTE FROM CANDLES (singles vs multi-source) " + "─" * 44)
    conn = sqlite3.connect(os.path.join(BRAIN, 'expiry_shadow.db'))
    try:
        exp_rows = conn.execute(
            "SELECT token, direction, confidence, source, created_at FROM events"
        ).fetchall()
    finally:
        conn.close()
    import calendar
    bands = defaultdict(lambda: {'s': [], 'm': []})
    for tok, d, conf, src, created in exp_rows:
        if not created or conf is None:
            continue
        try:
            ets = calendar.timegm(datetime.strptime(created, '%Y-%m-%d %H:%M:%S').timetuple())
        except (ValueError, TypeError):
            continue
        rows = candles(tok)
        fm = fwd_metrics(rows, ets, d) if rows else None
        if fm is None:
            continue
        bucket = int(ets + 299) // 300 * 300
        mb = market_mean(bucket, '4h', 'mean')
        if mb is None:
            continue
        exc = fm['f4h'] - (mb if d == 'LONG' else -mb)
        band = ('a <60' if conf < 60 else 'b 60-69' if conf < 70 else
                'c 70-79' if conf < 80 else 'd 80-89' if conf < 90 else 'e 90+')
        key = 's' if (src or '').find(',') < 0 else 'm'
        bands[band][key].append(exc)
    P(f"  {'band':8} {'single_n':>8} {'single_ex':>10} {'multi_n':>8} {'multi_ex':>10}")
    exp_out = []
    for band in sorted(bands):
        s, m = bands[band]['s'], bands[band]['m']
        sm, mm = (sum(s) / len(s) if s else float('nan')), (sum(m) / len(m) if m else float('nan'))
        P(f"  {band:8} {len(s):8} {sm:+10.4f} {len(m):8} {mm:+10.4f}")
        exp_out.append((band, len(s), sm, len(m), mm))
    # singles cluster test pooled conf>=80
    pooled = bands['c 70-79']['s'] + bands['d 80-89']['s'] + bands['e 90+']['s']
    if pooled:
        P(f"  conf>=70 SINGLE-source pooled: n={len(pooled)} mean={sum(pooled)/len(pooled):+.4f}%")

    with open(os.path.join(EXPORTS, 'v2_expiry_summary.tsv'), 'w') as f:
        f.write("band\tsingle_n\tsingle_ex4h\tmulti_n\tmulti_ex4h\n")
        for band, ns, sm, nm, mm in exp_out:
            f.write(f"{band}\t{ns}\t{sm:.4f}\t{nm}\t{mm:.4f}\n")

    # C6: t5 in-engine
    P()
    P("── C6 t5_shadow (in-engine) " + "─" * 70)
    conn = sqlite3.connect(os.path.join(BRAIN, 't5_shadow.db'))
    try:
        for row in conn.execute(
                "SELECT shadow_decision, COUNT(*), SUM(closed),"
                " SUM(CASE WHEN would_pnl IS NOT NULL THEN 1 ELSE 0 END),"
                " ROUND(AVG(would_pnl),4) FROM decisions GROUP BY 1 ORDER BY 2 DESC"):
            P(f"  {row[0]:14} n={row[1]:6} closed={row[2] or 0:5} with_pnl={row[3] or 0:5} avg={row[4]}")
    finally:
        conn.close()

    # summary exports
    with open(os.path.join(EXPORTS, 'v2_gate_summary.tsv'), 'w') as f:
        f.write("gate\tepisodes\tsolo10_pct\tex4h_mean\tex4h_median_base\tp_wilcoxon\t"
                "p_token_cluster\tp_day_cluster\tmfe2_share\town_token_mfe2_unconditional\n")
        for r in rows_out:
            med_s = f"{r['smed']['mean']:.4f}" if r['smed'] else ''
            pw_s = f"{r['s4']['p']:.5f}" if r['s4']['p'] is not None else ''
            pt_s = f"{r['p_tok']:.5f}" if r['p_tok'] is not None else ''
            pd_s = f"{r['p_day']:.5f}" if r['p_day'] is not None else ''
            f.write(f"{r['gate']}\t{r['n']}\t{r['solo']:.1f}\t{r['s4']['mean']:.4f}\t"
                    f"{med_s}\t{pw_s}\t{pt_s}\t{pd_s}\t{r['mfe2']:.1f}\t{r['own']:.1f}\n")

    with open('/root/.hermes/analysis/shadow_redundancy_deepdive_v2.out', 'w') as f:
        f.write('\n'.join(out))
    P()
    P("written: analysis/shadow_redundancy_deepdive_v2.out + exports/v2_*.tsv")

if __name__ == '__main__':
    main()
