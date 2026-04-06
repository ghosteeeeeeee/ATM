#!/usr/bin/env python3
"""Backtest: chart patterns vs minimal prompt on qwen2.5:1.5b.

Two variants:
  A) Minimal (baseline) — trend + RSI category
  B) Chart patterns — describe actual candle patterns detected, no raw numbers
"""

import json, requests, sqlite3, time, sys
import statistics

OLLAMA = 'http://127.0.0.1:11434/api/generate'
MODEL = 'qwen2.5:1.5b'

def call_ollama(prompt, num_predict=15):
    r = requests.post(OLLAMA, json={
        'model': MODEL,
        'prompt': prompt,
        'stream': False,
        'options': {'temperature': 0.3, 'num_predict': num_predict}
    }, timeout=30)
    return r.json().get('response', '').strip().upper()

# ── Candlestick pattern detection ──────────────────────────────────────────────

def candle_pattern(closes, opens, highs, lows):
    """Return list of detected patterns in the last 3 candles."""
    if len(closes) < 3:
        return []

    patterns = []

    c0, c1, c2 = closes[-1], closes[-2], closes[-3]
    o0, o1, o2 = opens[-1], opens[-2], opens[-3]
    h0, h1, h2 = highs[-1], highs[-2], highs[-3]
    l0, l1, l2 = lows[-1], lows[-2], lows[-3]

    body2 = abs(c2 - o2)
    body1 = abs(c1 - o1)
    body0 = abs(c0 - o0)

    # Upper shadow / lower shadow sizes
    def upper_shadow(o, c, h): return h - max(o, c)
    def lower_shadow(o, c, l): return min(o, c) - l

    # ── Single-candle patterns ─────────────────────────────────────────────────
    # Doji: tiny body relative to range
    for i in range(3):
        body = abs(closes[i] - opens[i])
        range_ = highs[i] - lows[i]
        if range_ > 0 and body / range_ < 0.1:
            patterns.append('doji')

    # Hammer / inverted hammer (last candle)
    ls0 = lower_shadow(o0, c0, l0)
    us0 = upper_shadow(o0, c0, h0)
    if c0 > o0 and ls0 > 2 * body0 and us0 < body0:
        patterns.append('hammer')       # bullish reversal
    if c0 < o0 and us0 > 2 * body0 and ls0 < body0:
        patterns.append('shooting_star') # bearish reversal

    # ── Two-candle patterns ───────────────────────────────────────────────────
    if len(closes) >= 2:
        # Engulfing bullish
        if c1 < o1 and c0 > o0:  # first candle bearish, second bullish
            if c0 > o1 and o0 < c1:
                patterns.append('bullish_engulfing')
        # Engulfing bearish
        if c1 > o1 and c0 < o0:  # first bullish, second bearish
            if o0 > c1 and c0 < o1:
                patterns.append('bearish_engulfing')

        # Doji after trend (doji star)
        prev_body = abs(c1 - o1)
        range1 = highs[1] - lows[1]
        if range1 > 0 and prev_body / range1 < 0.15:
            if c0 > o0:
                patterns.append('morning_star')
            else:
                patterns.append('evening_star')

    # ── Trend-based inference ──────────────────────────────────────────────────
    # Higher highs / higher lows
    if h2 < h1 < h0:
        patterns.append('higher_highs')
    if l2 < l1 < l0:
        patterns.append('higher_lows')

    if h2 > h1 > h0:
        patterns.append('lower_highs')
    if l2 > l1 > l0:
        patterns.append('lower_lows')

    # Three consecutive up/down candles
    if c2 > o2 and c1 > o1 and c0 > o0:
        patterns.append('three_white_soldiers')
    if c2 < o2 and c1 < o1 and c0 < o0:
        patterns.append('three_black_crows')

    # Close near high/low of candle
    for i in range(3):
        range_ = highs[i] - lows[i]
        if range_ > 0:
            close_pos = (closes[i] - lows[i]) / range_
            if close_pos > 0.9:
                patterns.append('close_near_high')
            elif close_pos < 0.1:
                patterns.append('close_near_low')

    return list(set(patterns))


def detect_support_resistance(closes, highs, lows, lookback=20):
    """Very simple: recent swing highs/lows."""
    return []  # placeholder for now


def pattern_summary(patterns):
    """Convert pattern list to readable text."""
    if not patterns:
        return 'no_clear_pattern'

    bullish = ['hammer', 'bullish_engulfing', 'morning_star', 'higher_lows',
               'higher_highs', 'three_white_soldiers', 'close_near_low']
    bearish  = ['shooting_star', 'bearish_engulfing', 'evening_star', 'lower_highs',
               'lower_lows', 'three_black_crows', 'close_near_high', 'doji']

    b_count = sum(1 for p in patterns if p in bullish)
    be_count = sum(1 for p in patterns if p in bearish)

    bias = 'bullish' if b_count > be_count else 'bearish' if be_count > b_count else 'mixed'
    top = ', '.join(patterns[:5])  # limit length
    return f'{bias} bias ({b_count}B/{be_count}Be): {top}'


def rsi_proxy(closes):
    """Simple RSI-like from recent momentum."""
    if len(closes) < 15:
        return 50, 'neutral'
    gains, losses = 0, 0
    for i in range(-14, 0):
        diff = closes[i+1] - closes[i]
        if diff > 0:
            gains += diff
        else:
            losses += abs(diff)
    avg_gain = gains / 14
    avg_loss = losses / 14
    if avg_loss == 0:
        return 70, 'overbought'
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    cat = 'overbought' if rsi > 70 else 'oversold' if rsi < 30 else 'neutral'
    return rsi, cat


# ── Prompt builders ───────────────────────────────────────────────────────────

def build_minimal_prompt(trend, rsi_cat):
    return f"BTC: trend={trend}, RSI={rsi_cat}. Reply ONLY UP or DOWN:\n\nDIRECTION:"

def build_pattern_prompt(trend, rsi_cat, patterns, prev3):
    pattern_txt = pattern_summary(patterns)
    return (
        f"BTC chart: trend={trend}, RSI={rsi_cat}, "
        f"recent_candles=[{prev3}], patterns={pattern_txt}. "
        f"Reply ONLY UP or DOWN:\n\nDIRECTION:"
    )


# ── Load test data ────────────────────────────────────────────────────────────

DB_PRED = '/root/.hermes/data/predictions.db'
DB_PRICE = '/root/.hermes/data/signals_hermes.db'

conn = sqlite3.connect(DB_PRED, timeout=10)
cur = conn.cursor()
cur.execute('''
    SELECT token, direction, regime
    FROM predictions
    WHERE correct IS NOT NULL
      AND direction IS NOT NULL
      AND price_at_prediction IS NOT NULL
    ORDER BY RANDOM()
    LIMIT %d
''' % int(sys.argv[1]) if len(sys.argv) > 1 else 30)
candles = cur.fetchall()
conn.close()

# Deduplicate tokens, get price data
conn2 = sqlite3.connect(DB_PRICE, timeout=10)
cur2 = conn2.cursor()

token_data = {}
for token, *_ in set(candles):
    cur2.execute('''
        SELECT price, timestamp FROM price_history
        WHERE token=? ORDER BY timestamp DESC LIMIT 25
    ''', (token,))
    rows = cur2.fetchall()
    if len(rows) >= 6:
        # oldest first
        rows = rows[::-1]
        prices = [r[0] for r in rows]
        # Estimate OHLC from closes (we only have price, not true O/H/L)
        # Use price +/- small variance as proxy
        token_data[token] = prices

conn2.close()
print(f'Loaded {len(token_data)} tokens, testing {len(candles)} candles')


# ── Run backtest ──────────────────────────────────────────────────────────────

variants = {
    'A_minimal':    build_minimal_prompt,
    'B_patterns':    build_pattern_prompt,
}

results = {name: {'hits': 0, 'total': 0, 'errors': 0} for name in variants}

for token, direction, regime in candles:
    if token not in token_data:
        continue
    prices = token_data[token]
    if len(prices) < 6:
        continue

    # Proxy OHLC from prices (we only have close; use adjacent as proxy)
    closes = prices
    # Very rough: open = previous close, high = max(close, next), low = min(close, next)
    opens  = [closes[0]] + closes[:-1]
    highs  = [max(closes[i], closes[i+1]) if i+1 < len(closes) else closes[i] for i in range(len(closes))]
    lows   = [min(closes[i], closes[i+1]) if i+1 < len(closes) else closes[i] for i in range(len(closes))]
    highs[-1] = closes[-1] + (closes[-1] * 0.002)  # slight bump for last
    lows[-1]  = closes[-1] - (closes[-1] * 0.002)

    # Indicators
    trend = 'UP' if closes[-1] > closes[-5] else 'DOWN' if closes[-1] < closes[-5] else 'FLAT'
    prev3 = ','.join(['UP' if closes[i] > opens[i] else 'DOWN' for i in range(-4, -1)])
    rsi_val, rsi_cat = rsi_proxy(closes)
    patterns = candle_pattern(closes[-3:], opens[-3:], highs[-3:], lows[-3:])

    for name, builder in variants.items():
        if name == 'A_minimal':
            prompt = builder(trend, rsi_cat)
        else:
            prompt = builder(trend, rsi_cat, patterns, prev3)

        try:
            resp = call_ollama(prompt)
            predicted = 'UP' if 'UP' in resp.upper() else 'DOWN'
            hit = int(predicted == direction)
            results[name]['hits'] += hit
            results[name]['total'] += 1
            print(f'  {token}: {direction}→{predicted} ({hit}) [{name}]')
        except Exception as e:
            results[name]['errors'] += 1
            print(f'  ERROR {token} [{name}]: {e}')
            continue

        time.sleep(0.6)

print('\n=== RESULTS ===')
for name, r in sorted(results.items(), key=lambda x: -x[1]['hits'] / max(x[1]['total'], 1)):
    acc = r['hits'] / r['total'] * 100 if r['total'] > 0 else 0
    print(f'{name}: {r["hits"]}/{r["total"]} = {acc:.1f}%  (errors={r["errors"]})')