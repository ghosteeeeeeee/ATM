# Anti-Patterns Observed in Hermes Hot-Set

## Accel-300+ / RS Conflicts

- All tokens in hot-set with `accel-300+, rs-sXX` — both signals fire in neutral market, self-canceling at RS level (RS Model B should fix this)
- All survival_round=1 — no tokens survived 2+ cycles, market too volatile for RS signals

## Z-Score / Regime Issues

- Z-score all 0.000 — no regime directionality in recent price action
- Speed percentile varies (17%-99%) but doesn't dominate over base confidence in current hot-set

## Overextended Tokens Still Entering

- RSI=98.2 on ONDO → would be blocked by overextended filter even though base conf=81.7%
- Tokens with extreme overextension values still passing base filters

## R² Flats (Low Confidence Regime)

- AVNT, ATOM, AVAX, EIGEN have R² 1-5% — price action essentially flat
- Regime is noise for these tokens — 1m LR produces whipsaw assignments
- Tokens that showed NEUTRAL on 5m slope show directional bias on 1m LR

## ZK / 2Z Accel-300+ Single Source Pattern

- ZK and 2Z consistently show `accel-300+` alone — no comma = single source
- These fail the confluence gate and stay PENDING
- No multi-source combo available for these tokens currently
- The signal fires but can't enter hot-set without a co-signal