# AXS zscore-pump lookback=150 too slow — 2026-05-18

## The Problem

zscore-pump configured at lookback=150 (hermes_constants: `ZSCORE_PUMP_LOOKBACK=150`, `ZSCORE_PUMP_THRESHOLD=2.2`).
150-bar mean is slow to update. When momentum fires, z-score stays elevated for ~45 bars after the initial spike.
Signal fires near the peak, then takes ~45 minutes to decay below 2.2 — by which point the move is often over.

## AXS 8h Case Study

Price range: $1.121–$1.161 (3.6% total range). 765 one-minute bars.

### Key events:

**Entry signal at 17:08-17:10 UTC**
- z150 first crossed 2.2 at ~17:08 (z=+2.50)
- Guardian picked it up at ~17:31 entry
- At entry: z150=+1.97 (below 2.2, already fading), z30=+2.26 (above 2.2, would have fired)

**Spike artifact at 11:43-11:48 UTC**
- Single-bar jump from $1.128 to $1.141 (+1.1%)
- z150 hit +10.15 — mathematically correct, economically meaningless (one-bar backfill artifact)
- No real sustained momentum followed

**Deep negative z at 14:17-14:22 UTC**
- Price falling 1.1388→1.1328 (-0.5%)
- z150 dropped to -3.37, z30 dropped to -4.16
- No SHORT fired — price stabilized immediately; z was deep negative because 150-bar mean was stuck at higher level from morning

## Z-score at entry time (17:31) by lookback

| Lookback | Z-Score | Fires? (thresh 2.2) |
|----------|---------|---------------------|
| 20 | +1.88 | No |
| 30 | +2.26 | **Yes** |
| 50 | +1.77 | No |
| 75 | +1.72 | No |
| 100 | +1.78 | No |
| 150 | +1.97 | No |

## Core structural issue

- z150 mean covers ~2.5 hours of price history
- Regime shift (price jumps +1.4%) takes ~60-90 bars for mean to catch up
- Signal fires at the top, not the bottom
- Decay tail: ~45 bars (~45 min) from +2.5 back below 2.2

## Approaches (no changes made — observation only)

1. **Shorter lookback (e.g. 30-50)** — catches moves earlier, more false signals
2. **Dual-lookback**: initial detection at 30, confirmation at 150 (confluence gate)
3. **Adaptive threshold**: lower threshold for shorter lookbacks (z30 @ 1.8 instead of 2.2)

## Data source

- `signals_hermes.db` → `price_history` table — correct source, confirmed fresher than `candles.db` by ~40s for BTC
- `signals_hermes.db` has 12.2M rows, 191 tokens
- No bug in data routing — zscore_pump.py already reads from `price_history`