#!/usr/bin/env python3
"""Audit part 4: independent recompute of the HML side claim
(63/70 hard_max_loss trades never reached +0.40% unrealized; median peak +0.07%)."""
import sqlite3, psycopg2, datetime as dt, statistics

CAND = sqlite3.connect("file:/root/.hermes/data/candles.db?mode=ro", uri=True)
PG = psycopg2.connect(host="/var/run/postgresql", dbname="brain", user="postgres")
pc = PG.cursor()
pc.execute("""
  SELECT id, token, direction, entry_price, exit_price, pnl_usdt, pnl_pct, leverage,
         open_time, close_time, peak_price, extract(epoch from (close_time-open_time))
  FROM trades
  WHERE status='closed' AND paper='f' AND exit_reason='hard_max_loss'
    AND close_time >= now() - interval '14 days'
  ORDER BY open_time""")
rows = pc.fetchall()
print(f"[HML] population (my SQL, now()-14d): n={len(rows)}")
print(f"[HML] peak_price NULL count: {sum(1 for r in rows if r[10] is None)}/{len(rows)}")

peaks_dir = []      # direction-aware best unrealized %
peaks_high = []     # MAX(high) regardless of direction (analyst's stated method)
nocov = []
detail = []
for (tid, tok, dire, entry, xit, pnlu, pnlp, lev, ot, ct, pk, dur) in rows:
    ots = int(ot.replace(tzinfo=dt.timezone.utc).timestamp())
    cts = int(ct.replace(tzinfo=dt.timezone.utc).timestamp())
    r = CAND.execute(
        "SELECT high, low, close FROM candles_1m WHERE token=? AND ts>=? AND ts<=? ",
        (tok.upper(), ots - 60, cts + 60)).fetchall()
    if not r:
        nocov.append((tid, tok)); continue
    e = float(entry); sgn = 1 if dire == 'LONG' else -1
    best_dir = max(((h - e) / e * 100 * sgn if sgn > 0 else (e - l) / e * 100) for (h, l, c) in r)
    best_high = max((h - e) / e * 100 for (h, l, c) in r)
    # also: max of direction-aware using close only (in case highs are wicks they call unrealistic)
    best_dir_close = max(((c - e) / e * 100 * sgn) for (h, l, c) in r)
    peaks_dir.append(best_dir); peaks_high.append(best_high)
    detail.append((tid, tok, dire, best_dir, best_high, best_dir_close, len(r), float(dur) / 60.0))

print(f"[HML] no candle coverage: {len(nocov)} {nocov[:8]}")
def summ(name, xs):
    xs = sorted(xs)
    n = len(xs)
    print(f"    {name}: n={n} median={xs[n//2]:+.3f}%  >=0.40%: {sum(1 for x in xs if x>=0.40)}  "
          f"<0.40%: {sum(1 for x in xs if x<0.40)}  max={xs[-1]:+.2f}%")
print("[HML] peak-unrealized variants:")
summ("direction-aware (high/low)", peaks_dir)
summ("MAX(high) all trades       ", peaks_high)
summ("direction-aware close-only ", [d[5] for d in detail])

print("\n[HML] trades whose direction-aware peak >= 0.40%:")
for d in detail:
    if d[3] >= 0.40:
        print(f"    id={d[0]} {d[1]} {d[2]} peak_dir={d[3]:+.2f}% peak_high={d[4]:+.2f}% "
              f"close_peak={d[5]:+.2f}% n_candles={d[6]} hold={d[7]:.0f}m")
print("\n[HML] 6 largest direction-aware peaks:")
for d in sorted(detail, key=lambda x: -x[3])[:6]:
    print(f"    id={d[0]} {d[1]} {d[2]} peak_dir={d[3]:+.2f}% hold={d[7]:.0f}m")
PG.close(); CAND.close()
print("DONE hml")
