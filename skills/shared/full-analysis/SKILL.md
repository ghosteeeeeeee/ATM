---
name: full-analysis
description: Use when you need a complete trading analysis combining MTF, technical, contrarian, continuum, S/R, Bollinger Bands, and EMA200. The master analysis skill. Triggers on "full analysis", "complete analysis", "what's the call", "analyze everything", "run all analysis".
---

# Full Analysis Skill

The master analysis framework combining all sub-skills into one comprehensive output. Run this before every trade decision.

## Components

This skill combines:
- **Position check** — Current open/closed positions, exit reasons, PnL
- **Structure engine** (computed) — `scripts/structure_analysis.py`: per-TF HH/HL/LH/LL sequences, swing levels, channel state, structure breaks
- **mtf-analysis** — Multi-timeframe analysis (1m/5m/15m/1h/4h)
- **technical-analysis** — RSI, MACD, EMAs, volume, patterns
- **contrarian-analysis** — "What if I'm wrong?" checklist
- **Continuum oscillator** — Macro regime
- **Support/Resistance** — Key levels (the structure engine's swing SH/SL are the authoritative ones)
- **Bollinger Bands** — BB position (0=lower band, 1=upper band)
- **EMA200** — Long-term dynamic support/resistance
- **Volume ratio** — Per-timeframe volume confirmation
- **ADX/ATR lifecycle** (computed) — `scripts/adx_atr_analysis.py`:
  trend-strength/range peaks, exhaustion & climax detection (rules below)

**Data source rule (2026-10-22):** ALL price/candle/indicator reads come from
the LOCAL stores — `data/candles.db` (refreshed every minute by the
price_collector timer) and `data/prices.json`. Never make ad-hoc
`candleSnapshot`/Hyperliquid API calls from an analysis session: they burn
shared rate-limit budget (429 risk) that order placement depends on, and the
local data is never staler than ~60s. API is only for what the local DB does
not have (live mid on a delisted/edge case, exchange positions state).

### Multi-coin spin-off (CEO directive 2026-11-10)

```bash
python3 scripts/coin_analysis.py               # jup_yolo list: HYPE SOL BTC ETH
python3 scripts/coin_analysis.py HYPE SOL ...  # explicit coins
```

Same engines, parameterized: `auto_analysis.build_decision(token=...)`
(scores/bracket/structure per coin), structure engine, ADX/ATR lifecycle,
precheck at execution. Two spin-off-specific pieces:

- **BTC-coupling label** (CEO worry: "trends would be very similar to
  btc... others might go up/down independently"): Pearson correlation of
  15m log-returns vs BTC (~18h) + beta + 24h relative strength →
  **OWN-TREND** (|corr| < 0.6 — trades its own story, BTC read = context
  only) vs **BTC-DRIVEN** (≥ 0.6 — a leveraged BTC echo: lead with the
  BTC full-analysis there). Empirically the majors ARE echoes (HYPE +0.84,
  SOL +0.90, ETH +0.95) — independent movers must be found OUTSIDE the
  jup list (run the spin-off on HL-universe candidates to screen them).
- **Regime is the market's**: alts have no continuum of their own — the
  BTC chop count is their regime context (output labels
  `regime_source: BTC`); structure/ADX/RSI/ATR are the coin's own.

Screening output only — any actual trade still goes through
manual-trade-override (precheck, explicit levels, verify).

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
3. Is the exit management actually firing for this signal type? For CEO
   trades (`ai-trader-manual`/`ai-trader-pending`/`ai-trader-auto`) that
   means `manual_exit_manager` per THE CONTRACT (manual-trade-override
   skill): labels should be `manual_sl_hit`/`manual_tp_hit`/
   `manual_trail_hit` — an `rr_engine_*` or `atr_*` label on a CEO trade
   is a routing bug. For pipeline signals: RR engine / ATR trailing.
4. Are you already on the right side or the wrong side?

**Exit reason interpretation:**
- `atr_trail_hit` — Trailing stop took profit (winner trailed out)
- `atr_sl_hit` — ATR stop loss hit (loser)
- `hard_max_loss` — cap hit (loser). NOTE (2026-11-14): for managed STRUCTURAL trades the threshold IS the structure-stop distance (`hml_threshold` — the account-floor clamp was retired after #16909 pre-empted an unbroken structure at 10x) — a managed `hard_max_loss` now means the stop line itself; non-managed keeps the old −4% account line.
- `rr_engine_*` — RR engine managed exit (structural support/resistance)
- `HL_CLOSED` — Closed on Hyperliquid directly
- `trail_sl` — Trailing stop loss hit
- `manual_sl_hit` — CEO trade's predefined stop did its job (exit contract)
- `manual_tp_hit` — predefined target hit (2026-11-15: suppressed for
  stop-bearing structural trades — target is validation-only there)
- `manual_trail_hit` — CEO trade's close trail took profit (exit contract)
- `manual_*`/`rr_engine_*`/`atr_*` mismatch on a signal type = routing bug — report it

**Also check what's ARMED:** positions are only half the exposure. Read
`data/pending_orders.json` + `data/pending_orders_state.json` — an armed
bracket between its triggers is live optionality that shapes every verdict
(e.g. a fired-but-unverified order needs recovery, not analysis). The
§12 bracket from the last analysis usually lives here.

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

### MTF Volume Analysis (COMPUTED — run every analysis)

Volume confirmation across timeframes tells you if a move is real.

**Run this every analysis** (local candles DB first — same pattern as
the other computed sections):

```python
import sqlite3
con = sqlite3.connect('file:/root/.hermes/data/candles.db?mode=ro', uri=True)
def vol_ratio(tf, window_bars):
    cur = con.cursor()
    cur.execute(f"SELECT volume FROM candles_{tf} WHERE token='BTC' "
                f"AND is_closed=1 ORDER BY ts DESC LIMIT {21*window_bars}")
    vols = [r[0] or 0 for r in cur.fetchall()]
    if len(vols) < 21*window_bars: return None
    # bars are DESC: [0] = newest window of `window_bars` bars
    recent = sum(vols[:window_bars]) / window_bars
    base = sum(vols[window_bars:21*window_bars]) / (20*window_bars)
    return (recent/base) if base > 0 else None
ratios = {tf: vol_ratio(tf, n) for tf, n in
          (('1m',1), ('5m',1), ('15m',1), ('1h',1))}
```

**⚠️ DATA-INTEGRITY RULE (added 2026-11-23):** a `None`/`0.00x` ratio
means the RECENT bars carry no volume (a collector gap — 5m/15m/1h
historical volume exists but recent closed bars read 0), NOT a market
condition. In that case: (a) fall back to aggregating the 1m volume
into that TF's window (the 1m path writes real volume), (b) report the
fallback explicitly ("15m vol via 1m-agg: X.XXx — collector gap"),
and (c) never print a dead column as `0.00x` beside the market reads —
a zero printed as a fact is worse than a missing number. Verify the
gap at the source (which writer stopped) before trusting any MTF
volume pattern that day.

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

**Slippage buffer (all BTC trades, any leverage):** before quoting R:R,
subtract a slip buffer from the risk side — 150-250pts on a normal tape,
**250-300pts in a fast tape** (the buffer sizes to the tape, not the
leverage: #16273 blew 208pts at 10x; #16353 filled 281pt adverse at 5x).
Quote "planned R:R" and "real R:R (with slip)" separately — armed
conditionals must clear ≥1.0 real (manual-trade-override arming rule 3).

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

### Structure Analysis — HH/HL sequences, channels, breaks (COMPUTED — run every analysis)

Indicators lag; structure doesn't. The CEO's manual 1h read on 2026-10-20
("higher-highs and higher-lows since 16:00") was the correct trade context
before any indicator confirmed it — and the structure engine now computes
exactly that read for every timeframe, every analysis:

```bash
python3 /root/.hermes/scripts/structure_analysis.py COIN
# default TFs: 1m 5m 15m 1h 4h — output: state, tags, swing levels, slope
```

**The four states per TF:**

| State | Tags | Meaning | Trade implication |
|-------|------|---------|-------------------|
| **UPTREND** | HH HL | Higher highs + higher lows | Direction bias LONG; buy flushes into the HL ladder |
| **DOWNTREND** | LH LL | Lower highs + lower lows | Direction bias SHORT; sell rallies into the LH ladder |
| **COMPRESSION** | LH HL | Lower highs + higher lows (coil) | Triangle — expansion is coming; do NOT fade the eventual break; the coil IS the §11 liquidity pile |
| **EXPANSION** | HH LL | Higher highs + lower lows (broadening) | Chaos/transition — no structure to trade; smallest size or stand down |

**The rules:**

1. **Swing levels are the real S/R** — the engine's SH/SL values (zigzag,
   0.6×ATR threshold) are where SL/TP belong. Round numbers are decoration;
   the 22:00 swing low at 82,944 is a level, 83,000 is not.
2. **Structure break = CLOSE beyond the last opposite swing.** A wick
   through is the §11 sweep (liquidity grab — often reverses); only the
   close-through is a break. Never enter on a wick-break of structure.
3. **Multi-TF structure reads as a sentence**: higher-TF state sets DIRECTION
   bias, executing-TF state sets ENTRY. 1h UPTREND + 5m DOWNTREND =
   "buy the pullback in the uptrend" — the disagreement is the entry, not a
   contradiction. 1h COMPRESSION + any lower-TF trend = the lower-TF move is
   probably the pre-break noise inside the coil — size down.
4. **Executing-TF structure outranks indicators at that TF.** If 5m says
   BEAR MACD but structure says UPTREND (HH HL), the MACD is the pullback
   inside the ladder — structure wins for direction, indicators only time
   the entry within it.
5. **States flip with the trend** — recompute after every swing confirms;
   a UPTREND whose last swing printed LL is now COMPRESSION or DOWNTREND.
   Never quote yesterday's state.

**Evidence of the engine matching the tape:** 2026-10-20 23:00 — engine
reported 1h UPTREND [HH HL] SH=83,189 SL=82,394; those are precisely the
22:00 high and 19:00 low the CEO read by eye. Same levels, no eyeballing.

### MTF RSI Structure (COMPUTED — run every analysis; CEO 2026-11-23)

Treat the RSI line as its OWN structure: swing highs/lows on the RSI
series → HH/HL/LH/LL sequences → and, crucially, **structural breaks
in the RSI itself**. Momentum structure breaks usually LEAD price —
the RSI loses its last swing-low while price is still above its own
swing-low = the early warning that the price structure is about to
follow. This is sequence-structure on the oscillator; §3 (the divergence
taxonomy) covers the VALUE relationship between price and RSI — use
both, label each precisely.

**States (per TF, from the last two RSI swings each side):**
- `RSI-STRUCT BULL` = HH + HL (momentum trending up)
- `RSI-STRUCT BEAR` = LH + LL (momentum trending down)
- `RSI-STRUCT MIXED` = transition (e.g., HH+LL = momentum topping,
  LH+HL = momentum bottoming)

**Break labels (the ask — the break IN the RSI):**
- `RSI-LOST-LAST-SL` — the RSI closed below its last swing-LOW: the
  HL chain broke = momentum-structure break bearish, OFTEN BEFORE the
  price structure breaks (the leading read)
- `RSI-RECLAIMED-LAST-SH` — the RSI closed above its last swing-HIGH:
  the LH chain broke = momentum-structure break bullish
- `RSI-NO-BREAK` — the current RSI sits inside its last swing range

**MTF alignment:** the higher TF's RSI-structure is the context, the
executing TF's is the trigger: `RSI-BEAR (15m) + RSI-BULL (1h)` = a
counter-trend bounce inside a bear momentum base (CHOP-shaped);
`RSI-BEAR (15m) + RSI-BEAR (1h)` = aligned bear momentum (the move has
the oscillator behind it); an `RSI-LOST-LAST-SL` on the executing TF
while the higher TFs are still BULL = the earliest exit/avoid warning
for longs (and the earliest entry warning for fades-of-the-break).

**Feeds the verdict:** (a) in §4 report it as its own line per TF; an
`RSI-LOST-LAST-SL` on 15m/1h UPGRADES the contrarian/avoid read even
when the price structure is intact (momentum broke first); (b) in CHOP
regime the executing-TF RSI-structure IS the momentum read the flag
says to prefer over the trend scores; (c) never treat an RSI break as
a fill — it informs DIRECTION/contrarian only (entries stay levels +
confirmation, per Decision Protocol §1).

```python
def rsi_series(closes, p=14):
    g, l = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i-1]
        g.append(max(0.0, d)); l.append(max(0.0, -d))
    ag = sum(g[:p]) / p; al = sum(l[:p]) / p
    out = [100.0 - 100.0/(1 + ag/al) if al > 0 else 100.0]
    for i in range(p, len(closes)):
        ag = (ag*(p-1) + g[i-1]) / p
        al = (al*(p-1) + l[i-1]) / p
        out.append(100.0 - 100.0/(1 + ag/al) if al > 0 else 100.0)
    return out

def rsi_structure(tf, lb=3):
    # closes from the local candles DB (the same read as the MTF block)
    ...closes = [...candles_{tf} close DESC...][::-1]
    r = rsi_series(closes)
    # the skill's find_swings(data, lb) works on any series:
    his = find_swings(r, lb)          # RSI swing-HIGH values
    los = find_swings([-x for x in r], lb)  # RSI swing-LOW values (negated maxima)
    los = [-x for x in los]
    if len(his) < 2 or len(los) < 2:
        return {'state': 'NA', 'break': 'RSI-NO-BREAK'}
    state = (('HH' if his[-1] >= his[-2] else 'LH') +
             '+' + ('HL' if los[-1] >= los[-2] else 'LL'))
    label = {'HH+HL': 'BULL', 'LH+LL': 'BEAR'}.get(state, 'MIXED')
    cur = r[-1]
    if cur < los[-1]:
        brk = 'RSI-LOST-LAST-SL'
    elif cur > his[-1]:
        brk = 'RSI-RECLAIMED-LAST-SH'
    else:
        brk = 'RSI-NO-BREAK'
    return {'state': f'RSI-STRUCT {label} ({state})', 'break': brk}
```

### ADX/ATR — Trend Lifecycle (COMPUTED — CEO rules, added 2026-10-27)

ADX measures trend STRENGTH, ATR measures range EXPANSION. Together they
DATE the move: when the strength/volatility behind a trend peaks, the
trend is in its last act. Run it on every analysis:

```bash
python3 /root/.hermes/scripts/adx_atr_analysis.py COIN   # local DB, closed bars only
```

**The lifecycle rules (CEO's, tape-derived — rules 1-4 from 2026-10-27/11-10, rule 5 from 2026-11-14):**

1. **ADX back to ~0 → new trend starting.** ADX below `ADX_NEAR_ZERO`
   (5.0) means the previous trend has ENDED — flat, and a NEW trend is
   beginning from neutral. This is a beginning signal, not an absence of
   one: the next directional ADX rise marks the new trend's birth.
2. **ADX peak + a NEW major extreme after the peak → the move is over.**
   ADX peaks when trend momentum is strongest; if price then prints a
   new major low (downtrend) / high (uptrend) AFTER that peak, the
   extreme is exhaustion — the 5th-wave final push. Price has usually
   then continued the OTHER way from the exhausted extreme.
   (Divergence shape: new price extreme, lower ADX peak.)
3. **ADX + ATR peaking together → climaxed move is over.** When strength
   AND range expansion peak within `ADX_DUAL_PEAK_TOL` (4) bars of each
   other, both engines are spent. Confirmation arrives like rule 2: a new
   extreme printed after the dual-peak that fails to extend momentum.
4. **ADX divergence at a price extreme → the trend may be changing**
   (CEO 2026-11-10, 15m read): price prints a NEW low (or high) while
   ADX's latest peak is SIMILAR-TO-LOWER than its previous peak — the
   indicator is not confirming the extreme → momentum is unconfirmed,
   the trend is exhausting, a reversal (e.g. the downtrend ending, an
   uptrend beginning) is brewing. Companion reads from the same snapshot:
   **ATR back at its previous peak** = volatility climax (both engines
   spent — same family as rule 3); **MACD and RSI both low** = oversold
   but NOT a floor — "could drop further", never a buy signal on its
   own: it needs rule-4 divergence + structure confirmation first.

5. **ADX-trendline family (CEO's own indicator, tape-verified 2026-11-10→13)**
   — draw the trendline on the ADX peaks/lows THEMSELVES, not on price:
   - **Bounce off an ADX-trendline low → the thrust**: ascending ADX
     lows (15.4 → 27.7, Nov-12) held, ADX then ran to a NEW PEAK
     (48.5 → 55.3) and price thrust with it (70k → 68.6k leg). A new
     ADX peak AFTER the bounce = the move extending, not ending.
   - **A PEAK and a CROSS mean different things** (Nov-10 dissection):
     the ADX PEAK (14:15, 33.5) preceded the big short (−2.5% to the
     low); the line-CROSS (17:15) preceded the recovery (+0.86% / 6h).
     Peak = the move; cross = its END. Never read them the same way.
   - **Split-reads = coiled resolution**: 1m ADX sitting on its series
     floor (16.9/15.0) while 15m ADX prints a new arc-high (59.8) =
     micro-trend spent vs macro-trend strongest — POSITION BOTH SIDES
     and let the pin resolve; do not predict (Nov-13 04:39 case: both
     wings armed, verdict "undecided by design", resolved later).

**How to read it in the verdict:** per-TF state (TRENDLESS / TREND
RUNNING / ADX PEAKED / DUAL-PEAK CLIMAX / EXHAUSTION + flags), then one
multi-TF sentence — lower TFs lead the lifecycle (1m/5m turn first),
higher TFs confirm the regime. Lifecycle flags do NOT set direction by
themselves; they DATE the move: an EXHAUSTION flag on the executing TF +
a §3 divergence + structure breaking = the reversal confluence; a RUNNING
higher-TF trend = don't fade it. Rule 1 zones (trendless) are exactly
where §11 sweeps and §12 brackets live.

Closed bars only (the script filters `is_closed=1`); if you eyeball ADX
mid-bar, the §4 forming-candle labeling rules apply.

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

**Ladder adds (CEO 2026-11-21: 'if it fires and another btc trade is open,
it should add — same for the long side'):** the ladder adds AS LEVELS —
each rung that crosses while a SAME-direction BTC position is open fires as
a second tranche (`--force` second-tranche path, own rung-level SL/TP, one
rung per pipeline cycle as the throttle). OPPOSITE-direction opens still
wait (netting would close a live trade = violates the stay-in doctrine, §13;
no accidental flips). Non-ladder autos keep the 2026-11-10 belt (dup-guard
fails them safe). Adds-at-a-level carry their own structure stop; the
tighter-SL rule above governs adds into the SAME level. Worst-case add
exposure = the armed rungs within reach × rung size — bounded per cycle,
not per move.

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
8. **First-break entries are the retest-stop trap** (2026-11-20 harness,
   the 9 burned rungs, independent-verdict AGREE-HIGH): entering the
   instant a level breaks with the stop at the reclaim-of-broken-level
   puts the stop INSIDE the retest's own wick envelope — MAE across the
   nine = 0.26–2.89% while armed stops were 0.25–0.58% → **0/9 as-armed,
   −33.93% margin** (stops-ignored direction was right8/9 — the entry×
   stop geometry, not the direction, was the defect). The brain gates
   that vetoed them (BANANA RSI<35 / HARD_FLOOR<45, all nine rejections
   cite them) are right about the SHAPE: the gate-compatible,
   §11-faithful entry is the **re-cross after the sweep-reclaim resolves
   with RSI recovered**, stop at the LEVEL (0.8% class) — not the
   trigger-reclaim. Consolidations deliver **runs of failed touches**
   before the clean leg (the Nov18–20 stop-run boundaries reproduce
   exactly; run-length counts are clustering-dependent — H1's specifics
   stay UNSETTLED until plan §9's F-3/F-5 clear).
9. **First break NEVER fills; entries are reclaim → re-cross; stops sit
   at major structure — never an arbitrary percentage** (CEO directive
   2026-11-20, after #17004). The execution machine (trade_watchdog):
   a fresh rung's FIRST cross records `first_break` and does NOT fill;
   when price reclaims the level → `retested`; only the NEXT cross
   (the failed-retest re-cross, §11's CONFIRM shape) fills — a
   brain-vetoed fill maps its reclaim to `retested` too (no burn).
   **Exception — continuation rungs** (`entry_style: continuation`, the
   fresh-air price×0.997 arms): air has no prior level to reclaim, so
   the retest-wait starves them in a straight slide (58736: first_break
   18:45, price fell to 58,162, zero fills — 'falling like a rock').
   They fill ON CROSS with their structure stop — #17004's sin was the
   arbitrary 0.6% stop, not the fill itself. Retest-style (structure)
   rungs keep first-break-never-fills.
   **Straight-line escape** (CEO takeoff thesis 2026-11-20, `MULTI_
   TOUCH_ESCAPE_PCT = 0.5`): a first_break rung whose price runs 0.5%
   PAST the level without ever reclaiming qualifies (`retested`) and
   FILLS — the rare one-way slice (the ~30% no-retest case) must not
   starve the ladder ('falling like a rock'; 'when btc takes off it
   will prob do so in a straight line, all the way to 70k, 80k'). Both
   directions; continuation rungs unaffected (they fill on cross).
   Why: #17004 was a first-tick catch with a `price×1.006` stop — no
   level broken, no thesis — and lost −6.89% margin in 3 minutes on the
   bounce; the sims had already scored first-break entries with
   reclaim-stops **0/9** (Study 1). Counterfactuals: the two-state
   machine skips #17004 entirely ($0); a conviction stop alone does
   not (it was −6.3% unrealized, never touched). Stop doctrine for
   catch-style arms: **MAJOR structure** (sh1h + 0.1·ATR1h — the lag's
   line convention), which means the worst case is the structure
   distance × leverage (at 10x, a 4.9% stop ≈ −49% margin — size and
   serial are the bounds; say so when arming). The keeper's fresh-air
   arms carry this stop; structure rungs keep their reclaim-SLs.

### 12. The no-edge default: ARM THE BRACKET (CEO directive, 2026-10-21)

When the analysis finds no clear direction — both scores negative or
MARGINAL, chop pin at the EMA300, LOSERS-list flags, dead volume, no
verified live read — **the default action is NOT a market entry and NOT
standing aside: it is arming a conditional bracket at the chart's support
and resistance.** The stop-limit process IS the backup strategy.

- Take the levels from the structure engine (swing SH/SL) cross-checked
  with the CEO's chart levels; cushion both triggers (§11-1 style);
  SLs get 200pt+ wick room; TPs exit INTO the opposing level, never AT
  round numbers; both legs verified non-overlapping.
  **CROSS-SIDE INVARIANT (2026-11-14):** every rung's SL must sit
  beyond the OPPOSITE side's nearest unfired trigger — rally kills the
  short before the long fires, drop kills the long before the short
  fires (evidence: the 68,551/68,557 pair — 6pts, serial-safe; and the
  three-way check that caught a 3pt overlap on 73,594-class rungs).
  `serial:true` then guarantees no stacking on top of it.
  **SIZING — add-on-winners (CEO 2026-11-13):** rungs size at **2× base
  ($22.20) when the side's last-5 closed trades net positive**, base
  ($11.10) otherwise (HL $11 floor = losers can't shrink; "remove from
  losers" = no pyramid + serial cuts). The keeper enforces it
  (`_side_mult`); apply the same table when deriving by hand.
- Market entries in no-edge states are the #16283/#16291/#16317 pattern —
  paying the sweep tax for information the bracket gets for free by
  waiting. The bracket converts indecision into defined-risk optionality:
  chop between the levels = no trade (correct), a real move = caught with
  structure-based invalidation.
- Every full-analysis that ends in "no trade" must END with the bracket
  proposal: the two levels, the four numbers per leg (trigger/SL/TP/size),
  armed and verified — not an empty verdict.
- **The bracket is a LADDER, probability-weighted (CEO 2026-11-10:
  "there is always a short we want to be ready for... it is about
  probabilities, anything can happen").** Arm every rung the chart gives
  — trendline-touch breaks, local-low breaks, major-low breaks (each
  own TP/SL, `serial: true` so they fire rung-after-rung), mirrored on
  the long side — instead of picking one level. The analysis's job is
  weighting (which rung is most likely to be reached first / to pay),
  never deciding "no short exists". See manual-trade-override rule 13.
- **⚠️ DIRECTION MAPPING IS FIXED — never silently all-longs.** Two levels
  given as a pair = the CEO's bracket by default:
  **break DOWN through the lower level → SHORT, break UP through the
  upper level → LONG.** Only an explicit CEO instruction overrides a leg
  (e.g. "defense long" for a flush-bounce thesis). 2026-10-22 miss:
  CEO gave support 84,278 / resistance 84,933 expecting the standard
  bracket; both legs were wired LONG from an analyst-side proposal —
  when 84,240 broke, a LONG fired at the breakdown (the CEO's model
  said SHORT) and the 1,100-pt decline was the trade that never existed.
  Whenever arming two levels, PRINT the mapping back
  ("lower break = SHORT at X, upper break = LONG at Y") and get the
  confirm before writing the config. Bracket legs also never re-fire at
  a spent level — a lower level already broken 1,000+ pts ago moves the
  short leg to the NEXT major shelf (§11 lesson: major structure only,
  cushioned), not back to the old number.

### 13. Major-structure stop discipline — hold through the whipsaw (CEO 2026-11-10)

A stop that follows the PATTERN'S INTERIOR swings gets hunted by the
pattern's own whipsaw. The flag/consolidation trades of 2026-11-10 are
the proof: #16851/52's stop tracked the 15m swing to 74,114 and was
hunted at 74,285 — **100 minutes before the real drop to 72,817**;
#16846's trailed stop (74,727) died on the 74,5xx retest of the same
flag. One held position would have ridden entry→72,8xx whole; instead
two early exits plus a double-stopped pair summed **−1.94%**. The CEO's
model:

- **The stop references MAJOR structure — the pattern boundary, 1h
  swings, and round lines (the 74,000-class) — not the 15m interior.**
  The watchdog's structure-follow (auto_trader tweak R1) and
  `_structure_sl` both use the **1h snapshot** for exactly this reason.
- **Ratchet only after the expansion leg establishes.** Inside the
  flag/compression the stop stays at the pattern's outer bound (the
  resistance-side stop that defined the entry); it moves down/trails
  only once price has broken and traveled (the drop past 74,000) —
  "anything crossing that (74,000) would break structure" is the
  trailing condition, not the 15m wiggle.
- Exit still means structure broken — measured against the TRADE'S
  timeframe: an 8h hold is invalidated by an 1h/round-level break, not
  by a 15m retest. Minor-structure stops = §11 sweep bait.

**Stay-in ruling (CEO 2026-11-21, after the four-trade night ledger
realized +$0.08 while moves ran 2,501/1,585/600pts): "look at what the
drawdown was for these trades, you need to stay in."** Exits are
DRAWDOWN-DRIVEN ONLY: a safe trade with zero/tiny drawdown stays in
(evidence: #17007 adverse +5pts, #17010 +47pts, #17013 ZERO — three
exits while safe; only #17008's 383pts justified its stop). The stops
that move a trade: BE-cap, structure-trail, HML, disaster — all
drawdown-driven. `mfe_exit` was REVERTED to its audited home (mirror
book, jup_yolo scope) and does NOT close structure-governed/ladder
trades; `prearm_lock` stays on the mirror book (CEO: keep). Full text:
manual-trade-override rule 14.
- Pair with ADX rule 4: interior whipsaws at fading ADX peaks are the
  exhaustion signature that PRECEDES the real leg — surviving them is
  the whole trade. Stacking lesson (same day): two AUTO shorts fired
  1min apart in one dump → 2× exposure stopped −3.80%×2 on one spike —
  auto orders now wait until flat (monitor stacking guard + scoped
  `--force`), CEO tranches keep the merge path.

- **Regime split (evidence: 2026-11-13)** — in CHOP the stop must
  reference MAJOR (1h) structure: the box interior is a SHAKEOUT zone
  (#16891's interior raise to 69,106 and #16896's armed 68,950 both
  died inside the base; 4 stops in 9h = −15.1% margin = the box tax).
  In TREND the responsive 15m trail books (#16886: five structure
  steps then the exit). The exit MECHANICS (birth re-anchor, regime-
  split lag, adverse-raise-to-1h, guardian structure-widening) live in
  manual-trade-override rules 12-13; this section owns the analysis
  reads that FEED them.

### 14. The pin/box state — no mid-range entries (evidence: 2026-11-13)

A **PIN** = price welded to the EMA300 (the precheck quantifies it:
"AT EMA300 Xm — mid-band entries have no edge — wait for resolution")
with z ≈ 0, velocity/acceleration ≈ 0 and CHOP regime. A **BOX** = the
same state framed as a range (1h/4h in-range % pinned at a band
extreme). Rules:
   (a) NO market entries mid-pin/mid-box — both sides get ARMED at the
   edges instead (the rungs ARE the entries);
   (b) the box has a price: the Nov-13 churn — 4 stops in 9h =
   −15.1% margin from interior stops + re-entries inside a ~1,000pt
   box — while the same discipline held FLAT through every pin cycle
   for free;
   (c) velocity/acceleration curling up from negative while z sits
   deeply below = the pre-bounce configuration — it preceded every
   bounce of this arc (3/3), but it is NOT a signal until the
   reclaim: confirm with the structure line or the EMA300, never
   front-run it;
   (d) a pin verdict is DIRECTION "undecided BY DESIGN" + ENTRY "none"
   + the armed-book listing (§12 completion) — a positioning answer,
   not a prediction.

### 15. Evidence discipline — what a strategy claim must survive (2026-11-20 harness + two independent audits)

Before ANY backtest number is quoted in an analysis, a plan, or a report:
1. **Four columns or it didn't happen**: as-simulated /
   confirmable-levels / flat-only / net-of-costs (0.09% RT fees + 0.10%
   slip = 0.19% price per round trip). Gross, lookahead, or
   unlimited-position numbers are illustrations, not edges.
2. **Lookahead kills, twice**: a swing's level is knowable the bar AFTER
   its confirm bar (the confirm bar's own close is mid-bar unknowable);
   gates read the PRIOR bar's close. A delay0 column must be labeled
   as-simulated — never compared to production as if it were real.
3. **Base-rate control**: every retest/recovery stat must beat its
   generic control (any 0.5% red bar bounces 90% within 24h — a raw
   "70% retest" proves nothing alone). H1's major-break/retest claims
   remain UNSETTLED until F-3/F-5 (plan §9).
4. **Gate with shipped labels**: a re-derived proxy gate (EMA80/320)
   agreed with the production `structure_json` states only **26%** —
   gate backtests with the SHIPPED state labels, and the gate's effect
   is side/column-dependent (gated < ungated in 17/32 rows; it *helped*
   longs 14/16) — never assume a gate helps; measure it per side.
5. **Concentration**: episodes are not independent (runs of 7–12; top-3
   half-days carried 73% of one total) — report block/half-day shares
   alongside counts.
6. **Pin the data**: `candles_15m` is a rolling 90-day window — print
   window + full-row sha with every result (a roll moved 65/99 lines
   between runs); re-run before citing an old number.
7. **State the fill model**: signs flip on slip alone (breakeven slip
   ≈ +1.9 bps over taker fees; ~6 bps RT flipped the fixed-TP short
   rows from negative to positive) — the assumption travels with the
   number.
8. **Proxy ≠ production**: a backtest exit-model is a stand-in — name
   its differences from the shipped code (the TRAIL proxy lacked
   adverse-raise, BE-cap, birth re-anchor, and the 30-min cycle — ten
   documented differences) before presenting its results as system
   expectations.
   Reference: `scripts/backtest_retest_fade.py` (pinned constants,
   data-sha header) · `plans/2026-11-20_retest-fade-system-plan.md`
   §7–9 · verdicts `1795152254`, `1795157600`,
   `bug-hunter-retest-fade-harness-2026-11-20`.

## Analysis Script

**Fast path (2026-10-22):** `python3 scripts/auto_analysis.py` runs the
SAME engines this skill specifies (chop flip counter, structure engine,
MTF scoring with chop adjustment) and emits the machine-readable decision
object — price, regime, structure per TF, scores, §12 bracket proposal
with triggers/SL/TP, reasons. Run it first, then fill in the tape reads
it can't compute (divergence nuance, live-momentum, CEO reads) by hand.

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
**FAIL is advisory for CEO trades (never hidden):** report the FAIL reasons
in the verdict and in the order `note` — the CEO decides. The precheck
catches what the eye misses: RSI band (shorting an oversold extreme =
BANANA), vol floor, LOSERS list, RR gate.

## Verdict Rules

| MTF Alignment | Continuum | Verdict |
|---------------|-----------|---------|
| 4-5 bullish | Bullish | **STRONG LONG** |
| 4-5 bearish | Bearish | **STRONG SHORT** |
| 3/5 bullish | Mixed | LONG with caution |
| 3/5 bearish | Mixed | SHORT with caution |
| Mixed | Any | **NO TRADE** |

**Ride-cost accounting (run whenever exits clustered inside a trend):**
ride = (trend-start candle-open − span low) × leverage; fragments = Σ
the trade pnls; captured% = fragments ÷ ride. Canonical (driven into
the TP-doctrine): Nov-11 19:00 → Nov-13 — ride **+37.3%** (to the
cited low) / **+39.5%** (span low 68,608) vs 7 fragmented trades
**+16.0%** = **41% captured**; every TP cap or interior exit during
directional travel is part of that ~23pt-of-margin gap. Cite the
method + numbers whenever the verdict reviews a series of exits.

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
  MTF VOLUME: 1m X.XXx · 5m X.XXx · 15m X.XXx (via 1m-agg if the
    column is dead) → pattern: real-breakout / fakeout / exhaustion /
    accumulation / none (per the table above); flag any collector gap
    by name
  RSI-STRUCT (the RSI's own swings): 1m [state/break] · 5m [...] ·
    15m [...] · 1h [...] → MTF alignment sentence (the leading-break
    warnings live in §4)

🧱 1b. STRUCTURE (python3 scripts/structure_analysis.py COIN)
  1m: [state HH/HL tags | SH/SL levels | slope]
  5m: ...
  15m: ...
  1h: ...
  4h: ...
  [Multi-TF read as a sentence: direction bias (higher TF) + entry context
   (executing TF) — flag any BROKEN tags]

📡 1c. ADX/ATR LIFECYCLE (python3 scripts/adx_atr_analysis.py COIN)
  1m: ADX [value] (peak Xb ago) | ATR [value] (x.x%) (peak Xb ago) | [state]
  5m: ...
  15m: ...
  1h: ...
  4h: ...
  [lifecycle sentence: where each TF sits in the cycle — rule 1/2/3 flags,
   which TFs are RUNNING vs EXHAUSTED, and what that dates about the move]
  ADX-trendline (rule 5): [line touch? peak-vs-cross? split-read?]

📈 2. CONTINUUM
  [continuum data]

📐 3. SUPPORT/RESISTANCE
  [key levels]

🔄 4. CONTRARIAN + DIVERGENCE
  RSI-STRUCT break warnings (the leading reads): [any RSI-LOST-LAST-SL /
   RSI-RECLAIMED-LAST-SH, with the TF — an executing-TF break while
   higher TFs disagree = the earliest warning line]
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
Structure engine added 2026-10-20 (scripts/structure_analysis.py): zigzag
0.6xATR swing detection, four states (UPTREND/DOWNTREND/COMPRESSION/
EXPANSION), close-based break rule. Reproduces the CEO's manual 1h HH/HL
read exactly (SH=83189 SL=82394 = the 22:00 high / 19:00 low).
§12 no-edge default added 2026-10-21 (CEO directive): when the analysis
finds no clear direction, the default action is arming the conditional
bracket at chart support/resistance — the stop-limit process is the
backup strategy; market entries in no-edge states are the sweep-tax pattern.
ADX/ATR lifecycle added 2026-10-27 (CEO rules + scripts/adx_atr_analysis.py):
rule 1 ADX→0 = new trend starting; rule 2 ADX peak + post-peak new major
extreme = 5th-wave exhaustion, move over; rule 3 ADX+ATR dual-peak =
climaxed move over (post-peak extreme confirms). Section 1c in output.
Rule 4 added 2026-11-10 (CEO): ADX divergence at a price extreme (new low
with a similar/lower ADX peak) = momentum unconfirmed → trend change
brewing; ATR at previous peak = climax; MACD+RSI low = could drop further,
never a floor alone. §13 added 2026-11-10: major-structure stop discipline
(hold through the flag's interior whipsaw — stops reference 1h/round
structure, not 15m interior swings; #16851/52 + #16846 + stacked-double
lessons). **2026-11-14 upgrade** (conversation audit, evidence-based):
rule 5 ADX-trendline family (peak=move / cross=end / split=coil — Nov-10
dissection + Nov-12/13 thrust); §14 pin/box state (box-tax −15.1%/9h,
pre-bounce velocity-curl 3/3, no mid-range entries); §12 cross-side SL
INVARIANT + add-on-winners sizing table; §13 regime-split (CHOP→1h
major vs TREND→15m responsive) with the mechanics pointer to
manual-trade-override; Verdict Rules ride-cost accounting (41% captured
canonical method); Step0 hard_max_loss = structure-widened cap note;
lifecycle intro count fixed. **2026-11-20 upgrade**: protocol item15
evidence-discipline (four-column standard; lookahead + prior-bar gates;
base-rate controls; shipped-state gates at 26% agreement; block
concentration; data-sha pinning; fill-model disclosure; proxy≠production
ten-difference rule) + §11 point8 first-break/retest-stop trap with the
gate-compatible entry shape (9-run study, AGREE-HIGH; H1 specifics
unsettled per plan §9 F-3/F-5) + §11 point9 multi-touch EXECUTION rule
(first break never fills — reclaim→re-cross machine in the watchdog;
stops at major structure sh1h+0.1·ATR1h, never arbitrary %; #17004
first-tick/arbitrary-stop loss −6.89% in 3min = the motivating case).
