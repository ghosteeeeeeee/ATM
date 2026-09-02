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
