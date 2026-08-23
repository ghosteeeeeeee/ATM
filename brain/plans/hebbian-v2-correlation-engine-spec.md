# Hebbian V2 — Correlation Engine Spec

**Created:** 2026-08-23
**Status:** SPEC
**Owner:** T (CEO), implementation via subagents

---

## What This Is

A real-time correlation engine that learns **which tokens pump together and in what order** from actual trade outcomes. Not text mining. Not co-occurrence from session logs. Real statistical associations from the trade log.

**The core insight:** When DOGE fires a signal, PUMP would also be a good trade — because tokens correlate in their pump timing. The system should learn these chains automatically.

**Proof this works** (from analysis of existing 3,773 trades):

| Chain | n | B Win Rate | B Avg PnL |
|-------|---|------------|-----------|
| ASTER → 2Z | 7 | 100.0% | +1.504% |
| AXS → 0G | 8 | 87.5% | +0.509% |
| LINK → ME | 8 | 87.5% | +0.711% |
| ME → GRIFFAIN | 14 | 85.7% | +0.935% |
| 2Z → BLUR | 7 | 85.7% | +0.715% |
| FET → ASTER | 11 | 81.8% | +0.779% |

**Inverse chains (avoid these):**

| Chain | n | B Win Rate | B Avg PnL |
|-------|---|------------|-----------|
| LINK → BCH | 6 | 0.0% | -0.989% |
| ADA → BCH | 6 | 0.0% | -1.179% |
| BLUR → PEOPLE | 6 | 0.0% | -0.390% |
| FET → ZK | 8 | 12.5% | -0.251% |
| TAO → BSV | 6 | 16.7% | -0.416% |

---

## Architecture

### Data Flow

```
trade closes (won/lost, pnl)
    │
    ▼
correlation_engine.ingest(trade)
    │
    ├─► token_token_matrix  (which tokens co-fire and in what order)
    ├─► signal_token_matrix (which signals work for which tokens)
    ├─► signal_signal_matrix (which signals fire together)
    └─► cadence_patterns    (when each token is active)
    │
    ▼
correlation_engine.query(token="DOGE")
    │
    ├─► returns: correlated tokens, expected win rate, confidence
    ├─► returns: "PUMP fires next" with probability
    └─► returns: signal effectiveness for this token
```

### Three Association Types

#### 1. Token-Token Sequential Chains (the killer feature)

**What it learns:** "After DOGE fires, PUMP tends to fire within 30 minutes with 80% win rate."

**How it's computed:**
- Window: 30 minutes (configurable)
- Direction: ordered (A→B is different from B→A)
- Minimum sample size: 5 co-firings to be significant
- Decays: old correlations lose weight (half-life: 14 days)

**Key metrics per pair (A→B):**
```
co_fires:        int     # how many times A fired then B fired within window
b_total:         int     # total times B traded (regardless of A)
b_wins_after_a:  int     # times B won when A fired first
b_pnl_after_a:   float   # total PnL of B trades after A fired
win_rate:        float   # b_wins_after_a / co_fires
lift:            float   # win_rate vs B's base win rate (is A actually predictive?)
confidence:      float   # Bayesian estimate (shrinks toward base rate for small n)
```

**Confidence calculation (Bayesian):**
```python
def confidence(n, observed_wr, prior_wr=0.50, prior_weight=10):
    """Shrink toward prior for small samples."""
    return (prior_weight * prior_wr + n * observed_wr) / (prior_weight + n)
```

**Decay:** Weight *= 0.95 per day since last co-fire. Old patterns fade, recent ones dominate.

#### 2. Signal-Token Effectiveness

**What it learns:** "hl_copy_trader on SOL = 60% win rate, accel-300-,rs-s-broken on BLUR = 63% win rate."

**Already partially exists** in the trade_log but needs proper matrix storage with decay and confidence.

**Metrics:**
```
token:           str
signal:          str
direction:       str
trades:          int
wins:            int
total_pnl:       float
win_rate:        float
avg_pnl:         float
last_seen:       timestamp
confidence:      float   # Bayesian shrunk estimate
```

#### 3. Signal-Signal Co-occurrence

**What it learns:** "When hl_copy_trader fires, accel-300-,rs-s-broken usually fires too (within same window)."

**Less critical** than token-token but useful for understanding signal clusters.

---

## Database Schema

**File:** `/root/.hermes/brain/correlations.db` (new file, not the old associative_memory.db)

### Table: `token_chains`

The core table. Every row = "when A fires, B follows with X probability."

```sql
CREATE TABLE token_chains (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_a TEXT NOT NULL,           -- fires first
    token_b TEXT NOT NULL,           -- fires second
    window_secs INTEGER DEFAULT 1800, -- observation window
    
    -- Raw counts
    co_fires INTEGER DEFAULT 0,      -- A fired, then B fired within window
    b_total INTEGER DEFAULT 0,       -- B's total trades (for base rate)
    b_wins_after_a INTEGER DEFAULT 0, -- B's wins when A fired first
    b_losses_after_a INTEGER DEFAULT 0,
    b_pnl_after_a REAL DEFAULT 0.0,
    
    -- Derived (updated on each ingest)
    win_rate REAL DEFAULT 0.0,       -- b_wins_after_a / co_fires
    base_wr REAL DEFAULT 0.0,        -- B's overall win rate (for lift calc)
    lift REAL DEFAULT 0.0,           -- win_rate / base_wr
    confidence REAL DEFAULT 0.0,     -- Bayesian shrunk estimate
    avg_pnl_after_a REAL DEFAULT 0.0,
    
    -- Temporal
    first_seen TIMESTAMP,
    last_seen TIMESTAMP,
    half_life_weight REAL DEFAULT 1.0, -- decay factor
    
    UNIQUE(token_a, token_b, window_secs)
);

CREATE INDEX idx_chain_a ON token_chains(token_a);
CREATE INDEX idx_chain_b ON token_chains(token_b);
CREATE INDEX idx_chain_lift ON token_chains(lift DESC);
CREATE INDEX idx_chain_conf ON token_chains(confidence DESC);
```

### Table: `signal_effectiveness`

Per token + signal + direction performance.

```sql
CREATE TABLE signal_effectiveness (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token TEXT NOT NULL,
    signal TEXT NOT NULL,
    direction TEXT,
    
    trades INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    total_pnl REAL DEFAULT 0.0,
    
    win_rate REAL DEFAULT 0.0,
    avg_pnl REAL DEFAULT 0.0,
    confidence REAL DEFAULT 0.0,
    
    last_seen TIMESTAMP,
    
    UNIQUE(token, signal, direction)
);

CREATE INDEX idx_se_token ON signal_effectiveness(token);
CREATE INDEX idx_se_signal ON signal_effectiveness(signal);
CREATE INDEX idx_se_conf ON signal_effectiveness(confidence DESC);
```

### Table: `signal_chains`

Which signals co-occur in the same window.

```sql
CREATE TABLE signal_chains (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_a TEXT NOT NULL,
    signal_b TEXT NOT NULL,
    window_secs INTEGER DEFAULT 1800,
    
    co_fires INTEGER DEFAULT 0,
    b_total INTEGER DEFAULT 0,
    b_wins_after_a INTEGER DEFAULT 0,
    
    win_rate REAL DEFAULT 0.0,
    lift REAL DEFAULT 0.0,
    confidence REAL DEFAULT 0.0,
    
    last_seen TIMESTAMP,
    
    UNIQUE(signal_a, signal_b, window_secs)
);
```

### Table: `cadence`

Per-token timing patterns (when is this token most active?).

```sql
CREATE TABLE cadence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token TEXT UNIQUE NOT NULL,
    
    -- Hourly distribution (24 buckets)
    hour_dist TEXT,  -- JSON array of 24 floats (normalized)
    
    -- Day-of-week distribution (7 buckets)
    day_dist TEXT,   -- JSON array of 7 floats (normalized)
    
    -- Burstiness
    mean_hours_between REAL,
    burstiness REAL,   -- stdev/mean (>1 = bursty, <1 = regular)
    
    -- Stats
    total_trades INTEGER DEFAULT 0,
    peak_hour_utc INTEGER,
    peak_day TEXT,
    
    last_updated TIMESTAMP
);
```

### Table: `engine_state`

Metadata for the engine.

```sql
CREATE TABLE engine_state (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Keys: `last_ingest_time`, `total_trades_processed`, `version`

---

## Core API

### `CorrelationEngine` class

**File:** `/root/.hermes/scripts/correlation_engine.py`

```python
class CorrelationEngine:
    def __init__(self, db_path="/root/.hermes/brain/correlations.db"):
        ...
    
    # === INGESTION ===
    def ingest_trade(self, token, signal, direction, won, pnl_pct, close_time):
        """Process a single closed trade. Updates all matrices."""
        ...
    
    def ingest_all(self):
        """Bulk ingest from trade_log. Idempotent (tracks last_ingest_time)."""
        ...
    
    # === QUERIES ===
    def next_tokens(self, fired_token: str, k: int = 5) -> list[dict]:
        """Given a token just fired, what tokens come next?
        Returns: [{token, win_rate, lift, confidence, avg_pnl, co_fires}]
        """
        ...
    
    def next_signals(self, fired_token: str, k: int = 5) -> list[dict]:
        """Given a token just fired, which signals should we look for?
        Returns: [{signal, win_rate, confidence, trades}]
        """
        ...
    
    def token_correlations(self, token: str, k: int = 10) -> list[dict]:
        """All tokens correlated with this token (both directions).
        Returns: [{token, direction, win_rate, lift, confidence, avg_pnl}]
        """
        ...
    
    def signal_effectiveness(self, token: str = None, signal: str = None) -> list[dict]:
        """Look up signal performance. Filter by token and/or signal.
        Returns: [{token, signal, direction, win_rate, confidence, avg_pnl, trades}]
        """
        ...
    
    def best_signals_for_token(self, token: str, min_n: int = 3) -> list[dict]:
        """Top signals for a specific token, sorted by confidence * win_rate.
        Returns: [{signal, direction, win_rate, confidence, avg_pnl, trades}]
        """
        ...
    
    def should_trade(self, token: str, signal: str = None) -> dict:
        """Main entry point for the trading system.
        Returns: {
            'recommendation': 'TRADE' | 'AVOID' | 'NEUTRAL',
            'confidence': float,
            'reason': str,
            'chain_signals': [{token, win_rate, ...}],  # tokens that follow
            'signal_wr': float or None,
            'base_wr': float,
        }
        """
        ...
    
    # === MAINTENANCE ===
    def apply_decay(self):
        """Apply daily decay to all chains. Half-life: 14 days."""
        ...
    
    def prune(self, min_co_fires: int = 2, max_age_days: int = 60):
        """Remove chains with too few observations or too old."""
        ...
    
    def stats(self) -> dict:
        """Engine health: total chains, total signals, coverage, freshness."""
        ...
```

### Query Examples

```python
engine = CorrelationEngine()

# "DOGE just fired — what should I trade next?"
results = engine.next_tokens("DOGE")
# Returns: [
#   {token: 'PUMP', win_rate: 0.82, lift: 1.64, confidence: 0.71, avg_pnl: 0.45, co_fires: 9},
#   {token: 'FLOKI', win_rate: 0.75, lift: 1.50, confidence: 0.65, avg_pnl: 0.38, co_fires: 6},
#   ...
# ]

# "Is hl_copy_trader good for SOL?"
result = engine.signal_effectiveness(token="SOL", signal="hl_copy_trader")
# Returns: {win_rate: 0.60, confidence: 0.55, trades: 10, avg_pnl: 0.33}

# "Should I take this trade?"
rec = engine.should_trade(token="BLUR", signal="bb_bounce+")
# Returns: {
#   recommendation: 'TRADE',
#   confidence: 0.72,
#   reason: 'BLUR base WR 52%, bb_bounce+ has 57% WR (n=26), BLUR co-fires with ME (85% lift)',
#   chain_signals: [{token: 'ME', win_rate: 0.86, ...}],
#   signal_wr: 0.57,
#   base_wr: 0.52,
# }
```

---

## Integration Points

### 1. Context Gate (replaces old Hebbian gate)

**Current:** `decider_run.py` calls `hebbian_trade_boost()` which uses the old co-occurrence graph.
**New:** `decider_run.py` calls `correlation_engine.should_trade()` which uses the real correlation matrices.

```python
# In context_gate, replace hebbian lookup:
from correlation_engine import CorrelationEngine
engine = CorrelationEngine()
rec = engine.should_trade(token, signal)

if rec['recommendation'] == 'AVOID' and rec['confidence'] > 0.7:
    return ('SKIP', rec['reason'], 0)
elif rec['recommendation'] == 'TRADE' and rec['confidence'] > 0.6:
    # boost confidence
    boost_amount = int(rec['confidence'] * 10)
```

### 2. Auto-triggers (the "PUMP would be good" feature)

When a signal fires on token A, the engine can **auto-suggest** looking at token B:

```python
# After a signal fires:
chain = engine.next_tokens(fired_token, k=3)
for c in chain:
    if c['confidence'] > 0.65 and c['lift'] > 1.3:
        # Suggest: "DOGE just fired → consider PUMP (82% WR, 1.6x lift)"
        log_signal_chain(fired_token, c['token'], c['win_rate'])
```

### 3. Dashboard

New JSON endpoint: `/var/www/hermes/data/correlations.json`

```json
{
  "last_updated": "2026-08-23T16:00:00Z",
  "total_trades_analyzed": 3773,
  "top_chains": [...],
  "top_signals": [...],
  "token_performance": {...}
}
```

### 4. Favorites Integration

The favorites snapshot already computes correlations (`top_correlations`). The new engine should:
- **Import** favorites correlations as seed data
- **Override** with live trade data when available
- **Compare** price-based correlations (favorites) vs trade-based correlations (engine)

---

## Ingestion Logic

### How chains are built

```
Trade closes at T=100:
  token=SOL, signal=bb_bounce+, direction=LONG, won=True, pnl=+0.5%

  1. Update signal_effectiveness(SOL, bb_bounce+, LONG)
     - trades += 1, wins += 1, total_pnl += 0.5
     - Recompute win_rate, confidence

  2. Find all trades in window [T-1800, T] where token != SOL
     For each such trade:
       Update token_chains(other_token → SOL)
       - co_fires += 1
       - b_wins_after_a += (1 if SOL won else 0)
       - Recompute win_rate, lift, confidence

  3. Find all trades in window [T, T+1800] where token != SOL
     For each such trade:
       Update token_chains(SOL → other_token)
       - co_fires += 1  
       - b_wins_after_a += (1 if other won else 0)
       - Recompute win_rate, lift, confidence

  4. Update cadence(SOL)
     - Increment hour_dist[hour]
     - Increment day_dist[day]
     - Recompute peak_hour, peak_day, burstiness

  5. Find all signals in window [T-1800, T+1800]
     Update signal_chains for each pair
```

### Idempotency

- `ingest_all()` tracks `last_ingest_time` in `engine_state`
- On re-run, only processes trades after `last_ingest_time`
- `ingest_trade()` uses `UNIQUE` constraints + `INSERT OR REPLACE`

### Bulk Bootstrap

First run: process all 3,773 trades from trade_log.

```python
engine = CorrelationEngine()
engine.ingest_all()  # processes from start to last_ingest_time
print(engine.stats())
```

---

## Decay & Freshness

### Half-life decay

Every chain has a `half_life_weight` that decreases by factor 0.95 per day since `last_seen`.

```python
days_since = (now - last_seen).days
decay = 0.95 ** days_since
effective_weight = co_fires * decay
```

Chains with `effective_weight < 2.0` are pruned.

### Why this matters

- A chain from May (ASTER→2Z = 100% WR) might not hold in August
- Recent data dominates
- Old patterns fade unless reinforced

### Daily maintenance

```python
# Run daily via systemd timer
engine.apply_decay()
engine.prune(min_co_fires=2, max_age_days=60)
engine.stats()  # log health
```

---

## Implementation Plan

### Phase 1: Core Engine (this session)

| Step | File | What |
|------|------|------|
| 1 | `correlation_engine.py` | Full engine with ingest, query, decay, prune |
| 2 | Bootstrap script | Process all 3,773 trades from trade_log |
| 3 | Unit tests | Verify chain building, confidence, decay |

### Phase 2: Integration

| Step | File | What |
|------|------|------|
| 4 | `context_gate.py` | Replace old Hebbian with new engine |
| 5 | Auto-chain triggers | When token fires, suggest correlated tokens |
| 6 | `correlations.json` | Dashboard data endpoint |

### Phase 3: Maintenance

| Step | File | What |
|------|------|------|
| 7 | Systemd timer | Daily decay + prune |
| 8 | Continuous ingest | Trade closes → engine.ingest_trade() |

---

## Success Criteria

1. **Chain quality:** Top chains have n>=10 and lift > 1.3 (statistically meaningful)
2. **Prediction accuracy:** When engine suggests "TRADE" with confidence > 0.7, actual WR > 65%
3. **Coverage:** >80% of tokens have at least 3 chain connections
4. **Freshness:** No chain older than 60 days without reinforcement
5. **Speed:** Query returns in <10ms (SQLite index)

---

## What Gets Deleted

| Old System | New System | Action |
|------------|-----------|--------|
| `brain/associative_memory.db` (1,940 nodes, 78% noise) | `brain/correlations.db` (clean statistical matrices) | Archive old DB, keep as backup |
| `hebbian_engine.py` (35KB, co-occurrence graph) | `correlation_engine.py` (statistical correlation engine) | Keep old file, new file replaces it |
| `hebbian_entity_extractor.py` (text mining) | Not needed (trade log IS the data source) | Archive |
| `hebbian_seed_sessions.py` (session text mining) | Not needed | Archive |
| `hebbian_session_learner.py` (session learning) | Not needed | Archive |
| `hebbian_learner.py` (brain-md co-occurrence) | Not needed | Archive |
| `hebbian_session_distill.py` (never created) | Not needed | Delete plan |
| Session summaries table | Not needed for correlation engine | Keep schema, ignore |

**Old DB stays as backup** — `associative_memory.db` has trade_log + favorites_snapshots that are still useful. The new engine reads trade_log from it but writes correlations to its own DB.

---

## Risks

| Risk | Mitigation |
|------|-----------|
| Small samples create false chains | Bayesian confidence shrinks toward 50% for small n; min_n=5 for recommendations |
| Chains from May may not hold in August | Half-life decay (0.95/day); recent data dominates |
| Correlation ≠ causation | Engine doesn't claim causation; lift metric shows if A is actually predictive vs base rate |
| Processing 3,773 trades takes time | O(n²) but n is small; <30 seconds for full bootstrap |
| Old Hebbian gate is live code | Phase 2 replaces it; Phase 1 runs in parallel |
