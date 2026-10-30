#!/usr/bin/env python3
"""shadow_redundancy_deepdive_2026-10-30.py

WHICH GATES/FILTERS ARE REDUNDANT? — deep dive over 26 days of shadow data.

Data sources (all pre-existing, zero live-path code):
  1. brain/gate_shadow.db events — 50,478 block events, 50 gates, 2026-10-04→10-30.
     Recorded by the hourly gate_shadow recorder (BLOCK_RE parser: 🚫🔒🚧🌊
     emoji + blocked/denied word; coverage caveat documented in report).
  2. brain/expiry_shadow.db events — 28,634 confluence-expired signals (D3).
  3. brain/t5_shadow.db decisions — cell-admission shadow (P4).

Strong counterfactual (the audited engine — cross-validated to <0.10% by an
independent implementation in audit/gate_counterfactual_verify.md):
  entry = OPEN of first 5m candle with ts >= blocked_at (no lookahead);
  fwd +30m/+1h/+4h; MFE/MAE 4h; excess = sgn × (fwd − cross-sectional market
  mean) — DIRECTION-SIGNED (the unsigned baseline manufactured false findings
  on 2026-10-08; that fix is why this engine is the reference).

Redundancy verdict per gate (claim-hygiene standard, CEO D3 2026-10-09):
  ECONOMICALLY redundant: |excess| small + p >= Bonferroni (blocks noise).
  FUNCTIONALLY redundant: fires solo rarely (another gate blocks same token+dir).
  Verdicts require BOTH episode-level counts and first-seen dates.

Outputs:
  analysis/exports/gate_events_enriched.tsv   (every event + computed metrics)
  analysis/exports/gate_summary.tsv           (per-gate table)
  analysis/exports/expiry_summary.tsv         (confluence-expiry answer)
  stdout → analysis/shadow_redundancy_deepdive_2026-10-30.out
"""
import sys
import os
import sqlite3
from datetime import datetime, timezone
from collections import defaultdict

sys.path.insert(0, '/root/.hermes/scripts')
from paths import HERMES_DATA

BRAIN = os.path.join(os.path.dirname(HERMES_DATA), 'brain')
CANDLES = os.path.join(HERMES_DATA, 'candles.db')
EXPORTS = '/root/.hermes/analysis/exports'
HORIZONS = {'30m': 6, '1h': 12, '4h': 48}
EPISODE_GAP = 3600
OOS_SPLIT = datetime(2026, 10, 17, 0, 0, tzinfo=timezone.utc).timestamp()

# ── load gate_shadow events ──────────────────────────────────────────────────
def load_events():
    conn = sqlite3.connect(os.path.join(BRAIN, 'gate_shadow.db'))
    try:
        rows = conn.execute(
            "SELECT id, gate, token, direction, blocked_at, would_trade, would_win, would_pnl"
            " FROM events ORDER BY blocked_at").fetchall()
    finally:
        conn.close()
    out = []
    for eid, gate, tok, d, bat, wt, ww, wp in rows:
        try:
            ts = datetime.fromisoformat(bat).timestamp()
        except (ValueError, TypeError):
            continue
        out.append((ts, gate, tok.upper(), d.upper(), eid, wt, ww, wp))
    return out

# ── candles ──────────────────────────────────────────────────────────────────
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

# market baseline: per-horizon per-token (ts->fwd) dicts, mean per bucket
_MKT = None
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

_MKT_CACHE = {}
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

# BTC regime at a timestamp (|30m vel|)
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

# ── stats ────────────────────────────────────────────────────────────────────
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

def main():
    out = []
    def P(s=''):
        print(s)
        out.append(str(s))

    events = load_events()
    P(f"gate_shadow events loaded: {len(events)}  "
      f"({datetime.fromtimestamp(events[0][0], timezone.utc):%m-%d} → "
      f"{datetime.fromtimestamp(events[-1][0], timezone.utc):%m-%d})")

    # enrich every event
    enriched = []
    no_cov = 0
    for ts, gate, tok, d, eid, wt, ww, wp in events:
        rows = candles(tok)
        bucket = int(ts + 299) // 300 * 300
        fm = fwd_metrics(rows, ts, d) if rows else None
        if fm is None:
            no_cov += 1
            enriched.append((ts, gate, tok, d, eid, None, None, None, None, None, None, None, None, wt, ww, wp))
            continue
        excs = {}
        for h in HORIZONS:
            mb = market_mean(bucket, h)
            excs[h] = (fm[{'30m': 'f30', '1h': 'f1h', '4h': 'f4h'}[h]]
                       - (mb if d == 'LONG' else -mb)) if mb is not None else None
        regime = btc_vel30(ts)
        enriched.append((ts, gate, tok, d, eid, fm['f30'], fm['f1h'], fm['f4h'],
                         excs['30m'], excs['1h'], excs['4h'], fm['mfe'], regime,
                         wt, ww, wp))
    P(f"enriched: {len(enriched) - no_cov} with forward data (no coverage: {no_cov})")

    # export enriched events
    os.makedirs(EXPORTS, exist_ok=True)
    with open(os.path.join(EXPORTS, 'gate_events_enriched.tsv'), 'w') as f:
        f.write("ts\tgate\ttoken\tdirection\tevent_id\tfwd_30m\tfwd_1h\tfwd_4h\t"
                "excess_30m\texcess_1h\texcess_4h\tmfe_4h\tbtc_vel30\t"
                "shadow_would_trade\tshadow_would_win\tshadow_would_pnl\n")
        for e in enriched:
            f.write('\t'.join('' if v is None else (
                f'{v:.4f}' if isinstance(v, float) else str(v)) for v in e) + '\n')

    # episodes (60min gap per gate+token+direction) — first event of each
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
    P(f"episodes (gap>{EPISODE_GAP // 60}min): {len(episodes)}")

    # solo analysis: another gate on same token+dir within ±10min
    tok_dir_ts = defaultdict(list)
    for e in episodes:
        tok_dir_ts[(e[2], e[3])].append((e[0], e[1]))
    solo_flags = []
    for e in episodes:
        lst = tok_dir_ts[(e[2], e[3])]
        solo = all(g == e[1] or abs(ts2 - e[0]) > 600 for ts2, g in lst)
        solo_flags.append(solo)

    # first-seen per gate
    first_seen = {}
    for e in events:
        first_seen.setdefault(e[1], e[0])

    # ── per-gate table ───────────────────────────────────────────────────────
    gate_eps = defaultdict(list)
    gate_solo = defaultdict(list)
    for e, solo in zip(episodes, solo_flags):
        gate_eps[e[1]].append(e)
        gate_solo[e[1]].append(solo)

    n_gates = len(gate_eps)
    bonf = 0.05 / n_gates
    P()
    P(f"── PER-GATE REDUNDANCY TABLE (episodes; direction-signed excess; "
      f"Bonferroni p<{bonf:.4f}) — {n_gates} gates " + "─" * 30)
    hdr = (f"{'gate':26} {'first':>5} {'eps':>5} {'solo%':>5} │ "
           f"{'ex4h':>8} {'med':>7} {'wr':>5} {'p':>7} │ {'ex1h':>8} │ "
           f"{'mfe≥2%':>7} {'regime':>6}")
    P(hdr)
    P('─' * len(hdr))
    rows_out = []
    for gate in sorted(gate_eps, key=lambda g: -len(gate_eps[g])):
        recs = gate_eps[gate]
        n = len(recs)
        solo_pct = sum(gate_solo[gate]) / n * 100 if n else 0
        s4 = summarize([r[10] for r in recs])
        s1 = summarize([r[9] for r in recs])
        mfe2 = sum(1 for r in recs if r[11] is not None and r[11] >= 2.0) / n * 100 if n else 0
        # dominant regime
        chop = sum(1 for r in recs if r[12] is not None and r[12] < 0.3)
        known = sum(1 for r in recs if r[12] is not None)
        regime = f"{chop / known * 100:.0f}%chop" if known else "n/a"
        fs = datetime.fromtimestamp(first_seen[gate], timezone.utc).strftime('%m-%d')
        if s4 is None:
            continue
        p_s = f"{s4['p']:.4f}" if s4['p'] is not None else "n/a"
        P(f"{gate:26} {fs:>5} {n:5} {solo_pct:4.0f}% │ "
          f"{s4['mean']:+8.3f} {s4['med']:+7.3f} {s4['wr']:4.0f}% {p_s:>7} │ "
          f"{s1['mean']:+8.3f} │ {mfe2:6.1f}% {regime:>6}")
        rows_out.append((gate, fs, n, solo_pct, s4, s1, mfe2, regime))

    # OOS halves
    P()
    P("── OOS SPLIT (excess_4h mean; Oct 4-17 vs Oct 17-30) " + "─" * 56)
    for gate, fs, n, solo_pct, s4, s1, mfe2, regime in rows_out:
        if n < 16:
            continue
        a = [r[10] for r in gate_eps[gate] if r[0] < OOS_SPLIT and r[10] is not None]
        b = [r[10] for r in gate_eps[gate] if r[0] >= OOS_SPLIT and r[10] is not None]
        if not a or not b:
            continue
        ma, mb = sum(a) / len(a), sum(b) / len(b)
        same = 'YES' if ma * mb > 0 else 'NO'
        P(f"  {gate:26} n1={len(a):4} {ma:+7.3f}  n2={len(b):4} {mb:+7.3f}  same-sign={same}")

    # regime split for the big gates
    P()
    P("── REGIME SPLIT (excess_4h mean; chop |vel|<0.3 vs trend) " + "─" * 51)
    for gate, fs, n, solo_pct, s4, s1, mfe2, regime in rows_out[:15]:
        if n < 16:
            continue
        ch = [r[10] for r in gate_eps[gate] if r[12] is not None and r[12] < 0.3 and r[10] is not None]
        tr = [r[10] for r in gate_eps[gate] if r[12] is not None and r[12] >= 0.3 and r[10] is not None]
        mc = f"{sum(ch)/len(ch):+7.3f} (n={len(ch):4})" if ch else "    n/a"
        mt = f"{sum(tr)/len(tr):+7.3f} (n={len(tr):4})" if tr else "    n/a"
        P(f"  {gate:26} chop {mc}   trend {mt}")

    # weak-vs-strong counterfactual agreement (triangulation)
    P()
    P("── TRIANGULATION: shadow's own closer (follow-on-trade join) vs audited engine " + "─" * 22)
    both = [(e[13], e[14], e[15], e[10]) for e in episodes if e[13] == 1 and e[10] is not None]
    if both:
        agree = sum(1 for wt, ww, wp, exc in both
                    if (ww == 1) == (exc > 0))
        P(f"  episodes with both closures: {len(both)}; sign agreement: "
          f"{agree / len(both) * 100:.0f}%")
        # per-gate weak pnl sum vs strong excess mean
        P(f"  {'gate':26} {'weak_pnl$':>10} {'strong_ex4h':>12}")
        wg = defaultdict(list)
        for e in episodes:
            if e[13] == 1:
                wg[e[1]].append((e[15] or 0.0, e[10]))
        for g in sorted(wg, key=lambda x: -len(wg[x]))[:12]:
            v = wg[g]
            wp_sum = sum(x[0] for x in v)
            se = [x[1] for x in v if x[1] is not None]
            P(f"  {g:26} {wp_sum:+10.2f} {sum(se)/len(se) if se else float('nan'):+12.3f}")

    # ── REDUNDANCY VERDICTS ──────────────────────────────────────────────────
    P()
    P("── REDUNDANCY VERDICTS " + "─" * 84)
    P("ECONOMICALLY-REDUNDANT = |ex4h mean| < 0.10% AND p >= Bonferroni (blocks noise).")
    P("FUNCTIONALLY-REDUNDANT = solo% < 25 (another gate usually blocks the same token+dir).")
    P("  → both = FULLY REDUNDANT (removal candidate, pending Nov 6 decision gate)")
    P()
    econ_red, func_red, both_red, has_edge, insufficient = [], [], [], [], []
    for gate, fs, n, solo_pct, s4, s1, mfe2, regime in rows_out:
        if n < 16 or s4['p'] is None:
            insufficient.append((gate, n))
            continue
        e_red = abs(s4['mean']) < 0.10 and s4['p'] >= bonf
        f_red = solo_pct < 25
        if e_red and f_red:
            both_red.append((gate, n, s4['mean'], s4['p'], solo_pct))
        elif e_red:
            func_red.append((gate, n, s4['mean'], s4['p'], solo_pct))  # econ-only
        elif s4['p'] < bonf and abs(s4['mean']) >= 0.10:
            has_edge.append((gate, n, s4['mean'], s4['p'], solo_pct))
        else:
            econ_red.append((gate, n, s4['mean'], s4['p'], solo_pct))  # econ-only
    P("FULLY REDUNDANT (economically + functionally):")
    for g, n, m, p, s in sorted(both_red, key=lambda x: -x[1]):
        P(f"  {g:26} n={n:4} ex4h={m:+.3f} p={p:.3f} solo={s:.0f}%")
    P("ECONOMICALLY REDUNDANT (no edge, but fires solo — removal changes flow):")
    for g, n, m, p, s in sorted(econ_red, key=lambda x: -x[1]) + \
            sorted([x for x in func_red], key=lambda x: -x[1])[:0]:
        P(f"  {g:26} n={n:4} ex4h={m:+.3f} p={p:.3f} solo={s:.0f}%")
    P("HAS EDGE (survives Bonferroni, |effect| >= 0.10% — NOT redundant):")
    for g, n, m, p, s in sorted(has_edge, key=lambda x: -abs(x[2])):
        P(f"  {g:26} n={n:4} ex4h={m:+.3f} p={p:.4f} solo={s:.0f}%")
    P(f"INSUFFICIENT (n<16 or no p): {len(insufficient)} gates — "
      f"{', '.join(f'{g}(n={n})' for g, n in sorted(insufficient, key=lambda x: -x[1])[:12])}")

    # dollarization
    P()
    P("── DOLLARIZATION (blocked opportunity at live sizing ~$15 notional, 4h markout) " + "─" * 16)
    tot = 0.0
    for gate, fs, n, solo_pct, s4, s1, mfe2, regime in rows_out:
        if s4['mean'] is None:
            continue
        dollars = n * s4['mean'] / 100 * 15.0
        tot += dollars
        if abs(dollars) >= 2.0:
            P(f"  {gate:26} {n:5} eps × {s4['mean']:+.3f}% × $15 = {dollars:+.0f}")
    P(f"  ALL GATES AGGREGATE: {tot:+.0f} (positive = gates refused profitable entries on net)")

    # ── expiry shadow (confluence-expiry answer) ─────────────────────────────
    P()
    P("── CONFLUENCE-EXPIRY ANSWER (expiry_shadow, 28k expired signals, D3 engine) " + "─" * 14)
    conn = sqlite3.connect(os.path.join(BRAIN, 'expiry_shadow.db'))
    try:
        rows = conn.execute("""
            SELECT CASE WHEN confidence < 60 THEN 'a <60' WHEN confidence < 70 THEN 'b 60-69'
                        WHEN confidence < 80 THEN 'c 70-79' WHEN confidence < 90 THEN 'd 80-89'
                        ELSE 'e 90+' END,
                   COUNT(*), SUM(CASE WHEN excess_4h IS NOT NULL THEN 1 ELSE 0 END),
                   ROUND(AVG(excess_4h),4),
                   SUM(CASE WHEN excess_4h > 0 THEN 1 ELSE 0 END),
                   ROUND(AVG(mfe_4h),2)
            FROM events GROUP BY 1 ORDER BY 1""").fetchall()
        P(f"  {'band':8} {'n':>6} {'closed':>6} {'ex4h':>8} {'wr':>6} {'mfe':>6}")
        for band, n, cl, ex, wins, mfe in rows:
            wr = f"{wins / cl * 100:.0f}%" if cl else "n/a"
            P(f"  {band:8} {n:6} {cl or 0:6} {ex if ex is not None else float('nan'):+8.4f} {wr:>6} {mfe or 0:6.2f}")
        tot_n, tot_cl = conn.execute(
            "SELECT COUNT(*), SUM(CASE WHEN excess_4h IS NOT NULL THEN 1 ELSE 0 END) FROM events").fetchone()
        P(f"  TOTAL: {tot_n} events, {tot_cl} with strong closures")
    finally:
        conn.close()

    # export gate summary
    with open(os.path.join(EXPORTS, 'gate_summary.tsv'), 'w') as f:
        f.write("gate\tfirst_seen\tepisodes\tsolo_pct\tex4h_mean\tex4h_med\tex4h_wr\tp_wilcoxon\t"
                "ex1h_mean\tmfe2_share\tdominant_regime\tdollars_at_15\n")
        for gate, fs, n, solo_pct, s4, s1, mfe2, regime in rows_out:
            dollars = n * s4['mean'] / 100 * 15.0 if s4['mean'] is not None else 0
            f.write(f"{gate}\t{fs}\t{n}\t{solo_pct:.1f}\t{s4['mean']:.4f}\t{s4['med']:.4f}\t"
                    f"{s4['wr']:.1f}\t{s4['p'] if s4['p'] is not None else ''}\t"
                    f"{s1['mean']:.4f}\t{mfe2:.1f}\t{regime}\t{dollars:.2f}\n")

    # export expiry summary
    conn = sqlite3.connect(os.path.join(BRAIN, 'expiry_shadow.db'))
    try:
        with open(os.path.join(EXPORTS, 'expiry_summary.tsv'), 'w') as f:
            f.write("band\tn\tclosed\tex4h_mean\twins\tmfe_mean\n")
            for band, n, cl, ex, wins, mfe in conn.execute("""
                SELECT CASE WHEN confidence < 60 THEN 'a <60' WHEN confidence < 70 THEN 'b 60-69'
                            WHEN confidence < 80 THEN 'c 70-79' WHEN confidence < 90 THEN 'd 80-89'
                            ELSE 'e 90+' END,
                       COUNT(*), SUM(CASE WHEN excess_4h IS NOT NULL THEN 1 ELSE 0 END),
                       AVG(excess_4h), SUM(CASE WHEN excess_4h > 0 THEN 1 ELSE 0 END), AVG(mfe_4h)
                FROM events GROUP BY 1 ORDER BY 1"""):
                f.write(f"{band}\t{n}\t{cl or 0}\t{ex if ex is not None else ''}\t{wins or 0}\t{mfe or ''}\n")
    finally:
        conn.close()

    P()
    P(f"exports written: {EXPORTS}/gate_events_enriched.tsv, gate_summary.tsv, expiry_summary.tsv")

    with open('/root/.hermes/analysis/shadow_redundancy_deepdive_2026-10-30.out', 'w') as f:
        f.write('\n'.join(out))

if __name__ == '__main__':
    main()
