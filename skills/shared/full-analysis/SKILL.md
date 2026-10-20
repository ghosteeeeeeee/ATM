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

### ⚠️ Chop-Regime Adjustment (MANDATORY — run before trusting any score)

The trend inputs (1h/15m/5m MACD, Continuum) assume trend persistence. In a
chop regime they LAG the flip — a score computed with stale trend data reads
GOOD on the wrong side. **Lesson: 2026-10-18 trade #16273 SHORT scored +45
GOOD using STRONG_DOWN continuum that flipped BULL the same evening; the
CEOs live-tape read (1m momentum bullish) was right and the score lost
-5.36%.**

**Detect:** count hourly EMA300-position flips in the last 24h from the
continuum history (hourly sampling filters 1m noise):

```bash
cat /var/www/hermes/data/continuum_data.json | python3 -c "
import sys, json, time
d = json.load(sys.stdin)
h = [e for e in d['history'] if e.get('token') == 'BTC']
now = h[-1]['ts']
hours = {}
for e in h:
    if e['ts'] < now - 86400: continue
    hours[time.gmtime(e['ts']).tm_hour] = 'ABOVE' if e['price'] > e['ema300'] else 'BELOW'
states = [hours[k] for k in sorted(hours)]
flips = sum(1 for a, b in zip(states, states[1:]) if a != b)
print(f'24h hourly EMA300 flips: {flips} ({\"CHOP\" if flips >= 2 else \"TREND\"} regime)')
"
```

**Apply:**
- **flips >= 2 (CHOP regime):** halve all trend-input points (1h/15m/5m MACD,
  Continuum — round toward zero), and add the flag **"CHOP REGIME — momentum
  over trend; live-tape reads outrank trend scores"** to the verdict. In chop,
  the score is a sanity check, not a gate: the CEO's momentum/divergence reads
  on the executing timeframe carry more weight than the trend inputs.
- **flips 0-1 (TREND regime):** score as normal.

**Slippage buffer (BTC 10x):** in any BTC trade at 10x, subtract a slippage
buffer (150-250 points) from the R:R risk side before quoting it. #16273's
paper 4.9:1 paid 2.2:1 because a squeeze blew 208 points past the stop
between 1-minute pipeline checks. Quote "planned R:R" and "real R:R (with
slip)" separately.

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

## Decision Protocol: From Reads to Trades

The score is one input. These rules — distilled from the 2026-10-16→19 sessions
(9 manual BTC trades, +$1.18% net after fixing the chop failures) — govern how
a score + tape reads become an actual trade.

### 1. Two calls, not one: DIRECTION and ENTRY are separate decisions

A directional read can be right while the entry loses money. **#16283 (LONG
-1.67%):** the momentum read was right (price did grind higher later) but the
add entered at the top of the push. **#16273 (SHORT -5.36%):** the structural
thesis was textbook — the entry just wasn't. The rule:

- **Direction call:** which side, from score + regime + reads (see trust protocol).
- **Entry call:** WHERE. Never at market on a fresh read. The entry is a LEVEL
  with a tight structural SL — a reclaim, a retest, a base break. If the level
  never comes, there is no trade. Missing is cheaper than wrong.

### 2. Level-break confirmation ≠ trend confirmation

A pending order firing on a level break confirms the BREAK, not the trend that
follows. #16283 fired perfectly on the 82,825 break and still lost — the pull
back through its SL was immediate. So: confirmation entries get the TIGHTEST
structural SL (below the pullback low / base low), not a wide thesis SL. The
first adverse move after a confirmation break is the market voting on the fake.

### 3. Divergence taxonomy — label precisely, three different things get confused

| Type | Price | MACD/RSI | Meaning |
|------|-------|----------|---------|
| **Bullish divergence** | LOWER low | HIGHER low | Real reversal signal — momentum recovered UNDER a falling price (5m 10-19: 81,762/-273 → 81,749/-222 = the base that held) |
| **Momentum recovery** | higher low | higher low | Both rising = straightforward bounce, NOT divergence. Weaker claim. |
| **Bearish divergence** | higher low | LOWER low | The opposite signal — price holding while momentum fades (1h 10-19 read) |

A "divergence" claim that isn't type 1 is something else — name it correctly
before scoring it. Both-higher is recovery; price-up/momentum-down is warning.

### 4. Forming-candle vs closed-bar reads — say which one you're using

The CEO reads forming candles (MACD curling, RSI bouncing mid-bar); closed-bar
analysis lags by up to a full period. Both are legitimate — silently mixing
them is not. When a read depends on the forming candle: label it
**(forming)**, and state the close that would confirm it. "1h MACD curving
toward signal **(forming)** — confirms if the candle closes above X." The
closed-bar skeptic position (histogram still widening) and the forming-candle
position (it's curling now) are the SAME observation at different timestamps.

### 5. Base/bottom playbook — the shape that earns a LONG in markdown

A base forms when: (a) a low is tested twice within ~0.1% (double-tap),
(b) the retest makes a HIGHER low, (c) candle bodies shrink (seller
exhaustion), (d) an oscillator diverges underneath (type-1 from §3). Example
2026-10-19: lows 81,762 → 81,749 (double-tap) → 81,770 (higher low), bodies
shrinking, 5m divergence under it. **The base earns a LONG — but the ENTRY
waits for the reclaim** (price back above the relevant EMA), never the touch.
The touch is where knives live; the reclaim is where the base is proven.
RSI < 30 is bounce FUEL (raises reclaim odds), never a signal by itself —
the knife-catch cluster (0/6) is the cost of forgetting this.

### 6. Two lines for every open trade

Every open position is stated with exactly two lines: **invalidation** (SL —
the thesis is dead here) and **confirmation** (the level that proves the
thesis — prior structure, EMA reclaim, measured target). Every position update
leads with where price sits BETWEEN the two lines. If you can't state both
lines in one sentence, the trade isn't defined — close it or size it down.

### 7. Adding to positions = separate tranche, tighter rules

Adds are NEW trades, not extensions: own SL/own TP/signal tag `ai-trader-pending`
or `ai-trader-manual`. The add's SL is TIGHTER than the original (a round-trip
on the add = the add thesis was wrong, exit; the original tranche keeps its
own wider SL). Never stack TPs at the same level — the add's TP sits BEFORE
the original's (e.g. add TP 82,600 vs system TP 83,687). Chop-regime adds are
half-size or skipped.

### 8. Trust protocol — who outranks whom, by regime

| Regime | Direction authority | Evidence |
|--------|--------------------|--------------------|
| **TREND** (0-1 flips/24h) | The score | Analysis direction went 4/4 in trend phases |
| **CHOP** (2+ flips/24h) | The CEO's live-tape reads | Score went 0/2 in chop; reads caught every flip |
| **Always** | Risk engineering (levels/size/slip) is the analyst's job regardless | #16273's paper 4.9:1 paid 2.2:1 without a slip buffer |

When score and reads disagree: the score sets SIZE (its confidence is real
information), the reads set DIRECTION and TIMING. Never let a negative score
silence a verified read — arm the read as a conditional order with the score's
objections priced into the SL.

### 9. Post-trade attribution — close the loop on every trade

After every manual/armed trade closes, run attribution BEFORE the next
full-analysis: who called the direction (score / CEO read / both / neither),
what regime, entry quality (did price respect the level), outcome, and the
lesson. Track it as a running scorecard — the 4/4 vs 0/2 split was only
visible because each trade was attributed. An unattributed trade teaches
nothing. Append to `brain/trading.md` or the session log.

### 10. Dead-volume discipline

Volume < 0.5x across the executing TFs = no conviction on EITHER side:
scores go negative both ways (correctly), level-breaks fire on thin tape, and
market entries have no edge. In dead volume: (a) bias to conditional orders
over market entries, (b) require the confirmation close WITH volume ≥ 1.2x
for momentum adds, (c) halve size. The #16283 add (0.5x volume at entry) and
the #16273 short (0.0-0.4x) both died of the same missing ingredient.

### 11. BTC chop zigzag — the liquidity-sweep pattern (CEO's thesis, tape-proven)

**BTC's chop signature: it sweeps BOTH sides of the range to collect all the
liquidity — zapping the longs, then the shorts (or reverse) — before the real
move.** CEO stated it directly: "btc loves zigzagging like that and getting
all the liquidity, zapping the longs and then the shorts." The 2026-10-19/20
six-trade sequence is the proof case:

- Range 81,334-82,270. Support swept TWICE (81,735→81,334; 81,550→81,357),
  resistance rejected 3x. Every conditional trigger sat at an OBVIOUS level —
  which means it sat ON a liquidity pool.
- Then the real impulse: +2,105 pts (81,334→83,439) after both sides were
  cleared. Then the reverse zap: -1,146 pts back through every breakout
  long's stop. Result: 4 chop trades = 1 win/3 losses, and both tranches of
  the "confirmed" breakout died (#16306 -1.08%, #16307 40x at -21.4% margin
  on a mere -0.53% price move).

**The rules this earns:**

1. **Obvious levels are liquidity, not structure.** Support/resistance where
   everyone's stops cluster gets SWEPT before the real move. A conditional
   trigger at an obvious level is a resting order waiting to be harvested.
2. **Expect ONE full sweep through each side before committing.** First
   touch/break of a level in chop = probable sweep. After a level has swept
   twice, the third resolution is real — or stand down until a RECLAIM
   (price back through the level and holding), never a touch/break entry.
3. **Break fills pay the sweep tax.** Breakout/level-break entries fill
   AFTER the level (slippage into the sweep): adverse fills of 200-300 pts
   were routine (#16273: -208 pts stop slip; #16306: -301 pts entry slip).
   The one winner (#16292) worked by riding INTO a flush, not by sitting
   on a level.
4. **The zap sequence predicts the next leg.** After the range's LONG side
   is zapped (stops below support fired), the next liquidity grab is
   typically UP (shorts' stops above the range) — and vice versa. Read
   which side just paid, and lean toward the OTHER side's zap next.
5. **Post-impulse flushes are liquidity, not reversals** (unless higher TFs
   break): after a real impulse, the deep flush (often 50-70%) grabs the
   breakout crowd's stops while 1h/4h stay intact. The re-entry is the
   flush INTO structure with a reclaim confirmation — never the impulse
   chase (worst fills) and never the mid-flush knife.
6. **Chop leverage ceiling: 5-10x. NEVER max leverage in chop.** #16307's
   40x turned a -0.53% flush into -21.4% margin — and stops slipped past
   the SL on top of it. High leverage converts ordinary sweeps into
   account-level damage. Save 40x for TREND regime with volume.
7. **Same-coin tranches MERGE on HL.** Two DB rows on one coin = one HL
   position at the average entry; whichever DB row's level hits first
   closes the ENTIRE position, and per-tranche attribution corrupts (both
   rows sync to the merged entry). Multi-tranche = plan for "tightest
   level governs everything" (align TPs, expect first-hit-closes-all).

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
  Open: [each trade + the TWO LINES: invalidation / confirmation]
  Recent closed: [exit reason + PnL + attribution: who called it]

⚠️ CHOP CHECK: [N flips/24h — CHOP or TREND regime]

📊 1. MULTI-TIMEFRAME
  [TF results — label forming-candle reads "(forming)"]

📈 2. CONTINUUM
  [continuum data]

📐 3. SUPPORT/RESISTANCE
  [key levels]

🔄 4. CONTRARIAN + DIVERGENCE
  [contrarian analysis — label divergence type per taxonomy §3]

🎯 5. SCORE
  [raw score → chop-adjusted score + regime flag]

🎯 6. VERDICT — two parts:
  DIRECTION: [LONG/SHORT/NONE + who outranks here per §8 trust protocol]
  ENTRY: [the LEVEL + tight structural SL + TP + planned AND real R:R
          (with slip buffer) — or "no trade, level never came"]

═══════════════════════════════════════════
```

## Date
Created 2026-10-16 combining all analysis skills. Decision Protocol added
2026-10-19 after the 9-trade manual BTC session (chop failures #16250/#16273,
confirmation lesson #16283, divergence taxonomy from the 1m/5m/1h reads).
§11 BTC chop zigzag added 2026-10-20 after the 6-trade sweep sequence
(#16291-#16307: both range sides swept, +2,105-pt impulse, -1,146-pt reverse
zap took the 40x tranche at -21.4% margin). CEO thesis: BTC collects all
liquidity — zap the longs, then the shorts — before the real move.
