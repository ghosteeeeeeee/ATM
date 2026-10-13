#!/usr/bin/env python3
"""Comprehensive audit: entry-delay cost, data quality, significance, SHORT/LONG split."""
import sqlite3, math, json
from datetime import datetime, timezone

SIG_DB = '/root/.hermes/data/signals_hermes_runtime.db'
CAND_DB = '/root/.hermes/data/candles.db'

WINDOW_MIN, THRESH, HOLD = 90, 4, 60

def to_epoch(ts_str):
    dt = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
    return int(dt.timestamp())

sc = sqlite3.connect(SIG_DB)
sig_rows = sc.execute("""
SELECT id, token, direction, created_at, source, price
FROM signals
WHERE decision IN ('PENDING','EXPIRED')
  AND created_at > datetime('now', '-7 days')
  AND source NOT LIKE '%,%'
  AND price > 0
ORDER BY token, direction, created_at
""").fetchall()
sc.close()

groups = {}
for rid, token, direction, created_at, source, price in sig_rows:
    groups.setdefault((token, direction), []).append({
        'id': rid, 't': to_epoch(created_at), 'ts': created_at, 'source': source, 'price': price})
for k in groups:
    groups[k].sort(key=lambda x: x['t'])

cc = sqlite3.connect(f"file:{CAND_DB}?mode=ro", uri=True, timeout=60)

def c_at_or_before(token, t):
    return cc.execute("SELECT ts, close FROM candles_1m WHERE token=? AND ts<=? ORDER BY ts DESC LIMIT 1", (token, t)).fetchone()

def c_at_or_after(token, t):
    return cc.execute("SELECT ts, close FROM candles_1m WHERE token=? AND ts>=? ORDER BY ts ASC LIMIT 1", (token, t)).fetchone()

# ============ DATA QUALITY ============
print("="*70)
print("DATA QUALITY")
print("="*70)
n_null_price = sum(1 for r in sig_rows if r[5] is None)
n_zero_price = sum(1 for r in sig_rows if r[5] == 0)
print(f"base signals: {len(sig_rows)}  null_price={n_null_price}  zero_price={n_zero_price} (both excluded by query)")

# duplicates: same token+direction+source within 60s
dup_pairs = 0
dup_events = []  # (token, direction, source) with clusters
for (token, direction), fires in groups.items():
    by_src = {}
    for f in fires:
        by_src.setdefault(f['source'], []).append(f)
    for src, fs in by_src.items():
        i = 0
        while i < len(fs):
            j = i + 1
            while j < len(fs) and fs[j]['t'] - fs[j-1]['t'] <= 60:
                j += 1
            if j - i > 1:
                dup_pairs += (j - i - 1)
                dup_events.append((token, direction, src, j - i, [x['ts'] for x in fs[i:j]]))
            i = j
print(f"duplicate fires (same token+dir+source within 60s of previous): extra rows = {dup_pairs}, clusters = {len(dup_events)}")
for e in dup_events[:10]:
    print(f"  dup: {e[0]} {e[1]} {e[2]} x{e[3]} at {e[4]}")

# simultaneous multi-source fires (same token+direction, exact same timestamp) - inflates fire count
simul = 0
for (token, direction), fires in groups.items():
    ts_count = {}
    for f in fires:
        ts_count[f['t']] = ts_count.get(f['t'], 0) + 1
    simul += sum(c - 1 for c in ts_count.values() if c > 1)
print(f"simultaneous fires (same token+dir, identical timestamp, different sources): extra rows = {simul}")

# candle coverage for tokens in signal set
sig_tokens = sorted(set(t for (t, d) in groups.keys()))
missing_candle_tokens = []
low_cov_tokens = []
for tok in sig_tokens:
    cnt = cc.execute("SELECT COUNT(*) FROM candles_1m WHERE token=? AND ts>=strftime('%s','now','-7 days')", (tok,)).fetchone()[0]
    if cnt == 0:
        missing_candle_tokens.append(tok)
    elif cnt < 7*24*60*0.8:  # <80% of 7 days of minutes
        low_cov_tokens.append((tok, cnt))
print(f"signal tokens: {len(sig_tokens)}  no candles at all (7d): {len(missing_candle_tokens)} {missing_candle_tokens}")
print(f"tokens with <80% minute coverage in 7d: {len(low_cov_tokens)} {low_cov_tokens}")

# ============ BYPASS EVENTS ============
bypasses = []  # includes events even without candle data, for delay-cost stats
for (token, direction), fires in groups.items():
    if len(fires) < THRESH:
        continue
    for i, f in enumerate(fires):
        wstart = f['t'] - WINDOW_MIN*60
        inwin = [g for g in fires[:i+1] if g['t'] >= wstart]
        if len(inwin) >= THRESH:
            bypasses.append({'token': token, 'direction': direction,
                             'bypass': f, 'first': inwin[0], 'window_fires': inwin})

print()
print("="*70)
print(f"BYPASS EVENTS: {len(bypasses)}")
print("="*70)

# distinct-timestamp inflation check
inflated = 0
for b in bypasses:
    distinct_ts = len(set(f['t'] for f in b['window_fires']))
    if distinct_ts < THRESH:
        inflated += 1
print(f"bypass events whose 90m-window has <4 DISTINCT timestamps (multi-source inflation): {inflated} / {len(bypasses)} ({inflated/len(bypasses)*100:.1f}%)")

# ============ ENTRY DELAY COST ============
# delay cost using SIGNAL prices (first fire vs bypass fire)
delay_costs_sig = []
delay_costs_candle = []
rows = []
for b in bypasses:
    token, direction = b['token'], b['direction']
    bf, ff = b['bypass'], b['first']
    if direction == 'LONG':
        dc_sig = (bf['price'] - ff['price']) / ff['price'] * 100
    else:
        dc_sig = (ff['price'] - bf['price']) / ff['price'] * 100
    delay_costs_sig.append(dc_sig)

    fp = c_at_or_before(token, ff['t'])
    bp = c_at_or_before(token, bf['t'])
    if fp and bp and fp[1] > 0:
        if direction == 'LONG':
            dc_c = (bp[1] - fp[1]) / fp[1] * 100
        else:
            dc_c = (fp[1] - bp[1]) / fp[1] * 100
        delay_costs_candle.append(dc_c)
    else:
        dc_c = None

    delay_minutes = (bf['t'] - ff['t']) / 60.0
    rows.append({'token': token, 'direction': direction, 'delay_min': delay_minutes,
                 'dc_sig': dc_sig, 'dc_candle': dc_c,
                 'first_t': ff['t'], 'bypass_t': bf['t'],
                 'first_price': ff['price'], 'bypass_price': bf['price'],
                 'first_candle': fp[1] if fp else None, 'bypass_candle': bp[1] if bp else None})

def stats(name, xs):
    if not xs:
        print(f"{name}: no data")
        return
    xs_s = sorted(xs)
    n = len(xs_s)
    mean = sum(xs_s) / n
    med = xs_s[n//2] if n % 2 else (xs_s[n//2 - 1] + xs_s[n//2]) / 2
    gt1 = sum(1 for x in xs_s if x > 1.0)
    gt2 = sum(1 for x in xs_s if x > 2.0)
    gt5 = sum(1 for x in xs_s if x > 5.0)
    neg = sum(1 for x in xs_s if x < 0)
    print(f"{name}: n={n} mean={mean:+.3f}% median={med:+.3f}%  >1%: {gt1} ({gt1/n*100:.0f}%)  >2%: {gt2} ({gt2/n*100:.0f}%)  >5%: {gt5} ({gt5/n*100:.0f}%)  negative(favorable): {neg} ({neg/n*100:.0f}%)")
    print(f"    min={xs_s[0]:+.3f}% p25={xs_s[n//4]:+.3f}% p75={xs_s[3*n//4]:+.3f}% max={xs_s[-1]:+.3f}%")

print()
print("DELAY COST (favorable = positive means price moved against favorable entry, i.e., cost)")
stats("signal-price delay cost", delay_costs_sig)
stats("candle-price delay cost", delay_costs_candle)
delays = [r['delay_min'] for r in rows]
stats("delay minutes", delays)

# ============ PnL: FIRST FIRE vs BYPASS FIRE ============
# For each bypass event: 60m forward return entering at first-fire candle vs bypass candle.
pnl_first, pnl_bypass = [], []
pnl_first_dir, pnl_bypass_dir = [], []  # signed for direction
missing_fwd = 0
for r in rows:
    token, direction = r['token'], r['direction']
    # forward from first fire
    e1 = c_at_or_before(token, r['first_t'])
    x1 = c_at_or_before(token, r['first_t'] + HOLD*60)
    # forward from bypass fire
    e2 = c_at_or_before(token, r['bypass_t'])
    x2 = c_at_or_before(token, r['bypass_t'] + HOLD*60)
    if not (e1 and x1 and e2 and x2):
        missing_fwd += 1
        continue
    ret1 = (x1[1] - e1[1]) / e1[1] * 100
    ret2 = (x2[1] - e2[1]) / e2[1] * 100
    if direction == 'SHORT':
        ret1, ret2 = -ret1, -ret2
    pnl_first.append(ret1)
    pnl_bypass.append(ret2)
    pnl_first_dir.append((direction, ret1))
    pnl_bypass_dir.append((direction, ret2))

n = len(pnl_first)
print()
print(f"PnL comparison (60m forward, n={n} events with full candle data, missing={missing_fwd}):")
if n:
    w1 = sum(1 for r in pnl_first if r > 0)
    w2 = sum(1 for r in pnl_bypass if r > 0)
    print(f"  ENTER AT FIRST FIRE : WR={w1/n*100:.1f}%  total={sum(pnl_first):+.2f}%  avg={sum(pnl_first)/n:+.3f}%")
    print(f"  ENTER AT BYPASS FIRE: WR={w2/n*100:.1f}%  total={sum(pnl_bypass):+.2f}%  avg={sum(pnl_bypass)/n:+.3f}%")
    print(f"  DELTA (bypass - first): total={sum(pnl_bypass)-sum(pnl_first):+.2f}%  avg={(sum(pnl_bypass)-sum(pnl_first))/n:+.3f}%")

# ============ SHORT vs LONG SPLIT ============
print()
print("="*70)
print("SHORT vs LONG SPLIT (bypass trades, 60m fwd, entry at bypass candle)")
print("="*70)
by_dir = {}
for direction, ret in pnl_bypass_dir:
    by_dir.setdefault(direction, []).append(ret)
for d, rets in sorted(by_dir.items()):
    nn = len(rets)
    w = sum(1 for r in rets if r > 0)
    print(f"  {d}: n={nn} WR={w/nn*100:.1f}% total={sum(rets):+.2f}% avg={sum(rets)/nn:+.3f}%")

# ============ SIGNIFICANCE ============
print()
print("="*70)
print("STATISTICAL SIGNIFICANCE")
print("="*70)

def wilson_ci(w, n, z=1.96):
    if n == 0:
        return (0, 0)
    p = w / n
    denom = 1 + z*z/n
    center = (p + z*z/(2*n)) / denom
    half = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / denom
    return (center - half, center + half)

def binom_p_ge(w, n, p0=0.5):
    # P(X >= w) under H0 p=p0, normal approx with continuity correction
    mu = n * p0
    sd = math.sqrt(n * p0 * (1 - p0))
    z = (w - 0.5 - mu) / sd
    # standard normal CDF
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))

if pnl_bypass:
    w2 = sum(1 for r in pnl_bypass if r > 0)
    nn = len(pnl_bypass)
    lo, hi = wilson_ci(w2, nn)
    p1 = binom_p_ge(w2, nn)
    p2 = 2 * min(p1, 1 - p1 + 0.5*(1 - math.erf((w2 - 0.5 - nn*0.5) / (math.sqrt(nn*0.25) * math.sqrt(2)))))
    print(f"bypass trades: n={nn} wins={w2} WR={w2/nn*100:.1f}%")
    print(f"  Wilson 95% CI on WR: [{lo*100:.1f}%, {hi*100:.1f}%]")
    print(f"  one-sided p (H0: WR<=50%): {p1:.4f}")
    # two-sided exact via normal approx
    p_two = 2 * min(p1, 1 - p1)
    print(f"  two-sided p (normal approx): {min(p_two,1.0):.4f}")
    # how many trades needed for 80% power at observed effect (approx)
    print(f"  NOTE: 50% inside CI? {'YES -> not significant' if lo < 0.5 < hi else 'NO -> significant at 5%'}")

if pnl_first:
    w1 = sum(1 for r in pnl_first if r > 0)
    nn = len(pnl_first)
    lo, hi = wilson_ci(w1, nn)
    p1 = binom_p_ge(w1, nn)
    print(f"first-fire trades: n={nn} wins={w1} WR={w1/nn*100:.1f}%  CI=[{lo*100:.1f}%,{hi*100:.1f}%]  one-sided p={p1:.4f}")

# cluster structure: how many trades per cluster (overlap issue)
print()
print("="*70)
print("TRADE INDEPENDENCE / CLUSTER OVERLAP")
print("="*70)
cluster_sizes = {}
for (token, direction), fires in groups.items():
    bs = [b for b in bypasses if b['token'] == token and b['direction'] == direction]
    if bs:
        cluster_sizes[(token, direction)] = len(bs)
sizes = list(cluster_sizes.values())
from collections import Counter
print(f"groups producing trades: {len(sizes)}  total bypass trades: {sum(sizes)}")
print(f"trades-per-group distribution: {dict(sorted(Counter(sizes).items()))}")
print(f"groups with >1 trade (repeat entries on same move): {sum(1 for s in sizes if s > 1)}")

cc.close()

# save rows for report
with open('/root/.hermes/brain/verdicts/audit_rows.json', 'w') as fjson:
    json.dump(rows, fjson)
print("\nsaved audit_rows.json")
