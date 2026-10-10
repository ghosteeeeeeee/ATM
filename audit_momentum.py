#!/usr/bin/env python3
"""Independent audit: verify 30m-momentum threshold claim on pump-chain LONG trades."""
import sqlite3, json, statistics as st

PG = None
try:
    import psycopg2
    PG = psycopg2.connect(host='/var/run/postgresql', database='brain',
                          user='postgres', connect_timeout=5)
except Exception as e:
    print("PG connect failed:", e)

CAND = sqlite3.connect("file:/root/.hermes/data/candles.db?mode=ro", uri=True, timeout=10)
SQ = sqlite3.connect("/root/.hermes/brain/associative_memory.db")

# ── 1. The 41-trade SQLite set (what the claim's 41/17W/24L matches) ─────────
sq_rows = SQ.execute("""
    SELECT id, token, signal, won, pnl_pct, close_time FROM trade_log
    WHERE direction='LONG' AND signal LIKE '%pump-chain%'
      AND close_time >= '2026-09-26'
    ORDER BY close_time""").fetchall()
print(f"SQLite trade_log 14d pump-chain LONG: n={len(sq_rows)} "
      f"W={sum(1 for r in sq_rows if r[3]==1)} L={sum(1 for r in sq_rows if r[3]==0)}")

# ── 2. PG set with open_time (entry anchor) ──────────────────────────────────
cur = PG.cursor()
cur.execute("""
    SELECT id, token, signal, pnl_pct, open_time, close_time,
           _signal_metadata->>'momentum_state' AS meta_mom,
           _signal_metadata->>'wave_phase' AS meta_wave
    FROM trades
    WHERE direction='LONG' AND signal LIKE '%pump-chain%'
      AND close_time >= '2026-09-26'
    ORDER BY close_time""")
pg_rows = cur.fetchall()
print(f"PG trades 14d pump-chain LONG:        n={len(pg_rows)} "
      f"W={sum(1 for r in pg_rows if r[3]>0)} L={sum(1 for r in pg_rows if r[3]<=0)}")

def mom30(token, t_anchor, closed_only=True):
    """30m momentum = % change over last 6 closed 5m candles ending at/before anchor.
    Mirrors V5 _check_30m_velocity (6 candles = 30 min)."""
    # anchor = epoch seconds of entry
    ts = int(t_anchor)
    if closed_only:
        # candle at ts covers [ts, ts+300); must be fully closed before anchor
        q = "SELECT close FROM candles_5m WHERE token=? AND is_closed=1 AND ts+300<=? ORDER BY ts DESC LIMIT 6"
    else:
        q = "SELECT close FROM candles_5m WHERE token=? AND is_closed=1 AND ts<=? ORDER BY ts DESC LIMIT 6"
    rows = CAND.execute(q, (token.upper(), ts)).fetchall()
    closes = [r[0] for r in rows]  # closes[0]=newest, closes[-1]=oldest
    if len(closes) < 6 or closes[-1] == 0:
        return None
    return (closes[0] - closes[-1]) / closes[-1] * 100

import datetime as dt
def to_epoch(ts):
    if isinstance(ts, str):
        ts = ts.replace('T', ' ').split('+')[0]
        return dt.datetime.fromisoformat(ts).replace(tzinfo=dt.timezone.utc).timestamp()
    return ts.replace(tzinfo=dt.timezone.utc).timestamp()

# ── 3. Compute 30m momentum at ENTRY for PG trades ───────────────────────────
data = []
for pid, token, signal, pnl, open_time, close_time, meta_mom, meta_wave in pg_rows:
    e = to_epoch(open_time)
    m_closed = mom30(token, e, closed_only=True)
    m_any    = mom30(token, e, closed_only=False)
    won = 1 if pnl > 0 else 0
    data.append(dict(id=pid, token=token, won=won, pnl=float(pnl),
                     m_closed=m_closed, m_any=m_any,
                     meta_mom=meta_mom, meta_wave=meta_wave))

have = [d for d in data if d['m_closed'] is not None]
print(f"\nTrades with computable 30m momentum at entry: {len(have)}/{len(data)}")

# ── 4. Threshold analysis: momentum < -0.1% ──────────────────────────────────
def analyze(rows, field, thr=-0.1):
    W = [r for r in rows if r['won']==1]; L = [r for r in rows if r['won']==0]
    blocked_L = [r for r in L if r[field] < thr]
    blocked_W = [r for r in W if r[field] < thr]
    kept_L = [r for r in L if r[field] >= thr]
    kept_W = [r for r in W if r[field] >= thr]
    wr = len(kept_W)/(len(kept_W)+len(kept_L))*100 if (kept_W or kept_L) else float('nan')
    win_avg = st.mean([r[field] for r in W]) if W else float('nan')
    loss_avg = st.mean([r[field] for r in L]) if L else float('nan')
    print(f"\n--- field={field} threshold={thr}% ---")
    print(f"  totals: {len(W)}W / {len(L)}L")
    print(f"  BLOCKED losses: {len(blocked_L)}/{len(L)}   BLOCKED wins: {len(blocked_W)}/{len(W)}")
    print(f"  kept: {len(kept_W)}W / {len(kept_L)}L  -> WR {wr:.1f}%")
    print(f"  WIN avg momentum {win_avg:+.4f}%   LOSS avg momentum {loss_avg:+.4f}%")
    return dict(blocked_L=len(blocked_L), blocked_W=len(blocked_W),
                kept_W=len(kept_W), kept_L=len(kept_L), wr=wr,
                win_avg=win_avg, loss_avg=loss_avg)

print("\n" + "="*70)
print("THRESHOLD ANALYSIS (PG entry-anchored, 30m momentum)")
print("="*70)
r_closed = analyze(have, 'm_closed', -0.1)
r_any    = analyze(have, 'm_any',    -0.1)

# also try -0.3 (V5's actual constant)
print("\n[V5 constant PUMP_CHAIN_VEL_30M_MIN = -0.3]")
analyze(have, 'm_closed', -0.3)

# ── 5. momentum_state gate equivalence ───────────────────────────────────────
print("\n" + "="*70)
print("momentum_state='flat' GATE vs 30m threshold")
print("="*70)
ms = [d for d in data if d['meta_mom']]
print(f"trades with meta momentum_state: {len(ms)}/{len(data)}")
from collections import Counter
print("momentum_state distribution:", Counter(d['meta_mom'] for d in ms))
flat = [d for d in ms if d['meta_mom']=='flat']
flatW = [d for d in flat if d['won']==1]; flatL = [d for d in flat if d['won']==0]
print(f"  momentum_state='flat': {len(flat)} trades -> {len(flatW)}W/{len(flatL)}L "
      f"(blocked wins={len(flatW)}, blocked losses={len(flatL)})")
keptW = [d for d in ms if d['meta_mom']!='flat' and d['won']==1]
keptL = [d for d in ms if d['meta_mom']!='flat' and d['won']==0]
wr = len(keptW)/(len(keptW)+len(keptL))*100 if (keptW or keptL) else float('nan')
print(f"  if gate blocks 'flat': kept {len(keptW)}W/{len(keptL)}L -> WR {wr:.1f}%")

# Is flat equivalent to mom < -0.1? Cross-tab on trades having BOTH
both = [d for d in data if d['meta_mom'] and d['m_closed'] is not None]
print(f"\nCross-tab momentum_state vs (30m mom < -0.1%) on {len(both)} trades:")
ct = Counter((d['meta_mom'], d['m_closed'] < -0.1) for d in both)
for k in sorted(ct, key=lambda x: (x[0], x[1])):
    print(f"   state={k[0]:8s} mom<-0.1={k[1]!s:5s} : {ct[k]}")

# What 30m-momentum window does 'flat' actually correspond to?
flat_m = [d['m_closed'] for d in both if d['meta_mom']=='flat']
if flat_m:
    print(f"\n'flat' trades' actual 30m momentum: min {min(flat_m):+.3f} max {max(flat_m):+.3f} "
          f"mean {st.mean(flat_m):+.4f}")
nonflat_m = [d['m_closed'] for d in both if d['meta_mom']!='flat']
print(f"non-'flat' trades' 30m momentum:    min {min(nonflat_m):+.3f} max {max(nonflat_m):+.3f} "
      f"mean {st.mean(nonflat_m):+.4f}")

# ── 6. What does -0.1% over 5m (momentum_state window) look like? ────────────
# recompute 5m momentum (6 one-min samples) at entry from candles_1m
def mom5(token, t_anchor):
    ts = int(t_anchor)
    rows = CAND.execute(
        "SELECT close FROM candles_1m WHERE token=? AND ts+60<=? ORDER BY ts DESC LIMIT 6",
        (token.upper(), ts)).fetchall()
    closes=[r[0] for r in rows]
    if len(closes)<6 or closes[-1]==0: return None
    return (closes[0]-closes[-1])/closes[-1]*100

for d in data:
    d['m5'] = mom5(d['token'], to_epoch(pg_rows[[p[0] for p in pg_rows].index(d['id'])][4])) if False else None

# simpler: recompute inline
print("\n" + "="*70)
print("5-MINUTE momentum (momentum_state window) at entry, threshold -0.1%")
print("="*70)
for i, (pid, token, signal, pnl, open_time, close_time, mm, mw) in enumerate(pg_rows):
    data[i]['m5'] = mom5(token, to_epoch(open_time))
have5 = [d for d in data if d['m5'] is not None]
print(f"trades with computable 5m momentum: {len(have5)}/{len(data)}")
r5 = analyze(have5, 'm5', -0.1)

# compare m5 classification vs momentum_state
both5 = [d for d in data if d['m5'] is not None and d['meta_mom']]
agree = sum(1 for d in both5 if (d['m5'] < -0.1) == (d['meta_mom']=='falling'))
print(f"\nm5<-0.1% agrees with state=='falling': {agree}/{len(both5)}")
ct5 = Counter((d['meta_mom'], d['m5'] < -0.1) for d in both5)
for k in sorted(ct5, key=lambda x:(x[0],x[1])):
    print(f"   state={k[0]:8s} m5<-0.1={k[1]!s:5s} : {ct5[k]}")

print("\nDONE")
