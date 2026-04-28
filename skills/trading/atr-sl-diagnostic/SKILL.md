---
name: atr-sl-diagnostic
description: Diagnose why ATR-based SL/TP is at breakeven or not catching moves as expected
---
# ATR SL/TP Diagnostic Skill

## When to Use
When a trade's ATR-based SL is at breakeven or behaving unexpectedly — SL not catching a pop, SL too wide/tight, TP never hit.

## Diagnostic Workflow

### Step 1 — Read the trade
```bash
python3 -c "
import json
with open('/var/www/hermes/data/trades.json') as f:
    trades = json.load(f)
for t in trades['open']:
    if t['coin'] == 'ETH':
        print(json.dumps(t, indent=2))
"
```
Check: entry, current price, sl, tp, direction, leverage.

### Step 2 — Check pipeline ATR logs
```bash
tail -100 /root/.hermes/logs/pipeline.log | grep -E "\[ATR\]|ETH"
```
Look for: `k=X ATR=X (X.XX%) → SL=X TP=X [ref=X]`

### Step 3a — Understand the SL floor problem
```python
# For low-vol tokens (ETH ~0.17% ATR), the MIN_SL_PCT_TRAILING floor
# (ATR_SL_MIN_ACCEL = 0.20%) overrides the ATR-based sl_pct (0.17%)
atr = 3.97       # ETH ATR(14)
entry = 2314.0
atr_pct = atr / entry  # 0.00172
sl_pct = atr_pct        # k=1.0
MIN_SL = 0.002          # ATR_SL_MIN_ACCEL
effective_sl_pct = max(sl_pct, MIN_SL)  # 0.20% wins
```
Key insight: `max(atr_pct, MIN_SL_PCT)` — on low-vol tokens where `atr_pct < MIN_SL_PCT`, the floor wins and the SL sits far from current price.

### Step 3b — SL at wrong price level (immediate exit at open)
If a trade closes in seconds with `atr_sl_hit` AND the SL appears to be on the WRONG SIDE of current price:
- For SHORT at entry ~1.41: SL at 1.003 is ABOVE current (should be below entry for SHORT)
- This means `new_sl = ref_price * (1 - effective_sl_pct)` used a wrong `ref_price`

**Diagnostic:**
```python
# From the DB trade record:
entry = 1.4165  # SHORT
sl = 1.00305    # WRONG — should be BELOW 1.4165 for SHORT
# The SL (1.003) is ABOVE entry (1.4165) — price would need to RISE 29% to hit SL
# Yet the trade closed in 3s with atr_sl_hit

# For SHORT: correct SL must be < entry_px
# SL = entry * (1 - effective_sl_pct)  → for SHORT
# If SL > entry → ref_price was a STALE PEAK (highest_price initialized wrong on creation)
```

**Root cause candidates:**
1. `highest_price` / `lowest_price` peak fields initialized to wrong value at trade creation (not entry price)
2. `_persist_atr_levels()` wrote SL using a stale `highest_price` as reference instead of entry price
3. For SHORT: code did `entry * (1 + sl_pct)` instead of `entry * (1 - sl_pct)`

**Check:** Look at `highest_price` and `lowest_price` in the trade record from PostgreSQL:
```python
# Trade ID 7817 (XRP SHORT, closed in 3s):
# highest_price=1.41655, lowest_price=1.0
# entry=1.4165, sl=1.003 — wrong reference used
```

**Files to check:**
- `position_manager.py`: `_collect_atr_updates()` — how `ref_price` (peak) is selected for SHORT vs LONG
- `position_manager.py`: `_persist_atr_levels()` — how SL/TP are written to DB on new trade
- `brain.py`: `add_trade()` — how `highest_price`/`lowest_price` are initialized on creation

### Step 4 — Check ATR cache
```bash
python3 -c "
import json, time
with open('/root/.hermes/data/atr_cache.json') as f:
    data = json.load(f)
eth = data.get('ETH', {})
print(f'ATR: {eth.get(\"atr\")}, age: {time.time() - eth.get(\"ts\",0):.1f}s')
"
```

### Step 5 — Trace ATR computation
`position_manager.py` `_collect_atr_updates()` (lines ~1550-1620):
- `atr_pct = atr / _entry`
- `k = _atr_sl_k_scaled(...)` — phase-based k multiplier
- `sl_pct = k * atr_pct`
- `effective_sl_pct = max(sl_pct, MIN_SL_PCT_TRAILING)` — floor applied here
- For LONG in profit: `ref_price = highest_price` (peak)
- `new_sl = round(ref_price * (1 - effective_sl_pct), 8)`

### Step 6 — Phase-based k
Phase thresholds in `signal_gen.py`:
- `PHASE_ACCELERATING` (percentile ≥ 75) → k = base_k × 0.15–0.25
- `PHASE_EXHAUSTION` (percentile ≥ 88) → k = base_k × 0.10–0.25
- `PHASE_EXTREME` (percentile ≥ 95) → k = base_k × 0.05–0.10

Phase multipliers only matter when `atr_pct > MIN_SL_PCT`.

## Key Constants (hermes_constants.py)
```
ATR_SL_MIN_ACCEL   = 0.002   # 0.20% — floor for all trailing SL
ATR_TP_MIN_ACCEL   = 0.005   # 0.50% — floor for trailing TP
ATR_SL_MIN         = 0.005   # 0.50% — standard floor
ATR_TP_K_MULT      = 1.25   # TP = k × 1.25 × ATR
```

## Related Skills
- `atr-trailing-sl-peak-initialization` — covers `highest_price`/`lowest_price` initialization bugs on trade creation; closely related to this failure mode
- `atr-trailing-sl-in-profit` — ATR trailing SL in-profit fast-lock pattern

## Relevant Files
- `/root/.hermes/scripts/position_manager.py` — `_collect_atr_updates()` ~1550–1620
- `/root/.hermes/scripts/hermes_constants.py` — ATR constants
- `/root/.hermes/scripts/signal_gen.py` — phase definitions (BUILDING=60, ACCEL=75, EXH=88, EXTREME=95)
- `/root/.hermes/data/atr_cache.json` — live ATR values
- `/var/www/hermes/data/trades.json` — open trades
