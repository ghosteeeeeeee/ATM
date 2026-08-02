# Pump Finder Signal — Catch Pumps Before They Peak

## Goal
Add a fast pump-detection signal to the per-minute pipeline that catches token pumps early, enabling better entry timing rather than entering after the pump has already reversed.

## Context / Problem

**ZETA case:**
- Pump: 00:00→00:04 | +5.78% in 4 minutes (0.05470 → 0.05786)
- Signals fired: hzscore-, pct-hermes-, vel-hermes- = SHORT
- System shorted at 00:56 @ 0.05684 — AFTER the pump peaked and reversed
- Result: -$0.65 loss because we entered at the wrong time

**The signals were directionally correct** (price was ultimately lower), but **timing was wrong** — we entered after the pump exhausted itself.

**Core issue:** The system detects the direction but not the momentum/acceleration of the move. A 5.78% pump in 4 minutes is not the same as a gradual drift. We need to:
1. Detect pumps as they form
2. Use pump timing to improve entry (enter on pullback after initial pump, not 56 minutes later)
3. Or optionally trade WITH the pump momentum briefly before reversing

## Proposed Approach

### Pump Finder Signal (`pump_finder`)

A new signal source that runs every pipeline minute and detects rapid price pumps.

**Detection Logic:**
```
For each traded token:
  1. Get 5m candle price series (last 3-5 candles)
  2. Calculate:
     - price_change_pct = (current - candle_1) / candle_1 * 100
     - velocity = price_change_pct / time_delta_minutes
     - acceleration = velocity_change_between_candles
  3. Pump threshold: price_change_pct > 2% in < 10 minutes
  4. If pump detected → emit `pump+` (for long) or `pump-` (for short pump from high)
```

**Pump Types:**
- **Pump+ (Bull pump):** Price surging up — could be a buy signal OR could mean "don't short yet, wait for pullback"
- **Pump- (Bear pump / dump):** Price falling fast — could confirm short entry

**Integration with existing signals:**
- If we have a SHORT signal (hzscore-, pct-hermes-) AND a pump- detected → strong confirmation to SHORT now
- If we have a SHORT signal but pump+ detected → WAIT, don't enter yet, the pump might reverse us
- If pump+ without any direction signal → could be a signal to go LONG briefly

**Entry Timing Use:**
- Pump detected at T0
- System waits for first pullback (price drops 30-50% of pump gain)
- Enter at pullback confirmation → better entry than waiting 56 minutes

## Step-by-Step Plan

### Step 1: Create pump detection logic
**File:** `/root/.hermes/scripts/pump_finder.py` (new file)

```python
def detect_pumps(token: str) -> dict:
    """
    Returns:
      {
        'token': 'ZETA',
        'pump_detected': True/False,
        'pump_direction': 'up' or 'down' or None,
        'pump_pct': 3.5,  # percent move
        'pump_duration_min': 4,  # how long the pump lasted
        'velocity': 0.87,  # % per minute
        'entry_recommendation': 'now' or 'wait_pullback' or 'skip'
      }
    """
```

**Thresholds (tunable):**
- MIN_PUMP_PCT = 2.0% (anything less is just noise)
- MIN_PUMP_SPEED = 0.3% per minute
- PUMP_WINDOW = 3 candles (15 minutes of 5m candles)

### Step 2: Add pump_finder to signal_gen
**File:** `/root/.hermes/scripts/signal_gen.py` (or wherever signals are generated)

Call `detect_pumps()` for all tokens in the hot-set every minute.
Add pump signals to the signals DB with source `pump+` or `pump-`.

### Step 3: Modify signal scoring to use pump info
**File:** `/root/.hermes/scripts/signal_compactor.py`

When scoring signals:
- If signal direction agrees with pump direction → BOOST confidence
- If signal direction disagrees with pump direction → REDUCE confidence or WAIT
- Pump signals alone (single source) with high velocity (e.g., >1% per min) → could trigger fast entry

### Step 4: Add to pipeline logging
**File:** `/root/.hermes/logs/pipeline.log` (already logs, just ensure pump signals appear)

```
[2026-04-19 00:03] [PUMP] ZETA pump+ detected: +3.2% in 3min (velocity=1.07%/min)
```

### Step 5: Backtest pump finder
- Run against historical data for ZETA and other pumps
- Tune thresholds (MIN_PUMP_PCT, PUMP_WINDOW)
- Verify pump signals correlate with actual pump starts

## Files to Change

1. **NEW:** `/root/.hermes/scripts/pump_finder.py` — pump detection logic
2. **MODIFY:** signal_gen.py — integrate pump detection into signal generation
3. **MODIFY:** signal_compactor.py — use pump signals in scoring
4. **MODIFY:** paths.py — add PUMP_SIGNAL_SOURCE = 'pump+' and 'pump-'

## Validation

1. Run pump_finder.py standalone on recent data → should detect ZETA pump at ~00:01-00:02
2. Check pipeline logs after integration → pump signals appear within 1 minute of pump start
3. Compare entries: with pump finder, ZETA should have entered ~00:05 instead of 00:56

## Risks & Tradeoffs

- **Pump whipsaws:** Fast pumps can reverse quickly — need good exit logic
- **Threshold tuning:** Too sensitive = false positives, too strict = miss pumps
- **Data latency:** Need 5m candles updated in real-time — check candle cache freshness
- **Already have vel-hermes-:** Velocity signal might overlap with pump detection — avoid redundancy

## Open Questions

1. Should pump signals trigger immediate entry or act as a filter for existing signals?
2. Do we trade WITH the pump (momentum) or wait for reversal (counter-trend)?
3. What's the optimal pump threshold — 2%? 3%? 5%?
4. Should pump finder look at individual exchange (Binance) vs aggregated price data?

## Implementation Order

1. Build pump_finder.py as standalone module with tests
2. Add to signal_gen (no execution yet, just logging)
3. Tune thresholds for 1-2 weeks in paper mode
4. If working, integrate into signal_compactor as filter/boost
