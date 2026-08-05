# Signal-ATR Mismatch — Winners Dying Too Early (2026-05-06)

## The Problem

`accel-300+,hzscore-` fires at **99% confidence**. The signal is correct. But:
- **Winners hold: 43 min avg** — EIGEN held 139 min → +6.65%, OP held 39 min → +4.02%
- **Losers hold: 21 min avg** — XMR -1.03% in 5.9m, BERA -0.20% in 6m, BLUR -0.45% in 8m

Losers get stopped out in 4-8 min before momentum develops. The ATR trailing stop activates too fast for this signal's natural rhythm.

## ATR Trailing Stop Behavior

All `accel-300+,hzscore-` trades:
- Exit reason: `profit-monster` OR `atr_sl_hit`
- Winners: EIGEN +6.65% (profit-monster, 139m), MON +4.06% (profit-monster, 18m), OP +4.02% (atr_sl_hit, 39m)
- Losers: ALL exit via `atr_sl_hit` in 4-90 min

The trailing stop cuts losers before they have a chance to recover. Some losers show almost zero adverse movement — they would have recovered if given more time.

## The Core Dilemma

**Widening the stop** = letting losers run longer (bad)
**Narrowing the stop** = cutting winners earlier (bad)
**Current behavior** = cuts both too early

This suggests the signal itself needs a **delayed trail activation** — don't arm the trailing stop until X minutes have passed. For `accel-300+,hzscore-`:
- First 15 min: no trailing stop, let the trade breathe
- After 15 min: activate trailing stop

## Audit Script

```python
import sys; sys.path.insert(0, '/root/.hermes/scripts')
import psycopg2
from _secrets import BRAIN_DB_DICT
conn = psycopg2.connect(**BRAIN_DB_DICT)
cur = conn.cursor()
def to_float(v): return float(v) if isinstance(v, type(v)) else (float(v) if v else 0.0)

cur.execute("""
  SELECT token, pnl_pct, direction, signal,
         EXTRACT(EPOCH FROM (close_time - open_time))/60 as dur_min,
         close_reason,
         entry_price, exit_price, stop_loss,
         highest_price, lowest_price
  FROM trades
  WHERE close_time IS NOT NULL AND pnl_pct IS NOT NULL
    AND signal = 'accel-300+,hzscore-'
  ORDER BY pnl_pct DESC
""")
for r in cur.fetchall():
    tok, pnl, d, sig, dur, creason = r[0], to_float(r[1]), r[2], r[3], to_float(r[4]), r[5]
    entry, exit_p, sl = to_float(r[6]), to_float(r[7]), to_float(r[8])
    hi, lo = to_float(r[9]), to_float(r[10])
    max_up = (hi - entry) / entry * 100 if entry > 0 else 0
    max_dn = (lo - entry) / entry * 100 if entry > 0 else 0
    outcome = "WIN" if pnl > 0 else "LOSS"
    print(f"{tok:<8} {pnl:>+7.2f}% {dur:>6.1f}m {outcome} {creason} maxup={max_up:+.2f}% maxdn={max_dn:+.2f}%")
```

## Related: April vs May Regime Divergence

Same signals perform radically differently across market regimes:

| Signal | Period | Direction | WR | Avg% |
|--------|--------|-----------|-----|------|
| `accel-300+` alone | Apr | LONG | 50% | +0.514% |
| `accel-300+` alone | May | LONG | 31.2% | +0.405% |
| `hzscore+,vel-hermes-` | Apr | SHORT | 30% | -0.305% |
| `hzscore+,vel-hermes-` | May | SHORT | 20% | -0.064% |
| `pct-hermes+` standalone | Apr | LONG | 50% | +1.015% |
| `pct-hermes+` standalone | May | LONG | 33% | +0.212% |

Signal quality varies by regime. Don't over-index on recent data.

## System P&L by Period

| Period | Direction | Trades | WR | Avg% | Total% |
|--------|-----------|--------|-----|------|--------|
| May | LONG | 425 | 36.7% | +0.282% | +119.82% |
| May | SHORT | 325 | 32.3% | +0.148% | +48.20% |
| Apr | LONG | 1036 | 32.9% | +0.164% | +169.79% |
| Apr | SHORT | 705 | 33.2% | +0.169% | +118.98% |

**May LONG is outperforming April** (+0.282% vs +0.164%). The signal quality IS there. The problem is execution (trailing stop) not generation.
