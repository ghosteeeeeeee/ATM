#!/usr/bin/env python3
"""Minimax candle predictor backtest — compare prompt variants."""

import json, requests, sqlite3, time, re, sys

API_KEY = None
with open('/root/.hermes/auth.json') as f:
    auth = json.load(f)
    API_KEY = auth['credential_pool']['minimax'][0]['access_token']

API_URL = 'https://api.minimax.io/v1/chat/completions'

def call_minimax(prompt):
    resp = requests.post(API_URL, headers={
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json'
    }, json={
        'model': 'MiniMax-M2',
        'messages': [{'role': 'user', 'content': prompt}],
        'max_tokens': 500,
        'temperature': 0.3,
    }, timeout=30)
    data = resp.json()
    return data['choices'][0]['message']['content']

def parse_response(raw):
    clean = re.sub(r'.*?\n\n', '', raw, count=1, flags=re.DOTALL).strip()
    clean = clean.upper()
    if 'UP' in clean and 'DOWN' not in clean:
        return 'UP'
    elif 'DOWN' in clean and 'UP' not in clean:
        return 'DOWN'
    elif 'UP' in clean:
        return 'UP'
    elif 'DOWN' in clean:
        return 'DOWN'
    return '???'

def load_candles(n=30):
    conn = sqlite3.connect('/root/.hermes/data/predictions.db', timeout=10)
    cur = conn.cursor()
    cur.execute('''
        SELECT token, direction, regime,
               predicted_move_pct, actual_move_pct,
               price_at_prediction, momentum_state
        FROM predictions
        WHERE correct IS NOT NULL
          AND direction IS NOT NULL
          AND regime IS NOT NULL
          AND price_at_prediction IS NOT NULL
        ORDER BY RANDOM()
        LIMIT %d''' % n
    )
    candles = [(r[0],r[1],r[2],r[3],r[4],r[5],r[6]) for r in cur.fetchall()]
    conn.close()
    return candles

def load_price_history(tokens):
    conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db', timeout=10)
    cur = conn.cursor()
    data = {}
    for token in tokens:
        cur.execute('''
            SELECT price FROM price_history
            WHERE token=? ORDER BY timestamp DESC LIMIT 6
        ''', (token,))
        rows = [r[0] for r in cur.fetchall()]
        if len(rows) >= 5:
            data[token] = list(reversed(rows))  # oldest->newest
    conn.close()
    return data

def compute_indicators(ph):
    trend = 'UP' if ph[-1] > ph[-5] else 'DOWN' if ph[-1] < ph[-5] else 'FLAT'
    prev3 = ','.join(['UP' if ph[i] > ph[i-1] else 'DOWN' for i in range(-4, -1)])
    recent_changes = [ph[i+1]/ph[i]-1 for i in range(len(ph)-1)]
    avg_change = sum(recent_changes) / len(recent_changes) if recent_changes else 0
    rsi_val = max(20, min(80, 50 + avg_change * 2000))
    rsi_cat = 'overbought' if rsi_val > 65 else 'oversold' if rsi_val < 35 else 'neutral'
    avg_price = sum(ph) / len(ph)
    std_price = (max(ph) - min(ph)) / 4 or 1
    z_val = max(-3, min(3, (ph[-1] - avg_price) / std_price))
    z_cat = 'elevated' if z_val > 1.5 else 'suppressed' if z_val < -1.5 else 'normal'
    return trend, prev3, rsi_val, rsi_cat, z_val, z_cat

VARIANTS = {
    'A_text_minimal':    'BTC: trend={trend}, RSI={rsi_cat}. Reply ONLY UP or DOWN:\n\nDIRECTION:',
    'B_numeric':         'BTC: trend={trend}, RSI={rsi_val:.1f}, Z={z_val:+.1f}. Reply ONLY UP or DOWN:\n\nDIRECTION:',
    'C_full_text':       'BTC: trend={trend}, RSI={rsi_cat}, Z={z_cat}, prev3=[{prev3}], regime={regime}. Reply ONLY UP or DOWN:\n\nDIRECTION:',
    'D_full_numeric':    'BTC: trend={trend}, RSI={rsi_val:.1f}, Z={z_val:+.1f}, prev3=[{prev3}], regime={regime}. Reply ONLY UP or DOWN:\n\nDIRECTION:',
}

def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    candles = load_candles(n)
    tokens = list(set(c[0] for c in candles))
    price_data = load_price_history(tokens)
    print(f'Testing {len(price_data)} tokens across {len(VARIANTS)} variants, {n} candles')

    results = {}
    for name, template in VARIANTS.items():
        hits, total, errors = 0, 0, 0
        for token, direction, regime, *_ in candles:
            if token not in price_data:
                continue
            ph = price_data[token]
            trend, prev3, rsi_val, rsi_cat, z_val, z_cat = compute_indicators(ph)

            prompt = template.format(
                trend=trend, rsi_cat=rsi_cat, z_cat=z_cat,
                rsi_val=rsi_val, z_val=z_val,
                prev3=prev3, regime=regime
            )

            try:
                raw = call_minimax(prompt)
                predicted = parse_response(raw)
                is_correct = predicted == direction
                hits += int(is_correct)
                total += 1
                print(f'  {token}: {direction}→{predicted} ({"hit" if is_correct else "miss"}) [{name}]')
            except Exception as e:
                errors += 1
                print(f'  ERROR {token}: {e}')
                continue

            time.sleep(0.5)

        acc = hits / total * 100 if total > 0 else 0
        results[name] = {'accuracy': acc, 'hits': hits, 'total': total, 'errors': errors}
        print(f'\n>>> {name}: {hits}/{total} = {acc:.1f}% (err={errors})\n')

    print('\n=== RESULTS SUMMARY ===')
    for name, r in sorted(results.items(), key=lambda x: -x[1]['accuracy']):
        print(f'{name}: {r["accuracy"]:.1f}% ({r["hits"]}/{r["total"]})')

if __name__ == '__main__':
    main()