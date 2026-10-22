#!/usr/bin/env python3
"""RSI source fragmentation study — brain_auditor #80, 2026-10-22.

Three live RSI implementations enforce the same thresholds (knife 35 / floor 45):
  A = signal_compactor.py:4110 approval floor: inline SIMPLE avg over last 14 5m deltas
  B = decider_run.py:2113 exec floor: rsi_utils Wilder 5m (limit=20)
  C = decider_run.py:1189/977 ctx safety floor + rsi_drift stamp: rsi_utils Wilder 1m
Question: how often do they disagree about (X < 45) / (X < 35) on the SAME candle?
Sample: A vs B over 14d x all 5m-capable tokens (every 3rd candle); A/B/C over 7d x
tokens actually traded (every 2nd 5m candle, C aligned at same ts from 1m candles).
Zero behavior — offline read-only.
"""
import sqlite3, statistics, json, sys
sys.path.insert(0, '/root/.hermes/scripts')
from paths import CANDLES_DB

FLOOR, KNIFE = 45.0, 35.0

def simple14(closes15_desc):
    d = [closes15_desc[i] - closes15_desc[i+1] for i in range(len(closes15_desc)-1)]
    g = sum(x for x in d if x > 0); l = sum(-x for x in d if x < 0)
    if l == 0: return 100.0
    return 100 - (100 / (1 + g/l))

def wilder20(closes_asc20):
    deltas = [closes_asc20[i] - closes_asc20[i-1] for i in range(1, len(closes_asc20))]
    g = [max(d,0) for d in deltas]; l = [max(-d,0) for d in deltas]
    ag = sum(g[:14])/14; al = sum(l[:14])/14
    for i in range(14, len(g)):
        ag = (ag*13 + g[i])/14; al = (al*13 + l[i])/14
    if al == 0: return 100.0
    return 100 - (100/(1 + ag/al))

def fetch(db, table, token, t0):
    rows = db.execute(f"SELECT ts, close FROM {table} WHERE token=? AND is_closed=1 AND ts>=? ORDER BY ts",
                      (token, t0)).fetchall()
    return [r[0] for r in rows], [r[1] for r in rows]

def band(flips, n):
    return 100.0*flips/n if n else 0.0

db = sqlite3.connect(f"file:{CANDLES_DB}?mode=ro", uri=True, timeout=10)
NOW = db.execute("SELECT MAX(ts) FROM candles_5m").fetchone()[0]
T0_14D, T0_7D = NOW - 14*86400, NOW - 7*86400

# ── Part 1: A vs B, 14d, every token, every 3rd 5m candle ──
tokens = [r[0] for r in db.execute("SELECT DISTINCT token FROM candles_5m").fetchall()]
n_obs = n_flip45 = n_flip35 = 0
diffs = []
per_token_flip = {}
for tk in tokens:
    ts, cl = fetch(db, 'candles_5m', tk, T0_14D)
    if len(cl) < 35: continue
    for i in range(19, len(cl), 3):
        A = simple14(cl[i-14:i+1][::-1])          # desc window of 15
        B = wilder20(cl[i-19:i+1])
        if A is None or B is None: continue
        n_obs += 1
        diffs.append(abs(A-B))
        f45 = (A < FLOOR) != (B < FLOOR)
        f35 = (A < KNIFE) != (B < KNIFE)
        n_flip45 += f45; n_flip35 += f35
        if f45:
            per_token_flip[tk] = per_token_flip.get(tk, 0) + 1
print(f"PART 1 — approval(5m-simple A) vs exec(5m-Wilder B), 14d, {len(tokens)} tokens")
print(f"  obs={n_obs}  mean|A-B|={statistics.mean(diffs):.2f}  median={statistics.median(diffs):.2f}  p95={sorted(diffs)[int(.95*len(diffs))]:.2f}")
print(f"  floor-45 decision flips: {n_flip45} ({band(n_flip45,n_obs):.2f}% of obs)")
print(f"  knife-35 decision flips: {n_flip35} ({band(n_flip35,n_obs):.2f}% of obs)")
top = sorted(per_token_flip.items(), key=lambda x:-x[1])[:8]
print(f"  top tokens by 45-flip count: {top}")

# ── Part 2: A/B/C all three, 7d, tokens traded last 7d, every 2nd 5m candle ──
import psycopg2
conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
cur = conn.cursor()
cur.execute("SELECT DISTINCT token FROM trades WHERE open_time > NOW() - INTERVAL '7 days'")
traded = [r[0] for r in cur.fetchall()]
conn.close()
n2 = fAB = fAC = fBC = f35_AC = 0
dAB = dAC = dBC = []
dAB, dAC, dBC = [], [], []
for tk in traded:
    ts5, cl5 = fetch(db, 'candles_5m', tk, T0_7D)
    ts1, cl1 = fetch(db, 'candles_1m', tk, T0_7D)
    if len(cl5) < 35 or len(cl1) < 35: continue
    j = 0
    for i in range(19, len(cl5), 2):
        t = ts5[i]
        # align: last 1m candle at or before t
        while j+1 < len(ts1) and ts1[j+1] <= t: j += 1
        if ts1[j] > t or j < 19: continue
        A = simple14(cl5[i-14:i+1][::-1]); B = wilder20(cl5[i-19:i+1]); C = wilder20(cl1[j-19:j+1])
        if None in (A, B, C): continue
        n2 += 1
        dAB.append(abs(A-B)); dAC.append(abs(A-C)); dBC.append(abs(B-C))
        fAB += (A < FLOOR) != (B < FLOOR)
        fAC += (A < FLOOR) != (C < FLOOR)
        fBC += (B < FLOOR) != (C < FLOOR)
        f35_AC += (A < KNIFE) != (C < KNIFE)
print(f"\nPART 2 — all three sources, 7d, {len(traded)} traded tokens")
print(f"  obs={n2}")
print(f"  mean|A-B|={statistics.mean(dAB):.2f}  mean|A-C|={statistics.mean(dAC):.2f}  mean|B-C|={statistics.mean(dBC):.2f}")
print(f"  floor-45 flips: A-vs-B {fAB} ({band(fAB,n2):.2f}%)  A-vs-C {fAC} ({band(fAC,n2):.2f}%)  B-vs-C {fBC} ({band(fBC,n2):.2f}%)")
print(f"  knife-35 flips: A-vs-C {f35_AC} ({band(f35_AC,n2):.2f}%)")
print("\nNOTE: B-vs-C flip rate = the false-comment impact (stamp claims 'same fetch as exec gates').")
db.close()
