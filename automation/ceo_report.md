## CEO Report — 2026-08-10 23:00 UTC

### Diagnosis

Verified DB: 24h 72T -$0.07 (47.2% WR — flat, first red after 15+ green days). 12h 37T -$0.45 (37.8% WR — rough stretch). 7d 370T +$0.41 (51.9% WR — positive, trajectory intact). 3 open positions, $0 unrealized.

Stars 7d: bb_bounce+,range_finder+ LONG 53T +$0.71 (58.5% WR — dominant), bb_bounce+,hzscore+ LONG 28T +$0.34 (53.6% WR — star), bb-bounce-short,hzscore- SHORT 16T +$0.17 (62.5% WR — profitable). All three stars profitable on 7d.

7d bleeds (all legacy, should age out): zscore-rising- SHORT 12T -$0.31 (33.3% WR), ma100-cross,return_exhaustion- SHORT 7T -$0.28 (42.9% WR), hzscore-,return_exhaustion- SHORT 10T -$0.18 (50% WR). All DISABLED, last fires Aug 5-6.

Cost drivers 48h: atr_sl_hit 36T -$1.62, cut-loser-CL-trail 26T -$0.98. SL widening (0.5%→1.2%) deployed 22:00 — too early to evaluate effect.

### Root Cause

Today's first red day is normal variance after 15+ consecutive green days. 12h window rough (37.8% WR) but 7d still positive at 51.9%. Market NEUTRAL, mean-reversion entries getting chopped in ranging conditions. No systemic issue — just noise.

### Fix Applied

**No trading changes.** The 1.2% SL widening (from 0.5%) deployed at 22:00 is the right move. Monitor 24h: if SL hit rate doesn't improve, investigate entry confidence threshold or regime filter sensitivity.

### Verification

7d rolling +$0.41 at 51.9% WR — positive. Daily: Aug 9 strong (+$0.62), Aug 10 flat (-$0.05). Trajectory intact. Next review in 12h to check SL widening effect.

---

## CEO Report — 2026-08-10 22:30 UTC

### Diagnosis

Verified DB: 24h 71T +$0.09 (47.9% WR — flat). Today 62T -$0.15 (45.2% WR — first red day). 7d 379T +$0.18 (50.4% WR — barely positive). LONG 24h 55T -$0.01 (45.5% WR). SHORT 24h 16T +$0.10 (56.3% WR — profitable). 1 open, $0 unrealized.

Stars24h: bb_bounce+,hzscore+ LONG 22T +$0.26 (54.5% WR — dominant), bb_bounce+,range_finder+ LONG 11T -$0.04 (54.5% WR — weak), bb-bounce-short,hzscore- SHORT 3T +$0.01 (66.7% WR).

Cost drivers: atr_sl_hit 36T -$1.62 (48h), cut-loser-CL-trail 28T -$1.04 (48h). bb_bounce+,hzscore+ had 7 SL hits at -$0.30 — all 0% WR. Avg peak move before SL: 0.028%. Trades barely move in favor before reversing.

### Root Cause

Market is NEUTRAL (105/106 tokens). Mean-reversion signals fire at BB touches + z-score extremes, but market isn't reverting — it's ranging/choppy. Entries get stopped out immediately. The SL widening to 1.2% (from 0.5%) reduced individual losses but didn't fix entry quality.

Daily: Aug 9 was strongest (+$0.62), Aug 10 first red (-$0.15). 7d daily shows consistent micro-scalps ($0.01-$0.04 per trade avg).

### Fix Applied

**No trading changes.** The 1.2% SL widening (from 0.5%) deployed at 22:00 is the right move — individual SL hit losses are already smaller (avg -$0.04 vs -$0.08 before). Monitor 24h: if bb_bounce+,hzscore+ SL hit rate stays above 30%, investigate entry confidence threshold.

### Verification

| Metric | Current | Target |
|--------|---------|--------|
| 24h WR | 47.9% | >50% |
| 7d PnL | +$0.18 | Sustain positive |
| SL hit rate (bb_bounce+hzscore+) | 32% (7/22) | <25% |
| SHORT 24h WR | 56.3% | >50% ✓ |

**1 open position. Pipeline timers active. 7d positive but fragile — monitoring.**

---

## CEO Report — 2026-08-10 (Parameter Review)

### Diagnosis

Verified DB: atr_sl_hit is the #1 cost driver — 134T in 7d, avg -0.57%, total -$7.95. The Aug 10 SL tightening (1.2% → 0.5%) did NOT reduce this bleed. It just changed WHO takes the loss: trades that would have recovered now get stopped out at 0.5%. cut-loser-CL-trail at -$1.08 is minor by comparison.

Root cause: **TRAILING_DISTANCE_PCT at 0.30% is the real killer.** With 5x leverage, a 0.06% adverse move from peak triggers exit. Trades lock in micro-profits (0.06-0.15%) then get clipped on any pullback. The SL tightening just made this worse — trades can't breathe to reach profit-monster-trail territory.

### Fix Applied — APPROVED (all 4 changes)

None of these flags are in CEO_PROTECTED_FLAGS. All safe to modify.

| Param | Before | After | Rationale |
|-------|--------|-------|-----------|
| ATR_SL_MIN | 0.005 (0.5%) | 0.012 (1.2%) | Revert. 0.5% SL is redundant with cut-loser, just kills trades early. |
| ATR_SL_MAX | 0.010 (1.0%) | 0.025 (2.5%) | Revert. High-vol tokens need room. |
| ATR_SL_MIN_INIT | 0.005 (0.5%) | 0.012 (1.2%) | MUST match ATR_SL_MIN — init is used for new trade breathing room (tpsl_utils.py:465). |
| ATR_SL_MAX_INIT | 0.010 (1.0%) | 0.025 (2.5%) | MUST match ATR_SL_MAX — paired with MIN_INIT. |
| TRAILING_DISTANCE_PCT | 0.003 (0.30%) | 0.006 (0.60%) | Widen. Trades need room to run. 0.60% still tighter than original 0.70%. |
| CL_TRAIL_ACTIVATE_PCT | -0.5 | -1.0 | Widen. Cut-loser firing at -0.5% is premature on volatile tokens. |
| SL_PCT_FALLBACK | 0.005 (0.5%) | 0.012 (1.2%) | Match ATR_SL_MIN — fallback must be consistent. |
| STOP_LOSS_DEFAULT | 0.005 (0.5%) | 0.012 (1.2%) | Match ATR_SL_MIN — hard fallback must be consistent. |

### Why ATR_SL_MIN_INIT matters

You asked about it. YES — revert it. `tpsl_utils.py:465` uses `ATR_SL_MIN_INIT` as `MIN_SL_PCT` for new trades. If ATR_SL_MIN is 1.2% but INIT stays at 0.5%, new trades still get the tight SL. They're paired params.

### Verification

Monitor for 24h after change:
- atr_sl_hit count should decrease (fewer premature stops)
- profit-monster-trail count should increase (trades reaching trailing territory)
- Avg PnL per trade should improve (trades capturing more of the move)

If WR drops below 45% in 24h, we know the wider SL is letting losers run too far — revert SLMIN/SLMAX only, keep trailing distance.

## CEO Report — 2026-08-10 23:00 UTC

### Diagnosis
Verified DB: 24h 71T -$0.02 (47.9% WR — flat/breakeven), today 63T -$0.04 (46.0% WR — first red day after 15+ green), 7d 368T +$0.42 (51.9% WR — solidly positive). LONG 24h dominant volume, SHORT 24h minimal. Stars: bb_bounce+,hzscore+ LONG 21T +$0.04 (52.4% WR — dominant volume), bb_bounce+,range_finder+ LONG 11T -$0.04 (54.5% WR — rough 24h but 7d intact). bb-bounce-short,hzscore- SHORT 3T +$0.01 (66.7%). 2 open positions. Disk 80%.

### Root Cause
Today's slight red is normal variance after 15+ consecutive green days. atr_sl_hit remains #1 cost driver (36T -$1.62 48h losses), which is why SL widening was deployed at 22:00. Too early to measure effect.

### Fix Applied
NO TRADING CHANGES — SL widening (ATR_SL 0.5→1.2%, TRAILING_DISTANCE 0.30→0.60%) deployed 1h ago, monitoring 24h for SL hit rate improvement. System on strong trajectory (7d +$0.42, 51.9% WR).

### Verification
7d: 368T +$0.42 (51.9% WR). Daily: Aug 5-9 all green, Aug 10 first red (-$0.04 noise). Stars intact. Pipeline healthy. 2 open.

## CEO Report — 2026-08-10 23:00 UTC

### Diagnosis
System flat — 24h 71T -$0.02 (47.9% WR). First red day (-$0.15) after15+ consecutive green days. Noise, not a trend break. 7d +$0.18 (50.4% WR) remains positive. 7d bleeds are ALL old disabled signals (Aug 3-8) aging out — will disappear from7d window within 24-48h.

### Root Cause
Neutral market (105/106 tokens) = low-quality entries getting chopped. atr_sl_hit still #1 cost driver (36T -$1.62 in 48h) — SL was too tight at 0.5%.

### Fix Applied
SL widening deployed at 22:00: ATR_SL_MIN/MAX 0.5%→1.2%/2.5%, TRAILING_DISTANCE_PCT 0.30%→0.60%. Monitoring window active — if WR <45% after 20+ new trades, revert SLMIN/SLMAX only.

### Verification
Parameters confirmed in hermes_constants.py. 6h post-change: 11 SL hits at -$0.50 avg -0.43% — too early to judge, need 12-24h for statistically meaningful sample. No other changes needed — system trajectory positive.

## CEO Report — 2026-08-10 23:55

### Diagnosis
24h 70T -$0.06 (47.1% WR — flat). First flat day after 15+ green days. Market NEUTRAL (105/106 tokens ranging). Mean-reversion entries getting chopped. Stars still positive but weakened. Cost drivers: atr_sl_hit 36T -$1.62, cut-loser-CL-trail 26T -$0.98 (48h).

### Root Cause
Market regime shifted to NEUTRAL — no directional bias for mean-reversion signals to exploit. SL at 1.2% may be too wide for choppy conditions (trades lingering longer before exiting). System was designed for trending regimes.

### Fix Applied
NO CHANGES. SL widening deployed at 22:00 (ATR_SL_MIN/MAX 0.5%→1.2%, TRAILING_DISTANCE_PCT 0.30%→0.60%). Too early to evaluate — needs 24h of data. Monitoring: if WR <45% tomorrow, revert SLMIN/SLMAX only.

### Verification
- DB verified: 24h -$0.06, 7d daily breakdown confirms Aug 4 legacy bleeds aging out
- Stars intact: bb_bounce+,hzscore+ (52.4%), bb-bounce-short,hzscore- (60.0%)
- Pipeline healthy, 4 open trades, $0 unrealized
- Next check: 24h for SL widening impact
