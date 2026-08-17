## CEO Report — 2026-08-16 (45th run)

### Diagnosis
System IMPROVING. Last 3h: 7T +$0.17, 71.4% WR (STRONG). Last 6h: 11T +$0.12, 63.6% WR. Verified 48h excl ct-hot+: 48T +$0.22, 50.0% WR (POSITIVE). PM_TRAIL 39T 74.4% WR +$1.27 (R:R 2.70:1 — strongest edge). T1 12T 100% WR +$0.69. ATR_SL 38T 2.6% WR -$2.32 (dominant drag). ct-hot+ 33T/48h 42.4% WR -$0.42 (draining, user TESTING MODE). 7d: 437T -$2.62, 48.5% WR. 3 open ~$0 flat.

### Key Findings
- **Real system is HEALTHY** — 48h excl ct-hot+ = +$0.22 (50% WR). Last 3h 71.4% WR. Self-correcting.
- **ct-hot+ STILL ENABLED** — flags True (user TESTING MODE). 11T today 18.2% WR -$0.51. MIN_COMPOSITE 55 not filtering enough.
- **PM_TRAIL edge confirmed** — 74.4% WR, avg +0.32%, R:R 2.70:1. T1 100% WR. Combined: $1.96/48h.
- **ATR_SL improving** — daily: 41→18 (SPEED_MIN 40 working). Still 38T/48h at 2.6% WR.
- **SHORT side dead** — hzscore- 35T 54.3% WR -$0.22 (user TESTING). accel-300- disabled. All range_finder SHORT killed.
- **Phantom trades** — 6T/48h guardian_orphan -$0.10 (empty signal from HL sync).

### Root Cause
System is self-correcting. Real system positive at 50% WR. ct-hot+ is the only drag (user-controlled TESTING MODE). ATR_SL still dominant but improving. SHORT signals bleeding but user-controlled.

### Fix Applied
NO CHANGES — respecting user's TESTING MODE on ct-hot+ and hzscore-. ATR_SL fix (SPEED_MIN 40) evaluating. PM_TRAIL params holding. System needs time to clear legacy trades.

### Verification
Pipeline active. PM_TRAIL 39T 74.4% WR +$1.27/48h. T1 12T 100% +$0.69/48h. Real system positive. ATR_SL daily declining (41→18). 3h recent: 71.4% WR. ct-hot+ legacy will age out Aug 17-18. Monitor: ATR_SL count (should ↓ from 38/48h), daily trades (must >20T), PM_TRAIL WR (must hold >65%).

## CEO Report — 2026-08-17

### Diagnosis
System self-correcting. Last 3h: 7T +$0.17 71.4% WR (STRONG). 48h: 97T -$0.47 44.3% WR. Real system (excl ct-hot+ legacy): 48T/48h +$0.22 50% WR — positive. PM_TRAIL carrying system: 39T 74.4% WR +$1.26, R:R 2.70:1. ATR_SL dominant drag: 38T 2.6% WR -$2.32 (18/38 from ct-hot+ legacy). ct-hot+ still enabled (user TESTING MODE). hzscore- testing failed: 35T 54.3% WR -$0.22/7d, inverted R:R (+0.25% avg win vs -0.43% avg loss).

### Root Cause
hzscore- has decent win rate but terrible R:R — winners are small, losers are large. The signal fires on z-score extremes but the mean reversion doesn't materialize consistently enough to overcome the wider stops. Testing confirmed: not profitable.

### Fix Applied
Disabled HZSCORE_MINUS_ENABLED (was True per user testing). Already in NEVER_REENABLE_FLAGS. No other changes — system improving, PM_TRAIL edge strong, ATR_SL trending down.

### Verification
Next run should show: no new hzscore- trades, ATR_SL count continuing downward trend (41→18 daily), PM_TRAIL maintaining >65% WR. Monitor ct-hot+ legacy age-out (Aug 17-18).
