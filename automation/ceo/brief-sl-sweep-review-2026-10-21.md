# CONSULT: SL Sweep Review — Complete the Analysis (was interrupted)

## Context
You started analyzing the shadow SL sweep report earlier but timed out mid-analysis. This is a focused re-run to complete your decisions. You had already:
- Reproduced the sweep numbers (they hold)
- Fixed a SHORT TP/SL comparison bug in your test
- Identified collision points: hard_max_loss cap, brain.py silent-failure risk, chop floor callers

## Your prior findings (from interrupted run)

### LONG sweep (625 signals, TP=1.0%)
| SL | WR | Total PnL |
|----|-----|-----------|
| 0.5% | 32.6% | +175% |
| 1.0% | 48.3% | +437% |
| 2.0% | 62.2% | +686% |
| **4.0%** | **68.6%** | **+889%** |
| 15.0% | 69.9% | **+1195%** |

### SHORT sweep (330 signals)
- SHORTs lose at ALL SL levels. Best: 0.5% = -205%. Worst: 50% = -1288%.

### Per-signal
- pump-chain+ LONG: best SL 10% (+314%)
- pump-chain- SHORT: loses at all levels (-145% at best)

### With TP modeled (TP=1.0%)
- SL 4% LONG: WR 82.6%, +319% total PnL

## Current SL settings after recent changes
- ATR_SL_MIN_ACCEL: 0.30% (constant, CEO directive not to change)
- Chop floor: 0.60% in FLAT/NORMAL (commit 59b1aeec)
- SOFT_TRAIL_PCT: 0.60% (was 0.30%, commit dacebfb0)
- ATR_SL_MIN: 1.5%, ATR_SL_MAX: 2.5%
- TRAILING_ACTIVATION: 0.40%, TRAILING_DISTANCE: 1.20%

## Bug_hunter audit findings (commit 9ee72494)
- SOFT_TRAIL_PCT was the REAL cause of BTC/NEO/SOL stop-outs (0.3% trail)
- Size-reduce was bypassed by brain.py (now fixed)
- All protected flags intact, $11 floor solid

## YOUR DECISIONS NEEDED

1. **LONG SL widening**: sweep says 3-4%. Current fixes only go to 0.6%. Go wider? How far?
   - Risk: wider SL = bigger per-trade loss when stop hits
   - Reward: more winners develop (WR 68.6% at 4% vs 32.6% at 0.5%)

2. **pump-chain- SHORT**: loses at ALL SL levels. Disable? Or find a regime where it works?

3. **Per-signal SL optimization**: pump-chain+ LONG best at 10%, bb-bounce best at 1.5%. Implement?

4. **SOFT_TRAIL_PCT**: widened to 0.6%. Based on sweep, should it go wider?

5. **Hard_max_loss interaction**: CUT_LOSER_PNL is -4.0% account. At 5x leverage, that's -0.8% price. Does this cap conflict with wider SL recommendations?

6. **Any concerns** about commits 59b1aeec (chop floor) and dacebfb0 (SOFT_TRAIL_PCT + size-reduce fix)?

Write your decision to automation/ceo/ceo_report.md with a new section "SL Sweep Decision — 2026-10-21". Be direct. Lead with the decisions.
