# Additional trigger logs (offloaded from SKILL.md to stay under 100K)

## Resolved signal debugging triggers

- "phase_accel fires every cycle — no cooldown"
  - Fix: added cooldown check in signal_gen.py phase_accel block

- "accel-300 fires on brief EMA dip then reverses — ME/UNI/CHIP should have been LONG"
  - Fix: adjusted accel_300_signals.py entry conditions

- "signal fires while guardian closing same token"
  - Fix: guardian closing marker not blocking signal — signal_schema.py add_signal now checks guardian_closing flag

- "zscore-pump+ combo loses always"
  - Fix: zscore-pump threshold/lookback tuning in zscore_momentum.py

- "z=None in trade records despite zscore-pump in sources"
  - Fix: zscore-pump was writing z_score to source but not to trade record z field

- "phase_accel not appearing in hot-set"
  - Fix: phase_accel signal was not passing hot-set filtering — added to signal_compactor acceptance

- "LAYER-type move not detected"
  - Fix: pattern_scanner.py LAYER detection logic was missing key candle sequence check