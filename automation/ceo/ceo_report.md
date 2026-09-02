## CEO Report — 2026-09-02 ~07:30 UTC

### Diagnosis
Previous CEO overcounted — combined accel-300-v2-long + v3-long as one signal. Corrected: v2-long only 4T/24h (closing old positions), v3-long 14T/24h -$0.51 (real #1 loss). LONG side bleeds -$1.79/7d, SHORT profitable +$0.48/7d.

### Root Cause
ACCEL_300_V3_LONG_ENABLED was added Sep 1 but bleeding immediately: 42.9% WR, ALL atr_sl_hit exits. Not CEO_PROTECTED. BB_BOUNCE_LONG still True, CEO_PROTECTED, flagged for T.

### Verified Numbers
| Metric | Value |
|--------|-------|
| 24h | 61T, 47.5% WR, -$0.97 |
| 48h | 127T, 47.2% WR, -$1.71 |
| 7d | 416T, 50.0% WR, -$1.31 |
| 7d SHORT | 248T, 53.2% WR, +$0.48 |
| 7d LONG | 168T, 45.2% WR, -$1.79 |
| #1 loss | accel-300-v3-long: 14T/24h -$0.51 |
| Carry | profit-monster-trail: 17T/24h +$1.01 |

### Fix Applied
- **KILLED ACCEL_300_V3_LONG_ENABLED.** Stops -$0.51/24h bleeding.
- FLAGGED BB_BOUNCE_LONG for T (CEO_PROTECTED, can't disable).

### Expected Impact
System improves from -$0.97/24h to approximately -$0.46/24h (-$0.51 stopped). Need T to disable BB_BOUNCE_LONG for further improvement.

---

## CEO Report — 2026-09-02

### Diagnosis
System is PROFITABLE without legacy bleed — but accel-300-v2-long is STILL TRADING despite being killed Sep 1. Previous CEO run at 01:40 reported it "DEAD (zero trades post-kill)" — WRONG. DB verified: 11T/24h -$0.52, 27.3% WR. This is the #1 bleeding source.

### Root Cause
Two CEO_PROTECTED signals dragging a profitable system:
1. **accel-300-v2-long** — constant is False but STILL generating trades (11T/24h, 27.3% WR, -$0.52). Previous "kill" did not work. Needs CODE investigation — pipeline may be caching the signal or signals_runner bypasses the flag.
2. **BB_BOUNCE_LONG_ENABLED=True** — T re-enabled for "TESTING" despite NEVER_REENABLE. 23T/24h 56.5% WR -$0.28. CEO_PROTECTED + NEVER_REENABLE conflict.

### Verified Numbers
| Metric | Value |
|--------|-------|
| 24h | 60T, 46.7% WR, -$1.08 |
| 48h | 114T, 46.5% WR, -$1.49 |
| 7d | 405T, 50.6% WR, -$0.62 |
| 7d clean (no legacy) | ~+$1.72 (system profitable) |
| Best signal | accel-300-v2- SHORT: 72T 52.8% WR +$1.46 |
| Carry mechanism | profit-monster-trail: 55T 94.5% WR +$2.60 |
| Open | 5 SHORT (all slightly profitable) |

### Fix Applied
No parameter changes — both blockers are CEO_PROTECTED. FLAGGED for T:
- **CRITICAL:** Investigate why accel-300-v2-long still trades despite constant=False. Check signals_runner.py and signal_compactor.py for cached imports or bypass paths.
- Disable BB_BOUNCE_LONG_ENABLED (CEO_PROTECTED + NEVER_REENABLE conflict)

### Expected Impact
If T fixes both blockers: system goes from -$0.62/7d to approximately **+$1.72/7d** (+$2.34 improvement). That's the entire gap between losing and profitable.
