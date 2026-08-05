# OPP Penalty — Floor Raised 40% → 65% (2026-05-05)

## What Was Done

**Fix** (signal_compactor.py line 277):
```python
# BEFORE: penalty = max(0.40, 1.0 - (opp_source_count * 0.30))
# AFTER:  penalty = max(0.65, 1.0 - (opp_source_count * 0.30))
```

**Effect**:
| opp_parts | floor=40% | floor=65% | conf=88 × staleness=0.6 |
|-----------|-----------|-----------|--------------------------|
| 0 | 100% | 100% | 52.8 |
| 1 | 70% | 70% | 37.0 |
| 2 | 40% | 65% | 34.3 |
| 3+ | 40% | 65% | 34.3 |

## What the OPP Penalty Was Doing Right

PURR LONG (`hzscore-,pct-hermes+,rs-s77`) was score=0 with floor=40%. OPP penalty was doing the RIGHT thing:
- `hzscore-` in LONG: WR=35%, avg=+0.10% — below average
- `pct-hermes+` in LONG: WR=33%, avg=+0.18% — mediocre (was blocked then unblocked)
- `rs-s77`: 0 trades — too new to evaluate

The OPP penalty was correctly identifying this as a weak signal and suppressing it.

## What the OPP Penalty Was Doing Wrong

Signals with GOOD components (like XMR LONG: `hzscore-,rs-s146,rs-s147,rs-s492`) were also getting crushed by the 40% floor when OPP noise existed. Floor=65% gives legitimate signals room to survive.

## hzscore+/- Direction — No Flip Needed

hzscore direction logic (signal_gen.py lines 1748-1766):
- `bullish_tfs = count of TFs where z > 0` (price above mean)
- `bearish_tfs = count of TFs where z < 0` (price below mean)
- `local_dir = 'LONG' if bearish_tfs >= 2` (price below mean across MTF = bullish for LONG)

This is correct. The 35% WR for hzscore- LONGs is because the market is 105/106 NEUTRAL (ranging) — mean-reversion requires a trending market. In ranging markets, price at bottom keeps falling. Direction is right; market regime is wrong.

## XMR LONG — Reference Good Signal

XMR LONG (currently +1.98%, going according to plan):
- Source: `hzscore-,rs-s146,rs-s147,rs-s492`
- `rs-s492`: WR=50%, avg=+1.09% — solid support level
- `rs-s146`, `rs-s147`: stacked supports = structural validity
- No `pct-hermes+` drag — pure RS + hzscore- combo
- Confidence=99.0

## Diagnostic Query

```python
python3 -c "
import sqlite3
RUNTIME_DB = '/root/.hermes/data/signals_hermes_runtime.db'
conn = sqlite3.connect(RUNTIME_DB)
c = conn.cursor()
for tok in ['INJ','DYDX','NEAR','2Z','PEOPLE','ORDI','MORPHO','TRB','NIL']:
    for direction in ['LONG','SHORT']:
        opp_dir = 'SHORT' if direction == 'LONG' else 'LONG'
        c.execute('''
            SELECT source, confidence FROM signals
            WHERE token=? AND direction=? AND created_at > datetime(\"now\",\"-5 minutes\")
            AND confidence >= 60 ORDER BY created_at DESC
        ''', (tok, opp_dir))
        opp_rows = c.fetchall()
        opp_parts = sum(len([p for p in o[0].split(',') if p.strip()]) if o[0] else 0 for o in opp_rows)
        penalty = max(0.65, 1.0 - opp_parts * 0.30)
        print(f'{tok:8} {direction:5}: {len(opp_rows)} opp signals, opp_parts={opp_parts} → mult={penalty:.0%}')
conn.close()
"
```
