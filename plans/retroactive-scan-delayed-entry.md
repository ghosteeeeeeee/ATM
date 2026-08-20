# Plan: Retroactive Breakout Scan / Delayed Entry

**Date:** 2026-08-20
**Status:** Open (v3 — audited, all bugs fixed)
**Priority:** High — safety net for missed breakouts (IMX +2.72% case)
**Parent:** `plans/imx-spike-detection.md` (Fix 3)

## 1. What It Does

After the main breakout engine runs its compression→breakout detection, a secondary "retroactive scan" checks every token for large moves that already happened but were missed by all signal generators. It looks backward over a short window (last 5 minutes) and emits a retroactive signal with lower confidence when: (a) a significant single-candle move occurred, (b) the move has not fully reversed, (c) no existing signal already covers this token+direction, (d) the token is not on cooldown, and (e) the token doesn't already have an open position. This catches the "ice breaker" candle scenario where compression was broken by an earlier move, or the pipeline missed the exact candle due to timing.

## 2. When It Fires

A retroactive signal fires when ALL of these conditions are true:

| Condition | Threshold | Rationale |
|-----------|-----------|-----------|
| **Move size** | Single 1m candle: `abs(close/open - 1) * 100 >= RETRO_MIN_MOVE_PCT` (default 1.5%) | The IMX case was +2.72% in one candle. 1.5% catches most meaningful spikes. |
| **Candle body filter** | `abs(close - open) / open * 100 >= 0.3%` — reject dojis | Prevents LONG signals on essentially flat candles where close > open by noise. |
| **Lookback window** | Last `RETRO_LOOKBACK_BARS` (default 5) 1m candles | Only catch fresh moves. Older moves are stale. |
| **Reversion guard** | Price has not retraced more than `RETRO_MAX_REVERSION_PCT` (default 40%) of the move from peak/trough | If price already reversed 40%+, the opportunity is gone. |
| **No existing signal** | No PENDING/APPROVED signal in `signals` table for same token+direction in last `RETRO_COOLDOWN_MIN` (default 10) minutes | Don't duplicate signals. Don't fire if breakout engine already caught it. |
| **No opposing signal** | No PENDING/APPROVED signal for same token OPPOSITE direction in last 5 minutes | Prevents conflicting LONG+SHORT on same token. |
| **Volume confirmation** | Candle volume >= `RETRO_VOL_MIN_RATIO` (default 1.5x) of 20-bar rolling average, AND volume > `MIN_VOL_ABS` (default 100) | Filters noise — real moves have volume. Floor prevents false signals on illiquid tokens. |
| **Not blacklisted** | Token not in SHORT_BLACKLIST/LONG_BLACKLIST | Standard safety. |
| **Not delisted** | `is_delisted(token)` returns False | Standard safety. |
| **No open position** | Token not in open positions set | Don't double up on existing trades. |
| **Not on loss cooldown** | Token not in loss_cooldowns.json | Don't re-enter a token that recently lost. |
| **Cooldown** | No retroactive signal for same token+direction in last `RETRO_COOLDOWN_MIN` minutes | Prevents repeated signals on the same move. |
| **ATR valid** | `compute_atr(candles) > 0` | Prevents degenerate SL/TP at entry price. |

### Direction Detection
- **LONG**: `close > open` on the spike candle (bullish), AND body >= 0.3%
- **SHORT**: `close < open` on the spike candle (bearish), AND body >= 0.3%
- Direction is determined from the largest candle in the lookback window.

## 3. Confidence Scoring

Retroactive signals are inherently lower quality than fresh breakout signals (the move already happened). Confidence is penalized accordingly:

```
base_conf = RETRO_BASE_CONFIDENCE  (default 55)

# Move size bonus: bigger move = more conviction
move_bonus = min(15, (move_pct - RETRO_MIN_MOVE_PCT) * 5)  # +5 per 1% above minimum

# Age penalty: older move = less opportunity
age_penalty = age_minutes * RETRO_AGE_PENALTY_PER_MIN  (default 2.0 per minute)

# Reversion penalty: more reversion = worse setup
reversion_penalty = reversion_pct * RETRO_REVERSION_PENALTY_MULT  (default 0.5 per %)

# Volume bonus: higher volume = stronger conviction
vol_bonus = min(10, max(0, (vol_ratio - 1.0) * 5))

confidence = base_conf + move_bonus + vol_bonus - age_penalty - reversion_penalty
# Hard cap: never exceed RETRO_CONFIDENCE_CAP (70)
confidence = min(RETRO_CONFIDENCE_CAP, confidence)
```

**IMPORTANT**: No floor check in code. If `confidence < RETRO_CONFIDENCE_FLOOR` (50), the signal is simply not emitted (the `if confidence < RETRO_CONFIDENCE_FLOOR: return None` check handles this). The `max()` floor from v1 was dead code.

Default values produce:
- 1.5% move, 1 min old, 0% reversion, 2x vol → 55 + 0 + 5 - 2 - 0 = **58**
- 2.7% move, 2 min old, 10% reversion, 3x vol → 55 + 6 + 10 - 4 - 5 = **62**
- 1.5% move, 5 min old, 30% reversion, 1.5x vol → 55 + 0 + 2.5 - 10 - 15 = **32.5 → below floor, no signal**

This ensures retroactive signals sit below fresh breakout signals (70–95) in the hot-set ranking.

## 4. Reversion Guard

The reversion guard prevents firing on moves that already reversed. This is the most critical filter — without it, every exhausted spike becomes a false positive.

### Algorithm (complete implementation)

```python
def _check_retro_reversion(candles, direction, spike_idx_in_full):
    """
    Check if the move has reversed beyond threshold.
    Returns True if BLOCKED (reversed too much).
    
    For LONG spike: find the highest high after the spike.
        reversion = (peak - current_close) / (peak - spike_open) * 100
        If reversion > RETRO_MAX_REVERSION_PCT → BLOCK
    
    For SHORT spike: find the lowest low after the spike.
        reversion = (current_close - trough) / (spike_open - trough) * 100
        If reversion > RETRO_MAX_REVERSION_PCT → BLOCK
    """
    spike = candles[spike_idx_in_full]
    post_spike = candles[spike_idx_in_full + 1:]
    
    if not post_spike:
        return False  # no post-spike data yet, allow
    
    current_close = candles[-1]['close']
    
    if direction == 'LONG':
        peak = max(c['high'] for c in post_spike)
        move_size = peak - spike['open']
        if move_size <= 0:
            return True  # no upward move to measure
        reversion = (peak - current_close) / move_size * 100
    else:
        trough = min(c['low'] for c in post_spike)
        move_size = spike['open'] - trough
        if move_size <= 0:
            return True  # no downward move to measure
        reversion = (current_close - trough) / move_size * 100
    
    return reversion > RETRO_MAX_REVERSION_PCT


def _compute_reversion_pct(candles, direction, spike_idx_in_full):
    """Return the % of the move that has been given back."""
    spike = candles[spike_idx_in_full]
    post_spike = candles[spike_idx_in_full + 1:]
    
    if not post_spike:
        return 0.0
    
    current_close = candles[-1]['close']
    
    if direction == 'LONG':
        peak = max(c['high'] for c in post_spike)
        move_size = peak - spike['open']
        if move_size <= 0:
            return 0.0
        return (peak - current_close) / move_size * 100
    else:
        trough = min(c['low'] for c in post_spike)
        move_size = spike['open'] - trough
        if move_size <= 0:
            return 0.0
        return (current_close - trough) / move_size * 100
```

### Additional Reversion Checks
1. **Last candle reversal**: If the most recent 1m candle is a strong reversal (close against signal direction with range > 0.5%), BLOCK immediately.
2. **RSI extreme**: If RSI(14) > 80 for LONG or < 20 for SHORT, BLOCK (overextended, likely to revert).

```python
def _compute_rsi(candles, period=14):
    """RSI from close prices. Requires period+1 candles."""
    if len(candles) < period + 1:
        return 50.0  # neutral if insufficient data
    closes = [c['close'] for c in candles]
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))
```

## 5. Integration Point

### Where It Runs

The retroactive scan runs **inside `breakout_engine.py`**, as a second pass after the main compression→breakout detection. This is the natural home because:
- It reuses the same candle-fetching infrastructure (`get_candles`)
- It runs at the same cadence (every minute via `STEPS_EVERY_MIN`)
- No new systemd timer or pipeline step needed

### Execution Flow

```
run_pipeline.py
  → breakout_engine.py (STEPS_EVERY_MIN)
    → Phase A: Existing compression→breakout detection (unchanged)
    → Phase B: Retroactive scan (NEW — runs after Phase A)
      → Collect open positions set
      → Collect existing signal tokens (from Phase A + cooldown DB)
      → For each token with recent candle data:
        1. Skip if delisted, blacklisted, has open position, or on loss cooldown
        2. Fetch last RETRO_LOOKBACK_BARS + 20 1m candles (need 20 for volume avg)
        3. Find the largest move in the lookback window
        4. Check candle body filter (reject dojis)
        5. Check volume (ratio + absolute floor)
        6. Check reversion guard
        7. Check RSI extreme
        8. Check no existing signal (same direction) or opposing signal
        9. Check cooldown via DB query
        10. Compute confidence
        11. If confidence >= RETRO_CONFIDENCE_FLOOR → emit signal
      → Write to DB via add_signal()
      → Write directly to hotset (own writer, NOT reusing breakout's writer)
```

### Signal Registration

The retroactive scan is NOT a separate signal in `signals/__init__.py`. It's part of breakout_engine.py's output. The signal_type written to DB is `retroactive_breakout` and the source is `retroactive-breakout`. This keeps it separate from fresh breakout signals for performance tracking.

### Scoring Integration

1. Add to `SIGNAL_SOURCE_WEIGHTS` in `signal_compactor.py`:
```python
('retroactive_breakout', 'retroactive-breakout'): 0.7,  # suppressed — delayed entry, lower conviction
```

2. Add to `STANDALONE_BYPASS_SIGNALS` in `hermes_constants.py`:
```python
'retroactive_breakout',  # allowed to fire without confluence — has its own volume/reversion gates
```

### Hotset Writer (OWN implementation — does NOT reuse breakout's writer)

The breakout engine's `write_to_hotset()` hardcodes `source: 'breakout'` and `signal_type: 'breakout_engine'` at lines 489-490. The retroactive scan must write its own hotset entry to preserve the correct source/type:

```python
def write_to_hotset_retro(signals: List[dict], dry: bool = False):
    """Write retroactive signals to hotset.json directly (not via breakout's writer)."""
    import fcntl
    HOTSET_PATH = HOTSET_FILE  # from paths.py
    entry = {
        'tokens': {},
        'updated_at': time.time(),
        'source': 'retroactive-breakout',
    }
    for sig in signals:
        entry['tokens'][sig['token']] = {
            'token': sig['token'],
            'direction': sig['direction'],
            'confidence': sig['confidence'],
            'source': 'retroactive-breakout',
            'signal_type': 'retroactive_breakout',
            'price': sig['price'],
            'entry': sig['entry'],
            'stop': sig['stop'],
            'target': sig['target'],
            'atr': sig['atr'],
            'timeframe': '1m',
            'retro_trade_size_mult': RETRO_SIZE_MULTIPLIER,
        }
    
    if not dry:
        fd = None
        try:
            fd = open(HOTSET_PATH + '.lock', 'w')
            fcntl.flock(fd, fcntl.LOCK_EX)
            # Read existing hotset, merge retro tokens
            existing = {}
            if os.path.exists(HOTSET_PATH):
                with open(HOTSET_PATH) as f:
                    existing = json.load(f)
            existing_tokens = existing.get('tokens', {})
            existing_tokens.update(entry['tokens'])
            entry['tokens'] = existing_tokens
            with open(HOTSET_PATH, 'w') as f:
                json.dump(entry, f, indent=2)
        except Exception as e:
            log(f"RETRO hotset write error: {e}")
        finally:
            if fd is not None:
                fcntl.flock(fd, fcntl.LOCK_UN)
                fd.close()
```

### DB Cooldown Query

```python
def _retro_on_cooldown(token: str) -> bool:
    """Check if token has a retroactive signal in the cooldown window."""
    import sqlite3
    from paths import RUNTIME_DB
    conn = sqlite3.connect(RUNTIME_DB, timeout=5)
    try:
        c = conn.cursor()
        cutoff = time.time() - (RETRO_COOLDOWN_MIN * 60)
        c.execute("""
            SELECT COUNT(*) FROM signals
            WHERE token = ? AND signal_type = 'retroactive_breakout'
              AND created_at >= ?
        """, (token.upper(), cutoff))
        return c.fetchone()[0] > 0
    except Exception:
        return False
    finally:
        conn.close()


def _retro_has_opposing_signal(token: str, direction: str) -> bool:
    """Check if token has an opposing signal in the last 5 minutes."""
    import sqlite3
    from paths import RUNTIME_DB
    opposing = 'SHORT' if direction == 'LONG' else 'LONG'
    conn = sqlite3.connect(RUNTIME_DB, timeout=5)
    try:
        c = conn.cursor()
        cutoff = time.time() - 300  # 5 minutes
        c.execute("""
            SELECT COUNT(*) FROM signals
            WHERE token = ? AND direction = ?
              AND created_at >= ?
        """, (token.upper(), opposing, cutoff))
        return c.fetchone()[0] > 0
    except Exception:
        return False
    finally:
        conn.close()
```

## 6. Risk Management

### Position Sizing
**NOTE**: The retroactive signal writes `retro_trade_size_mult` to `signal_metadata`. However, `decider_run.py` and `guardian` do NOT currently read this field. Two options:

- **Option A (recommended for v1)**: Use normal position sizing. The reduced source weight (0.7) already penalizes retroactive signals in hot-set ranking, making them less likely to be selected over fresh signals. Implement size multiplier in a future iteration after verifying guardian integration.
- **Option B**: Modify `decider_run.py` to read `signal_metadata.retro_trade_size_mult` and apply to `amount_usdt`. This requires changes outside the plan scope.

### Stop Placement
- ATR-based SL/TP uses the same `compute_levels()` function from breakout_engine.py
- SL is placed at `ATR * 1.5` from entry (same as breakout engine)
- **Tighter trailing**: retroactive entries activate trailing sooner
  - `RETRO_TRAIL_ACTIVATE_PCT = 0.25` (vs normal 0.40%)
  - `RETRO_TRAIL_DISTANCE_PCT = 0.15%` (vs normal 0.20%)
  - **NOTE**: Trailing parameters need guardian integration (not currently read). Use existing trailing params for v1. Mark as TODO.
- Rationale: delayed entries have less room — lock in profit faster

### Max Hold
**NOTE**: `RETRO_MAX_HOLD_MINUTES = 15` is defined as a constant but `position_manager.py` does NOT currently enforce per-signal-type max hold times. For v1, rely on existing SL/TP/trailing. Implement max-hold in a future iteration.

### ATR Floor
```python
atr = compute_atr(candles)
if atr <= 0 or math.isnan(atr):
    return None  # prevent degenerate SL/TP
```

## 7. Edge Cases

| Scenario | Behavior |
|----------|----------|
| **Move still in progress** | The scan looks at closed candles only (1m). If the current candle is still developing and is the spike, it will be caught on the next pipeline run when the candle closes. The scan does NOT fire on developing candles. |
| **Multiple tokens spike simultaneously** | Each token is scanned independently. Up to `RETRO_MAX_SIGNALS_PER_SCAN` (default 3) retroactive signals can fire per scan. Prevents a mass-spike event from flooding the hot-set. |
| **Same token spikes twice within cooldown** | Cooldown check prevents re-firing. Only the first spike generates a signal. If the second spike is larger and the first signal was already executed, the second spike is ignored (cooldown). |
| **Move reverses between scan and execution** | The reversion guard runs at scan time. If the move reverses AFTER the signal is written but BEFORE guardian picks it up, the normal staleness decay in signal_compactor kills it (10-min expiry). |
| **Breakout engine already caught it** | The "no existing signal" check prevents duplication. If breakout_engine already wrote a signal for this token+direction, the retroactive scan skips it. |
| **Opposing signal exists** | `spike_exhaustion_short` could fire SHORT while retro fires LONG on the same token. The `_retro_has_opposing_signal()` check blocks the retro signal if an opposing signal was written in the last 5 minutes. |
| **Token in blacklist** | Standard blacklist check — skipped. |
| **Volume data missing (V=0)** | If the spike candle has volume=0 (aggregator gap), vol_ratio check fails → signal blocked. This is correct: we can't confirm the move was real without volume. |
| **ATR is 0** | `compute_atr()` returns 0 with <15 candles. ATR floor check blocks the signal — prevents degenerate SL/TP at entry price. |
| **Token has open position** | Checked via `_get_open_tokens()` set. Signal blocked — don't double up. |
| **Token on loss cooldown** | Checked via `loss_cooldowns.json`. Signal blocked — don't re-enter a losing token. |
| **Hotset race condition** | The retro hotset writer acquires `FileLock` and merges with existing hotset entries. No data loss from concurrent writes. |

## 8. Config Parameters

All tunable values go in `hermes_constants.py`:

```python
# ── Retroactive Breakout Scan ─────────────────────────────────────────────────
# Secondary scan after breakout engine: catches missed moves with lower confidence.
# Plan: plans/retroactive-scan-delayed-entry.md

RETRO_ENABLED = True                     # master kill switch

# Move detection
RETRO_MIN_MOVE_PCT = 1.5                 # min single-candle move % to qualify
RETRO_LOOKBACK_BARS = 5                  # 1m candles to look back

# Candle body filter
RETRO_MIN_BODY_PCT = 0.30               # min candle body % (reject dojis)

# Reversion guard
RETRO_MAX_REVERSION_PCT = 40.0           # max % of move that can retrace before BLOCK
RETRO_REVERSION_CHECK_RSI = True         # also check RSI extremes

# Confidence scoring
RETRO_BASE_CONFIDENCE = 55               # base confidence for retroactive signals
RETRO_CONFIDENCE_FLOOR = 50              # minimum confidence (below = no signal)
RETRO_CONFIDENCE_CAP = 70                # maximum confidence (never exceeds fresh signals)
RETRO_AGE_PENALTY_PER_MIN = 2.0          # confidence penalty per minute of age
RETRO_REVERSION_PENALTY_MULT = 0.5       # confidence penalty per % reversion

# Volume filter
RETRO_VOL_MIN_RATIO = 1.5               # candle volume must be >= this × 20-bar avg
RETRO_MIN_VOL_ABS = 100                  # minimum absolute volume (prevents illiquid false positives)

# Cooldown / dedup
RETRO_COOLDOWN_MIN = 10                  # minutes between retro signals per token+direction
RETRO_MAX_SIGNALS_PER_SCAN = 3           # max retroactive signals per pipeline run

# Risk management
RETRO_SIZE_MULTIPLIER = 0.75             # position size = normal × this (TODO: needs guardian integration)
RETRO_TRAIL_ACTIVATE_PCT = 0.0025       # 0.25% — tighter than normal 0.40% (TODO: needs guardian integration)
RETRO_TRAIL_DISTANCE_PCT = 0.0015       # 0.15% — tighter than normal 0.20% (TODO: needs guardian integration)
RETRO_MAX_HOLD_MINUTES = 15             # auto-close timeout (TODO: needs position_manager integration)
```

## 9. File Changes

### Modify: `scripts/breakout_engine.py`

**Add imports** (top of file):
```python
import math
import json
import fcntl
```

**Add helper functions** (after `compute_levels`, ~line 317):
- `_compute_rsi(candles, period=14)` — RSI calculation (see Section 4)
- `_check_retro_reversion(candles, direction, spike_idx_in_full)` — reversion guard (see Section 4)
- `_compute_reversion_pct(candles, direction, spike_idx_in_full)` — reversion % (see Section 4)
- `_retro_on_cooldown(token)` — DB cooldown check (see Section 5)
- `_retro_has_opposing_signal(token, direction)` — opposing signal check (see Section 5)

**Add retroactive scan function** (after helper functions, ~line 385):
- `scan_retroactive(token, existing_signal_tokens, open_tokens, dry=False)` — full detection logic (see Section 10 pseudocode)

**Add to `run()` function** (after breakout signals loop, ~line 573):
```python
    # Phase B: Retroactive scan (after main breakout detection)
    retro_signals = []
    # Collect open positions
    open_tokens = set()
    try:
        from position_manager import get_open_positions
        open_tokens = {p['token'].upper() for p in get_open_positions()}
    except Exception:
        pass
    
    existing_tokens = {s['token'] for s in breakout_signals}
    for token in tokens:
        if token in existing_tokens or token in open_tokens:
            continue
        try:
            retro = scan_retroactive(token, existing_tokens, open_tokens, dry=dry)
            if retro and len(retro_signals) < RETRO_MAX_SIGNALS_PER_SCAN:
                retro_signals.append(retro)
        except Exception as e:
            if verbose:
                log(f"  [{token}] RETRO ERROR: {e}", 'WARN')
    
    if retro_signals:
        log(f"Retroactive scan: {len(retro_signals)} signals detected")
        write_signals_to_db_retro(retro_signals, dry=dry)
        write_to_hotset_retro(retro_signals, dry=dry)
```

**Add retroactive DB writer** (new function):
```python
def write_signals_to_db_retro(signals: List[dict], dry: bool = False):
    """Write retroactive signals to DB with retroactive_breakout signal_type."""
    from signal_schema import add_signal
    for sig in signals:
        add_signal(
            token=sig['token'],
            direction=sig['direction'],
            signal_type='retroactive_breakout',
            source='retroactive-breakout',
            confidence=sig['confidence'],
            value=sig.get('atr'),
            price=sig['price'],
            timeframe='1m',
            signal_metadata={'retro_trade_size_mult': RETRO_SIZE_MULTIPLIER},
        )
```

**Add retroactive hotset writer** (new function — does NOT reuse breakout's writer):
```python
def write_to_hotset_retro(signals: List[dict], dry: bool = False):
    """Write retroactive signals to hotset.json directly."""
    # See Section 5 for full implementation
```

### Modify: `scripts/hermes_constants.py`

**Add retroactive constants** after ATR TP/SL section (~line 512):
```python
# ── Retroactive Breakout Scan ─────────────────────────────────────────────────
# (all constants listed in Section 8)
```

**Add to `STANDALONE_BYPASS_SIGNALS`** (~line 1216):
```python
'retroactive_breakout',  # has its own volume/reversion gates
```

### Modify: `scripts/signal_compactor.py`

**Add source weight** to `SIGNAL_SOURCE_WEIGHTS` dict (~line 280):
```python
('retroactive_breakout', 'retroactive-breakout'): 0.7,
```

### Create: `tests/test_retroactive_scan.py`

Unit tests for: reversion guard, confidence scoring, cooldown, opposing signal check, RSI, body filter, ATR floor.

## 10. Pseudocode: Core Detection Logic

```python
def scan_retroactive(token, existing_signal_tokens, open_tokens, dry=False):
    if is_delisted(token):
        return None
    if token in existing_signal_tokens:
        return None
    if token in open_tokens:
        return None
    
    # Blacklist check (direction-aware)
    from hermes_constants import SHORT_BLACKLIST, LONG_BLACKLIST
    if token.upper() in SHORT_BLACKLIST and token.upper() in LONG_BLACKLIST:
        return None  # fully blacklisted, skip entirely
    
    # Note: direction-specific blacklist is checked AFTER direction is determined
    
    # Loss cooldown check — keys are "TOKEN:DIRECTION" format
    try:
        with open(os.path.join(HERMES_DATA, 'loss_cooldowns.json')) as f:
            loss_cooldowns = json.load(f)
        if any(k.startswith(token.upper() + ':') for k in loss_cooldowns):
            return None
    except Exception:
        pass
    
    # Cooldown check (DB)
    if _retro_on_cooldown(token):
        return None
    
    # Need enough candles for lookback + volume average
    candles = get_candles(token, '1m', bars=max(RETRO_LOOKBACK_BARS + 25, 30))
    if not candles or len(candles) < RETRO_LOOKBACK_BARS + 5:
        return None
    
    # Only scan closed candles (get_candles returns dicts without is_closed,
    # but DB candles are pre-closed — this filter is a safety no-op)
    closed = [c for c in candles if c.get('is_closed', True)]
    if len(closed) < RETRO_LOOKBACK_BARS + 5:
        return None
    
    recent = closed[-RETRO_LOOKBACK_BARS:]
    
    # Find the spike candle (largest absolute move)
    spike_idx = None
    spike_move = 0
    for i, c in enumerate(recent):
        if c['open'] <= 0:
            continue
        move = abs(c['close'] - c['open']) / c['open'] * 100
        if move > spike_move:
            spike_move = move
            spike_idx = i
    
    if spike_move < RETRO_MIN_MOVE_PCT or spike_idx is None:
        return None
    
    spike = recent[spike_idx]
    direction = 'LONG' if spike['close'] > spike['open'] else 'SHORT'
    
    # Direction-specific blacklist check
    if direction == 'SHORT' and token.upper() in SHORT_BLACKLIST:
        return None
    if direction == 'LONG' and token.upper() in LONG_BLACKLIST:
        return None
    
    # Body filter (reject dojis)
    body_pct = abs(spike['close'] - spike['open']) / spike['open'] * 100
    if body_pct < RETRO_MIN_BODY_PCT:
        return None
    
    # Volume check — average BEFORE the spike (correct window)
    spike_idx_in_full = len(closed) - RETRO_LOOKBACK_BARS + spike_idx
    vol_window_start = max(0, spike_idx_in_full - 20)
    vol_window = closed[vol_window_start:spike_idx_in_full]
    if not vol_window:
        return None
    avg_vol = sum(c['volume'] for c in vol_window) / len(vol_window)
    if avg_vol < RETRO_MIN_VOL_ABS:
        return None  # too illiquid
    vol_ratio = spike['volume'] / avg_vol
    if vol_ratio < RETRO_VOL_MIN_RATIO:
        return None
    
    # Reversion check
    if _check_retro_reversion(closed, direction, spike_idx_in_full):
        return None
    
    # RSI check
    if RETRO_REVERSION_CHECK_RSI:
        rsi = _compute_rsi(closed, 14)
        if direction == 'LONG' and rsi > 80:
            return None
        if direction == 'SHORT' and rsi < 20:
            return None
    
    # Last candle reversal check
    last = closed[-1]
    last_range = (last['high'] - last['low']) / last['open'] * 100 if last['open'] > 0 else 0
    if last_range > 0.5:
        if direction == 'LONG' and last['close'] < last['open']:
            return None  # bearish reversal
        if direction == 'SHORT' and last['close'] > last['open']:
            return None  # bullish reversal
    
    # Age (minutes since spike candle)
    age_minutes = (time.time() - spike['ts']) / 60
    if age_minutes > RETRO_LOOKBACK_BARS + 2:
        return None
    
    # Opposing signal check
    if _retro_has_opposing_signal(token, direction):
        return None
    
    # Reversion percentage
    reversion_pct = _compute_reversion_pct(closed, direction, spike_idx_in_full)
    
    # Confidence
    move_bonus = min(15, max(0, (spike_move - RETRO_MIN_MOVE_PCT) * 5))
    vol_bonus = min(10, max(0, (vol_ratio - 1.0) * 5))
    age_penalty = age_minutes * RETRO_AGE_PENALTY_PER_MIN
    reversion_penalty = reversion_pct * RETRO_REVERSION_PENALTY_MULT
    confidence = RETRO_BASE_CONFIDENCE + move_bonus + vol_bonus - age_penalty - reversion_penalty
    confidence = min(RETRO_CONFIDENCE_CAP, confidence)
    
    if confidence < RETRO_CONFIDENCE_FLOOR:
        return None
    
    # ATR floor check
    atr = compute_atr(candles)
    if atr <= 0 or math.isnan(atr):
        return None
    
    price = candles[-1]['close']
    if direction == 'LONG':
        stop = price - atr * 1.5
        target = price + atr * 1.5 * 1.5
    else:
        stop = price + atr * 1.5
        target = price - atr * 1.5 * 1.5
    
    return {
        'token': token.upper(),
        'direction': direction,
        'confidence': confidence,
        'entry': price,
        'stop': stop,
        'target': target,
        'atr': atr,
        'price': price,
        'spike_dt': spike['dt'],
        'spike_move_pct': round(spike_move, 2),
        'vol_ratio': round(vol_ratio, 1),
        'reversion_pct': round(reversion_pct, 1),
        'age_minutes': round(age_minutes, 1),
        'source': 'retroactive-breakout',
        'signal_type': 'retroactive_breakout',
        'timeframe': '1m',
        'timestamp': time.time(),
    }
```

## v1 Scope (What This Plan Actually Implements)

Due to integration complexity, the following are **deferred to future iterations**:
- Position size multiplier (needs guardian/decider_run changes)
- Tighter trailing params (needs guardian changes)
- Max hold timer (needs position_manager changes)

For v1, the retroactive signal uses normal sizing, normal trailing, and relies on existing SL/TP. The source weight (0.7) ensures it ranks below fresh signals. This is conservative — the signal fires but doesn't override risk management.

## 11. Testing

### Dry Run (no trades)
```bash
python3 scripts/breakout_engine.py --dry --verbose
tail -50 /var/www/hermes/logs/breakout_engine.log | grep RETRO
```

### Historical Replay
```bash
python3 scripts/breakout_engine.py --verbose --token IMX
# Expected: retroactive signal with conf ~58-62
```

### Unit Tests (`tests/test_retroactive_scan.py`)
- `test_reversion_guard_blocks_reversed_move()` — 50% reversion → BLOCKED
- `test_reversion_guard_allows_fresh_move()` — 10% reversion → PASS
- `test_confidence_capped_below_breakout()` — never exceeds 70
- `test_cooldown_prevents_duplicate()` — second spike within 10 min → skipped
- `test_opposing_signal_blocks()` — opposing SHORT signal exists → BLOCKED
- `test_body_filter_rejects_doji()` — 0.1% body → BLOCKED
- `test_atr_floor_blocks_zero_atr()` — ATR=0 → BLOCKED
- `test_volume_floor_blocks_illiquid()` — vol < 100 → BLOCKED
- `test_loss_cooldown_blocks()` — token in loss_cooldowns → BLOCKED

### Monitoring
```sql
SELECT signal_type, COUNT(*), 
       SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END) as wins,
       ROUND(AVG(pnl_usdt), 4) as avg_pnl
FROM trades 
WHERE signal_type = 'retroactive_breakout'
  AND close_time > NOW() - INTERVAL '7 days'
GROUP BY signal_type;
```
