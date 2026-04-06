#!/usr/bin/env python3
"""Backtest candle predictor prompts against historical BTC 4h candles."""
import sqlite3, statistics, requests, time, re, sys, random
from concurrent.futures import ThreadPoolExecutor, as_completed

PRICES_DB = '/root/.hermes/data/signals_hermes.db'
OLLAMA_URL = 'http://127.0.0.1:11434/api/generate'
MODEL = 'qwen2.5:1.5b'
candle_minutes = 240
MAX_TEST_CANDLES = 20
MAX_WORKERS = 2
NUM_PREDICT = 60
LLM_TIMEOUT = 20

# ── Build OHLCV ──────────────────────────────────────────────────────
conn = sqlite3.connect(PRICES_DB, timeout=10)
cur = conn.cursor()
cur.execute("SELECT timestamp, price FROM price_history WHERE token='BTC' ORDER BY timestamp ASC")
rows = cur.fetchall()
conn.close()

candles = {}
for ts, price in rows:
    bucket = int(ts // (candle_minutes * 60)) * (candle_minutes * 60)
    if bucket not in candles:
        candles[bucket] = {'open': price, 'high': price, 'low': price, 'close': price}
    else:
        c = candles[bucket]
        c['high'] = max(c['high'], price)
        c['low'] = min(c['low'], price)
        c['close'] = price

ohlcv = sorted([(v['open'], v['high'], v['low'], v['close'], k) for k, v in candles.items()])
closes = [c[3] for c in ohlcv]
print(f"Total candles: {len(ohlcv)}", flush=True)

# ── Indicators ───────────────────────────────────────────────────────
def compute_rsi(closes, period=14):
    if len(closes) < period + 2:
        return None
    deltas = [closes[i+1] - closes[i] for i in range(len(closes)-1)]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period-1) + gains[i]) / period
        avg_loss = (avg_loss * (period-1) + losses[i]) / period
    if avg_loss == 0:
        return 85.0
    return round(100 - (100 / (1 + avg_gain / avg_loss)), 2)

def compute_macd(closes, fast=12, slow=26, signal=9):
    if len(closes) < slow + signal:
        return None, None, None
    def ema(data, period):
        k = 2 / (period + 1)
        val = sum(data[:period]) / period
        for p in data[period:]:
            val = p * k + val * (1 - k)
        return val
    ef = ema(closes, fast)
    es = ema(closes, slow)
    macd_line = ef - es
    macd_values = []
    for i in range(slow, len(closes)):
        ef_i = ema(closes[max(0, i-fast+1):i+1], fast) if i+1 >= fast else None
        es_i = ema(closes[max(0, i-slow+1):i+1], slow) if i+1 >= slow else None
        if ef_i is not None and es_i is not None:
            macd_values.append(ef_i - es_i)
    if len(macd_values) < signal:
        return round(macd_line, 6), None, None
    signal_line = ema(macd_values[-signal:], signal)
    return round(macd_line, 6), round(signal_line, 6), round(macd_line - signal_line, 6)

def make_features(closes_hist):
    """Features from closes up to T-1, used to predict candle T direction."""
    closes = list(closes_hist)
    if len(closes) < 30:
        return None
    rsi = compute_rsi(closes)
    macd_line, macd_sig, macd_hist = compute_macd(closes)
    recent = closes[-20:]
    avg = statistics.mean(recent)
    std = statistics.stdev(recent) if len(recent) > 1 else 1
    z = (closes[-1] - avg) / std
    chg_4h = (closes[-1] - closes[-2]) / closes[-2] * 100 if len(closes) >= 2 else 0
    # Trend: 5-candle momentum
    trend = 'UP' if closes[-1] > closes[-5] else 'DOWN' if closes[-1] < closes[-5] else 'FLAT'
    # Micro: 3-candle momentum
    micro = 'UP' if closes[-1] > closes[-4] else 'DOWN'
    # Intra-candle range (volatility proxy)
    return {'price': closes[-1], 'rsi': rsi, 'macd_hist': macd_hist, 'z': z,
            'chg_4h': chg_4h, 'trend': trend, 'micro': micro}

def parse_response(text):
    """Extract direction from natural language response — tail-biased with regex."""
    t = text.upper().strip()
    tail = t[-400:] if len(t) > 400 else t

    # 1. Standalone "UP" or "DOWN" as last word (after Reply ONLY:)
    words = tail.split()
    for word in reversed(words):
        if word in ('UP', 'DOWN'):
            return word

    # 2. Explicit "DIRECTION: UP/DOWN"
    for line in tail.split('\n'):
        line = line.strip()
        if 'DIRECTION:' in line.upper():
            parts = line.split('DIRECTION:')[-1].strip().split()
            if parts and parts[0] in ('UP', 'DOWN'):
                return parts[0]

    # 3. "is UP" or "is DOWN" near end
    patterns = [
        r'\bIS\s+(UP|DOWN)\b',
        r'\bBE\s+(UP|DOWN)\b',
    ]
    for pat in patterns:
        m = re.search(pat, tail)
        if m:
            return m.group(1)

    return None

# ── Build test cases ─────────────────────────────────────────────────
# Predict candle i using closes[:i], actual = ohlcv[i] close vs open
start_idx = 35
end_idx = len(ohlcv) - 5
test_cases = []
for i in range(start_idx, end_idx):
    feat = make_features(closes[:i])
    if not feat:
        continue
    actual = 'UP' if ohlcv[i][3] > ohlcv[i][0] else 'DOWN'
    test_cases.append({'idx': i, 'feat': feat, 'actual': actual})

# Sample mix of UP and DOWN
random.seed(42)
up_cases = [c for c in test_cases if c['actual'] == 'UP']
down_cases = [c for c in test_cases if c['actual'] == 'DOWN']
half = MAX_TEST_CANDLES // 2
test_cases = []
test_cases.extend(random.sample(up_cases, min(half, len(up_cases))))
test_cases.extend(random.sample(down_cases, min(MAX_TEST_CANDLES - len(test_cases), len(down_cases))))
test_cases.sort(key=lambda c: c['idx'])

dist = {'UP': sum(1 for c in test_cases if c['actual']=='UP'),
        'DOWN': sum(1 for c in test_cases if c['actual']=='DOWN')}
print(f"Test: {len(test_cases)} | UP={dist['UP']}, DOWN={dist['DOWN']} | "
      f"Total available: UP={len(up_cases)}, DOWN={len(down_cases)}", flush=True)
for c in test_cases:
    f = c['feat']
    rsi_cat = 'OB' if f['rsi'] > 65 else 'OS' if f['rsi'] < 35 else 'N'
    z_cat = 'HIGH' if f['z'] > 1.5 else 'LOW' if f['z'] < -1.5 else 'N'
    macd_dir = '+' if f['macd_hist'] and f['macd_hist'] > 0 else '-'
    print(f"  [{c['idx']}] {f['price']:.0f} RSI={f['rsi']:.0f}({rsi_cat}) Z={f['z']:+.1f}({z_cat}) MACD={macd_dir} tr={f['trend']} → {c['actual']}", flush=True)
print(f"Baseline (random guess 50%): 50.0%\n", flush=True)

# ── Prompts ─────────────────────────────────────────────────────────
PROMPTS = {
    # Best from earlier: no rules, just data
    "p3_all_three": "BTC: trend={trend}, RSI={rsi:.1f} ({rsi_cat}), Z={z:+.1f} ({z_cat}).\nReply ONLY UP or DOWN:",

    # Same + MACD
    "p_all4": "BTC: trend={trend}, RSI={rsi:.1f} ({rsi_cat}), Z={z:+.1f}, MACD={macd_val:+.0f}.\nReply ONLY UP or DOWN:",

    # Shortest possible
    "p_minimal": "BTC tr={trend} RSI={rsi:.0f} Z={z:+.0f}. UP or DOWN? ONLY:",

    # Just RSI + Z (drop trend, see if it's noise)
    "p_rsi_z": "BTC: RSI={rsi:.1f}, Z={z:+.1f}. UP or DOWN? Reply ONLY:",
}

def build_prompt(template, feat):
    rsi_cat = 'overbought' if feat['rsi'] > 65 else 'oversold' if feat['rsi'] < 35 else 'neutral'
    z_cat = 'elevated' if feat['z'] > 1.5 else 'suppressed' if feat['z'] < -1.5 else 'normal'
    macd = 'positive' if feat['macd_hist'] and feat['macd_hist'] > 0 else 'negative'
    return template.format(
        rsi=feat['rsi'], rsi_cat=rsi_cat,
        macd=macd, macd_val=feat['macd_hist'] or 0,
        z=feat['z'], z_cat=z_cat, trend=feat['trend'], chg_4h=feat['chg_4h'],
    )

def worker(args):
    idx, feat, actual, prompt_template = args
    prompt = build_prompt(prompt_template, feat)
    try:
        resp = requests.post(OLLAMA_URL, json={
            'model': MODEL, 'prompt': prompt, 'stream': False,
            'options': {'temperature': 0.3, 'num_predict': NUM_PREDICT}
        }, timeout=LLM_TIMEOUT)
        text = resp.json().get('response', '')
        pred = parse_response(text)
        return {'idx': idx, 'pred': pred, 'actual': actual,
                'correct': pred == actual if pred else None,
                'raw': text[-250:] if text else ''}
    except Exception as e:
        return {'idx': idx, 'pred': None, 'actual': actual, 'correct': None, 'err': str(e)}

def run_backtest(prompt_template):
    results = []
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = [pool.submit(worker, (c['idx'], c['feat'], c['actual'], prompt_template))
                   for c in test_cases]
        for fut in as_completed(futures):
            results.append(fut.result())
    elapsed = time.time() - t0
    results.sort(key=lambda r: r['idx'])
    valid = [r for r in results if r['pred'] is not None]
    if not valid:
        return None, elapsed, results
    total = len(valid)
    correct = sum(1 for r in valid if r['correct'])
    up = [r for r in valid if r['pred'] == 'UP']
    down = [r for r in valid if r['pred'] == 'DOWN']
    up_acc = sum(1 for r in up if r['correct']) / len(up) * 100 if up else 0
    down_acc = sum(1 for r in down if r['correct']) / len(down) * 100 if down else 0
    errs = sum(1 for r in results if r.get('err'))
    return {
        'total': total, 'correct': correct, 'acc': correct/total*100,
        'up_n': len(up), 'up_acc': up_acc,
        'down_n': len(down), 'down_acc': down_acc,
        'errors': errs,
    }, elapsed, results

# ── Run ──────────────────────────────────────────────────────────────
print("=== BACKTEST RESULTS ===", flush=True)
best_name, best_acc = None, 0
best_full = None
for name, tmpl in PROMPTS.items():
    result, elapsed, results = run_backtest(tmpl)
    if result:
        print(f"{name}: {result['correct']}/{result['total']}={result['acc']:.1f}% | "
              f"UP={result['up_acc']:.0f}%({result['up_n']}) DOWN={result['down_acc']:.0f}%({result['down_n']}) | "
              f"errs={result['errors']} | {elapsed:.1f}s", flush=True)
        if result['acc'] >= best_acc:
            best_acc = result['acc']
            best_name = name
            best_full = results
    else:
        print(f"{name}: FAILED", flush=True)

print(f"\n→ Best: {best_name} at {best_acc:.1f}%\n", flush=True)

# ── Detailed predictions for best ───────────────────────────────────
tmpl = PROMPTS[best_name]
print(f"=== DETAILED ({best_name}) ===", flush=True)
for r in best_full:
    c = next(x for x in test_cases if x['idx'] == r['idx'])
    f = c['feat']
    rsi_cat = 'OB' if f['rsi'] > 65 else 'OS' if f['rsi'] < 35 else 'N'
    z_cat = 'HIGH' if f['z'] > 1.5 else 'LOW' if f['z'] < -1.5 else 'N'
    ok = '✓' if r['correct'] else '✗' if r['pred'] else '?'
    print(f"  [{r['idx']}] RSI={f['rsi']:.0f}({rsi_cat}) Z={f['z']:+.1f}({z_cat}) tr={f['trend']} → {r['pred'] or '?'} vs {r['actual']} {ok}", flush=True)
    if r.get('raw'):
        print(f"       {r['raw'][:200].strip().replace(chr(10),' ')}", flush=True)
