# Arm-Breakeven-Stop Verdict (brain_auditor, 2026-10-17 18:50 UTC)

**Status: PRE-REGISTERED for v6 exit-stack / shadow. NOT ship-live (CEO: exit-stack = v6 vehicle, no standalone patch). 0 config changes.**

Creative from 12:20 run, executed by brain_auditor (self_learner dead — 8 consecutive undeliveries).
Script: `analysis/arm_breakeven_stop_2026-10-17.py`. 30d candle OOS, 778 trades, 19.6M 1m candles.

## Mechanism

Once unleveraged live_pnl touches +0.40% (= PM_TRAIL_ACTIVATE_PCT), if price ever returns
to <= entry (0.00%), counterfactual exit AT BREAKEVEN. Trades never armed, or never
round-tripping, keep actual outcome. Gap being filled: trail stop sits at peak-1.20%
(distance constant), so an armed trade can round-trip through entry to -0.80%+ /
D3 floor -3% acct before any trail cut. BE-stop caps give-back at 0 post-arm.

## Results (house bar: fk<=20% of ARMED winners, net>0, fired>=5; fees ignored)

| Cohort | armed_w | fired | fk% | NET$ | verdict |
|--------|---------|-------|-----|------|---------|
| UNIVERSE 30d | 346 | 184 | 16.5 | **+5.94** | **PASS** |
| non-EXTREME 30d | 207 | 71 | **9.7** | **+3.46** | **PASS** |
| EXTREME 30d | 139 | 113 | 26.6 | +2.48 | FAIL (fk) |
| pump-chain+ | 51 | 39 | 25.5 | +0.88 | FAIL (fk) |
| pump-chain- | 54 | 65 | 35.2 | +2.77 | FAIL (fk) |
| bb-bounce | 43 | 5 | 2.3 | +0.05 | PASS (thin) |
| volume- | 28 | 13 | 21.4 | -1.26 | FAIL |
| other | 116 | 56 | 13.8 | +3.44 | PASS |

## Split-sample OOS (15d/15d)

| Window | armed_w | fired | fk% | NET$ |
|--------|---------|-------|-----|------|
| OLD (d30-16) | 187 | 116 | 21.9 | +3.03 |
| NEW (d15-1) | 159 | 68 | 10.1 | +2.91 |
| OLD non-EXT | 103 | 46 | 12.6 | +2.11 |
| NEW non-EXT | 104 | 25 | 6.7 | +1.35 |

Net positive in BOTH halves (universe and non-EXTREME). fk% non-EXTREME passes bar in
both halves; universe OLD misses bar marginally (21.9%). Med arm->BE crossing: 13-23m.

## Findings

1. **The 12:20 hypothesis INVERTS on scope.** EXTREME armed-then-reverse was the flagged
   cohort, but EXTREME fails fk (26.6% — whipsaw recoveries). The clean scope is
   **non-EXTREME** (fk 6.7-12.6% across halves, net +$1.35-2.11/15d). Do NOT scope to EXTREME.
2. **Complements TAT, does not duplicate it.** TAT (exit-ladder grid, same day) cuts
   NEVER-ARMED stallers at fixed T — only bb-squeeze eligible; pump-chain- FAILed all
   cells. Arm-BE targets the other chop family: trades that PROVED momentum then gave it
   back. Different cohort, different mechanism, same bleed source.
3. **FK tail is small and identifiable:** fk avg cost ~$0.14; expensive fks concentrated
   in volume- (COMP +8.42% end, ben -0.94; SUPER +2.83%) and EXTREME pump-chain. Keep
   volume- family OUT of any shadow scope.
4. **CHIP anomaly noted:** trade #16151 pnl_usdt=0.00 with pnl_pct=+2.14% (lev 3) — data
   artifact, single row, does not move conclusions. bug_hunter minor.
5. **Deployment path (NOT this run):** (a) zero-behavior shadow collector in PM
   post-arm BE-crossing would-fire log (sibling to MFE-CUT / bb-bounce TAT shadows),
   scope non-EXTREME, exclude volume-; (b) v6 exit-stack integration with re-arm
   whipsaw + fee modeling; (c) CEO GO before any live flip. Shadow NOT shipped this run:
   resume-risk window (0 trades since 16:57 resume, 5+ unvalidated changes landing).

## Reuse

TAT-eligibility meta-rule (exit-ladder verdict, same day) still governs fixed-T cuts.
This mechanism needs its own screen: armed-rate >= 30% of cohort AND fk<=20% in BOTH
15d halves AND non-EXTREME net>0. Pre-registered here.
