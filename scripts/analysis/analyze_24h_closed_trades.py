#!/usr/bin/env python3
"""
Deep analysis of last 24h closed trades.
- Splits WIN vs LOSS
- For each: duration, signal type, leverage, confidence, price action (max excursion, MAE)
- Identifies patterns in winners vs losers
- Looks at SL distance vs actual price move
- Highlights MERL/ENS/AAVE/TAO/ONDO/UMA losses
- Highlights ASTER 10-second bug
"""
import psycopg2
import json
import sqlite3
from datetime import datetime
from collections import defaultdict

# PG conn
conn = psycopg2.connect(host='/var/run/postgresql', dbname='brain', user='postgres')
cur = conn.cursor()

# Pull all 24h closed trades
cur.execute("""
    SELECT id, token, direction, entry_price, exit_price, pnl_usdt, pnl_pct,
           exit_reason, open_time, close_time, signal, confidence, leverage,
           stop_loss, target, _signal_metadata, highest_price, current_price,
           server
    FROM trades
    WHERE status='closed' AND close_time > NOW() - INTERVAL '24 hours'
    ORDER BY open_time ASC
""")
trades = []
for r in cur.fetchall():
    trades.append({
        'id': r[0], 'token': r[1], 'dir': r[2],
        'entry': float(r[3]), 'exit': float(r[4]),
        'pnl': float(r[5]), 'pnl_pct': float(r[6]),
        'exit_reason': r[7], 'open_time': r[8], 'close_time': r[9],
        'signal': r[10], 'confidence': r[11], 'leverage': r[12],
        'sl': float(r[13]) if r[13] else None,
        'target': float(r[14]) if r[14] else None,
        'meta': r[15] or {}, 'highest': float(r[16]) if r[16] else None,
        'current': float(r[17]) if r[17] else None,
        'server': r[18]
    })

print(f"=== {len(trades)} closed trades in last 24h ===\n")

# 1) CUMULATIVE PNL TIMELINE
print("=" * 80)
print("CUMULATIVE PNL TIMELINE (T shows inflection points)")
print("=" * 80)
cum = 0
peak = 0
peak_at = None
trough = 0
trough_at = None
streak = 0
streak_type = None
streak_pnl = 0
streaks = []
for t in trades:
    cum += t['pnl']
    if cum > peak:
        peak = cum
        peak_at = t['close_time']
    if cum < trough:
        trough = cum
        trough_at = t['close_time']
    # streak detection
    win = t['pnl'] > 0
    if streak_type is None or (win != streak_type):
        if streak_type is not None and len(streak) >= 2:
            streaks.append((streak_type, len(streak), sum(x['pnl'] for x in streak)))
        streak_type = win
        streak = [t]
    else:
        streak.append(t)
if streak_type is not None and len(streak) >= 2:
    streaks.append((streak_type, len(streak), sum(x['pnl'] for x in streak)))

print(f"Net: ${cum:+.2f} | Peak: ${peak:+.2f} @ {peak_at} | Trough: ${trough:+.2f} @ {trough_at}")
print(f"Streaks (>=2):")
for kind, n, pnl in streaks:
    label = "WINS " if kind else "LOSS "
    print(f"  {label} n={n:2d}  net=${pnl:+.2f}")

# 2) SPLIT WINS VS LOSSES — show in sequence
print("\n" + "=" * 80)
print("WINS vs LOSSES IN SEQUENCE (in open_time order)")
print("=" * 80)
for t in trades:
    marker = "W " if t['pnl'] > 0 else "L "
    dur = (t['close_time'] - t['open_time']).total_seconds()
    print(f"  {marker} #{t['id']:5d} {t['token']:6s} {t['dir']:5s} | "
          f"dur={dur:6.0f}s | lev={t['leverage']}x | conf={t['confidence'] or 'N/A':>4} | "
          f"pnl=${t['pnl']:+.2f} ({t['pnl_pct']:+.2f}%) | "
          f"exit={t['exit_reason']:15s} | sig={t['signal'] or 'NONE':25s}")

# 3) GROUP BY OUTCOME — DISTRIBUTIONS
print("\n" + "=" * 80)
print("WINNER vs LOSER PROFILE")
print("=" * 80)
wins = [t for t in trades if t['pnl'] > 0]
losses = [t for t in trades if t['pnl'] < 0]

def profile(name, group):
    if not group:
        return
    durs = [(t['close_time'] - t['open_time']).total_seconds() for t in group]
    pnl_pcts = [t['pnl_pct'] for t in group]
    levs = [t['leverage'] for t in group]
    confs = [t['confidence'] for t in group if t['confidence']]
    long_pct = sum(1 for t in group if t['dir'] == 'LONG') / len(group) * 100
    short_pct = sum(1 for t in group if t['dir'] == 'SHORT') / len(group) * 100
    signals = defaultdict(int)
    for t in group:
        signals[t['signal'] or 'NONE'] += 1
    exits = defaultdict(int)
    for t in group:
        exits[t['exit_reason']] += 1
    avg_pnl = sum(t['pnl'] for t in group) / len(group)
    avg_dur = sum(durs) / len(durs)
    print(f"\n  {name}: n={len(group)}  total=${sum(t['pnl'] for t in group):+.2f}  avg=${avg_pnl:+.3f}")
    print(f"    LONG {long_pct:.0f}% | SHORT {short_pct:.0f}%")
    print(f"    avg duration: {avg_dur:.0f}s ({avg_dur/60:.1f}min) | range: {min(durs):.0f}-{max(durs):.0f}s")
    print(f"    pnl_pct: avg {sum(pnl_pcts)/len(pnl_pcts):+.2f}% | range {min(pnl_pcts):+.2f} to {max(pnl_pcts):+.2f}")
    print(f"    leverage: avg {sum(levs)/len(levs):.1f}x | vals {sorted(set(levs))}")
    if confs:
        print(f"    confidence: avg {sum(confs)/len(confs):.1f} | range {min(confs):.0f}-{max(confs):.0f}")
    print(f"    signals: {dict(signals)}")
    print(f"    exit_reasons: {dict(exits)}")
    # leverage breakdown
    by_lev = defaultdict(list)
    for t in group:
        by_lev[t['leverage']].append(t['pnl'])
    print(f"    PnL by leverage: " + " | ".join(f"{lev}x: ${sum(v):+.2f} (n={len(v)}, wr={sum(1 for x in v if x>0)/len(v)*100:.0f}%)" for lev, v in sorted(by_lev.items())))

profile("WINNERS", wins)
profile("LOSERS", losses)

# 4) PER-TOKEN BREAKDOWN
print("\n" + "=" * 80)
print("PER-TOKEN BREAKDOWN (last 24h)")
print("=" * 80)
by_token = defaultdict(list)
for t in trades:
    by_token[t['token']].append(t)
for tok in sorted(by_token.keys()):
    grp = by_token[tok]
    net = sum(t['pnl'] for t in grp)
    wr = sum(1 for t in grp if t['pnl'] > 0) / len(grp) * 100
    avg_pct = sum(t['pnl_pct'] for t in grp) / len(grp)
    sigs = set(t['signal'] for t in grp)
    print(f"  {tok:8s} n={len(grp):2d}  wr={wr:5.0f}%  net=${net:+.2f}  avg%={avg_pct:+.2f}  | sigs={sigs}")

# 5) SIGNAL TYPE BREAKDOWN
print("\n" + "=" * 80)
print("SIGNAL TYPE BREAKDOWN")
print("=" * 80)
by_sig = defaultdict(list)
for t in trades:
    by_sig[t['signal'] or 'NONE'].append(t)
for sig in sorted(by_sig.keys()):
    grp = by_sig[sig]
    net = sum(t['pnl'] for t in grp)
    wr = sum(1 for t in grp if t['pnl'] > 0) / len(grp) * 100
    avg_pct = sum(t['pnl_pct'] for t in grp) / len(grp)
    avg_dur = sum((t['close_time'] - t['open_time']).total_seconds() for t in grp) / len(grp)
    print(f"  {sig:30s} n={len(grp):2d}  wr={wr:5.0f}%  net=${net:+.2f}  avg%={avg_pct:+.2f}  avg_dur={avg_dur:.0f}s")

# 6) SPECIFIC BUG INVESTIGATION — ASTER 10s
print("\n" + "=" * 80)
print("ASTER 10-SECOND BUG INVESTIGATION")
print("=" * 80)
cur.execute("""
    SELECT id, token, direction, entry_price, exit_price, pnl_usdt, pnl_pct,
           exit_reason, open_time, close_time, signal, confidence, leverage,
           stop_loss, current_price, highest_price, server, exchange, _signal_metadata
    FROM trades
    WHERE token='ASTER' AND close_time > NOW() - INTERVAL '24 hours'
    ORDER BY open_time
""")
for r in cur.fetchall():
    t = {
        'id': r[0], 'token': r[1], 'dir': r[2],
        'entry': float(r[3]), 'exit': float(r[4]),
        'pnl': float(r[5]), 'pnl_pct': float(r[6]),
        'exit_reason': r[7], 'open_time': r[8], 'close_time': r[9],
        'signal': r[10], 'conf': r[11], 'leverage': r[12],
        'sl': float(r[13]) if r[13] else None,
        'current': float(r[14]) if r[14] else None,
        'highest': float(r[15]) if r[15] else None,
        'server': r[16], 'exchange': r[17],
        'meta': r[18] or {}
    }
    dur = (t['close_time'] - t['open_time']).total_seconds()
    print(f"  #{t['id']} {t['dir']:5s} | dur={dur:.0f}s | "
          f"entry={t['entry']:.5f} -> exit={t['exit']:.5f} | "
          f"SL={t['sl']:.5f} | highest={t['highest']:.5f} | "
          f"current_at_close={t['current']:.5f}")
    print(f"     exit_reason={t['exit_reason']:20s} | pnl=${t['pnl']:+.2f} ({t['pnl_pct']:+.2f}%) | "
          f"conf={t['conf']} | lev={t['leverage']}x | server={t['server']} | exchange={t['exchange']}")
    # For a SHORT: profit if exit < entry. Check whether exit even moved
    if t['dir'] == 'SHORT':
        # ideal target would be lower price, SL would be higher
        if t['exit'] > t['entry']:
            print(f"     *** EXIT PRICE > ENTRY (price went UP, against SHORT) — moved {((t['exit']/t['entry'])-1)*100:.3f}%")
        elif t['exit'] < t['entry']:
            print(f"     EXIT < entry (price went DOWN, FOR short), price dropped {((1-t['exit']/t['entry'])*100):.3f}%")
    # Check if exit happened before price could even move
    print()

# 7) PRICE ACTION ON BIGGEST LOSSES
print("=" * 80)
print("PRICE ACTION ON BIGGEST LOSSES — what did price do during trade?")
print("=" * 80)
biggest_losses = sorted(losses, key=lambda x: x['pnl'])[:10]

# Connect to candles
candle_conn = sqlite3.connect('/root/.hermes/data/candles.db')

for t in biggest_losses:
    print(f"\n  #{t['id']} {t['token']:6s} {t['dir']:5s} | pnl=${t['pnl']:+.2f} ({t['pnl_pct']:+.2f}%) | "
          f"exit={t['exit_reason']:15s} | dur={(t['close_time']-t['open_time']).total_seconds():.0f}s")
    print(f"     entry={t['entry']:.6f} exit={t['exit']:.6f} sl={t['sl'] if t['sl'] else 'N/A'} target={t['target'] if t['target'] else 'N/A'}")
    print(f"     signal={t['signal']} | conf={t['confidence']} | lev={t['leverage']}x")

    # Get 1m candles around the trade
    open_unix = int(t['open_time'].timestamp())
    close_unix = int(t['close_time'].timestamp())
    cur_c = candle_conn.cursor()
    cur_c.execute("""
        SELECT ts, open, high, low, close FROM candles_1m
        WHERE token=? AND ts BETWEEN ? AND ?
        ORDER BY ts
    """, (t['token'], open_unix - 600, close_unix + 600))
    rows = cur_c.fetchall()
    if not rows:
        print(f"     NO 1m candle data for {t['token']}")
        continue

    # Find max favorable (MFE) and max adverse (MAE) excursion during trade
    in_trade = [r for r in rows if open_unix <= r[0] <= close_unix]
    if not in_trade:
        print(f"     No in-trade candles (data gap)")
        continue

    highs = [r[2] for r in in_trade]
    lows = [r[3] for r in in_trade]

    if t['dir'] == 'LONG':
        mfe_pct = (max(highs) - t['entry']) / t['entry'] * 100  # max upside
        mae_pct = (t['entry'] - min(lows)) / t['entry'] * 100  # max drawdown
        print(f"     1m candle during trade: n={len(in_trade)} bars")
        print(f"     MFE (best LONG excursion): {mfe_pct:+.2f}%  (peak high {max(highs):.6f})")
        print(f"     MAE (worst drawdown): {mae_pct:+.2f}%  (trough low {min(lows):.6f})")
        print(f"     Final close: {in_trade[-1][4]:.6f}")
        # Path: did price hit MFE first then reverse?
        peak_idx = next(i for i, r in enumerate(in_trade) if r[2] == max(highs))
        trough_idx = next(i for i, r in enumerate(in_trade) if r[3] == min(lows))
        print(f"     Peak bar #{peak_idx}/{len(in_trade)-1}, trough bar #{trough_idx}/{len(in_trade)-1}")
        if mfe_pct > 0.5 and t['pnl'] < 0:
            print(f"     *** MISSED OPPORTUNITY: price moved +{mfe_pct:.2f}% but trade lost {t['pnl_pct']:+.2f}%")
    else:  # SHORT
        mfe_pct = (t['entry'] - min(lows)) / t['entry'] * 100  # max DOWN-move = profit
        mae_pct = (max(highs) - t['entry']) / t['entry'] * 100  # max UP-move = pain
        print(f"     1m candle during trade: n={len(in_trade)} bars")
        print(f"     MFE (best SHORT excursion): {mfe_pct:+.2f}%  (peak low {min(lows):.6f})")
        print(f"     MAE (worst upside): {mae_pct:+.2f}%  (trough high {max(highs):.6f})")
        print(f"     Final close: {in_trade[-1][4]:.6f}")
        peak_idx = next(i for i, r in enumerate(in_trade) if r[3] == min(lows))
        trough_idx = next(i for i, r in enumerate(in_trade) if r[2] == max(highs))
        print(f"     Peak bar #{peak_idx}/{len(in_trade)-1}, trough bar #{trough_idx}/{len(in_trade)-1}")
        if mfe_pct > 0.5 and t['pnl'] < 0:
            print(f"     *** MISSED OPPORTUNITY: price dropped {mfe_pct:.2f}% then reversed to hit SL")

# 8) PRICE ACTION ON WINNERS
print("\n" + "=" * 80)
print("PRICE ACTION ON WINNERS — what did price do during trade?")
print("=" * 80)
biggest_wins = sorted(wins, key=lambda x: -x['pnl'])[:10]
for t in biggest_wins:
    print(f"\n  #{t['id']} {t['token']:6s} {t['dir']:5s} | pnl=${t['pnl']:+.2f} ({t['pnl_pct']:+.2f}%) | "
          f"exit={t['exit_reason']:15s} | dur={(t['close_time']-t['open_time']).total_seconds():.0f}s")
    print(f"     entry={t['entry']:.6f} exit={t['exit']:.6f}")
    print(f"     signal={t['signal']} | conf={t['confidence']} | lev={t['leverage']}x")

    open_unix = int(t['open_time'].timestamp())
    close_unix = int(t['close_time'].timestamp())
    cur_c = candle_conn.cursor()
    cur_c.execute("""
        SELECT ts, open, high, low, close FROM candles_1m
        WHERE token=? AND ts BETWEEN ? AND ?
        ORDER BY ts
    """, (t['token'], open_unix - 600, close_unix + 600))
    rows = cur_c.fetchall()
    if not rows:
        print(f"     NO 1m candle data for {t['token']}")
        continue
    in_trade = [r for r in rows if open_unix <= r[0] <= close_unix]
    if not in_trade:
        print(f"     No in-trade candles")
        continue
    highs = [r[2] for r in in_trade]
    lows = [r[3] for r in in_trade]
    if t['dir'] == 'LONG':
        mfe_pct = (max(highs) - t['entry']) / t['entry'] * 100
        mae_pct = (t['entry'] - min(lows)) / t['entry'] * 100
        print(f"     MFE: {mfe_pct:+.2f}% | MAE: {mae_pct:+.2f}% | n={len(in_trade)} bars")
    else:
        mfe_pct = (t['entry'] - min(lows)) / t['entry'] * 100
        mae_pct = (max(highs) - t['entry']) / t['entry'] * 100
        print(f"     MFE: {mfe_pct:+.2f}% | MAE: {mae_pct:+.2f}% | n={len(in_trade)} bars")
    print(f"     Final close: {in_trade[-1][4]:.6f}")

conn.close()
candle_conn.close()
