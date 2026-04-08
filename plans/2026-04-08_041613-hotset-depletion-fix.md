# Hot-Set Depletion Fix — Full Redesign

## Goal

Rebuild the hot-set pipeline to match T's original intent:
- **Signals generated in last 10 mins** → compacted by AI every 10 mins → top 20 survive
- **Hot-set is the ONLY source of trades** — highest confidence signal gets entered
- **Survival rounds** make signals stronger; reverse signals penalize and eventually evict them
- **Signals NOT in top 20** → purged (moved to rejected column)
- **No signal buildup** — only the last 10 mins matter at any given time

---

## Current Broken State — Full Root Cause Diagnosis

### The 5 bugs killing the hot-set:

**Bug 1: Compaction only scores `review_count >= 1` signals — new signals are invisible**

```python
# Line 1093 — compaction query
WHERE review_count >= 1   # ← NEW SIGNALS (rc=0) ARE SKIPPED HERE
```

New signals (just generated, `review_count=0`) are **never scored** in compaction. Their `review_count` never increments. They stay `review_count=0` until the 60-min expiry purges them. They **never enter the hot-set**.

**Bug 2: Hot-set query requires `review_count >= 1` — blocks all new signals**

```python
# Line 1369 — hot-set query
WHERE ... AND review_count >= 1   # ← rc=0 signals CANNOT enter hot-set
```

Combined with Bug 1: signals are generated, sit at `review_count=0` for up to 60 mins, never scored, never reviewed, then expire.

**Bug 3: 3-hour window in hot-set query — opposite of the 10-min design**

```python
# Line 1364 — hot-set query
WHERE created_at > datetime('now', '-3 hours')   # ← SHOULD BE -10 MINUTES
```

The hot-set is supposed to reflect the **last 10 minutes only**. The 3-hour window is the wrong direction entirely — it keeps stale signals alive when they should be purged.

**Bug 4: Signals not in top 20 are never purged — they accumulate**

The compaction marks bottom signals as `EXPIRED` but only within the 3-hour window. Signals between 3h and 24h old accumulate in the DB as `SKIPPED`/`EXPIRED`. There is **no 10-min purge** — signals from 10 minutes ago are still sitting in the DB.

**Bug 5: Confusing state machine — `review_count`, `compact_rounds`, `survival_score` all conflated**

- `review_count`: incremented when AI marks signal SKIPPED (but new signals never get here)
- `compact_rounds`: incremented in compaction for ALL signals (but new signals excluded)
- `survival_score`: computed in compaction (but new signals excluded)
- `decision`: PENDING/APPROVED/WAIT/EXPIRED/SKIPPED — semantics unclear

The system has 4 parallel tracking mechanisms doing similar things. This is over-engineered and broken.

---

## The Correct Design (per T's description)

```
Every 10 mins:
  1. PURGE: Move last cycle's signals to rejected column if not in top 20
  2. NEW SIGNALS: ~250 new signals generated (last 10 mins only)
  3. AI COMPACTION: Review all ~250 signals, rank top 20, penalize reverse signals
  4. WRITE HOT-SET: Write top 20 to hotset.json with survival_round count
  5. DECIDER-RUN: Enter trade on highest confidence signal from hot-set

Signal state machine (simplified):
  GENERATED → PENDING → APPROVED (in hot-set) → EXECUTED (trade placed)
                       → REJECTED (not in top 20, purged to rejected column)
                       → REVERSED (counter signal hit, penalized/confidence dropped)
```

---

## What Needs to Change

### Core Data Model Changes

**`signals` table — new column:**
```sql
ALTER TABLE signals ADD COLUMN rejected_at TIMESTAMP DEFAULT NULL;
-- When signal is rejected (not in top 20), mark this timestamp
-- Also move rejected signals to a rejected_at column view or separate tracking
```

**Hot-set JSON — include survival_round:**
```json
{
  "hotset": [
    {
      "token": "BTC",
      "direction": "LONG",
      "confidence": 85,
      "survival_round": 3,     // survived 3 compaction cycles
      "penalty": null,          // or "REVERSED" if counter signal hit
      ...
    }
  ],
  "timestamp": 1775620981.9,
  "compaction_cycle": 42        // monotonically increasing cycle counter
}
```

### ai_decider.py — Complete Rewrite of `_load_hot_rounds()` and Compaction

**Step 1: Purge last cycle's losers**

Before generating the new hot-set, mark signals from the **previous cycle** that weren't in the top 20 as REJECTED:

```python
# Signals that existed in the PREVIOUS hot-set but aren't in the new top 20:
# → Move to rejected (not EXPIRED, REJECTED means "ranked but not top 20")
PREV_CYCLE_THRESHOLD = 10  # minutes
c.execute("""
    UPDATE signals
    SET decision = 'REJECTED',
        rejected_at = CURRENT_TIMESTAMP,
        rejection_reason = 'not_in_top_20_compaction'
    WHERE decision = 'PENDING'
      AND created_at < datetime('now', '-10 minutes')
      AND review_count = 0
      AND token NOT IN (SELECT token FROM <new_top_20>)
""")
```

**Step 2: Get only the last 10 minutes of signals**

```python
# Hot-set query: ONLY last 10 minutes, no review_count filter
c.execute("""
    SELECT token, direction, signal_type, confidence,
           entry_price, regime, z_score_tier, z_score,
           created_at
    FROM signals
    WHERE decision IN ('PENDING', 'APPROVED')
      AND created_at > datetime('now', '-10 minutes')
      AND token NOT LIKE '@%'
    ORDER BY confidence DESC
    LIMIT 100   -- top 100 for AI to rank
""")
```

**Step 3: AI Compaction Prompt — Rank Top 20, Identify Reversals**

New prompt: Feed the ~100 signals from last 10 mins + the current hot-set (for survival context) into a streamlined Minimax prompt:

```
You are a crypto signal ranker. Rank the TOP 20 signals from the last 10 minutes.
Also identify any reverse signals (opposite direction to current hot-set survivors).

Signals (last 10 mins):
[SIGNALS HERE]

Current hot-set survivors (for survival context):
[HOT-SET HERE — if same token appears in both, penalize OR keep both if strong enough]

Tasks:
1. Rank top 20 signals by confidence × survival_bonus
2. If a token has BOTH LONG and SHORT in top 20 → keep only the higher confidence one
3. If a NEW signal opposes a current hot-set survivor → penalize that survivor's confidence by 20%
4. Return JSON: {"top_20": [...], "reversed": {...}}

Output format:
  RANKED: [token] [direction] [final_confidence] [survival_rounds] [reason]
  REVERSED: [token] [old_direction] → [penalty applied]
```

**Step 4: Write hot-set JSON**

```python
compaction_cycle += 1
hotset_data = {
    'hotset': top_20_signals,  # with survival_round = prev_round + 1
    'compaction_cycle': compaction_cycle,
    'timestamp': time.time()
}
with open(hotset_file, 'w') as f:
    json.dump(hotset_data, f)
```

**Step 5: Update signal decisions**

- Signals in top 20 → `decision = 'APPROVED'` (they ARE the hot-set)
- Signals not in top 20 → `decision = 'REJECTED'`, `rejected_at = NOW()`
- Survival_round: increment by 1 for survivors, reset to 1 for new entries

---

## Signal State Machine (Simplified)

| State | Meaning |
|-------|---------|
| `PENDING` | Waiting for next compaction cycle |
| `APPROVED` | In the hot-set (top 20 of last 10 mins) |
| `EXECUTED` | Trade placed on this signal |
| `REJECTED` | Not in top 20, purged to rejected column |
| `REVERSED` | Counter signal appeared, penalized out of hot-set |
| `EXPIRED` | Was PENDING, never made top 20, time ran out |

**Key rule: Only APPROVED signals can become EXECUTED trades.**

---

## Files to Change

| File | Change |
|------|--------|
| `/root/.hermes/scripts/ai_decider.py` | Complete rewrite of compaction logic, new AI prompt, simplified state machine |
| `/root/.hermes/scripts/decider-run.py` | Ensure it only reads hot-set, no DB fallback |
| `/var/www/hermes/data/hotset.json` | Add `compaction_cycle` field |
| Brain PostgreSQL `signals` table | Add `rejected_at` column, `rejection_reason` column |
| `/root/.hermes/scripts/hermes-trades-api.py` | Ensure hot-set rejection column is shown in UI |

---

## What's NOT Changing

- **Blacklist filters** — keep SHORT_BLACKLIST, LONG_BLACKLIST, Solana-only checks
- **Regime filters** — keep LONG_BIAS/SHORT_BIAS enforcement
- **Speed/momentum filters** — keep momentum > 0 requirement
- **Decider-run execution** — hot-set → trade entry flow stays the same
- **Guardian/position_manager** — no changes needed

---

## Testing Plan

1. **Dry run compaction**: `python3 /root/.hermes/scripts/ai_decider.py` → check hotset.json has 20 tokens
2. **Verify rejection**: Check signals DB has `REJECTED` entries with `rejected_at` timestamps
3. **Verify no buildup**: Run compaction 3 times, confirm signals from 30+ mins ago are gone
4. **Verify survival rounds**: Run compaction twice on same signal → confirm survival_round increments
5. **Verify reversal**: Manually create counter signal → confirm original signal penalized
6. **Pipeline test**: Full pipeline run → hot-set should be populated within 2 cycles

---

## Open Questions

1. **Purge threshold**: When is a REJECTED signal permanently deleted? (24h? 1 week?)
2. **AI prompt optimization**: Should we A/B test the prompt? (Same as we did for candle-predictor with Ollama)
3. **Hot-set size**: 20 tokens always, or can it be fewer if fewer signals qualify?
4. **Execution**: When decider-run reads hot-set, does it just take the #1 ranked signal every time? Or does it still apply additional filters?
