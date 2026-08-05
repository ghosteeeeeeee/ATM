# mtf-macd Signal — Extraction Reference

## Source Location

signal_gen.py lines 1373-1643, function `_run_mtf_macd_signals()`.

## Source Tag Collision (Critical)

**Both hmacd.py and mtf_macd.py write the same source tag: `hmacd-{+|-}`**

- hmacd.py: MACD histogram agreement across 15m + 1H (standalone, 262 lines)
- mtf_macd.py: z_1h threshold + histogram agreement + MTF alignment boost + cascade boost

They are NOT the same signal:
- hmacd.py: fires on 15m+1H histogram agreement alone
- mtf_macd.py: requires z_1h > 2.0 AND histogram agreement, plus boosts from compute_mtf_macd_alignment and cascade_entry_signal

But they produce the same source tag in `add_signal()`. After signal_compactor merges, hot-set sees a single `hmacd-` entry. Both scripts will fire but look like one signal.

**Workaround:** Use separate source tags if both are enabled (`mtf-macd-{+|-}` vs `hmacd-{+|-}`), or consolidate into one script.

## Signal Logic (mtf_macd.py)

```
z_1h > +2.0 AND h_15m < 0 AND h_1h < 0 → SHORT  (stretched up, expect down)
z_1h < -2.0 AND h_15m > 0 AND h_1h > 0 → LONG   (oversold, expect up)
```

Confidence = `min(75, 45 + (|z_1h| - 2.0) * 10)`, then:
- MTF alignment score ≥ 3 → +10 conf
- MTF alignment score ≥ 2 AND direction matches → +5 conf
- Cascade direction matches → +10 conf
- Cascade direction opposes → BLOCK

## Key Imports

```python
from signal_schema import (init_db, get_all_latest_prices, get_price_history,
                           price_age_minutes, add_signal, get_cooldown)
from hermes_constants import (HMACD_ENABLED, HMACD_PLUS_ENABLED, HMACD_MINUS_ENABLED,
                               SHORT_BLACKLIST, LONG_BLACKLIST)
from macd_rules import get_macd_params, compute_mtf_macd_alignment, cascade_entry_signal
```

## 1H Z-Score Access

```python
from signal_gen import get_tf_zscores
zscores = get_tf_zscores(token)
z_1h = zscores.get('1h', (None, None))[0]
```

## Per-Token MACD Params

```python
from macd_rules import get_macd_params
params = get_macd_params(token)  # {'fast': int, 'slow': int, 'signal': int}
fast, slow, sig = params['fast'], params['slow'], params['signal']
```

## Standalone Run

```bash
cd /root/.hermes/scripts
python3 signals/mtf_macd.py  # exits 0 when HMACD_ENABLED=False
```

## hermes_constants Flags

```python
HMACD_ENABLED       = False  # master kill-switch (disabled 2026-05-06)
HMACD_PLUS_ENABLED = True   # hmacd+ (LONG) enabled
HMACD_MINUS_ENABLED = True  # hmacd- (SHORT) enabled
OC_MTF_MACD_ENABLED = False  # OpenClaw version block
```

## Registry Entry

```python
# signals/__init__.py
{'name': 'mtf_macd', 'enabled': 'HMACD_ENABLED', 'run': _mtf_macd_run},
```

Note: `mtf_macd` and `hmacd` share `HMACD_ENABLED` — enabling one enables both. Use directional flags to control direction independently.