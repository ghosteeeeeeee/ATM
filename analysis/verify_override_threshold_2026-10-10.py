#!/usr/bin/env python3
"""Verify LONG momentum override threshold bands. Read-only."""
import sqlite3, subprocess, json, sys, os
sys.path.insert(0, '/root/.hermes/scripts')

HERMES_DATA = '/root/.hermes/data'

def pg(q):
    r = subprocess.run(['sudo', '-u', 'postgres', 'psql', '-d', 'brain', '-t', '-A', '-F', '|', '-c', q],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr); sys.exit(1)
    return [l.split('|') for l in r.stdout.strip().split('\n') if l]

rows = pg("""
SELECT token, open_time, pnl_usdt, pnl_pct, signal, direction, confidence, leverage
FROM trades
WHERE status='closed' AND direction='LONG'
  AND open_time > NOW() - INTERVAL '21 days'
  AND pnl_usdt IS NOT NULL
""")
print(f"Fetched {len(rows)} closed LONG trades (21d)")

cont = sqlite3.connect(os.path.join(HERMES_DATA, 'continuum.db'), timeout=5)
candles = sqlite3.connect(os.path.join(HERMES_DATA, 'candles.db'), timeout=5)

def ts_of(s):
    # "2026-10-10 14:49:36.497752" -> epoch
    from datetime import datetime, timezone
    dt = datetime.fromisoformat(s)
    return dt.replace(tzinfo=timezone.utc).timestamp()

def cont_bearish_at(epoch):
    row = cont.execute(
        "SELECT market_phase, linreg_direction, ema300_position, ts FROM continuum_states WHERE token='BTC' AND ts<=? ORDER BY ts DESC LIMIT 1",
        (int(epoch),)).fetchone()
    if not row: return None
    phase, linreg, ema, ts = row
    if epoch - ts > 1800:  # >30min stale at open — flag
        return ('stale', phase, linreg, ema, ts)
    bear = phase in ('DECLINING','CALM','RECOVERY') and linreg in ('LEAN_BEAR','BEAR') and ema in ('BELOW','AT')
    return (bear, phase, linreg, ema, ts)

def vel_at(token, epoch):
    # last closed 15m candle at or before open
    rows15 = candles.execute(
        "SELECT close FROM candles_15m WHERE token=? AND is_closed=1 AND ts<=? ORDER BY ts DESC LIMIT 20",
        (token.upper(), int(epoch))).fetchall()
    if len(rows15) < 10: return None, None
    closes = [r[0] for r in reversed(rows15)]
    if closes[-6] <= 0: return None, None
    vel = (closes[-1] - closes[-6]) / closes[-6] * 100
    sma = sum(closes[-20:]) / len(closes[-20:])
    above = closes[-1] > sma
    return vel, above

from collections import defaultdict
bands = defaultdict(lambda: {'n':0,'w':0,'pnl':0.0,'an':0,'aw':0,'apnl':0.0})
bear_total = {'n':0,'w':0,'pnl':0.0}
skipped = 0
details = defaultdict(list)

for token, ot, pnl, pnl_pct, signal, direction, conf, lev in rows:
    try:
        epoch = ts_of(ot)
    except Exception:
        skipped += 1; continue
    cb = cont_bearish_at(epoch)
    if cb is None or cb[0] == 'stale':
        skipped += 1; continue
    if cb[0] is not True:
        continue  # not bearish BTC — out of scope
    vel, above = vel_at(token, epoch)
    if vel is None:
        skipped += 1; continue
    pnl = float(pnl)
    bear_total['n'] += 1
    bear_total['w'] += 1 if pnl > 0 else 0
    bear_total['pnl'] += pnl
    if vel < 0: b = '1_vel<0'
    elif vel < 0.50: b = '2_0-0.50'
    elif vel < 0.75: b = '3_0.50-0.75'
    elif vel < 1.00: b = '4_0.75-1.00'
    elif vel < 1.50: b = '5_1.00-1.50'
    else: b = '6_>=1.50'
    bands[b]['n'] += 1
    bands[b]['w'] += 1 if pnl > 0 else 0
    bands[b]['pnl'] += pnl
    if above:
        bands[b]['an'] += 1
        bands[b]['aw'] += 1 if pnl > 0 else 0
        bands[b]['apnl'] += pnl
    details[b].append((token, round(vel,3), above, signal, round(pnl,2)))

print(f"\nBearish-BTC LONG trades with vel data: {bear_total['n']} | WR {100*bear_total['w']/max(bear_total['n'],1):.1f}% | PnL ${bear_total['pnl']:.2f}")
print(f"Skipped (stale cont / no candles): {skipped}\n")
print(f"{'band':<14} {'n':>3} {'WR%':>6} {'PnL':>8} | {'aSMA_n':>6} {'aWR%':>6} {'aPnL':>8}")
for b in sorted(bands):
    d = bands[b]
    awr = 100*d['aw']/d['an'] if d['an'] else 0
    print(f"{b:<14} {d['n']:>3} {100*d['w']/d['n']:>6.1f} {d['pnl']:>8.2f} | {d['an']:>6} {awr:>6.1f} {d['apnl']:>8.2f}")

print("\nThreshold nets (above-SMA only, what override admits):")
LO = {'1_vel<0':-99,'2_0-0.50':0.0,'3_0.50-0.75':0.50,'4_0.75-1.00':0.75,'5_1.00-1.50':1.00,'6_>=1.50':1.50}
for thr in (0.50, 0.75, 1.00, 1.50):
    admitted = {'n':0,'w':0,'pnl':0.0}
    for b, d in bands.items():
        if LO[b] >= thr:
            admitted['n'] += d['an']; admitted['w'] += d['aw']; admitted['pnl'] += d['apnl']
    wr = 100*admitted['w']/admitted['n'] if admitted['n'] else 0
    print(f"  thr {thr:.2f}%: n={admitted['n']:>3} WR={wr:>5.1f}% PnL=${admitted['pnl']:>6.2f}")

print("\nDetails per band (above-SMA entries marked *):")
for b in sorted(details):
    print(f"  {b}:")
    for tok, vel, above, sig, pnl in sorted(details[b], key=lambda x: x[1]):
        print(f"    {'*' if above else ' '} {tok:<8} vel={vel:+.3f} {sig[:40]:<40} ${pnl:+.2f}")

cont.close(); candles.close()
