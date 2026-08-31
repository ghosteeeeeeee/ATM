#!/usr/bin/env python3
"""
Independent audit of MACD divergence trades.
For each trade, compute from 1m candle data:
  - RSI(14) at entry
  - Distance from 20-bar high at entry
  - 5-bar return at entry
  - MACD(8,50,12) histogram at entry
"""

import json, sqlite3, math, datetime

# ── Load trades ─────────────────────────────────────────────────────────────────
trades_data = json.load(open('/var/www/hermes/data/trades.json'))
all_closed = trades_data['closed']
macd_trades = [t for t in all_closed if 'macd-div' in t.get('signal', '').lower()]
print(f"Total macd-div trades: {len(macd_trades)}")

# ── Connect to candles.db ──────────────────────────────────────────────────────
CANDLES_DB = '/root/.hermes/data/candles.db'

def get_1m_candles(token, ts_seconds, n_bars=200):
    """Get 1m candles ending at or before ts_seconds."""
    conn = sqlite3.connect(CANDLES_DB, timeout=10)
    c = conn.cursor()
    c.execute(
        "SELECT ts, open, high, low, close FROM candles_1m "
        "WHERE token=? AND ts <= ? ORDER BY ts DESC LIMIT ?",
        (token.upper(), ts_seconds, n_bars)
    )
    rows = c.fetchall()
    conn.close()
    # oldest first
    return [(r[0], r[1], r[2], r[3], r[4]) for r in reversed(rows)]


def compute_rsi(closes, period=14):
    """Compute RSI on closes (oldest first)."""
    if len(closes) < period + 1:
        return None
    gains = []
    losses = []
    for i in range(1, len(closes)):
        change = closes[i] - closes[i - 1]
        gains.append(max(0, change))
        losses.append(max(0, -change))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    return 100 - (100 / (1 + avg_gain / avg_loss))


def compute_macd_histogram(closes, fast=8, slow=50, signal_period=12):
    """Compute MACD histogram."""
    if len(closes) < slow + signal_period:
        return None
    # EMA helper
    def ema(data, period):
        if len(data) < period:
            return [None] * len(data)
        k = 2.0 / (period + 1)
        result = [None] * (period - 1)
        ema_val = sum(data[:period]) / period
        result.append(ema_val)
        for price in data[period:]:
            ema_val = price * k + ema_val * (1 - k)
            result.append(ema_val)
        return result

    ema_fast = ema(closes, fast)
    ema_slow = ema(closes, slow)
    macd_line = []
    for ef, es in zip(ema_fast, ema_slow):
        if ef is None or es is None:
            macd_line.append(None)
        else:
            macd_line.append(ef - es)

    first_valid = slow - 1
    macd_valid = macd_line[first_valid:]
    if len(macd_valid) < signal_period:
        return None
    ema_sig = ema(macd_valid, signal_period)
    signal_line = [None] * first_valid + ema_sig
    hist = []
    for m, s in zip(macd_line, signal_line):
        if m is None or s is None:
            hist.append(None)
        else:
            hist.append(m - s)
    return hist


# ── Process each trade ─────────────────────────────────────────────────────────
results = []
for i, t in enumerate(macd_trades):
    token = t['coin']
    direction = t['direction']
    entry_price = t['entry']
    pnl_pct = t['pnl_pct']
    opened = t['opened']
    signal = t['signal']

    # Convert opened to timestamp
    dt = datetime.datetime.strptime(opened[:19], '%Y-%m-%d %H:%M:%S')
    ts_seconds = int(dt.timestamp())

    candles = get_1m_candles(token, ts_seconds, n_bars=200)
    if len(candles) < 60:
        print(f"Trade {i} ({token}): insufficient candles ({len(candles)})")
        continue

    # Closes oldest first
    closes = [c[4] for c in candles]
    highs = [c[2] for c in candles]
    lows = [c[3] for c in candles]

    # RSI(14) at entry (using last 15 closes)
    rsi = compute_rsi(closes, period=14)

    # Distance from 20-bar high
    # Entry is the last close
    last_close = closes[-1]
    high_20 = max(highs[-20:]) if len(highs) >= 20 else max(highs)
    dist_from_high = (last_close - high_20) / high_20 * 100  # percentage

    # 5-bar return
    if len(closes) >= 6:
        ret5 = (closes[-1] - closes[-6]) / closes[-6] * 100
    else:
        ret5 = None

    # MACD(8,50,12) histogram at entry
    hist = compute_macd_histogram(closes, fast=8, slow=50, signal_period=12)
    macd_hist = hist[-1] if hist and hist[-1] is not None else None

    result = {
        'trade': i,
        'token': token,
        'direction': direction,
        'entry': entry_price,
        'pnl_pct': pnl_pct,
        'signal': signal,
        'rsi14': round(rsi, 2) if rsi else None,
        'dist_from_20h': round(dist_from_high, 4),
        'ret5': round(ret5, 4) if ret5 else None,
        'macd_hist': round(macd_hist, 6) if macd_hist else None,
    }
    results.append(result)
    print(f"Trade {i:2d}: {token:6s} {direction:5s} entry={entry_price:10.6f} pnl={pnl_pct:+7.2f}% | RSI={rsi:6.2f} dist20h={dist_from_high:+7.4f}% ret5={ret5:+7.4f}% MACD_hist={macd_hist:+.6f} | {signal}")

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
winners = [r for r in results if r['pnl_pct'] > 0]
losers = [r for r in results if r['pnl_pct'] <= 0]
print(f"Winners: {len(winners)} | Losers: {len(losers)} | Winrate: {len(winners)/len(results)*100:.1f}%")
print(f"Total PnL%: {sum(r['pnl_pct'] for r in results):+.2f}%")
print(f"Total PnL$ (sum): {sum(t['pnl_usdt'] for t in macd_trades):+.2f}")

print("\n--- WINNERS ---")
for r in sorted(winners, key=lambda x: x['pnl_pct'], reverse=True):
    print(f"  {r['token']:6s} pnl={r['pnl_pct']:+7.2f}% RSI={r['rsi14']:6.2f} dist20h={r['dist_from_20h']:+7.4f}% ret5={r['ret5']:+7.4f}% MACD_hist={r['macd_hist']:+.6f}")

print("\n--- LOSERS ---")
for r in sorted(losers, key=lambda x: x['pnl_pct']):
    print(f"  {r['token']:6s} pnl={r['pnl_pct']:+7.2f}% RSI={r['rsi14']:6.2f} dist20h={r['dist_from_20h']:+7.4f}% ret5={r['ret5']:+7.4f}% MACD_hist={r['macd_hist']:+.6f}")

# ── Test the proposed filters ──────────────────────────────────────────────────
print("\n" + "="*80)
print("PROPOSED FILTER TEST: RSI>35 AND dist>-0.5% AND ret5>-0.3%")
print("="*80)
filtered = []
excluded = []
for r in results:
    passes = True
    if r['rsi14'] is not None and r['rsi14'] <= 35:
        passes = False
    if r['dist_from_20h'] is not None and r['dist_from_20h'] <= -0.5:
        passes = False
    if r['ret5'] is not None and r['ret5'] <= -0.3:
        passes = False
    if passes:
        filtered.append(r)
    else:
        excluded.append(r)

print(f"Passes filter: {len(filtered)} trades")
print(f"Excluded: {len(excluded)} trades")
if filtered:
    filtered_pnl = sum(r['pnl_pct'] for r in filtered)
    filtered_wr = len([r for r in filtered if r['pnl_pct'] > 0]) / len(filtered) * 100
    print(f"Filtered WR: {filtered_wr:.1f}% | Filtered PnL%: {filtered_pnl:+.2f}%")
    for r in filtered:
        print(f"  PASS  {r['token']:6s} pnl={r['pnl_pct']:+7.2f}% RSI={r['rsi14']:6.2f} dist20h={r['dist_from_20h']:+7.4f}% ret5={r['ret5']:+7.4f}%")
if excluded:
    excluded_pnl = sum(r['pnl_pct'] for r in excluded)
    excluded_wr = len([r for r in excluded if r['pnl_pct'] > 0]) / len(excluded) * 100 if excluded else 0
    print(f"\nExcluded WR: {excluded_wr:.1f}% | Excluded PnL%: {excluded_pnl:+.2f}%")
    for r in excluded:
        print(f"  EXCL  {r['token']:6s} pnl={r['pnl_pct']:+7.2f}% RSI={r['rsi14']:6.2f} dist20h={r['dist_from_20h']:+7.4f}% ret5={r['ret5']:+7.4f}%")

# ── Overall improvement ───────────────────────────────────────────────────────
print("\n" + "="*80)
print("IMPROVEMENT CALCULATION")
print("="*80)
orig_pnl = sum(t['pnl_usdt'] for t in macd_trades)
new_pnl = sum(t['pnl_usdt'] for t in macd_trades if any(r['token'] == t['coin'] and r['pnl_pct'] == t['pnl_pct'] for r in filtered))
print(f"Original total PnL$: {orig_pnl:+.2f}")
print(f"After filter total PnL$: {new_pnl:+.2f}")
print(f"Improvement: {new_pnl - orig_pnl:+.2f}")

# Save results for later
json.dump(results, open('/root/.hermes/data/audit_macd_results.json', 'w'), indent=2)
