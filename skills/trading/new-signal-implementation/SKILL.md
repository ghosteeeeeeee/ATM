---
name: new-signal-implementation
description: Adding a new signal to Hermes — fixed-param or simple signals that don't need per-token tuning. Covers signal architecture, critical bugs, and integration patterns.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [signals, hermes, implementation]
    related_skills: [per-token-signal-implementation, rs-signal-implementation]
triggers:
  - add new signal to hermes
  - new fixed-param signal
  - standalone signal function
  - signal scanner implementation
---

# New Signal Implementation in Hermes (Fixed-Param)

## When to Use This

Adding a signal with fixed parameters (same across all tokens) — no per-token tuning needed. For signals that need per-token tuned params, use `per-token-signal-implementation` instead.

Examples covered here:
- MA300 + candle confirmation (LONG: MA cross up → 2 candles confirm)
- Simple MA cross (golden/death cross)
- RSI threshold signals
- Volume anomaly signals
- **Multi-timeframe signals**: TF-A provides reference indicator (e.g., EMA300 on 1m), TF-B (e.g., 5m) provides signal bars. Always use bisect for alignment, not offset arithmetic. Keep TF-B candles fresh via candles.db aggregation, not on-the-fly synthesis.

## Architecture

```
standalone scanner script (or signal_gen function)
    ↓ reads local candles.db (zero HL API calls)
signal_schema.add_signal()  → signals_hermes_runtime.db
    ↓
signal_compactor.py  → hotset.json
    ↓
guardian → execution
```

## Files to Create

1. **`scripts/{signal_name}_signals.py`** — detection engine, pure library, no external deps
2. **`scripts/run_{signal_name}_signals.py`** — standalone runner with all guards
3. **`scripts/backtest_{signal_name}.py`** — validation script

Or integrate directly into `signal_gen.py` if the signal is simple and doesn't need a separate backtester.

## Step-by-Step: Fixed-Param Scanner

### 1. Write the Detection Function

```python
# In scripts/{name}_signals.py
def scan_{name}_signals(prices_dict: dict, **kwargs) -> tuple[int, set[str]]:
    """
    Scan for {name} signals.
    Returns: (count_of_signals_written, set_of_tokens_that_fired)
    """
    from signal_schema import add_signal, price_age_minutes
    from position_manager import get_open_positions as _get_open_pos

    open_pos = {p['token']: p['direction'] for p in _get_open_pos()}
    added = 0
    fired_tokens = set()

    for token, data in prices_dict.items():
        if token.startswith('@'): continue
        if not data.get('price') or data['price'] <= 0: continue
        if token.upper() in open_pos: continue
        if price_age_minutes(token) > 10: continue

        # Fetch candles from local DB
        candles = _get_candles_from_db(token, lookback=500)

        # Detect signal
        signal = detect_{name}(candles, **kwargs)
        if not signal:
            continue

        direction, confidence, source = signal
        price = data['price']

        sid = add_signal(
            token=token,
            direction=direction,
            signal_type='{name}',
            source=source,
            confidence=confidence,
            value=float(confidence),
            price=price,
            exchange='hyperliquid',
            timeframe='1m',
            z_score=None,
            z_score_tier=None,
        )
        if sid:
            added += 1
            fired_tokens.add(token)

    return added, fired_tokens
```

### 2. Write the Standalone Runner

```python
# In scripts/run_{name}_signals.py
from {name}_signals import scan_{name}_signals
from signal_schema import is_delisted, price_age_minutes, record_cooldown_start
from position_manager import get_open_positions

# Guards applied HERE, not in the scanner
BLACKLIST = {...}  # from hermes_constants

def run():
    prices = _get_prices()  # your price-fetch function

    # Apply all guards BEFORE passing to scanner
    filtered = {}
    for token, data in prices.items():
        if token.startswith('@'): continue
        if not data.get('price'): continue
        if is_delisted(token.upper()): continue
        if price_age_minutes(token) > 10: continue
        filtered[token] = data

    added, fired = scan_{name}_signals(filtered, **your_params)

    # CRITICAL: only write cooldowns for tokens that actually fired
    for token in fired:
        record_cooldown_start(token, 'LONG', cooldown_hours=1)

    print(f'{name}: {added} signals, tokens: {fired}')
    return added
```

## Critical Bug #1: Cooldown Writer Receives Only Count

**Symptom:** Every token in the scan gets a cooldown written, not just the ones that fired.

**Root cause:** Scanner returns only `int` (count), caller loops over ALL tokens.

**Fix:** Scanner MUST return `tuple[int, set[str]]` — both count AND the set of tokens that fired.

```python
# WRONG:
def scan_xxx_signals(prices_dict):
    ...
    return added  # caller has no idea which tokens fired!

# In runner:
for token in prices_dict:  # WRONG: every token gets cooldown
    record_cooldown_start(token, 'LONG', hours=1)

# RIGHT:
def scan_xxx_signals(prices_dict):
    ...
    return added, fired_tokens  # set of tokens that actually fired

# In runner:
for token in fired_tokens:  # CORRECT: only tokens that fired
    record_cooldown_start(token, 'LONG', hours=1)
```

This bug appeared identically in BOTH `rs_signals.py` AND `ma_cross_signals.py`. Always return which tokens fired.

## Critical Bug #2: Multi-Indicator Array Alignment

**Symptom:** MA cross fires wrong direction — EMA10 > EMA200 but output shows SHORT.

**Root cause:** Two indicators with different warm-up periods don't share the same starting candle index.

```python
# WRONG (naive alignment):
valid_ema10 = [ema10[i] for i in range(9, len(ema10))]
valid_ema200 = [ema200[i] for i in range(199, len(ema200))]
# valid_ema10[0] = candle index 9, valid_ema200[0] = candle index 199
# These are NOT the same candle!

# RIGHT (alignment by timestamp):
ema10_by_ts = {candles[i]['ts']: ema10[i] for i in range(9, len(ema10))}
ema200_by_ts = {candles[i]['ts']: ema200[i] for i in range(199, len(ema200))}
common_ts = sorted(ema10_by_ts.keys() & ema200_by_ts.keys())

for ts in common_ts:
    e10 = ema10_by_ts[ts]
    e200 = ema200_by_ts[ts]
    # now e10 and e200 correspond to the SAME candle
```

This applies to ANY signal comparing two+ indicators with different warm-up periods: MA crosses, MACD, Bollinger Bands, ATR stops, etc.

### Multi-Timeframe Signal Alignment (bisect pattern)

**Pattern:** TF-A (e.g., 1m) provides a reference indicator (e.g., EMA300), TF-B (e.g., 5m) provides signal bars. The arrays have DIFFERENT start times and lengths — offset arithmetic always breaks.

**Right approach — use `bisect` for O(log n) timestamp lookup:**

```python
import bisect

def _ema300_for_5m_bar(bar_ts, ema300_ts_array, ema300_vals):
    """Find EMA300 value for a 5m bar timestamp using binary search."""
    idx = bisect.bisect_right(ema300_ts_array, bar_ts) - 1
    if idx < 0:
        return None
    return ema300_vals[idx]

# Build 1m EMA300 arrays once (full lookback)
ema300_ts = [row[0] for row in ema300_rows]   # timestamps
ema300_vl = [row[1] for row in ema300_rows]   # values

# For each 5m bar, look up the EMA300 that corresponds to its timestamp
for bar in candles_5m:
    bar_ts = bar['ts']
    ema300 = _ema300_for_5m_bar(bar_ts, ema300_ts, ema300_vl)
    if ema300 is None:
        continue
    gap_pct = (bar['close'] - ema300) / ema300 * 100
```

**Why not offset arithmetic?** If 1m starts at 16:54 and 5m starts at 11:05, then `candles_1m[i]` and `candles_5m[j]` with the same index `i=j` point to DIFFERENT real times. The arrays don't share a common zero. Bisect always finds the correct 1m candle whose timestamp is ≤ the 5m bar's open time.

**Note on data freshness:** If candles.db TF-B table (e.g., candles_5m) is stale but signals_hermes.db price_history has fresh 1m bars, backfill TF-B from price_history first, then rely on `_aggregate_tf(300, 'candles_5m')` in price_collector.py going forward. Do NOT synthesize 5m from 1m on every signal call — cache it in candles.db and keep it fresh via the pipeline.

## Critical Bug #3: Backtester Per-Token Stats Key Bug

**Symptom:** Per-token stats return empty or wrong results; overall stats are correct.

**Root cause:** The `compute_stats()` helper returns a dict keyed by token, but the sweep script passes a different variable name or the wrong dict.

```python
# In backtester:
def compute_stats(results):
    stats = {}
    for rec in results:
        token = rec['token']
        # ... compute WR, PnL ...
        stats[token] = {'wr': wr, 'pnl': pnl, 'n': n}
    return stats

# In sweep script:
all_results = []
for token in tokens:
    ...
    results = backtest_signal(token, ...)
    all_results.extend(results)

# WRONG: results is a flat list, not per-token dict
# You need to call compute_stats separately per token or restructure

# RIGHT:
token_results = {token: [] for token in tokens}
for token in tokens:
    ...
    token_results[token].extend(backtest_signal(token, ...))

# Now compute per-token:
for token, results in token_results.items():
    stats[token] = compute_stats(results)  # correctly scoped
```

## Critical Bug #5: --dry Flag Must Patch add_signal

**Symptom:** `--dry` flag is passed but signals still write to the DB.

**Root cause:** The CLI module has a `--dry` argument that sets a flag, but `add_signal()` from signal_schema is called directly in the scanner — it doesn't check that flag.

**Fix:** In the CLI module, patch `add_signal` to a no-op after parsing args:

```python
# In run_{name}_signals.py, after arg parsing:
if args.dry:
    import signal_schema
    original_add_signal = signal_schema.add_signal
    def noop_add_signal(*args, **kwargs):
        return None
    signal_schema.add_signal = noop_add_signal
    print('[DRY RUN] add_signal patched to no-op')
```

## Critical Bug #6: Token Source Wrong Database or Missing Table

**Symptom:** Scanner returns 0 signals written despite tokens meeting all criteria. No exception, silent failure.

**Root cause:** Scanner queries `SELECT DISTINCT token FROM tokens` on signals_hermes_runtime.db — but that table doesn't exist in that database. SQLite doesn't raise an error for SELECT on a non-existent table in a read query (it returns empty rows silently).

**Fix:** Use the correct table from the correct database:
- Token list: `latest_prices` table in `signals_hermes.db` (191 tokens, always populated)
- NOT `tokens` table in `signals_hermes_runtime.db` (doesn't exist)
- NOT `candles_1m` table (excludes delisted tokens that still have candles)

```python
from hermes_tools import read_file  # or use sqlite3 directly
conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
c.execute("SELECT DISTINCT token FROM latest_prices")
tokens = [r[0] for r in c.fetchall()]
```

## Critical Bug #7: Stale Signal — Check Only the Most Recent Bar

**Symptom:** Signal fires on a bar from 70+ minutes ago that happened to meet criteria, even though the current bar does not.

**Root cause:** Loop iterates over ALL bars in the lookback window and fires if ANY bar meets criteria. Old bars always eventually meet criteria in a trending market.

**Fix:** Only check the most recent bar:

```python
# WRONG: iterate all bars, fire if any meets criteria
for bar in recent_bars:
    if meets_criteria(bar):
        emit_signal(bar)
        break

# RIGHT: only the current/recent bar can fire
if len(recent_bars) == 0:
    return None
latest = recent_bars[-1]
if meets_criteria(latest):
    emit_signal(latest)
```

If you need to check multiple bars for persistence (e.g., "gap above EMA300 for N consecutive bars"), use timestamp-based lookups for those historical bars but only emit once, on the current bar.

## Critical Bug #8: Trend-Persistence Signal Design — was_below is Too Restrictive

**Symptom:** Strong uptrend never fires — price has been above EMA300 the entire lookback and never "crossed from below." The signal was designed to detect crosses, not sustained breaks.

**Pattern:** A "persistent gap above EMA(N)" signal should detect:
- (A) Strong acceleration: gap >> rolling average of recent gaps (bypasses purity check)
- (B) Gradual persistence: gap consistently above rolling average for ≥X% of recent N bars

NOT: "price crossed from below EMA300 in the last N bars" — this fails for coins that have been in a clear uptrend for hours.

**Dual-path pattern:**

```python
MIN_GAP_PCT     = 0.50   # minimum absolute gap to fire
ACCEL_THRESH    = 0.30   # gap - avg_gap > this → fires via Path A
TREND_PURITY    = 0.50   # fraction of bars with gap > avg_gap → Path B
RECENT_BARS     = 15     # lookback for purity check

def detect_gap300_signal(candles_5m, candles_1m):
    gaps = compute_gaps(candles_5m, candles_1m)  # (ts, gap_pct) per 5m bar
    recent = gaps[-RECENT_BARS:]
    if not recent:
        return None

    latest_gap = recent[-1]['gap_pct']
    avg_gap    = mean([b['gap_pct'] for b in recent])
    gap_growth = latest_gap - avg_gap

    # Path A: strong acceleration (bypasses purity)
    if latest_gap >= MIN_GAP_PCT and gap_growth > ACCEL_THRESH:
        return signal(gap_growth=gap_growth, path='A')

    # Path B: consistent persistence
    above_avg = sum(1 for b in recent if b['gap_pct'] > avg_gap)
    purity = above_avg / len(recent)
    if latest_gap >= MIN_GAP_PCT and purity >= TREND_PURITY:
        return signal(purity=purity, path='B')

    return None
```

## Critical Bug #5: Compression Detection — Relative vs Absolute Thresholds

**Symptom:** Compression phase never fires, even when the market is clearly coiled. The breakout engine detects the breakout correctly but has zero Phase 1 confluence, so signals lack the coiled-spring confirmation that filters noise.

**Root cause:** Using relative ratios like `comp_window_vol < prior_window_vol * 0.40` fails when the "prior window" itself is noisy. A single spike bar anywhere near the compression window inflates the baseline, making the quiet window look loud by comparison.

**Concrete example (BNB 1m, April 22 2026):**
- Compression window (12 bars, 13:29-13:40): avg vol = 854, range = 0.06-0.08%
- Prior window (20 bars, 13:09-13:28): avg vol = 59 (inflated by a 509-volume spike at 13:31)
- Relative ratio: 854 / 59 = 14.4x → FAILs the < 0.40x test
- Absolute test (all bars vol < 200, range_pct < 0.10%): PASSES for 13:36-13:40

**The fix — use absolute thresholds:**

```python
# WRONG: relative to noisy baseline (FAILS)
prior_avg_vol = sum(c['volume'] for c in prior_window) / len(prior_window)
quiet_bars = sum(1 for c in comp_window if c['volume'] < prior_avg_vol * 0.30)
vol_ok = quiet_bars / len(comp_window) >= 0.80  # fails because spike contaminated prior

# RIGHT: absolute thresholds (WORKS)
VOL_COMP_ABS  = 200    # max volume per bar to qualify as compressed (1m)
RNG_COMP_ABS  = 0.10   # max range_pct per bar to qualify as compressed (1m)
quiet_vol = all(v < VOL_COMP_ABS for v in vols)
tight_rng = all(r < RNG_COMP_ABS for r in rng_pcts)
compressed = bool(quiet_vol and tight_rng)
```

**Rule: Compression thresholds must be absolute, not relative.** The compression window must be quiet in absolute terms — comparing it to a "prior window" baseline that may itself be noisy is unreliable.

**Second lesson — window length (COMPRESSION_BARS) tuning:**
- Too long (e.g., 12 bars): A single noisy bar contaminates the window for too long
- Too short (e.g., 3 bars): Doesn't capture genuine multi-bar compression
- Empirically: 8 bars for 1m, 6 bars for 5m — short enough to outlast spike bars

**Third lesson — validate Phase 1 independently of Phase 3:**
Don't assume compression detection works just because breakout detection works. Test `detect_compression()` in isolation first. In the BNB case, `detect_breakout()` was correct all along (vol_ratio=48x, range=1.2%) — it was `detect_compression()` that never fired.

```python
# Validate compression BEFORE testing breakout
window = candles[:idx+1]
is_comp, stats = detect_compression(window, COMPRESSION_BARS_1m)
direction = detect_breakout_direction(window, COMPRESSION_BARS_1m)
is_brk = False
if direction:
    is_brk, brk_stats = detect_breakout(window, direction)
print(f'Bar {idx}: comp={is_comp} dir={direction} brk={is_brk}')
```

**Symptom:** Signal has a "transition" condition (e.g., phase changed from X to Y) but emits 0 signals forever despite the state existing in the DB.

**Root cause:** The signal function calls a state-reader helper that reads from a table/cachethe signal function itself just wrote to in the same iteration. The "previous" state always equals the current state.

**Example pattern (from `phase_accel` signal, 2026-04-22):**
```python
def _run_phase_accel_signals(prices_dict):
    for token in ...:
        mom = get_momentum_stats(token)   # computes phase, WRITES to momentum_cache
        phase = mom.get('phase')            # current phase
        if phase != 'accelerating':
            continue
        prev_phase = _get_previous_phase(token)  # reads momentum_cache — same iteration!
        if prev_phase == 'accelerating':
            continue  # ALWAYS true — we just wrote 'accelerating' above
        # Never reaches here
```

The `get_momentum_stats()` call at line N updates `momentum_cache.phase = 'accelerating'`. The `_get_previous_phase()` call at line N+1 reads `momentum_cache.phase`, which is now `'accelerating'`, so the transition check fails every time.

**Fix:** Store the previous phase in a SEPARATE column in the same table:
```sql
ALTER TABLE momentum_cache ADD COLUMN prev_phase TEXT;
```
Then update BEFORE overwriting:
```python
# In _persist_momentum_state:
cur.execute("""INSERT INTO momentum_cache ... DO UPDATE SET
    prev_phase = excluded.phase,  -- save current as prev BEFORE new phase overwrites it
    phase = excluded.phase, ...""", ...)
```
And read `prev_phase` not `phase`.

**Detection:** `SELECT COUNT(*) FROM signals WHERE source='phase-accel'` returns 0 despite `momentum_cache` having `phase='accelerating'` for multiple tokens. Pipeline logs show the function runs but `accel_added = 0` every time.

## Integration into signal_gen.py (Optional)

If integrating into signal_gen.py rather than standalone:

1. Add import at top of file
2. Add `_run_{name}_signals()` function BEFORE the pattern scanner section (~line 2100)
3. Cache reset at start of `run()`: set module-level cache to `None`
4. Add call in main loop after pattern signals
5. Add routing in `signal_compactor.py` `SIGNAL_SOURCE_WEIGHTS` if needed

## Critical Bug #9: candles_Xm Table Missing `is_closed` Column

**Symptom:** New candle table (e.g., candles_5m) is created by `_init_candles_db()` but existing rows from the Binance seed path have NULL/missing `is_closed` values, causing `_aggregate_tf` to miscompute per-token last-closed boundaries.

**Schema rule:** All candle tables must have `is_closed INTEGER DEFAULT 1`:
```sql
CREATE TABLE candles_5m (
    token TEXT NOT NULL, ts INTEGER NOT NULL,
    open REAL, high REAL, low REAL, close REAL, volume REAL,
    is_closed INTEGER DEFAULT 1,   -- ← required for self-healing aggregation
    PRIMARY KEY (token, ts)
);
```

**Migration pattern** (run once before aggregation):
```python
def migrate_is_closed():
    conn = sqlite3.connect(CANDLES_DB, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        conn.execute(f"ALTER TABLE {TABLE} ADD COLUMN is_closed INTEGER DEFAULT 1")
        conn.execute(f"UPDATE {TABLE} SET is_closed = 1 WHERE is_closed IS NULL")
        conn.commit()
        print(f"[migrate] Added is_closed=1 to {TABLE}")
    except Exception as e:
        if 'duplicate column' not in str(e).lower():
            print(f"[migrate] {TABLE}: {e}")
    conn.close()
```

## Critical Bug #10: Systemd Timer Setup for Standalone Signal Scripts

**Pattern:** When a signal needs its own timer (separate from signal_gen.py pipeline), create a oneshot service + timer.

**Service file** (`/etc/systemd/system/hermes-{name}.service`):
```ini
[Unit]
Description=Hermes {Name} Signal
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /root/.hermes/scripts/{name}_signals.py
WorkingDirectory=/root/.hermes
StandardOutput=journal
StandardError=journal
```

**Timer file** (`/etc/systemd/system/hermes-{name}.timer`):
```ini
[Unit]
Description=Hermes {Name} Timer — every N min
Requires=hermes-{name}.service

[Timer]
OnBootSec=30s
OnUnitActiveSec=5min
Persistent=true

[Install]
WantedBy=timers.target
```

**Activate:**
```bash
sudo tee /etc/systemd/system/hermes-{name}.service > /dev/null << 'EOF'
...
EOF
sudo tee /etc/systemd/system/hermes-{name}.timer > /dev/null << 'EOF'
...
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now hermes-{name}.timer
```

**Verify:**
```bash
systemctl list-timers | grep {name}
```

**Key design rules:**
- `Type=oneshot` for scripts that complete quickly (candle aggregation, signal scanning)
- `Persistent=true` catches missed runs if the system was off
- `OnUnitActiveSec` defines the interval; `OnBootSec` defines first run delay
- Service MUST exist before timer can activate (`Requires=` in timer unit)

## Critical Bug #11: Crossing-Bar Consecutive Count Resets to Zero

**Symptom:** An "exhaustion" or "momentum break" signal that fires when price crosses EMA after N consecutive bars on the wrong side never fires, even when N is clearly satisfied.

**Root cause:** At the crossing bar, price is now ON the other side of EMA, so the consecutive count resets to 0. The signal checks the current bar's count, which is always 0 at the exact crossover moment.

**Concrete example (XLM at 02:11 UTC):**
- Prior bar (02:10): price=0.17253, above EMA, consecutive_above=31 ✓
- Crossing bar (02:11): price=0.17248, below EMA, consecutive_above=0 ✗
- Signal checks current bar → 0 < 15 → never fires

**Fix:** Check the **prior bar's** consecutive count, but verify the **current bar** crosses EMA:

```python
# WRONG: count from current bar
consec_above = 0
for i in range(len(prices) - 1, -1, -1):  # starts at current bar (-1)
    if prices[i] >= ema_series[i]:
        consec_above += 1
    else:
        break
if consec_above >= CONSEC_THRESH and current_price < current_ema:
    fire_short()  # FAILS — consec_above is 0 at cross

# RIGHT: count from prior bar, verify cross
prior_price = prices[-2]
prior_ema   = ema_series[-2]
consec_above_prior = 0
for i in range(len(prices) - 2, -1, -1):  # starts at -2 (prior bar)
    if prices[i] >= ema_series[i]:
        consec_above_prior += 1
    else:
        break
crossed_short = (prior_price > prior_ema) and (current_price < current_ema)
if consec_above_prior >= CONSEC_THRESH and crossed_short:
    fire_short()  # WORKS — consec_above_prior=31, cross confirmed
```

**Also fix:** Add `None` guards when EMA warmup hasn't completed:
```python
if ema_series[i] is not None and prices[i] >= ema_series[i]:
```

**Detection:** Run signal with `--dry` on a known crossing event. If 0 signals when you expected 1+, add debug prints showing `consec_above` and `gap` at each bar near the crossing.

## Critical Bug #12: Exhaustion Signal Fires ONLY at Crossing — Not Continuous

**Symptom:** An exhaustion counter-trend signal fires once at the crossing but never again, even when the market continues in the reversal direction.

**Root cause:** By design. Exhaustion signals fire at the MOMENT price crosses EMA after a sustained move — they detect the turning point, not the continuation. After crossing, price is now on the opposite side, and consecutive-bar count in that direction is just beginning.

**Implication for backtesting:** You cannot "wait for the signal to fire" in a backtest — you must check every bar and fire at exactly the crossing bar. A backtest that checks only the most recent bar at end-of-day will miss exhaustion signals that fired mid-day.

**Verifying exhaustion signals:** Use historical simulation — fetch a window of price data around a known crossing event, iterate bar-by-bar checking for the exhaustion condition. Do NOT test by running the signal live on current data — you'll miss it because the crossing happened minutes/hours ago.

```python
# Historical simulation to verify exhaustion fires at a known crossing
for i in range(EMA_PERIOD, len(prices)):
    if i < 2:
        continue
    consec, cross = compute_exhaustion(prices, ema_series, i)
    if consec >= CONSEC_THRESH and cross:
        dt = timestamp[i]
        print(f"EXHAUSTION at {dt}: consec={consec} gap={gap[i]:+.3f}%")
```

## Variant: Counter-Signal Blocker

A counter-signal blocker is a **reactive** signal — it fires only when an open position exists and a strong opposing signal appears. It does NOT generate new entry signals. It writes a blocking signal to DB that expires opposing-direction PENDING/APPROVED signals via `add_signal()`'s conflict guard.

**Use cases:**
- Counter-signal exit: when we're LONG and z-score momentum reverses strongly (conf >= 75), write a SHORT counter-signal that expires the LONG entry signal
- Cascade flip first-responder: detects the counter-signal before cascade flip fires, blocking entry signals early

**Architecture:**
```
signal_gen.run()  →  scan_counter_signal_block(prices_dict)
                        ↓ reads open positions from PostgreSQL brain DB
                        ↓ checks runtime DB for opposing signals (z-score, MACD)
                        ↓ writes counter_signal type via add_signal()
                            → conflict guard expires opposite PENDING/APPROVED
```

**Key design differences from entry signals:**
- Reads from **brain PostgreSQL** (`trades WHERE status='open'`) not from candles
- Checks **runtime DB** for opposing signals — not price data
- `signal_type='counter_signal'` — distinct from entry signals
- Always gated by `CASCADE_FLIP_ENABLED` — won't fire unless cascade flip is armed
- Does NOT close positions — that is cascade_flip / position_manager's job
- `add_signal()` conflict guard does the blocking — no custom logic needed

**Implementation pattern:**
```python
# counter_signal_block.py
from hermes_constants import CASCADE_FLIP_ENABLED
from signal_schema import add_signal
from _secrets import BRAIN_DB_DICT  # PostgreSQL for open positions

_RUNTIME_DB = '/root/.hermes/data/signals_hermes_runtime.db'

def scan_counter_signal_block(prices_dict: dict = None) -> int:
    if not CASCADE_FLIP_ENABLED:
        return 0  # Gated by master toggle

    # Read open positions from PostgreSQL
    conn = psycopg2.connect(**BRAIN_DB_DICT)
    open_pos = {row[0].upper(): row[1].upper()
                for row in cur.fetchall() if row[2] == 'open'}

    for token, open_dir in open_pos.items():
        counter_dir = 'SHORT' if open_dir == 'LONG' else 'LONG'
        # Check for strong opposing z-score or MACD signal in runtime DB
        conf, z_score = _get_counter_signal_zscore(token, counter_dir)
        if conf < 75:  # MIN_COUNTER_CONFIDENCE threshold
            continue
        # add_signal() conflict guard expires opposite signals automatically
        add_signal(token=token, direction=counter_dir,
                   signal_type='counter_signal',
                   source=f'counter-block,zscore-momentum{counter_dir[0]}',
                   confidence=conf, ...)
```

**Integration in signal_gen.py:**
```python
# Import near other scanners (~line 2237)
from counter_signal_block import scan_counter_signal_block

# Call before confluence detection (so blocking happens before approval)
counter_blocked = scan_counter_signal_block(prices_dict)
if counter_blocked:
    print(f'  Counter-signal: {counter_blocked} entry signals blocked')
```

**Critical notes:**
- `_RUNTIME_DB` must be hardcoded as `/root/.hermes/data/signals_hermes_runtime.db` — do NOT import from `paths`, signal_gen.py defines it locally
- Brain DB credentials come from `_secrets.BRAIN_DB_DICT`, NOT from `hermes_constants`
- `signal_type='counter_signal'` must be unique — do NOT reuse an existing signal type name

## Naming Convention for Counter-Trend Signals

Use `+/-` suffix to indicate direction relative to EMA:
- `trend_purity+` — price above EMA = uptrend LONG
- `trend_purity-` — price below EMA = downtrend SHORT
- `exhaustion+` — uptrend exhausted = SHORT (price cracked below EMA after grind above)
- `exhaustion-` — downtrend exhausted = LONG (price bounced above EMA after grind below)

This allows signal_compactor to correctly identify directional conflicts (e.g., `trend_purity+` LONG conflicts with `exhaustion+` SHORT on the same token).

## Key Files

- `/root/.hermes/scripts/signal_gen.py` — main pipeline
- `/root/.hermes/scripts/signal_compactor.py` — hot-set scoring
- `/root/.hermes/scripts/signal_schema.py` — `add_signal()`, `record_cooldown_start()`
- `/root/.hermes/data/candles.db` — local candle data (table: `candles_1m`)
- `/root/.hermes/data/signals_hermes_runtime.db` — signals output

## Verification

```bash
# Check signals wrote to DB
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT token, direction, signal_type, confidence, source, created_at \
   FROM signals WHERE signal_type='{name}' ORDER BY created_at DESC LIMIT 5;"

# Check hot-set
cat /var/www/hermes/data/hotset.json | python3 -m json.tool | grep {name}

# Check no new HL API calls
grep -rn "_http_post\|requests\." scripts/{name}_signals.py
```

## Candles DB Schema

```
candles_1m: token, ts, open, high, low, close, volume
(NOT open_time — that's the signals_hermes.db ohlcv_1m schema)
```

## Common Signal Patterns

### Pattern: EMA9 + SMA20 ROC Gap Signal

Based on ema9_sma20_signals.py (2026-04-26). A trend-following signal using 9 EMA and 20 SMA on 1m prices, triggered when the rate-of-change of the EMA/SMA divergence crosses above a threshold.

**Signal logic:**
- LONG: EMA9 and SMA20 both rising (3 consecutive slope bars) AND price > EMA9 > SMA20 AND ROC gap crosses above X
- SHORT: EMA9 and SMA20 both falling AND price < EMA9 < SMA20 AND ROC gap crosses above X
- gap_type='roc' (verified best): `abs(slope_EMA9 - slope_SMA20) / price * 100`
- gap_type='gap' (gap-300 style): `abs(EMA9 - SMA20) / price * 100` — consistently worse

**Validated params (20-day backtest × 9 tokens, split-sample verified):**
| Param | Value |
|-------|-------|
| GAP_TYPE | `roc` |
| LONG_X | 0.008% |
| SHORT_X | `None` (disabled — negative PNL across ALL X values) |
| HOLD | 60 bars (~60min) |

**Results:**
- Full 20-day: 771 LONG signals, WR=49.0%, PNL=+0.017%/signal
- Split-sample: Train PNL=-0.016% → Test PNL=+0.041% (positive on unseen data)
- Per-token: AVAX best (+0.137%), DOT worst (-0.075%)

**Critical pattern: per-direction X thresholds**
When LONG and SHORT have asymmetric performance, use separate X constants:
```python
MIN_GAP_PCT_LONG  = 0.008  # ROC threshold for LONG
MIN_GAP_PCT_SHORT = None   # Disabled — SHORT PNL negative across all X
HOLD_BARS         = 60     # Exit after 60 bars regardless of profit
```
The detection function must accept both and test each independently:
```python
def detect_ema9_sma20_cross(token, prices, price,
                             min_gap_pct_long=MIN_GAP_PCT_LONG,
                             min_gap_pct_short=MIN_GAP_PCT_SHORT,
                             gap_type='roc'):
    # Test LONG cross at min_gap_pct_long
    # Test SHORT cross at min_gap_pct_short (only if not None)
    # Pick the most recent valid cross
```

**Why SHORT was disabled:** Across all tested X values (0.001%–0.020%) and hold periods (10–60 bars), SHORT PNL was negative. This is a genuine directional asymmetry in this indicator — the slope-based ROC gap widens more reliably on bullish setups than bearish ones on 1m Hyperliquid data.

**Backtest methodology used:**
1. Multi-token sweep (9 tokens × 20k bars = ~20 days)
2. Gap-type comparison: 'gap' vs 'roc'
3. X threshold sweep: 0.001%–0.020% in steps
4. Hold period sweep: 10, 15, 20, 30, 40, 60 bars
5. Per-token breakdown to find token-specific patterns
6. Split-sample validation: 7d train → 7d test (verified sign consistency)
7. Edge metric: `net_edge = (L_pnl*L_n + S_pnl*S_n)/(L_n+S_n)` — prioritizes direction consistency over raw count

---

### Pattern: MA Cross + Confirmation
```
LONG: candle[i] crosses above MA(N)
      AND candle[i+1].open > candle[i].high
      AND candle[i+1].close > candle[i].high
      AND candle[i+2].open > candle[i].high  # second confirmation
      AND candle[i+2].close > candle[i].high
Entry: candle[i+2].close (non-repainting — both candles confirmed)
```

Key filters that emerged empirically:
- Min MA separation: 0.5% (candle[i] close must be 0.5%+ away from MA)
- Freshness cap: only fire if confirmation happened within last 5 bars
- Direction: always LONG if price above MA, SHORT if below (no counter-trend)

### Pattern: Freshness Cap
```python
# Only fire if signal confirmed within last N bars
# Prevents stale re-firing on old setups
BARS_SINCE_CONFIRM = 5  # if conf happened >5 bars ago, skip
if bars_since_confirm > BARS_SINCE_CONFIRM:
    continue
```

## Signal Naming Convention

- `signal_type`: snake_case, descriptive (e.g., `ma300_candle`, `rsi_threshold`)
- `source` tag: includes key params for debugging (e.g., `ma300c-confirm2@sep0.5`)
