# Signal Quality Fix — 2026-05-05
## Updated: 2026-05-06 Morning Session

## Background
T reported signals were incorrect calls — coins instantly doing the opposite of what signals predicted. P&L in the gutter. This plan documents the migration from inline signal_gen.py to a clean registry-based architecture.

---

## Architecture: Before vs After

### BEFORE
- signal_gen.py: monolithic, all signals inline, no kill-switch guards
- Blacklist: SIGNAL_SOURCE_BLACKLIST in hermes_constants.py — all manually commented out (redundant with Layer 2)
- Two sources firing same signals simultaneously

### AFTER
- scripts/signals/: individual signal scripts extracted, each independently callable
- signals_runner.py: canonical pipeline step, reads from SIGNAL_REGISTRY
- signal_gen removed from STEPS_EVERY_MIN (all master *_ENABLED flags = False)
- blacklist commented out — Layer 2 add_signal() is sole per-source gate
- Directional flags (*_PLUS_ENABLED, *_MINUS_ENABLED) control signal direction

---

## Pipeline Architecture

STEPS_EVERY_MIN = [signal_compactor, breakout_engine, signals_runner, decider_run, position_manager, hermes-trades-api]
STEPS_EVERY_5M  = [signals_runner_slow]  # momentum + mtf_momentum

signals_runner.py --slow (every 5 min):
  - momentum, mtf_momentum (scan 191 tokens, ~180s each)

signals_runner.py (every minute):
  - 21 fast signals: pct_hermes, vel_hermes, hzscore, hmacd, phase_accel, fast_momentum, accel_300, rs, ma_cross, ma_cross_5m, hh_hl, guppy, macd_accel, trend_purity, ema9_sma20, r2_trend, volume_hl, ma300_candle_confirm, atr_compression, exhaustion, counter_flip

---

## Kill-Switch Architecture (3 Layers)

| Layer | File | What it does |
|-------|------|------|
| Layer 1 | hermes_constants.py *_ENABLED flags | Script-level gate — set False to block entire signal family |
| Layer 2 | signal_schema.py add_signal() | Per-source directional filtering — checks *_PLUS/_MINUS_ENABLED |
| Layer 3 | decider_run.py execution gate | Final block before trade executes |

---

## Kill-Switch Flag State (Current — Updated 2026-05-06)

### Master Flags (False = signal_gen inline blocked, registry scripts handle it)
PCT_HERMES_ENABLED=False     # was True  | BLOCKED
VEL_HERMES_ENABLED=False    # was True  | BLOCKED
HZSCORE_ENABLED=False      # was True  | BLOCKED
HMACD_ENABLED=False        # was True  | BLOCKED
MOMENTUM_ENABLED=False    # was True  | BLOCKED
MTF_MOMENTUM_ENABLED=False # was True | BLOCKED
PHASE_ACCEL_ENABLED=False  # was True  | BLOCKED
FAST_MOMENTUM_ENABLED=False # was True | BLOCKED

### Directional Flags (True = allowed to fire, False = BLOCKED)
PCT_HERMES_PLUS_ENABLED=True    # pct-hermes+ | PASS
PCT_HERMES_MINUS_ENABLED=False # pct-hermes- | BLOCKED (catches knives)
VEL_HERMES_PLUS_ENABLED=False  # vel-hermes+ | BLOCKED
VEL_HERMES_MINUS_ENABLED=True  # vel-hermes- | PASS
HZSCORE_PLUS_ENABLED=True      # hzscore+ | PASS
HZSCORE_MINUS_ENABLED=True     # hzscore- | PASS
HMACD_PLUS_ENABLED=True       # hmacd+ | PASS
HMACD_MINUS_ENABLED=True      # hmacd- | PASS
MOMENTUM_PLUS_ENABLED=False    # momentum+ | BLOCKED (no Layer 2 guard — was firing!)
MOMENTUM_MINUS_ENABLED=False  # momentum- | BLOCKED (no Layer 2 guard — was firing!)
MTF_MOMENTUM_PLUS_ENABLED=True  # mtf-momentum+ | PASS
MTF_MOMENTUM_MINUS_ENABLED=True # mtf-momentum- | PASS
PHASE_ACCEL_PLUS_ENABLED=True  # phase-accel+ | PASS
PHASE_ACCEL_MINUS_ENABLED=True # phase-accel- | PASS
FAST_MOMENTUM_PLUS_ENABLED=True  # fast-momentum+ | PASS
FAST_MOMENTUM_MINUS_ENABLED=False # fast-momentum- | BLOCKED (losing signal)

### OpenClaw Signal Flags (all BLOCKED — had no Layer 2 guard)
OC_MTF_MACD_ENABLED=False    # oc-mtf-macd+, oc-mtf-macd- | BLOCKED
OC_RSI_ENABLED=False         # oc-rsi+, oc-rsi- | BLOCKED
OC_MTF_RSI_ENABLED=False     # oc-mtf-rsi+, oc-mtf-rsi- | BLOCKED
OC_PENDING_ENABLED=False     # oc-pending-* | BLOCKED

### Other Signals (not migrated from inline — already had their own flags)
ACCEL_300_ENABLED=True        # accel-300+ | PASS
RS_ENABLED=True               # rs | PASS
GAP_300_ENABLED=False         # gap-300+ | BLOCKED
GAP_300_MINUS_ENABLED=False   # gap-300- | BLOCKED
MA_CROSS_ENABLED=False        # ma_cross+ | BLOCKED
MA_CROSS_PLUS_ENABLED=False   # ma_cross+ | BLOCKED
MA_CROSS_MINUS_ENABLED=True   # ma_cross- | PASS
MA_CROSS_5M_ENABLED=False     # ma_cross_5m | BLOCKED
MA_CROSS_5M_PLUS_ENABLED=False # ma_cross_5m+ | BLOCKED
MA_CROSS_5M_MINUS_ENABLED=True # ma_cross_5m- | PASS
HH_HL_ENABLED=False           # hh_hl | BLOCKED
GUPPY_ENABLED=True            # guppy | PASS
MACD_ACCEL_ENABLED=True       # macd_accel | PASS
TREND_PURITY_ENABLED=False    # trend_purity | BLOCKED
EMA9_SMA20_ENABLED=False      # ema9_sma20 | BLOCKED
R2_REV_ENABLED=False          # r2_rev+/r2_rev- | BLOCKED
R2_TREND_ENABLED=True         # r2_trend | PASS
VOLUME_HL_ENABLED=False       # volume_hl | BLOCKED
MA300_CANDLE_ENABLED=False   # ma300_candle_confirm | BLOCKED
ATR_COMPRESSION_ENABLED=False # atr_compression | BLOCKED
EXHAUSTION_ENABLED=True       # exhaustion | PASS
COUNTER_FLIP_ENABLED=True     # counter_flip | PASS

### Signals BLOCKED at Layer 2 (22 + variants)
pct-hermes-, vel-hermes+, momentum+/momentum-/momentum bare,
fast-momentum-, gap-300+/gap-300-, ma_cross+, ma_cross_5m+,
r2_rev+/r2_rev-, oc-mtf-macd+/-, oc-rsi+/-, oc-mtf-rsi+/-, oc-pending-*


---

## Signal → Kill-Switch Mapping (Blacklist Sources)

| Blacklisted Signal | Flag | Status |
|--------------------|------|--------|
| pct-hermes- | PCT_HERMES_MINUS_ENABLED=False | BLOCKED |
| vel-hermes+ | VEL_HERMES_PLUS_ENABLED=False | BLOCKED |
| hzscore+ | HZSCORE_PLUS_ENABLED=True | PASS (keep) |
| hzscore- | HZSCORE_MINUS_ENABLED=True | PASS (keep) |
| momentum+ | MOMENTUM_PLUS_ENABLED=False | BLOCKED (no Layer 2 guard — was firing!) |
| momentum- | MOMENTUM_MINUS_ENABLED=False | BLOCKED (no Layer 2 guard — was firing!) |
| mtf-momentum+ | MTF_MOMENTUM_PLUS_ENABLED=True | PASS (keep) |
| mtf-momentum- | MTF_MOMENTUM_MINUS_ENABLED=True | PASS (keep) |
| phase_accel+ | PHASE_ACCEL_PLUS_ENABLED=True | PASS (keep) |
| phase_accel- | PHASE_ACCEL_MINUS_ENABLED=True | PASS (keep) |
| fast-momentum+ | FAST_MOMENTUM_PLUS_ENABLED=True | PASS (keep) |
| fast-momentum- | FAST_MOMENTUM_MINUS_ENABLED=False | BLOCKED (losing signal) |
| hmacd+ | HMACD_PLUS_ENABLED=True | PASS (keep) |
| hmacd- | HMACD_MINUS_ENABLED=True | PASS (keep) |
| oc-mtf-macd | OC_MTF_MACD_ENABLED=False | BLOCKED |
| oc-rsi | OC_RSI_ENABLED=False | BLOCKED |
| oc-mtf-rsi | OC_MTF_RSI_ENABLED=False | BLOCKED |
| oc-pending | OC_PENDING_ENABLED=False | BLOCKED |

---

## Bugs Fixed

1. pct-hermes+ still in blacklist despite "REMOVED" comment → actually removed
2. ACCEL_300_ENABLED missing from __init__.py imports → added
3. mtf_momentum / momentum: compute_regime() returns 5 values, not 3 → `regime, long_mult, short_mult, *_ = compute_regime()`
4. run_all_signals() didn't pass prices_dict to scan functions → _needs_prices_dict() inspection dispatch
5. accel_300.py: get_cooldown() returns bool not dict → direct bool check
6. accel_300.py: get_cooldown not imported → added to imports
7. hh_hl and ema9_sma20: wrong function names in __init__.py → fixed to scan_hh_hl_signals / scan_ema9_sma20_signals
8. r2_rev+ and r2_rev- bypassed R2_REV_ENABLED=False → added explicit directional checks in add_signal()
9. Registry showed 15 instead of 23 signals → enabled=True hardcoded for 8 migrated signals (were using False master flags)
10. signal_gen still in STEPS_EVERY_MIN → removed (was burning compute for zero output)
11. Registry had wrong import names for hh_hl and ema9_sma20 → fixed function pointers
12. pct_hermes docstring still referenced kill-switch guard → removed, comment notes guard in signal_gen.py
13. phase_accel had broken indentation from patch → fixed
14. fast_momentum had wrong branch variable (bullish_tfs instead of bearish_tfs) → fixed

---

## Outstanding

1. **Pipeline timing** — signals_runner FAST takes ~120s for 21 signals. Pipeline should complete every minute; slow signals (momentum, mtf_momentum) run every 5 min. May need further optimization.

2. **momentum + mtf_momentum slow** — both scan 191 tokens and compute regime independently. Could share prices_dict and regime result in a future optimization pass.

3. **Signal quality** — T reported signals were incorrect calls. The kill-switch flags address which signals fire. Whether the signals that DO fire are profitable requires live P&L tracking. pct-hermes- (catches knives) and vel-hermes+ (0% WR) are blocked. accel-300+ and hzscore+ remain active. Monitor WR/PnL per source.

---

## Files Changed

- scripts/signals/__init__.py — 24-signal registry, fast/slow split, run_all_signals dispatch
- scripts/signals_runner.py — fast/slow mode via --slow flag, signal_list parameter
- scripts/run_pipeline.py — removed signal_gen, added signals_runner_slow, timeouts updated
- scripts/hermes_constants.py — master *_ENABLED=False for migrated signals, directional flags preserved
- scripts/signal_schema.py — r2_rev+ and r2_rev- explicit kill-switch checks added
- scripts/signal_gen.py — all inline signals wrapped with if not *_ENABLED: continue
- scripts/signals/pct_hermes.py — removed Layer 1 guard (registry handles it)
- scripts/signals/vel_hermes.py — removed Layer 1 guard
- scripts/signals/hzscore.py — removed Layer 1 guard
- scripts/signals/hmacd.py — removed Layer 1 guard
- scripts/signals/mtf_momentum.py — removed Layer 1 guard
- scripts/signals/momentum.py — removed Layer 1 guard
- scripts/signals/phase_accel.py — removed Layer 1 guard
- scripts/signals/fast_momentum.py — removed Layer 1 guard
- scripts/signals/mtf_momentum.py — compute_regime 5-value unpack fix
- scripts/signals/momentum.py — compute_regime 5-value unpack fix
- scripts/signals/accel_300.py — get_cooldown bool fix + direction-aware cooldown
- scripts/signals/hh_hl.py — wrong function name fixed
- scripts/signals/ema9_sma20.py — wrong function name fixed

---

## Session Progress — 2026-05-06 Morning (Complete)

### What Was Done

#### Architecture Migration Complete
- **signal_gen.py inline signals → signals_runner registry**
- `signal_gen` removed from STEPS_EVERY_MIN in run_pipeline.py
- All 8 migrated signals: Layer 1 guards removed from registry scripts, now controlled by Layer 2 (add_signal in signal_schema.py) + hermes_constants flags

#### Kill-Switch Gaps Found and Fixed (CRITICAL — was losing money)
The following signals had **NO Layer 2 kill-switch** in signal_schema.py add_signal() despite being blacklisted:
- `momentum+/momentum-/momentum bare` — had no Layer 2 guard at all (critical bug — these were firing!)
- `oc-mtf-macd+/oc-mtf-macd-` — no guard (were firing!)
- `oc-rsi+/oc-rsi-` — no guard (were firing!)
- `oc-mtf-rsi+/oc-mtf-rsi-` — no guard
- `oc-pending-*` — no guard

**Fix:** Added all OC kill-switch flags + momentum flags to hermes_constants.py and Layer 2 guards to signal_schema.py

#### hermes_constants.py — New Flags Added
```
OC_MTF_MACD_ENABLED    = False  # oc-mtf-macd+, oc-mtf-macd-
OC_RSI_ENABLED         = False  # oc-rsi+, oc-rsi-
OC_MTF_RSI_ENABLED     = False  # oc-mtf-rsi+, oc-mtf-rsi-
OC_PENDING_ENABLED     = False  # oc-pending-*
MOMENTUM_ENABLED       = False  # momentum bare — BLOCKED
MOMENTUM_PLUS_ENABLED  = False  # momentum+ — BLOCKED
MOMENTUM_MINUS_ENABLED = False  # momentum- — BLOCKED
MTF_MOMENTUM_ENABLED   = False  # mtf_momentum bare — BLOCKED
MTF_MOMENTUM_PLUS_ENABLED = True   # mtf-momentum+ — PASS
MTF_MOMENTUM_MINUS_ENABLED = True  # mtf-momentum- — PASS
PHASE_ACCEL_ENABLED    = False  # phase_accel bare — BLOCKED
FAST_MOMENTUM_ENABLED  = False  # fast_momentum bare — BLOCKED
FAST_MOMENTUM_MINUS_ENABLED = False # fast-momentum- — BLOCKED
```

#### signal_schema.py — Layer 2 Kill-Switch Added
New block after fast-momentum guards:
- `momentum+/momentum-/momentum` → MOMENTUM_PLUS/MINUS/ENABLED
- `oc-mtf-macd+/oc-mtf-macd-` → OC_MTF_MACD_ENABLED
- `oc-rsi+/oc-rsi-` → OC_RSI_ENABLED
- `oc-mtf-rsi+/oc-mtf-rsi-` → OC_MTF_RSI_ENABLED
- `oc-pending-*` (prefix match) → OC_PENDING_ENABLED

#### oc_signal_importer.py — Early-Return Guards (4 layers of defense)
- `import_mtf_macd_signals()`: `if not OC_MTF_MACD_ENABLED: return 0`
- `import_rsi_signals()`: `if not OC_RSI_ENABLED: return 0`
- `import_pending_signals()`: `if not OC_PENDING_ENABLED: return 0` + `oc-mtf-rsi` per-signal guard inside loop
- `run_oc_import()`: master `any([all flags])` guard at top

#### signals_runner.py — Fast/Slow Split
- New `--slow` flag: runs only momentum + mtf_momentum (2 signals)
- get_fast_signals() = 21 signals, get_slow_signals() = 2 signals
- Slow signals run every 5 min via signals_runner_slow step

#### Duplicate Flags Cleaned Up
- Removed duplicate legacy MOMENTUM/MTF_MOMENTUM/PHASE_ACCEL/FAST_MOMENTUM flags from Signal Kill Switches section (were inconsistent — True values next to False)
- Consolidated authoritative values in new "Momentum Killswitches" section

### Final Kill-Switch Status (22 blocked signals + variants)
| Signal | Flag | Value |
|--------|------|-------|
| pct-hermes- | PCT_HERMES_MINUS_ENABLED | False ✓ |
| vel-hermes+ | VEL_HERMES_PLUS_ENABLED | False ✓ |
| momentum+ | MOMENTUM_PLUS_ENABLED | False ✓ |
| momentum- | MOMENTUM_MINUS_ENABLED | False ✓ |
| momentum (bare) | MOMENTUM_ENABLED | False ✓ |
| mtf-momentum (bare) | MTF_MOMENTUM_ENABLED | False ✓ |
| phase_accel (bare) | PHASE_ACCEL_ENABLED | False ✓ |
| fast-momentum- | FAST_MOMENTUM_MINUS_ENABLED | False ✓ |
| gap-300+ | GAP_300_PLUS_ENABLED | False ✓ |
| gap-300- | GAP_300_MINUS_ENABLED | False ✓ |
| ma_cross+ | MA_CROSS_PLUS_ENABLED | False ✓ |
| ma_cross_5m+ | MA_CROSS_5M_PLUS_ENABLED | False ✓ |
| r2_rev+ | R2_REV_ENABLED | False ✓ |
| r2_rev- | R2_REV_ENABLED | False ✓ |
| oc-mtf-macd+ | OC_MTF_MACD_ENABLED | False ✓ |
| oc-mtf-macd- | OC_MTF_MACD_ENABLED | False ✓ |
| oc-rsi+ | OC_RSI_ENABLED | False ✓ |
| oc-rsi- | OC_RSI_ENABLED | False ✓ |
| oc-mtf-rsi+ | OC_MTF_RSI_ENABLED | False ✓ |
| oc-mtf-rsi- | OC_MTF_RSI_ENABLED | False ✓ |
| oc-pending-breakout | OC_PENDING_ENABLED | False ✓ |
| oc-pending-mtf-macd-* | OC_PENDING_ENABLED | False ✓ |

### Files Changed (15 files)
1. hermes_constants.py — 7 new flags added, duplicate flags removed
2. signal_schema.py — 11 new Layer 2 kill-switch checks added
3. oc_signal_importer.py — 4 early-return guards added
4. signals_runner.py — rewritten with fast/slow split
5. signals/__init__.py — added get_fast_signals/get_slow_signals
6. run_pipeline.py — signal_gen removed, signals_runner_slow added, timeouts updated
7-14. signals/pct_hermes.py, vel_hermes.py, hzscore.py, hmacd.py, mtf_momentum.py, phase_accel.py, fast_momentum.py, momentum.py — Layer 1 guards removed
15. signal_gen.py — 7 inline signal blocks wrapped with if not *_ENABLED: continue guards

### Still Open
- ~~**Pipeline timing:** signals_runner FAST takes ~120s (21 signals), leaving no headroom in 1-min cycle.~~ ✅ FIXED 2026-05-06
- **Signal quality:** Need to audit which signals have actual edge; filter/remove烂 signals.

---

## Changes Made — 2026-05-06 Afternoon Session (Signal Quality Fix)

### Pipeline Timing Fix
- signals_runner now runs in BACKGROUND (forked subprocess). Non-signal steps complete in ~4s.
- Added `run_bg()` to run_pipeline.py for non-blocking signals_runner.
- Total pipeline time: ~4s (was 120s+).

### Signal Quality Fix (Based on 741-Trade Audit)

**5 changes made:**

1. **accel_300 token allowlist** (`ACCEL_300_TOKEN_ALLOWLIST` in hermes_constants.py)
   - 23 tokens with ≥50% historical WR on accel-300+
   - Rest of tokens blocked from accel-300 signals entirely
   - Prevents wasting on trash coins with no edge

2. **accel_300 co-signal gate** (`ACCEL_300_BLOCK_COSIGS` in signal_compactor.py)
   - Block accel-300+ if paired with `ma-cross-5m+` (16.7% WR) or `pct-hermes+` (35.7% WR)
   - Fires before hot-set entry

3. **pct_hermes threshold raised** (`PCT_RANK_THRESH` 72→80 in pct_hermes.py)
   - Only fires at most extreme 20% of 42-day range (was 28%)
   - Falls through to pct-hermes+ only at truly extreme bottoms

4. **vel_hermes+ hard blocked** (`VEL_HERMES_PLUS_ENABLED=False` in vel_hermes.py)
   - 31% WR, -0.127% avg — wrong direction in bull market

5. **vel_hermes regime filter** (avg_z check in vel_hermes.py)
   - vel-hermes- SHORT: only fires if avg_z < 0 (market below mean)
   - vel-hermes+ LONG: only fires if avg_z > 0 (market above mean)
   - Prevents fading trending markets

6. **GOOD_STANDALONE_SIGNALS updated** with audited 741-trade WR values

### Files Changed
- `hermes_constants.py` — added ACCEL_300_TOKEN_ALLOWLIST, ACCEL_300_BLOCK_COSIGS
- `signals/pct_hermes.py` — raised PCT_RANK_THRESH 72→80
- `signals/vel_hermes.py` — blocked VEL_HERMES_PLUS, added avg_z regime filter
- `signals/accel_300.py` — added token allowlist filter
- `signal_compactor.py` — added co-signal gate, updated GOOD_STANDALONE_SIGNALS
- `run_pipeline.py` — added run_bg() for non-blocking signals_runner
- `signals/__init__.py` — ProcessPoolExecutor for parallel signal execution
