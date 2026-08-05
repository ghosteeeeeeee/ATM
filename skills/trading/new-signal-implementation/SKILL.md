---
name: new-signal-implementation
description: Adding new signals to Hermes — fixed-param signals, per-token tuned signals, pattern signals (HH/HL, breakout, support/resistance, z-score momentum, fake-dump), and backtest methodology.
tags: [signals, hermes, implementation]
triggers:
  - add new signal to hermes
  - migrate signal from inline to registry
  - extract inline signal from signal_gen.py
  - signals_runner not firing
  - dual-fire signals prevention
  - new fixed-param signal
  - standalone signal function
  - signal scanner implementation
  - new pattern signal
  - pct-hermes direction wrong
  - percentile rank signal timing
  - extreme z-score signal
  - "tweak signal params for specific market conditions"   # gap % miscalibration: refs: accel-300-gap-calibration-jun-2026.md
  - accel-300 not firing on sustained moves (BLUR, ME, AXS)  # refs: accel-300-sustained-moves-jun-2026.md
  - accel-300 wrong direction signal (SHORT when price is above EMA)  # refs: accel-300-stale-bar-bug-2026-06-25.md
  - signal fired hours after the actual condition was true (stale-bar bug)
  - live signal uses different logic than accel_300_signals.py
  - backward-scan detector fires in wrong direction
  - mtp-zscore signal design
  - multi-timeperiod z-score trend-following
  - z-score bounds per period (min/max)
  - trend-following vs mean-reversion z-score
  - scan_zscore_rising_signals() PITFALL: single full-array z-score is wrong — must iterate per-bar. See references/scan-zscore-pitfall.md
  - zscore_rising signal (acceleration-first, crossing+velocity) — PITFALL: signal fires on EMA cross momentum peak, not at start of move. Use acceleration/velocity instead.
  - refactor existing signal to hermes_constants (hardcoded locals shadow hermes_constants — discovered 2026-06-08 with accel_300.py)
  - Bug #15: dual implementation — patches to signals/rs.py don't reach live pipeline (signal_gen.py imports rs_signals.py, not signals/rs.py)
  - Bug #16: constant drift — signals/rs.py hardcoded constants diverge from hermes_constants.py (FIXED 2026-06-04)
  - mtp-zscore vs zscore_rising: different move types caught — grind vs spike
  - zscore_rising misses gradual grinds (XLM: +4.7% over 20 bars, z peaked at 1.96, never crossed TH=2.5)
  - rs-s-broken SHORT fires when price recovered above broken support: add price>level check inside `if broken:` to reclassify as bounce LONG. See references/rs-broken-level-recovery.md
  - zscore_rising excels at sharp spikes (SNX: z=2.52 crossing, fires cleanly)
  - mtp-zscore multi-LB ensemble catches grinds via LB=80 lagging mean; zscore_rising needs crossing

## mtp-zscore Reference Data

Backtest results for 10 winning tokens (DYDX, MON, BCH, NEAR, ENS, etc.) with recommended lookbacks (50/100/150), starting Z-score bounds, and tuning knobs: references/mtp-zscore-backtest.md
---

# New Signal Implementation in Hermes — UMBRELLA SKILL

This skill covers all signal types in Hermes. For detailed reference, see the files in `references/`.

---

## 1. Signal Architecture Overview

### 3-Layer Kill-Switch System

Every signal is protected by three independent layers:

| Layer | File | What it does |
|-------|------|-------------|
| 1 | `hermes_constants.py` `*_ENABLED` flags | Script-level gate — if False, `add_signal()` never called |
| 2 | `signal_schema.py` `add_signal()` | Per-source guard after blacklist — catches even if Layer 1 fails |
| 3 | `decider_run.py` execution gate | Final execution block — catches if signals somehow got through |

**Order of evaluation:**
1. `validate_source()` checks `SIGNAL_SOURCE_BLACKLIST` — if blocked, returns `'unknown'`
2. If NOT in blacklist, `add_signal()` Layer 2 guard checks `*_ENABLED` flags
3. At execution time, decider_run checks `*_ENABLED` flags again

**CRITICAL: Blacklist wins over flags.** If a signal is in `SIGNAL_SOURCE_BLACKLIST`, its `*_ENABLED` flag is never evaluated. To use a flag to control a signal, it MUST NOT be in the blacklist.

### Signal Directory: `scripts/signals/`

All signal generators live in `/root/.hermes/scripts/signals/`. This is the **canonical home** for signal scripts. The old architecture had signals embedded inline in `signal_gen.py` — new signals should always go in `scripts/signals/`.

**Registry pattern:** `/root/.hermes/scripts/signals/__init__.py` exports `SIGNAL_REGISTRY`, `get_registered_signals()`, and `run_all_signals()`.

**Wiring into pipeline:** `run_pipeline.py` calls `signal_gen.py` which calls individual signal scripts. The `scripts/signals/` registry can be called in parallel or as a migration step.

### Kill-Switch Flag Naming Convention

```
{SIGNAL}_ENABLED          = True   # master kill-switch (optional if directional flags exist)
{SIGNAL}_PLUS_ENABLED     = True   # LONG direction only
{SIGNAL}_MINUS_ENABLED    = False  # SHORT direction only
```

**Three valid configurations:**
| Config | Blacklist | Flag | Result |
|--------|-----------|------|--------|
| Permitted | Not in list | True | Signal passes |
| Kill-switch controlled | Not in list | False | Signal blocked by flag |
| Permanently blocked | In list | Irrelevant | Signal blocked by blacklist |

**Never do this:** Put a signal in both the blacklist AND set its flag to True — the blacklist wins every time.

---

## 1. Fixed-Param Signals

Pattern_scanner, EMA cross, RSI, volume anomaly. Each is a generator script that writes to `signals_hermes_runtime.db` via `add_signal()`.

**Constants management:** All signal thresholds that may differ by direction (LONG vs SHORT) MUST be defined in `hermes_constants.py` as `MIN_GAP_PCT_LONG` / `MIN_GAP_PCT_SHORT` (or equivalent) and imported. Never define direction-specific thresholds as local constants in the signal script — it makes them invisible to the rest of the system. Example:
```python
# WRONG — hardcoded locally
MIN_GAP_PCT = 0.10

# RIGHT — centralized in hermes_constants.py, imported
from hermes_constants import MIN_GAP_PCT_LONG, MIN_GAP_PCT_SHORT
min_gap = MIN_GAP_PCT_LONG if direction == 'LONG' else MIN_GAP_PCT_SHORT
```

**Refactor pattern (existing signals with hardcoded locals):** If a signal file has local constants at the top that differ from hermes_constants values, the local ones take precedence and hermes_constants becomes a dead tuning layer. Fix: import from hermes_constants and alias to local names at the top of the file and inside `detect_*`. See `references/hardcoded-constants-refactor-2026-06-08.md` for full procedure (discovered during accel_300.py audit, 2026-06-08).

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

### CRITICAL: Every module MUST have a `run()` function

`signals_runner` calls `getattr(mod, 'run', None)` to execute each signal. If the
module has no `run()`, the signal is **silently skipped** every cycle — no error, no
log, nothing. The signal appears registered and enabled but never fires.

```python
def run() -> int:
    """Entry point for signals_runner. Returns count of signals written."""
    prices = get_all_latest_prices()
    return scan_xxx_signals(prices)
```

**Always verify after adding a new signal:**
```python
mod = __import__(f'signals.{name}', fromlist=[''])
assert hasattr(mod, 'run'), f"signal {name} has no run() function!"
```

This caught `accel_300` dead for weeks (2026-05-07). 13 other signals had the same
issue: `rs`, `ma_cross`, `ma_cross_5m`, `hh_hl`, `guppy`, `macd_accel`,
`trend_purity`, `phase_accel`, `fast_momentum`, `momentum`, `mtf_momentum`, `hmacd`.
Standalone signal modules live in `scripts/signals/` and are wired into the pipeline via `signals/__init__.py`'s `SIGNAL_REGISTRY`. This is the preferred pattern for any signal extracted from `signal_gen.py`.

**Required exports:**
- `run(prices_dict: dict) -> int` — main entry, returns number of signals written
- Optionally: `detect_{name}(...)` for pure detection logic

**sys.path trick for `scripts/signals/` subdirectory:**
```python
# Scripts in scripts/signals/ need parent directory on path
# to resolve signal_schema, signal_gen, hermes_constants
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```

**Registry integration (in `signals/__init__.py`):**
```python
from hermes_constants import PHASE_ACCEL_ENABLED
# ...
SIGNAL_REGISTRY = [
    # ...
    {'name': 'phase_accel', 'enabled': PHASE_ACCEL_ENABLED, 'run': phase_accel.run},
]
```

**Phase-acceleration signals** (phase == 'accelerating' AND prev_phase != 'accelerating'):
- Source tags: `phase-accel+` (LONG), `phase-accel-` (SHORT)
- Signal types: `phase_accel_long`, `phase_accel_short`
- Direction: `momentum_state == 'bullish'` → LONG, `bearish` → SHORT
- Constants: `PHASE_ACCEL_PLUS_ENABLED`, `PHASE_ACCEL_MINUS_ENABLED`
- Required helper: `_get_previous_phase(token)` reads `prev_phase` column from `momentum_cache` — NOT the `phase` column (which has been overwritten by the current pipeline run)

## Files to Create
**Exit:** signal expires after 30 min

### Critical: Every Signal Module MUST Have a `run()` Function

`signals_runner` dispatches via `getattr(mod, 'run', None)`. If the module has no `run()`,
the signal is **silently skipped** every cycle — no error, no log. Most dangerous class of bug.

The `_run_signal()` wrapper in `signals/__init__.py`:
```python
mod = __import__(f'signals.{module_name}', fromlist=['run'])
fn = getattr(mod, 'run', None)  # ← scans for 'run' attribute
if fn is None:
    return sig_name, None        # ← SILENT SKIP
```

**Every signal module must export:**
```python
def run(prices_dict=None) -> int:
    """Entry point for signals_runner via _run_signal() getattr dispatch."""
    from signal_schema import get_all_latest_prices
    prices = get_all_latest_prices() if prices_dict is None else prices_dict
    added, tokens = scan_xxx_signals(prices)
    return added
```

## Key Lesson from This Migration
A signal can be **fully wired** (registered, in name_to_module, all imports correct, no errors) and still not fire — because the master kill-switch (`ZSCORE_PUMP_ENABLED`) is False. Same silent-fail pattern as `accel_300` missing its `run()` function.

**Always check the master kill-switch first** when a registered signal isn't firing:
```bash
grep "ZSCORE_PUMP_ENABLED" /root/.hermes/scripts/hermes_constants.py
```

Per-direction flags (`ZSCORE_PUMP_PLUS_ENABLED`, `ZSCORE_PUMP_MINUS_ENABLED`) being True is necessary but not sufficient — the master flag must also be True.

The `signals_runner` forks as a background process every minute via systemd timer — output goes to journalctl, NOT to `pipeline.log`. Use `journalctl -u hermes-pipeline -f` to follow signal output.

**Known signals missing `run()`**: guppy (has `scan_all_tokens`), rs (has `scan_rs_signals`).
Both need a wrapper. The skill's backtest scripts (run_xxx_signals.py) are separate from the
live pipeline entry point — don't confuse the two.

### Files to Create

1. **`scripts/signals/{signal_name}.py`** — detection engine, calls `add_signal()` directly. Has Layer 1 kill-switch at top of `run()`.
2. **`scripts/run_{signal_name}_signals.py`** — standalone runner with all guards (optional, for cron/standalone use)
3. **`scripts/backtest_{signal_name}.py`** — validation script

### Standalone Signal Scripts (signals/ directory)

These scripts own their own token iteration (call `get_all_latest_prices()` internally,
loop tokens, call `add_signal()` directly). Each exports `run() → int`.

| Script | Signal Type | Source Tags | Notes |
|--------|-------------|-------------|-------|
| `hmacd.py` | `hmacd` | `hmacd+`, `hmacd-` | 15m+1H histogram agreement, per-token tuned MACD |

### Step-by-step: Fixed-Param Scanner

```python
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

---

## 2. Per-Token Tuned Signals

Scanner + tuner DB + systemd timer pattern. Parameters tuned per-token based on backtest data stored in `per_token_params.db`.

**Architecture:**
```
backtest script (one-shot or cron)
    ↓ writes best params
tuner DB table (token_best_config_1m)
    ↓ read at startup
signal_gen.py standalone function (_run_xxx_signals)
    ↓ fires signals via add_signal()
signals DB
    ↓
signal_compactor.py (routes to hot-set scoring)
    ↓
ai-decider / guardian (execution)
```

### Key Steps

1. **Design the signal** — direction, timeframe, data source, backtest metric
2. **Run per-token backtests** — param grid sweep, pre-load all closes for speed
3. **Store best params in DB** — dedicated table per timeframe
4. **Write standalone function** in `signal_gen.py` — module-level cache, reset each run
5. **Wire into run() pipeline**
6. **Add to signal_compactor routing** — `SIGNAL_SOURCE_WEIGHTS`
7. **Create tuner script** with systemd timer

### Minimum signal count for tuning: n ≥ 15

- n=5 was far too lenient — tokens with 5 signals showing 100% WR are pure noise
- After bump to n=15: avg WR dropped from 69.6% to 58.0% — honest numbers

---

## 0b. Registering in signals/__init__.py (CRITICAL — 2026-05-08)

When adding a new signal module, you MUST register it in `scripts/signals/__init__.py`
in TWO places: the import block AND `SIGNAL_REGISTRY`.

**Step 1 — Import the run function:**
```python
try:
    from signals.my_signal import run as _my_signal_run
except Exception:
    _my_signal_run = None
```

**Step 2 — Add to SIGNAL_REGISTRY:**
```python
SIGNAL_REGISTRY: list[dict] = [
**Step 2 — Add to `name_to_module` in `run_all_signals()`:**
The `name_to_module` dict in `__init__.py` maps signal names to module names for `_run_signal()` dispatch. **If a signal is missing from `name_to_module`, its result is silently dropped** — `run_all_signals()` returns nothing for that signal, no error, no log.
```python
name_to_module = {
    # ... existing ...
    'zscore_pump': 'zscore_pump',  # ← add here
}
```

**Step 3 — Add to registry** (add after existing entries in the list):
```python
{'name': '{name}', 'enabled': {NAME}_ENABLED, 'run': _{name}_run},
```

**CRITICAL: Use a flag name STRING, not `True` or `False`.**

**WRONG (dual-flag problem):**
```python
{'name': 'my_signal', 'enabled': True, 'run': _my_signal_run}  # ignores hermes_constants!
```

**Also update `_SLOW_SIGNALS` if applicable:**
If the new signal is slow (>10s for 191 tokens), add its name to `_SLOW_SIGNALS`
at the top of `get_slow_signals()` — otherwise it runs every minute and burns CPU.

---

## 3. Signal Naming Convention

- `+` = LONG, `-` = SHORT
- `signal_type`: snake_case, descriptive (e.g., `ma300_candle`, `rsi_threshold`)
- `source` tag: includes key params for debugging (e.g., `ma300c-confirm2@sep0.5`)

**Blacklist rule (DEPRECATED — use kill-switch flags):**

`SIGNAL_SOURCE_BLACKLIST` is **commented out entirely** — the 3-layer kill-switch architecture makes it redundant. Keep the commented structure for historical reference.

**Critical pitfall — removing from blacklist is NOT enough to unblock:**
A signal can be blocked at two independent layers: (1) `*_ENABLED` flag in hermes_constants.py, (2) blacklist in hermes_constants.py. If `pct-hermes-` is removed from blacklist but `PCT_HERMES_MINUS_ENABLED=False`, it stays blocked. To unblock: remove from blacklist AND set the flag to True.

**Critical pitfall — "REMOVED" comment ≠ entry removed:**
The blacklist has two separate sections. A comment saying "REMOVED" at one location does NOT mean the entry is gone from the other section. Always verify by checking `python3 -c "from hermes_constants import SIGNAL_SOURCE_BLACKLIST; print('pct-hermes+' in SIGNAL_SOURCE_BLACKLIST)"`.

### Named Variants

| Source | Direction | Trigger |
|--------|-----------|---------|
| `hh_hl_breakout` | `hhh-long{N}`, `hhh-short{N}` | Price breaks above last swing high (HH) or below last swing low (LL) |
| `hh_hl_pullback` | `hhp-long{N}`, `hhp-short{N}` | Price pulls back to prior swing level in established structure then bounces |
| `fake_dump` | SHORT only | RSI crashes from overbought to oversold, bounces, then real crash |
| `zscore_momentum` | `zscore+`, `zscore-` | z > threshold = LONG momentum, z < -threshold = SHORT momentum |
| `zscore_pump` (pipeline, migrated 2026-05-16) | `zscore-pump+` (LONG), `zscore-pump-` (SHORT) | Migrated from standalone executor. Uses price_history, per-token tuned lookback (10-60 bars), threshold 1.5-4.0, min 15 signals. Guardian-aware — no standalone position conflicts. See `references/zscore-pump-migration-2026-05-16.md` |
| `ema_angle` | `ema-angle+`, `ema-angle-` | EMA300 angle crosses its own percentile threshold with positive angle_speed (slope rising), fires on steep + rising EMA — very sparse, ~2×/week per token |
| `zscore_momentum` | `zscore+`, `zscore-` | z > threshold = LONG momentum, z < -threshold = SHORT momentum |
| `zscore_pump` (pipeline, migrated 2026-05-16) | `zscore-pump+` (LONG), `zscore-pump-` (SHORT) | Migrated from standalone executor. Uses price_history, per-token tuned lookback (10-60 bars), threshold 1.5-4.0, min 15 signals. Guardian-aware — no standalone position conflicts. See `references/zscore-pump-migration-2026-05-16.md` |
| `breakout` | LONG/SHORT | Volume spike confirms compression break |

---

## 4. Backtest Methodology

### Survival Analysis Before Fixed TP/SL

**Critical principle: Exit on reverse cross, NOT fixed TP/SL.**

Fixed exits clip winners and misclassify reversals as "stop losses." This creates misleading win rates (70%+ WR on paper) while net P&L is catastrophic.

Correct methodology: **exit on reverse signal** — models T's "book profit fast" philosophy, produces realistic WR (18-30%) and accurate P&L.

### Multi-Pair Sweeps

Load all token closes once, sweep across param grid:
- EMA cross: test (8,50), (12,50), (20,50), (20,200) pairs
- MACD: Fast=2-10, Slow=8-40, Signal=3-8, Hold=10-60
- Always pre-compute EMA/MACD lines once per token — numpy vectorization for speed

### Directional Asymmetry

Test LONG and SHORT separately. They often have opposite outcomes:
- MA cross: SHORTS dominate across all pairs (+4984% net vs LONGS -1800%)
- MACD 1m: SHORT WR=59%, LONG WR=48.5%
- Always let empirical results decide — do not assume symmetry

### Regime Filtering

- Test signals only in appropriate market regime
- ADX+DI: NOT VIABLE — WR consistently ~42-44%, too many false signals in ranging markets
- Filter by z-score threshold: z > 3.0 blocks nearly all signals; z > 2.0 is the sweet spot

### Asymmetric Thresholds

When LONG and SHORT have asymmetric performance, use separate constants:
```python
MIN_GAP_PCT_LONG  = 0.008  # ROC threshold for LONG
MIN_GAP_PCT_SHORT = None   # Disabled — SHORT PNL negative across all X
HOLD_BARS         = 60     # Exit after 60 bars regardless of profit
```

### Lucky Sampling Warning

~5 days of 5m data can lucky-sample. Always validate:
1. Split-sample: 7d train → 7d test (verified sign consistency)
2. Multi-token sweep: 9+ tokens × 20k+ bars
3. Edge metric: `net_edge = (L_pnl*L_n + S_pnl*S_n)/(L_n+S_n)` — prioritizes direction consistency over raw count

### Small Sample Fallacy Kills Live Performance (2026-05-07)
pct-hermes+ was added to GOOD_STANDALONE_SIGNALS based on **3 trades at 100% WR**.
Live outcome: **64 trades, 4.7% WR, -52.9% avg_pnl**. A 3-trade sample cannot
establish reliability. **Rule: never add a signal to GOOD_STANDALONE_SIGNALS with
fewer than 30+ trades AND require WR >= 40% AND avg_pnl > 0.** Even then,
validate with live SQL against signal_outcomes before committing.

### Good_Standalone_Signals Values Are Stale by Definition (2026-05-07)
The hardcoded `{'wr': XX, 'avg': Y.Y}` in signal_compactor.py is a snapshot from
the last audit. Live outcomes diverge daily. The May 6 audit said pct-hermes-
had 35% WR. Live May 6-7 data: **0% WR across 14+ trades**. Always re-query
signal_outcomes before trusting those values:
```sql
SELECT signal_type, direction, COUNT(*) cnt, SUM(is_win) wins,
       ROUND(100.0*SUM(is_win)/COUNT(*),1) wr,
       ROUND(100.0*AVG(pnl_pct),3) avg_pnl
FROM signal_outcomes
WHERE created_at > datetime('now', '-7 days')
GROUP BY signal_type, direction
HAVING cnt >= 10
ORDER BY wr DESC, avg_pnl DESC;
```

### Market Regime Dominates Signal Quality (2026-05-07)
System WR collapsed: Mar ~53% → Apr ~25% → Apr-end ~14% → May 5-7 ~0%.
Root cause: strong bullish regime in early May 2026.
- SHORT signals crushed: pct-hermes- fires at market bottoms, price rips higher → SL hit
- pct-hermes+ fires at market tops, price mean-reverts in trending market → SL hit
- accel-300+ fires near momentum peaks, subsequent reversal → SL hit
**Implication**: A signal can be mechanically correct yet unprofitable in the wrong
regime. Raising PCT_RANK_THRESH (88→95) was wrong direction — it only catches
the most extreme prints, which mean-revert harder in trending markets. Consider
reverting thresholds in strong trends rather than tightening them.

---

## 7. Co-Signal Analysis (Audit-Driven)

Before modifying co-signal logic, run the full audit on `trades` table. See `../hermes-signal-debugging/references/co-signal-audit-2026-05-06.md` for complete methodology and findings.

### Winning Combos (2026-05-06 audit, 742 trades)

| Combo | Dir | Trades | WR | Avg% |
|-------|-----|--------|-----|------|
| `accel-300+,trend_purity+` | LONG | 8 | 62.5% | +0.36% |
| `accel-300+,hzscore-` | LONG | 30 | 36.7% | +0.66% |
| `hzscore+,pct-hermes-,vel-hermes-` | SHORT | 39 | **46.2%** | +0.38% |
| `gap-300-` | LONG | 75 | 40.0% | +0.22% |

### Poison Combos — Block in signal_compactor.py

| Combo | WR | Avg% | Fix |
|-------|-----|------|-----|
| `hzscore+,vel-hermes-` (no pct-hermes-) | 20% | −0.064% | Require `pct-hermes-` |
| `accel-300+,ma-cross-5m+` | 16.7% | −0.32% | Block entirely |
| `accel-300+,pct-hermes+` (no trend_purity+) | 35.7% | −0.26% | Require `trend_purity+` |

### ATR Trailing Stop Issue on `accel-300+,hzscore-`

Winners hold 43 min avg, losers 21 min. Losers getting stopped in 4-8 min before momentum develops.
Signal is 99% confident but market needs time. EIGEN held 139 min → +6.65%.

## 8. Pattern Signals

### 5a. HH/HL Structure (hh-hl-signal)

**Source:** `hhh-long{N}`, `hhh-short{N}`, `hhp-long{N}`, `hhp-short{N}`

Higher Highs / Higher Lows breakout and pullback signals. Detects swing highs/lows using proxy method (close-only data), fires when price breaks the last swing level.

**Key params (from hermes_constants.py):**
```python
HH_HL_LOOKBACK = 200      # candles for swing detection (~3h20m at 1m)
HH_HL_SWING_WINDOW = 4    # close-only: 4 beats 8
HH_HL_BREAKOUT_THRESHOLD = 0.0005  # 0.05% breakout required
HH_HL_MAX_BARS_SINCE = 10  # reject stale breakouts
HH_HL_COOLDOWN_MIN = 15
HH_HL_BASE_CONFIDENCE = 62
```

**Backtest results (13 tokens, 30 days):** 53.0% WR overall, +84.13% net. LONG 54.4%, SHORT 51.8%. BTC/SOL slightly negative. SCR LONG WR: 70.1%.

**Key finding:** All 2611 trades timed out — TP/SL levels too wide for 1m close-only volatility. TP_ATR_MULT sweep needed.

### 5b. Compression-Breakout (breakout-signal)

**Source:** `breakout-long`, `breakout-short`

Detects coiled price in tight range with low volume, fires when volume spike confirms the move.

**5m wins decisively over 1m:**
| Timeframe | Trades | Win Rate | Total PnL | W/L Ratio |
|-----------|--------|----------|-----------|-----------|
| 1m        | 7      | 57%      | -0.56%    | 0.47      |
| **5m**    | **29** | **55%**  | **+5.40%**| **1.49**  |

**Default 5m params:**
```
COMPRESSION_BARS_5m: 6      # 30-min coil
VOL_SPIKE_THRESHOLD:  0.3   # vol < 30% of avg = compressed
VOL_POP_THRESHOLD:    3.0   # breakout vol > 3x compressed vol
BREAKOUT_RANGE_PCT:   0.5%  # min candle range to qualify
```

**Critical:** Compression thresholds must be absolute, not relative. Using relative to a noisy baseline fails when spikes contaminate the prior window.

### 5c. Support/Resistance (rs-signal)

**⚠️ CRITICAL: rs.py has its own constants — NOT imported from hermes_constants.py**

The `signals/rs.py` file defines its own local constants (lines 35-41) that **diverge** from `hermes_constants.py`:

| Constant | rs.py (local) | hermes_constants.py | Effect |
|----------|--------------|---------------------|--------|
| `RS_PROXIMITY_K` | `0.70` | `1.20` | rs.py fires on tighter proximity than hermes_constants allows |
| `RS_ATR_PERIOD` | `14` | `30` | Different ATR normalization |
| `RS_LEVEL_LOOKBACK` | `20` | `300` | Different swing detection window |
| `RS_MIN_TOUCHES` | `3` | `8` | rs.py accepts weaker levels |
| `RS_CLUSTER_ATR` | `0.50` | `0.75` | Tighter clustering in rs.py |

**This is a persistent architectural desync.** When modifying RS behavior, check BOTH files. The signal_compactor.py reads hermes_constants. The rs.py signal scanner uses its own local values. Always verify rs.py constant values directly — do not assume hermes_constants changes propagate.

**Fix direction:** rs.py should import these from hermes_constants. Until then, treat rs.py's local constants as the source of truth for the RS signal itself.

**⚠️ CRITICAL: price_history is close-only data**
The `signals_hermes.db` price_history table stores `open=high=low=close` for every
candle (synthesized from ticker updates). This breaks any function that assumes real OHLCV.
Two bugs in particular:

1. **`_level_recently_broken`** — cannot use `open < level < close` since open==close.
   Fix: compare successive candle closes (`prev_close < level < curr_close`).
2. **`_bounce_confirmation`** — cannot use candle direction (wick/high/low) to confirm
   bounces. Fix: detect touches across candle boundaries (close near level, next close
   moved away by >0.05%).

See `references/rs-close-only-candles-bug-2026-05-08.md` for full reproduction trace.

Detects touch-count S/R zones, fires on retest breakouts.
`references/rs-signal-implementation.md` for full implementation details, bug fixes,
touch count quality bands, and verified working configuration (2026-05-07).

### 5d. Z-Score Momentum (zscore-momentum-signal)

**Source:** `zscore+24,2.00`, `zscore-`

Fires LONG when price significantly above recent average (z > threshold), SHORT when below. Momentum confirmation, not mean reversion.

**Per-token tuning:** lookback 10-60 bars, threshold 1.5-4.0. Min 15 signals before trusting params.

**Key findings (156 tokens, n≥15):**
- Avg WR: 58%, 87% tokens have positive avg_PnL
- Optimal threshold cluster: 2.0–2.5
- LONG dominates (~65% LONG vs ~35% SHORT)
- ETH SHORT is notable outlier: SHORT WR 83% vs LONG WR 50%

### 5f. Diagonal Trendline Breakout (tl_break)

**Source:** `tl_break_long`, `tl_break_short`

Diagonal trendline consolidation → horizontal zone → breakout confirmation. Bidirectional:
LONG when price breaks above diagonal, SHORT when price breaks below.

**Two-phase architecture** (critical — single-phase fails):
```
Phase 1 (first 70% of lookback): Detect diagonal slope
Phase 2 (last 30% of lookback): Detect breakout from zone
```

A single-phase regression over the full window is contaminated by post-breakout candles
(which flatten the diagonal slope). The diagonal must be measured ONLY over the consolidation
phase, before the breakout occurred.

**Anchor at START, not END:**
```python
# WRONG — anchor at END (trendline floats above breakout zone):
start_price = closes[diag_end - 1]
slope = (closes[-1] - closes[diag_end - 1]) / (diag_end - 1)

# CORRECT — anchor at START:
start_price = closes[0]
slope = (closes[diag_end - 1] - closes[0]) / (diag_end - 1)
```

**Direction = breakout direction, NOT diagonal slope:**
```
Down-sloping diagonal (start > end): price oscillates BELOW it
  → break ABOVE = LONG,  break BELOW = SHORT

Up-sloping diagonal (start < end): price oscillates ABOVE it
  → break BELOW = SHORT, break ABOVE = LONG
```

**Bounce detection must be direction-aware:**
```python
if direction == 'LONG':
    # Bounce = price BELOW diagonal, then next candle ABOVE
    if closes[i] < diag_at_i and closes[i + 1] > diag_at_i_plus_1:
        touches.append({'price': closes[i]})
elif direction == 'SHORT':
    # Bounce = price ABOVE diagonal, then next candle BELOW
    if closes[i] > diag_at_i and closes[i + 1] < diag_at_i_plus_1:
        touches.append({'price': closes[i]})
```

**Pairwise bounce clustering** (not adjacent-only):
With 3+ bounces (e.g., OP with 7), non-adjacent pairs can be tighter than adjacent pairs.
Use O(n²) search for any 2 bounces within `3 × ATR`:
```python
def _cluster_bounces_simple(bounces, atr):
    for i in range(len(bounces)):
        for j in range(i + 1, len(bounces)):
            if abs(bounces[i]['price'] - bounces[j]['price']) <= 3 * atr:
                return (bounces[i]['price'] + bounces[j]['price']) / 2
    return None
```

**Key params:**
```python
LOOKBACK = 80         # candles (~6.7h at 5m)
DIAGONAL_CUTOFF = 0.70  # first 70% = diagonal, last 30% = breakout zone
BOUNCE_ATR = 2.0      # touch threshold
MIN_BOUNCES = 2       # 2+ touches to form zone
CLUSTER_TOL = 3.0     # any 2 bounces within 3*ATR form zone
BREAKOUT_ATR = 0.35   # price must be 0.35*ATR beyond diagonal level
FOLLOWTHROUGH = 0.50  # breakout candle must be 50%+ of its own range
```

**Wiring into signal_compactor.py:**
- `SIGNAL_SOURCE_WEIGHTS`: `('tl_break_long', 'tl_break_long')` → 1.25, same for short
- hotset LONG filter: `tl_break_long` exempt from `accel-300+` requirement (alongside `accel-300+`)
- Registration in `signals/__init__.py`: import at line ~167, `SIGNAL_REGISTRY` entry at line ~219, `name_to_module` at line ~257

**Why it fires on ~20% of tokens:** The signal requires only 2 bounces + zone formation + breakout.
These conditions are common in volatile markets. Tune `MIN_BOUNCES` or `BREAKOUT_ATR` to reduce
false signals. `MIN_BOUNCES=3` would filter to stronger zones.

---

### 5e. Fake-Dump Short (fake-dump-short-signal)

**Source:** `fake_dump`, `breakdown`

Detects the pattern: RSI crashes from overbought to oversold → bounces → real crash.

**Type A — Dead Cat Bounce Short:**
- RSI was >60 (overbought) 30 min ago
- RSI crashed to <30 in last 15 candles (fake dump)
- RSI now recovering 35-65 (bounce phase)
- Entry: SHORT when RSI bounces to 40-60 zone

**Type B — Continuation Breakdown Short (most common):**
- Price below SMA20 confirmed
- Volume spike >10x avg
- Entry: SHORT on vol spike + RSI >50 + price below SMA20

**Empirical findings (179 big dumps >15% in 1h):**
- Volume spike >5x avg: 100% (universal)
- Price below SMA20: ~95%
- RSI overbought at some point: ~35%

---

## 5f. Standalone Executors — Guardian Conflict + Migration Pattern

**Migration update (2026-05-16):** `zscore_pump` successfully migrated. `signals/zscore_pump.py` created, wired to `signals/__init__.py`, constants added to `hermes_constants.py`. `name_to_module` in `run_all_signals()` updated to include `'zscore_pump': 'zscore_pump'`. See `references/zscore-pump-migration-2026-05-16.md`.

**Problem (observed 2026-05-16 with zscore_pump_hunter):**

A standalone executor opens positions via `mirror_open()` directly — guardian has **no awareness** of these positions. When guardian runs its position sync (`hl-sync-guardian.py`), it sees an open position it didn't track, concludes it's a rogue entry, and closes it immediately.

**Why it happens:**
1. Standalone executor fires independently of pipeline
2. Opens position via `mirror_open()` → position exists in HL, not in guardian's tracked set
3. Guardian's next sync cycle sees "unknown position" → triggers close
4. Position is closed by guardian within minutes of opening

**Symptoms:**
- Standalone executor log shows successful `mirror_open` with position opened
- Guardian log shows `UNKNOWN_POSITION` → `closing unexpected position`
- Position appears in HL but disappears within 1-2 guardian cycles

**The fix:** Migrate the standalone executor to a pipeline signal.

### Migration: Standalone → Pipeline Signal

**Step 1 — Create signal file** (`signals/zscore_pump.py`):
- Reads from `price_history` (signals_hermes.db) — NOT from candles.db directly
- Calls `add_signal()` → `signals_hermes_runtime.db` → `signal_compactor` → hot-set → guardian
- **Removes all own position tracking** — no JSON files, no `mirror_open`/`mirror_close`
- Uses same cooldown, blacklist, open-position guards as other pipeline signals
- Has `scan_{name}_signals(prices_dict) -> int` function + `run()` wrapper for signals_runner

**Step 2 — Add constants** to `hermes_constants.py`:
```python
ZSCORE_PUMP_ENABLED        = False  # master kill-switch
ZSCORE_PUMP_PLUS_ENABLED   = True   # LONG direction
ZSCORE_PUMP_MINUS_ENABLED  = True   # SHORT direction
ZSCORE_PUMP_LOOKBACK       = 24     # default lookback bars
ZSCORE_PUMP_THRESHOLD      = 2.0    # |z| must exceed this
ZSCORE_PUMP_COOLDOWN_BARS  = 10     # bars before re-fire
ZSCORE_PUMP_MIN_SIGNALS_FOR_TUNED = 15  # min signals before tuned params
```

**Step 3 — Register in `signals/__init__.py`** (both import and registry):
```python
try:
    from signals.zscore_pump import scan_zscore_pump_signals as _zscore_pump_run
except Exception:
    _zscore_pump_run = None

# In from hermes_constants import (...):
ZSCORE_PUMP_ENABLED, ZSCORE_PUMP_PLUS_ENABLED, ZSCORE_PUMP_MINUS_ENABLED,

# In SIGNAL_REGISTRY:
{'name': 'zscore_pump', 'enabled': ZSCORE_PUMP_ENABLED, 'run': _zscore_pump_run},
```

**Step 4 — Verify (dry run):**
```bash
cd /root/.hermes/scripts && python3 -c "
import hermes_constants; hermes_constants.ZSCORE_PUMP_ENABLED = True
from signals.zscore_pump import scan_zscore_pump_signals
import sqlite3
prices = {}
conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db', timeout=10)
c = conn.cursor()
c.execute('''SELECT token, price, timestamp FROM price_history ph1
    WHERE timestamp = (SELECT MAX(timestamp) FROM price_history ph2 WHERE ph2.token = ph1.token)''')
for token, price, ts in c.fetchall(): prices[token] = {'price': price}
conn.close()
n = scan_zscore_pump_signals(prices)
print(f'zscore_pump: {n} signals emitted')
"
```

**Step 5 — Keep old standalone executor disabled:**
Set `ZSCORE_PUMP_ENABLED = False` in `hermes_constants.py` — both the old standalone executor AND the new pipeline signal inherit the same flag. Once the pipeline version is verified, delete the old standalone script.

**Key pattern:** A migrated signal does NOT call `mirror_open`/`mirror_close`. Guardian handles execution. The signal only writes to DB via `add_signal()`.

### Killswitch Pattern for Standalone Executors

Both need killswitches in `hermes_constants.py`:
```python
# ── Standalone Executor Killswitches ───────────────────────────────────────────
PUMP_HUNTER_ENABLED        = True   # set False to block pump_hunter
ZSCORE_PUMP_ENABLED        = True   # set False to block zscore_pump
```

The check goes at the top of `scan_and_fire()`:
```python
def scan_and_fire():
    from hermes_constants import ZSCORE_PUMP_ENABLED
    if not ZSCORE_PUMP_ENABLED:
        log("ZSCORE_PUMP_ENABLED=False — block zscore_pump from firing", "OFF")
        return
```

### Guardian/Position Manager Exclusion

Standalone executor signals must be excluded from guardian and position_manager queries:
```sql
-- Pattern: use NOT IN for clean multi-signal exclusion
WHERE signal NOT IN ('pump_hunter', 'zscore_pump')
```

Files with exclusions (3 queries in each):
- `/root/.hermes/scripts/hl-sync-guardian.py` — ~lines 589, 616, 1032
- `/root/.hermes/scripts/position_manager.py` — ~lines 278, 302, 326

### Dry-Run Bug in Standalone Executors

In dry-run mode, `mirror_open/mirror_close` return `{'success': True, 'dry': True}`. The scan loop must NOT add phantom positions:
```python
# WRONG — fires in dry mode too:
if result.get('success'):
    add_zs_position(...)

# CORRECT — skips dry mode:
if result.get('success') and not result.get('dry'):
    add_zs_position(...)
```

### Exit Strategies

**zscore_pump**: ZS cross-0 (confirmed 2026-04-20 as the edge) + 20% ROC dimmer as early exit.
**pump_hunter**: mean-reversion — fade the spike. Vol spike >5x avg = universal, price below SMA20 ~95%.

**Source:** `pump_hunter`, `zscore_pump`

`pump_hunter` and `zscore_pump` are **standalone executors** — they run outside the signal pipeline entirely, bypass the hot-set gate, and manage their own positions via a JSON track file.

**Architecture:**
```
systemd timer (every 1-5 min)
  └── pump_hunter.py / zscore_pump_hunter.py
        ├── reads candles.db directly (zero HL API calls in detection)
        ├── manages own position JSON
        ├── writes to brain DB (trades table) on open/close
        └── exits via price-based SL/TP or ZS cross-0
```

**Key distinction from pipeline signals:**
| Aspect | Pipeline Signals | Standalone Executors |
|--------|-----------------|---------------------|
| Gate | hot-set + signal_compactor | bypasses hot-set entirely |
| Execution | via guardian + ai-decider | direct mirror_open/mirror_close |
| Position tracking | brain DB + trades.json | JSON track file |
| Expiry | 30-min signal TTL | price-based or ZS cross-0 |

### Killswitch Pattern

Both need killswitches in `hermes_constants.py` so they can be disabled without editing their scripts:

```python
# ── Standalone Executor Killswitches ───────────────────────────────────────────
PUMP_HUNTER_ENABLED        = True   # set False to block pump_hunter from firing
ZSCORE_PUMP_ENABLED        = True   # set False to block zscore_pump from firing
```

The check goes at the top of `scan_and_fire()` in each executor:

```python
def scan_and_fire():
    from hermes_constants import ZSCORE_PUMP_ENABLED
    if not ZSCORE_PUMP_ENABLED:
        log("ZSCORE_PUMP_ENABLED=False — block zscore_pump from firing", "OFF")
        return
```

### Guardian/Position Manager Exclusion

Both signals must be excluded from guardian (`hl-sync-guardian.py`) and `position_manager.py` SQL queries — they manage their own SL/TP and close logic:

```sql
-- Pattern: use NOT IN for clean multi-signal exclusion
WHERE signal NOT IN ('pump_hunter', 'zscore_pump')
```

Files with exclusions (all 3 queries in each):
- `/root/.hermes/scripts/hl-sync-guardian.py` — ~lines 589, 616, 1032
- `/root/.hermes/scripts/position_manager.py` — ~lines 278, 302, 326

### Position File Location

`zscore_pump_hunter` writes to: `/var/www/hermes/data/zscore-pump.json`
`pump_hunter` writes to: `/var/www/hermes/data/pump_hunter_positions.json`

There is a stale duplicate at `/root/.hermes/data/pump_hunter_positions.json` — always reference the `/var/www/hermes/data/` path.

### Dry-Run Bug

In dry-run mode, `mirror_open/mirror_close` return `{'success': True, 'dry': True}`. The scan loop must NOT add phantom positions:

```python
# WRONG — fires in dry mode too:
if result.get('success'):
    add_zs_position(...)

# CORRECT — skips dry mode:
if result.get('success') and not result.get('dry'):
    add_zs_position(...)
```

### Exit Strategies

**zscore_pump**: ZS cross-0 (confirmed 2026-04-20 as the edge) + 20% ROC dimmer as early exit. Acceleration-only exits lose money badly.

**pump_hunter**: mean-reversion — fade the spike. Vol spike >5x avg = universal, price below SMA20 ~95%, RSI overbought ~35%.

### Signal Name Collision — Critical Pitfall

When extracting a signal from `signal_gen.py` to a standalone script, verify the source tag written by the new script does not collide with an existing signal's source tag.

**Example:** The `mtf-macd` signal (signal_gen.py lines 1373-1643) writes `hmacd-{+|-}` as its source tag — identical to the standalone `hmacd.py` signal. Both fire the same conditions under the same source tag, creating duplicate registry entries but a single entry in hot-set after merge.

**Mitigation:** Either (a) use a distinct source tag (e.g., `mtf-macd-{+|-}`) if logic differs, (b) consolidate into one script, or (c) document the collision for correct SOURCE_WEIGHTS application in signal_compactor.

### Extraction Pattern: signal_gen → standalone signal script

**When to extract:** Signal logic is complex enough to need its own file for maintainability (mtf-macd, mtf_momentum are examples).

**Required components for standalone signal:**
1. `run()` function — entry point, returns `int` (signals added)
2. `_log()` helper — writes to both stdout and signals.log (not bare print)
3. Guard checks: price age, open position, cooldown, blacklist, delist, reasonable price
4. `init_db()` at start
5. Master kill-switch check (`<SIGNAL>_ENABLED`) + directional (`<SIGNAL>_PLUS_ENABLED`, `<SIGNAL>_MINUS_ENABLED`)
6. Correct imports: signal_schema, hermes_constants, macd_rules (if used)
7. Register in `signals/__init__.py`:
   - Import: `from signals.{name} import run as _{name}_run`
   - Registry entry: `{'name': '{name}', 'enabled': '<FLAG>', 'run': _{name}_run}`
8. Add to `_SLOW_SIGNALS` set if runtime > 10s

**Verification after extraction:**
```bash
python3 -m py_compile signals/{name}.py
cd /root/.hermes/scripts && python3 -c "
from signals import get_registered_signals, SIGNAL_REGISTRY
print('All:', [s['name'] for s in SIGNAL_REGISTRY])
"
python3 signals/{name}.py  # exits clean when flag is False
```

## 6. Build Sequence — Adding a New Signal (Step-by-Step)

When adding a new signal (e.g., `ema_angle.py`), follow this exact sequence to ensure it integrates with the full pipeline. Skipping steps causes hard-to-debug failures (signals silently blocked, missing from hot-set, etc.).

### Step 1 — Constants in `hermes_constants.py`
Add a clearly commented block under the existing signal constants section:
```python
# ── New Signal Name ────────────────────────────────────────────────────────
# description, what the signal measures, how it fires
NEW_SIGNAL_LOOKBACK        = 500   # candles for ...
NEW_SIGNAL_PERCENTILE_LONG = 75    # p75 threshold for LONG
NEW_SIGNAL_ENABLED         = True  # master kill switch
NEW_SIGNAL_PLUS_ENABLED   = True  # new-signal+ LONG
NEW_SIGNAL_MINUS_ENABLED  = True  # new-signal- SHORT
# ... additional params
```
Include the `*_PLUS_ENABLED` and `*_MINUS_ENABLED` flags even if you only plan to use one direction — they are needed for the Layer 2 kill-switch in signal_schema.py.

### Step 2 — Signal File in `signals/`
Create `/root/.hermes/scripts/signals/{name}.py`:
- Import constants directly from `hermes_constants`
- Signal identity constants at top:
  ```python
  SIGNAL_TYPE = 'new_signal'   # goes in signal_type column
  SOURCE_LONG  = 'new-signal+'   # goes in source column for LONG
  SOURCE_SHORT = 'new-signal-'   # goes in source column for SHORT
  ```
- Implement `detect_{name}(token, prices)` → returns signal dict or None
- Implement `scan_{name}_signals(prices_dict)` → calls `add_signal()` for each hit
- Export `run()` as the entry point for signals_runner

### Step 3 — Layer 2 Kill-Switch in `signal_schema.py`
Add to the imports inside `add_signal()` (around line ~432, after ACCEL_300 entries):
```python
from hermes_constants import (
    ...
    NEW_SIGNAL_ENABLED, NEW_SIGNAL_PLUS_ENABLED, NEW_SIGNAL_MINUS_ENABLED,
)
```
Add the guard checks after the existing signal blocks (around line ~584):
```python
# new-signal
if _comp == 'new-signal+' and not NEW_SIGNAL_PLUS_ENABLED:
    print(f'  DEBUG add_signal BLOCKED: ... NEW_SIGNAL_PLUS_ENABLED=False', flush=True)
    return None
if _comp == 'new-signal-' and not NEW_SIGNAL_MINUS_ENABLED:
    print(f'  DEBUG add_signal BLOCKED: ... NEW_SIGNAL_MINUS_ENABLED=False', flush=True)
    return None
if _comp == 'new-signal' and not NEW_SIGNAL_ENABLED:
    return None
```

### Step 4 — Register in `signals/__init__.py`
**Import the run function** (add after existing try/except blocks):
```python
try:
    from signals.{name} import scan_{name}_signals as _{name}_run
except Exception:
    _{name}_run = None
```
**Add to the `from hermes_constants import (...)` block:**
```python
{NAME}_ENABLED, {NAME}_PLUS_ENABLED, {NAME}_MINUS_ENABLED,
```
**Add to registry** (add after existing entries in the list):
```python
{'name': '{name}', 'enabled': {NAME}_ENABLED, 'run': _{name}_run},
```

### Step 5 — Verify
```bash
# Import check
python3 -c "import signals; entry = [e for e in signals.get_registered_signals() if e['name']=='{name}'][0]; print(entry)"

# Dry run with debug flag
{NAME}_DEBUG=1 python3 -c "import signals.{name}; {name}.run()"

# Confirm in DB
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT token, direction, source, confidence FROM signals WHERE source LIKE '{name}%' ORDER BY created_at DESC LIMIT 5"
```

### Common Bugs in New Signal Files

**Bug: Recency calculation with array offsets**
When using `latest_idx` from a sliced array (e.g., `angle_speeds[i]` where `i` is an index into `angles`), `latest_idx` is the index into `angles`, not into `angle_speeds`. Converting: `speed_pos = latest_idx - speed_period` gives the position in the speed array. Then `bars_ago = len(angle_speeds) - 1 - speed_pos`.

**Bug: DB token scan uses wrong placeholder variable**
When falling back to DB scan without `prices_dict`, do NOT use `(prices_dict,)` as the SQL parameter — it will silently pass a dict as the LIMIT clause. Use a real `cutoff_ts` variable:
```python
cutoff_ts = int(os.environ.get('READY_BEFORE_TS', 0)) or (
    __import__('time').time() - 900
)
cur.execute("SELECT ... WHERE ts > ?", (cutoff_ts,))
```

**Bug: Confidence overflow**
Cap at `min(92, confidence)` — signals above 92 get truncated at the DB layer and lose nuance. The MAX_CONFIDENCE ceiling in add_signal() is applied before the record is written.

## 7. Adding to Hot-Set

## 6. Mandatory Component Rules — accel-300+ for LONG

### accel-300+ Required for All LONG Entries (2026-05-05)

**Rationale**: `accel-300+` (WR=40%, avg=+0.33% over 80 trades) is our strongest LONG signal. Requiring it as mandatory for all LONG hot-set entries filters out rs-only and hzscore-only entries that lack directional momentum confirmation.

**Implementation**: Two insertion points in `signal_compactor.py`:

1. **`run_compaction()` hotset_final loop** (line ~728) — new entries into hot-set:
```python
# After the validate_source() blacklist check (~line 725):
if direction == 'LONG':
    source_parts = [p.strip() for p in (src or '').split(',') if p.strip()]
    if 'accel-300+' not in source_parts:
        log(f"  🚫 [HOTSET-FILTER] {tkn}: LONG blocked — requires accel-300+ (has: {src})")
        continue
```

2. **`_filter_safe_prev_hotset()`** (line ~1159) — preserved entries from previous cycle:
```python
# After validate_source() check:
if direction == 'LONG':
    sp = [p.strip() for p in src_str.split(',') if p.strip()]
    if 'accel-300+' not in sp:
        continue  # skip LONG without accel-300+ momentum confirmation
```

**Effect**: rs-only LONGs (rs-s2472, rs-s386), hzscore- only LONGs, and hhh-long4/5 combos are blocked. Only `accel-300+,hzscore-,rs-s####` and `accel-300+,rs-s####` combos can enter the hot-set as LONG.

**SHORT signals unaffected**: `accel-300+` is a LONG momentum signal. SHORTs use hzscore+, pct-hermes-, vel-hermes-, gap-300-, and ma-cross-5m- (WR=56%).

### Adding Mandatory Component Rules

To add a new mandatory component rule (e.g., `pct-hermes+` required for SHORT):
1. Add to `run_compaction()` hotset_final loop after validate_source()
2. Add the same check to `_filter_safe_prev_hotset()` for consistency
3. Add the signal to `SIGNAL_SOURCE_BLACKLIST` in `hermes_constants.py` if it's also chronically underperforming

---

## 6. Signal Registry Architecture (scripts/signals/)

After the 2026-05-05 mass migration, all signal scripts live in `/root/.hermes/scripts/signals/` with a central `SIGNAL_REGISTRY` in `__init__.py`.

### Registry Structure

```python
# scripts/signals/__init__.py
SIGNAL_REGISTRY = []

def register_signal(name: str, enabled: bool, run_fn):
    SIGNAL_REGISTRY.append({'name': name, 'enabled': True, 'run': run_fn})
```

### Migration Checklist

When extracting inline signal code from `signal_gen.py`:

1. **Imports:** All symbols from signal_gen.py must be imported (add_signal, get_cooldown, compute_regime, price_age_minutes)
2. **compute_regime unpack:** Use `regime, long_mult, short_mult, *_ = compute_regime()` — it returns 5 values, not 3
3. **get_cooldown:** Always `get_cooldown(token, direction=direction)` — no-arg form returns bool, not dict
4. **Signature dispatch:** `run_all_signals()` inspects function signature — scan functions need `prices_dict` param
5. **Register correctly:** Use actual function name (e.g., `scan_hh_hl_signals`, not `scan_all_tokens`)
6. **Verify:** Compile + run individually before wiring into pipeline

### 3-Layer Kill-Switch (Always All Three)

| Layer | File | What it does |
|-------|------|-------------|
| 1 | hermes_constants.py `*_ENABLED` flags | Script-level gate |
| 2 | signal_schema.py `add_signal()` per-source | Per-source guard in DB write path |
| 3 | decider_run.py execution gate | Final gate before real money |

### Blacklist is Redundant

`SIGNAL_SOURCE_BLACKLIST` is **commented out** — the 3-layer kill-switch makes it unnecessary. Keep commented structure for historical reference.

---

## 6. Build Sequence — Adding a New Signal (Step-by-Step)

When adding a new signal (e.g., `ema_angle.py`), follow this exact sequence to ensure it integrates with the full pipeline. Skipping steps causes hard-to-debug failures (signals silently blocked, missing from hot-set, etc.).

### Step 1 — Constants in `hermes_constants.py`
Add a clearly commented block under the existing signal constants section:
```python
# ── New Signal Name ────────────────────────────────────────────────────────
# description, what the signal measures, how it fires
NEW_SIGNAL_LOOKBACK        = 500   # candles for ...
NEW_SIGNAL_PERCENTILE_LONG = 75    # p75 threshold for LONG
NEW_SIGNAL_ENABLED         = True  # master kill switch
NEW_SIGNAL_PLUS_ENABLED   = True  # new-signal+ LONG
NEW_SIGNAL_MINUS_ENABLED  = True  # new-signal- SHORT
# ... additional params
```
Include the `*_PLUS_ENABLED` and `*_MINUS_ENABLED` flags even if you only plan to use one direction — they are needed for the Layer 2 kill-switch in signal_schema.py.

### Step 2 — Signal File in `signals/`
Create `/root/.hermes/scripts/signals/{name}.py`:
- Import constants directly from `hermes_constants`
- Signal identity constants at top:
  ```python
  SIGNAL_TYPE = 'new_signal'   # goes in signal_type column
  SOURCE_LONG  = 'new-signal+'   # goes in source column for LONG
  SOURCE_SHORT = 'new-signal-'   # goes in source column for SHORT
  ```
- Implement `detect_{name}(token, prices)` → returns signal dict or None
- Implement `scan_{name}_signals(prices_dict)` → calls `add_signal()` for each hit
- Export `run()` as the entry point for signals_runner

### Step 3 — Layer 2 Kill-Switch in `signal_schema.py`
Add to the imports inside `add_signal()` (around line ~432, after ACCEL_300 entries):
```python
from hermes_constants import (
    ...
    NEW_SIGNAL_ENABLED, NEW_SIGNAL_PLUS_ENABLED, NEW_SIGNAL_MINUS_ENABLED,
)
```
Add the guard checks after the existing signal blocks (around line ~584):
```python
# new-signal
if _comp == 'new-signal+' and not NEW_SIGNAL_PLUS_ENABLED:
    print(f'  DEBUG add_signal BLOCKED: ... NEW_SIGNAL_PLUS_ENABLED=False', flush=True)
    return None
if _comp == 'new-signal-' and not NEW_SIGNAL_MINUS_ENABLED:
    print(f'  DEBUG add_signal BLOCKED: ... NEW_SIGNAL_MINUS_ENABLED=False', flush=True)
    return None
if _comp == 'new-signal' and not NEW_SIGNAL_ENABLED:
    return None
```

### Step 4 — Register in `signals/__init__.py`
**Import the run function** (add after existing try/except blocks):
```python
try:
    from signals.{name} import scan_{name}_signals as _{name}_run
except Exception:
    _{name}_run = None
```
**Add to the `from hermes_constants import (...)` block:**
```python
{NAME}_ENABLED, {NAME}_PLUS_ENABLED, {NAME}_MINUS_ENABLED,
```
**Add to registry** (add after existing entries in the list):
```python
{'name': '{name}', 'enabled': {NAME}_ENABLED, 'run': _{name}_run},
```

### Step 5 — Verify
```bash
# Import check
python3 -c "import signals; entry = [e for e in signals.get_registered_signals() if e['name']=='{name}'][0]; print(entry)"

# Dry run with debug flag
{NAME}_DEBUG=1 python3 -c "import signals.{name}; {name}.run()"

# Confirm in DB
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT token, direction, source, confidence FROM signals WHERE source LIKE '{name}%' ORDER BY created_at DESC LIMIT 5"
```

### Common Bugs in New Signal Files

**Bug: Recency calculation with array offsets**
When using `latest_idx` from a sliced array (e.g., `angle_speeds[i]` where `i` is an index into `angles`), `latest_idx` is the index into `angles`, not into `angle_speeds`. Converting: `speed_pos = latest_idx - speed_period` gives the position in the speed array. Then `bars_ago = len(angle_speeds) - 1 - speed_pos`.

**Bug: DB token scan uses wrong placeholder variable**
When falling back to DB scan without `prices_dict`, do NOT use `(prices_dict,)` as the SQL parameter — it will silently pass a dict as the LIMIT clause. Use a real `cutoff_ts` variable:
```python
cutoff_ts = int(os.environ.get('READY_BEFORE_TS', 0)) or (
    __import__('time').time() - 900
)
cur.execute("SELECT ... WHERE ts > ?", (cutoff_ts,))
```

**Bug: Confidence overflow**
Cap at `min(92, confidence)` — signals above 92 get truncated at the DB layer and lose nuance. The MAX_CONFIDENCE ceiling in add_signal() is applied before the record is written.

## 7. Adding to Hot-Set — Confluence Is Binary, No Exceptions

**Hot-set rule**: only signals with 2+ unique signal types reach APPROVED.
Single-source signals are BLOCKED — there is no GOOD_STANDALONE bypass, no kill-switch,
no historical WR exception. This is a hard rule.

The confluence gate in `signal_compactor.py`:
```python
if unique_signal_types >= 2:
    pass_gate = True
else:
    pass_gate = False  # always block single-source
```

**What this means for signal design**: A new signal cannot stand alone. It must be
## 6. Build Sequence — Adding a New Signal (Step-by-Step)

When adding a new signal (e.g., `ema_angle.py`), follow this exact sequence to ensure it integrates with the full pipeline. Skipping steps causes hard-to-debug failures (signals silently blocked, missing from hot-set, etc.).

### Step 1 — Constants in `hermes_constants.py`
Add a clearly commented block under the existing signal constants section:
```python
# ── New Signal Name ────────────────────────────────────────────────────────
# description, what the signal measures, how it fires
NEW_SIGNAL_LOOKBACK        = 500   # candles for ...
NEW_SIGNAL_PERCENTILE_LONG = 75    # p75 threshold for LONG
NEW_SIGNAL_ENABLED         = True  # master kill switch
NEW_SIGNAL_PLUS_ENABLED   = True  # new-signal+ LONG
NEW_SIGNAL_MINUS_ENABLED  = True  # new-signal- SHORT
# ... additional params
```
Include the `*_PLUS_ENABLED` and `*_MINUS_ENABLED` flags even if you only plan to use one direction — they are needed for the Layer 2 kill-switch in signal_schema.py.

### Step 2 — Signal File in `signals/`
Create `/root/.hermes/scripts/signals/{name}.py`:
- Import constants directly from `hermes_constants`
- Signal identity constants at top:
  ```python
  SIGNAL_TYPE = 'new_signal'   # goes in signal_type column
  SOURCE_LONG  = 'new-signal+'   # goes in source column for LONG
  SOURCE_SHORT = 'new-signal-'   # goes in source column for SHORT
  ```
- Implement `detect_{name}(token, prices)` → returns signal dict or None
- Implement `scan_{name}_signals(prices_dict)` → calls `add_signal()` for each hit
- Export `run()` as the entry point for signals_runner

### Step 3 — Layer 2 Kill-Switch in `signal_schema.py`
Add to the imports inside `add_signal()` (around line ~432, after ACCEL_300 entries):
```python
from hermes_constants import (
    ...
    NEW_SIGNAL_ENABLED, NEW_SIGNAL_PLUS_ENABLED, NEW_SIGNAL_MINUS_ENABLED,
)
```
Add the guard checks after the existing signal blocks (around line ~584):
```python
# new-signal
if _comp == 'new-signal+' and not NEW_SIGNAL_PLUS_ENABLED:
    print(f'  DEBUG add_signal BLOCKED: ... NEW_SIGNAL_PLUS_ENABLED=False', flush=True)
    return None
if _comp == 'new-signal-' and not NEW_SIGNAL_MINUS_ENABLED:
    print(f'  DEBUG add_signal BLOCKED: ... NEW_SIGNAL_MINUS_ENABLED=False', flush=True)
    return None
if _comp == 'new-signal' and not NEW_SIGNAL_ENABLED:
    return None
```

### Step 4 — Register in `signals/__init__.py`
**Import the run function** (add after existing try/except blocks):
```python
try:
    from signals.{name} import scan_{name}_signals as _{name}_run
except Exception:
    _{name}_run = None
```
**Add to the `from hermes_constants import (...)` block:**
```python
{NAME}_ENABLED, {NAME}_PLUS_ENABLED, {NAME}_MINUS_ENABLED,
```
**Add to registry** (add after existing entries in the list):
```python
{'name': '{name}', 'enabled': {NAME}_ENABLED, 'run': _{name}_run},
```

### Step 5 — Verify
```bash
# Import check
python3 -c "import signals; entry = [e for e in signals.get_registered_signals() if e['name']=='{name}'][0]; print(entry)"

# Dry run with debug flag
{NAME}_DEBUG=1 python3 -c "import signals.{name}; {name}.run()"

# Confirm in DB
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT token, direction, source, confidence FROM signals WHERE source LIKE '{name}%' ORDER BY created_at DESC LIMIT 5"
```

### Common Bugs in New Signal Files

**Bug: Recency calculation with array offsets**
When using `latest_idx` from a sliced array (e.g., `angle_speeds[i]` where `i` is an index into `angles`), `latest_idx` is the index into `angles`, not into `angle_speeds`. Converting: `speed_pos = latest_idx - speed_period` gives the position in the speed array. Then `bars_ago = len(angle_speeds) - 1 - speed_pos`.

**Bug: DB token scan uses wrong placeholder variable**
When falling back to DB scan without `prices_dict`, do NOT use `(prices_dict,)` as the SQL parameter — it will silently pass a dict as the LIMIT clause. Use a real `cutoff_ts` variable:
```python
cutoff_ts = int(os.environ.get('READY_BEFORE_TS', 0)) or (
    __import__('time').time() - 900
)
cur.execute("SELECT ... WHERE ts > ?", (cutoff_ts,))
```

**Bug: Confidence overflow**
Cap at `min(92, confidence)` — signals above 92 get truncated at the DB layer and lose nuance. The MAX_CONFIDENCE ceiling in add_signal() is applied before the record is written.

## 7. Adding to Hot-Set

**signal_compactor.py must be updated to recognize new source names in SIGNAL_SOURCE_WEIGHTS table.** Without this, new signals are invisible to the hot-set pipeline.

### Routing in signal_compactor.py

```python
SIGNAL_SOURCE_WEIGHTS = {
    # ... existing entries ...
    ('xxx_signal', 'xxx-'): 1.25,  # description
}
```

**Weight guidance:**
- 1.5 = very strong (e.g., `hmacd-`)
- 1.35 = strong (e.g., `macd-accel-`)
- 1.25 = standard
- 0.8 = suppress (weak signals)

### Blacklist in hermes_constants.py

```python
SIGNAL_SOURCE_BLACKLIST = {
    # ... existing entries ...
    # 'xxx++',  # REMOVE if this is a valid bare source
    # 'xxx--',
}
```

Bare source names in blacklist block ALL merged signals containing that component. Remove only if the bare source IS a valid standalone signal.

---

## 7. Scalable Signal Metadata: JSONB Catch-All (2026-05-09)

**The problem with per-signal columns:** Adding a dedicated PostgreSQL column per signal (signal_z_score, signal_rsi_14, signal_macd_hist, etc.) causes schema sprawl and the infamous d31692f bug — 42 expressions for 41 columns due to `NOW()` being a SQL function (not a placeholder), silently breaking all live trading.

**The solution: JSONB catch-all columns.**

### PostgreSQL schema (done 2026-05-09)

Two columns cover ALL future signals with zero schema changes:

```sql
ALTER TABLE trades ADD COLUMN _signal_metadata JSONB;  -- per-signal values: {accel_300: {conf: 85, gap_pct: 0.22}}
ALTER TABLE trades ADD COLUMN _exp_metadata    JSONB;  -- A/B test variants: {sl_variant: 'tight', timing: 'aggressive'}
```

For SQLite analysis DB (archive-trades.py), same columns as TEXT.

### PostgreSQL trades table signal columns (legacy, keep for migration)

Existing dedicated columns still exist: signal_z_score, signal_rsi_14, signal_macd_hist, signal_macd_value, signal_macd_signal, signal_momentum_state, signal_z_score_tier, signal_decision, signal_leverage, signal_created_at. These are migration-complete for zscore, MACD, RSI. New signals use JSONB only.

### Runtime signals DB schema

```sql
ALTER TABLE signals ADD COLUMN signal_metadata TEXT;
```

New signals write their values here at `add_signal()` time. signal_compactor reads it and passes through to hotset entry. decider_run passes to brain.py as JSON string.

### Data flow for a new signal

```
signal generator writes {your_signal: {conf: 85, your_param: 0.22}}
    → signal_metadata TEXT column in signals_hermes_runtime.db
    → signal_compactor reads it → hotset entry
    → decider_run passes signal_metadata JSON → brain.py
    → brain.py json.dumps() → PostgreSQL _signal_metadata JSONB
    → archive-trades.py reads JSONB → writes TEXT to analysis SQLite
```

### Adding a new signal (zero schema work)

1. Signal generator writes values to `signal_metadata` dict
2. Calls `add_signal(signal_metadata=your_dict)` — no new column needed
3. signal_compactor automatically passes it through to hotset
4. Analysis: `WHERE _signal_metadata LIKE '%your_signal%'`

### Implementation status (2026-05-09)

| Component | Status |
|-----------|--------|
| PostgreSQL `_signal_metadata` + `_exp_metadata` JSONB columns | DONE |
| SQLite signals table `signal_metadata` TEXT column | DONE |
| brain.py `add_trade()` signature | DONE (params added) |
| brain.py argparse `--signal-metadata-json` / `--exp-metadata-json` | PENDING |
| brain.py INSERT (add 2 columns + 2 JSON-serialized values) | PENDING |
| decider_run `execute_trade()` signal_metadata param + CLI passthrough | PENDING |
| signal_compactor (read signal_metadata → hotset entry) | PENDING |
| archive-trades.py (_signal_metadata + _exp_metadata TEXT columns) | PENDING |
| Verification (INSERT column/placeholder balance check) | PENDING |

### Why NOT to add per-signal columns anymore

- Every new column requires: PostgreSQL ALTER, brain.py argparse, brain.py INSERT rewrite, decider_run forwarding, archive-trades mapping — all error-prone
- The d31692f incident (42 expr / 41 cols) silently broke ALL live trading for a full day
- With 10+ signals planned, per-signal columns = 10+ ALTER + 10+ forwarding paths
- JSONB catch-all: add signal = write to dict, done
    'trend_purity+': {'wr': 38, 'avg': 0.257, 'dir': 'LONG'},
    'ma-cross-5m-':  {'wr': 47, 'avg': 0.062, 'dir': 'SHORT'},
}
```

**Fire rate vs. scoring**: A signal can have perfect SCORING_TABLE entries but still never reach hot-set if it requires a co-signal that fires on a different token universe. pct-hermes+ fired 1,759 times in 6h (100% EXPIRED) because it was NOT in GOOD_STANDALONE_SIGNALS — adding it there allowed it to pass the confluence gate as a single-source signal.

**Decision tree for new signals:**
1. Does it need a co-signal? → Add to SIGNAL_SOURCE_WEIGHTS, rely on merging
2. Does it have standalone edge? → Add to GOOD_STANDALONE_SIGNALS (requires positive backtest stats: wr + avg_pnl)
3. Both? → Add to both (GOOD_STANDALONE_SIGNALS for standalone pass, SIGNAL_SOURCE_WEIGHTS for combo scoring)

### Blacklist in hermes_constants.py

```python
SIGNAL_SOURCE_BLACKLIST = {
    # ... existing entries ...
    # 'xxx++',  # REMOVE if this is a valid bare source
    # 'xxx--',
}
```

Bare source names in blacklist block ALL merged signals containing that component. Remove only if the bare source IS a valid standalone signal.

---

## 7. pct-hermes Direction — FIXED (2026-05-04)

**The signal_gen.py logic was inverted** — pct-hermes+ was entering LONG at the BOTTOM of its range (suppressed price), catching falling knives in downtrends.

**Corrected semantics (signal_gen.py lines 1686-1692):**
- `pct_short` = % of 200-bar lookback with price >= current → **high pct_short = price near BOTTOM**
- `pct_long` = % of 200-bar lookback with price <= current → **high pct_long = price near TOP**

| Source | Direction | Trigger | Notes |
|--------|-----------|---------|-------|
| `pct-hermes+` | **LONG** | pct_short >= 72 (price suppressed = buy the dip) | Was 0% WR before flip |
| `pct-hermes-` | **SHORT** | pct_long >= 72 (price elevated = sell the rally) | Already correct |
| `pct-hermes` (bare) | blocked | combo-only | blacklisted in SIGNAL_SOURCE_BLACKLIST |

**Empirical validation (62 pct-hermes+ trades with outcomes):**

| pct_short bucket | Before flip WR | After flip WR |
|---|---|---|
| 72-80% | 4.5% | **95.5%** |
| 80-85% | 0% | **100%** |
| 85-90% | 0% | **100%** |
| 90-95% | 0% | **96.2%** |
| 95%+ | 0% | **83.3%** |

**Why the original was wrong**: pct_short >= 72 fires at 84-100% (deeply suppressed prices in a downtrend). Buying at the bottom with T's "first candle against us we're out" philosophy = immediate loss. The flip makes pct-hermes+ = SHORT at suppression (sell the pump that follows price down), winning 95%+ in emulated backtest.

**pct-hermes- was already correct** — pct_long >= 72 → SHORT (sell elevated price) is directionally right. Its ~7% live WR is a trending-market persistence problem, not direction. NOT changed.

**Constant**: `PCT_RANK_THRESH = 72` in `signal_gen.py`. Confidence: `(pct_val - 72) * 1.25 + 50`, capped at 60.
3. Re-check pct_short at fill time in guardian — don't fill if pct_short < 72%
4. Add session-peak filter in guardian

See also: `hermes-signal-debugging` skill — "pct-hermes+ ALSO Broken" section for full analysis.

---

### Bug #15: Signed-Angle Signals — Percentile Thresholds Without Sign Gate

**Symptom:** In a bear market, all angles for a token are negative. The 75th-percentile threshold (p75) is therefore negative (e.g., `-0.001°`). A signal with `angle >= p75` fires LONG even though the angle is deeply negative (price below EMA, still falling). STX, XRP, SKY all fired LONG when they should have fired SHORT or stayed quiet.

**Root cause:** Percentile thresholds adapt to the distribution. In a downtrend, p75 is the "least negative" angle, not a flat/positive angle. The signal logic used only `angle >= p75` without checking whether the angle has actually crossed through zero into positive territory.

**Fix:** Add a hard sign gate before the percentile check:

```python
# LONG: angle must cross from flat (near 0) into POSITIVE steep territory
if EMA_ANGLE_PLUS_ENABLED and latest_angle > 0 and latest_angle >= p75 and latest_speed > EMA_ANGLE_MIN_SPEED:
    # signal fires

# SHORT: angle must cross from flat (near 0) into NEGATIVE steep territory  
if EMA_ANGLE_MINUS_ENABLED and latest_angle < 0 and latest_angle <= p25 and latest_speed < -EMA_ANGLE_MIN_SPEED:
    # signal fires
```

**Lesson:** Angle signals that depend on percentile thresholds need an explicit sign check. The percentile threshold alone only tells you "is this steep relative to its own history" — not "is the price above or below the EMA." Without the sign gate, a bear-market downtrend produces false LONG signals on every token with negative angles.

## Bug #18: 500-Bar p75 — Root Cause of False LONG Fires (2026-05-15)

**Symptom:** CHIP, MORPHO, MOVE, ZK fire LONG with angles like 0.000047° to 0.000863° — micro-jitter territory. Their 500-bar p75 is negative (-0.000319° to -0.000080°).

**Root cause:** `p75 = sorted_angles[int(len(sorted_angles) * 0.75)]` computes the percentile from the last 500 bars only. During chop/sideways, the 500-bar window captures only grind-up and grind-down — producing near-zero or negative p75. Any tiny positive angle then exceeds it and fires.

**Contrast with SHORT:** A negative 500-bar p25 (from chop) correctly means "no steep downtrend yet" — `angle <= p25` is harder to satisfy when p25 is negative, not easier. SHORTS naturally filter for steepness.

**Proof with real data:**
| Token | 500-bar p75 | Full-history p75 | Fires? |
|-------|------------|-----------------|--------|
| CHIP | -0.000319° | +0.003224° | YES (wrong) |
| MORPHO | -0.000256° | +0.001407° | YES (wrong) |
| MOVE | -0.000080° | +0.003224° | YES (wrong) |

**Fix:** Compute p75 from the token's FULL angle history, not the 500-bar window. The current angle is still from 500 bars (needed for responsiveness), but the percentile threshold reflects the token's full historical steepness:

```python
# Fetch ALL available closes for p75 computation
all_closes = _get_1m_prices_full(token)  # all historical candles
all_ema = _ema(all_closes, 300)
all_angles = [math.degrees(math.atan((all_ema[i] - all_ema[i-20])/20 / all_ema[i]))
              for i in range(20, len(all_ema))]
all_sorted = sorted(all_angles[10:])  # skip first 10 (speed warmup)
full_p75 = all_sorted[int(len(all_sorted) * 0.75)]

# Current angle from 500-bar window, threshold from full history:
angle_meets_minimum = latest_angle >= full_p75
```

**PURR reference:** PURR's full-history p75 = 0.002046°. Signal fires when angle > full_p75 AND price above EMA AND EMA rising.

## Bug #19: Stale Price Index — Wrong Bar for Timestamp and Price Field

**Symptom:** `latest_ts = prices[latest_idx + speed_period][0]`. With 500 prices and latest_idx=479, `prices[489]` is OUT OF BOUNDS. Even when valid, reads ~10 bars stale.

**Fix:** Use `prices[-1]` for actual latest price/timestamp. Returned `price` field uses `closes[-1]`, not `closes[latest_idx + speed_period]`.

**Symptom:** `breakout_engine` fires a signal for a token (ILV) that is delisted on Hyperliquid. Guardian cannot execute because HL returns `None` for that token. Signal shows in hotset with masked token `***` and wrong price.

**Root cause chain:**
1. `price_collector.py` `_seed_universe_candles()` fetches Binance candles for ALL tokens in the HL universe, including `isDelisted=True` tokens (line ~143). ILV trades on Binance, so Binance has ILV data → ILV candles at ~$4.66 stored in `candles.db`.
2. `breakout_engine.py` token list (line ~557) = "any token in candles.db with recent data" — no HL live-token validation.

## Cooldown Patterns (2026-05-15)

Two distinct cooldown patterns in the signal system:

| Signal | Mechanism | Duration | Implementation |
|--------|-----------|----------|----------------|
| `accel_300` | bars-based + DB cooldown | `COOLDOWN_BARS=10` (~10min) + `MIN_TRADE_INTERVAL_MINUTES` | `set_cooldown()` via DB in scanner |
| `ema_angle` | time-based + DB cooldown | `EMA_ANGLE_COOLDOWN_MIN=15` (15min) | `_last_signal_ts` in-memory cache + `get_cooldown()` DB check |

**Key lesson:** cooldown can live in two places — in-memory cache (fast, per-run) and DB (shared across restarts). When adding cooldown to a new signal, use in-memory `_last_signal_ts` dict keyed by `token:direction` for per-run dedup, PLUS DB cooldown for cross-session blocking.

For new signals: add `XXX_COOLDOWN_MIN` constant to `hermes_constants.py` (not hardcoded in the signal file). Import and use it in both the in-memory check and the DB `get_cooldown()` call. This matches the `ema_angle.py` pattern established 2026-05-15.

**Pattern for ema_angle.py (established 2026-05-15):**
```python
_last_signal_ts = {}  # in-memory: token:direction → timestamp (ms)

def _cooldown_ok(token, direction, now_ts):
    key = f"{token}:{direction}"
    last = _last_signal_ts.get(key, 0)
    if (now_ts - last) < EMA_ANGLE_COOLDOWN_MIN * 60 * 1000:
        return False
    _last_signal_ts[key] = now_ts
    return True

# At signal detection:
if not _cooldown_ok(token, direction, sig['ts']):
    continue  # skip, cooldown active

# Also check DB cooldown (shared with other signals):
cd = get_cooldown(token, direction)
if cd and (now_ts / 1000 - cd) < EMA_ANGLE_COOLDOWN_MIN * 60:
    continue
```
3. ILV's last candle is 30+ min stale, but the vol spike detection fires on the stale data.
4. HL `allMids` returns `None` for delisted tokens → guardian can't find ILV → masked `***` in oc_pending_signals.json.

**Two fix points:**
- `price_collector.py` line ~143: add `not u.get('isDelisted', False)` to the universe filter — prevents delisted HL tokens from getting Binance candles in candles.db.
- `breakout_engine.py` (or any signal engine): cross-check token against live HL `allMids` before emitting. If `allMids[token]` is `None` or token not in universe → skip.

**Staleness exit worked correctly:** `entry_origin_ts=~03:58`, staleness = `max(0, 1 - age_m/5)` → hit 0 after ~25 min → ILV exited hotset at ~04:13. No bug in exit logic.

**Verification query:**
```sql
-- Check which tokens in candles.db are delisted on HL
-- (compare candles.db tokens against hl_cache.json delisted list)
SELECT token, MAX(ts), COUNT(*) FROM candles_5m GROUP BY token
HAVING token IN (SELECT name FROM universe WHERE isDelisted=True);
### Bug #15: Signed-Angle Signals — Percentile Thresholds Without Sign Gate

**Symptom:** In a bear market, all angles for a token are negative. The 75th-percentile threshold (p75) is therefore negative (e.g., `-0.001°`). A signal with `angle >= p75` fires LONG even though the angle is deeply negative (price below EMA, still falling). STX, XRP, SKY all fired LONG when they should have fired SHORT or stayed quiet.

**Root cause:** Percentile thresholds adapt to the distribution. In a downtrend, p75 is the "least negative" angle, not a flat/positive angle. The signal logic used only `angle >= p75` without checking whether the angle has actually crossed through zero into positive territory.

**Fix:** Add a hard sign gate before the percentile check:

```python
# LONG: angle must cross from flat (near 0) into POSITIVE steep territory
if EMA_ANGLE_PLUS_ENABLED and latest_angle > 0 and latest_angle >= p75 and latest_speed > EMA_ANGLE_MIN_SPEED:
    # signal fires

# SHORT: angle must cross from flat (near 0) into NEGATIVE steep territory  
if EMA_ANGLE_MINUS_ENABLED and latest_angle < 0 and latest_angle <= p25 and latest_speed < -EMA_ANGLE_MIN_SPEED:
    # signal fires
```

**Lesson:** Angle signals that depend on percentile thresholds need an explicit sign check. The percentile threshold alone only tells you "is this steep relative to its own history" — not "is the price above or below the EMA." Without the sign gate, a bear-market downtrend produces false LONG signals on every token with negative angles.

## Bug #18: 500-Bar p75 — Root Cause of False LONG Fires (2026-05-15)

**Symptom:** CHIP, MORPHO, MOVE, ZK fire LONG with angles like 0.000047° to 0.000863° — micro-jitter territory. Their 500-bar p75 is negative (-0.000319° to -0.000080°).

**Root cause:** `p75 = sorted_angles[int(len(sorted_angles) * 0.75)]` computes the percentile from the last 500 bars only. During chop/sideways, the 500-bar window captures only grind-up and grind-down — producing near-zero or negative p75. Any tiny positive angle then exceeds it and fires.

**Contrast with SHORT:** A negative 500-bar p25 (from chop) correctly means "no steep downtrend yet" — `angle <= p25` is harder to satisfy when p25 is negative, not easier. SHORTS naturally filter for steepness.

**Proof with real data:**
| Token | 500-bar p75 | Full-history p75 | Fires? |
|-------|------------|-----------------|--------|
| CHIP | -0.000319° | +0.003224° | YES (wrong) |
| MORPHO | -0.000256° | +0.001407° | YES (wrong) |
| MOVE | -0.000080° | +0.003224° | YES (wrong) |

**Fix:** Compute p75 from the token's FULL angle history, not the 500-bar window. The current angle is still from 500 bars (needed for responsiveness), but the percentile threshold reflects the token's full historical steepness:

```python
# Fetch ALL available closes for p75 computation
all_closes = _get_1m_prices_full(token)  # all historical candles
all_ema = _ema(all_closes, 300)
all_angles = [math.degrees(math.atan((all_ema[i] - all_ema[i-20])/20 / all_ema[i]))
              for i in range(20, len(all_ema))]
all_sorted = sorted(all_angles[10:])  # skip first 10 (speed warmup)
full_p75 = all_sorted[int(len(all_sorted) * 0.75)]

# Current angle from 500-bar window, threshold from full history:
angle_meets_minimum = latest_angle >= full_p75
```

**PURR reference:** PURR's full-history p75 = 0.002046°. Signal fires when angle > full_p75 AND price above EMA AND EMA rising.

## Bug #19: Stale Price Index — Wrong Bar for Timestamp and Price Field

**Symptom:** `latest_ts = prices[latest_idx + speed_period][0]`. With 500 prices and latest_idx=479, `prices[489]` is OUT OF BOUNDS. Even when valid, reads ~10 bars stale.

**Fix:** Use `prices[-1]` for actual latest price/timestamp. Returned `price` field uses `closes[-1]`, not `closes[latest_idx + speed_period]`.

---

## Critical Pitfall: Delisted Token Signal Contamination

**Symptom (ILV case, 2026-05-05):** Breakout engine fires a signal for ILV LONG at $4.66, conf=95. Guardian can't trade it — ILV returns `None` on Hyperliquid (delisted). Token shows in hot-set for 15+ minutes.

## See Also

- `references/stale-price-data-bug.md` — Bug #16: signal reads from stale `price_history` instead of live `candles.db`, causing counter-trend entries (15 losing trades, 2026-05-13)

**Root cause — two-layer bug:**

1. **`_seed_universe_candles()` has no `isDelisted` check** (`price_collector.py` lines 143-146):
   ```python
   # WRONG — includes delisted tokens:
   all_tokens = sorted(set(u['name'] for u in universe if ...))
   ```
   Binance has ILV data (ILV trades on Binance). Seeding writes ILV candles at ~$4.66 into `candles.db`.

2. **Breakout engine token list = "anything with recent candles"** (`breakout_engine.py` lines 557-562):
   ```python
   c.execute('''SELECT DISTINCT token FROM candles_1m WHERE ts > strftime('%s','now','-30 minutes')''')
   tokens = [r[0] for r in c.fetchall()]
   ```
   ILV has recent-looking Binance candles → passes filter → fires signal.

**The fix** (applied 2026-05-05):
```python
# price_collector.py line ~143 — ADD isDelisted filter:
all_tokens = sorted(set(
    u['name'] for u in universe
    if u.get('name')
    and not u['name'].startswith('@')
    and len(u['name']) <= 10
    and not u.get('isDelisted', False)  # ← ADD THIS
))
```

**Recovery steps:**
1. Fix the source (`price_collector.py` as above)
2. Delete stale delisted tokens from candles.db:
   ```python
   # Delete across all timeframes
   for tf in ['1m', '5m', '15m', '1h', '4h']:
       c.execute(f'DELETE FROM candles_{tf} WHERE token=?', ('ILV',))
   ```
3. Clean delisted tokens from hl_cache.json `allMids`:
   ```python
   delisted = [u['name'] for u in universe if u.get('isDelisted')]
   for k in list(mids.keys()):
       if k in delisted: del mids[k]
   ```

**Rule for new signals reading from candles.db:** Always cross-check against live HL universe before treating a token as tradeable. The `candles.db` token list is "anything anyone ever seeded" — not "currently active on HL." Use:
```python
from hyperliquid_exchange import get_all_token_names  # set of live HL tokens
live_tokens = get_all_token_names()
# filter: token in live_tokens
```

## `compute_regime()` Return Values

**Returns 5 values, not 3:**
```python
regime, long_mult, short_mult, use_regime_filter, avg_abs_speed = compute_regime()
```
- `regime`: str — 'bullish' | 'bearish' | 'neutral'
- `long_mult`: float — multiplier for LONG confidence
- `short_mult`: float — multiplier for SHORT confidence
- `use_regime_filter`: bool — whether to apply regime filtering
- `avg_abs_speed`: float — average absolute speed across tokens

**Migrated signal scripts that use `compute_regime()` must unpack with `*_`:**
```python
# WRONG (ValueError: too many values to unpack):
regime, long_mult, short_mult = compute_regime()

# RIGHT:
regime, long_mult, short_mult, *_ = compute_regime()
```
Affected: `mtf_momentum.py`, `momentum.py`

## `run_all_signals()` Dispatch Pattern

In `signals/__init__.py`, `run_all_signals()` iterates the registry and dispatches to each signal's `run()` function. Some scan functions need `prices_dict` (they fetch data internally), others don't.

**Detection pattern — use `inspect.signature`:**
```python
import inspect

def _needs_prices_dict(fn):
    try:
        sig = inspect.signature(fn)
        return 'prices_dict' in sig.parameters
    except (ValueError, TypeError):
        return False  # built-in or C extension — skip

def run_all_signals(prices_dict=None, **kwargs):
    results = {}
    for s in SIGNAL_REGISTRY:
        if not s['enabled'] or s['run'] is None:
            continue
        fn = s['run']
        try:
            if _needs_prices_dict(fn):
                results[s['name']] = fn(prices_dict, **kwargs)
            else:
                results[s['name']] = fn(**kwargs)
        except Exception as e:
            results[s['name']] = {'error': str(e)}
    return results
```

**Always test migrated signals individually:**
```bash
cd /root/.hermes/scripts
python3 -c "
import sys; sys.path.insert(0, '.')
from signals.{name} import scan_{name}_signals
import inspect
sig = inspect.signature(scan_{name}_signals)
print(f'{name}: params = {list(sig.parameters.keys())}')
"
```

### candles.db query — ALWAYS use DESC then reversed() (2026-05-09)
**Bug**: `_get_candles_5m` used `ORDER BY ts ASC LIMIT 120` — returned oldest 120 rows (2026 data),
not most recent. candles.db has years of historical data. ASC query returns the oldest rows first.
**Fix**: `ORDER BY ts DESC LIMIT N` then `list(reversed(rows))` to get most-recent-first in
oldest-first array order. Save `most_recent_ts = rows[0][0]` BEFORE reversal (rows[0] is most
recent before reversal). After reversal, rows[0] is oldest.

### Freshness guard timing for 5m candles (2026-05-09)
5m candles update with lag. A freshness guard of 300s (5 min) is too tight — misses candles
that are 6-8 min old due to exchange API delays. Relax to 600s (10 min) for 5m candles.
1m candles can use 300s.

### Slope threshold calibration — empirical not theoretical (2026-05-09)
Slope thresholds derived from theory can be 8x too strict. ME: diagonal drop of -0.66% over
10h = slope of -6.3e-06 per 5m candle. Theoretical minimum was set to 1e-6, which excluded ME.
Test against real candle data before setting thresholds. A slope that misses real patterns
needs adjustment, not the data.

### Bounce clustering tolerance — TL_ZONE_ATR_K too tight (2026-05-09)
`TL_ZONE_ATR_K=0.75` (bounces must be within 0.75×ATR to cluster into a horizontal zone)
was too strict for 2Z — bounces at indices [26, 74] didn't cluster. Widening to 1.5×ATR
or reducing MIN_BOUNCES from 2 to 1 unlocks valid signals.

### Lookback window must match the actual pattern duration (2026-05-09)
120 candles (10h) averages the diagonal portion with flat/ranging periods that follow,
weakening the slope signal. For a 6-10h diagonal, either reduce lookback to 60 candles (6h)
or add a "recent slope" check — require the last 30-40 candles to also show the diagonal
direction, not just the full window.

### Pattern signal implementation: tl_break.py (2026-05-09)
Diagonal trendline breakout signal at `/root/.hermes/scripts/signals/tl_break.py`.
Architecture: linear regression slope → bounce detection → bounce clustering → breakout
confirmation → follow-through scoring. Bidirectional (LONG on downside break, SHORT on
upside break). Output via `signal_metadata` dict (no new DB columns needed).
Key params: `TL_SLOPE_LONG=-0.000001`, `TL_SLOPE_SHORT=0.000001`, `TL_SLOPE_MAG_MIN=0.000001`,
`TL_ZONE_ATR_K=1.5`, `TL_MIN_BOUNCES=2`, `TL_BREAKOUT_ATR=1.5`, `TL_FOLLOW_ATR=2.0`.
See `references/tl-break-implementation-2026-05-09.md` for full trace.

## 7. The `run()` Wrapper Pattern — Required for signals_runner

**Every signal module in `signals/` MUST have a `run()` function for signals_runner to discover it.**

The correct architecture is a two-file separation:

```
/root/.hermes/scripts/{name}_signals.py     ← detection logic, scan_* functions (pure library)
/root/.hermes/scripts/signals/{name}.py       ← signals_runner wrapper, has run()
```

**Wrapper pattern (`signals/{name}.py`):**
```python
# signals_runner entry point
# ═══════════════════════════════════════════════════════════════════════════════

# Re-export so signals/__init__.py import works
from {name}_signals import scan_{name}_signals as _scan_fn

def run(prices_dict=None):
    """Entry point for signals_runner. Returns count of signals emitted."""
    if prices_dict is None:
        from signal_schema import get_all_latest_prices
        prices_dict = get_all_latest_prices()
    count, tokens = _scan_fn(prices_dict)
    return count  # signals_runner expects int, not tuple
```

**Critical: the wrapper MUST re-export the scan function** — `from {name}_signals import scan_{name}_signals` — so direct imports (`from signals.{name} import scan_{name}_signals`) continue to work. Without the re-export, direct imports raise `ImportError`.

**The run() function is what signals_runner's SIGNAL_REGISTRY looks for.** Without it, the signal is invisible to the pipeline even if the scan function is correct.

### Common Bugs

**Bug: run() calls scan function that wasn't imported**
```
NameError: name 'scan_ma300_candle_signals' is not defined
```
Fix: add `from ma300_candle_confirm_signals import scan_ma300_candle_signals` inside `run()`.

**Bug: ma_cross ignoring PLUS/MINUS killswitch**
`MA_CROSS_PLUS_ENABLED = False` but LONG signals still fire. The scan function checks the old `MA_CROSS_ENABLED` but not the per-direction flags. Fix: add per-direction checks before add_signal:
```python
from hermes_constants import MA_CROSS_PLUS_ENABLED, MA_CROSS_MINUS_ENABLED
if direction == 'LONG' and not MA_CROSS_PLUS_ENABLED:
    continue
if direction == 'SHORT' and not MA_CROSS_MINUS_ENABLED:
    continue
```

---

## Key Files

- `/root/.hermes/scripts/signal_gen.py` — main pipeline (still calls inline signals, migration target)
- `/root/.hermes/scripts/signals/` — **canonical home for all signal scripts** (new architecture)
- `/root/.hermes/scripts/signals/__init__.py` — signal registry: `SIGNAL_REGISTRY`, `get_registered_signals()`, `run_all_signals()`
- `/root/.hermes/scripts/signal_compactor.py` — hot-set scoring
- `/root/.hermes/scripts/signal_schema.py` — `add_signal()` (Layer 2 kill-switch), `validate_source()` (blacklist)
- `/root/.hermes/scripts/decider_run.py` — execution gate (Layer 3 kill-switch)
- `/root/.hermes/scripts/hermes_constants.py` — `SIGNAL_SOURCE_BLACKLIST`, `*_ENABLED` flags (Layer 1 kill-switch), direction-specific signal thresholds (`MIN_GAP_PCT_LONG`, `MIN_GAP_PCT_SHORT`, etc.)
- `/root/.hermes/data/candles.db` — local candle data (`candles_1m`, `candles_5m`, etc.)
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

---

## 5f. Pre-Cursor Signals — Accumulation Detection

**NEW (2026-05-05):** All existing signals are **in-flight** type — they require momentum to already be happening. None detect the **accumulation phase** before a move starts.

**The gap:** Volume builds 8-10x normal while price grinds in a tight range — classic smart money accumulation pattern. EIGEN showed this 30-40 minutes before a 15% pump. Existing signals caught it 0 minutes early.

**Priority signal:** `volrange_div` — volume/range divergence. See `references/volrange-div-signal.md` for full design spec.

**Key distinction:** Pre-cursor signals use COMPRESSION STATE MACHINES — track volume accumulation while price stays range-bound, fire only on the confirmed breakout with volume.

## Related Skills (Reference Files)

- [ema-angle-signal](./references/ema-angle-signal.md) — EMA300 signed angle signal: signed angle fix, cooldown pattern, registration steps, post-entry win rates. Key finding: abs() in angle formula breaks SHORT detection.
- [new-signal-implementation.md](./references/new-signal-implementation.md) — original fixed-param implementation guide
- `references/signal-lessons-learned.md` — regime-naive signals, FINAL_VERIFY wrong bar, hardcoded constants, stale signals, audit false positives
- `references/new-signal-implementation.md` — original fixed-param implementation guide
- `references/accel-300-early-entry-fix-2026-05-09.md` — **2026-05-09**: PERSISTENCE_BARS 2→1 + MIN_GAP_PCT 0.10→0.15 fix; live trade analysis; acceleration gate logic with PB=1; watch-for metrics
- `references/signal-bug-patterns-jun-2026.md` — Bug #16: signed metric in confidence formula gives SHORT zero bonus (abs() fix); Bug #17: recovery branch missing downstream state variable causes hard gate to block valid recovered signals (e.g. rs.py broken resistance bounces=True)
- `references/phase_accel_signal.md` — phase_accel extraction example (bug fixes, momentum_cache prev_phase pattern, sys.path trick for signals/ subdirectory)
- `references/signal-architecture-2026-05-05.md` — **3-layer kill-switch architecture, migration state, current flag settings**
- `references/ema-angle-signal.md` — EMA300 angle signal: concept, params, backtest results, verified entry timestamps
- `references/ema-angle-long-floor-bug.md` — **2026-05-15**: Bugs #16/#17 — asymmetric ABS_ANGLE_FLOOR on LONG (SHORT works, LONG doesn't), no EMA cross confirmation. Remove floor, add cross check.
- `references/new-signal-implementation.md` — original fixed-param implementation guide
- `references/per-token-tuned-signal.md` — scanner + tuner + systemd pattern
- `references/per-direction-killswitches.md` — per-direction flag implementation, patterns, and audit results (P0: hh_hl pass bug, pre-existing SIGNAL_SOURCE_BLACKLIST={} bug)
- `references/breakout-signal-implementation.md` — compression-breakout signal
- `references/hh-hl-unit-mismatch-bug.md` — HH_HL breakout_strength unit mismatch bug (breakout_strength in % vs threshold in decimal fraction)
- `references/rs-bounce-threshold-fix.md` — RS bounce threshold ATR fix (ATR multipliers must be validated against low-ATR tokens)
- `references/rs-signal-implementation.md` — RS signal type must be `'rs'` (not `'support_resistance'`). ATR band filter 0.30-0.60 ATR rejects valid setups. Touch_count quality bands: rs-s16-150 = 100% WR gold zone. Source field IS correct (`rs-s150` format). Phase scan results: 191 tokens classified (ACCEL=34, EXH=16, EXT=27).
- `references/accel-300-rs-signal-combo.md` — **2026-05-07**: best working combos. accel-300+ + rs-s48/rs-s72/rs-s140 = +4-5% wins. Pattern: momentum + strong support level bounce. DASH +4.80% with 4-way combo. Why it works, anti-patterns, implementation notes.
- `references/zscore-momentum-signal.md` — z-score momentum signal
- `references/fake-dump-short-signal.md` — fake-dump short detection
- `references/ma-cross-parameter-sweep.md` — EMA cross param sweep
- `references/ma-cross-parameter-sweep.md` — EMA cross param sweep
- `references/ma-cross-sep-tuning.md` — EMA separation threshold tuning
- `references/mtf-macd-signal-debug.md` — MTF-MACD debug guide
- `references/mtf-macd-backtest-findings.md` — MTF-MACD backtest results
- `references/vectorized-macd-param-sweep.md` — numpy MACD sweep
- `references/dydx-momentum-signal-backtest.md` — DYDX momentum backtest
- `references/trend-signal-backtest.md` — ADX+MACD backtest
- `references/rsi-backtest.md` — RSI signal evaluation
- `references/rsi-backtest.md` — RSI signal evaluation
- `references/pump-hunter-backtest.md` — pump_hunter mean-reversion
- `references/zscore-pump-backtest.md` — zscore_pump methodology
- `references/zscore-pump-migration-2026-05-16.md` — migration from standalone executor to pipeline signal (guardian conflict fix)
- `references/r2-trend-5m-backtest.md` — R² trend 5m backtest
- `references/momentum-mean-reversion-backtest.md` — combined momentum+reversion
- `references/ema_angle-signal.md` — EMA300 angle signal (ema_angle) implementation notes

## 7. EMA300 Angle Signal (ema_angle)

**Source:** `ema-angle+` (LONG), `ema-angle-` (SHORT)

**IMPORTANT (2026-05-16):** Formula changed from `arctan(slope_n / ema_val)` (degrees) to `arctan(Δprice_20 / price)` (radians).
The old formula produced angles orders of magnitude too small — 45° was unreachable (needed price to double). The new formula uses the natural 0-90° compass range via radians. See `references/ema-angle-signal.md` for full analysis.

**Angle = `arctan(Δprice_20 / price)` in RADIANS** — signed:
- `+angle` = price above EMA, trending up
- `-angle` = price below EMA, trending down
- 0 = price at EMA (flat)

**LONG (ema-angle+) — flat → steep transition:**
- was_flat: all angles < 0.5 rad for last 10 bars
- is_steep: angle >= 0.5 rad AND < 1.0 rad (30° to 45°)
- crossover: angle crossed 0.5 rad (was below, now above)
- accelerating: speed > EMA_ANGLE_MIN_SPEED
- price_above_ema required

**SHORT (ema-angle-) — unchanged:** angle <= p25 with negative speed.

**Key constants (2026-05-16):**
```python
EMA_ANGLE_STEEP_THRESHOLD_RAD = 0.5   # 30° — minimum for LONG steep
EMA_ANGLE_CEILING_RAD         = 1.0   # 45° — don't fire into parabolic
EMA_ANGLE_FLAT_WINDOW         = 10    # bars to check was_flat
EMA_ANGLE_MIN_SPEED          = 0.001  # radians/bar (raised from 0.00005)
```

**T's radian communication:** When T says "0.5-1.0 radians via arctan" — this is the 30°-45° steep window for LONG.
**Reference coin: PURR** — flat-to-45° transition ~48h ago (May 14, 2026 ~03:00 EST).

**Confluence rule:** ema-angle is NEVER solo — always requires another direction-aligned signal.

## 8. Signal Required Gate — signal_compactor.py

**Current rule:** Every hot-set entry MUST include `rs` (support/resistance) as co-signal — `accel-300` is no longer the required signal (swapped 2026-05-15).

```python
# signal_compactor.py lines ~632-637
has_rs = any(p.startswith('rs') for p in source_parts)
if not has_rs:
    log(f"  SKIP {token} {direction}: no rs signal")
    continue
```

To change the required signal: swap `has_rs` check to match the desired signal prefix (e.g., `any(p.startswith('accel-300') for p in source_parts)` for accel-300).

- `references/same-timeframe-confluence-illusion-2026-05-21.md` — **2026-05-21**: Trade archive analysis (700 trades, excluding accel-300/profit-monster). Key finding: zscore_pump+RS combos lose vs RS alone. All active signals (zscore_pump, rs, hhh, accel_300, ema_angle) read the same 1m price_history source — they are not independent, they amplify noise together. RS_SHORT alone = +$83 on 96 trades. zscore_pump+RS combos = -$20 on 42 trades. Real confluence requires multi-timeframe independence, not same-bar repetition.
- `references/zscore-pump-extreme-z-losses-2026-05-24.md` — Extreme z-score (|z|>4) strongly associated with SL-trigger losses. z=6.7 SHORT fires same as z=2.1 SHORT but is a blow-off top about to reverse. Proposed fix: `ZSCORE_PUMP_MAX_Z=4.0` cap and `ZSCORE_PUMP_SHORT_MAX_Z=3.5` (stricter for SHORT — crypto down-moves are faster). Winners have z ~2.0-3.0. Losers have z > 4.0. Divergence filter alone insufficient — needs hard z cap.

## Critical Pipeline Name — signal_compactor.py NOT signal_runner

The hot-set pipeline owner is `signal_compactor.py` — NOT "signal_runner.py" or "signals_runner.py". T has corrected this twice. When a skill or plan says "runner", read it as `signal_compactor.py`.

When adding a new signal to Hermes, two files must be updated together:
1. `signals/__init__.py` — register the scanner (import + SIGNAL_REGISTRY entry + `name_to_module` dict)
2. `signal_compactor.py` — add `SIGNAL_SOURCE_WEIGHTS` entries so the compactor recognizes the new source tags

Without (2), the signal is invisible to the hot-set regardless of how many signals are written.

---

## Critical Bugs Reference
- `references/regime-directionality-fix-2026-05-11.md` — RS regime Model B + compactor multiplier update (aligned→1.50x, counter→0.50x, neutral→0.50x)
- `references/hmacd-signal.md` — HMACD signal: standalone histogram-MACD 15m+1H agreement, fires hmacd+ / hmacd-
- `references/momentum-mean-reversion-backtest.md` — combined momentum+reversion
- `references/signal-quality-2026-05-05.md` — confluence gate fix, vel-hermes- unblock, regime filter verification, signal quality root causes
