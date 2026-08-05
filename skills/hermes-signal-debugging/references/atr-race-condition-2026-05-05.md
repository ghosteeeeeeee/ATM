# ATR Race Condition — Fresh Entries Log SL=$0.0000 (2026-05-05)

## Symptom
POPCAT LONG and GALA LONG logged with `SL=$0.0000 TP=$0.0000` at entry (06:04:05):
```
[2026-05-05 06:04:05]   2026-05-05 06:03:46 EXEC: POPCAT LONG @ $0.061059 conf=95% SL=$0.0000 TP=$0.0000 [hhh-long4,rs-s896] [SL=0.5% trail=1.0%/1.0%][spd=4%]
[2026-05-05 06:04:05]   2026-05-05 06:03:55 EXEC: GALA LONG @ $0.003170 conf=96% SL=$0.0000 TP=$0.0000 [accel-300+,rs-s852] [SL=0.5% trail=1.0%/1.0%][spd=80%]
```

Guardian eventually sets stops 3 seconds later (06:04:08):
```
[2026-05-05 06:04:08]   [ATR] POPCAT: k=0.500 ATR=0.0004 (0.61%) → SL=0.060894 TP=0.061445 [ref=0.061079]
[2026-05-05 06:04:08]   [ATR] GALA: k=0.500 ATR=0.0000 (0.43%) → SL=0.003162 TP=0.003188 [ref=0.003169]
```

## Root Cause
Pipeline runs: decider_run → position_manager in sequence.

decider_run.py logs the trade immediately when HL confirms fill:
```python
# decider_run.py line ~1669 — logs before ATR is calculated
log(f'EXEC: {token} {direction} @ ${price:.6f} conf={confidence:.0f}% '
    f'SL=${sl:.4f} TP=${tp:.4f} ...')
# sl and tp are 0 at this point — ATR not yet calculated
```

position_manager runs AFTER decider, calculates ATR, then writes updated SL/TP:
```
[06:04:08] Running position_manager...
[06:04:08]   [ATR] POPCAT: k=0.500 ATR=0.0004 (0.61%) → SL=0.060894 TP=0.061445
```

The ~3 second gap means fresh entries have no ATR-based stops in the pipeline log.

## Effect
- The guardian eventually manages these positions correctly
- The pipeline log shows $0.0000 stops which could be confusing during debugging
- For volatile alts, price could move 0.5-1% in that 3-second window before stops are set
- This is a LOGGING issue only — the guardian sets real stops

## Fix Options
1. **Preferred**: Pre-calculate ATR in decider_run before the execute log line. ATR needs: current price (available), ATR value (requires candles.db query), and k_tp multiplier. This adds ~100ms but eliminates the race.

2. **Accept the gap**: Document as known limitation — the guardian sets stops within seconds, it's a logging artifact not a trading risk.

## Pipeline Order (current)
```
Running decider_run...
  EXEC: POPCAT LONG @ $0.061059 conf=95% SL=$0.0000 TP=$0.0000  ← ATR not set
  → ENTERED: POPCAT LONG (trade #8421)
Running position_manager...
  [ATR] POPCAT: k=0.500 ATR=0.0004 (0.61%) → SL=0.060894 TP=0.061445  ← ATR set here
```
