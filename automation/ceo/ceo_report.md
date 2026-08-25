## CEO Report — 2026-08-25 ~15:20 UTC (255th run)

### Diagnosis

System **RED** — verified DB: 24h 56T **-$2.40, 39.3% WR**. 7d: 316T **-$3.96, 50.3% WR**. Today Aug 25: 30T **-$1.58, 33.3% WR**. 5 open positions near breakeven (BTC LONG, ETH SHORT, GMT SHORT +1.37%, HBAR SHORT +0.57%, WLFI LONG).

**ct-hot+ STILL GENERATING TRADES** — COIN_TRACKER_HOT_ENABLED=True in RESEARCH_FLAGS. 7d: 66T, 36.4% WR, **-$3.65** (dominant loss). Without ct-hot+: 7d system ~+$0.20 (profitable). CEO cannot touch RESEARCH_FLAGS.

**ATR_SL hit dominant exit** — 24h: 23 trades, 57.4% of exits, **-$3.61**. ATR_SL_MIN=1.5% deployed 08:05 but too early to evaluate (few trades since change). Previous 48h: atr_sl_hit 39T 60% avg -$5.74. Problem is entry quality (ct-hot+ low-confidence entries), not SL tightness.

**Winners unchanged:**
- bb_bounce+ 32T/7d 71.9% WR +$0.88
- hl_copy_trader 78T/7d 47.4% WR +$0.80
- r2-trend-long6 3T/7d 100% WR +$0.25

**SHORT side:** hl_copy_trader SHORT killed (Aug 25 03:30), legacy draining. tl_break_short 7d 28.6% WR -$0.32 (concerning). macd-div- 69.2% WR -$0.14 (slight negative despite good WR — R:R issue).

### Root Cause

COIN_TRACKER_HOT_ENABLED=True in RESEARCH_FLAGS generates ~1 trade/day. Combined with ATR_SL exits (23 hits/24h), system cannot overcome drag. Today's 33.3% WR = ct-hot+ 0% + atr_sl_hit 57% of exits.

### Fix Applied

**NO CODE CHANGES** — RESEARCH_FLAGS protected. ATR_SL_MIN 1.5% deployed by auto_1hr (eval window ends ~Aug 27). CONF_FILTER_MAX=89 active (eval ends Aug 26).

### Recommendation to T (URGENT)

1. **Disable COIN_TRACKER_HOT_ENABLED** — base flag True in RESEARCH_FLAGS, generating ct-hot+ trades. Without it: system profitable.
2. **Monitor tl_break_short** — 7d 28.6% WR -$0.32. If persists, consider disabling.

### Monitoring

| Item | Status | Next |
|------|--------|------|
| ATR_SL_MIN=1.5% | Deployed 08:05 | Eval 48h (~Aug 27) |
| CONF_FILTER_MAX=89 | Active | Eval Aug 26 |
| ct-hot+ drain | 66T/7d 36.4% WR | Until flag disabled |
| bb_bounce+ WR | 71.9% 7d | Monitor |
| hl_copy_trader WR | 47.4% 7d | Monitor |
| Disk | 82% | Clean at 85% |
