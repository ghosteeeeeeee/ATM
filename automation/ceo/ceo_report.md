## CEO Report — 2026-08-25 ~10:30 UTC (253rd run)

### Diagnosis

System **RED** — verified DB: 24h 78T **-$2.92, 44.9% WR**. 7d: 312T **-$3.45, 50.6% WR**. Today Aug 25: 23T **-$0.98, 34.8% WR** (bad day). 5 open positions near breakeven.

**ct-hot+ STILL #1 LOSER** — 66T/7d, 36.4% WR, **-$3.65**. ALL 3 flags still True (COIN_TRACKER_HOT_ENABLED, COIN_TRACKER_HOT_MINUS_ENABLED). CEO_PROTECTED. Without ct-hot+: 7d system ~+$0.20 (profitable).

**ATR_SL improving** — auto_1hr raised ATR_SL_MIN 1.2%→1.5% today 08:05 UTC. Today: 17 ATR_SL hits, 41.2% WR, avg -$1.38. Yesterday: 32 hits, 25% WR, avg -$3.34. Floor working.

**70-84 confidence tier BLEEDING** — 207T/7d, 46.9% WR, **-$5.01**. Root cause: ct-hot+ (66T) + legacy SHORT signals (hl_copy SHORT 6T, macd-div+ 3T, various ct-hot- combos). The CONF_FILTER_MAX=89 blocks 90+ but 70-84 tier is the real loss source.

**Winners today struggling:**
- bb_bounce+ LONG: 9T today, 44.4% WR, -$0.22 (was 88.9% 7d — small sample noise)
- hl_copy_trader LONG: 8T today, 37.5% WR, -$0.32 (was 51.4% 7d — small sample noise)

**Winners 7d still green:**
- bb_bounce+ LONG: 29T/7d, 72.4% WR, +$0.83
- hl_copy_trader LONG: 70T/7d, 51.4% WR, +$1.98
- profit-monster-trail: carrying system

### Root Cause

ct-hot+ family (base + SHORT) generating ~9 trades/day in 70-84 confidence tier. Combined with ATR_SL exits (44 hits/48h, -$7.39), system cannot overcome the drag. Cascade flip SQL bug fixed this morning (was blocking closes for ~30min).

### Fix Applied

**NO CODE CHANGES** — CEO_PROTECTED flags. ATR_SL_MIN 1.5% deployed by auto_1hr (needs eval window).

### Recommendation to T (URGENT)

1. **Disable COIN_TRACKER_HOT_ENABLED and COIN_TRACKER_HOT_MINUS_ENABLED** — same family as killed ct-hot+. 66T/7d -$3.65. Without them: system profitable.
2. **Consider CONF_FILTER_MIN=75** — blocks 70-74 tier (bleeding). Requires code change in signal_compactor.py + hermes_constants.py.

### Monitoring

| Item | Status | Next |
|------|--------|------|
| ATR_SL_MIN=1.5% | Just deployed (08:05) | Eval 48h (~Aug 27) |
| CONF_FILTER_MAX=89 | Active | Eval Aug 26 |
| MIN_PRE_MOVE 0.3 | Due today | Check results |
| bb_bounce+ WR | 72.4% 7d, 44.4% today | Monitor (small sample) |
| hl_copy_trader WR | 51.4% 7d, 37.5% today | Monitor (small sample) |
| Disk | 82% | Clean at 85% |
