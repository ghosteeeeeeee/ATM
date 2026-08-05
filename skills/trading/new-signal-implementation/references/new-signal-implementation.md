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

## 3. Key Files

- `/root/.hermes/scripts/signal_gen.py` — main pipeline (ALWAYS check this for which signal files it imports directly)
- `/root/.hermes/scripts/signal_compactor.py` — hot-set scoring
- `/root/.hermes/scripts/signal_schema.py` — `add_signal()`, `record_cooldown_start()`
- `/root/.hermes/data/candles.db` — local candle data (`candles_1m`, `candles_5m`, etc.)
- `/root/.hermes/data/signals_hermes_runtime.db` — signals output
- `/root/.hermes/scripts/hermes_constants.py` — `SIGNAL_SOURCE_BLACKLIST`, `SHORT_BLACKLIST`

## 4. References

- `references/new-signal-implementation.md` — fixed-param implementation guide
- `references/rs-signal-implementation.md` — support/resistance signal
- `references/per-token-signal-implementation.md` — per-token tuning workflow
