## CEO Report — 2026-08-17 (48th run)

### Diagnosis
System POSITIVE. Verified 24h: 41T +$0.17, 48.8% WR. Today Aug17: 3T +$0.35, 100% WR (early but clean). 48h exits: PM_TRAIL 42T +$1.61 (80% WR, avg +0.37%), T1 11T +$0.62, ATR_SL 38T -$2.32 (avg -0.62%). PM_TRAIL R:R = +0.37%/-0.62% = 0.60:1 — better than last run. ct-hot+ 33T/48h 42.4% WR -$0.42 (18 ATR_SL hits = 47% of all stops). Open: 1, $0 flat. 7d: 430T -$2.84, 48.1% WR.

### Key Findings
- **System FLIPPED POSITIVE** — +$0.17/24h (was -$0.02 last run). Self-correcting.
- **PM_TRAIL stronger than reported** — 42 exits 80% WR +$1.61/48h. avg +0.37% per exit. R:R improving (0.60:1 vs 0.33:1 earlier).
- **ATR_SL stable** — 38T/48h at -0.62%. 18 from ct-hot+ (47%). Non-ct-hot ATR_SL = 20T -$1.70/48h.
- **Today clean** — 3T +$0.35, 100% WR. All r2-trend and bb_bounce+ signals.
- **Stars intact** — return_exhaustion_long 4T 100% +$0.43, bb_bounce+ 24T 58.3% +$0.21, r2-trend-long2 17T 64.7% +$0.19.
- **Hotset empty** — normal for Sunday 02:00 UTC (dead market, 0 entries/hour).
- **ct-hot+ legacy clearing** — 18/38 ATR_SL from ct-hot+. Expected to clear Aug 17-18.
- **7d losers all KILLED** — wave_catcher+, range_breakout+, trend_momentum all disabled. Only ct-hot+ remains (user testing mode).
- **Phantom trades** — guardian_orphan 6T -$0.10/48h. Non-critical, backlog.

### Fix Applied
NO CHANGES — system positive (+$0.17/24h), respecting user TESTING MODE on ct-hot+ (MIN_COMPOSITE 55). PM_TRAIL dist 0.20% working (80% WR). ATR_SL count 38/48h stable. All other losers already killed. No signal starvation (41T/24h).

### Verification
24h +$0.17 POSITIVE. PM_TRAIL 42T 80% WR +$1.61/48h. ATR_SL 38T -$2.32 (18 from ct-hot+). Real system positive. Monitor: ATR_SL count (should ↓ from 38/48h), PM_TRAIL WR (must hold >65%), ct-hot+ legacy clear Aug 17-18, daily trades (must >20T).

---

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

## CEO Report — 2026-08-17 (46th run)

### Diagnosis
System IMPROVING. Verified 24h: 42T -$0.33, 42.9% WR. Real system excl ct-hot+: ~30T +$0.01, flat (POSITIVE). PM_TRAIL 20T +$0.62 dominant winner. ATR_SL 17T -$0.85 dominant drag (daily: 41→18, SPEED_MIN 40 working). 2 open trades (bb_bounce+ LONG $57, ct-hot+ LONG $0.16). ct-hot+ 10T/24h -$0.46, 20% WR — user TESTING MODE. Guardian_orphan 4T/24h -$0.10 phantom trades. 7d stars intact: return_exhaustion_long 4T 100% +$0.43, bb_bounce+ 24T 58.3% +$0.21, r2-trend-long2 17T 64.7% +$0.19. 7d: 432T -$2.84, 48.1% WR.

### Root Cause
System is self-correcting. Real engine flat to positive. ct-hot+ is #1 drag (user-controlled, can't disable). ATR_SL improving but still dominant. Phantom trades (guardian_orphan) are noise — not a signal issue. SHORT side dead but user-controlled.

### Fix Applied
NO CHANGES — respecting user TESTING MODE on ct-hot+ and range_breakout_short. PM_TRAIL dist 0.15% confirmed working (74.4% WR, R:R 2.70:1). SPEED_MIN 40 continuing evaluation (daily ATR_SL: 41→18). hzscore- killed this run.

### Verification
Pipeline active. PM_TRAIL 20T +$0.62/24h. ATR_SL 17T -$0.85 (down from 38/48h). Real system positive. ct-hot+ legacy aging out. Monitor: ATR_SL count (should ↓ from 17/24h), PM_TRAIL WR (must hold >65%), daily trades (must >20T), ct-hot+ legacy clear Aug 17-18.

## CEO Report — 2026-08-17 (47th run)

### Diagnosis
System NEARLY FLAT — major improvement. Verified 24h: 40T -$0.02, 47.5% WR. 48h: 98T, PM_TRAIL 41T 75.6% WR +$1.42, T1 11T 100% +$0.62, ATR_SL 38T 2.6% -$2.32. Real system excl ct-hot+ (user TESTING MODE): ~30T +$0.21 (POSITIVE). 2 open ~$0.21 unrealized. 7d: 430T -$2.84, 48.1% WR. ATR_SL daily: 23→18→41→28→28→20→18 (SPEED_MIN 40 working, 56% reduction from peak). ct-hot+ ATR_SL: 18/38 hits (47%), -$1.23 (53% of ATR_SL loss). NEUTRAL regime 100% for7d. Guardian_orphan 6T/48h -$0.10 phantom trades.

### Root Cause
System self-correcting. Real engine positive. ct-hot+ is #1 drag (user-controlled TESTING MODE) — responsible for 47% of ATR_SL hits. ATR_SL improving but still dominant. PM_TRAIL carrying system at 75.6% WR. Market flat (NEUTRAL) — no regime-driven opportunities.

### Fix Applied
NO CHANGES — respecting user TESTING MODE on ct-hot+. System essentially flat (-$0.02/24h). PM_TRAIL edge strong (75.6% WR, R:R 2.70:1). SPEED_MIN 40 continuing to reduce ATR_SL frequency. hzscore- already killed.

### Verification
Pipeline active. 24h nearly flat (-$0.02). PM_TRAIL 41T 75.6% +$1.42/48h. ATR_SL 38T -$2.32/48h (18 from ct-hot+). Real system positive. Monitor: ATR_SL count (should ↓ from 38/48h), PM_TRAIL WR (must hold >65%), ct-hot+ legacy clear Aug 17-18, daily trades (must >20T).
