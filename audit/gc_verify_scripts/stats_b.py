#!/usr/bin/env python3
"""Per-gate table: audit formula vs neutral/median/BTC/raw baselines, horizons,
solo-only, OOS halves, per-day, MFE. Reads recs_solo.json (has nsolo/ovgates)."""
import json, math
import numpy as np
from collections import defaultdict

recs = json.load(open('/tmp/gaudit/recs_solo.json'))
AUDIT_GATES = {'SHORT-CONTINUUM','LONG-RSI-BLOCK','LONG-NEUTRAL','PUMP-CHAIN-SHORT-RSI-MIN',
 'SHORT-NEUTRAL','HALL-SHAME','LONG-RSI-CEILING','BTC-CHOP-GATE','SHORT-RSI-FLOOR',
 'PUMP-CHAIN-RSI-MAX','OVERSOLD-SHORT','CTX-GATE','BTC-CRASH','PUMP-CHAIN-SHORT-HIGH',
 'SPIKE-FILTER','PUMP-CHAIN-VEL-SHORT','SHORT-BB-DEAD-ZONE2','PUMP-CHAIN-RSI-MIN',
 'SHORT-REGIME-GATE','CHOP','EXEC-RSI-HARD-FLOOR','PUMP-CHAIN-VEL','EXEC-RSI-CEILING',
 'PHANTOM-WRITE','LONG-RSI-FLOOR','SHORT-RSI-CEILING','EXEC-BLOCK','SHORT-BB-DEAD-ZONE',
 'HOT-SET-COOLDOWN','PRESERVE-SPIKE-BLOCK','HOTSET-FILTER-WR','VEL-FILTER','HARD-BLOCK',
 'EXEC-RSI-FLOOR','V3-LONG-EXTREME','BTC-ACCEL','V2-RECHECK','BB-SQUEEZE-EXTREME'}
MFE_SHARE2_L = D_L = None
MFE_MARKET = {'long_mean': 1.421, 'long_share2': 22.0, 'short_mean': 1.517, 'short_share2': 23.6}

def w(v):
    return np.array([x for x in v if x is not None and not (isinstance(x, float) and math.isnan(x))], dtype=float)

def wp(v):
    from scipy import stats as sps
    v = w(v)
    if len(v) < 10 or len(np.unique(v)) < 2:
        return None
    try:
        return float(sps.wilcoxon(v).pvalue)
    except Exception:
        return None

by_gate = defaultdict(list)
for r in recs:
    by_gate[r['gate']].append(r)

print("PER-GATE TABLE (my universe; ex* = excess variants)")
print("ex = audit formula (signed - market_mean, same sign for both dirs)")
print("exn = market-neutral (shorts use +market_mean), exm = neutral vs median, exb = neutral vs BTC")
print("p_w = wilcoxon, p_p = permutation(4k, mean), CI = bootstrap 95% of mean")
hdr = (f"{'gate':26} {'eps':>5} {'dir%':>4} {'solo':>5} │ {'ex4 mean':>8} {'p_w':>5} {'p_p':>5} │ "
       f"{'exn4':>7} {'exm4':>7} {'exb4':>7} {'raw4':>7} │ {'30m':>7} {'1h':>7} {'8h':>7} │ "
       f"{'lag1':>7} │ {'solo-ex4':>8} {'ovl':>4} │ {'mfe':>5} {'sfe>2':>5} {'first':>5} {'last':>5}")
print(hdr)
print('─' * len(hdr))

rows = []
for g in sorted(by_gate, key=lambda x: -len(by_gate[x])):
    rs = by_gate[g]
    n = len(rs)
    shorts = sum(1 for r in rs if r['dir'] == 'SHORT') / n * 100
    ex4 = w([r['ex_4h'] for r in rs]); exn4 = w([r['exn_4h'] for r in rs])
    exm4 = w([r['exm_4h'] for r in rs]); exb4 = w([r['exb_4h'] for r in rs])
    raw4 = w([r['4h'] for r in rs]); e30 = w([r['ex_30m'] for r in rs])
    e1h = w([r['ex_1h'] for r in rs]); e8h = w([r.get('ex_8h') for r in rs])
    lag1 = w([r.get('ex_4h_lag1') for r in rs])
    solo = [r for r in rs if r['nsolo'] == 0]
    solo_ex4 = w([r['ex_4h'] for r in solo])
    ovl = np.mean([r['nsolo'] for r in rs])
    mfe = np.mean([r['sfe'] for r in rs if r['sfe'] is not None])
    sfe2 = np.mean([1 for r in rs if r['sfe'] is not None and r['sfe'] >= 2.0]) * 100
    pw = wp([r['ex_4h'] for r in rs])
    # permutation p
    RNG = np.random.default_rng(7)
    if len(ex4) >= 10:
        idx = RNG.integers(0, len(ex4), size=(3000, len(ex4)))
        sgn = RNG.choice(np.array([-1., 1.]), size=(3000, len(ex4)))
        pp = float((np.abs((ex4[idx] * sgn).mean(axis=1)) >= abs(ex4.mean())).mean())
    else:
        pp = None
    tss = [r['ts'] for r in rs]
    def dstr(ts):
        import datetime as dt
        return dt.datetime.utcfromtimestamp(ts).strftime('%m-%d')
    print(f"{g:26} {n:5} {shorts:4.0f} {len(solo):5} │ {ex4.mean():+8.3f} "
          f"{(f'{pw:.3f}' if pw is not None else '  -  '):>5} {(f'{pp:.3f}' if pp is not None else '  -  '):>5} │ "
          f"{exn4.mean():+7.3f} {exm4.mean():+7.3f} {exb4.mean():+7.3f} {raw4.mean():+7.3f} │ "
          f"{e30.mean():+7.3f} {e1h.mean():+7.3f} {e8h.mean() if len(e8h) else float('nan'):+7.3f} │ "
          f"{lag1.mean() if len(lag1) else float('nan'):+7.3f} │ "
          f"{solo_ex4.mean() if len(solo_ex4) else float('nan'):+8.3f} {ovl:4.1f} │ "
          f"{mfe:5.2f} {sfe2:5.1f} {dstr(min(tss)):>5} {dstr(max(tss)):>5}")
    rows.append(dict(gate=g, n=n, ex4=float(ex4.mean()), pw=pw, pp=pp, exn4=float(exn4.mean()),
                     solo_n=len(solo), solo_ex4=float(solo_ex4.mean()) if len(solo_ex4) else None,
                     short_share=float(shorts)))

json.dump(rows, open('/tmp/gaudit/gate_rows.json', 'w'))
print()
print(f"market MFE(4h) reference: LONG mean {MFE_MARKET['long_mean']}% share>=2% {MFE_MARKET['long_share2']}% | "
      f"SHORT mean {MFE_MARKET['short_mean']}% share>=2% {MFE_MARKET['short_share2']}%")

# ---------- OOS halves + per-day ----------
print()
print("OOS: ex_4h mean first half (Oct2 20:00-Oct5 12:00) vs second (Oct5 12:00-Oct8 23:02), audit formula AND neutral")
SPLIT = int((__import__('datetime').datetime(2026, 10, 5, 12, 0, tzinfo=__import__('datetime').timezone.utc)).timestamp())
for g in sorted(by_gate, key=lambda x: -len(by_gate[x]))[:20]:
    rs = by_gate[g]
    a = [r['ex_4h'] for r in rs if r['ts'] < SPLIT]
    b = [r['ex_4h'] for r in rs if r['ts'] >= SPLIT]
    an = [r['exn_4h'] for r in rs if r['ts'] < SPLIT]
    bn = [r['exn_4h'] for r in rs if r['ts'] >= SPLIT]
    ma = np.mean(w(a)) if len(w(a)) else float('nan')
    mb = np.mean(w(b)) if len(w(b)) else float('nan')
    mna = np.mean(w(an)) if len(w(an)) else float('nan')
    mnb = np.mean(w(bn)) if len(w(bn)) else float('nan')
    print(f"  {g:26} n1={len(a):4} ex={ma:+7.3f} (neu {mna:+6.3f})  n2={len(b):4} ex={mb:+7.3f} (neu {mnb:+6.3f})")

print()
print("PER-DAY ex_4h mean (audit formula) — regime stability")
days = [f"10-{d:02d}" for d in range(2, 9)]
def day_of(ts):
    import datetime as dt
    return dt.datetime.utcfromtimestamp(ts).strftime('%m-%d')
print(f"{'gate':26} " + ' '.join(f"{d:>8}" for d in days))
for g in sorted(by_gate, key=lambda x: -len(by_gate[x]))[:16]:
    rs = by_gate[g]
    per = defaultdict(list)
    for r in rs:
        per[day_of(r['ts'])].append(r['ex_4h'])
    print(f"{g:26} " + ' '.join((f"{np.mean(w(per[d])):+8.3f}" if d in per and len(w(per[d])) else f"{'—':>8}") for d in days))
