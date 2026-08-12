# Coin Tracker — Per-Coin Intelligence System

## Problem

Current `coins.html` is a static snapshot from March 2026. It shows ~500 coins with a single price change number — no trend, no health, no context. We have 55+ signal modules that fire on individual coins, but no unified view of which coins are alive, dead, accumulating, or setting up. The system is flying blind on coin selection.

## Goal

A live collector that:
1. Tracks every tradable HL coin (~500+)
2. Computes per-coin health state (dead / moving / accumulating / distributing / setup developing / ready)
3. Maintains per-coin event history in SQLite
4. Produces composite scores that the pipeline can consume
5. Zero fakeouts — data quality is the first priority

## Architecture

### Data Source
- **Primary**: `allMids` from HL `/info` endpoint (already cached by `price_collector.py` → `hype_cache.py`)
- **Rate**: Existing 60s polling cycle — no new API calls needed
- **Supplemental**: Binance candles already in `candles.db` (1m, 5m, 15m, 1h, 4h)
- **Meta**: HL `meta` endpoint (already cached) for max leverage, decimals, etc.

### Database: `coin_tracker.db`

One mega DB with per-coin tables. Pattern: `coin_{symbol}` for each coin.

```
coin_tracker.db
├── _meta                    -- global state (last run, coin count, version)
├── _coin_registry           -- master list: symbol, first_seen, status, last_updated
├── coin_{SYMBOL}            -- per-coin events table (e.g. coin_BTC, coin_ETH)
├── coin_{SYMBOL}_1m         -- per-coin 1-minute candle cache (optional, for fast queries)
└── agg_scores               -- latest composite scores for all coins
```

### Per-Coin Table Schema: `coin_{SYMBOL}`

```sql
CREATE TABLE coin_{SYMBOL} (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          INTEGER NOT NULL,          -- unix timestamp
    event_type  TEXT NOT NULL,             -- price_tick | candle | signal | regime | health
    -- Price data
    price       REAL,
    bid         REAL,
    ask         REAL,
    spread_bps  REAL,                      -- spread in basis points
    -- Volume
    vol_1m      REAL,                      -- 1m volume (from candle)
    vol_5m      REAL,
    vol_1h      REAL,
    vol_24h     REAL,
    -- Indicators (computed at event time)
    rsi_14      REAL,
    macd_hist   REAL,
    ema_9       REAL,
    ema_20      REAL,
    ema_50      REAL,
    atr_14      REAL,
    -- Health state
    health      TEXT,                      -- dead | cold | warm | hot | setup | ready
    health_score REAL,                     -- 0-100 composite
    -- Signal context
    signal_type TEXT,                      -- the signal that fired (if any)
    signal_confidence REAL,
    -- Metadata
    regime      TEXT,                       -- bull | bear | neutral
    notes       TEXT                        -- free-form (e.g. "volume spike detected")
);
CREATE INDEX idx_coin_{SYMBOL}_ts ON coin_{SYMBOL}(ts);
CREATE INDEX idx_coin_{SYMBOL}_health ON coin_{SYMBOL}(health);
```

### Coin Registry: `_coin_registry`

```sql
CREATE TABLE _coin_registry (
    symbol      TEXT PRIMARY KEY,
    first_seen  INTEGER,
    last_seen   INTEGER,
    status      TEXT DEFAULT 'active',     -- active | delisted | paused
    health      TEXT DEFAULT 'unknown',
    health_score REAL DEFAULT 0,
    last_signal TEXT,
    signal_count_24h INTEGER DEFAULT 0,
    win_rate    REAL,                       -- historical win rate of signals on this coin
    total_trades INTEGER DEFAULT 0,
    avg_spread_bps REAL,                    -- liquidity indicator
    max_leverage INTEGER,
    decimals    INTEGER
);
```

### Composite Score: `agg_scores`

```sql
CREATE TABLE agg_scores (
    symbol      TEXT PRIMARY KEY,
    ts          INTEGER,
    health      TEXT,                       -- dead | cold | warm | hot | setup | ready
    score       REAL,                       -- 0-100
    momentum    REAL,                       -- price velocity score
    volume      REAL,                       -- volume trend score
    volatility  REAL,                       -- ATR-based score
    spread      REAL,                       -- liquidity score (inverse spread)
    signals     REAL,                       -- signal confluence score
    regime      REAL,                       -- regime alignment score
    composite   REAL                        -- weighted final score
);
```

## Health States

| State | Definition | Score Range |
|-------|-----------|-------------|
| `dead` | No volume, no price movement, delisted or abandoned | 0-10 |
| `cold` | Minimal activity, no trades worth watching | 11-25 |
| `warm` | Activity picking up, volume above average | 26-50 |
| `hot` | Active momentum, volume expansion, price moving | 51-75 |
| `setup` | Technical setup developing (e.g. squeeze, divergence) | 76-90 |
| `ready` | Setup confirmed, signal fired, ready to trade | 91-100 |

## Score Components (all normalized 0-100)

1. **Momentum** — Price velocity (rate of change), acceleration, position relative to EMAs
2. **Volume** — Volume vs 24h average, volume trend (increasing/decreasing), volume spikes
3. **Volatility** — ATR relative to price, Bollinger bandwidth, squeeze detection
4. **Spread** — Bid-ask spread in bps (inverse: tight spread = high score = liquid)
5. **Signals** — Number and quality of signals from existing modules firing on this coin
6. **Regime** — Alignment with market regime (bull coins score higher in bull regime)

Weights (configurable):
```python
WEIGHTS = {
    "momentum": 0.25,
    "volume": 0.25,
    "volatility": 0.15,
    "spread": 0.15,
    "signals": 0.10,
    "regime": 0.10,
}
```

## Collector Script: `coin_tracker.py`

Single script, runs every 60s (systemd timer or called from pipeline).

### Flow

```
1. Read hl_cache.json (allMids + meta) — already fetched by price_collector
2. Read candles.db for active tokens — already populated
3. For each coin in universe:
   a. Compute spread (bid/ask from allMids or last trade)
   b. Pull latest candle data (vol, OHLC)
   c. Compute indicators (RSI, MACD, EMA, ATR)
   d. Determine health state from composite score
   e. Write event to coin_{SYMBOL} table
   f. Update _coin_registry
4. Write agg_scores table (all coins, sorted by composite)
5. Prune old events (keep 30 days per coin, configurable)
```

### Integration with Existing Pipeline

- **Reads from**: `hl_cache.json` (allMids), `candles.db`, `signals_hermes.db` (existing signals)
- **Writes to**: `coin_tracker.db` (new)
- **No API calls** — all data already available locally
- **Called from**: `run_pipeline.py` (add as step 0, before signal generation)

### Dashboard: `coin_tracker.html`

Replace static `coins.html` with feature-rich live dashboard.

#### Layout
- **Header**: Total coins tracked, market health distribution (pie/bar), last updated timestamp
- **Filter bar**: Health state filter (dead/cold/warm/hot/setup/ready), sort by score/volume/change, search by symbol
- **Coin grid**: Card-based layout, each card = one coin

#### Per-Coin Card
Each coin card contains:
- **Symbol + name** (top left)
- **Health badge** (top right) — color-coded pill: dead=gray, cold=blue, warm=yellow, hot=orange, setup=purple, ready=green
- **Composite score** — large number, color matches health
- **Mini price chart** — 24h sparkline (SVG canvas, ~200x60px)
  - Price line with gradient fill
  - Signal markers overlaid on chart: triangles (▲/▼) at signal fire points, color = direction (green=long, red=short)
  - Health state transitions shown as background color bands
  - Volume bars at bottom of chart (subtle, semi-transparent)
- **Key stats row**: Price, 24h change%, volume, spread bps
- **Signal summary**: Last 3 signals with timestamps, type, confidence
- **Expandable detail** (click card): Full event history table, indicator timeline, regime log

#### Chart Tech
- Pure SVG/Canvas — no charting library (vanilla JS, single HTML file)
- Data from `/api/coin_tracker/coins/{symbol}` endpoint OR embedded JSON blob from `coin_tracker.db`
- 24h lookback, 1-minute resolution = 1440 data points max per chart
- Signal markers: positioned at exact timestamp, tooltip on hover showing signal details

#### Visual Design
- Dark theme (matches existing `coins.html` / `trades.html`)
- Health badge colors: dead=#484f58, cold=#388bfd, warm=#d29922, hot=#f0883e, setup=#a371f7, ready=#3fb950
- Card borders: subtle glow matching health color
- Responsive: 4 cards/row on desktop, 2 on tablet, 1 on mobile
- Auto-refresh every 60s (smooth transition, no flash)

## File Plan

| File | Purpose |
|------|---------|
| `scripts/coin_tracker.py` | Main collector — runs every 60s |
| `scripts/coin_tracker_schema.py` | DB init and schema management |
| `scripts/coin_tracker_score.py` | Scoring engine (importable by other scripts) |
| `scripts/coin_tracker_api.py` | JSON API for dashboard (reads coin_tracker.db, serves to HTML) |
| `data/coin_tracker.db` | The mega DB |
| `web/coin_tracker.html` | Live dashboard with mini charts |
| `data/coin_tracker_state.json` | Runtime state (for debug) |

## Phase 1 Scope

1. ✅ Create `coin_tracker_schema.py` — DB init, per-coin table creation
2. ✅ Create `coin_tracker.py` — Collector that reads allMids + candles, writes per-coin events
3. ✅ Create `coin_tracker_score.py` — Scoring engine, composite score computation
4. ✅ Add to `run_pipeline.py` as step 0
5. ✅ Basic dashboard (`coin_tracker.html`) — live view of all coins sorted by score
6. ✅ Systemd timer for 60s cycle (or integrate into existing pipeline)

## Phase 2 (Future)

- Signal integration: pipe `agg_scores` into signal generation
- Pattern detection: auto-detect accumulation/distribution patterns
- Historical analysis: per-coin win rate tracking
- Alerting: notify when coins hit "ready" state

## Anti-Fakeout Measures

1. **Volume confirmation** — No health upgrade without volume supporting it
2. **Spread filter** — Coins with wide spreads (low liquidity) get penalized
3. **Multi-timeframe** — Score requires agreement across 1m, 5m, 15m timeframes
4. **Regime gate** — Bull signals in bear regime are suppressed
5. **Decay** — Scores decay over time without fresh confirmation
6. **Min activity threshold** — Coins below minimum volume/spread thresholds are auto-marked "cold"
