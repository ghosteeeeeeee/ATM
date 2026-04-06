---
name: prompt-training
description: Systematic LLM prompt backtesting for financial candle direction prediction — test variants against historical candles, measure accuracy, iterate. Built from qwen2.5:1.5b experiments (2026-04-06), ported to Minimax for production use.
created: 2026-04-06
tags: [candle-prediction, llm, backtesting, trading, minimax]
---

# prompt-training — LLM Prompt Backtesting for Financial Direction Prediction

## What It Does
Systematic prompt variant testing against historical candles to find what actually works vs what looks good in theory. Built from qwen2.5:1.5b backtesting (2026-04-06), now ported to Minimax.

## When to Use
- New prompt idea for candle direction prediction
- Changed indicators or model
- After any significant market structure change (new regime)
- Before deploying any prompt to live production

## The Methodology

### Step 1: Gather Test Candles
```python
import sqlite3

DB = '/root/.hermes/data/signals_hermes.db'
conn = sqlite3.connect(DB, timeout=10)
cur = conn.cursor()

# Get 20-30 balanced candles (mix of up/down, different regimes)
cur.execute('''
    SELECT token, direction, regime, momentum_state,
           CAST(predicted_move_pct AS REAL) as move,
           CAST(actual_move_pct AS REAL) as actual
    FROM predictions
    WHERE correct IS NOT NULL
      AND direction IS NOT NULL
      AND predicted_move_pct IS NOT NULL
    ORDER BY RANDOM()
    LIMIT 40
''')
candles = cur.fetchall()
conn.close()
```

### Step 2: Define Prompt Variants
Test no more than 3-5 variants at once. Each variant should test ONE hypothesis.

```python
variants = {
    'minimal':      'BTC: trend={trend}, RSI={rsi_cat}. Reply ONLY UP or DOWN:\n\nDIRECTION:',
    'with_z':       'BTC: trend={trend}, RSI={rsi_cat}, Z={z_cat}. Reply ONLY UP or DOWN:\n\nDIRECTION:',
    'with_regime':  'BTC: trend={trend}, RSI={rsi_cat}, regime={regime}. Reply ONLY UP or DOWN:\n\nDIRECTION:',
    'full_context': 'BTC: trend={trend}, RSI={rsi_cat}, Z={z_cat}, prev3=[{prev3}], regime={regime}, momentum={momentum}. Reply ONLY UP or DOWN:\n\nDIRECTION:',
}
```

### Step 3: Run Backtest
```python
import requests

MINIMAX_API = 'https://api.minimax.chat/v1/text/chatcompletion_v2'
MINIMAX_MODEL = 'MiniMax-Text-01'

def test_variant(variant_name, prompt_template, candles, api_key):
    hits, total = 0, 0
    results = []

    for token, direction, regime, momentum, predicted_pct, actual_pct in candles:
        # Build context for this candle
        if len(price_history) < 5:
            continue

        # Compute indicators
        trend = 'UP' if price_history[-1] > price_history[-5] else 'DOWN'
        prev3 = ','.join(['UP' if price_history[i] > price_history[i-1] else 'DOWN'
                          for i in range(-4, -1)])
        rsi_cat = 'overbought' if rsi > 65 else 'oversold' if rsi < 35 else 'neutral'
        z_cat = 'elevated' if z > 1.5 else 'suppressed' if z < -1.5 else 'normal'

        prompt = prompt_template.format(
            trend=trend, rsi_cat=rsi_cat, z_cat=z_cat,
            prev3=prev3, regime=regime, momentum=momentum
        )

        # Call Minimax
        resp = requests.post(MINIMAX_API, headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }, json={
            'model': MINIMAX_MODEL,
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': 20,
            'temperature': 0.3,
        }, timeout=15)

        result = resp.json()['choices'][0]['message']['content'].strip().upper()
        predicted = 'UP' if 'UP' in result else 'DOWN'

        is_correct = (predicted == direction)
        hits += int(is_correct)
        total += 1
        results.append({'token': token, 'predicted': predicted, 'actual': direction, 'correct': is_correct})

    accuracy = hits / total * 100 if total > 0 else 0
    return {'variant': variant_name, 'accuracy': accuracy, 'hits': hits, 'total': total}
```

### Step 4: Analyze and Iterate
Compare accuracies. Rule of thumb:
- **>55%**: promising — run more candles (50+)
- **50-55%**: marginal — may be random noise
- **<50%**: worse than random — discard or invert
- **Adding anything**: usually hurts on small models

---

## Key Findings from Qwen Backtest (qwen2.5:1.5b)

**These findings are MODEL-SPECIFIC — do NOT assume they transfer to Minimax.**

| Hypothesis | Result on Qwen | Action |
|-----------|----------------|--------|
| RSI numeric (RSI=55.3) | Garbage — model treats as arbitrary token | Use only categories |
| Z-score numeric | Garbage — model doesn't compute | Use only categories |
| MACD in prompt | HURTS → 35% | Skip |
| 5-shot examples | HURTS | Skip |
| W&B accuracy stats in prompt | HURTS | Skip |
| Regime (bearish/bullish) | FLIPS predictions even when trend=UP | Keep — strong signal |
| Prev 3 candles | Strong micro-momentum signal | Keep |
| Trend (5-candle) | Baseline signal | Keep |
| Full context (regime+momentum+prev3) | Best overall (55%) | Use as starting point for Minimax |

---

## Minimax Findings (2026-04-06)

**Critical issue**: MiniMax-M2 has safety policy blocking financial predictions.

| Prompt | Result | Reason |
|--------|--------|--------|
| `BTC: trend=UP, RSI=neutral` | REFUSAL | Up prediction = financial advice |
| `BTC: trend=DOWN, RSI=overbought` | DOWN (complies) | Downward predictions acceptable |
| `BTC: trend=UP, RSI=overbought` | DOWN (complies) | Overbought bearish context works |
| `BTC: trend=DOWN, RSI=oversold` | TRUNCATED | Contradictory signals → model keeps reasoning |

**Key insight**: MiniMax-M2 blocks upward predictions more than downward ones — safety asymmetry.

**Working around it** (not fully tested):
- Completion endpoint instead of chat completions (might bypass safety)
- Frame as: "I have data. Predict. Say UP or DOWN" — but likely same issue
- Ask for "analysis then decision" (two-step — might slip past filter)
- Use function-calling / tool use (might bypass content filter)

**Backtest results on 15 candles**:
- text_only: 3/15 = 20% (very poor)
- numeric: 1/15 = 7% (worse than random)
- Full backtest timed out — content filter making it unreliable

**Conclusion**: MiniMax is NOT suitable as direct candle predictor due to safety policy.
Use qwen for predictions. Use MiniMax only for:
1. **Post-prediction validation** (ask: "is this prediction reasonable?" without asking for direction)
2. **Explanation generation** (explain WHY a prediction was made)
3. **Hot-set compaction** (already working, different task)

---

## Qwen vs Minimax Role Split
- **qwen2.5:1.5b**: All prediction work (fast, local, no safety blocks)
- **MiniMax-M2**: Validation, explanation, analysis (NOT direction prediction)