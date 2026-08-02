# Surfing Signal Pipeline: Confidence Wave System

## Status: DRAFT — Discussion Outline

---

## 1. Problem Statement

The current system is **reactive** — each signal is evaluated independently against thresholds and either passes or fails. There's no concept of a signal building over time, no memory of what came before, and no staged escalation from "ripple" to "go time."

The surfing metaphor exposes this gap: real waves don't announce themselves with a siren. They build — first you see a ripple, then the water starts moving, then the swell connects. You don't paddle into a ripple.

---

## 2. Core Concept: Signal Confidence Waves

### The Three Stages

```
SIGNAL RECEIVED (any source)
        │
        ▼
┌───────────────────────────┐
│      PENDING QUEUE        │  ← "I see a wave forming"
│  confidence_building      │
│  source_count = 1         │
│  Direction confirmed?     │
│  Same source: +conf       │
│  Same dir, diff src: +conf│  ← "I'm paddling"
│  Opposite dir: -conf     │
└───────────────────────────┘
        │ 3rd signal (same coin, same dir) + conf >= threshold
        ▼
┌───────────────────────────┐
│     APPROVED QUEUE        │  ← "Wave is live — I'm riding"
│  conf >= GO_THRESHOLD     │
│  → immediately add to     │
│    hot-set                │
│  → immediately move to    │
│    EXECUTE (if slot free) │
└───────────────────────────┘
        │
        ▼
┌───────────────────────────┐
│      EXECUTE QUEUE        │  ← "Paddle, stand, go"
│  awaiting position open  │
└───────────────────────────┘
```

### Confidence Mechanics

| Event | Effect |
|---|---|
| New signal, same source + same direction as pending | `conf += 15` (reinforcement) |
| New signal, different source + same direction | `conf += 25` (confluence boost) |
| New signal, opposite direction | `conf -= 30` (wave collapsing) |
| Time decay: no new signal in 10 min | `conf -= 10` (wave passed) |
| Time decay: no new signal in 20 min | Remove from pending entirely |

**Threshold Reference:**
- `conf >= 60` → enters pending
- `conf >= 80` + 3rd same-dir signal → GO → approved + execute

---

## 3. Signal Prioritization (Wave Sequence)

Not all signals are created equal. A wave has a natural order:

### Preferred Signal Sequence (the "perfect swell")

```
STEP 1: zscore_change  (wave ripple detected)
        ↓
STEP 2: velocity       (water is moving — momentum confirmed)
        ↓
STEP 3: mtf_macd       (multiple timeframes agree — wave is real)
```

**Why this order?**
- `zscore_change`: Directional bias established (price drifting away from mean)
- `velocity`: Confirms the drift has energy (not just a static dislocation)
- `mtf_macd`: The heavy confirmation — 1h + 4h both agree

### Priority Scoring

```python
SIGNAL_PRIORITY = {
    'zscore_change':   1,   # first ripple
    'velocity':         2,   # momentum building
    'mtf_macd':         3,  # full confirmation
    'pattern_scanner':  3,  # also full confirmation
    'rsi_div':          4,  # fine-tuning entry
}
```

**A "perfect wave" is all three arriving within a 15-minute window, in order.**

If they arrive out of order (e.g., `mtf_macd` before `zscore_change`), the pending entry still fires but confidence is lower — this is a "late-starting wave" vs a "perfect sequence wave."

---

## 4. Source Diversity Bonus

Signals from **different sources** carry more weight than repeated signals from the same source.

```python
# Same source, same direction, 2nd time → +15 conf
# Different source, same direction     → +25 conf  (confluence!)
# Different source, opposite direction → -20 conf  (still lowers)
```

This rewards genuine multi-signal agreement over repeated pinging from one source.

---

## 5. Reserve Slot Policy

**Critical rule: Always keep 1 trade slot open for pending waves.**

Example with 10 max positions:
- 9 positions open → system is SCANNING only, no new entries until a slot frees
- When a position closes → pending queue immediately gets evaluated for that slot

This prevents the "wave came and I was full" problem. The surfer is always watching the lineup with one board ready.

---

## 6. Stale Pending Cleanup

```
Pending age > 20 min with no confirmation → expire pending
Pending age > 10 min, conf < 30            → expire pending
Pending age > 5 min, conf DECREASING       → flag as "dying wave"
```

---

## 7. Proposed Data Structures

### Pending Entry

```python
pending_entry = {
    "coin":            "BTC",
    "direction":       "LONG",          # or SHORT
    "regime_at_entry": "LONG",          # regime when first signal came in
    "conf":            65,              # current confidence
    "source_count":    2,               # total signals received
    "signal_sequence": ["zscore_change","velocity"],  # what we've seen
    "first_seen":      1745034567000,  # unix ms
    "last_update":     1745034892000,
    "zscore_at_entry": -1.4,           # zscore when first signal fired
    "speed_at_entry":  0.73,            # speed_percentile at first signal
}
```

### New signals_pending DB table (SQLite)

```sql
CREATE TABLE signals_pending (
    coin TEXT,
    direction TEXT,
    conf INTEGER,
    source_count INTEGER,
    signal_sequence TEXT,  -- JSON array
    first_seen INTEGER,
    last_update INTEGER,
    zscore_at_entry REAL,
    speed_at_entry REAL,
    PRIMARY KEY (coin, direction)
);
```

---

## 8. Signal Flow Changes Required

### `signal_gen.py` (no changes needed)
- Signals already written to DB with source + direction + timestamp

### `ai_decider.py` (new logic)
- On each run: check pending queue first
- Process new incoming signals against pending
- Update conf, check for GO condition
- Move approved → hot-set + execute if slot available

### `decider-run.py` (execute logic)
- Reserve slot check before executing approved signal
- If no slot, approved stays in approved queue until slot frees

### `position_manager.py` (slot freeing)
- On position close → trigger pending queue evaluation

---

## 9. Implementation Phases

### Phase 1: Infrastructure (foundational)
- [ ] Add `signals_pending` table to signals DB
- [ ] Write `pending_manager.py`: add/update/expire pending entries
- [ ] Write `pending_signal_processor.py`: confidence logic + GO detection
- [ ] Unit tests for confidence mechanics

### Phase 2: Integration
- [ ] Hook into `ai_decider.py` run loop
- [ ] Connect approved → hot-set writer
- [ ] Reserve slot logic in `decider-run.py`
- [ ] Position close → pending re-evaluation trigger

### Phase 3: Prioritization & Ordering
- [ ] Add `signal_priority` ranking in pending logic
- [ ] "Perfect sequence" detection (zscore → velocity → mtf_macd in order)
- [ ] Late-starting wave penalty (out-of-order signals)
- [ ] Time decay implementation

### Phase 4: Tuning
- [ ] Backtest confidence thresholds (60/80)
- [ ] Tune time decay windows (10/20 min)
- [ ] Tune confidence deltas (+15/+25/-30)
- [ ] Compare hit rate: perfect sequence vs any-order

---

## 10. The 3 Core Design Decisions

### D1: Time window — how long does a wave live?
If signal 1 fires at 10:00, does it still count toward a wave if signal 2 fires at 10:20? 10:45? 11:30?

- **Short (10-15 min):** Aggressive — waves must stack quickly or die. Misses slow-building waves, filters noise.
- **Long (30-45 min):** Patient — allows genuine slow swells. Risk: counter-signals arrive during window and kill valid waves.
- **Current proposal:** 20-minute window. Signal 1 starts the clock. Any confirmation within 20 min counts. After 20 min with no 3rd signal → pending dies.

### D2: Same-source repeats — do they count as new signals?
If hzscore fires 3x in 3 minutes (no other source yet), does that get us to GO?

- **No (source deduplication):** Same source within X minutes = 1 signal. Need 3 *different* sources for GO. Safer, ensures real confluence.
- **Yes (count all):** Every fire = +conf. 3 hzscore fires = GO. Faster but gaming risk.
- **Current proposal:** Same-source deduplication with 5-min cooldown. Within 5 min = same signal. After 5 min = new signal. Still need 3 total *fires* for GO but they can all be from same source.

### D3: Counter-regime signals in pending — kill the wave or penalize?
We're in SHORT regime. BTC is pending LONG. Then a SHORT signal fires for BTC.

- **Kill:** Pending resets to 0 conf or gets deleted. The regime won — don't fight it.
- **Penalize (-30 conf):** Wave weakens significantly but doesn't die. If 4th same-dir signal arrives quickly, wave still has a chance.
- **Current proposal:** Kill only if conf hasn't hit 60 yet (pre-pending). Once in pending (conf >= 60), counter-regime signals penalize but don't delete.

---

## 11. Risks

| Risk | Mitigation |
|---|---|
| 3-signal delay causes missed entries (wave passed before GO) | GO threshold is config-tunable; aggressive mode = lower threshold |
| Complex state causes bugs hard to reproduce | Pending entries fully logged; every state transition logged |
| Time zone / clock drift causes pending expiry issues | Use `time.time()` consistently, UTC everywhere |
| System restart wipes in-memory pending state | Pending persisted to SQLite on every update |
| Slot reservation causes starvation (always full) | At least 1 slot always reserved; scanning positions don't count |

---

## 12. Files Likely to Change

- `ai_decider.py` — new pending processor hook
- `decider-run.py` — reserve slot logic
- `position_manager.py` — slot-free → pending re-eval trigger
- `signal_gen.py` — likely no changes (already emits signals)
- `db_manager.py` — `signals_pending` table schema
- `pending_manager.py` — **NEW** — pending queue CRUD + confidence logic
- `pending_signal_processor.py` — **NEW** — wave detection + GO logic
- `surfing.md` — update to reflect new pipeline

---

## 13. Validation Plan

1. **Unit tests:** Confidence math, expiry logic, sequence detection
2. **Paper trade comparison:** Run 30 days of historical signals through new logic vs old; measure how many would-have-been-GO signals old system missed
3. **Simulation mode:** New `dry_run=true` flag that processes signals normally but only logs GO decisions without executing
4. **Canary test:** Run new logic in parallel with old for 1 week; compare execute rates and win rates before full cutover
