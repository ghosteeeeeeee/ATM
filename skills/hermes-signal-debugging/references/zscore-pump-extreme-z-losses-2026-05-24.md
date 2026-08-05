# zscore-pump — Extreme Z-Score Losses (2026-05-24)

## Empirical Finding: Last 24h (83 trades, brain DB)

**Core observation:** zscore-pump signals at extreme z-scores (|z| > 4.0) are strongly associated with SL-trigger losses. They fire at blow-off exhaustion, not sustainable momentum.

### Loser Profile — Extreme Z

| Token | Direction | z_score | pnl_pct | Dur_min | Exit |
|-------|-----------|---------|---------|---------|------|
| IP | SHORT | -6.712 | -1.41% | 179 | atr_sl_hit |
| VINE | SHORT | -5.619 | large loss | <1 | atr_sl_hit |
| BLUR | SHORT | -6.161 | -large loss | <1 | atr_sl_hit |
| PURR | SHORT | -4.876 | large loss | <1 | atr_sl_hit |
| MON | SHORT | -4.601 | large loss | <1 | atr_sl_hit |
| GRIFFAIN | SHORT | -3.6 (signal) | -0.49% | ~0 | atr_sl_hit |
| ME | LONG | +3.995 (signal) | +4.27% | 49 | **atr_sl_hit** (big win) |

### Winner Profile — Elevated but not Extreme

| Token | Direction | z_score | pnl_pct | Dur_min | Exit |
|-------|-----------|---------|---------|---------|------|
| SKY | LONG | +5.715 | +1.49% | 448 | profit-monster |
| TIA | SHORT | -2.53 | +1.43% | 41 | profit-monster |
| XRP | LONG | +2.5 | +1.22% | 48 | profit-monster |
| BLUR | SHORT | -2.88 | +1.69% | 3 | profit-monster |
| MON | LONG | +2.9 | +1.51% | 13 | profit-monster |

### Key Distinction

- **Winners:** z between ~2.0–3.0 (sustainable directional momentum)
- **Losers:** z > 4.0 (blow-off exhaustion, reversal imminent)

The divergence filter kicks in at `ZSCORE_PUMP_DIVERGENCE_EXTREME_Z = 3.0` — but this only REJECTS the signal, it doesn't prevent entries at z=3.5 or 4.0 that pass the filter. At z=4+, even a passing divergence check is a trap entry.

### Constants Currently in hermes_constants.py

```python
ZSCORE_PUMP_LOOKBACK               = 70     # lookback bars
ZSCORE_PUMP_THRESHOLD              = 2.0    # fire when |z| > 2.0
ZSCORE_PUMP_DIVERGENCE_ENABLED     = True
ZSCORE_PUMP_DIVERGENCE_LOOKBACK    = 40     # short-term spot check
ZSCORE_PUMP_DIVERGENCE_EXTREME_Z   = 3.0   # reject if z spikes then crashes
ZSCORE_PUMP_DIVERGENCE_VEL_THD     = -0.5   # negative velocity threshold
ZSCORE_PUMP_DIVERGENCE_BARS        = 2       # consecutive bars of decline
```

**Missing:** A hard cap `ZSCORE_PUMP_MAX_Z` — there's no maximum z beyond which the signal won't fire. z=6.7 SHORT fires the same as z=2.1 SHORT, but they're completely different market states.

## Proposed Fix: ZSCORE_PUMP_MAX_Z Cap

Add to `hermes_constants.py`:
```python
ZSCORE_PUMP_MAX_Z            = 4.0   # reject entries at extreme z (blow-off territory)
ZSCORE_PUMP_SHORT_MAX_Z      = 3.5   # stricter for SHORT — crypto down-moves are violent
```

In `signals/zscore_pump.py` `detect_zscore_pump()`:
```python
# After z calculation (line ~250):
if direction == 'LONG' and abs(z) > ZSCORE_PUMP_MAX_Z:
    _log(f"  REJECT {token}: z={z:+.3f} exceeds MAX_Z={ZSCORE_PUMP_MAX_Z}")
    return None
if direction == 'SHORT' and abs(z) > ZSCORE_PUMP_SHORT_MAX_Z:
    _log(f"  REJECT {token}: z={z:+.3f} exceeds SHORT_MAX_Z={ZSCORE_PUMP_SHORT_MAX_Z}")
    return None
```

**Why separate LONG/SHORT:** Crypto down-moves are faster and sharper — a z=-3.5 SHORT is already at blow-off bottom territory and prone to instant reversal. LONG blow-offs take longer to reverse.

## Alternative: Strengthen Divergence Filter

If MAX_Z feels too blunt, alternatively:
- Lower `ZSCORE_PUMP_DIVERGENCE_EXTREME_Z` from 3.0 to 2.5 — catches earlier
- At `|z| > 4.0`, require `neg_vel_bars >= 1` (not just 2) — immediate rejection on any decline

## Signals/DB Evidence

Check zscore_pump signals in signals_hermes_runtime.db:
```sql
SELECT token, direction, confidence, value, z_score, created_at
FROM signals
WHERE signal_type IN ('zscore_pump_long', 'zscore_pump_short')
  AND created_at >= datetime('now', '-24 hours')
  AND abs(z_score) > 4.0
ORDER BY abs(z_score) DESC;
```

Most recent z-scores in DB (2026-05-23):
- KAITO LONG: z=7.202 (extreme!)
- LTC LONG: z=7.051
- UNI LONG: z=6.314
- LINK LONG: z=6.198

These fired but may not have been executed (confluence gate, RS requirement).

## Related Files

- `references/zscore-pump-migration-2026-05-16.md` — migration details
- `references/zscore-pump-counter-trend-2026-05-17.md` — counter-trend logic
- `references/zscore-combo-null-guardian-2026-05-21.md` — zscore+RS combo analysis
- `references/same-timeframe-confluence-illusion-2026-05-21.md` — same-source noise amplification