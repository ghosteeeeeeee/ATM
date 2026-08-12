## CEO Report — 2026-08-14 23:00 UTC

### Diagnosis

**Verified DB numbers (not trusting old reports):**
- **7d**: ~398T +$0.88, 53.3% WR — solid
- **24h**: 66T -$0.15, 51.5% WR — flat/slightly negative
- **LONG 24h**: 50T -$0.47, 46.0% WR — bleeding
- **SHORT 24h**: 16T +$0.32, 68.8% WR — strong
- **Open**: 5T, $0.00 unrealized

**Stars7d intact:** bb_bounce+,range_finder+ LONG 53T +$0.71 58.5%, bb-bounce-short,hzscore- SHORT 17T +$0.12 58.8%, hzscore+,mover+ LONG 5T +$0.17 80%, bb_bounce+,hzscore+ LONG 34T +$0.22 50%

**24h bleeders:** trend_momentum_near_sma+ LONG 6T -$0.37 16.7% WR (DISABLED, legacy), range_breakout+ LONG 5T -$0.28 20% WR, hzscore+ LONG 11T -$0.16 36.4% WR

**48h exit drivers:** atr_sl_hit 53T -$2.60 (dominant), cut-loser-CL-T1 4T -$0.42, cut-loser-CL-trail 6T -$0.28

**Daily trend:** Aug 9 +$0.62 (peak) → Aug 10 -$0.10 → Aug 11 -$0.33 (trough) → Aug 12 +$0.07 (recovery) — system stabilizing

### Root Cause

1. LONG bias bleeding today — range_breakout+ and hzscore+ standalone entries catching falling knives. Both already have momentum fade filters deployed Aug 13 — evaluation window now complete.
2. SHORT turned profitable today (+$0.32) — regime-driven, not signal-driven.

### Fix Applied

**NO CHANGES THIS RUN.** Rationale:
- Aug 13 changes eval window COMPLETE (trailing stop fix, momentum fade, confidence tightening, accel-300 re-enable)
- 7d PnL +$0.88 — positive, stars intact
- SHORT recovery confirmed — profitable today
- Pipeline recovered from decider_run crash — stable since 19:30
- Overreacting destabilizes — let filters work

### Verification

- Pipeline: ACTIVE (recovered from decider_run crash)
- Stars7d intact: all 4 star combos profitable
- trend_momentum_near_sma+ DISABLED (legacy)
- 5 open trades flat — no risk
- Disk 76% — safe
- Live trading: enabled

### Next Review

- Monitor range_breakout+ LONG — if 7d bleeds >$0.50, disable
- Monitor hzscore+ standalone — if momentum fade filter doesn't improve 24h WR, remove from STANDALONE_BYPASS_SIGNALS
- SHORT7d bleed -$0.77 — improving, no action needed unless worsens to -$1.50+
