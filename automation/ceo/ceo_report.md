## CEO Report — 2026-08-26 ~14:30 UTC (262nd run)

### Diagnosis
24h: 33T, +$0.31, 51.5% WR (POSITIVE day). 7d: 330T, -$3.58, 50.6% WR. Today Aug 26: 20T, +$0.24, 55% WR. 5 open: +$0.39 unrealized (4 bb_bounce+ LONG, 1 cascade-reverse-v2 SHORT). System green today.

### Root Cause
7d -$3.58 breakdown:
1. **ct-hot+ LONG** 66T 36.4% WR -$3.65 (DOMINANT — legacy draining, ages out Aug 27)
2. **ATR_SL** 39T/48h -$5.88 (structural, offset by profit-monster-trail)
3. **hl_copy_trader SHORT** 6T 16.7% WR -$0.76 (already killed)

### Discovery
1. **tl_break_short recommendation is STALE** — signal was killed Aug 25 (TL_BREAK_MINUS_ENABLED=False, NEVER_REENABLE_FLAGS). CURRENT.md line 67 still says "RECOMMEND T: Investigate tl_break_short SHORT SL params." Stale.
2. **hl_copy_trader ALL killed by auto_1hr** (Aug 25 ~20:10 UTC). Was backbone signal at +$1.44/7d, 49.3% WR. Last24h:2T 0% WR -$0.34 (BTC/ETH ATR_SL hits). Kill justified by recent bleed. System now has ONLY bb_bounce+ as performer — single-signal dependency risk.
3. **bb_bounce+ 24h degraded** — 8T 37.5% WR -$0.08 (was 66.7% 7d). Still 7d profitable but 24h weak. Monitor closely.

### Fix Applied
No code changes. Updated CURRENT.md:
- Removed stale tl_break_short recommendation (line 67)
- Added hl_copy_trader ALL killed status
- Added RECOMMEND: build new backbone signal to replace hl_copy_trader

### Verification
Today +$0.24, 55% WR. All kills active. ct-hot+ legacy draining. Lifecycle filters LIVE (48h eval ending Aug 28). Disk 83%. Pipeline 0 errors. System positive but fragile — single-signal dependency on bb_bounce+.

---

## CEO Report — 2026-08-26 ~13:00 UTC (261st run)

### Diagnosis
24h: 33T, -$0.54, 48.5% WR. 7d: 329T, -$3.61, 50.5% WR. Today Aug 26: 20T, +$0.24, 55% WR (best day of week — recovering from Aug 25's 35.1% disaster). 5 open: +$0.27 unrealized. Lifecycle filters deployed today, 48h eval ending Aug 28.

### Root Cause
7d -$3.61 dominated by:
1. **ct-hot+ LONG** 66T 36.4% WR -$3.65 (DOMINANT — legacy draining, ages out Aug 26-27)
2. **ATR_SL** 182T -$5.35 (55% of exits — structural, offset by profit-monster-trail 94T +$5.45)
3. **SHORT side** 96T -$2.73 (all losing — hl_copy_trader SHORT 6T -$0.76 already killed, tl_break_short inverted R:R)

### Discovery
**tl_break_short has INVERTED R:R** — 62.5% WR but -$0.11/7d. PM_TRAIL exits: 11T +$0.57 (+2.13% avg = EDGE). ATR_SL exits: 3T -$0.48 (-6.35% avg = DESTROYS EDGE). Signal works but SHORT SL is too loose — 3 ATR_SL trades at -6.35% avg erase 11 PM_TRAIL wins at +2.13% avg. Recommend T: tighten SHORT SL parameters or disable tl_break_short.

### Fix Applied
No code changes. RECOMMEND T: investigate tl_break_short SHORT SL params (ATR_SL avg -6.35% vs PM_TRAIL avg +2.13% — inverted). auto_1hr watching continuation- (3T 0% WR, kill on next loss). pump-catcher+ at 2T 0% WR -$0.17 (1 loss from kill threshold).

### Verification
System improving underneath: Aug 26 best WR day of week (55%). All kills active. ct-hot+ legacy draining. Signal lifecycle filters LIVE. Disk 83%. Pipeline 0 errors. Market: 111 SHORT_BIAS, 41 NEUTRAL, 20 LONG_BIAS.

---

## CEO Report — 2026-08-26 ~00:25 UTC (259th run)

### Diagnosis
24h: 34T, -$1.35, 41.2% WR. 7d: 317T, -$3.95, 50.5% WR. Today Aug 26: 2T, +$0.04 (just started). 5 open trades (2 cascade-reverse-v2 SHORT, 2 continuation- SHORT, 1 r2-trend-long14 LONG).

### Root Cause
7d -$3.95 dominated by:
1. **ct-hot+** 66T/7d 36.4% WR -$3.65 (DOMINANT — CEO_PROTECTED, draining)
2. **hl_copy_trader SHORT** 6T/7d 16.7% WR -$0.76 (KILLED, legacy closing)
3. **ATR_SL** 175T/7d -$5.41 (55% of all exits — structural)
4. **cut-loser-MAE-GUARD** 17T/7d -$1.58 (legacy, signal killed)

### SHORT vs LONG
- SHORT 7d: 88T 47.7% WR -$2.85 (bleeding — hzscore- 50% WR inverted R:R, cascade-reverse-v2 new)
- LONG 7d: 229T 51.5% WR -$1.10 (improving — bb_bounce+ star, hl_copy_trader backbone)

### What's Working
- bb_bounce+: 33T/7d 69.7% WR +$0.66 (star — today degraded to 41.7%, small sample)
- hl_copy_trader LONG: 73T/7d 49.3% WR +$1.44 (backbone)
- r2-trend-long6: 3T/7d 100% WR +$0.25
- All kills active (hl_copy_trader SHORT/LONG, ct-hot+)
- ATR_SL_MIN=1.2% (reverted from 1.5% — wider was worse)
- CONF_FILTER_MAX=89 (eval ending Aug 26)
- Pipeline active, timers firing, disk 82%

### Monitoring
- **CONF_FILTER_MAX=89 eval (Aug 26)** — 48h window closing
- **MIN_PRE_MOVE=0.3 eval (Aug 25)** — check if filter producing results
- **bb_bounce+ recovery** — 41.7% today vs 69.7% 7d, small sample but watch
- **cascade-reverse-v2 SHORT** — 3 open, 0 closed, new signal evaluating
- **continuation- SHORT** — 2 open, 1 closed (-$0.14), re-enabled Aug 25
- **Phantom trade ALT SHORT #14327** — flagged, likely stale

### DECISION: 30s Price Interval

**A — Split Architecture.** System at 39.4% WR / -$1.36 — no time for risky full migration. Split keeps 30s exit freshness while signals revert to calibrated 60s bars. One line change, zero signal rewrites.

### DECISION: Signal Cluster — Build option B (Signal Lifecycle Filters)

**Rationale:** ATR_SL is 55% of all exits (177T/7d -$5.10). Lifecycle filters address WHEN SL/TP triggers, not just IF. 1-hour build, high ROI.

### Next Actions
1. **Monitor CONF_FILTER_MAX=89** — eval window closes Aug 26
2. **Monitor MIN_PRE_MOVE=0.3** — check filter impact today
3. **Build new SHORT signal** — SHORT side structural issue, pending from Aug 24
4. **Monitor bb_bounce+** — if 48h WR <50%, delegate signal_analyst

## CEO Report — 2026-08-26

### Acknowledgment
- **30s split architecture** implemented: price_history quantized to minute bars, latest_prices every 30s for exit freshness. 3 bugs fixed (row counter, backfill range, connection lifecycle). CEO approved.

## CEO Report — 2026-08-26 ~04:05 UTC

### Diagnosis
System 7d: 320T -$3.62, 50.9% WR. Today: 6T +$0.40, 100% WR (improving). ATR_SL dominant loss: 177T/7d -$5.10 (55% of exits). ct-hot+ legacy 66T/7d -$3.65 still draining. hl_copy_trader LONG bad48h (-$1.03, 30.8% WR) but 7d still +$1.39. SHORT 48h 62T -$1.83 bleeding. Market 111 SHORT_BIAS tokens — SHORT signals allowed but edge missing.

### Root Cause
ct-hot+ (CEO_PROTECTED, RESEARCH_FLAGS) remains dominant loss. hl_copy_trader LONG rough patch — all 7 losses from ATR_SL_MIN=1.5% period (reverted to 1.2%). 79 conf tier is -1.4.31 but 90% is ct-hot+ (36/40T). Without ct-hot+: system 7d ~+$0.03 (breakeven, improving).

### Fix Applied
No code changes. All kills active. ATR_SL_MIN reverted to1.2% (Aug 25 16:30). Post-revert trades: 6T +$0.40, 100% WR. Monitor 48h for ATR_SL improvement.

### Verification
- 24h: 33T -$1.25, 42.4% WR (legacy closing)
- 7d: 320T -$3.62, 50.9% WR
- Today: 6T +$0.40, 100% WR
- Pipeline: active, 0 errors
- Disk: 83%
- Open: 5 SHORT
- Regime: 111 SHORT_BIAS, 41 NEUTRAL, 20 LONG_BIAS

### DECISION: Signal Cluster — Build option A (Inverse Correlation Guard, 15 min). Rationale: ATR_SL dominant (55% exits -.10/7d) but signal-level correlation bleed is a separate problem — contradictory families (e.g. bb_bounce+ LONG vs SHORT) fire simultaneously, creating hedged losses. Quick win, 15 min, clears confluence noise before tackling lifecycle filters.

DECISION: Build option A (Inverse Guard)
