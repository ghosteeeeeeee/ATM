# Post-Change: Position Manager Fix — 2026-08-29

## What was done

Fixed critical bug: position_manager.py was the primary trade close path (atr_sl_hit = 2,390 trades = 63% of all closes) but only called HebbianEngine, not CorrelationEngine. 342 trades were missed since Aug 23.

## Files changed

- scripts/position_manager.py: added CorrelationEngine().ingest_trade() call

## Results

- 355 missed trades caught up via bulk ingest
- 573 new chains added (3,620 → 3,940 total)
- Correlation engine now gets live data from every trade close
