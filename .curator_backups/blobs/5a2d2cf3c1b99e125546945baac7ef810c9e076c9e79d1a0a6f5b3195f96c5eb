---
name: self-contained-signals
description: Self-contained signal systems that own their own position tracking, exit decisions, and HL execution — running in parallel with the guardian rather than through it. For signals that need custom exit logic incompatible with the guardian's uniform ATR trailing stop.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [signals, hermes, execution, position-management]
    related_skills: [new-signal-implementation]
triggers:
  - add a signal that manages its own exits
  - signal needs custom stop loss or exit logic
  - zscore_pump pattern
  - self-contained trading system
  - signal owns its own position lifecycle
---

# Self-Contained Signal Systems

## The Core Problem

The standard signal pipeline (signal_gen → signal_compactor → hot-set → guardian) applies **uniform ATR-based trailing stops** to ALL positions. The guardian's `check_atr_tp_sl_hits()` closes positions based on `stop_loss` and `target` columns in `brain.trades` — it has no knowledge of which signal opened a position or what custom exit logic that signal needs.

**Result:** If you build a signal with custom exit logic (e.g., Guppy's fast-group flip exit, or zscore_pump's fixed 3%/2% SL-TP), the guardian's ATR stop runs in parallel and will override your intended exits.

## The Solution: Self-Contained Architecture

Signals that need custom exit logic run **completely outside the guardian's ATR system**, using their own:

1. **Own JSON tracker file** — source of truth for position state
2. **Own state machine** — compression → breakout → exit conditions
3. **Own HL execution** — `mirror_close()` calls that close positions on HL directly
4. **Own systemd timer** — independent scan + monitor loop
5. **Brain DB as secondary record** — written for audit/reconciliation, not read for decisions

```
self_contained_signal.py
    ├── Own JSON tracker (source of truth for position state)
    ├── scan_and_fire()      → mirror_open() on HL
    ├── add_position()       → writes to own JSON + brain DB
    ├── check_and_close()    → own exit conditions → mirror_close()
    └── systemd timer         → runs scan_and_fire + check_and_close each cycle
```

**Guardian's role:** Orphan cleanup only. It sees no HL position on next cycle → closes the brain DB record. No conflict.

## ⚠️ Pitfall: Signal Definition — Expansion, NOT Cross + Separation

When implementing Guppy MMA (or any EMA-group signal), **do NOT define the signal as "cross + separation."**

At the moment of cross, separation is near-zero by definition. By the time separation grows to a meaningful threshold, the cross is already 1-3 bars old.

The correct pattern:
1. Look back for a recent cross (within last 1-3 bars)
2. Measure separation **NOW** (after the cross has had room to develop)
3. Signal fires if separation is growing (expansion) AND meets minimum threshold

On 1m candles, max observed separation at cross across 20+ tokens was 0.4% — any floor above 0.5% produces zero signals. Test the actual separation distribution before setting thresholds.

Also: squeeze should mean "was expanding, now compressed" — not just "currently compressed." A market compressed for 140 bars is not in squeeze, it's ranging. Require prior expansion before compression to qualify as a true squeeze setup.

## ⚠️ Pre-Existing Bug: Guardian Exclusion List is Incomplete

`hl-sync-guardian.py` excludes ONLY `pump_hunter` in its orphan recovery logic. `position_manager.py` correctly excludes both `pump_hunter` AND `zscore_pump`. This means `zscore_pump` positions could trigger guardian orphan handling — a latent bug.

**When adding a new standalone signal, fix BOTH files:**
- `position_manager.py`: add the new signal to `signal NOT IN ('pump_hunter', 'zscore_pump', '{name}')`
- `hl-sync-guardian.py`: add the new signal AND fix `zscore_pump` to `signal NOT IN ('pump_hunter', 'zscore_pump', '{name}')`

Both files need updating — don't update one without the other.

## True Independent Live Trading: The GUPPY_LIVE Bypass

Both `pump_hunter` and `zscore_pump` use `--live` flags, but their `mirror_*` calls still check `is_live_trading_enabled()`. This means enabling live mode for either requires `LIVE_TRADING_ENABLED=True` globally — the whole system must be armed.

For a signal that needs to trade independently of the rest of the system, add an **env var bypass** in `hyperliquid_exchange.py`:

```python
# In mirror_open() and mirror_close():
if not is_live_trading_enabled():
    # Check per-signal bypass env vars
    bypass_signals = ['GUPPY_LIVE', 'ZS_PUMP_LIVE', 'PUMP_LIVE']
    if any(os.environ.get(v, '').lower() in ('1', 'true', 'yes')
           for v in bypass_signals):
        pass  # allow through
    else:
        return {"success": False, "message": "Live trading disabled"}
```

This gives true independence: `GUPPY_LIVE=1` + `LIVE_TRADING_ENABLED=False` → guppy places real trades, all other systems blocked.

The service file sets the env var:
```ini
[Service]
Environment=GUPPY_LIVE=1
```

## ⚠️ Gap: brain.py Places TP/SL Without Cleanup Path

`brain.py`'s `add_trade()` (lines 539-553) places TP and SL via `place_sl()`/`place_tp()` immediately on open, storing order IDs in `hl_sl_order_id`/`hl_tp_order_id`. **No cleanup exists** — when a position closes (via any path: guardian, manual, market fill), the TP/SL reduceOnly orders are NOT cancelled and become orphaned on Hyperliquid.

The guardian's orphan handler only manages brain DB ↔ HL position gaps — it does NOT cancel open TP/SL orders for rows that have no HL position.

**Fix:** Guardian orphan handler must cancel `hl_sl_order_id` and `hl_tp_order_id` when it finds a brain DB row with no HL position. See `references/orphaned-tp-sl-orders-gala-2026-05-17.md` for full incident details and live order IDs.

## Reference Implementations

There are two self-contained signal patterns. Use the first (`pump_hunter`) as the canonical example — it's the cleanest.

### Canonical: pump_hunter — Truly Standalone

`/root/.hermes/scripts/pump_hunter.py` — self-contained, no brain DB writes, owns its exits completely.

**What makes it "truly standalone":**
- Uses `LIVE_MODE` flag (`--live` arg or `PUMP_LIVE` env var) — separate from global `is_live_trading_enabled()`
- Own tracker JSON at `/var/www/hermes/data/pump_hunter_positions.json`
- Own HTML dashboard served via nginx at `/pump-hunter.html`
- Brain DB write happens ONLY after successful HL fill (not before like zscore_pump)
- Guardian and position_manager learn about positions AFTER the fact
- Excludes itself from position_manager via brain DB `signal='pump_hunter'` column

**Kill switch hierarchy (pump_hunter pattern):**
```
GUPPY_ENABLED flag  →  is_live_trading_enabled()  →  --live flag (explicit override)
```
The `--live` flag is the user's explicit override. Without it, the script logs signals but never calls `mirror_open()`.

### Variant: zscore_pump_hunter — Self-Managed with Brain DB Writes

`/root/.hermes/scripts/zscore_pump_hunter.py` — same pattern but writes to brain DB for tracking.

**Key differences from pump_hunter:**
- Writes brain DB record BEFORE HL trade (pre-creation pattern)
- Uses `ZS_PUMP_LIVE` env var for live mode toggle
- Same exclusion pattern in position_manager (signal='zscore_pump')

Both patterns are self-contained. Prefer pump_hunter as the reference.

### Architecture

```
/var/www/hermes/data/zscore-pump.json   ← own tracker (source of truth)
/root/.hermes/scripts/zscore_pump_hunter.py
    ├── scan_and_fire()        → reads candles.db, detects signal, mirror_open()
    ├── add_zs_position()      → writes JSON + brain DB simultaneously
    ├── check_and_close_positions() → own exit logic, mirror_close()
    └── main()                 → runs both scan and close each cycle
```

### Key Design Decisions in zscore_pump

**1. JSON tracker is the decision source, brain DB is audit only**

```python
# /var/www/hermes/data/zscore-pump.json — source of truth
{'positions': {TOKEN: {
    'token': 'BTC',
    'direction': 'LONG',
    'entry_price': 97432.50,
    'signal_source': 'zscore_pump',   # ← identifies origin
    'z_score': 2.34,
    'stop_price': 94509.47,           # fixed 3% SL
    'tp_price': 99380.75,             # fixed 2% TP
    'opened_at': 1746374400,
}}, 'closed': [...]}
```

**2. Dual-write on entry: JSON + brain DB**

```python
def add_zs_position(token, direction, signal, size, entry_price):
    # Write own tracker (decisions use this)
    data['positions'][token.upper()] = pos
    _write_json(data)
    
    # Write brain DB (audit / orphan recovery only)
    _create_brain_record(token, direction, ...)
```

**3. Own exit conditions, own mirror_close()**

```python
def check_and_close_positions():
    open_pos = get_open_zs_positions()  # reads own JSON
    
    for token, pos in open_pos.items():
        # zscore crosses 0 → exit
        curr_z = _get_zscore_at_bar(token, pos['lookback'])
        should_exit = (pos['direction'] == 'LONG' and curr_z <= 0) or \
                      (pos['direction'] == 'SHORT' and curr_z >= 0)
        
        if should_exit:
            remove_zs_position(token, 'ZS_CROSS', ...)  # updates JSON
            mirror_close(token, direction)               # closes on HL
```

**4. Brain DB record uses signal column for identification**

```python
cur.execute("""
    INSERT INTO trades (
        ...
        signal='zscore_pump',
        is_guardian_close=FALSE,
        guardian_closed=FALSE
    )
    WHERE NOT EXISTS (
        SELECT 1 FROM trades WHERE token=%s AND server='Hermes' AND status='open'
    )
""", ...)
```

This ensures:
- Guardian won't try to manage it (guardian reads `signal` column)
- If self-contained system closes first → guardian next cycle sees no HL position → orphan handler marks `HL_CLOSED`
- If guardian orphan handler runs first → self-contained system next cycle finds no HL position → its own JSON says "no position" → does nothing safely

**5. mirror_close() is idempotent**

`mirror_close()` returns `{"success": True}` even when there's no position to close. No error raised. Safe to call twice (once by self-contained system, once by guardian orphan handler on same token).

## Guardian Compatibility

**The guardian is safe to use as orphan cleanup** — it will never interfere with a self-contained signal's positions because:

1. Guardian orphan handler only fires when `HL position exists but no brain DB row` OR `brain DB row exists but no HL position`
2. Self-contained signal writes BOTH simultaneously → no orphan gap
3. When self-contained system closes → HL position gone → brain DB row updated → no orphan condition
4. Guardian's `check_atr_tp_sl_hits()` only operates on rows where `stop_loss`/`target` are set — self-contained signals set these to their OWN values, not the guardian's ATR values. The guardian would close at those values IF it reached the position first, but since the self-contained system manages its own closes, it closes first. Guardian next cycle: no position found.

**The one risk:** If guardian orphan handler runs BETWEEN the self-contained system's scan cycle and its close cycle (i.e., finds the position "orphaned" because the self-contained system updated brain DB but HL close hasn't propagated yet), it might try to close. This is mitigated by the 2-consecutive-cycle rule for paper orphans.

## position_manager Exclusion Pattern

`/root/.hermes/scripts/position_manager.py` already has hardcoded exclusion for self-managed signals. When adding a new self-managed signal, add its `signal` name to ALL FOUR SQL exclusion lists:

```python
# Lines ~259, ~283, ~307:
WHERE (signal IS NULL OR signal NOT IN ('pump_hunter', 'zscore_pump', 'guppy'))
```

**Also update `hl-sync-guardian.py`** — it needs the same exclusion in BOTH places (orphan recovery AND hard-stop). Currently it only has `pump_hunter` — this is the pre-existing bug.

```python
# In guardian.py ~line 607, 634, 1054:
signal NOT IN ('pump_hunter')  →  signal NOT IN ('pump_hunter', 'guppy')
```

**When adding a new signal, fix BOTH files and also add `zscore_pump` to guardian** to match position_manager's pattern.

## Per-Signal Kill Switch Architecture

T wants individual signal generators toggleable without disabling `LIVE_TRADING_ENABLED` (which gates the whole system).

### hermes_constants.py

```python
# Per-signal kill switches — True = signal generator runs normally
# False = signal generator is completely disabled (no signals generated)
SIGNAL_GENERATOR_ENABLED = {
    'mtf_macd':        True,
    'zscore_momentum':  True,
    'pattern_scanner':  True,
    'gap300':           True,
    'rsi':              True,
    'velocity':         True,
    'fast_momentum':    True,
    'phase_accel':      True,
    'oc_pending':       True,
    'ma_cross_5m':      True,
    'guppy':            False,  # ← new signals start disabled
}
```

### Usage pattern

```python
from hermes_constants import SIGNAL_GENERATOR_ENABLED

def _run_guppy_signals():
    if not SIGNAL_GENERATOR_ENABLED.get('guppy', False):
        return  # completely silent — no signals, no logs, no HL calls
    # ... rest of guppy signal logic
```

### Benefits
- Flip `SIGNAL_GENERATOR_ENABLED['guppy'] = True` → guppy scanning starts immediately
- All other signals unaffected
- `LIVE_TRADING_ENABLED = True` → guppy fires real trades
- Disabling a generator doesn't kill its in-flight positions — those are managed by the tracker's own close logic

## When to Use Self-Contained vs Standard Pipeline

| Factor | Standard Pipeline | Self-Contained |
|--------|------------------|-----------------|
| Exit logic | Guardian ATR (uniform) | Custom in own code |
| Position tracking | brain.trades only | Own JSON + brain DB |
| Timer | signal_gen pipeline | Own systemd timer |
| Example | MACD accel, HH/HL | zscore_pump, Guppy MMA |
| Counter-signals | Via signal_compactor | Own counter-exit logic |
| Testing needed | Backtest only | Backtest + live dry-run |

**Use self-contained when:**
- Signal needs fixed SL/TP (not ATR-based)
- Signal has custom exit conditions (e.g., indicator flip, regime change)
- Signal needs stateful compression detection across cycles
- Signal operates independently of other signals in the hot-set

**Use standard pipeline when:**
- Signal fits the ATR stop model
- Signal benefits from hot-set confluence scoring
- Multiple signals can share the same exit logic

## Files to Create

```
/root/.hermes/scripts/{name}_signals.py      # detection + own tracker
/systemd/system/hermes-{name}.service       # oneshot service
/systemd/system/hermes-{name}.timer          # periodic timer
```

## Checklist

- [ ] Own JSON tracker file (source of truth for position decisions)
- [ ] `signal_source` field set to unique signal name in brain DB writes
- [ ] `is_guardian_close=FALSE` in brain DB INSERT
- [ ] `mirror_close()` called from own check_and_close_positions()
- [ ] Systemd timer runs scan_and_fire AND check_and_close each cycle
- [ ] Guardian has no knowledge of this signal's position management
- [ ] Idempotency: safe if both self-contained system and guardian orphan handler both fire
