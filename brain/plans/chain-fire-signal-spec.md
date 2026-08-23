# Chain Fire Signal — Spec

**Created:** 2026-08-23
**Status:** SPEC
**Owner:** T (CEO)

---

## What This Is

A signal that fires on a **follower token** when a **leader token** fires with a high-confidence chain. The correlation engine already knows which tokens pump together — this signal acts on that knowledge in real-time.

**Example:** ASTER fires → correlation engine says 2Z follows with 100% WR → chain_fire fires on 2Z → trades it.

---

## Architecture

```
Any signal fires on Token A (ASTER)
    │
    ▼
chain_fire.scan() runs every pipeline cycle
    │
    ├─► Check: what signals fired recently? (last 30min)
    │     → queries signal_outcomes or active signals table
    │
    ├─► For each recently-fired leader token:
    │     → correlation_engine.next_tokens(leader, k=5)
    │     → filters: lift > 1.5, confidence > 0.60, co_fires >= 5
    │
    ├─► For each qualifying follower token:
    │     → Check cooldown (not already signaled recently)
    │     → Check blacklist
    │     → Check volatility gate
    │
    └─► Fire signal on follower token
          → source = "chain_fire+"
          → confidence = correlation confidence × 88 (scaled to Hermes range)
          → value = lift ratio (for scoring)
```

---

## Data Flow

### Input: Which tokens just fired?

Two approaches:

**Option A: Query `signal_outcomes` (recommended)**
```sql
SELECT DISTINCT token, direction, signal_type, created_at
FROM signal_outcomes
WHERE created_at > datetime('now', '-30 minutes')
  AND is_win IS NOT NULL  -- only closed trades
ORDER BY created_at DESC
```

**Option B: Query `signals` table (active signals)**
```sql
SELECT DISTINCT token, direction, source, created_at
FROM signals
WHERE created_at > datetime('now', '-30 minutes')
  AND status != 'SKIPPED'
```

Option A is better — we want signals that actually EXECUTED (trades that closed), not just signals that were generated. A signal that got filtered by context gate shouldn't trigger chain suggestions.

### Processing: Correlation lookup

```python
from correlation_engine import CorrelationEngine

engine = CorrelationEngine()

for leader_token, direction in recently_fired_tokens:
    chains = engine.next_tokens(leader_token, k=5)
    
    for chain in chains:
        follower = chain['token_b']
        lift = chain['lift']
        conf = chain['confidence']
        n = chain['co_fires']
        wr = chain['win_rate']
        
        # Filter: must meet minimum thresholds
        if lift < MIN_LIFT:
            continue
        if conf < MIN_CONFIDENCE:
            continue
        if n < MIN_CO_FIRES:
            continue
        
        # Fire signal on follower
        add_signal(
            token=follower,
            direction=direction,  # same direction as leader
            signal_type='chain_fire_long' or 'chain_fire_short',
            source='chain_fire+',
            confidence=compute_confidence(conf, lift, n),
            value=lift,
            price=get_latest_price(follower),
        )
```

### Output: Signal on follower token

The signal enters the normal pipeline:
```
chain_fire.py → add_signal() → signal_compactor → hotset → decider_run → brain → HL
```

---

## Confidence Calculation

The correlation engine returns Bayesian confidence (0.0-1.0). We need to scale this to Hermes confidence (50-88).

```python
def compute_confidence(chain_conf, lift, n):
    """
    Scale chain data to Hermes confidence range.
    
    Base: 75 (neutral — chain suggests but doesn't guarantee)
    Boost: up to +13 based on lift and sample size
    Cap: 88 (system ceiling)
    Floor: 65 (minimum for chain signals — must have some evidence)
    """
    base = 75
    
    # Lift bonus: 1.5x → +3, 2.0x → +6, 3.0x → +10
    lift_bonus = min(10, int((lift - 1.0) * 10))
    
    # Sample size bonus: n=5 → +0, n=10 → +3, n=20 → +6
    sample_bonus = min(6, int((n - 5) * 0.4))
    
    # Chain confidence bonus: 0.6 → +0, 0.8 → +3, 0.9+ → +5
    conf_bonus = min(5, int((chain_conf - 0.6) * 12.5))
    
    raw = base + lift_bonus + sample_bonus + conf_bonus
    return max(65, min(88, raw))
```

Examples:
| Chain | lift | n | conf | → confidence |
|-------|------|---|------|-------------|
| ASTER→2Z | 1.8x | 7 | 0.67 | 75 + 8 + 1 + 1 = 85 |
| ME→GRIFFAIN | 1.8x | 14 | 0.71 | 75 + 8 + 4 + 1 = 88 (capped) |
| MON→DASH | 2.6x | 3 | 0.62 | 75 + 16 → 88 (capped, but n<5 so filtered) |
| FET→ASTER | 1.9x | 11 | 0.67 | 75 + 9 + 2 + 1 = 87 |

---

## Guard Rails

### 1. Cooldown per follower

After chain_fire fires on a token, cooldown for 4 hours. Don't spam the same follower.

```python
if get_cooldown(follower, direction='LONG'):
    continue  # already signaled recently
set_cooldown(follower, direction='LONG', hours=4)
```

### 2. Leader must be "hot"

The leader token must have fired RECENTLY (within 30min). Old leader signals don't count.

```python
leader_age = (now - leader_fired_at).total_seconds()
if leader_age > MAX_LEADER_AGE_SECS:
    continue  # stale leader
```

### 3. Chain freshness

The chain must have been seen recently (within 60 days). Old chains from May might not hold.

```python
from correlation_engine import CorrelationEngine
engine = CorrelationEngine()
# next_tokens already filters by recency via decay
```

### 4. Blacklist

Follower token must not be blacklisted.

```python
if follower in LONG_BLACKLIST or follower in SHORT_BLACKLIST:
    continue
```

### 5. Volatility gate

Follower token must pass the volatility gate.

```python
from volatility_gate import should_trade
vol_result, _ = should_trade(follower)
if vol_result == 'SKIP':
    continue
```

### 6. No self-referential chains

Don't fire on the leader token itself.

```python
if follower == leader_token:
    continue
```

### 7. Max chain suggestions per cycle

Cap at 3 chain signals per pipeline cycle to avoid flooding.

```python
if chain_signals_fired >= 3:
    break
```

---

## File Structure

### Signal script: `signals/chain_fire.py`

```python
#!/usr/bin/env python3
"""chain_fire — Fire on follower tokens when leader tokens pump."""
import sys, os, sqlite3
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal, get_cooldown, set_cooldown, price_age_minutes
from paths import HERMES_DATA

from hermes_constants import (
    CHAIN_FIRE_ENABLED,
    CHAIN_FIRE_PLUS_ENABLED,
    CHAIN_FIRE_MINUS_ENABLED,
    CHAIN_FIRE_MIN_LIFT,
    CHAIN_FIRE_MIN_CONFIDENCE,
    CHAIN_FIRE_MIN_CO_FIRES,
    CHAIN_FIRE_MAX_LEADER_AGE_SECS,
    CHAIN_FIRE_COOLDOWN_HOURS,
    CHAIN_FIRE_MAX_PER_CYCLE,
    LONG_BLACKLIST, SHORT_BLACKLIST,
)

SIGNAL_TYPE_LONG  = 'chain_fire_long'
SIGNAL_TYPE_SHORT = 'chain_fire_short'
SOURCE_LONG       = 'chain_fire+'
SOURCE_SHORT      = 'chain_fire-'

_SIGNALS_DB = os.path.join(HERMES_DATA, 'signals_hermes_runtime.db')


def _get_recent_leaders():
    """Get tokens that had signals fire in the last 30 minutes."""
    try:
        conn = sqlite3.connect(f"file:{_SIGNALS_DB}?mode=ro", uri=True, timeout=5)
        try:
            cutoff = (datetime.now(timezone.utc) - timedelta(
                seconds=CHAIN_FIRE_MAX_LEADER_AGE_SECS
            )).isoformat()
            
            rows = conn.execute("""
                SELECT DISTINCT token, direction, created_at
                FROM signal_outcomes
                WHERE created_at > ?
                  AND is_win IS NOT NULL
                ORDER BY created_at DESC
            """, (cutoff,)).fetchall()
            
            return [(r[0], r[1], r[2]) for r in rows]
        finally:
            conn.close()
    except Exception:
        return []


def scan_signals():
    """Main scan: check recent leaders, fire on qualifying followers."""
    from correlation_engine import CorrelationEngine
    
    if not CHAIN_FIRE_ENABLED:
        return 0
    
    engine = CorrelationEngine()
    leaders = _get_recent_leaders()
    
    if not leaders:
        return 0
    
    added = 0
    for leader_token, direction, fired_at in leaders:
        if added >= CHAIN_FIRE_MAX_PER_CYCLE:
            break
        
        # Get chain suggestions
        chains = engine.next_tokens(leader_token, k=5)
        
        for chain in chains:
            if added >= CHAIN_FIRE_MAX_PER_CYCLE:
                break
            
            follower = chain['token_b']
            lift = chain['lift']
            conf = chain['confidence']
            n = chain['co_fires']
            wr = chain['win_rate']
            
            # Skip self-referential
            if follower == leader_token:
                continue
            
            # Filter by thresholds
            if lift < CHAIN_FIRE_MIN_LIFT:
                continue
            if conf < CHAIN_FIRE_MIN_CONFIDENCE:
                continue
            if n < CHAIN_FIRE_MIN_CO_FIRES:
                continue
            
            # Direction check
            if direction == 'LONG' and not CHAIN_FIRE_PLUS_ENABLED:
                continue
            if direction == 'SHORT' and not CHAIN_FIRE_MINUS_ENABLED:
                continue
            
            # Blacklist
            if direction == 'LONG' and follower in LONG_BLACKLIST:
                continue
            if direction == 'SHORT' and follower in SHORT_BLACKLIST:
                continue
            
            # Cooldown
            if get_cooldown(follower, direction=direction):
                continue
            
            # Price freshness
            if price_age_minutes(follower) > 10:
                continue
            
            # Get price
            from signal_schema import get_all_latest_prices
            prices = get_all_latest_prices()
            if follower not in prices:
                continue
            price = prices[follower]['price']
            
            # Compute confidence
            confidence = _compute_confidence(conf, lift, n)
            
            # Fire
            sig_type = SIGNAL_TYPE_LONG if direction == 'LONG' else SIGNAL_TYPE_SHORT
            source = SOURCE_LONG if direction == 'LONG' else SOURCE_SHORT
            
            sid = add_signal(
                token=follower,
                direction=direction,
                signal_type=sig_type,
                source=source,
                confidence=confidence,
                value=lift,
                price=price,
                exchange='hyperliquid',
                timeframe='5m',
            )
            
            if sid:
                added += 1
                set_cooldown(follower, direction, hours=CHAIN_FIRE_COOLDOWN_HOURS)
                print(f"  [CHAIN-FIRE] {leader_token} → {follower} "
                      f"(lift={lift:.1f}x, wr={wr:.0%}, n={n}, conf={confidence})")
    
    return added


def _compute_confidence(chain_conf, lift, n):
    """Scale chain data to Hermes confidence range."""
    base = 75
    lift_bonus = min(10, int((lift - 1.0) * 10))
    sample_bonus = min(6, max(0, int((n - 5) * 0.4)))
    conf_bonus = min(5, max(0, int((chain_conf - 0.6) * 12.5)))
    raw = base + lift_bonus + sample_bonus + conf_bonus
    return max(65, min(88, raw))


def run():
    return scan_signals()
```

---

## Constants (hermes_constants.py)

```python
# ── Chain Fire Signal ─────────────────────────────────────────────────────
# chain_fire.py — Fire on follower tokens when leader tokens pump
CHAIN_FIRE_ENABLED = True                # master kill-switch
CHAIN_FIRE_PLUS_ENABLED = True           # LONG direction
CHAIN_FIRE_MINUS_ENABLED = True          # SHORT direction
CHAIN_FIRE_MIN_LIFT = 1.5               # minimum lift ratio (chain must be 50%+ better than base)
CHAIN_FIRE_MIN_CONFIDENCE = 0.60         # minimum Bayesian confidence
CHAIN_FIRE_MIN_CO_FIRES = 5             # minimum historical co-firings
CHAIN_FIRE_MAX_LEADER_AGE_SECS = 1800    # leader must have fired within 30min
CHAIN_FIRE_COOLDOWN_HOURS = 4           # per-follower cooldown after chain fire
CHAIN_FIRE_MAX_PER_CYCLE = 3            # max chain signals per pipeline run
CHAIN_FIRE_CONF_BASE = 75               # base confidence
CHAIN_FIRE_CONF_FLOOR = 65              # min confidence
CHAIN_FIRE_CONF_CAP = 88                # max confidence
```

---

## Registry (signals/__init__.py)

```python
# Import flags
from hermes_constants import (
    CHAIN_FIRE_ENABLED, CHAIN_FIRE_PLUS_ENABLED, CHAIN_FIRE_MINUS_ENABLED,
)

# Import run function
try:
    from signals.chain_fire import run as _chain_fire_run
except Exception:
    _chain_fire_run = None

# Registry entry
{'name': 'chain_fire', 'enabled': CHAIN_FIRE_ENABLED, 'run': _chain_fire_run},
```

---

## Layer 2 (signal_schema.py)

```python
# chain_fire
if _comp == 'chain_fire':
    try:
        from hermes_constants import CHAIN_FIRE_ENABLED
        if not CHAIN_FIRE_ENABLED:
            return None
    except ImportError:
        pass
if _comp == 'chain_fire+':
    try:
        from hermes_constants import CHAIN_FIRE_PLUS_ENABLED
        if not CHAIN_FIRE_PLUS_ENABLED:
            return None
    except ImportError:
        pass
if _comp == 'chain_fire-':
    try:
        from hermes_constants import CHAIN_FIRE_MINUS_ENABLED
        if not CHAIN_FIRE_MINUS_ENABLED:
            return None
    except ImportError:
        pass
```

---

## Compactor Weight (signal_compactor.py)

```python
('chain_fire_long', 'chain_fire+'):   1.2,  # slightly boosted — data-driven signal
('chain_fire_short', 'chain_fire-'):  1.2,
```

---

## Expected Impact

| Metric | Estimate |
|--------|----------|
| Signals per day | 5-15 (depends on how many leaders fire) |
| Chain quality | lift > 1.5x, WR > 65% (filtered by thresholds) |
| New trade opportunities | Tokens that wouldn't have been traded otherwise |
| Latency | <100ms (correlation engine query is fast) |

### Example scenario

```
09:00 — ASTER gets accel-300-,rs-s-broken signal (SHORT)
09:05 — chain_fire scans, finds ASTER fired
09:05 — correlation_engine.next_tokens("ASTER") → [2Z: 100% WR, 1.8x lift, n=7]
09:05 — chain_fire fires on 2Z: source="chain_fire-", confidence=85
09:10 — signal_compactor scores 2Z chain_fire
09:10 — if approved → decider_run → brain → HL opens SHORT on 2Z
09:30 — 2Z hits TP → +1.5% profit (as predicted by correlation engine)
```

---

## Risks

| Risk | Mitigation |
|------|-----------|
| Chains from historical data don't hold live | Half-life decay keeps chains fresh; min_n=5 ensures statistical significance |
| Too many signals flood the pipeline | MAX_PER_CYCLE=3 cap; cooldown prevents spam |
| Correlation engine not yet populated | Runs after ingest_all; chains grow over time via continuous ingestion |
| Direction mismatch (leader SHORT, follower should LONG) | Uses same direction as leader — pump chains are direction-correlated |
| Stale leader signals trigger false chains | MAX_LEADER_AGE_SECS=1800 limits to 30min window |

---

## Implementation Order

| Step | File | What |
|------|------|------|
| 1 | `signals/chain_fire.py` | Signal script |
| 2 | `hermes_constants.py` | Constants |
| 3 | `signals/__init__.py` | Registry |
| 4 | `signal_schema.py` | Layer 2 |
| 5 | `signal_compactor.py` | Source weight |
| 6 | bug_hunter | Verify all files |
| 7 | Test | Dry run + verify logs |
| 8 | Commit | Push |

---

## Success Criteria

1. Signal fires on at least 1 follower per day when leaders fire
2. Chain signals have lift > 1.5x in live trading
3. No false positives from stale chains
4. No pipeline flooding (max 3 per cycle)
5. All guard rails working (cooldown, blacklist, volatility)
