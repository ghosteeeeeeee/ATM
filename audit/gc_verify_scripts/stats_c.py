#!/usr/bin/env python3
"""Phase C: neutral-baseline significance, horizon consistency, solo+neutral,
MFE shares (fixed), overlap matrix, coverage/gap analysis."""
import json, math, sqlite3
import numpy as np
from collections import defaultdict
from scipy import stats as sps

recs = json.load(open('/tmp/gaudit/recs_solo.json'))
RNG = np.random.default_rng(99)

def w(v):
    return np.array([x for x in v if x is not None and not (isinstance(x, float) and math.isnan(x))], dtype=float)

def tests(v):
    v = w(v)
    n = len(v)
    if n < 10 or len(np.unique(v)) < 2:
        return None
    try:
        pw = float(sps.wilcoxon(v).pvalue)
    except Exception:
        pw = None
    idx = RNG.integers(0, n, size=(3000, n))
    sgn = RNG.choice(np.array([-1., 1.]), size=(3000, n))
    pp = float((np.abs((v[idx] * sgn).mean(axis=1)) >= abs(v.mean())).mean())
    return dict(n=n, mean=float(v.mean()), med=float(np.median(v)), pw=pw, pp=pp)

by_gate = defaultdict(list)
for r in recs:
    by_gate[r['gate']].append(r)

print("A. VERDICT ROBUSTNESS MATRIX — ex4h under 4 baselines (mean / wilcoxon-p)")
print(f"{'gate':26} {'n':>5} │ {'audit':>16} │ {'neutral':>16} │ {'median-base':>16} │ {'BTC-base':>16} │ {'raw':>16}")
for g in sorted(by_gate, key=lambda x: -len(by_gate[x]))[:26]:
    rs = by_gate[g]
    cells = []
    for key in ('ex_4h', 'exn_4h', 'exm_4h', 'exb_4h', '4h'):
        t = tests([r[key] for r in rs])
        if t is None:
            cells.append(f"{'—':>16}")
        else:
            sig = '*' if (t['pw'] or 1) < 0.05 else ' '
            cells.append(f"{t['mean']:+.3f}{sig} p={(t['pw'] if t['pw'] is not None else float('nan')):.3f}")
    print(f"{g:26} {len(rs):5} │ {cells[0]:>16} │ {cells[1]:>16} │ {cells[2]:>16} │ {cells[3]:>16} │ {cells[4]:>16}")

print()
print("B. HORIZON CONSISTENCY (audit-formula ex and neutral exn), top gates")
print(f"{'gate':26} {'ex30m':>8} {'ex1h':>8} {'ex4h':>8} {'ex8h':>8} │ {'exn30m':>8} {'exn1h':>8} {'exn4h':>8} {'exn8h':>8}")
for g in sorted(by_gate, key=lambda x: -len(by_gate[x]))[:18]:
    rs = by_gate[g]
    row = []
    for key in ('ex_30m', 'ex_1h', 'ex_4h', 'ex_8h', 'exn_30m', 'exn_1h', 'exn_4h', 'exn_8h'):
        v = w([r.get(key) for r in rs])
        row.append(f"{v.mean():+8.3f}" if len(v) else f"{'—':>8}")
    print(f"{g:26} " + ' '.join(row))

print()
print("C. SOLO-ONLY (no other gate within +-10min) — audit-formula and neutral ex4h")
print(f"{'gate':26} {'solo_n':>6} {'solo_ex4':>9} {'solo_exn4':>9} │ {'ovl_n':>5} {'ovl_ex4':>8} {'ovl_exn4':>8}")
for g in sorted(by_gate, key=lambda x: -len(by_gate[x]))[:20]:
    rs = by_gate[g]
    solo = [r for r in rs if r['nsolo'] == 0]
    ovl = [r for r in rs if r['nsolo'] > 0]
    def m(field, sub):
        v = w([r[field] for r in sub])
        return f"{v.mean():+.3f}" if len(v) else "   —  "
    print(f"{g:26} {len(solo):6} {m('ex_4h', solo):>9} {m('exn_4h', solo):>9} │ {len(ovl):5} {m('ex_4h', ovl):>8} {m('exn_4h', ovl):>8}")

print()
print("D. OVERLAP MATRIX (share of gate's episodes co-blocked with each top gate, +-10min)")
tops = [g for g in sorted(by_gate, key=lambda x: -len(by_gate[x]))[:8]]
mat = {}
for g in tops:
    rs = by_gate[g]
    c = defaultdict(int)
    for r in rs:
        for og in r['ovgates']:
            c[og] += 1
    mat[g] = {k: v / len(rs) for k, v in c.items()}
print(f"{'gate':26} " + ' '.join(f"{t[:9]:>10}" for t in tops) + f" {'any':>6}")
for g in tops:
    cells = []
    for t in tops:
        cells.append(f"{mat[g].get(t, 0) * 100:9.1f}%")
    anyov = np.mean([1 for r in by_gate[g] if r['nsolo'] > 0]) * 100
    print(f"{g:26} " + ' '.join(cells) + f" {anyov:5.1f}%")

print()
print("E. MFE: direction-aware favorable excursion >=2% share vs direction-matched market rate")
MKT = {'LONG': 22.0, 'SHORT': 23.6}
print(f"{'gate':26} {'n':>5} {'dir%short':>9} {'sfe mean':>8} {'sfe>=2%':>8} {'mkt>=2%':>8} {'excess kill':>11}")
for g in sorted(by_gate, key=lambda x: -len(by_gate[x]))[:22]:
    rs = by_gate[g]
    sfe = [r['sfe'] for r in rs if r['sfe'] is not None]
    share = np.mean([1.0 if s >= 2.0 else 0.0 for s in sfe]) * 100
    mkt = np.mean([MKT[r['dir']] for r in rs]) if len(rs) else 0
    sh = np.mean([1 if r['dir'] == 'SHORT' else 0 for r in rs]) * 100
    print(f"{g:26} {len(rs):5} {sh:8.0f}% {np.mean(sfe):8.2f} {share:7.1f}% {mkt:7.1f}% {share - mkt:+10.1f}%")

print()
print("F. CANDLE COVERAGE / GAPS (attack G)")
conn = sqlite3.connect('/root/.hermes/data/candles.db')
cur = conn.cursor()
toks = sorted({r['token'] for r in recs} | {'BTC'})
WIN0 = int((__import__('datetime').datetime(2026, 10, 2, 20, 0, tzinfo=__import__('datetime').timezone.utc)).timestamp())
WIN1 = int((__import__('datetime').datetime(2026, 10, 8, 23, 0, tzinfo=__import__('datetime').timezone.utc)).timestamp())
print(f"{'token':10} {'n_candles':>9} {'expected':>8} {'max_gap_min':>11}")
sparse = []
for t in toks:
    rows = cur.execute("SELECT ts FROM candles_5m WHERE token=? AND is_closed=1 AND ts>=? AND ts<=? ORDER BY ts",
                       (t, WIN0, WIN1)).fetchall()
    ts = np.array([r[0] for r in rows], dtype=np.int64)
    n = len(ts)
    exp = (WIN1 - WIN0) // 300 + 1
    gaps = np.diff(ts) if n > 1 else np.array([0])
    mx = int(gaps.max()) // 60 if n else -1
    if n < exp * 0.95 or mx > 60:
        sparse.append((t, n, exp, mx))
    if t in ('BTC',) or n < exp * 0.95:
        print(f"{t:10} {n:9} {exp:8} {mx:11}")
print(f"tokens with <95% coverage or >60min gaps: {[(s[0], s[1], s[3]) for s in sparse]}")
conn.close()

# which passed-trade tokens lacked coverage
side = json.load(open('/tmp/gaudit/side.json'))
print(f"\npassed: n={len(side['passed']['4h'])} (5 lacked coverage)")
