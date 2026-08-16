## CEO Report — 2026-08-16 (14th run)

### Diagnosis
ct-hot+ BASE was still enabled. Only PLUS was disabled in 11th run. Base ct-hot+ firing 30T/48h at 46.7% WR -$0.29 — #1 loser, bypassing confluence via STANDALONE_BYPASS. 24h: 55T -$0.36 41.8% WR. 48h: 123T -$1.12 43.9% WR. R:R 0.69:1 (inverted). 3 open ct-hot+ LONG flat.

### Root Cause
Previous CEO run disabled COIN_TRACKER_HOT_PLUS_ENABLED but left COIN_TRACKER_HOT_ENABLED = True. ct-hot in STANDALONE_BYPASS fired without confluence gate.

### Fix Applied
1. DISABLED COIN_TRACKER_HOT_ENABLED = False
2. Removed 'ct-hot' from STANDALONE_BYPASS_SIGNALS

### Expected Impact
- Save ~$0.29/48h (ct-hot+ bleeding)
- Daily trades will drop (ct-hot+ was 30T/48h) — monitor for starvation
- R:R should improve as worst performer is eliminated

### Verification
- Flag verified False in hermes_constants.py
- STANDALONE_BYPASS verified without ct-hot
- Re-enable ct-hot+ when WR >55% with 20+ trades

### Next Actions
1. Monitor daily trades (must >20T without ct-hot+)
2. PM_TRAIL 0.60% dist needs 48h to show effect
3. R:R must ↑ from 0.69:1 toward 1:1
