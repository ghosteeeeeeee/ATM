# Plan: mtp-zscore (Multi-Timeperiod Z-Score) Signal

## Goal

Add a new signal `mtp-zscore` that computes z-score momentum on **three simultaneous lookback windows** (50, 100, 150 bars, all in hermes_constants), fires only when ALL 3/3 periods agree on direction — providing automatic regime filtering and reducing false signals from single-period noise.

---

## Current State

**Reference signal**: `signals/zscore_pump.py` — most-tuned signal, single lookback (ZSCORE_PUMP_LOOKBACK=150), reads from `signals_hermes.db` price_history (1m closes), fires LONG/SHORT on |z| > threshold.

**Key zscore_pump patterns to replicate:**
- `_get_1m_prices()` — fetch lookback+50 bars from price_history
- `compute_zscore()` — stdev/mean over a chunk
- `detect_zscore_pump()` — core detection returning dict with token, direction, z_score, etc.
- `scan_zscore_pump_signals()` — scanner with all guards (blacklist, open-positions, cooldown, price-age)
- `add_signal()` call with `signal_type='zscore_pump_long/short'`, `source='zscore-pump+'/'zscore-pump-'`
- Divergence gate (rejects signals when z was extreme then reversing)
- `--dry` CLI flag

**Constants already in `hermes_constants.py` for zscore_pump:**
```
ZSCORE_PUMP_NEW_ENABLED    = True
ZSCORE_PUMP_PLUS_ENABLED  = True
ZSCORE_PUMP_MINUS_ENABLED = True
ZSCORE_PUMP_LOOKBACK      = 150
ZSCORE_PUMP_THRESHOLD     = 3.0
ZSCORE_PUMP_DIVERGENCE_*  = ...
```

**What changes for MTF:** Instead of ONE lookback → THREE (short=50, medium=100, long=150, all in hermes_constants). Instead of |z| > threshold on ONE period → ALL 3/3 periods must agree AND each must pass per-period Z_MIN/Z_MAX bounds check.

---

## Proposed Design

### Signal Type / Source Names
- `signal_type`: `mtp_zscore_long`, `mtp_zscore_short`
- `source`: `mtp-zscore+` (LONG), `mtp-zscore-` (SHORT)
- Registered in `signals/__init__.py` and `signal_compactor.py`

### Core Philosophy — Trend-Following, NOT Mean-Reversion

This is ride-the-momentum, not fade-it. The three periods act as a **multi-timeframe confirmation filter**:
- 50-bar z-score catches the fast move
- 100-bar z-score is the medium-term trend
- 150-bar z-score is the structural trend

**No divergence gate** — zscore_pump's divergence gate rejects signals when z was extremely elevated then crashing. That's anti-momentum logic (meant for mean-reversion). mtp-zscore is the opposite: when ALL THREE periods agree on direction, that's a structural trend that should be ridden until profit-monster or SL closes it.

Exit is handled entirely by **profit-monster / ATR SL** — NOT z-score crossing 0. We don't exit because z looks "tired."

### Core Logic (with per-period min/max bounds check)

For each token:
1. Fetch `max(lookbacks) + 50` bars of 1m closes from `signals_hermes.db`
2. For each period (short/medium/long):
   a. Compute current z-score over that period's lookback (can be positive or negative)
      - If `std == 0` (flat series) → `compute_zscore` returns `None` → period is REJECTED, cannot vote
   b. Compute `z_abs = abs(z)` for BOUNDS check only
   c. Reject period if `z_abs < Z_MIN` (not meaningful enough for THIS period)
   d. Reject period if `z_abs > Z_MAX` (too extended — reject THIS period)
   e. If period passes → direction vote: z > 0 → LONG vote, z < 0 → SHORT vote
3. Count direction votes across all 3 periods
4. Min-agree gate: **ALL 3/3 periods must vote the same direction** (no exceptions)
   - If any period is rejected (None z, Z_MIN fail, Z_MAX fail) → not 3/3 → NO SIGNAL
5. If 3/3 agree SHORT → fire SHORT; if 3/3 agree LONG → fire LONG
6. 3/3 same direction AND all within bounds = fire; anything else = no signal

### z_score Stored in Signal

**`z_score` REAL** — average of all 3 agreeing period z-scores (all 3 passed Z_MIN/Z_MAX bounds checks, all 3 voted same direction). A period that fails Z_MAX or Z_MIN is already excluded from voting — it cannot contaminate the average.

**`z_score_tier` TEXT** — MUST be explicitly passed to `add_signal()` (NOT None, NOT omitted):
```python
z_score_tier=json.dumps({
    'z_short': round(z_short, 3),
    'z_mid':   round(z_mid, 3),
    'z_long':  round(z_long, 3),
    'agree_count': 3,   # always 3 at fire (3/3 agree), future-proofs for potential 2/3 mode
})
```
`import json` is required — zscore_pump.py does not use json.dumps (it passes None), so the import must be explicitly added to mtp_zscore.py.

**`value` param in `add_signal()`** — use the `z_score` average (same as the stored `z_score` REAL column). This is the composite z-score across all 3 periods.

### Named Periods (short / medium / long — no X/Y/Z)

| Period | Lookback | Constant | Z_MIN | Z_MAX | In hermes_constants |
|--------|----------|-----------|-------|-------|---------------------|
| short | 50 | MTP_ZSCORE_LB_SHORT | Z_SHORT_Z_MIN | Z_SHORT_Z_MAX | Yes |
| medium | 100 | MTP_ZSCORE_LB_MID | Z_MID_Z_MIN | Z_MID_Z_MAX | Yes |
| long | 150 | MTP_ZSCORE_LB_LONG | Z_LONG_Z_MIN | Z_LONG_Z_MAX | Yes |

All constants live in `hermes_constants.py` — T can tune any value independently without code changes.

### Per-Period Z-Score Fields (runtime-computed)

```
z_short  = z-score over last 50 closes
z_mid    = z-score over last 100 closes
z_long   = z-score over last 150 closes
```

### z-score Implementation Pitfalls (from zscore_pump hard lessons)

**1. abs() wrapping — direction-agnostic comparison:**
```python
# WRONG — this checks the MAGNITUDE only, loses sign info
if abs(z) < threshold:
    return None
# CORRECT — abs() is only for threshold comparison, direction from sign
if abs(z) < threshold:
    return None
direction = 'LONG' if z > 0 else 'SHORT'
```

**2. Zero stddev — prevents divide-by-zero:**
```python
def compute_zscore(values):
    if len(values) < 2:
        return None
    mean = statistics.mean(values)
    std = statistics.stdev(values)
    if std == 0:        # MUST guard — flat price series has zero stdev
        return None
    return (values[-1] - mean) / std
```

**3. Negative z means SHORT (not an error):**
The z-score formula `(last - mean) / stdev` produces a negative value when price is below its mean. That is correct and expected. `direction = 'LONG' if z > 0 else 'SHORT'` handles it properly.

**4. abs() in min/max bounds — both directions valid:**
Short period z_short = -3.0 is valid. It means price is 3 stdevs BELOW the 50-bar mean → bearish momentum. abs(-3.0) = 3.0 > Z_SHORT_Z_MAX(2.0) → reject (too extended in bearish direction). This is intentional.

**5. Cooldown: set_cooldown takes hours (1 bar = 1 minute on 1m data):**
```python
# mtp-zscore: 20 bars → 20/60 = 0.333 hours (~20 min)
from signal_gen import set_cooldown
set_cooldown(token, direction, hours=MTP_ZSCORE_COOLDOWN_BARS / 60.0)
```

**6. Price staleness check — always verify fresh data:**
```python
most_recent_ts = rows[-1][0]
if (time.time() - most_recent_ts) > 120:
    _log(f"  [mtp-zscore] {token}: stale price_history (last ts {most_recent_ts}), skipping")
    return []
```

**7. Minimum data length:**
```python
# Each period lookback requires its own data length check
if len(prices) < MTP_ZSCORE_LB_LONG + 2:   # longest period needs most data
    continue
```

**8. Falsy-0.0 bug — NEVER use `or 0` with float fields:**
```python
# WRONG — float('nan') or 0 → 0 (wrong), float(0.0) or 0 → 0 (also wrong),
# any falsy float hits the or and returns int 0 instead of the float 0.0
z = float(row['z_score'] or 0)

# CORRECT — explicit None check preserves real 0.0 values
z = float(row['z_score']) if row['z_score'] is not None else None
```

**9. Signal metadata JSON encoding — always json.dumps() for multi-field storage:**
```python
# Composite z values stored as JSON in signal_metadata or z_score_tier
import json
metadata = json.dumps({
    'z_short': round(z_short, 3),
    'z_mid':   round(z_mid, 3),
    'z_long':  round(z_long, 3),
})
```

### Constants

Add to `hermes_constants.py`:
```python
MTP_ZSCORE_ENABLED       = True    # master kill-switch
MTP_ZSCORE_PLUS_ENABLED  = True    # LONG
MTP_ZSCORE_MINUS_ENABLED = True     # SHORT

# Lookback periods
MTP_ZSCORE_LB_SHORT      = 50      # fast period
MTP_ZSCORE_LB_MID        = 100      # medium period
MTP_ZSCORE_LB_LONG       = 150     # structural period

# Per-period Z-Score bounds (MIN = floor, MAX = ceiling)
# If current |z| on any period EXCEEDS its Z_MAX → reject that period (too extended)
# If current |z| on any period is BELOW its Z_MIN → reject that period (not meaningful)

# Short period (50-bar)
Z_SHORT_Z_MIN            = 0.5
Z_SHORT_Z_MAX            = 2.0

# Medium period (100-bar)
Z_MID_Z_MIN             = 0.5
Z_MID_Z_MAX             = 2.5

# Long period (150-bar)
Z_LONG_Z_MIN            = 0.5
Z_LONG_Z_MAX            = 3.0

# Signal-level params
MTP_ZSCORE_MIN_AGREE     = 3  # 3/3 ALL periods must agree — stricter than 2/3
MTP_ZSCORE_BASE_CONF     = 80  # base confidence (all 3/3 = fires, so no tiered bonus)
MTP_ZSCORE_CONF_BONUS   = 5   # reserved for potential 2/3 vs 3/3 tiering in future
MTP_ZSCORE_COOLDOWN_BARS = 20  # cooldown in bars (1m = 20 min) — lives in hermes_constants
```

Note: No divergence params needed — anti-momentum logic doesn't belong in a trend-following signal.

---

## Step-by-Step Implementation

### Step 1 — Add constants to `hermes_constants.py`
Add the block above. Ask T before changing existing zscore_pump constants.

### Step 2 — Create `scripts/signals/mtp_zscore.py`
```
signals/
  mtp_zscore.py   # ~350-400 lines, following zscore_pump.py structure
```

Structure mirroring zscore_pump (minus divergence gate):
- `compute_zscore(values)` — identical to zscore_pump
- `_get_1m_prices(token, lookback)` — identical, reads from signals_hermes.db price_history
- `detect_mtp_zscore(token, prices)` — multi-period detection, per-period min/max bounds check
- `scan_mtp_zscore_signals(prices_dict)` — scanner with all guards (blacklist, open-positions, cooldown, price-age)
- `if __name__ == '__main__':` — CLI entry, dry run support
- `_log()` helper → writes to signals.log + stdout
- **`DRY_RUN = '--dry' in sys.argv`** — module level (line ~79 of zscore_pump.py), NOT inside the scanner function. Read by the `if __name__ == '__main__':` block when deciding whether to log or actually execute.

### Step 3 — Register in `signals/__init__.py`
```python
from signals.mtp_zscore import scan_mtp_zscore_signals as _mtp_zscore_run

{'name': 'mtp_zscore', 'enabled': 'MTP_ZSCORE_ENABLED', 'run': _mtp_zscore_run},
```
And add import: `MTP_ZSCORE_ENABLED, MTP_ZSCORE_PLUS_ENABLED, MTP_ZSCORE_MINUS_ENABLED`

Also add to `name_to_module` dict **inside `run_all_signals()`** (it is a local dict at ~line 305, not module-level):
```python
'name_to_module': {
    # ... existing entries ...
    'mtp_zscore': 'scan_mtp_zscore_signals',
}

### Step 4 — Add to `signal_compactor.py` SOURCE_WEIGHTS
Under existing zscore_momentum entries (~line 219):
```python
('mtp_zscore_long',   'mtp-zscore+'): 1.25,   # TBD — start conservative
('mtp_zscore_short',  'mtp-zscore-'): 1.25,
```
Note: start at 1.25 (same as zscore_momentum) but can tune up to 1.5 after live validation.

### Step 5 — Optional: divergence sub-signal weights
Similar to how zscore_pump has its own source entries in compactor for fine-grained control.

---

## Files To Change

| File | Change |
|------|--------|
| `scripts/hermes_constants.py` | Add MTP_ZSCORE_* constant block (~15 lines) |
| `scripts/signals/mtp_zscore.py` | **NEW** — ~300-350 lines |
| `scripts/signals/__init__.py` | Import + register + add to name_to_module dict |
| `scripts/signal_compactor.py` | Add SOURCE_WEIGHTS entries for mtp-zscore |

---

## Files To Create

| File | Purpose |
|------|---------|
| `scripts/signals/mtp_zscore.py` | Detection engine, scanner, CLI entry |

---

## Backlog Questions (answered)

1. ~~Threshold~~ — Not needed since we use per-period Z_MIN/Z_MAX (not a single threshold)
2. ~~Cooldown~~ — 20 bars in hermes_constants (MTP_ZSCORE_COOLDOWN_BARS) — answered above
3. ~~Composite z-score~~ — average of agreeing periods — answered
4. ~~Per-period threshold~~ — per-period Z_MIN/Z_MAX bounds — answered
5. ~~Direction disagreement~~ — ALL 3/3 must agree (3/3 = fire, 2/3 or 1/3 = no signal) — answered
6. ~~Divergence gate~~ — NO divergence gate (trend-following, not mean-reversion) — answered
7. ~~Combined with zscore_pump~~ — both fire as separate sources — answered
8. ~~Confidence scoring~~ — base=80, bonus=5 per additional agreeing period — answered

**Still open:**
- Entry confidence base=80, bonus=5 — T wants to tune after live data comes in
- Z_MAX/Z_MIN starting values — T tunes from live data (0.5-3.0 range shown is initial)

---

## Verification Steps

```bash
# 1. Check DB schema
sqlite3 /root/.hermes/data/signals_hermes_runtime.db ".schema signals"

# 2. Run signal in dry mode
cd /root/.hermes/scripts
python3 signals/mtp_zscore.py --dry

# 3. Verify signals written
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT token, direction, signal_type, confidence, source, z_score, created_at \
   FROM signals WHERE signal_type LIKE 'mtp_zscore%' ORDER BY created_at DESC LIMIT 5;"

# 4. Check hot-set appears
cat /var/www/hermes/data/hotset.json | python3 -m json.tool | grep mtp

# 5. Verify no HL API calls
grep -rn "http_post\|requests\." signals/mtp_zscore.py
```

---

## Risks / Tradeoffs

- **Fewer signals**: requiring all 3/3 periods to agree is stricter than 2/3 — mtp-zscore will fire less often than zscore_pump. This is by design (quality over quantity).
- **Additional DB reads**: mtp_zscore fetches max(150)+50 = 200 bars per token. zscore_pump only fetches 152. Acceptable overhead.
- **Short period (50-bar) sensitivity**: 50-bar z-score is noise-prone on low-liquidity tokens. The Z_SHORT_Z_MAX bound at 2.0 helps filter this, but T should watch for false triggers on thin tokens.
- **Staleness check** (120s direct check vs 10min scanner-level): mtp_zscore uses the 120s direct check on price_history timestamps. The scanner-level `price_age_minutes() > 10` guard in `scan_mtp_zscore_signals()` is a separate secondary guard. Both apply — the 120s is per-token inside detect, the 10min is at scanner level.

---

## Review Corrections Applied (ai-engineer round 2)

| # | Severity | Finding | Fix Applied |
|---|----------|---------|-------------|
| 1 | MUST | DRY_RUN must be module-level, not inside scanner | ✅ Plan now says "module level, NOT inside the scanner function" |
| 2 | MUST | name_to_module is local inside `run_all_signals()` | ✅ Plan now says "inside `run_all_signals()`" and shows full dict block |
| 3 | MUST | `agree_count` always equals 3 at fire (redundant) | ✅ Added comment "always 3 at fire, future-proofs for 2/3 mode" |
| 4 | MUST | `value` param in add_signal() not specified | ✅ Added: "use z_score average, same as stored z_score REAL column" |
| 5 | SHOULD | `import json` not mentioned as required | ✅ Added explicit note that `import json` must be added |
| 6 | SHOULD | Two staleness check layers (120s vs 10min) unclear | ✅ Risks section now clarifies both apply, roles differ |
| 7-9 | SHOULD | Minor clarifications | ✅ Incorporated into plan |
| 10-23 | CONFIRMED OK | All verified against actual code | ✅ No changes needed |
