## CEO Report — 2026-08-24 ~22:15 UTC (251st run)

### Diagnosis

System **SLIGHTLY RED** — 24h 92T **-$0.65, 59.8% WR**. 7d: 292T **-$2.51, 51.7% WR**. 5 open near breakeven (-$0.18). Win rate healthy (59.8%) but exit math negative — ATR_SL exits -39T -$6.53 dragging.

**ct-hot+ STILL the #1 LOSER** — 66T/7d, 36.4% WR, **-$3.65**. ALL 3 flags still `True` in hermes_constants.py (COIN_TRACKER_HOT_ENABLED=True, COIN_TRACKER_HOT_MINUS_ENABLED=True). CEO_PROTECTED — cannot disable. Without ct-hot+: 7d system ~+$1.14 (profitable).

**Winners carrying:**
- bb_bounce+ LONG: 18T/7d, **88.9% WR**, +$1.11 (star)
- hl_copy_trader LONG: 62T/7d, 53.2% WR, +$2.30 (backbone)
- profit-monster-trail: 49T/24h, +$3.17 (exit engine)

**Daily:** Aug 22 was worst (-$2.73, ct-hot+ drain). Aug 24: 91T -$0.51, 60.4% WR (flat).

### Root Cause

ct-hot+ family (base + SHORT) still enabled, same edge problem as ct-hot+ LONG (killed Aug 24). 66T/7d legacy trades in 7d window. Plus ATR_SL exits: 39T/48h -$6.53 — trades that hit SL exit at -5.87% avg.

### Fix Applied

**NO CODE CHANGES** — CEO_PROTECTED flags cannot be disabled.

### Recommendation to T (URGENT)

1. **Disable COIN_TRACKER_HOT_ENABLED** and **COIN_TRACKER_HOT_MINUS_ENABLED** — same family as killed ct-hot+. Add to NEVER_REENABLE_FLAGS. Projected: system becomes ~+$1.14/7d without drag.
2. **Monitor CONF_FILTER_MAX=89** — eval ends ~Aug 26 15:30 UTC. 90+ tier now +$1.91/7d.

### Monitoring

| Item | Status | Next |
|------|--------|------|
| CONF_FILTER_MAX=89 | Active | Eval Aug 26 |
| MAE-Guard | Active, monitoring hl_copy_trader WR | If drops, recommend disable |
| MIN_PRE_MOVE 0.3 | 0 closed trades/48h | Eval extended to Aug 25 |
| bb_bounce+ WR | 88.9% (18T) | Keep >70% |
| PM_TRAIL edge | +$3.17/24h | Must hold >80% WR |
| Disk | 81% | Clean at 85% |
| Wyckoff detection | 25/109 tokens | Monitor continued improvement |
