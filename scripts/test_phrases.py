#!/usr/bin/env python3
import requests, sys

OLLAMA_URL = 'http://127.0.0.1:11434/api/generate'

tests = [
    ('BTC: RSI=70 (overbought), MACD=-200 (bearish), Z=+2.1 (elevated). Next 4h direction?',),
    ('BTC: RSI=28 (oversold), MACD=+150 (bullish), Z=-2.0 (suppressed). Next 4h direction?',),
    ('BTC: RSI=50, MACD=-50, Z=+0.2. Next 4h direction?',),
    ('BTC: RSI=60, MACD=+100, Z=-1.0. Next 4h direction?',),
]
for args in tests:
    prompt = args[0]
    r = requests.post(OLLAMA_URL, json={
        'model': 'qwen2.5:1.5b', 'prompt': prompt, 'stream': False,
        'options': {'temperature': 0.3, 'num_predict': 200}
    }, timeout=30)
    print(f'Q: {prompt}')
    print(f'A: {r.json().get("response","")}')
    print()
sys.stdout.flush()
