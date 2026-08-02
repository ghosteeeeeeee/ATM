# Plan: Replace LLM Hot-Set Compaction with Deterministic Script

## Goal

Completely remove the LLM-based hot-set compaction (`_do_compaction_llm()` in `ai_decider.py`) and replace it with a pure-Python deterministic script (`signal_compactor.py`) that produces identical output using the same signal data, scoring logic, and DB schema.

---

## What the LLM Compaction Actually Does

Understanding every step is required to replace it faithfully.

### End-to-end flow

```
signal_gen.py                    → signals DB (PENDING)
         ↓
_do_compaction_llm() [ai_decider.py, lines 1127-1858]
  1. Query: PENDING signals, last 10 min, conf≥60, not executed
  2. Pre-filter: blocklist, Solana, delisted, bare hzscore
  3. Regime cache: get_regime() per unique token
  4. Build prompt from main-prompt.md template
  5. Call MiniMax-M2 API (max_tokens=6000, temperature=0.3)
  6. Strip </think> thinking block, extract HOT-SET lines
  7. Parse Format A: "1. TOKEN | DIR | CONF=75% | ROUNDS=2 | WAVE=... | MOM=... | SPD=... | OVEREXT=... // reason"
  8. Parse Format B: "TOKEN LONG 75 reason" (legacy)
  9. Hallucination guard: token must be in valid_tokens or _hot_tokens_set
  10. Recovery: match by direction+conf if hallucinated
  11. Deduplicate by token+direction
  12. Fallback scoring (if LLM output empty): formula-based scoring
  13. Load prev hotset.json for survival_round tracking
  14. Score → rank → top 20
  15. APPROVED top-20 in DB, REJECTED others; increment compact_rounds
  16. Enrich with speed data: wave_phase, is_overextended, momentum_score, speed_percentile
  17. Safety filters on each entry: blocklist, Solana, delisted, bare hzscore
  18. Preserve previous hotset if new output empty/all-filtered
  19. Write hotset.json with FileLock, include compaction_cycle
  20. Write hotset_last_updated.json heartbeat
```

### Signal data flow

```
signals DB columns used:
  token, direction, signal_type, confidence, source, created_at,
  z_score_tier, z_score, compact_rounds, hot_cycle_count

token_speeds DB table (written by speed_tracker.py, read by compactor):
  token, speed_percentile, momentum_score, wave_phase,
  is_overextended, price_acceleration, price_velocity_5m

speed_cache.json (written by speed_tracker.py, read by compactor):
  {token: {speed_percentile, momentum_score, wave_phase,
           is_overextended, price_acceleration, ...}, ...}

prev hotset.json (read at step 13):
  {hotset: [{token, direction, survival_round, compact_rounds,
             survival_score, source, ...}], ...}
```

### Scoring formula (fallback, currently used only on LLM failure)

```python
score = confidence
  × survival_bonus    (1.0 + cr * 0.15, only if cr > 0 AND age_h < 1.0)
  × staleness_mult   (max(0, 1.0 - age_h * 0.2))
  × regime_bonus     (+15% for aligned direction in SHORT_BIAS market)
```

### Key output fields written to hotset.json

```json
{
  "hotset": [{
    "token": "HYPE",
    "direction": "LONG",
    "confidence": 75,
    "reason": "score=68.2 rounds=2 wave=building momentum=65 speed=72 overextended=false",
    "source": "hmacd-,hzscore",
    "z_score": 0.42,
    "compact_rounds": 2,
    "survival_score": 0.0,
    "survival_round": 2,
    "wave_phase": "accelerating",
    "is_overextended": false,
    "price_acceleration": 0.12,
    "momentum_score": 65.0,
    "speed_percentile": 72.0,
    "timestamp": 1744809600
  }],
  "compaction_cycle": 47,
  "timestamp": 1744809600
}
```

### Safety filters applied at write time (steps 17-18)

For each candidate entry:
- SHORT_BLACKLIST / LONG_BLACKLIST
- is_solana_only()
- is_delisted()
- source in SIGNAL_SOURCE_BLACKLIST
- bare hzscore as first component

If ALL entries fail safety OR LLM output empty:
→ preserve previous hotset entries (filtered through same safety rules)

---

## What to Keep (reuse from ai_decider.py)

| Component | Location | Purpose |
|-----------|----------|---------|
| `SHORT_BLACKLIST`, `LONG_BLACKLIST` | `hermes_constants.py` | Blocklist filter |
| `SIGNAL_SOURCE_BLACKLIST` | `hermes_constants.py` | Source blocklist |
| `is_solana_only()` | `tokens.py` | Solana-only filter |
| `is_delisted()` | `hyperliquid_exchange.py` | Delisted filter |
| `_get_source_weight()` | `ai_decider.py` lines ~324-369 | Source type multiplier |
| `get_regime()` | `ai_decider.py` lines ~1960-2015 | Per-coin regime lookup |
| `FileLock` | `hermes_file_lock.py` | Atomic hotset.json writes |
| `RUNTIME_DB`, `SIGNALS_DB` | `paths.py` | DB paths |
| `HOTSET_FILE` | `paths.py` | Output path |
| `signal_schema.mark_signal_processed()` | `signal_schema.py` | DB decision updates (reference only) |

---

## What to Remove from ai_decider.py

1. `_do_compaction_llm()` function (lines 1127–1858)
2. LLM imports: `openai`, `OpenAI` client
3. Auth loading for MiniMax token (`/root/.hermes/auth.json` → minimax credential)
4. Token budget globals: `_MAX_PROMPT_CHARS`, `_DAILY_PROMPT_BUDGET`, `_DAILY_PROMPT_USED`, `_DAILY_BUDGET_FILE`, `_check_token_budget()`, `_record_token_usage()`
5. Prompt template loading: `_prompt_path`, `main-prompt.md` template substitution
6. `speed_tracker_ai` lazy-loader and `_speed_tracker_ai` global
7. Debug temp file writes: `/tmp/llm_compaction_content.txt`
8. `broad_z_avg` undefined variable bug (line 1338 in template substitution)
9. The `get_pending_signals()` call to `_do_compaction_llm()` at line 1874

---

## Frequency: Every 5 Minutes (Changed from 10)

The compactor runs on a 5-minute schedule (was 10 minutes). This matches the guardian/position-manager cadence and makes the hot-set twice as responsive to regime changes.

### Pipeline schedule change

**File:** `/root/.hermes/scripts/run_pipeline.py`

Current:
```python
STEPS_EVERY_10M = ['ai_decider', 'strategy_optimizer', 'ab_optimizer', 'ab_learner']
```

Change to a `STEPS_EVERY_5M` list and add 5-minute timing logic:
```python
STEPS_EVERY_5M  = ['signal_compactor']  # was ai_decider (LLM compaction)
STEPS_EVERY_10M = ['strategy_optimizer', 'ab_optimizer', 'ab_learner']
```

Note: `ai_decider` in the 10-minute list is the LLM compaction step only. After this change, `ai_decider.py` no longer runs compaction — it only handles the signal generation loop (`get_pending_signals()` for `decider_run.py`). Its 10-minute registration can be removed or left as a no-op.

The `run_pipeline.py` main loop needs a 5-minute tick added:
```python
every_5  = (minute % 5 == 0)
every_10 = (minute % 10 == 0)

if every_5:
    for step in STEPS_EVERY_5M:
        run_step(step, ...)
if every_10:
    for step in STEPS_EVERY_10M:
        run_step(step, ...)
```

### Signal query window also changes to 5 minutes

The 10-minute signal query window in `_do_compaction_llm` was designed for a 10-minute cycle (to catch signals generated mid-cycle). With a 5-minute cycle, the window should be tightened to avoid including signals that are still being evaluated:

```python
# Change from:
AND created_at > datetime('now', '-10 minutes')
# To:
AND created_at > datetime('now', '-5 minutes')
```

This keeps the window consistent with the new 5-minute cycle — signals must be fresh enough to have been generated in the current cycle.

---

## New Script: `signal_compactor.py`

**File:** `/root/.hermes/scripts/signal_compactor.py`

### Interface

```bash
python3 /root/.hermes/scripts/signal_compactor.py        # normal run
python3 /root/.hermes/scripts/signal_compactor.py --dry   # dry-run (log only, no write)
python3 /root/.hermes/scripts/signal_compactor.py --verbose  # log per-signal scoring
```

### Exports

```python
def run_compaction(dry=False, verbose=False) -> dict:
    """Returns {'hotset': [...], 'compaction_cycle': N, 'approved': N, 'rejected': N}"""
```

---

### Step 1: Query signals

```python
# From signals DB — 5-minute window matching the 5-min compaction schedule
c.execute("""
    SELECT token, direction, signal_type, confidence, source, created_at,
           z_score_tier, z_score, compact_rounds, hot_cycle_count
    FROM signals
    WHERE decision = 'PENDING'
      AND executed = 0
      AND created_at > datetime('now', '-5 minutes')   # was 10 min, tightened to match 5-min cycle
      AND confidence >= 60
      AND token NOT LIKE '@%'
    ORDER BY confidence DESC
    LIMIT 150
""", ...)
```

### Step 2: Pre-filter (same as LLM version)

```python
signals = [s for s in signals if not (
    (s[1].upper() == 'SHORT' and s[0] in SHORT_BLACKLIST) or
    (s[1].upper() == 'LONG'  and s[0] in LONG_BLACKLIST) or
    is_solana_only(s[0]) or
    is_delisted(s[0]) or
    (s[4] and s[4].split(',')[0] == 'hzscore' and ',' not in s[4])  # bare hzscore
)]
```

### Step 3: Enrich with speed data

Read from `speed_cache.json` (written by `speed_tracker.py` every pipeline run):

```python
import json, os
_speed_cache_path = '/root/.hermes/data/speed_cache.json'
# {token: {speed_percentile, momentum_score, wave_phase, is_overextended, price_acceleration}, ...}
```

Read from `token_speeds` DB table as fallback if cache is missing:
```python
c.execute("SELECT token, speed_percentile, momentum_score, wave_phase, is_overextended, price_acceleration FROM token_speeds")
```

### Step 4: Per-coin regime cache

```python
_regime_cache = {token.upper(): get_regime(token) for token in unique_tokens}
# get_regime() already exists in ai_decider.py — copy it over
```

### Step 5: Load previous hotset for survival tracking

```python
prev_hotset = {}
if os.path.exists(HOTSET_FILE):
    with open(HOTSET_FILE) as f:
        _data = json.load(f)
        for s in _data.get('hotset', []):
            prev_hotset[f"{s['token']}:{s['direction']}"] = s
```

### Step 6: Score each signal

```python
def _score_signal(token, direction, conf, source, age_h, compact_rounds,
                   regime, regime_conf, speed_data, market_regime):
    # Base
    score = float(conf)

    # Survival bonus: only if survived previous cycles AND age < 1h
    survival_bonus = 1.0 + (compact_rounds * 0.15) if (compact_rounds > 0 and age_h < 1.0) else 1.0

    # Staleness penalty: -20% per hour, no floor (matches current fallback)
    staleness_mult = max(0.0, 1.0 - (age_h * 0.2))

    # Regime multiplier: +15% aligned, -30% counter-regime (matching main-prompt counter-regime penalty)
    reg_mult = 1.0
    if regime != 'NEUTRAL' and regime_conf > 0:
        if (regime == 'LONG_BIAS' and direction == 'LONG') or \
           (regime == 'SHORT_BIAS' and direction == 'SHORT'):
            reg_mult = 1.15
        elif (regime == 'LONG_BIAS' and direction == 'SHORT') or \
             (regime == 'SHORT_BIAS' and direction == 'LONG'):
            reg_mult = 0.70

    # Source weight (from _get_source_weight — already proven logic)
    source_mult = _get_source_weight(signal_type, source)

    # Speed percentile bonus: +10% if speed_percentile >= 80
    speed_mult = 1.0 + (0.10 if speed_data.get('speed_percentile', 0) >= 80 else 0)

    final_score = score * survival_bonus * staleness_mult * reg_mult * source_mult * speed_mult
    return final_score
```

### Step 7: Rank and select top 20

```python
scored.sort(key=lambda x: x['score'], reverse=True)
top20 = scored[:20]
```

### Step 8: Deduplicate by token+direction

```python
_seen = set()
_unique_top20 = []
for s in top20:
    key = f"{s['token']}:{s['direction']}"
    if key not in _seen:
        _seen.add(key)
        _unique_top20.append(s)
```

### Step 9: Determine survival_round per entry

```python
for s in _unique_top20:
    key = f"{s['token']}:{s['direction']}"
    prev = prev_hotset.get(key, {})
    s['survival_round'] = prev.get('survival_round', 0) + 1
    s['compact_rounds'] = max(prev.get('compact_rounds', 0) + 1, 1)
```

### Step 10: Build hotset entries with full schema

```python
for s in _unique_top20:
    spd = speed_cache.get(s['token'].upper(), {})
    hotset_entry = {
        'token': s['token'],
        'direction': s['direction'],
        'confidence': s['confidence'],
        'reason': f"deterministic score={s['score']:.1f} rounds={s['survival_round']} "
                  f"wave={spd.get('wave_phase','unknown')} momentum={spd.get('momentum_score','?')} "
                  f"speed={spd.get('speed_percentile','?')} overextended={spd.get('is_overextended',False)}",
        'source': s['source'],
        'z_score': s.get('z_score', 0),
        'compact_rounds': s['compact_rounds'],
        'survival_score': 0.0,
        'survival_round': s['survival_round'],
        'wave_phase': spd.get('wave_phase', 'neutral'),
        'is_overextended': spd.get('is_overextended', False),
        'price_acceleration': spd.get('price_acceleration', 0.0),
        'momentum_score': spd.get('momentum_score', 50.0),
        'speed_percentile': spd.get('speed_percentile', 50.0),
        'timestamp': time.time(),
    }
```

### Step 11: Safety filters on entries (same as LLM version)

```python
# Apply to hotset_entries before writing
hotset_final = []
for entry in hotset_entries:
    tkn, direction, src = entry['token'], entry['direction'], entry.get('source', '')
    if direction == 'SHORT' and tkn in SHORT_BLACKLIST: continue
    if direction == 'LONG' and tkn in LONG_BLACKLIST: continue
    if is_solana_only(tkn): continue
    if is_delisted(tkn): continue
    if src in SIGNAL_SOURCE_BLACKLIST: continue
    if src and src.split(',')[0] == 'hzscore' and ',' not in src: continue
    hotset_final.append(entry)
```

### Step 12: Preserve previous hotset if empty/all-filtered

```python
if not hotset_final:
    # Load prev_hotset, filter through safety rules, preserve
    # (same logic as LLM version lines 1727-1786)
```

### Step 13: Write hotset.json with FileLock

```python
_compaction_cycle = prev_cycle + 1
with FileLock('hotset_json'):
    with open(HOTSET_FILE, 'w') as f:
        json.dump({
            'hotset': hotset_final[:20],
            'compaction_cycle': _compaction_cycle,
            'timestamp': time.time()
        }, f)
```

### Step 14: Update DB decisions

```python
# APPROVED: top 20 (ids from step 1 filtered to top20 keys)
c.execute("""
    UPDATE signals
    SET decision = 'APPROVED',
        compact_rounds = COALESCE(compact_rounds, 0) + 1,
        updated_at = CURRENT_TIMESTAMP
    WHERE id IN ({ids})
""")

# REJECTED: not in top 20
c.execute("""
    UPDATE signals
    SET decision = 'REJECTED',
        rejected_at = CURRENT_TIMESTAMP,
        rejection_reason = 'hotset_compactor_not_in_top20',
        updated_at = CURRENT_TIMESTAMP
    WHERE id IN ({ids})
""")
```

### Step 15: Write heartbeat

```python
with FileLock('hotset_last_updated'):
    with open('/var/www/hermes/data/hotset_last_updated.json', 'w') as f:
        json.dump({'last_compaction_ts': time.time()}, f)
```

---

## Execution order

| # | Task | File(s) | Notes |
|---|------|---------|-------|
| 1 | Create `signal_compactor.py` | `scripts/signal_compactor.py` | Standalone, no ai_decider dependency |
| 2 | Mark `ai_decider.py` LLM compaction as `# DEFUNCT` | `scripts/ai_decider.py` | Comment out `_do_compaction_llm()` call |
| 3 | Wire `signal_compactor.py` into `run_pipeline.py` as a 5-min step | `scripts/run_pipeline.py` | New `STEPS_EVERY_5M` list |
| 4 | Run manually, verify `hotset.json` schema is correct | | |
| 5 | Deploy to pipeline, monitor 48h | | |
| 6 | Clean up `ai_decider.py` (remove LLM code after 48h verified) | `scripts/ai_decider.py` | Optional — can leave defunct code in place |
| 7 | Update `brain/trading.md` | `brain/trading.md` | |

---

## Step 1: Create `signal_compactor.py`

**File:** `/root/.hermes/scripts/signal_compactor.py`

Standalone script — no imports from `ai_decider.py`. Copies only the specific helpers it needs:
- `get_regime()` — copy the function body directly from `ai_decider.py`
- `_get_source_weight()` — copy the function body directly from `ai_decider.py`
- `SHORT_BLACKLIST`, `LONG_BLACKLIST`, `SIGNAL_SOURCE_BLACKLIST` — import from `hermes_constants.py`
- `is_solana_only()` — import from `tokens.py`
- `is_delisted()` — import from `hyperliquid_exchange.py`
- `FileLock` — import from `hermes_file_lock.py`
- `RUNTIME_DB`, `HOTSET_FILE` — import from `paths.py`

Does NOT import from `ai_decider.py` — no circular dependencies, no LLM artifacts.

---

## Step 2: Mark `ai_decider.py` LLM compaction as DEFUNCT

In `ai_decider.py`, find `get_pending_signals()` (around line 1874):

```python
# DEFUNCT 2026-04-16: LLM compaction replaced by signal_compactor.py
# _do_compaction_llm()  # commented out — left as documentation of old behavior
```

The rest of `ai_decider.py` (signal generation, pending signal queries) remains live — it still feeds `decider_run.py`.

---

## Validation Checklist

- [ ] `signal_compactor.py` standalone run produces valid `hotset.json` schema
- [ ] `hotset.json` has all required fields: token, direction, confidence, survival_round, wave_phase, momentum_score, speed_percentile, is_overextended, source, timestamp
- [ ] DB APPROVED/REJECTED decisions set correctly
- [ ] Run twice consecutively → identical output (deterministic)
- [ ] Run on empty signal DB → empty hotset `{"hotset": []}`, no crash
- [ ] Previous `hotset.json` preserved on failure (FileLock prevents corruption)
- [ ] Compaction completes in < 2 seconds (vs 30-60s for LLM)
- [ ] Speed data (`speed_percentile`, `wave_phase`, `is_overextended`) present in output
- [ ] After 48h: hotset has entries, no empty hotset stalls
- [ ] Compare: last LLM hotset vs first deterministic hotset — any tokens missing that shouldn't be?

---

## Open Questions

1. **Speed data staleness:** `speed_cache.json` is written by `speed_tracker.py` every ~1 min. If the compactor runs and the cache is > 5 min stale, should we log a warning? (Recommendation: yes, log warning but proceed with default values)

2. **Compact rounds vs hot cycle count:** The LLM version increments `compact_rounds` in the DB. The `hot_cycle_count` column also exists. Should the compactor update both, or just `compact_rounds`? (Recommendation: just `compact_rounds` — `hot_cycle_count` is managed elsewhere)

3. **Default speed values:** If a token has no entry in `speed_cache.json` or `token_speeds`, use defaults: `speed_percentile=50`, `momentum_score=50`, `wave_phase='neutral'`, `is_overextended=False`. Log in verbose mode only.
