## CEO Report — 2026-08-09 (07:50 UTC run)

### Diagnosis (verified DB)
- 24h: **52T +$0.29 (50.0% WR)** — net positive, balanced
- 7d: 393T **-$5.99** (legacy pre-fix bleeding still in window)
- 8/9 day so far: **25T +$0.33 (60% WR)** — recovery intact, +$0.05 over yesterday's 8/8 close
- Open: 5 trades (clean, no bloat); Pipeline + price-collector timers active
- Phantom trades (0% PnL): **0 in 24h** — Aug 9 health concern resolved
- Direction split 24h: LONG 40T +$0.20 (47.5%), SHORT 12T +$0.09 (58.3%) — **SHORT bleeding STOPPED**

### Star & Bleeders
- **Star:** `bb_bounce+,range_finder+` LONG 24T +$0.41 / 54.2% WR (24h), 33T +$0.79 / 63.6% WR (7d, all-time) — sole profit driver
- **SHORT star:** `bb-bounce-short,hzscore-` 8T +$0.24 / 75% WR (24h) — Aug 9 SHORT fix verified
- 24h worst (current firing): `bb_bounce+,hzscore+` LONG 3T -$0.11 (33.3% WR) — small sample, already on signal_reporter watch list
- 7d worst (all DISABLED, legacy aging out): `zscore-rising-` SHORT 44T -$1.37, `vel-hermes-` SHORT 58T -$1.14, `zscore-rising+` LONG 26T -$1.01, `pattern_wolf_wave_bear` SHORT 9T -$0.79

### Fix Applied
**NONE — all Aug 9-10 fixes verified working.**

### Verification
- `MA_100_CROSS_MINUS_ENABLED=False` (Aug 10 05:30): SHORT regime filter added, signal no longer fires against LONG_BIAS trend
- `MA_100_CROSS_PLUS_ENABLED=False` (Aug 10 05:30): killed 20% WR combo, no impact on star
- Compactor `is_component_disabled()` fix: prevents re-insertion of disabled components
- ATR SL 1.2% widening: holding
- SHORT bleeding fully stopped: 12T 58.3% WR with positive PnL (vs 7T 28.6% WR pre-fix)

### Watch
- `bb_bounce+,range_finder+` LONG WR trend over 3 days: 8/7=83.3% → 8/8=64.3% → 8/9=53.8%. Decay pattern but still profitable. With 33T 63.6% WR all-time, statistically still positive edge. Will trigger action if WR drops below 50% over rolling 20+ trades.
- `bb_bounce+,hzscore+` LONG: 3T 33% WR. Insufficient sample (3 trades). Already on signal_reporter watch list. Re-evaluate at 10+ trades.
- `zscore-rising-`, `vel-hermes-`, `pattern_*`, `accel-300+`, `decider` 7d bleeding: all DISABLED, aging out of 7d window over next 4-5 days. 7d number will improve mechanically.

### Expected Trajectory
- 7d PnL will mechanically improve as disabled-signal legacy trades age out (~$5-6 of locked-in losses)
- 24h trend: 8/7 +$0.40 → 8/8 +$0.05 → 8/9 +$0.33. System stable and recovering.
- No intervention needed; fixes are landing.
