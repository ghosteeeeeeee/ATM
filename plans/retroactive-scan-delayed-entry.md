# Plan: Retroactive Breakout Scan / Delayed Entry

**Date:** 2026-08-20
**Status:** Open
**Priority:** High — safety net for missed breakouts (IMX +2.72% case)
**Parent:** `plans/imx-spike-detection.md` (Fix 3)

## 1. What It Does

After the main breakout engine runs its compression→breakout detection, a secondary "retroactive scan" checks every token for large moves that already happened but were missed by all signal generators. It looks backward over a short window (last 5–10 minutes) and emits a retroactive signal with lower confidence when: (a) a significant single-candle or multi-candle move occurred, (b) the move has not fully reversed, (c) no existing signal already covers this token+direction, and (d) the token is not on cooldown. This catches the "ice breaker" candle scenario where compression was broken by an earlier move, or the pipeline missed the exact candle due to timing.

## 2. When It Fires

A retroactive signal fires when ALL of these conditions are true:

| Condition | Threshold | Rationale |
|-----------|-----------|-----------|
| **Move size** | Single 1m candle: `abs(close/open - 1) * 100 >= RETRO_MIN_MOVE_PCT` (default 1.5%) OR cumulative 3-candle move >= `RETRO_MIN_CUM_MOVE_PCT` (default 2.0%) | The IMX case was +2.72% in one candle. 1.5% catches most meaningful spikes. |
| **Lookback window** | Last `RETRO_LOOKBACK_BARS` (default 5) 1m candles | Only catch fresh moves. Older moves are stale. |
| **Reversion guard** | Price has not retraced more than `RETRO_MAX_REVERSION_PCT` (default 40%) of the move from peak/trough | If price already reversed 40%+, the opportunity is gone. |
| **No existing signal** | No PENDING/APPROVED signal in `signals` table for same token+direction in last `RETRO_COOLDOWN_MIN` (default 10) minutes | Don't duplicate signals. Don't fire if breakout engine already caught it. |
| **Volume confirmation** | Candle volume >= `RETRO_VOL_MIN_RATIO` (default 1.5x) of 20-bar rolling average | Filters noise — real moves have volume. |
| **Not blacklisted** | Token not in SHORT_BLACKLIST/LONG_BLACKLIST | Standard safety. |
| **Not delisted** | `is_delisted(token)` returns False | Standard safety. |
| **Cooldown** | No retroactive signal for same token+direction in last `RETRO_COOLDOWN_MIN` minutes | Prevents repeated signals on the same move. |

### Direction Detection
- **LONG**: `close > open` on the spike candle (bullish)
- **SHORT**: `close < open` on the spike candle (bearish)
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
vol_bonus = min(10, (vol_ratio - 1.0) * 5)

confidence = base_conf + move_bonus + vol_bonus - age_penalty - reversion_penalty
confidence = max(RETRO_CONFIDENCE_FLOOR, min(RETRO_CONFIDENCE_CAP, confidence))
```

Default values produce:
- 1.5% move, 1 min old, 0% reversion, 2x vol → 55 + 0 + 5 - 2 - 0 = **58**
- 2.7% move, 2 min old, 10% reversion, 3x vol → 55 + 6 + 10 - 4 - 5 = **62**
- 1.5% move, 5 min old, 30% reversion, 1.5x vol → 55 + 0 + 2.5 - 10 - 15 = **32.5 → floored at 50**

This ensures retroactive signals sit below fresh breakout signals (70–95) in the hot-set ranking.

## 4. Reversion Guard

The reversion guard prevents firing on moves that already reversed. This is the most critical filter — without it, every exhausted spike becomes a false positive.

### Algorithm

```python
def check_reversion(candles, direction, spike_candle_idx):
    """
    Check if the move has reversed beyond threshold.
    
    For LONG spike: find the highest high after spike_candle_idx.
        reversion = (peak - current_close) / (peak - spike_open) * 100
        If reversion > RETRO_MAX_REVERSION_PCT → BLOCK
    
    For SHORT spike: find the lowest low after spike_candle_idx.
        reversion = (current_close - trough) / (spike_open - trough) * 100
        If reversion > RETRO_MAX_REVERSION_PCT → BLOCK
    """
```

### Additional Reversion Checks
1. **Last candle reversal**: If the most recent 1m candle is a strong reversal (close against signal direction with range > 0.5%), BLOCK immediately.
2. **RSI extreme**: If RSI(14) > 80 for LONG or < 20 for SHORT, BLOCK (overextended, likely to revert).

## 5. Integration Point

### Where It Runs

The retroactive scan runs **inside `breakout_engine.py`**, as a second pass after the main compression→breakout detection. This is the natural home because:
- It reuses the same candle-fetching infrastructure (`get_candles`)
- It writes to the same outputs (DB, OC pending, hotset)
- It runs at the same cadence (every minute via `STEPS_EVERY_MIN`)
- No new systemd timer or pipeline step needed

### Execution Flow

```
run_pipeline.py
  → breakout_engine.py (STEPS_EVERY_MIN)
    → Phase A: Existing compression→breakout detection (unchanged)
    → Phase B: Retroactive scan (NEW — runs after Phase A)
      → For each token with recent candle data:
        1. Fetch last RETRO_LOOKBACK_BARS 1m candles
        2. Find the largest move in the window
        3. Check reversion guard
        4. Check if any existing signal covers this token+direction
        5. Compute confidence
        6. If confidence >= RETRO_CONFIDENCE_FLOOR → emit signal
      → Write to DB via add_signal() with source='retroactive-breakout'
      → Write to hotset via write_to_hotset() (reuses existing function)
```

### Signal Registration

The retroactive scan is NOT a separate signal in `signals/__init__.py`. It's part of breakout_engine.py's output. The signal_type written to DB is `retroactive_breakout` and the source is `retroactive-breakout`. This keeps it separate from fresh breakout signals for performance tracking.

### Scoring Integration

Add to `SIGNAL_SOURCE_WEIGHTS` in `signal_compactor.py`:
```python
('retroactive_breakout', 'retroactive-breakout'): 0.7,  # suppressed — delayed entry, lower conviction
```

## 6. Risk Management

### Position Sizing
Retroactive signals use **reduced position sizing**:
- `RETRO_SIZE_MULTIPLIER = 0.75` — 75% of normal position size
- Applied at the signal level via `signal_metadata` field: `{'retro_trade_size_mult': 0.75}`
- Guardian/decider_run reads this and adjusts `amount_usdt` accordingly

### Stop Placement
- ATR-based SL/TP uses the same `compute_levels()` function from breakout_engine.py
- SL is placed at `ATR * 1.5` from entry (same as breakout engine)
- **Tighter trailing**: retroactive entries activate trailing sooner
  - `RETRO_TRAIL_ACTIVATE_PCT = 0.25` (vs normal 0.40%)
  - `RETRO_TRAIL_DISTANCE_PCT = 0.15` (vs normal 0.20%)
- Rationale: delayed entries have less room — lock in profit faster

### Max Hold
- `RETRO_MAX_HOLD_MINUTES = 15` — auto-close if neither SL nor TP hit in 15 minutes
- Retroactive entries are scalp-style: get in, get out

## 7. Edge Cases

| Scenario | Behavior |
|----------|----------|
| **Move still in progress** | The scan looks at closed candles only (1m). If the current candle is still developing and is the spike, it will be caught on the next pipeline run when the candle closes. The scan does NOT fire on developing candles. |
| **Multiple tokens spike simultaneously** | Each token is scanned independently. Up to `RETRO_MAX_SIGNALS_PER_SCAN` (default 3) retroactive signals can fire per scan. Prevents a mass-spike event from flooding the hot-set. |
| **Same token spikes twice within cooldown** | Cooldown check prevents re-firing. Only the first spike generates a signal. If the second spike is larger and the first signal was already executed, the second spike is ignored (cooldown). |
| **Move reverses between scan and execution** | The reversion guard runs at scan time. If the move reverses AFTER the signal is written but BEFORE guardian picks it up, the normal staleness decay in signal_compactor kills it (10-min expiry). |
| **Breakout engine already caught it** | The "no existing signal" check prevents duplication. If breakout_engine already wrote a signal for this token+direction, the retroactive scan skips it. |
| **Token in blacklist** | Standard blacklist check — skipped. |
| **Volume data missing (V=0)** | If the spike candle has volume=0 (aggregator gap), vol_ratio check fails → signal blocked. This is correct: we can't confirm the move was real without volume. |

## 8. Config Parameters

All tunable values go in `hermes_constants.py`:

```python
# ── Retroactive Breakout Scan ─────────────────────────────────────────────────
# Secondary scan after breakout engine: catches missed moves with lower confidence.
# Plan: plans/retroactive-scan-delayed-entry.md

RETRO_ENABLED = True                     # master kill switch

# Move detection
RETRO_MIN_MOVE_PCT = 1.5                 # min single-candle move % to qualify
RETRO_MIN_CUM_MOVE_PCT = 2.0            # min 3-candle cumulative move %
RETRO_LOOKBACK_BARS = 5                  # 1m candles to look back

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

# Cooldown / dedup
RETRO_COOLDOWN_MIN = 10                  # minutes between retro signals per token+direction
RETRO_MAX_SIGNALS_PER_SCAN = 3           # max retroactive signals per pipeline run

# Risk management
RETRO_SIZE_MULTIPLIER = 0.75             # position size = normal × this
RETRO_TRAIL_ACTIVATE_PCT = 0.0025       # 0.25% — tighter than normal 0.40%
RETRO_TRAIL_DISTANCE_PCT = 0.0015       # 0.15% — tighter than normal 0.20%
RETRO_MAX_HOLD_MINUTES = 15             # auto-close timeout

# Source weight in signal_compactor (add to SIGNAL_SOURCE_WEIGHTS dict)
# ('retroactive_breakout', 'retroactive-breakout'): 0.7,
```

## 9. Testing

### Dry Run (no trades)
```bash
# Run breakout engine with retroactive scan in dry mode
python3 scripts/breakout_engine.py --dry --verbose

# Check retroactive signals in log output
tail -50 /var/www/hermes/logs/breakout_engine.log | grep RETRO
```

### Historical Replay
```bash
# Test against known missed moves (IMX 2026-08-19 20:55 UTC)
python3 scripts/breakout_engine.py --verbose --token IMX

# Verify the scan detects the +2.72% move that was missed
# Expected: retroactive signal with conf ~58-62
```

### Unit Test
Create `tests/test_retroactive_scan.py`:
```python
def test_reversion_guard_blocks_reversed_move():
    """Move of 2% that reversed 50% should be BLOCKED."""
    # Mock candles with spike + reversion
    # Assert check_reversion returns True (blocked)

def test_reversion_guard_allows_fresh_move():
    """Move of 2% with 10% reversion should PASS."""
    # Mock candles with spike + minimal reversion
    # Assert check_reversion returns False (allowed)

def test_confidence_capped_below_breakout():
    """Retroactive confidence should never exceed RETRO_CONFIDENCE_CAP."""
    # Assert compute_retro_confidence returns <= 70

def test_cooldown_prevents_duplicate():
    """Second spike within cooldown window should be skipped."""
    # Mock DB with existing retroactive signal 5 min ago
    # Assert scan returns 0 new signals
```

### Monitoring
```bash
# Track retroactive signal performance
psql brain -c "
  SELECT signal_type, COUNT(*), 
         SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END) as wins,
         ROUND(AVG(pnl_usdt), 4) as avg_pnl
  FROM trades 
  WHERE signal_type = 'retroactive_breakout'
    AND close_time > NOW() - INTERVAL '7 days'
  GROUP BY signal_type
"
```

## 10. File Changes

### Modify: `scripts/breakout_engine.py`

**Add retroactive scan function** (after `detect_breakout_for_token`, ~line 385):
```python
def scan_retroactive(token: str, existing_signal_tokens: set, dry: bool = False) -> Optional[dict]:
    """
    Secondary scan: detect missed moves that the breakout engine didn't catch.
    Looks back RETRO_LOOKBACK_BARS 1m candles for large moves.
    Returns retroactive signal dict or None.
    """
    from hermes_constants import (
        RETRO_ENABLED, RETRO_MIN_MOVE_PCT, RETRO_LOOKBACK_BARS,
        RETRO_MAX_REVERSION_PCT, RETRO_VOL_MIN_RATIO, RETRO_COOLDOWN_MIN,
        RETRO_BASE_CONFIDENCE, RETRO_CONFIDENCE_FLOOR, RETRO_CONFIDENCE_CAP,
        RETRO_AGE_PENALTY_PER_MIN, RETRO_REVERSION_PENALTY_MULT,
        RETRO_MAX_SIGNALS_PER_SCAN,
    )
    if not RETRO_ENABLED:
        return None
    # ... implementation (see pseudocode below)
```

**Add to `run()` function** (after breakout signals loop, ~line 573):
```python
    # Phase B: Retroactive scan (after main breakout detection)
    retro_signals = []
    if not dry:
        # Collect tokens that already have breakout signals (skip them)
        existing_tokens = {s['token'] for s in breakout_signals}
        for token in tokens:
            if token in existing_tokens:
                continue
            try:
                retro = scan_retroactive(token, existing_tokens, dry=dry)
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
        )
```

**Add retroactive hotset writer** (reuses existing `write_to_hotset` with different params):
```python
def write_to_hotset_retro(signals: List[dict], dry: bool = False):
    """Write retroactive signals to hotset with retro scoring."""
    for sig in signals:
        sig['source'] = 'retroactive-breakout'
        sig['signal_type'] = 'retroactive_breakout'
    write_to_hotset(signals, dry=dry)
```

### Modify: `scripts/hermes_constants.py`

**Add retroactive constants** after ATR TP/SL section (~line 512):
```python
# ── Retroactive Breakout Scan ─────────────────────────────────────────────────
RETRO_ENABLED = True
RETRO_MIN_MOVE_PCT = 1.5
RETRO_MIN_CUM_MOVE_PCT = 2.0
RETRO_LOOKBACK_BARS = 5
RETRO_MAX_REVERSION_PCT = 40.0
RETRO_REVERSION_CHECK_RSI = True
RETRO_BASE_CONFIDENCE = 55
RETRO_CONFIDENCE_FLOOR = 50
RETRO_CONFIDENCE_CAP = 70
RETRO_AGE_PENALTY_PER_MIN = 2.0
RETRO_REVERSION_PENALTY_MULT = 0.5
RETRO_VOL_MIN_RATIO = 1.5
RETRO_COOLDOWN_MIN = 10
RETRO_MAX_SIGNALS_PER_SCAN = 3
RETRO_SIZE_MULTIPLIER = 0.75
RETRO_TRAIL_ACTIVATE_PCT = 0.0025
RETRO_TRAIL_DISTANCE_PCT = 0.0015
RETRO_MAX_HOLD_MINUTES = 15
```

### Modify: `scripts/signal_compactor.py`

**Add source weight** to `SIGNAL_SOURCE_WEIGHTS` dict (~line 280):
```python
    ('retroactive_breakout', 'retroactive-breakout'): 0.7,
```

### Create: `tests/test_retroactive_scan.py`

Unit tests for the reversion guard, confidence scoring, and cooldown logic.

## Pseudocode: Core Detection Logic

```python
def scan_retroactive(token, existing_signal_tokens, dry=False):
    if is_delisted(token):
        return None
    if token in existing_signal_tokens:
        return None
    
    # Check cooldown
    if _retro_on_cooldown(token):
        return None
    
    candles = get_candles(token, '1m', bars=30)
    if not candles or len(candles) < RETRO_LOOKBACK_BARS + 5:
        return None
    
    recent = candles[-RETRO_LOOKBACK_BARS:]
    
    # Find the spike candle (largest absolute move)
    spike_idx = None
    spike_move = 0
    for i, c in enumerate(recent):
        move = abs(c['close'] - c['open']) / c['open'] * 100
        if move > spike_move:
            spike_move = move
            spike_idx = i
    
    if spike_move < RETRO_MIN_MOVE_PCT:
        return None
    
    spike = recent[spike_idx]
    direction = 'LONG' if spike['close'] > spike['open'] else 'SHORT'
    
    # Volume check
    avg_vol = rolling_avg_vol(candles[:-RETRO_LOOKBACK_BARS + spike_idx + 1], window=20)
    if avg_vol <= 0:
        return None
    vol_ratio = spike['volume'] / avg_vol
    if vol_ratio < RETRO_VOL_MIN_RATIO:
        return None
    
    # Reversion check
    if _check_retro_reversion(candles, direction, spike_idx):
        return None
    
    # RSI check
    if RETRO_REVERSION_CHECK_RSI:
        rsi = _compute_rsi(candles, 14)
        if direction == 'LONG' and rsi > 80:
            return None
        if direction == 'SHORT' and rsi < 20:
            return None
    
    # Age (minutes since spike candle)
    age_minutes = (time.time() - spike['ts']) / 60
    if age_minutes > RETRO_LOOKBACK_BARS + 2:  # allow 2 min buffer
        return None
    
    # Reversion percentage
    reversion_pct = _compute_reversion_pct(candles, direction, spike_idx)
    
    # Confidence
    move_bonus = min(15, max(0, (spike_move - RETRO_MIN_MOVE_PCT) * 5))
    vol_bonus = min(10, max(0, (vol_ratio - 1.0) * 5))
    age_penalty = age_minutes * RETRO_AGE_PENALTY_PER_MIN
    reversion_penalty = reversion_pct * RETRO_REVERSION_PENALTY_MULT
    confidence = RETRO_BASE_CONFIDENCE + move_bonus + vol_bonus - age_penalty - reversion_penalty
    confidence = max(RETRO_CONFIDENCE_FLOOR, min(RETRO_CONFIDENCE_CAP, confidence))
    
    if confidence < RETRO_CONFIDENCE_FLOOR:
        return None
    
    # Compute ATR levels
    atr = compute_atr(candles)
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
