---
name: hermes-signal-debugging
description: Debug and fix signal direction, hot-set entry filtering, and source weight issues in the Hermes trading system
triggers:
  - "signal direction wrong"
  - "hot-set single signal through"
  - "hzscore pct-hermes"
  - "signal combo not blocked"
  - "vel-hermes opposite signal"
  - "signal merge conflict"
  - "pct_score natural_score"
  - "z_score 0 confidence"
  - "pct_long extreme override"
  - "no signals after threshold change"
---

# Hermes Signal System Debugging

## Key Files
- `/root/.hermes/scripts/signal_gen.py` — signal generation (pct-hermes, hzscore, vel-hermes, RSI)
- `/root/.hermes/scripts/macd_rules.py` — MACD signal generation (mtf_macd, cascade)
- `/root/.hermes/scripts/ai_decider.py` — LLM compaction, SOURCE_WEIGHT_OVERRIDES, hot-set writing
- `/root/.hermes/scripts/decider_run.py` — hot-set approval, execution block
- `/root/.hermes/scripts/rsi_backtest.py` — signal quality backtest using PostgreSQL trades (run to get current numbers)
- `/root/.hermes/data/candles.db` — local OHLCV candle store (populated by price_collector)
- `/var/www/hermes/data/` — host runtime data (trades.json, hotset.json)
- Docker container `hermes-core`: `/app/hermes/data/signals_hermes_runtime.db`

## Signal Source Naming
- `source='hzscore'` — bare hzscore, combo-only, NEVER solo
- `source='hzscore,pct-hermes'` — allowed combo
- `source='hzscore,pct-hermes,vel-hermes'` — triple combo
- `source='hmacd-'` — solo momentum, not allowed

## Critical Debugging Findings

### 0. Fast-Momentum — Added speed_percentile Filter (2026-04-18)

**Symptom**: NIL fired `fast-momentum+` LONG on a flat chart (0.03829–0.03849, ±0.03% candles). Signal was a false positive on sideways noise.

**Root cause**: `_run_fast_momentum_signal()` used absolute z-score thresholds (`z_accel > 0.15`) with no check on whether the token was a universe top-mover. A flat token with tiny z-score noise could pass the acceleration threshold.

**Fix**: Added `speed_percentile >= 70` filter — only fire on tokens in universe's top 30% by velocity (Binance-style top movers):
```python
spd = speed_tracker.get_token_speed(token)
speed_pctl = spd.get('speed_percentile', 50.0) if spd else 50.0
if speed_pctl < 70:
    continue  # not a top mover — skip
```

**Current thresholds** (`signal_gen.py` `_run_fast_momentum_signal()`):
- `ACCEL_THRESHOLD = 0.15` — z_5m - z_30m must exceed ±0.15
- `MIN_CONFIDENCE = 62` — minimum confidence to write signal
- `speed_percentile >= 70` — token must be top 30% by velocity (NEW)
- RSI confirmation: LONG skips if RSI > 70, SHORT skips if RSI < 45
- MACD confirmation: LONG skips if macd_hist < 0, SHORT skips if macd_hist > 0
- 5m z must be more extreme than 60m z for true acceleration

**Source weight**: 1.3x in `SIGNAL_SOURCE_WEIGHTS` (signal_compactor.py lines 138-139)

**Trade diagnosis query:**
```bash
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT token, source, direction, confidence, decision FROM signals \
   WHERE source LIKE 'fast-momentum%' ORDER BY created_at DESC LIMIT 10;"
```

### 1. ALL signals silently failing — only pattern_scanner works (2026-04-16)

**Investigation (2026-04-18)**: Revisited and confirmed — the "only pattern_scanner appears" symptom was a **false premise**. All signal types (momentum, hzscore, velocity, fast-momentum, mtf-momentum) ARE being written to `signals_hermes_runtime.db`. The hot-set.json shows `mtf-momentum`, `hzscore-`, `fast-momentum-` entries.

**Why only 6 hot-set entries**: `signal_compactor.py` has strict confluence enforcement (≥2 distinct source components) and top-20 dedup. Most signals get merged into multi-source signals. `pattern_scanner` runs first and bypasses some filters, giving it higher visibility.

**Key insight**: Check the runtime DB first before assuming signals aren't being generated:
```bash
sqlite3 /root/.hermes/data/signals_hermes_runtime.db "SELECT source, COUNT(*) FROM signals GROUP BY source ORDER BY COUNT(*) DESC LIMIT 20;"
```

### 2. review_count=0 for ALL signals — survival bonus never applies (2026-04-18)

**Symptom**: All 28,121 signals in `signals_hermes_runtime.db` have `review_count=0`. No signal ever accumulates a survival bonus.

**Root cause**: `signal_compactor.py` APPROVED UPDATE (line ~498) was updating `compact_rounds` and `hot_cycle_count` but NOT `review_count`. The survival bonus logic requires `review_count > 0` to activate, but it was never being incremented.

**Fix** (`signal_compactor.py` ~line 501):
```python
# ADD THIS to the APPROVED UPDATE:
review_count = COALESCE(review_count, 0) + 1,
# alongside compact_rounds and hot_cycle_count updates
```

**Also**: The hot-cycle sync gap (survival_round in hotset.json but hot_cycle_count=0 in DB) was already documented above — both the DB sync and the review_count fix are needed for survival bonus to work.

### 3. Hot-set entry filter (decider_run.py ~line 1171)
**Symptom**: Only `pattern_scanner` signals appear. No mtf_macd, velocity, momentum, or confluence signals.

**Root cause — TWO independent bugs:**

**Bug A: `z_dir` undefined variable crash (signal_gen.py lines ~1066, ~1125)**
```python
# Line ~1066 — WRONG:
if z_dir != 'rising':
# FIXED TO:
if mom['z_direction'] != 'rising':

# Line ~1125 — WRONG:
elif z_dir == 'rising' and percentile_long < 40:
# FIXED TO:
elif mom['z_direction'] == 'rising' and percentile_long < 40:
```
`compute_score()` crashed on token #1 of the main loop, preventing ALL momentum, mtf_zscore, percentile_rank, velocity signals AND confluence signals from being generated.

**Bug B: 190 HL API calls per signal_gen run — rate limit cascade**
Every token loop called `is_delisted(token)` → `_get_meta()` → `_http_post()` → 1 HL API call per token. With 190 tokens × 1 call = 190 rate-limited API calls per run → most calls failed → most tokens skipped.

**Bug C: macd_rules making 570 Binance API calls per run**
`_fetch_binance_candles()` in `macd_rules.py` was calling Binance API for 3 TFs × 190 tokens = 570 calls per run. Each failing with 429 rate limits, causing cascade failures downstream.

**Fixes applied (2026-04-16):**
1. Fixed `z_dir` → `mom['z_direction']` at both locations
2. Added `_DELISTED_SET` batch loading — 1 API call at `run()` start instead of 190 per-token calls:
   ```python
   _DELISTED_SET = set(get_tradeable_tokens())  # 1 batch HL API call
   def _is_delisted_cached(token):
       return token in _DELISTED_SET  # pure set lookup, zero API calls
   ```
3. Replaced all 6 `is_delisted()` call sites with `_is_delisted_cached()`
4. Patched `macd_rules._fetch_binance_candles()` to read from `candles.db` first (zero Binance API calls), with per-token warmup calculation based on that token's MACD params

**Diagnosis command:**
```bash
cd /root/.hermes/scripts && timeout 120 python3 signal_gen.py 2>&1 | grep "DEBUG ADDED"
```
If no `DEBUG ADDED mtf_macd` or `DEBUG ADDED velocity` lines appear after pattern_scanner output → the above bugs.

### 1. Hot-set entry filter (decider_run.py ~line 1171)
Single-source signals are blocked at hot-set entry. The filter only applied inside `if sig_type == 'confluence'` block — `hzscore` with `signal_type='mtf_zscore'` bypassed it entirely.

Fix: Added explicit block:
```python
if sig_src == 'hzscore':
    log(f'  🚫 [HOT-SET] {token} {direction} BLOCKED: hzscore (combo-only, no confluence)')
    _record_hotset_failure(token, direction, failures)
    continue
```

### 2. SOURCE_WEIGHT_OVERRIDES ordering (ai_decider.py)
First-match wins. Longer prefixes must come BEFORE shorter ones:
```python
('mtf_zscore', 'hzscore,pct-hermes', 1.0),      # specific FIRST
('mtf_zscore', 'hzscore', 0.15),                # bare LAST (would shadow combos otherwise)
```

### 3. pct_score missing from natural_score — scored ETH at 20 instead of 80 (2026-04-19)
**Symptom**: ETH passed LONG with confidence 79.3 (should have been ~80+) — discovered during Option B z-score threshold tuning when ENTRY_THRESHOLD=70 produced 0 signals (correct but too aggressive).

**Root cause** (`signal_gen.py` line 1146): `natural_score` was defined as `phase_score + rsi_score` — missing `pct_score` entirely. The `pct_score` (0-60 pts potential) was computed but never added to the final score:
```python
# WRONG (line 1146):
natural_score = phase_score + rsi_score

# FIXED:
natural_score = pct_score + phase_score + rsi_score
```

**Effect**: ETH with `pct_long=20` (avg price) scored only 20 pts from pct when it should have scored ~50. This caused ENTRY_THRESHOLD=70 to reject all signals even with correct z-score floors.

**Lesson**: When tuning entry thresholds, always verify pct_score is in natural_score first — or threshold changes produce misleading 0-signal results.

### 4. pct_long phase override blocked LONG incorrectly (2026-04-19)
**Symptom**: pct_long=8 (price near highs = bad for LONG) was setting phase='extreme' which blocked LONG signals. But pct_long=8 means price at the TOP of its range = suppresssed counter-intuitively — pct_long measures % of bars BELOW current price, so 8% below means price is near the TOP (elevated), which IS correct for a LONG setup at local highs.

**Root cause** (`signal_gen.py` lines 901-919): The override logic was semantically inverted. pct_long=8 should mean "price elevated = good SHORT" but the override treated it as "extreme = bad for both directions" and blocked LONG.

**Fix**:
```python
# REMOVED pct_long <= 10 → extreme override that blocked LONG
# pct_short >= 80 → extreme override for SHORT (kept — correct semantics)
# The phase and pct_score already handle percentile scoring correctly;
# explicit overrides were fighting the natural scoring logic.
```

**Lesson**: Always verify the semantic direction of percentile measures — `pct_long` (% of bars below price) and `pct_short` (% of bars above price) have OPPOSITE meanings to what their names suggest.

### 5. Dead code in ai_decider.py
All `hmacd-*` variants are caught by SOURCE_WEIGHT_OVERRIDES entries (line 133, 141). The inline `if source.startswith('hmacd-')` block in the `else` of `_get_source_weight()` was dead code — removed.

## Signal Merge Architecture (critical for combo debugging)

Three independent signals are generated per token in `signal_gen.py` run(), then merged into ONE DB row:

| Signal | Source | Direction Logic |
|--------|--------|----------------|
| Percentile rank | `pct-hermes` | LOW pct → LONG (suppressed), HIGH → SHORT (elevated) |
| Z-score velocity | `vel-hermes` | velocity > 0 → SHORT (rising z = price reverting up), velocity < 0 → LONG (falling z = price reverting down) |
| MTF Z-score | `hzscore` | majority TFs below mean → LONG, majority above → SHORT |

**Merge in `signal_schema.py` `add_signal()` (lines 407-488):**
1. CONFLICT GUARD: Expires OPPOSITE-direction signals for same token (line 407)
2. MERGE: If same token+direction exists in last 30 min, merges sources (line 424)
3. `source` field = comma-joined: `hzscore,pct-hermes,vel-hermes`
4. `signal_types` = all contributing types
5. Confidence = MAX + merge bonuses (lines 454-472)

**Why combos flip direction:** `vel-hermes` fires on momentum reversal (z-score changing direction). `hzscore+pct-hermes` fire on mean-reversion. These can directly contradict. When vel-hermes fires SHORT while hzscore+pct are LONG, the CONFLICT GUARD sees them as different token+direction pairs — no guard fires, and the new SHORT row survives.

**`compute_score()` in `signal_gen.py` (line 863):** Computes ONE score per token+direction from CURRENT market data, not from individual source directions. The `vel_score` contribution (0-10 pts, line 1025) can override pct/hermes direction.

**Key locations:**
- `signal_gen.py` lines 1680-1760 — individual signal generation
- `signal_schema.py` lines 407-488 — CONFLICT GUARD + MERGE logic
- `signal_gen.py` lines 863-1080 — compute_score() merging all signals into one score

## SIGNAL_SOURCE_BLACKLIST — Exact String Matching Only

**Critical**: `SIGNAL_SOURCE_BLACKLIST` uses **exact string matching** in `add_signal()` (`signal_schema.py:397`). The check is `source in SIGNAL_SOURCE_BLACKLIST` — NOT prefix matching.

This means:
- `'pct-hermes'` in blacklist → blocks bare `pct-hermes` only
- `'pct-hermes+'` and `'pct-hermes-'` → NOT blocked (exact strings don't match `'pct-hermes'`)
- `'vel-hermes'` in blacklist → blocks bare `vel-hermes` only
- `'vel-hermes+'` and `'vel-hermes-'` → NOT blocked
- `'hzscore'` in blacklist → blocks bare `hzscore` only
- `'hzscore+'` and `'hzscore-'` → NOT blocked
- `'hwave'` in blacklist → blocks bare `hwave` only
- `'hwave+'` and `'hwave-'` → NOT blocked

**Current blacklist** (as of 2026-04-18):
```python
SIGNAL_SOURCE_BLACKLIST = {
    'rsi-confluence',    # 0% WR — suppress entirely
    'rsi_confluence',    # underscore variant
    'pct-hermes',        # bare = combo-only, never solo
    'vel-hermes',        # bare = solo source, no confluence
    'rsi-hermes',
    'hmacd+-', 'hmacd-+',  # MTF disagreement merge artifacts
    'conf-1s',
    # NOTE: hzscore and hwave REMOVED — compute_score never generates them bare,
    # only hzscore+/hzscore- and hwave+/hwave- (directional, not blocked)
}
```

**Component-level check** (only runs for merged/comma-separated sources):
```python
if ',' in source:
    for component in source.split(','):
        if component.strip() in SIGNAL_SOURCE_BLACKLIST:
            return None  # block if ANY component is blacklisted
```

So `hzscore,pct-hermes,vel-hermes` → `pct-hermes` and `vel-hermes` are checked individually. If either is in blacklist → blocked. Since `pct-hermes` IS in blacklist, this combo is blocked.

## Single-Source Signals — Must Stay PENDING Until Confluence

**Bug (fixed 2026-04-18)**: Single-source signals (e.g., `mtf_zscore|hzscore`, `pattern_micro_flag|pattern_scanner`) were bypassing the compactor's confluence filter because `conf_float >= 70.0` allowed them through. They reached `APPROVED` without a second source.

**Fix** (`signal_compactor.py` confluence enforcement block):
```python
# BEFORE (WRONG):
if len(source_parts) < 2 and conf_float < 70.0:
    blocked
if len(source_parts) < 2:
    allow through (high-conf bypass)  # ← BUG

# AFTER (CORRECT):
if len(source_parts) < 2:
    blocked  # NO bypass — single-source always stays PENDING
```

**Rule**: Only multi-source signals (2+ comma-separated components in `source` field) can be APPROVED. Single-source signals stay PENDING until a second source fires for the same token+direction and they merge.

**Why ai_decider is not the approval path**: The compactor's `_transition_to_approved()` writes APPROVED directly to the DB based on hot-set top-20. ai_decider.py is defunct for new approvals — the compactor is the sole gatekeeper.

## Directional Conflict Detection — Merged Sources Fighting Each Other (2026-04-18)

**Symptom**: A 3-signal confluence (`hzscore+,pct-hermes+,vel-hermes+`) fires with 95% confidence but price moves the opposite direction. Example: GAS SHORT at $1.7105 went +1.2% against the position.

**Root cause — signals measure different timeframes and contradict each other:**
- `pct-hermes-` fires on 1m/5m price uptick (correct: short-term bounce = short)
- `hzscore+` tracks 4h z-score recovery (correct: price bouncing from bottom = long)
- `vel-hermes-` catches a 1m downward velocity flicker during the bounce

These are all "correct" for their respective windows but fight each other when merged into one row.

**Fix 1 — Per-row directional conflict check** (`signal_compactor.py`):
```python
# Parse directional suffix from each source component.
# '+' = LONG, '-' = SHORT. If both polarities present, skip entirely.
long_srcs  = [p for p in source_parts if p.endswith('+')]
short_srcs = [p for p in source_parts if p.endswith('-')]
if long_srcs and short_srcs:
    log(f"  ⚔️  [CONFLICT] {token} {direction}: LONG={','.join(long_srcs)} vs SHORT={','.join(short_srcs)}, skipping")
    continue
```
This catches cases like `pct-hermes-,hzscore+` — a merged row with opposing directional sources.

**Fix 2 — Cross-direction filter** (`signal_compactor.py` Step 7b):
Safety net if both LONG and SHORT rows for the same token make it into top 20:
```python
by_token = {}
for s in top20:
    tok = s['row'][0]
    direction = s['row'][1]
    if tok not in by_token:
        by_token[tok] = []
    by_token[tok].append((direction, conf, s))

for tok, entries in by_token.items():
    dirs = [e[0] for e in entries]
    if 'LONG' in dirs and 'SHORT' in dirs:
        entries.sort(key=lambda x: x[1], reverse=True)
        winner_dir, winner_conf, winner_s = entries[0]
        loser_dir, loser_conf, loser_s = entries[1]
        log(f"  ⚔️  [CROSS-DIR CONFLICT] {tok}: kept {winner_dir}, dropped {loser_dir}")
        conflict_kills.append(loser_s)
top20 = [s for s in top20 if s not in conflict_kills]
```

**EIGEN example** — signals fighting for 90+ minutes:
```
21:51: pct-hermes- (SHORT) + hzscore+ (LONG) — CONFLICTED
22:07: vel-hermes- (SHORT) + hzscore+,pct-hermes+ (LONG) — 3-WAY FIGHT
22:11: vel-hermes- (SHORT) + pct-hermes+ (LONG) — CONFLICTED
```

**What was missing for GAS and EIGEN:**
1. **Bounce detection**: GAS bounced +1.24% on the 4h from local low — we shorted near the top of a bounce
2. **4h candle direction check**: GAS 22:00 4h candle was +1.24% (bullish) — SHORT against opposite-direction candle
3. **Same-bar conflict filter**: If SHORT and LONG fire within the same 5-min window, don't add either until resolved

**Trade diagnosis query:**
```bash
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT created_at, token, source, direction, confidence FROM signals \
   WHERE token='GAS' AND created_at > datetime('now','-3 hour') ORDER BY created_at;"
```

### 6. Z_FLOOR — z_score contributes 0 pts unless |avg_z| >= 1.5 (2026-04-19)
**Approach**: Option B for fixing weak signal combos (hzscore+,pct-hermes+ firing on mildly suppressed prices that continue down).

**Implementation** (`signal_gen.py` lines 1017-1022): Only award z_score pts when `|avg_z| >= Z_FLOOR`:
```python
Z_FLOOR = 1.5  # only award z_score pts when |avg_z| >= 1.5

# In compute_score():
if abs(avg_z) >= Z_FLOOR:
    z_contribution = min(abs(avg_z) * 20, 30)
else:
    z_contribution = 0  # no z_score pts for weak readings
```

**Effect**: BTC (avg_z=-0.43), ETH (avg_z=-0.73), SOL (avg_z=-0.19) all get 0 z_score pts — weak readings no longer inflate confidence on mediocre setups.

**Entry thresholds** used with Z_FLOOR:
- ENTRY_THRESHOLD = 55 (was 50, slightly stricter)
- SHORT_ENTRY_THRESHOLD = 60 (was 55)

**Current z-score trend thresholds** (`signal_gen.py` lines 222-232):
```
LONG_*_Z_MAX:  +0.5/+0.3/+0.5 → +1.5/+1.5/+1.5 (1h/4h/30m)
SHORT_*_Z_MAX: +2.0 → +2.5
```

**Lesson**: Raising entry thresholds without Z_FLOOR blocks everything (0 signals at ENTRY_THRESHOLD=70). Z_FLOOR filters weak z readings at the scoring level; entry threshold is a secondary gate. Run `python3 -c "from signal_gen import ..."` to verify constants after changes.

---

## SPEED_WEIGHT — Defined But Never Used in Hot-set Approval (2026-04-28)

**Symptom**: `SPEED_WEIGHT = 0.15` is set in `decider_run.py` (line 63) with a comment saying "15% of total hot-set score comes from speed percentile" — but it's **never referenced in the approval logic**.

**What actually controls hot-set approval** (lines 920-1010 of decider_run.py):
- `wave_mult` alignment multipliers (1.15 boost for wave-aligned, 0.70 penalty for counter)
- `is_overextended` hard block (|vel_5m| > 3%)
- `momentum_score` — used for tagging/logging only

**Where speed_percentile IS actually used:**
1. `signal_gen.py` — signal generation blocking (pctl < 20 blocked, pctl >= 70 gets 5% easier entry threshold)
2. `ai_decider.py` — compaction scoring (10% weight via `SPEED_COMPACTION_WEIGHT = 0.10` in speed_tracker.py)
3. `position_manager.py` — stale position exit logic

**Effect of increasing SPEED_WEIGHT**: Nothing, until it's wired into `effective_conf` calculation in `decider_run.py` around line 992. To make it active:
```python
# Around line 992 of decider_run.py — add speed boost:
speed_factor = speed_pctl / 100.0  # 0.0 to 1.0
speed_boost = speed_factor * SPEED_WEIGHT * float(sig_conf)
effective_conf = float(sig_conf) * wave_mult + speed_boost
```

**Key lesson**: A constant defined with a comment about its purpose is not the same as it being wired into the code. Always grep for actual usage of constants, not just their definition.

---

## pct-hermes Direction Semantics — CONFIRMED BROKEN (2026-04-25)

**Critical finding after backtesting across 15 tokens on 200-bar (3-day) lookback:**

| Signal | Direction | Logic | 72h Win Rate |
|--------|-----------|-------|-------------|
| `pct-hermes+` | LONG | pct_short>=72 (price suppressed → bounce) | **75-100%** across 15 tokens |
| `pct-hermes-` | SHORT | pct_long>=72 (price elevated → pull back) | **29-68%** — universally broken |
| `pct-hermes-` (FLIPPED) | LONG | pct_long>=72 (price elevated → continue UP) | **38-71%** — still weak |

**pct-hermes- is BROKEN**: pct_long>=72 fires constantly in uptrends (price is almost always near the top of a rising window). Going SHORT on that fights the trend and loses 30-70% of the time. This is the OPPOSITE of what it claims to do.

**pct-hermes+ is EXCELLENT**: pct_short>=72 (price suppressed in 3-day window → bounce) wins 75-100% at 72h across most tokens. This is the best performing signal in the system by win rate.

**Fix**: Flip pct-hermes- direction in `signal_gen.py`:
- `pct_long >= 72` → should signal LONG (momentum: elevated price continues up), NOT SHORT
- OR disable pct-hermes- entirely in `SIGNAL_SOURCE_BLACKLIST`

**Why it looked correct before**: Initial backtests used 500-bar (20-day) lookback. pct_long>=72 fires 91% of the time on BTC in a bull market — so the sample was polluted. Using ZSCORE_HISTORY=200 (3-day, matching signal_gen's actual lookback) reveals the true brokenness.

**Backtest command** (200-bar lookback, 72h horizon):
```python
# Quick 4-way test
lookback=200; horizons=[72]
for tok in [BTC,ETH,SOL,AVAX,LINK,PEOPLE,ZK,BCH,AAVE,MKR,TAO,NEAR,FTM,SUI,DOT]:
    # pct_long>=72 SHORT: universally 30-45% WR
    # pct_short>=72 LONG: 75-100% WR
```

**Also**: pct_long measures % of bars BELOW current price — pct_long=92 means price is at the TOP (elevated), not bottom. The naming is counter-intuitive. pct_long=high = price elevated = bad for LONG (original broken logic). The original pct-hermes- SHORT logic is doubly wrong: it fires constantly AND in the wrong direction.

## Scenario: Signals Generated but Rejected at Compactor (hotset_compactor_not_in_top20)

**Symptom**: A signal type IS being generated (visible in `signals_hermes_runtime.db`) but never appears in the hot-set. The compactor rejects them with `hotset_compactor_not_in_top20` or `hotset_compactor_not_in_top20_after_5_rounds`.

**Root cause**: The signal's confidence (and thus survival_score) is too low to break into the top-20, OR the signal fires frequently enough that the compactor's per-token/per-direction dedup kicks in before it can accumulate rounds.

**Diagnosis — SQL queries in order:**

```bash
# Step 1: Check decision distribution for the signal type
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT decision, COUNT(*) FROM signals WHERE source LIKE 'pct-hermes%' GROUP BY decision;"

# Example output:
# EXPIRED|2787
# PENDING|1
# REJECTED|4673
# → Most are REJECTED → investigate why

# Step 2: Check specific rejection reasons
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT rejection_reason, COUNT(*) FROM signals WHERE source LIKE 'pct-hermes%' \
   AND decision='REJECTED' GROUP BY rejection_reason ORDER BY COUNT(*) DESC;"

# Example output:
# hotset_compactor_not_in_top20|4494
# hotset_compactor_not_in_top20_after_5_rounds|179
# → Signals are firing but never reaching top-20

# Step 3: Compare confidence vs other signal types in hot-set
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT source, direction, AVG(confidence) as avg_conf, COUNT(*) as cnt \
   FROM signals WHERE decision IN ('PENDING','APPROVED','HOT') \
   AND created_at > datetime('now','-24 hours') \
   GROUP BY source, direction ORDER BY avg_conf DESC LIMIT 20;"

# Step 4: Check what's currently in the hot-set (pending/approved)
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT token, signal_type, source, decision, confidence, created_at \
   FROM signals WHERE created_at > datetime('now','-10 minutes') \
   AND decision IN ('PENDING','APPROVED') ORDER BY confidence DESC LIMIT 20;"

# Step 5: Recent pct-hermes signals — their fate
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT token, signal_type, source, decision, confidence, created_at \
   FROM signals WHERE source LIKE 'pct-hermes%' ORDER BY created_at DESC LIMIT 10;"
```

**Key insight**: `pct-hermes+` fires at exactly `PCT_RANK_THRESH=72` → minimum confidence 60 (formula: `(pct_val - 72) * 1.25 + 50` → at pct_val=72: exactly 50, capped at 60). Other signals (mtf_zscore, ma_cross_5m) fire at 70-87 confidence. The pct-hermes signals are too weak to accumulate survival_score and get filtered out by the top-20 compactor.

**Fix options:**
1. Lower `PCT_RANK_THRESH` (e.g., 68) so signals fire earlier with higher confidence
2. Boost the signal's survival_score so it competes in top-20
3. Add a merge/crossfeed so pct-hermes combines with stronger signals earlier

---

**Fix**: Add `'loss' in reason.lower()` guard in `decider_run.py` line ~672. Also clear stale cooldowns:
```bash
python3 -c "
import psycopg2
conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
cur = conn.cursor()
cur.execute(\"DELETE FROM signal_cooldowns\")
conn.commit()
print('Cleared all cooldowns')
"
```

**Key lesson**: When EVERY signal is blocked by cooldown despite no obvious loss events, check `signal_cooldowns` table directly — the cooldown flood is the most likely cause. `reason='signal'` cooldowns come from `set_cooldown()` in `decider_run.py`, NOT from `set_loss_cooldown()` (which writes to `loss_cooldowns.json`).

---

## Multi-Source Signal Architecture — Key Distinction

The `sources` field (plural) in `hotset.json` contains the full comma-joined multi-source string like `gap-300-,zscore-momentum-`. The `source` field (singular) in `signals_hermes_runtime.db` is the same format. When debugging dashboard display issues, check whether the template handles both field names.

**Files to check for signal state**:
- `/var/www/hermes/data/trades.json` — open/closed trades
- `/var/www/hermes/data/hotset.json` — current hot-set (uses `sources`)
- `/var/www/hermes/data/signals_hermes_runtime.db` — runtime signal DB (SQLite, uses `source`)
- `/var/www/hermes/data/signals.json` — API output (`approved` uses `source`, `hot_set` uses `sources`)
- `/var/www/hermes/logs/pipeline.log` — pipeline step timing and errors
- `/var/www/hermes/logs/signal-compactor.log` — compactor cooldown/filter decisions

## Docker vs Host
- Docker `hermes-core`: signals in `/app/hermes/data/signals_hermes_runtime.db` — access via `docker exec hermes-core`
- Host: `/var/www/hermes/data/` — access directly
- To clear Docker signals: `docker exec hermes-core sqlite3 /app/hermes/data/signals_hermes_runtime.db "UPDATE signals SET decision='PURGED', executed=1 WHERE decision IN ('PENDING','WAIT','APPROVED');"`

## Hot-set and Trades Clear Checklist
```bash
# Host DB - signals
sqlite3 /root/.hermes/data/signals_hermes_runtime.db "UPDATE signals SET decision='PURGED', executed=1 WHERE decision IN ('PENDING','WAIT','APPROVED');"

# Docker DB - signals  
docker exec hermes-core sqlite3 /app/hermes/data/signals_hermes_runtime.db "UPDATE signals SET decision='PURGED', executed=1 WHERE decision IN ('PENDING','WAIT','APPROVED');"

# Host trades.json - closed trades
python3 -c "import json; d=json.load(open('/var/www/hermes/data/trades.json')); d['closed']=[]; json.dump(d,open('/var/www/hermes/data/trades.json','w'),indent=2)"

# Docker trades - find via docker exec ls /app/hermes/data/
```

## RSI Signal Blind Spots — CONFIRMED AND DISABLED (2026-04-14)

### Backtest Results (794 closed Hermes trades)
```
Signal                                  N     WR       Avg    Total
hzscore,pct-hermes,vel-hermes (NO RSI)  167  58.1%  +0.099%  +$16.58  ← BEST
hzscore,pct-hermes,rsi-hermes (RSI)      52  44.2%  -0.092%   -$4.77
hzscore,rsi-hermes (RSI only)             7   0.0%  -0.228%   -$1.60
rsi_individual SHORT                       6   0.0%  -0.210%     n/a

HAS RSI (any):    62 trades  WR=38.7%  Avg=-0.105%  Total=-$6.50
NO RSI (signal): 732 trades  WR=50.1%  Avg=+0.021%  Total=+$15.69
```

**Conclusion:** RSI degrades every combo. Adding RSI to `hzscore,pct-hermes,vel-hermes` drops win rate from 58.1% to 44.2%, avg from +0.099% to -0.092%. RSI individual SHORT has 0% win rate across 6 trades.

**Run the backtest:** `python3 /root/.hermes/scripts/rsi_backtest.py`

### What Was Disabled (2026-04-14)
1. **RSI individual signal** (`signal_gen.py` lines ~1642-1673): fires LONG/SHORT independently of z-score — COMMENTED OUT
2. **RSI confluence SHORT** (`signal_gen.py` lines ~1334-1348): "No z-score filter for SHORTs" — COMMENTED OUT

### RSI Individual Has No Z-Score Filter
**Location:** `signal_gen.py` lines 1645-1673 (NOW DISABLED)

RSI fires LONG when RSI < 42, SHORT when RSI > 60 — **completely independently of z-score**. This was the single biggest source of wrong-direction trades.

**PostgreSQL evidence:** Adding RSI to any combo makes it worse — see backtest table above.

### RSI Confluence SHORT Has No Z-Score Filter
**Location:** `signal_gen.py` lines 1343-1356 (NOW DISABLED)

Comment literally says "No z-score filter for SHORTs — elevated prices are valid short targets." In a BTC pump, EVERYTHING looks elevated. No z-score confirmation = wrong direction.

### All Entry Features Are NULL
**Location:** `hl-sync-guardian.py` — trade open

`entry_rsi_14`, `entry_macd_hist`, `entry_bb_position`, `entry_regime_4h`, `entry_trend` are **never recorded**. All 773 closed + 8 open trades have NULL for all entry features. Post-hoc analysis of "what conditions produced this losing trade?" is impossible.

**Fix:** Record current indicator values at trade open in `hl-sync-guardian.py`.

## Multi-DB Signal→Trade Correlation (2026-04-14)

When a signal generates a trade, it goes through two databases:

**SQLite `signals_hermes_runtime.db`** — individual signals at generation time:
```sql
-- What individual signals existed for a token?
SELECT signal_type, direction, confidence, z_score, rsi_14, macd_hist, decision, created_at
FROM signals WHERE token='LINK' ORDER BY created_at DESC LIMIT 20;
```

**PostgreSQL `brain.trades`** — merged signal at trade time:
```sql
-- What merged signal led to a trade?
SELECT token, direction, signal, pnl_pct, close_reason, entry_timing
FROM trades WHERE server='Hermes' AND status='closed' AND token='LINK';
```

**The join key:** `signal` column in PostgreSQL = `source` column in SQLite (e.g., `hzscore,pct-hermes,vel-hermes`).

**Key query — signal quality by type:**
```sql
-- SQLite: individual signal counts
SELECT signal_type, direction, COUNT(*), AVG(confidence)
FROM signals GROUP BY signal_type, direction ORDER BY COUNT(*) DESC;

-- PostgreSQL: merged signal trade outcomes
SELECT signal, direction, COUNT(*), AVG(pnl_pct), SUM(pnl_pct)
FROM trades WHERE server='Hermes' AND status='closed' AND signal IS NOT NULL
GROUP BY signal, direction HAVING COUNT(*) >= 3 ORDER BY SUM(pnl_pct);
```

## Scenario: Signals in DB but Missing from signals.json

**Symptom:** Runtime DB has PENDING signals but `signals.json` is empty or stale.

**Root cause:** `decider_run` timed out (~5 min limit), blocking `hermes-trades-api` from running in the same pipeline cycle.

**Diagnosis:**
```bash
# Check runtime DB for signals
sqlite3 /root/.hermes/data/signals_hermes_runtime.db "SELECT COUNT(*), decision, created_at FROM signals GROUP BY decision ORDER BY created_at DESC LIMIT 5;"

# Check signals.json
cat /var/www/hermes/data/signals.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'pending={len(d[\"pending\"])} approved={len(d[\"approved\"])} executed={len(d[\"executed\"])}')"

# Check last hermes-trades-api run
grep "hermes-trades-api" /root/.hermes/logs/pipeline.log | tail -3

# Check for decider_run timeouts blocking pipeline
grep "ERROR decider_run" /root/.hermes/logs/pipeline.log | tail -3
```

**Fast fix — manually run the sync:**
```bash
python3 /root/.hermes/scripts/hermes-trades-api.py
```

**Long-term fix:** Reduce `decider_run` timeout or optimize its slow queries so it doesn't block `hermes-trades-api`.

## LLM Prompt Contamination: `COIN` Placeholder Causing `COIN` Literal in Output (2026-04-16)

**Symptom**: LLM outputs `COIN` as a literal token name in hot-set. Hallucination guard at `ai_decider.py` line 1560 catches it:
```python
if token == '***' or token == 'COIN' or (token not in valid_tokens ...
```
The `COIN` literal appears because the prompt's output schema uses `COIN` as a placeholder:
```
1. COIN | DIRECTION | CONF={.}% | ...
2. COIN | DIRECTION | CONF={.}% | ...
```
The LLM confuses `COIN` (example placeholder) with an actual token symbol.

**Fix**: Replace `COIN` → `SYMBOL` in all output schema sections of `main-prompt.md`. `SYMBOL` is unambiguous and clearly a placeholder. Only change schema/output sections — keep `COIN` in prose (e.g., "don't rank a LONG signal for a coin that's already in a losing LONG position").

**Locations in main-prompt.md** (lines 40, 48-50, 72, 76-78, 104-105, 109, 113):
- Schema example lines: `1. COIN | DIRECTION | ...` → `1. SYMBOL | DIRECTION | ...`
- Action lines: `` `APPROVED:coin:direction` `` → `` `APPROVED:SYMBOL:direction` ``
- Field description: `- 'COIN' — coin symbol` → `- 'SYMBOL' — coin symbol`

**Also update ai_decider.py line 1560**: Remove `token == 'COIN' or` from the guard since `COIN` should no longer appear.

**Diagnosis**: Check `/tmp/llm_compaction_content.txt` after each ai_decider run for lines starting with `COIN`.

---

## hot_cycle_count Sync Gap: survival_round Never Written to DB (2026-04-16)

**Symptom**: Token has `survival_round=5` in `hotset.json` but `hot_cycle_count=0` in `signals_hermes_runtime.db`. Token disappears from hot-set when a new PENDING signal arrives because the DB value controls `decider_run` ordering.

**Root Cause**: Two-part failure:
1. The APPROVED UPDATE (`ai_decider.py` ~line 1709) has `WHERE created_at > datetime('now', '-10 minutes')` — if a survivor's most recent PENDING signal is older than 10 minutes, UPDATE affects 0 rows.
2. After writing `hotset.json`, `survival_round` from the JSON is never written back to `hot_cycle_count` in the DB.

**Fix**: Add Step 7b after the hotset.json write (~line 1745 in `ai_decider.py`):
```python
# STEP 7b: Sync survival_round → hot_cycle_count in DB
for entry in hotset_entries:
    c.execute("""
        UPDATE signals
        SET hot_cycle_count = ?
        WHERE token = ? AND direction = ?
          AND hot_cycle_count < ?
    """, (entry['survival_round'], entry['token'], entry['direction'].upper(),
          entry['survival_round']))
conn.commit()
```

**Diagnosis**:
```bash
cd /root/.hermes/scripts && python3 - << 'EOF'
import sqlite3
db = '/root/.hermes/data/signals_hermes_runtime.db'
conn = sqlite3.connect(db)
cur = conn.cursor()
cur.execute("""
    SELECT token, direction, hot_cycle_count, survival_round
    FROM signals WHERE token IN ('SOL','HBAR','XPL')
    ORDER BY hot_cycle_count DESC LIMIT 10
""")
for r in cur.fetchall():
    print(r)
conn.close()
EOF
```
If `hot_cycle_count=0` but `survival_round > 0` in `hotset.json` → bug is active.

---

## Survivor Context Starvation: LLM Re-ranks With Insufficient Data (2026-04-16)

**Symptom**: LLM rejects or poorly ranks high-round survivors (r3+) because it only sees a one-line summary: `SOL(r5,90%)` — no regime, no wave phase, no source quality.

**Root Cause**: The HOT SURVIVORS section (`ai_decider.py` ~line 1313) reads from `prev_hotset` — the previous `hotset.json` file. If that file is stale, empty, or the survivor wasn't written with regime data, the LLM gets zero useful context for re-ranking.

Additionally, `regime` and `regime_conf` are only added to `hotset.json` entries for newly-ranked tokens — not for carried-forward survivors.

**Fix**: Replace JSON-only survivor read with DB-first query:
```python
# Query DB for all hot-set survivors with full quality data
_surv_conn = sqlite3.connect(SIGNALS_DB)
_surv_cur = _surv_conn.cursor()
_surv_cur.execute("""
    SELECT token, direction, MAX(hot_cycle_count) as rounds,
           MAX(confidence) as max_conf, MAX(source) as src, MAX(z_score) as z
    FROM signals WHERE hot_cycle_count >= 1
    GROUP BY token, direction ORDER BY rounds DESC LIMIT 30
""")
_surv_rows = _surv_cur.fetchall()
_surv_conn.close()

# Overlay extra fields from hotset.json (wave, momentum, speed, regime)
_hs_map = {f"{s['token']}:{s['direction']}": s for s in prev_hotset.values()}

for _sr in _surv_rows:
    _tok, _dir, _rounds, _conf, _src, _z = _sr
    _extra = _hs_map.get(f"{_tok}:{_dir}", {})
    _reg = _extra.get('regime', 'N')
    _reg_conf = _extra.get('regime_conf', 0)
    _survivor_detail_str += (
        f"{_tok} | {_dir} | conf={_conf:.0f}% | regime={_reg[:2]}({_reg_conf:.0f}%) | "
        f"rounds={_rounds} | src={_src} | z={_z:+.2f} | WAVE={_extra.get('wave_phase','neutral')} | ..."
    )
```

**Key fields to always include in survivor context**: `regime`, `regime_conf`, `wave_phase`, `source`, `confidence`, `rounds`, `z_score`, `momentum_score`, `speed_percentile`, `age_hours`.

---

## Guardian Orphan Trade Creation — DISABLED (2026-04-16)

**Symptom**: UNI and AVAX appeared in `brain.trades` without being in the hot-set. No pipeline log entry for execution. Guardian was creating paper trades for orphan HL positions.

**Root cause**: `reconcile_hype_to_paper()` in `hl-sync-guardian.py` called `add_orphan_trade()` for any HL position with no matching DB record, then immediately closed it. This bypassed the hot-set entirely.

**Fix**: In `reconcile_hype_to_paper()` (~line 977), replaced the orphan trade creation block with:
```python
# ORPHAN GUARD (2026-04-16): Guardian must NOT create paper trades for orphan
# HL positions — only decider-run can open new trades. Log and skip.
log(f'  ⛔ {coin} HL position has no DB record — guardian cannot create trades (skip)', 'WARN')
continue
```

**Rule**: Guardian closes only. `decider_run` opens only. Guardian never creates new paper trades.

## vel-hermes Direction Semantics

**Current (code line 1818-1824):**
- `vel-hermes+` = **SHORT** — velocity > 0 (z-score rising = price reverting up = counter-trend SHORT)
- `vel-hermes-` = **LONG** — velocity < 0 (z-score falling = price reverting down = counter-trend LONG)

```python
# FLIPPED: vel-hermes+ = SHORT (z rising = price reverting up = counter-trend SHORT)
#          vel-hermes- = LONG  (z falling = price reverting down = counter-trend LONG)
vel_signal_dir = 'SHORT' if velocity > 0 else 'LONG'
sid = add_signal(token, vel_signal_dir, 'velocity', f'vel-hermes{"+" if vel_signal_dir == "SHORT" else "-"}', ...)
```

Bare `vel-hermes` (no +/-) is in `SIGNAL_SOURCE_BLACKLIST` — only `vel-hermes+` and `vel-hermes-` are allowed.

## hwave Direction Semantics (Flipped 2026-04-16)

**Before**: `hwave+` = LONG (price below + upward momentum crossing through), `hwave-` = SHORT
**After**: `hwave+` = SHORT (price ABOVE + downward momentum = counter-trend), `hwave-` = LONG (price BELOW + upward momentum)

`signal_gen.py` line ~1988:
```python
# FLIPPED: hwave+ = SHORT, hwave- = LONG
hwave_source = f'hwave{"-" if local_dir == "LONG" else "+"}'
```

Bare `hwave` is in `SIGNAL_SOURCE_BLACKLIST` — only `hwave+` and `hwave-` are allowed.

## Signal Compactor — Own systemd Timer (2026-04-16)

**Problem**: `signal_compactor` was in `STEPS_EVERY_5M` inside `run_pipeline.py`, triggered by `minute % 5 == 0`. But pipeline runs every 1 min and something else was also triggering it at non-5-min boundaries.

**Fix**: Created standalone systemd timer at `*:0/5:00`:
- Service: `/etc/systemd/system/hermes-signal-compactor.service`
- Timer: `/etc/systemd/system/hermes-signal-compactor.timer`
- Runs: `python3 /root/.hermes/scripts/signal_compactor.py`
- Log: `/root/.hermes/logs/signal-compactor.log`
- Removed from `run_pipeline.py` STEPS_EVERY_5M (now empty)

Verify it's running:
```bash
systemctl list-timers --all | grep signal-compactor
```

## Bug: survival_round Inflated from Stale `approved_cr_cache` (2026-04-26)

**Symptom**: A re-approved token shows `survival_round=21` in hotset even though the current signal's `compact_rounds=2`. All tokens in hotset show sr=1 despite being approved for multiple rounds.

**Root cause** (`signal_compactor.py` Step 9, line ~546):

`approved_cr_cache[key]` = `MAX(compact_rounds)` across **ALL** APPROVED rows for that token+direction. When a signal expires and a new one re-enters:

```
XRP SHORT: old APPROVED (executed, expired)  cr=21  ← still in DB as APPROVED
          new APPROVED (current)            cr=2   ← fresh signal
          approved_cr_cache['XRP:SHORT'] = MAX(21, 2) = 21
          sr = 21 + 1 = 22  ← wrong
```

The old signal's cr=21 persists in the cache even though the new signal only has cr=2.

**Also**: `key = f"{token}:{direction}"` on line 538 became unused after the fix — removed.

**Fix** (signal_compactor.py Step 9):
```python
# WRONG — stale MAX across all approved signals:
if key in approved_cr_cache:
    survival_round = approved_cr_cache[key] + 1
else:
    survival_round = prev_hotset.get(key, {}).get('survival_round', 0) + 1

# CORRECT — use THIS signal row's compact_rounds directly:
survival_round = cr + 1  # cr = row[8] already extracted per-row
```

**Verification**:
```bash
# Check what approved_cr_cache actually stores (MAX across all rows):
python3 -c "
import sqlite3
conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
cur = conn.cursor()
cur.execute(\"SELECT token, direction, MAX(compact_rounds), COUNT(*) FROM signals WHERE decision='APPROVED' GROUP BY token, direction ORDER BY MAX(compact_rounds) DESC LIMIT 10\")
for r in cur.fetchall():
    print(f'{r[0]:10} {r[1]:5} MAX_cr={r[2]:2} count={r[3]}')
"

# Compare hotset sr vs DB cr:
python3 -c "
import json, sqlite3
hs = json.load(open('/var/www/hermes/data/hotset.json'))['hotset']
conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
for e in hs:
    cur = conn.cursor()
    cur.execute(\"SELECT compact_rounds FROM signals WHERE token=? AND direction=? AND decision='APPROVED' ORDER BY created_at DESC LIMIT 1\", (e['token'], e['direction']))
    row = cur.fetchone()
    db_cr = row[0] if row else 'N/A'
    match = '✓' if e['survival_round'] == db_cr + 1 else '✗ WRONG'
    print(f\"{e['token']:10} sr={e['survival_round']:2} db_cr={db_cr} {match}\")
"
```

**Key lesson**: `approved_cr_cache` is built for the staleness filter (`MAX(cr)` determines which row to keep), NOT for survival_round. Always use the per-row `cr` value directly in Step 9.

## Fix Patterns for Signal Combo Direction Conflicts

**When `hzscore,pct-hermes` works but `hzscore,pct-hermes,vel-hermes` flips direction:**

**Fix 1 (recommended): Raise velocity threshold** — require stronger momentum for vel-hermes to fire
```python
# signal_gen.py line 1710 — raise from 0.03 to 0.05
if abs(velocity) >= 0.05:  # was 0.03
```

**Fix 2: Penalize 3-way combo weight** — quick workaround
```python
# ai_decider.py SOURCE_WEIGHT_OVERRIDES
('mtf_zscore', 'hzscore,pct-hermes,vel-hermes', 0.7),  # was 0.85
```

**Fix 3: Add direction-consistency check during merge** — most correct fix
In `signal_schema.py` `add_signal()`, before merging, check if the incoming signal's direction contradicts the existing row. If conflicting sources like `hzscore+pct` (mean-reversion) vs `vel` (momentum) disagree, keep the higher-weight signal and discard the conflicting one.

## Hot-set Pipeline Architecture — Single Writer, Single Reader Fix (2026-04-21)

### The Problem
`signals.html` (dashboard) showed 0 approved signals even though `hotset.json` had 7 tokens. Two bugs were interacting:

### Bug 1 — Open-position filter gap causing ghost signals and re-entry loops (2026-04-23)

**Symptom**: A traded token (e.g., MEME) appears in hot-set.json AND a new MEME signal re-enters in the same compaction cycle. Guardian fires a trade → PostgreSQL `status='open'` → hot-set.json NOT updated until next compactor run (~1 min later) → MEME is still in hot-set AND a new MEME signal appears → re-entry loop.

**Fix** (`signal_compactor.py` lines 720-726): Remove tokens with open positions right before writing hot-set.json, using a live PostgreSQL query:
```python
# FIX: Remove traded tokens right before writing hot-set.json.
# Closes the ~1-minute gap where guardian fires a trade but compactor
# hasn't refreshed _open_pos_cache from PostgreSQL yet.
live_open_tokens = _get_open_tokens()
if live_open_tokens:
    hotset_output = [e for e in hotset_output if e['token'].lower() not in live_open_tokens]
    log(f"  🛡️  [HOTSET-FILTER] Removed {removed} traded tokens (open pos): ...")
```

**Why this fix is better than fixing guardian**: Guardian doesn't own hot-set.json — compactor does. This fix reuses the existing `_get_open_tokens()` function and FileLock infrastructure already at the write step, avoiding a new race condition.

### Bug 2 — API staleness check using JSON-internal timestamp (race condition)
`hermes-trades-api.py` `_get_hotset_from_file()` checked `data.get('timestamp', 0)` from inside the JSON. This value is written by `signal_compactor.py` AT THE END of its write. But the API runs every 1 min via the pipeline, and the compactor runs every 1 min via its own systemd timer. Their timing is not synchronized — the API could read the file BEFORE the compactor finished writing it, seeing a stale timestamp and returning `[]`.

**Fix**: Use file `mtime` (filesystem modification time) instead:
```python
# BEFORE (WRONG):
ts = data.get('timestamp', 0)
if ts > 0 and (time.time() - ts) > 1200:
    return []  # stale

# AFTER (CORRECT):
file_mtime = os.fstat(os.open(HOTSET_FILE, os.O_RDONLY)).st_mtime
if (time.time() - file_mtime) > 1200:
    return []  # stale
```

### Bug 2 — `approved_list` from wrong source
`write_signals()` built `approved_list` from raw DB rows via `get_signals_from_db()`. But `decision=APPROVED` in the DB doesn't mean "currently in hot-set" — many APPROVED signals exist in the DB that aren't in the current top-10. The actual hot-set comes from `hotset.json`.

**Fix**: Use `hot_set` (enriched from `hotset.json`) as `approved_list`:
```python
# BEFORE (WRONG):
approved_list = [s for s in signals if s['decision'] == 'APPROVED']  # from raw DB rows

# AFTER (CORRECT):
approved_list = hot_set  # enriched from hotset.json
pending_list  = [s for s in signals if s['decision'] == 'PENDING']
executed_list = [s for s in signals if s['decision'] == 'EXECUTED']
```

### The Single-Writer Architecture
- `signal_compactor.py` (systemd timer, every 1 min) → sole writer to `hotset.json`
- `hermes-trades-api.py` (pipeline, every 1 min) → reads `hotset.json`, enriches with live RSI/MACD, writes `signals.json`
- `signals.html` → reads `signals.json`
- `compact.py` (skill script) → audit/standalone only, NOT a writer, not in systemd

### Diagnosis Commands
```bash
# Check hotset.json content
python3 -c "import json; d=json.load(open('/var/www/hermes/data/hotset.json')); print(f'hotset={len(d[\"hotset\"])}')"

# Check signals.json approved count
python3 -c "import json; d=json.load(open('/var/www/hermes/data/signals.json')); print(f'approved={len(d[\"approved\"])}')"

# Check API staleness message
grep "hotset" /root/.hermes/logs/hermes-trades-api.log | tail -3

# Check compactor is running
systemctl list-timers --all | grep signal-compactor

# Check file mtime vs JSON timestamp
python3 -c "import os,time,json; f='/var/www/hermes/data/hotset.json'; d=json.load(open(f)); m=os.path.getmtime(f); print(f'file mtime={m} (age={time.time()-m:.0f}s), json ts={d.get(\"timestamp\")}')"
```

---

## Bug 7: Sources Showing `--` in Dashboard Despite Valid Multi-Source Signals (2026-04-23)

**Symptom**: Dashboard APPROVED tab shows all hot-set tokens with `hot set` as source instead of actual multi-source strings like `gap-300-,zscore-momentum-,ema_sma_gap_300_short`.

**Root cause** (`/var/www/hermes/signals.html` line 371): Template reads `s.source` (singular) but hot_set entries from `hotset.json` use `s.sources` (plural):
```javascript
// WRONG — only reads singular `source`:
${s.source || '--'}

// FIXED — fallback to plural `sources`:
${(s.source || s.sources) || '--'}
```

**Why it passed tests**: The `signals.json` `approved` array uses `source` (singular) from the DB, while `hot_set` array uses `sources` (plural) from `hotset.json`. The template was only handling the singular case.

**Files**: `/var/www/hermes/signals.html` line 371.

---

## Critical Bug: Cooldown Flood — Every Trade Close Writing Cooldowns (2026-04-23)

**Symptom**: Hot-set stays empty. `signal-compactor.log` shows `Pre-filter: 17 signals passed` but then `COOLDOWN skip` for EVERY signal. `hotset.json` writes 0 tokens for consecutive cycles.

**Root cause**: `decider_run.py` line 672 was calling `set_cooldown()` on **every closed trade**, regardless of profit or loss:
```python
# WRONG — wrote cooldown on EVERY close:
if trade_dir:
    set_cooldown(token.upper(), trade_dir.upper(), hours=1)

# FIXED — only on LOSS:
if trade_dir and 'loss' in reason.lower():
    set_cooldown(token.upper(), trade_dir.upper(), hours=1)
```

**Effect**: PostgreSQL `signal_cooldowns` table accumulated 217+ active `reason='signal'` entries. `signal_compactor.py`'s `get_cooldown()` checks PostgreSQL first → every signal hit cooldown skip → hot-set empty for ~1 hour.

**Diagnosis**:
```bash
# Check active cooldown count in PostgreSQL
cd /root/.hermes && python3 -c "
import psycopg2
conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
cur = conn.cursor()
cur.execute(\"SELECT COUNT(*) FROM signal_cooldowns WHERE expires_at > NOW()\")
print(f'Active cooldowns: {cur.fetchone()[0]}')
cur.execute(\"SELECT reason, COUNT(*) FROM signal_cooldowns WHERE expires_at > NOW() GROUP BY reason\")
print('By reason:', cur.fetchall())
"

# Check signal-compactor.log for COOLDOWN skip pattern
tail -100 /root/.hermes/logs/signal-compactor.log | grep "COOLDOWN skip"

# Verify get_cooldown returns True for any token
cd /root/.hermes && python3 -c "from scripts.signal_schema import get_cooldown; print(get_cooldown('AVAX','SHORT'))"
```

**Fix**: Add `'loss' in reason.lower()` guard in `decider_run.py` line ~672. Also clear stale cooldowns:
```bash
python3 -c "
import psycopg2
conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
cur = conn.cursor()
cur.execute(\"DELETE FROM signal_cooldowns\")
conn.commit()
print('Cleared all cooldowns')
"
```

**Lesson**: When EVERY signal is blocked by cooldown despite no obvious loss events, check `signal_cooldowns` table directly — the cooldown flood is the most likely cause. The `reason='signal'` cooldowns come from `set_cooldown()` in `decider_run.py`, not from `set_loss_cooldown()` (which writes to `loss_cooldowns.json`).

## Files to Check for Signal State
- `/var/www/hermes/data/trades.json` — open/closed trades
- `/var/www/hermes/data/hotset.json` — current hot-set
- `/var/www/hermes/data/signal-cooldowns.json` — cooldowns
- `/var/www/hermes/data/signals_hermes_runtime.db` — runtime signal DB (sqlite3)
- `/root/.hermes/logs/pipeline.log` — pipeline step timing and errors
- `/root/.hermes/logs/signal-compactor.log` — compactor cooldown/filter decisions
- Docker: `docker exec hermes-core sqlite3 /app/hermes/data/signals_hermes_runtime.db "SELECT COUNT(*), decision FROM signals GROUP BY decision;"`
