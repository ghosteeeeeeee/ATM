## CEO Report — 2026-08-16 (38th run)

### Diagnosis
System -$0.82/24h (34.8% WR, RED). ct-hot+ user-re-enabled (TESTING MODE): 17T/24h -$0.58, 29.4% WR. Non-ct-hot real system: 22T/24h flat (-$0.01). ATR_SL still dominant drag: 36T/48h avg -0.70% -$2.50 (92% of losses). PM_TRAIL working: 10T/48h avg +0.23% +$0.26 (70% WR). 3 open, $0.00 unrealized. R:R inverted 0.33:1 (PM_TRAIL +0.23% vs ATR_SL -0.70%).

### Root Cause
R:R structural inversion. PM_TRAIL distance 0.20% caps avg win at ~0.20%. ATR_SL avg loss -0.70%. To flip R:R positive, need either PM_TRAIL wins >0.70% (impossible at 0.20% dist) OR ATR_SL losses <0.20% (requires drastic tightening). SPEED_MIN 40 deployed today — ATR_SL daily trend: 41→28→28→20→15. Working but needs full 24h eval. ct-hot+ TESTING MODE: user explicitly re-enabled (flags True, "DO NOT DISABLE"). 18/36 ATR_SL hits are ct-hot+.

### Fix Applied
**NO CHANGES this run.** Reasons:
1. SPEED_MIN 40 eval window active (deployed today, needs 24h)
2. PM_TRAIL 0.20% dist confirmed working (70% WR)
3. ct-hot+ user-controlled (TESTING MODE — cannot disable)
4. Non-ct-hot system stable (flat, 22T/24h)
5. Legacy trades clearing naturally (Aug 17-18)
6. Stars7d intact: return_exhaustion_long 4T 100% +$0.43, bb_bounce+ 22T 63.6% +$0.25, r2-trend-long2 17T 64.7% +$0.19

### Verification
| Metric | Before (37th) | Current (38th) | Target |
|--------|---------|---------|--------|
| 24h PnL | -$0.84 | -$0.82 | $0 |
| 24h WR | 34.0% | 34.8% | >55% |
| ATR_SL 48h | 37T -$2.43 | 36T -$2.50 | <20T |
| PM_TRAIL WR | 67.5% | 70.0% | >60% |
| R:R | 0.51:1 | 0.33:1 | >1:1 |
| Daily trades | 33T | 46T | >20T |
| ATR_SL daily | 15 | 15 | <10 |

### Next Actions
1. **ATR_SL eval** — SPEED_MIN 40 needs 24h. If ATR_SL still >25/48h → raise to 45
2. **ct-hot+ monitoring** — user TESTING MODE, track if WR improves at current params
3. **PM_TRAIL hold** — 70% WR at 0.20% dist, must hold >60%
4. **Legacy age-out** — ct-hot+ legacy clearing Aug 17-18 (all flags False, old entries)
5. **R:R improvement** — currently 0.33:1, structural constraint at PM_TRAIL 0.20% dist
