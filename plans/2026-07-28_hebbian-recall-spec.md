# Spec: Hebbian Recall — Similar Setup Lookup at Trade Decision Time

**Date:** 2026-07-28
**Status:** ✅ PHASE 1/2 DONE — see Phase 3 spec for next steps (`plans/2026-07-29_hebbian-phase3-spec.md`)
**Inspiration:** Memory recall problem from AI Agents podcast — "agent has to know when to search its memory files"

---

## Problem

We have 2573 closed trades with full PnL outcomes, but we **never query this data before entering a new trade**. When ETH fires accel-300- SHORT at exhaustion phase with speed 88%, we don't ask:

> "Last time we saw this exact setup, what happened?"

The data exists but:
1. **Entry indicators were never recorded** — `signal_z_score`, `entry_rsi_14`, `entry_macd_hist`, `regime`, `entry_trend` are ALL empty in the trades table (2573 trades, 0 with indicator data). Only `confidence`, `signal`, `direction`, `token` are populated.
2. **brain.db has Hebbian associations** (17K nodes, 397K synapses) but contains concepts/files/tokens, not trade outcomes with market conditions.

We're trading blind to our own history.

---

## Solution

Two-phase approach:

### Phase 1: Start Recording Entry Conditions (fix the data gap)

Populate the existing empty columns in the trades table at trade entry time. The columns already exist — we just never write to them.

In `decider_run.py`, `execute_trade()` — before calling `brain.py`, capture:
- `signal_z_score` — from context gate computation (already computed)
- `signal_z_score_tier` — from hotset signal metadata
- `signal_momentum_state` — from hotset signal metadata
- `entry_rsi_14` — from signal_metadata
- `entry_macd_hist` — from signal_metadata
- `regime` — from hotset regime field
- `entry_trend` — compute from recent price direction

Most of these are already passed as CLI args to `brain.py` (`--signal-z-score`, `--signal-rsi-14`, etc.). Brain.py just isn't writing them to the DB, OR they're newer columns that were never wired up.

**Fix:** Audit the `brain.py trade add` command to ensure these fields get INSERTed into the trades table. This is a one-time fix that starts populating the dataset.

**Timeline:** Fix now, data accumulates over next 2-4 weeks.

### Phase 2: Similar Setup Lookup (the actual recall)

Once we have ~200+ trades with entry conditions recorded, add a lookup function that queries PostgreSQL for similar setups.

#### "Similar" Definition

A similar setup = same signal source + same direction + similar market conditions:

```sql
SELECT 
    COUNT(*) as n,
    AVG(CASE WHEN pnl_pct > 0 THEN 1.0 ELSE 0.0 END) as win_rate,
    AVG(pnl_pct) as avg_pnl,
    AVG(entry_rsi_14) as avg_rsi
FROM trades
WHERE close_time IS NOT NULL
    AND signal = :source        -- same signal
    AND direction = :direction   -- same direction  
    AND token = :token           -- same token (or NULL for all tokens)
    AND entry_rsi_14 BETWEEN :rsi - 10 AND :rsi + 10  -- similar RSI band
    AND signal_z_score_tier = :tier   -- same z-score tier
GROUP BY signal, direction
HAVING COUNT(*) >= 3   -- need at least 3 similar trades
```

#### Where to Call It

In the context gate, **after** the rule-based gate passes but **before** the LLM gate:

```
Signal → Hard filters → Rule-based gate → Similar setup lookup → LLM gate → Confidence check
                                       (advisory: penalize if <40% WR)
```

#### How to Use the Result

| Similar Setup WR | Action | Guardrail Type |
|:----------------:|--------|:---------------:|
| >= 50% | No penalty | — |
| 40-49% | -10 confidence (advisory) | Soft |
| 30-39% | -15 confidence (advisory) | Soft |
| <30% (n>=5) | SKIP → block | Hard |

The hard block at <30% WR with >=5 similar trades is the "coin history gate" concept applied at the **setup** level (not just coin level). This is strictly better than the existing coin history gate because it considers the specific market conditions.

#### Function Signature

```python
def similar_setup_lookup(token, source, direction, rsi, z_tier):
    """Query historical trades for similar setups. Returns (n, win_rate, avg_pnl) or None."""
    try:
        from _secrets import BRAIN_DB_DICT
        import psycopg2
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        c = conn.cursor()
        c.execute("""
            SELECT COUNT(*), 
                   AVG(CASE WHEN pnl_pct > 0 THEN 1.0 ELSE 0.0 END),
                   AVG(pnl_pct)
            FROM trades
            WHERE close_time IS NOT NULL
                AND signal = %s AND direction = %s
                AND COALESCE(token, '') = %s OR %s = ''
                AND entry_rsi_14 BETWEEN %s AND %s
        """, (source, direction, token if match_token else '', token if match_token else '',
              rsi - 10 if rsi else 0, rsi + 10 if rsi else 100))
        row = c.fetchone()
        conn.close()
        n, wr, avg_pnl = row
        if n and n >= 3:
            return (n, float(wr), float(avg_pnl))
        return None
    except Exception:
        return None
```

### Phase 2 Constraints

- **Don't block on Phase 1 data** — until we have 200+ trades with entry conditions, the lookup should fail-open (return None, no penalty)
- **PostgreSQL call cost** — one extra query per trade entry (~5ms), acceptable since we only enter 5-15 trades/day
- **Cache** — 300s TTL like the LLM gate cache, keyed on `token:source:direction:z_tier`

### New Constants

```python
SIMILAR_SETUP_LOOKUP_ENABLED = False  # enable after Phase 1 has 200+ trades
SIMILAR_SETUP_MIN_SAMPLE = 3          # need >= 3 similar trades to act
SIMILAR_SETUP_HARD_BLOCK_WR = 30       # <30% WR with >=5 similar → hard block
SIMILAR_SETUP_HARD_BLOCK_MIN_N = 5     # minimum n for hard block
SIMILAR_SETUP_PENALTY_40 = 10          # WR 40-49% → -10 confidence
SIMILAR_SETUP_PENALTY_30 = 15          # WR 30-39% → -15 confidence
```

### Implementation Timeline

| Phase | When | What | Status |
|-------|------|------|--------|
| 1a | Now | Audit `brain.py trade add` — ensure indicator fields are INSERTed | ✅ `f42cdd5` |
| 1b | Now | Fix any gaps in `decider_run.py` — ensure all `--signal-*` CLI args are passed | ✅ `f42cdd5` |
| 1c | Now | Deploy — start accumulating entry-condition data | ✅ Live |
| 2a | +2 weeks | Verify 200+ trades have entry conditions populated | ✅ 2538 trades |
| 2b | +2 weeks | Implement `similar_setup_lookup()` function | ✅ `5824e78` |
| 2c | +2 weeks | Wire into context gate (between rule-based and LLM) | ✅ `5824e78` |
| 2d | +2 weeks | Enable `SIMILAR_SETUP_LOOKUP_ENABLED = True` | ✅ Live |
| 2e | 2026-07-29 | Hebbian WR estimate from brain.db | ✅ `94ed919` |
| 3a-c | 2026-Q3 | Token sentiment, co-fire, cluster density | 📋 See `plans/2026-07-29_hebbian-phase3-spec.md` |

### Risk

- Phase 1: LOW — adding fields to existing INSERT, no logic change
- Phase 2: MEDIUM — new DB query per trade, but fail-open design means bugs don't block trades
- Key risk: Phase 1 brain.py fix doesn't record data correctly → 2 weeks of wasted accumulation. Need to verify within 24h of deployment that columns are populating.

### Files to Modify

| Phase | File | Change |
|-------|------|--------|
| 1a | `brain.py` | INSERT indicator fields into trades table |
| 1b | `decider_run.py` | Ensure all `--signal-*` CLI args are passed |
| 2b | `decider_run.py` | Add `similar_setup_lookup()` function |
| 2c | `decider_run.py` | Wire into `context_gate()` |
| 2d | `hermes_constants.py` | Add SIMILAR_SETUP_* constants |
| — | AGENTS.md | Document both phases |