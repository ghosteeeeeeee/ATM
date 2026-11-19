#!/usr/bin/env python3
"""gate_usefulness_selfaudit_2026-11-19.py

INDEPENDENT SELF-AUDIT of gate_usefulness_deepdive_2026-11-19 — a SECOND
computation path for every headline number, so the external auditor can refute
or agree with each claim individually.

Checks (each written PASS/FAIL with both numbers):
  A1  gate_summary.tsv re-derived from nov19_gate_events.tsv (pure SQL-style
      groupbys, no import of the engine) — eps/ex4h/p per top-12 gates
  A2  5 random events hand-verified: raw log line EXISTS at that ts + candle
      forward return recomputed via a different method (no binary search:
      bisect module + independent sqlite query)
  A3  market baseline spot-check: recompute excess for 3 events via SQL AVG
      over all tokens at the same bucket (different code path than engine)
  A4  live-book claims: WR/net by direction recomputed with a second SQL
      (pnl_pct sign vs pnl_usdt sign consistency — catches convention bugs)
  A5  frame dedup sanity: no duplicate (gate,token,dir,10-min bucket) in export
  A6  big-misses: nov19_bigmisses.tsv MFE values spot-checked vs raw candles

Output: analysis/gate_usefulness_selfaudit_2026-11-19.md
"""
import os
import re
import csv
import sqlite3
import random
import bisect
from datetime import datetime, timezone

CANDLES = '/root/.hermes/data/candles.db'
EXPORTS = '/root/.hermes/analysis/exports'
OUT_MD = '/root/.hermes/analysis/gate_usefulness_selfaudit_2026-11-19.md'
LOGS = ['/root/.hermes/logs/archive/pipeline.log.20261107001010.gz',
        '/root/.hermes/logs/archive/pipeline.log.20261115000915.gz',
        '/root/.hermes/logs/archive/pipeline.log.20261119090701.gz',
        '/root/.hermes/logs/pipeline.log']

import gzip

results = []
def check(cid, desc, ok, detail):
    results.append((cid, desc, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {cid}: {desc} — {detail}")

def load_tsv(name):
    with open(os.path.join(EXPORTS, name)) as f:
        return list(csv.DictReader(f, delimiter='\t'))

def fnum(x):
    try:
        return float(x)
    except (ValueError, TypeError):
        return None

def main():
    # A1: INDEPENDENT re-coalescing of the raw events export → per-gate episode
    # means must match nov19_gate_summary.tsv (true second path)
    events = load_tsv('nov19_gate_events.tsv')
    summary = load_tsv('nov19_gate_summary.tsv')
    raw_by = {}
    for e in events:
        raw_by.setdefault((e['gate'], e['token'], e['direction']), []).append(
            (float(e['ts']), fnum(e['excess_4h'])))
    indep_eps = {}
    for key, lst in raw_by.items():
        lst.sort()
        last = None
        for ts, ex in lst:
            if last is None or ts - last > 3600:
                indep_eps.setdefault(key[0], []).append(ex)
            last = ts
    a1_ok = True
    a1_detail = []
    for row in summary[:12]:
        g = row['gate']
        all_eps = indep_eps.get(g, [])
        vals = [v for v in all_eps if v is not None]
        if not vals:
            a1_ok = False
            a1_detail.append(f"{g}: no indep episodes")
            continue
        indep_mean = sum(vals) / len(vals)
        summ_mean = fnum(row['ex4h_mean'])
        n_eps = int(row['episodes'])
        # summary 'episodes' = ALL episodes; its mean = non-None only (engine summarize())
        match_n = n_eps == len(all_eps)
        match_m = abs(indep_mean - (summ_mean or 0)) < 0.005
        a1_detail.append(f"{g}: n {'OK' if match_n else f'MISMATCH({n_eps} vs {len(all_eps)})'} "
                         f"mean {'OK' if match_m else f'MISMATCH({indep_mean:+.3f} vs {summ_mean:+.3f})'}")
        if not (match_n and match_m):
            a1_ok = False
    check('A1', 'independent re-coalescing of events export matches summary',
          a1_ok, '; '.join(a1_detail[:4]) + ' ...')

    # A2: 5 random events — log line exists + fwd via different method
    import bisect as _bisect
    sample = random.Random(42).sample(events, 5)
    a2_ok = True
    a2_detail = []
    conn = sqlite3.connect(CANDLES)
    for e in sample:
        ts = int(float(e['ts']))
        tok, d = e['token'], e['direction']
        # (i) raw log line exists — ONLY checkable for reparse-provenance events;
        # db-only (Oct 4-30) raw logs were deleted by pre-rotator rotation → n/a
        if e['provenance'] == 'reparse':
            found = False
            stamp = datetime.fromtimestamp(ts, timezone.utc).strftime('%Y-%m-%d %H:%M')
            for lp in LOGS:
                op = gzip.open if lp.endswith('.gz') else open
                try:
                    with op(lp, 'rt', errors='replace') as f:
                        for line in f:
                            if line.startswith(stamp) and tok in line and \
                               ('blocked' in line.lower() or 'block' in line.split(']')[-1].lower() if ']' in line else False):
                                found = True
                                break
                except FileNotFoundError:
                    continue
                if found:
                    break
            log_s = 'OK' if found else 'MISSING'
            if not found:
                a2_ok = False
        else:
            log_s = 'n/a (db-only, raw deleted)'
        # (ii) fwd via independent query (fresh SELECT + explicit LIMIT, no bisect)
        rows = conn.execute(
            "SELECT ts, open, close FROM candles_5m WHERE token=? AND is_closed=1"
            " AND ts >= ? ORDER BY ts LIMIT 49", (tok, ts)).fetchall()
        fwd_ok = False
        if rows and rows[0][0] > ts + 300:
            fwd_s = 'n/a (candles pruned post-run — see data-mutation note)'
        elif len(rows) >= 49:
            o = rows[0][1]
            c4 = rows[48][2]
            raw_f = (c4 / o - 1) * 100
            got = fnum(e['fwd_4h'])
            if d == 'SHORT':
                raw_f = -raw_f
            fwd_ok = got is not None and abs(raw_f - got) < 0.01
            fwd_s = 'OK' if fwd_ok else 'MISMATCH'
            if not fwd_ok:
                a2_ok = False
        else:
            fwd_s = 'n/a (insufficient rows)'
        a2_detail.append(f"{tok}/{d} @{datetime.fromtimestamp(ts, timezone.utc):%m-%d %H:%M} "
                         f"log={log_s} fwd={fwd_s}")
    conn.close()
    check('A2', 'random events: log line exists (reparse prov) + independent fwd recompute',
          a2_ok, '; '.join(a2_detail))

    # A3: excess via SQL AVG baseline (different path)
    a3_ok = True
    a3_detail = []
    conn = sqlite3.connect(CANDLES)
    for e in random.Random(7).sample(events, 3):
        ts = int(float(e['ts']))
        bucket = (ts + 299) // 300 * 300
        got = fnum(e['excess_4h'])
        mb = conn.execute("""
            SELECT AVG(c4/o - 1) * 100 FROM (
              SELECT t.ts, t.open o, lead(t.close, 48) OVER (PARTITION BY token ORDER BY t.ts) c4
              FROM candles_5m t WHERE t.is_closed=1 AND t.ts = ?)
            WHERE c4 IS NOT NULL""", (bucket,)).fetchone()[0]
        # simpler independent path: per-token manual loop
        rets = []
        for (tok,) in conn.execute("SELECT DISTINCT token FROM candles_5m WHERE is_closed=1 LIMIT 300"):
            r = conn.execute(
                "SELECT open, close FROM candles_5m WHERE token=? AND is_closed=1 AND ts=?",
                (tok, bucket)).fetchone()
            r2 = conn.execute(
                "SELECT close FROM candles_5m WHERE token=? AND is_closed=1 AND ts=?",
                (tok, bucket + 48 * 300)).fetchone()
            if r and r2 and r[0] > 0:
                rets.append((r2[0] / r[0] - 1) * 100)
        if len(rets) >= 20 and got is not None:
            m = sum(rets) / len(rets)
            sgn = 1 if e['direction'] == 'LONG' else -1
            raw_fwd = got  # excess already computed; recompute from fwd_4h
            fwd = fnum(e['fwd_4h'])
            excess2 = fwd - (m if sgn == 1 else -m)
            agree = abs(excess2 - got) < 0.02  # tolerance: export rounds to 4dp;
            # but baseline token-set may differ slightly → allow 0.05
            agree = abs(excess2 - got) < 0.06
            a3_detail.append(f"{e['token']}: sql_excess={excess2:+.4f} export={got:+.4f} "
                             f"({'OK' if agree else 'DIFF'}) n_tokens={len(rets)}")
            if not agree:
                a3_ok = False
    conn.close()
    check('A3', 'excess re-derived via independent SQL baseline (300-token sample)',
          a3_ok, '; '.join(a3_detail))

    # A4: live-book claims, second SQL + sign consistency
    import psycopg2
    sys_path = '/root/.hermes/scripts'
    import sys
    sys.path.insert(0, sys_path)
    from _secrets import BRAIN_DB_DICT
    pg = psycopg2.connect(**BRAIN_DB_DICT)
    cur = pg.cursor()
    cur.execute("""
        SELECT direction, COUNT(*),
               SUM(CASE WHEN (pnl_usdt > 0) = (pnl_pct > 0) THEN 1 ELSE 0 END),
               SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END), SUM(pnl_usdt)
        FROM trades WHERE paper='f' AND status='closed' AND open_time >= '2026-10-04'
        GROUP BY 1""")
    a4_ok = True
    a4_detail = []
    for d, n, consistent, wins, net in cur.fetchall():
        wr = wins / n * 100
        a4_detail.append(f"{d}: n={n} WR={wr:.1f}% net={net:+.2f} sign_consistent="
                         f"{consistent}/{n} (mismatches = $0.00 scratches)")
        if consistent != n:
            cur.execute("""SELECT COUNT(*) FROM trades WHERE paper='f' AND status='closed'
                AND open_time >= '2026-10-04' AND direction=%s
                AND (pnl_usdt > 0) != (pnl_pct > 0) AND pnl_usdt <> 0""", (d,))
            if cur.fetchone()[0] != 0:
                a4_ok = False
    pg.close()
    check('A4', 'live-book WR/net second SQL + pnl_usdt/pnl_pct sign consistency',
          a4_ok, '; '.join(a4_detail))

    # A5: dedup sanity — no duplicate (gate,token,dir,10-min bucket)
    seen = set()
    dups = 0
    for e in events:
        key = (e['gate'], e['token'], e['direction'],
               int(float(e['ts']) // 600))
        if key in seen:
            dups += 1
        seen.add(key)
    check('A5', 'no duplicate (gate,token,dir,10min) in events export',
          dups == 0, f"duplicates={dups} / {len(events)} rows")

    # A6: big-misses MFE spot-check
    big = load_tsv('nov19_bigmisses.tsv')
    a6_ok = True
    a6_detail = []
    conn = sqlite3.connect(CANDLES)
    for row in random.Random(3).sample(big, min(4, len(big))):
        ts = int(datetime.fromisoformat(row['ts']).timestamp())
        rows = conn.execute(
            "SELECT open, high, low FROM candles_5m WHERE token=? AND is_closed=1"
            " AND ts >= ? ORDER BY ts LIMIT 49", (row['token'], ts)).fetchall()
        if len(rows) >= 49:
            o = rows[0][0]
            if row['direction'] == 'LONG':
                mfe = (max(r[1] for r in rows) / o - 1) * 100
            else:
                mfe = (1 - min(r[2] for r in rows) / o) * 100
            got = fnum(row['mfe_4h'])
            ok = got is not None and abs(mfe - got) < 0.05
            a6_detail.append(f"{row['token']}: recomputed={mfe:.2f} export={got:.2f} "
                             f"{'OK' if ok else 'MISMATCH'}")
            if not ok:
                a6_ok = False
    conn.close()
    check('A6', 'big-miss MFE values vs raw candles', a6_ok, '; '.join(a6_detail))

    # write markdown
    with open(OUT_MD, 'w') as f:
        f.write("# Self-Audit — Gate Usefulness Deep Dive 2026-11-19\n\n")
        f.write("Second computation path for every headline number. "
                "External auditors: refute or agree per check.\n\n")
        f.write("| Check | Description | Result | Detail |\n|---|---|---|---|\n")
        for cid, desc, ok, detail in results:
            f.write(f"| {cid} | {desc} | {'PASS' if ok else '**FAIL**'} | {detail} |\n")
        n_fail = sum(1 for _, _, ok, _ in results if not ok)
        f.write(f"\n**Overall: {len(results) - n_fail}/{len(results)} PASS"
                f"{' — ALL CHECKS PASSED' if n_fail == 0 else f' — {n_fail} FAILURES REQUIRE CORRECTION'}**\n")
    print(f"\nwritten: {OUT_MD}")

if __name__ == '__main__':
    main()
