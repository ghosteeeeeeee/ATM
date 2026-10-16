---
name: full-analysis
description: Use when you need a complete trading analysis combining MTF, technical, contrarian, continuum, S/R, Bollinger Bands, and EMA200. The master analysis skill. Triggers on "full analysis", "complete analysis", "what's the call", "analyze everything", "run all analysis".
---

# Full Analysis Skill

The master analysis framework combining all sub-skills into one comprehensive output. Run this before every trade decision.

## Components

This skill combines:
- **mtf-analysis** — Multi-timeframe analysis (1m/5m/15m/1h/4h)
- **technical-analysis** — RSI, MACD, EMAs, volume, patterns
- **contrarian-analysis** — "What if I'm wrong?" checklist
- **Continuum oscillator** — Macro regime
- **Support/Resistance** — Key levels
- **Bollinger Bands** — BB position (0=lower band, 1=upper band)
- **EMA200** — Long-term dynamic support/resistance
- **Volume ratio** — Per-timeframe volume confirmation

## Key Indicators

### Bollinger Band Position
```
BB Position = (Price - Lower Band) / (Upper Band - Lower Band)
```
- **0.0-0.2** = Near lower band (oversold, bounce zone)
- **0.2-0.4** = Lower half (pullback zone)
- **0.4-0.6** = Middle (neutral)
- **0.6-0.8** = Upper half (rally zone)
- **0.8-1.0** = Near upper band (overbought, rejection zone)
- **>1.0** = Above upper band (extreme, imminent pullback)

### EMA200
- Price ABOVE EMA200 = long-term bullish
- Price BELOW EMA200 = long-term bearish
- EMA200 acts as dynamic support/resistance
- Bounce off EMA200 = key entry signal

### Volume Ratio
- **>1.5x** = Surge (real move, confirmed)
- **0.8-1.5x** = Normal (uncertain)
- **<0.8x** = Low (weak move, likely fakeout)

### Z-Score (20-bar)
```
Z = (Price - 20-bar Mean) / 20-bar StdDev
```
- **>2.0** = EXTREME_HIGH (overbought, reversal imminent)
- **1.0-2.0** = HIGH (overbought, approaching reversal)
- **-1.0 to 1.0** = NEUTRAL (normal range)
- **-2.0 to -1.0** = LOW (oversold, bounce zone)
- **<-2.0** = EXTREME_LOW (oversold, reversal imminent)

**MTF Z-Score alignment:**
- All TFs same sign = strong trend
- Lower TFs HIGH, higher TFs LOW = bounce in downtrend
- Lower TFs LOW, higher TFs HIGH = dip in uptrend

## Analysis Script

Run this to get the complete picture:
```bash
python3 -c "
import sys; sys.path.insert(0, '/root/.hermes/scripts')
import sqlite3, json

def ema(data, period):
    k = 2 / (period + 1)
    e = [data[0]]
    for i in range(1, len(data)):
        e.append(data[i] * k + e[-1] * (1 - k))
    return e

def analyze_tf(token, table):
    conn = sqlite3.connect('/root/.hermes/data/candles.db')
    cur = conn.cursor()
    cur.execute(f'SELECT high, low, close, volume FROM candles_{table} WHERE token=\"{token}\" AND is_closed=1 ORDER BY ts DESC LIMIT 200')
    rows = [r for r in cur.fetchall()][::-1]
    conn.close()
    if len(rows) < 50: return None
    closes = [r[2] for r in rows]
    ema50 = ema(closes, 50)
    ema100 = ema(closes, 100) if len(closes) >= 100 else ema(closes, len(closes))
    ema8 = ema(closes, 8)
    macd_line = [e8 - e50 for e8, e50 in zip(ema8, ema50)]
    signal_line = ema(macd_line, 12)
    histogram = [m - s for m, s in zip(macd_line, signal_line)]
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        gains.append(max(0, diff))
        losses.append(max(0, -diff))
    ag = sum(gains[-14:]) / 14
    al = sum(losses[-14:]) / 14
    rs = ag / al if al > 0 else 100
    rsi = 100 - (100 / (1 + rs))
    crossover = ''
    if len(macd_line) >= 2:
        if macd_line[-2] < signal_line[-2] and macd_line[-1] > signal_line[-1]: crossover = ' BULL XO'
        elif macd_line[-2] > signal_line[-2] and macd_line[-1] < signal_line[-1]: crossover = ' BEAR XO'
    return {'rsi': rsi, 'macd_above': macd_line[-1] > signal_line[-1], 'hist': histogram[-1], 'xo': crossover, 'price': closes[-1]}

# MTF
print('📊 MTF:')
for tf in ['1m', '5m', '15m', '1h', '4h']:
    r = analyze_tf('BTC', tf)
    if r:
        bb = '🟢B' if r['macd_above'] else '🔴B'
        print(f'  {tf:4s} RSI={r[\"rsi\"]:5.1f} {bb} hist={r[\"hist\"]:+.0f}{r[\"xo\"]}')

# Continuum
with open('/var/www/hermes/data/continuum_data.json') as f:
    d = json.load(f)
c = d.get('current', {})
print(f'\\n📈 Continuum: EMA300={c.get(\"ema300_position\")} Z={c.get(\"zscore_tier\")} Trend={c.get(\"trend_quality\")} Linreg={c.get(\"linreg_direction\")}')

# S/R
conn = sqlite3.connect('/root/.hermes/data/candles.db')
cur = conn.cursor()
cur.execute('SELECT high, low FROM candles_5m WHERE token=\"BTC\" AND is_closed=1 ORDER BY ts DESC LIMIT 60')
rows = [r for r in cur.fetchall()][::-1]
conn.close()
highs = [r[0] for r in rows]
lows = [r[1] for r in rows]
def find_swings(data, lb=3):
    pts = []
    for i in range(lb, len(data)-lb):
        if data[i] == max(data[i-lb:i+lb+1]):
            pts.append(data[i])
    return pts[-5:]
print(f'\\n📐 R: {\", \".join([f\"{r:.0f}\" for r in find_swings(highs)])}')
print(f'   S: {\", \".join([f\"{s:.0f}\" for s in find_swings(lows)])}')
"
```

## Precheck

After analysis, run the precheck:
```bash
python3 /root/.hermes/scripts/ai_trader_precheck.py COIN DIRECTION
```

## Verdict Rules

| MTF Alignment | Continuum | Verdict |
|---------------|-----------|---------|
| 4-5 bullish | Bullish | **STRONG LONG** |
| 4-5 bearish | Bearish | **STRONG SHORT** |
| 3/5 bullish | Mixed | LONG with caution |
| 3/5 bearish | Mixed | SHORT with caution |
| Mixed | Any | **NO TRADE** |

## Output Template

```
═══════════════════════════════════════════
       FULL ANALYSIS — [COIN]
═══════════════════════════════════════════

📊 1. MULTI-TIMEFRAME
  [TF results]

📈 2. CONTINUUM
  [continuum data]

📐 3. SUPPORT/RESISTANCE
  [key levels]

🔄 4. CONTRARIAN CHECK
  [contrarian analysis]

🎯 5. VERDICT
  [LONG/SHORT/NO TRADE + reasoning]

═══════════════════════════════════════════
```

## Date
Created 2026-10-16 combining all analysis skills.
