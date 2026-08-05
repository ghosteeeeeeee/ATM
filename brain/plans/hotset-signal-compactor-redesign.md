# Hot-Set Signal Compactor Redesign

**Date:** 2026-04-26
**Status:** Design agreed, not yet implemented
**File:** `/root/.hermes/scripts/signal_compactor.py`

---

## Core Model

### Signal Entry Lifecycle

Each signal firing creates a **new DB row** (no updates to existing rows). Entries flow through states:

```
PENDING → APPROVED → (EXPIRED when staleness=0)
```

- **PENDING:** Signal fired but hasn't achieved confluence yet (waiting for 2nd source)
- **APPROVED:** Signal is in the hot-set (top-10 by score)
- **EXPIRED:** Signal left the hot-set (staleness reached 0) — NOT rejected

---

### Combo Identity

**Identical combo = token + direction + source set (order-independent)**

When multiple sources fire together for the same token+direction, they merge into one hot-set entry.

Example:
- `gap+` fires at T=0 → PENDING row (single source, waiting for confluence)
- `fast+` fires at T=4 → merged with gap+ → hot-set entry: `gap+,fast+`, rounds=1
- `gap+` fires again at T=5 (partner `fast+` silent) → new PENDING row for `gap+` alone
- If `fast+` fires at T=8 → new PENDING row for `fast+` → merged with existing `gap+` PENDING → new hot-set entry: `gap+,fast+`, rounds=2

### Rounds

**Rounds = how many consecutive cycles the IDENTICAL combo fired together.**

- New entry (first time combo fires): rounds=1
- Same combo fires together again (all sources fire within grace window): rounds = MAX(previous_rounds) + 1
- If combo goes silent for >5 min: entry dies (staleness=0). When it fires again later: rounds=1 (fresh)

**Implementation:** Track `(token, direction, frozenset(sources))` as combo identity. On each compaction cycle, check if combo exists in current hot-set → increment rounds. If not → rounds=1 (new).

---

### Staleness

**Formula:** `staleness = max(0.0, 1.0 - (now - last_signal_time) / 5)`

- `last_signal_time` = MAX(`created_at`) among ALL sources currently in the combo
- At exactly 5 min of no firing: staleness = 0.0 (entry is dead)
- Staleness resets to 1.0 ONLY when ALL sources in the combo fire together again
- Partial firing (one source fires, partner silent) does NOT reset staleness

**Critical:** Staleness is computed from the sources in the combo, NOT from the most recent PENDING signal for that token+direction.

---

## Database Schema Changes

### New Column: `combo_key`

Add to `signals` table:

```sql
ALTER TABLE signals ADD COLUMN combo_key TEXT;
```

`combo_key` = `token:direction:sorted_sources` where `sorted_sources` = `,`.join(sorted(source_set))

Examples:
- `gap+,fast+` → `DYDXXXXX:LONG:fast+,gap+` (sorted alphabetically for identity)
- `pct-hermes-,hzscore-` → `ZECXXXXX:SHORT:hzscore-,pct-hermes-`

### Column Renames / Splits

| Old Name | New Name | Purpose |
|---|---|---|
| `compact_rounds` | (keep for PENDING) | PENDING failure count — how many cycles signal tried to enter top-10 and failed |
| (new) | `survival_rounds` | APPROVED survival rounds — how many consecutive cycles identical combo fired together |

Alternative: Keep `compact_rounds` for PENDING, add `survival_rounds` for APPROVED. Both can coexist.

### Decision States

| Decision | Meaning |
|---|---|
| `PENDING` | Waiting for confluence (2+ sources) or not in top-10 |
| `APPROVED` | In hot-set (top-10) |
| `REJECTED` | PENDING for 5+ cycles without entering top-10 — **deprecated** (replaced by EXPIRED) |
| `EXPIRED` | Was APPROVED, left hot-set because staleness=0 |

---

## Hot-Set JSON Schema

File: `/var/www/hermes/data/hotset.json`

```json
{
  "compaction_cycle": 15901,
  "generated_at": "2026-04-26T19:50:00Z",
  "entries": [
    {
      "token": "ETH",
      "direction": "LONG",
      "confidence": 88,
      "final_confidence": 88,
      "source": "fast+,gap+",
      "signal_type": "deterministic",
      "z_score": 1.5,
      "combo_key": "ETH:LONG:fast+,gap+",
      "rounds": 2,
      "staleness": 0.8,
      "age_m": 1.0,
      "wave_phase": "uptrend",
      "is_overextended": false,
      "price_acceleration": 0.3,
      "momentum_score": 72.0,
      "speed_percentile": 65.0,
      "score": 94.5,
      "reason": "deterministic score=94.5 rounds=2 wave=uptrend ..."
    }
  ]
}
```

**Changes from current:**
- Remove `survival_score` (was `rounds * 0.5`, never read)
- Remove `compact_rounds` (PENDING concept, not hot-set concept)
- Add `combo_key` for identity matching across cycles
- `rounds` replaces `survival_round` (no +1 offset)
- Add `staleness` explicitly to JSON (computed per entry)

---

## Key Implementation Changes

### 1. GROUP BY Query Fix (line ~280)

**Current (broken):**
```python
SELECT token, direction, stype,
       MAX(confidence) AS confidence,
       GROUP_CONCAT(source) AS source,
       MAX(created_at) AS created_at,
       ...
FROM signals
WHERE decision = 'PENDING'
  AND created_at > datetime('now', '-5 minutes')
GROUP BY token, direction
```

**Problem:** `MAX(created_at)` and `MAX(compact_rounds)` are across ALL PENDING signals for the token+direction pair — mixing unrelated signals.

**Fix:** Keep GROUP BY but add `combo_key` to identify which sources actually belong together. Alternatively: query by `combo_key` directly.

Better approach: Pre-group by `combo_key` first, then take top entry per token+direction:

```python
SELECT token, direction, stype, confidence, source, created_at,
       combo_key, compact_rounds
FROM signals
WHERE decision = 'PENDING'
  AND created_at > datetime('now', '-5 minutes')
  AND combo_key IS NOT NULL
GROUP BY combo_key
ORDER BY confidence DESC
LIMIT 150
```

### 2. Staleness Computation

For each hot-set entry, compute staleness from MAX(created_at) of all sources in the combo:

```python
def compute_staleness(entry, current_time):
    # Parse source list from entry
    sources = [s.strip() for s in entry['source'].split(',') if s.strip()]
    # Look up MAX(created_at) across all PENDING signals for this combo_key
    # staleness = max(0, 1 - (now - last_signal_time) / 5)
    last_signal_time = get_max_created_at_for_combo(entry['combo_key'])
    age_m = (current_time - last_signal_time).total_seconds() / 60
    return max(0.0, 1.0 - (age_m * 0.2))
```

### 3. Rounds Increment Logic

On each compaction cycle:

```python
def get_combo_rounds(combo_key, current_hotset):
    """Look up if combo_key already exists in current hot-set."""
    for entry in current_hotset['entries']:
        if entry.get('combo_key') == combo_key:
            return entry.get('rounds', 0) + 1
    return 1  # New combo

# When building hot-set entry:
entry['rounds'] = get_combo_rounds(combo_key, prev_hotset)
```

### 4. PENDING → APPROVED Transition

When a combo enters top-10:

```python
# Mark all PENDING signals for this combo as APPROVED
c.execute("""
    UPDATE signals
    SET decision = 'APPROVED',
        survival_rounds = 1,
        hot_cycle_count = COALESCE(hot_cycle_count, 0) + 1,
        updated_at = CURRENT_TIMESTAMP
    WHERE combo_key = ?
      AND decision = 'PENDING'
""", (combo_key,))
```

### 5. EXPIRED vs REJECTED

**REJECTED** (line 679 `cr >= 5`): Remove this logic. PENDING signals don't get rejected — they wait for confluence.

**EXPIRED:** When an APPROVED signal leaves the hot-set (not in current top-10 and staleness=0):

```python
# Mark expired signals
c.execute("""
    UPDATE signals
    SET decision = 'EXPIRED',
        expired_at = CURRENT_TIMESTAMP,
        updated_at = CURRENT_TIMESTAMP
    WHERE decision = 'APPROVED'
      AND executed = 0
      AND token || ':' || direction NOT IN (current_hotset_keys)
      AND staleness = 0
""")
```

### 6. Opposing Signals Penalty — Updated 2026-04-27

**Any opposing signal for the same coin applies a penalty — no source-overlap check.**
This ensures counter_flip and other opposing signals can knock an original-direction combo out of the hot-set.

**Implementation:** In scoring function, check for opposing signals in the last 5 min for the same token:

```python
def _get_opposing_penalty(db_path: str, token: str, direction: str) -> float:
    """
    Check for opposing signals in the last 5 min for this token.
    ANY opposing signal — regardless of source — applies a penalty.
    Penalty: -15% per opposing source, capped at -30% total (floor 70%).
    """
    opp_direction = 'SHORT' if direction.upper() == 'LONG' else 'LONG'
    opp_sources = query_opposing_signals(token, opp_direction, window_min=5)
    if opp_sources:
        opp_source_count = sum(len(src.split(',')) for src in opp_sources)
        return max(0.70, 1.0 - (opp_source_count * 0.10))
    return 1.0
```

**Effect:** A counter_flip signal with 3 sources (e.g. `counter_flip+,counter_flip_mtf,counter_flip_macd`) hitting a LONG combo → 30% penalty → score drops from ~80 to ~56 → likely ejected from top-10 hot-set.

**Conflict guard removed (2026-04-27):** The `add_signal()` conflict guard that expired opposing signals on write is removed. Relying on signal_compactor's `opp_penalty` (-15% per opposing source, 5-min window) instead — it handles opposing signal penalization naturally in hot-set scoring. The conflict guard was causing counter_flip signals to expire each other.

---

## Files to Modify

1. **`/root/.hermes/scripts/signal_compactor.py`** — main changes
2. **`/root/.hermes/scripts/decider_run.py`** — if `survival_round` renamed to `rounds`, update sort
3. **`/var/www/hermes/data/hotset.json`** — schema update (handled by signal_compactor)
4. **`/root/.hermes/data/signals_hermes_runtime.db`** — add `combo_key` and `survival_rounds` columns

---

## Migration / Backwards Compatibility

- Add new columns as nullable (don't require existing rows to have values)
- Old `compact_rounds` column stays for PENDING tracking (no migration needed)
- `combo_key` populated on new inserts; old rows get `NULL` (handled gracefully)
- `survival_rounds` starts at `NULL` for existing APPROVED rows, populated on next cycle

---

## What Stays the Same

- GROUP BY token+direction deduplication (first past threshold wins)
- Confidence scoring and survival bonus formula
- Wave phase, speed data, regime filters
- Blacklist checking (SHORT_BLACKLIST, LONG_BLACKLIST, SIGNAL_SOURCE_BLACKLIST)
- Open position filtering
- Cascade flip eviction filtering
