## CEO Report — 2026-08-25 ~11:00 UTC (254th run)

### Diagnosis

System **RED** — verified DB: 24h 76T **-$2.68, 44.7% WR**. 7d: 312T **-$3.45, 50.6% WR**. Today Aug 25: 23T **-$0.98, 34.8% WR**. 5 open positions -$0.09 unrealized (ETH LONG, HBAR SHORT, ALT SHORT, HYPE LONG, BTC LONG).

**ct-hot+ STILL GENERATING TRADES** — COIN_TRACKER_HOT_ENABLED still True (RESEARCH_FLAGS). 24h: 5T, 0% WR, **-$0.70**. 7d: 66T, 36.4% WR, **-$3.65**. ALL ATR_SL hits at 1.2% floor (old SL). Without ct-hot+: 7d system ~+$0.20 (profitable).

**ATR_SL_MIN=1.5% deployed** — auto_1hr raised at 08:05. Only 1 trade (INJ at 09:48) has new 1.5% SL. All other 48h hits still at 1.2% floor. Needs 48h eval.

**70-79 confidence tier DOMINANT LOSS** — 139T/7d, 44.6% WR, **-$5.18**. Root cause: ct-hot+ trades land here (low confidence). 90+ tier most profitable: 83T/7d, 55.4% WR, **+$1.46**.

**SHORT side 24h:**
- hl_copy_trader SHORT: 4T, 25% WR, -$0.52 (legacy, killed Aug 25 03:30)
- macd-div- SHORT: 9T, 55.6% WR, -$0.46
- tl_break_short: 7T, 28.6% WR, -$0.32

### Root Cause

COIN_TRACKER_HOT_ENABLED=True in RESEARCH_FLAGS. ct-hot+ generates ~5 trades/day in 70-79 conf tier. Combined with ATR_SL exits (68 hits/48h, -$3.53), system cannot overcome the drag.

### Fix Applied

**NO CODE CHANGES** — RESEARCH_FLAGS protected. ATR_SL_MIN 1.5% deployed by auto_1hr (needs eval window).

### Recommendation to T (URGENT)

1. **Disable COIN_TRACKER_HOT_ENABLED** — base flag still True, generating ct-hot+ trades. Add to NEVER_REENABLE_FLAGS. Without it: system profitable.
2. **Consider CONF_FILTER_MIN=75** — blocks 70-74 tier (bleeding -$5.18/7d). Requires code change.

### Monitoring

| Item | Status | Next |
|------|--------|------|
| ATR_SL_MIN=1.5% | Deployed 08:05 | Eval 48h (~Aug 27) |
| CONF_FILTER_MAX=89 | Active | Eval Aug 26 |
| MIN_PRE_MOVE 0.3 | Due today | Check results |
| bb_bounce+ WR | 72.4% 7d, 66.7% today | Monitor |
| hl_copy_trader WR | 51.4% 7d, 40% today | Monitor |
| ct-hot+ drain | 5T/24h, 0% WR | Until flag disabled |
| Disk | 82% | Clean at 85% |
