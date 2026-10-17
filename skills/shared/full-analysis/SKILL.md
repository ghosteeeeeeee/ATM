---
name: full-analysis
description: Use when you need a complete trading analysis combining MTF, technical, contrarian, continuum, S/R, Bollinger Bands, and EMA200. The master analysis skill. Triggers on "full analysis", "complete analysis", "what's the call", "analyze everything", "run all analysis".
---

# Full Analysis Skill

The master analysis framework combining all sub-skills into one comprehensive output. Run this before every trade decision.

## Components

This skill combines:
- **Position check** — Current open/closed positions, exit reasons, PnL
- **mtf-analysis** — Multi-timeframe analysis (1m/5m/15m/1h/4h)
- **technical-analysis** — RSI, MACD, EMAs, volume, patterns
- **contrarian-analysis** — "What if I'm wrong?" checklist
- **Continuum oscillator** — Macro regime
- **Support/Resistance** — Key levels
- **Bollinger Bands** — BB position (0=lower band, 1=upper band)
- **EMA200** — Long-term dynamic support/resistance
- **Volume ratio** — Per-timeframe volume confirmation

## Step 0: Current Position Check (MANDATORY)

**Always check current positions before any analysis.** This tells you:
- What's open right now (direction, entry, SL, TP, unrealized PnL)
- What just closed and why (exit reason reveals system behavior)
- Whether you're already exposed to this coin/direction
- Whether exit management is working correctly

```bash
python3 -c "
import sys; sys.path.insert(0, '/root/.hermes/scripts')
import psycopg2
from _secrets import BRAIN_PASSWORD, BRAIN_HOST
conn = psycopg2.connect(host=BRAIN_HOST, dbname='brain', user='postgres', password=BRAIN_PASSWORD, connect_timeout=5)
cur = conn.cursor()
# Open positions
cur.execute('''SELECT id, token, direction, entry_price, current_price, stop_loss, target, pnl_pct, signal, leverage, amount_usdt 
FROM trades WHERE status='open' ORDER BY open_time DESC''')
open_trades = cur.fetchall()
print('=== OPEN POSITIONS ===')
for t in open_trades:
    print(f'#{t[0]} {t[1]} {t[2]} entry={t[3]} px={t[4]} SL={t[5]} TP={t[6]} pnl={t[7]}% sig={t[8]} lev={t[9]}x size={t[10]}')
# Recent closed (last 10)
cur.execute('''SELECT id, token, direction, entry_price, exit_price, pnl_pct, exit_reason, signal, close_time 
FROM trades WHERE status='closed' ORDER BY close_time DESC LIMIT 10''')
closed = cur.fetchall()
print('\\n=== RECENT CLOSED ===')
for t in closed:
    print(f'#{t[0]} {t[1]} {t[2]} entry={t[3]} exit={t[4]} pnl={t[5]}% reason={t[6]} sig={t[7]} closed={t[8]}')
cur.close(); conn.close()
"
```

**Key questions to answer:**
1. Is there an open position on this coin? If yes, are you adding to it or flipping?
2. What exit reason killed the last trade on this coin? (`atr_trail_hit` = trailing worked; `hard_max_loss` = stop hit; `atr_sl_hit` = ATR stop hit)
3. Is the exit management (RR engine, trailing) actually firing for this signal type?
4. Are you already on the right side or the wrong side?

**Exit reason interpretation:**
- `atr_trail_hit` — Trailing stop took profit (winner trailed out)
- `atr_sl_hit` — ATR stop loss hit (loser)
- `hard_max_loss` — Hard max loss cap hit (loser)
- `rr_engine_*` — RR engine managed exit (structural support/resistance)
- `HL_CLOSED` — Closed on Hyperliquid directly
- `trail_sl` — Trailing stop loss hit

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

### Z-Score (Multi-Window)
```
Z = (Price - N-bar Mean) / N-bar StdDev
```

**Standard windows:**
- **20-bar** — Short-term (quick signals, noisy)
- **50-bar** — Medium-term (balanced)
- **100-bar** — Longer-term (trend confirmation)
- **200-bar** — Long-term (macro view)

**Z-Score tiers:**
- **>2.0** = EXTREME_HIGH (overbought, reversal imminent)
- **1.0-2.0** = HIGH (overbought, approaching reversal)
- **-1.0 to 1.0** = NEUTRAL (normal range)
- **-2.0 to -1.0** = LOW (oversold, bounce zone)
- **<-2.0** = EXTREME_LOW (oversold, reversal imminent)

**Multi-window interpretation:**
- 20-bar NEUTRAL + 50-200 bar HIGH = short-term dip in extended uptrend
- 20-bar NEUTRAL + 50-200 bar LOW = short-term bounce in extended downtrend
- All windows same sign = strong trend
- Divergence between windows = trend exhaustion

**MTF Z-Score alignment:**
- All TFs same sign = strong trend
- Lower TFs HIGH, higher TFs LOW = bounce in downtrend
- Lower TFs LOW, higher TFs HIGH = dip in uptrend

### MTF Volume Analysis

Volume confirmation across timeframes tells you if a move is real:

**Per-TF volume ratio** (current vs 20-bar average):
- **>1.5x** = 🔥 Surge (strong conviction)
- **0.8-1.5x** = 🟢 Normal (healthy)
- **<0.8x** = 🔴 Low (weak, likely fakeout)

**MTF volume patterns:**

| Pattern | 1m | 5m | 15m | Meaning |
|---------|----|----|-----|---------|
| **Real breakout** | 🔥 | 🔥 | 🟢 | Strong move, institutional buying |
| **Fakeout** | 🔥 | 🔴 | 🔴 | Only 1m spike = noise, not conviction |
| **Exhaustion** | 🔴 | 🟢 | 🟢 | Move happened, now fading |
| **Accumulation** | 🟢 | 🟢 | 🔴 | Quiet building before move |

**Key rules:**
- **1m volume alone = noise.** Need 5m+ confirmation.
- **5m surge + 15m surge = real move.** Institutional interest.
- **Volume on crossover:** MACD crossover WITH volume = real. Without = fake.
- **Volume divergence:** Price higher but volume declining = weak rally, reversal coming.

### MTF MACD Analysis

MACD alignment across timeframes shows trend strength:

**Per-TF MACD status:**
- **Bullish** = MACD line above signal line
- **Bearish** = MACD line below signal line
- **Crossover** = momentum shift (BULL XO or BEAR XO)
- **Histogram** = distance between MACD and signal (rising = momentum building, falling = fading)

**MTF MACD patterns:**

| Pattern | 1m | 5m | 15m | 1h | Meaning |
|---------|----|----|-----|----|---------|
| **Full bull** | 🟢 | 🟢 | 🟢 | 🟢 | Strong uptrend, ride it |
| **Full bear** | 🔴 | 🔴 | 🔴 | 🔴 | Strong downtrend, ride it |
| **Bull forming** | 🟢 | 🟢 | 🔴 | 🔴 | Bottom-up, early long |
| **Bear forming** | 🔴 | 🔴 | 🟢 | 🟢 | Top-down, early short |
| **Mixed** | Mixed | Mixed | Mixed | Mixed | Chop, no edge |

**Key rules:**
- **1m/5m lead, 15m/1h confirm.** If lower TFs cross bullish but higher TFs bearish, it's a bounce not a trend.
- **Histogram divergence:** Price makes higher high but histogram makes lower high = bearish divergence (and vice versa).
- **Crossover timing:** Enter on 5m crossover, not 1m (1m is noise).
- **Cascading crossovers:** 1m → 5m → 15m → 1h = strongest signal (momentum building through TFs).
- **Histogram slope:** Rising histogram = momentum building. Falling = fading. Flat = consolidation.

**MACD + Volume confirmation:**
- MACD crossover + volume surge = **real move**
- MACD crossover + low volume = **fake move, likely fails**
- MACD bearish + volume surge = **real selloff**
- MACD bullish + volume surge = **real rally**

### Probability of Trade Succeeding

Score each factor, sum them, and convert to a probability:

**Scoring System (0-100 points):**

| Factor | Bullish | Bearish | Points |
|--------|---------|---------|--------|
| **1h MACD** | BULL | BEAR | +15 / -15 |
| **15m MACD** | BULL | BEAR | +10 / -10 |
| **5m MACD** | BULL | BEAR | +10 / -10 |
| **RSI position** | 45-60 sweet spot | <30 or >70 | +10 / -10 |
| **Volume** | >1.5x surge | <0.5x dead | +10 / -10 |
| **Continuum** | ABOVE + BULL linreg | BELOW + BEAR linreg | +15 / -15 |
| **Z-Score (5m)** | NEUTRAL (-1 to 1) | EXTREME (±>2) | +5 / -10 |
| **Trend alignment** | Price above EMA50 | Price below EMA50 | +5 / -5 |
| **Pattern** | Continuation (flag) | Reversal against you | +5 / -5 |
| **Contrarian** | Contrarian view weaker | Contrarian view stronger | +5 / -5 |

**Probability Conversion:**

| Score | Probability | Action |
|-------|-------------|--------|
| **+50 to +100** | 70-90% | **STRONG ENTRY** — full size |
| **+20 to +49** | 55-70% | **GOOD ENTRY** — normal size |
| **0 to +19** | 45-55% | **MARGINAL** — small size or skip |
| **-19 to -1** | 35-45% | **AVOID** — counter-trend |
| **-50 to -20** | 10-35% | **STRONG AVOID** — wrong side |

**Example: BTC LONG scoring:**
```
1h MACD:    BEAR  = -15
15m MACD:   BULL  = +10
5m MACD:    BEAR  = -10
RSI:        46.6  = +10 (sweet spot)
Volume:     0.2x  = -10 (dead)
Continuum:  BELOW = -15
Z-Score:    NEUTRAL = +5
EMA50:      Below = -5
Pattern:    None  = 0
Contrarian: Neutral = 0
            ─────────
Total:      -30 points → 25% probability → STRONG AVOID
```

**Key rules:**
- **Higher TFs matter more** (1h = 15 points vs 5m = 10 points)
- **Volume is critical** — no volume = no conviction
- **Continuum is the macro context** — don't fight it
- **Score < 0 = wrong side of the trade** — skip or size down
- **Score > 50 = high conviction** — normal or increased size

**This is a heuristic, not a guarantee.** Use it as one input among many.

### Trendlines

Trendlines connect swing points to show trend direction and dynamic support/resistance:

**How to draw:**
- **Uptrend line:** Connect 2+ rising swing lows (support)
- **Downtrend line:** Connect 2+ falling swing highs (resistance)
- **More touches = stronger trendline** (3+ touches = significant)
- **Steeper trendline = more fragile** (breaks easily on pullback)
- **Shallower trendline = more robust** (survives volatility)

**Breakout/breakdown signals:**
- Price breaks ABOVE downtrend line = **bullish signal**
- Price breaks BELOW uptrend line = **bearish signal**
- Wait for candle CLOSE beyond trendline (not just wick)
- **Volume confirmation** — breakout with volume = real, without = fake

**Trendline + EMA confluence:**
- Trendline and EMA200 at same level = **strong support/resistance**
- Bounce off both = high-probability entry
- Break through both = strong reversal signal

### Chart Patterns

**Continuation Patterns:**

| Pattern | Structure | Entry | Target |
|---------|-----------|-------|--------|
| **Bull Flag** | Sharp rally (pole) + tight consolidation (flag) | Break above flag high | Pole height projected up |
| **Bear Flag** | Sharp decline (pole) + tight consolidation (flag) | Break below flag low | Pole height projected down |
| **Bull Pennant** | Rally + converging triangle consolidation | Break above pennant | Pole height projected up |
| **Ascending Triangle** | Flat resistance + rising lows | Break above resistance | Triangle height projected up |
| **Descending Triangle** | Flat support + falling highs | Break below support | Triangle height projected down |

**Reversal Patterns:**

| Pattern | Structure | Signal |
|---------|-----------|--------|
| **Double Bottom** | Two troughs at similar price | Bullish — enter long on break above neckline |
| **Double Top** | Two peaks at similar price | Bearish — enter short on break below neckline |
| **Head & Shoulders** | Peak with two lower shoulders | Bearish — enter short on break below neckline |
| **Inverse H&S** | Trough with two higher shoulders | Bullish — enter long on break above neckline |
| **Rounding Bottom** | Gradual shift from down to up | Bullish — enter on breakout |

**Fakeout Patterns:**

| Pattern | Structure | Signal |
|---------|-----------|--------|
| **Bull Trap** | Breaks above resistance then dumps | Bearish — exit longs, consider short |
| **Bear Trap** | Breaks below support then pumps | Bullish — exit shorts, consider long |
| **Stop Hunt** | Quick spike through S/R to trigger stops | Reversal likely — wait for direction |

**Pattern Detection Rules:**
- **Flag ratio:** Flag consolidation should be <50% of pole height
- **Volume:** Patterns need declining volume during consolidation, increasing on breakout
- **Timeframe:** 5m+ patterns are more reliable than 1m
- **Confluence:** Pattern + EMA + S/R = strongest signals

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

📋 0. CURRENT POSITIONS
  Open: [list open positions on this coin + status]
  Recent closed: [last trade exit reason + PnL]
  [If open: "Currently LONG/SHORT at X, SL at Y, unrealized Z%"]
  [If just closed: "Last trade closed by [reason] at [PnL]%"]

📊 1. MULTI-TIMEFRAME
  [TF results]

📈 2. CONTINUUM
  [continuum data]

📐 3. SUPPORT/RESISTANCE
  [key levels]

🔄 4. CONTRARIAN CHECK
  [contrarian analysis]

🎯 5. VERDICT
  [LONG/SHORT/NO TRADE + reasoning + probability score]

═══════════════════════════════════════════
```

## Date
Created 2026-10-16 combining all analysis skills.
