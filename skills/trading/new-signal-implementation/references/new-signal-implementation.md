---
name: new-signal-implementation
description: Adding new signals to Hermes — fixed-param signals, per-token tuned signals, pattern signals (HH/HL, breakout, support/resistance, z-score momentum, fake-dump), and backtest methodology.
tags: [signals, hermes, implementation]
triggers:
  - add new signal to hermes
  - migrate signal from inline to registry
  - extract inline signal from signal_gen.py
  - dual implementation — wrong file patched
---

# New Signal Implementation in Hermes — UMBRELLA SKILL

This skill covers all signal types in Hermes. For detailed reference, see the files in `references/`.

---

## 1. Fixed-Param Signals

Pattern_scanner, EMA cross, RSI, volume anomaly. Each is a generator script that writes to `signals_hermes_runtime.db` via `add_signal()`.

**Architecture:**
```
standalone scanner script (or signal_gen function)
    ↓ reads local candles.db (zero HL API calls)
signal_schema.add_signal()  → signals_hermes_runtime.db
    ↓
signal_compactor.py  → hotset.json
    ↓
guardian → execution
```

**Entry:** confidence threshold + optional regime/wave filter
**Exit:** signal expires after 30 min

### Files to Create

1. **`scripts/{signal_name}_signals.py`** — detection engine, pure library, no external deps
2. **`scripts/run_{signal_name}_signals.py`** — standalone runner with all guards
3. **`scripts/backtest_{signal_name}.py`** — validation script

---

## 2. Critical Bugs Reference

### Bug #15: Dual Implementation — Patches Applied to Wrong File (2026-05-08)
**The RS signal case: patches to `signals/rs.py` didn't reach the live pipeline.**
Two separate RS implementations existed:
- `signals/rs.py` — new/migrated version, registered in `signals/__init__.py` → used by `signals_runner.py` CLI
- `rs_signals.py` — old version, imported directly by `signal_gen.py` (line 2234) → used by live pipeline

**Symptom**: Patches applied, CLI test showed correct behavior, but live pipeline stopped writing
RS signals entirely (last write: 4.5h ago, all 180 signals EXPIRED).

**Prevention checklist** — run BEFORE patching any signal module:
1. `grep -rn "import.*rs_signals\|from.*rs_signals\|from signals.rs" /root/.hermes/scripts/signal_gen.py`
   — checks if signal_gen imports this module directly
2. `grep -rn "import.*rs_signals\|from.*rs_signals" /root/.hermes/scripts/signal_compactor.py`
3. Check if `signals/__init__.py` registry references the NEW path — if so, check if signal_gen.py also imports the OLD path directly
4. After patching, run a live pipeline cycle and verify DB has fresh entries:
   `sqlite3 /root/.hermes/data/signals_hermes_runtime.db "SELECT MAX(created_at) FROM signals WHERE source LIKE 'rs-%';"`

**Rule**: The live pipeline (`signal_gen.py`) is the source of truth. `signals_runner.py` and `signals/__init__.py` are separate CLI tooling that may use different code paths. When patching a signal, ALWAYS patch the file that `signal_gen.py` imports.

### Bug #1: Cooldown Writer Receives Only Count
Scanner returns only `int` (count), caller loops over ALL tokens. **Fix:** Return `tuple[int, set[str]]` — both count AND tokens that fired.

### Bug #2: Multi-Indicator Array Alignment
Two indicators with different warm-up periods don't share the same starting candle index. **Fix:** Use `bisect` for O(log n) timestamp lookup. Never use offset arithmetic.

### Bug #5: Compression Detection — Relative vs Absolute Thresholds
Using relative to noisy baseline fails when spikes contaminate the prior window. **Fix:** Use absolute thresholds (volume < X, range% < Y).

### Bug #7: Stale Signal — Check Only the Most Recent Bar
Loop iterates over ALL bars, fires if ANY meets criteria. Old bars always eventually meet criteria. **Fix:** Only check the most recent bar.

### Bug #8: Trend-Persistence Signal — was_below Too Restrictive
"Price crossed from below" fails for coins in clear uptrend for hours. **Fix:** Dual-path: (A) strong acceleration bypasses purity check, (B) consistent persistence ≥X% of recent bars.

### Bug #14: Persistence + Gap-Growth Signal Catches Peaks
"Persistent above EMA + gap growing" fires at END of extension, not start. **Fix:** Add marginal acceleration check — latest bar-over-bar delta must exceed prior delta.

### Bug #10: Systemd Timer Setup
Use oneshot service + timer pattern. `Persistent=true` catches missed runs. Service MUST exist before timer activates.

### Bug #11: Crossing-Bar Consecutive Count Resets to Zero
At crossing bar, count resets to 0. **Fix:** Check prior bar's consecutive count, verify current bar crosses EMA.

### Bug #13: Bare print() Goes to pipeline.log
When signal script is imported as module, bare print() goes to captured stdout → pipeline.log. **Fix:** Write `_log()` helper that writes to both stdout and signals.log.

### Bug #12: Exhaustion Signal Fires ONLY at Crossing
Exhaustion signals fire at the MOMENT price crosses EMA. **Fix:** Historical simulation to verify — iterate bar-by-bar checking for exhaustion condition.

---

## 3. Signal Clustering Integration (REQUIRED)

**Every new signal MUST be added to the signal clustering system.** This ensures the tide detector, phase gate, and volatility gate can properly categorize and weight the signal.

### Step 1: Add to FAMILY_MAP

Edit `scripts/market_phase_gate.py` and add the new signal to the appropriate family:

```python
FAMILY_MAP = {
    'Trendline': ['tl_break', 'tl_break_long', 'tl_break_short', 'your_new_signal'],  # ← Add here
    'Bollinger': ['bb_bounce', 'bb_bounce_short'],
    'Momentum': ['momentum', 'fast_momentum', 'velocity', 'phase_accel'],
    # ... etc
}
```

**Which family?** Match the signal's logic:
- Breakout/trend signals → `Trendline`
- Mean reversion → `Bollinger`
- Speed/acceleration → `Momentum` or `Accelerate`
- Exhaustion/reversal → `Exhaustion`
- Copy-trading → `HL_Copy`
- Support/resistance levels → `Support_Resistance`

### Step 2: Add to signal_lifecycle_filter.py (if applicable)

Edit `scripts/signal_lifecycle_filter.py` and add the signal's lifecycle role:

```python
SIGNAL_LIFECYCLE = {
    # EARLY: fires before the move (needs wider SL)
    'your_early_signal': 'early',
    
    # CONCURRENT: fires during the move (normal SL)
    'your_concurrent_signal': 'concurrent',
    
    # LAGGING: fires after the move (tight SL)
    'your_lagging_signal': 'lagging',
}
```

### Step 3: Add to volatility_gate.py REGIME_SIGNALS (if applicable)

Edit `scripts/volatility_gate.py` and add the signal to the appropriate regime(s):

```python
REGIME_SIGNALS = {
    'FLAT': {'your_signal', ...},     # Works in low volatility
    'NORMAL': {'your_signal', ...},   # Works in normal volatility
    'HIGH': {'your_signal', ...},     # Works in high volatility
    'EXTREME': {'your_signal', ...},  # Works in extreme volatility
}
```

### Step 4: Add to tide_detector.py (if it has lead-lag patterns)

If the new signal has predictive relationships with other families, add to `scripts/tide_detector.py`:

```python
LEAD_LAG_RULES = [
    ...
    {'leader': 'YourFamily', 'follower': 'Bollinger', 'lag_days': 1, 'corr': 0.8},
]

PHASE_TRANSITIONS = {
    'YourFamily': {'next_phase': 'explosion', 'lag_days': 1, 'confidence': 0.8},
}
```

### Verification Checklist

After adding a new signal, verify clustering integration:

```bash
# 1. Test family mapping
python3 -c "from market_phase_gate import signal_family; print(signal_family('your_new_signal'))"
# Should print: Trendline (or whichever family you assigned)

# 2. Test lifecycle role
python3 -c "from signal_lifecycle_filter import get_lifecycle_params; print(get_lifecycle_params('your_new_signal'))"
# Should print: {'role': 'concurrent', ...}

# 3. Test volatility gate
python3 -c "from volatility_gate import should_trade; print(should_trade('BTC', 'your_new_signal'))"
# Should print: ('TRADE', 'NORMAL') or similar

# 4. Run tide auto-learner (if available)
python3 tide_auto_learner.py --dry
# Should NOT list your signal as "unknown"
```

---

## 4. Key Files

- `/root/.hermes/scripts/signal_gen.py` — main pipeline (ALWAYS check this for which signal files it imports directly)
- `/root/.hermes/scripts/signal_compactor.py` — hot-set scoring
- `/root/.hermes/scripts/signal_schema.py` — `add_signal()`, `record_cooldown_start()`
- `/root/.hermes/data/candles.db` — local candle data (`candles_1m`, `candles_5m`, etc.)
- `/root/.hermes/data/signals_hermes_runtime.db` — signals output
- `/root/.hermes/scripts/hermes_constants.py` — `SIGNAL_SOURCE_BLACKLIST`, `SHORT_BLACKLIST`
- `/root/.hermes/scripts/market_phase_gate.py` — **FAMILY_MAP** (signal → family mapping)
- `/root/.hermes/scripts/signal_lifecycle_filter.py` — **SIGNAL_LIFECYCLE** (signal → role mapping)
- `/root/.hermes/scripts/volatility_gate.py` — **REGIME_SIGNALS** (regime → signal sets)
- `/root/.hermes/scripts/tide_detector.py` — **LEAD_LAG_RULES** (predictive correlations)

## 5. References

- `references/new-signal-implementation.md` — fixed-param implementation guide
- `references/rs-signal-implementation.md` — support/resistance signal
- `references/per-token-signal-implementation.md` — per-token tuning workflow
