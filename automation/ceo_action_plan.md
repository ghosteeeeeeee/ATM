# CEO Action Plan — 2026-08-06 02:15 UTC

## Status: LIVE · PROFITABLE · TIGHTENED

## Done (this session)
- [x] RE-ENABLE live trading — kill switch set true (was paused since 2026-08-05 02:50)
- [x] TIGHTEN trailing — activation 0.35%→0.30%, distance 0.80%→0.70%
- [x] UPDATE ceo_report.md with 24h performance snapshot

## Now (only)

| P | Action | Detail |
|---|--------|--------|
| P0 | MONITOR trailing impact | 0.30% activation may trigger too early on volatile tokens — watch for premature exits |
| P1 | WATCH tl_break_long decay | 100% WR (14 trades) historically decays to 0% within 24-48h |
| P1 | VERIFY return_exhaustion signals | Threshold lowered 80→70, should be firing now |
| P2 | VERIFY vortex_break signals | Window expanded 3→5, should be firing now |

## Locked Parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| ATR_SL_MIN_INIT | 1.0% | Matches exit behavior |
| TRAILING_ACTIVATION | 0.30% | CEO tightened 2026-08-06 |
| TRAILING_DISTANCE | 0.70% | CEO tightened 2026-08-06 |
| STOP_LOSS_DEFAULT | 1.0% | Hard fallback |
| MAX_OPEN_POSITIONS | 6 | Diversified |

## Signal Stance

| Signal | Stance | Evidence |
|--------|--------|----------|
| tl_break_long | ON, WATCH | 100% WR — decay imminent |
| zscore-rising± | ON | 55-63% WR, profitable |
| vel-hermes- | ON | 43.5% WR, +$0.47 |
| hzscore± | ON | Mixed but enabled |
| bb_bounce | DEAD | Asymmetric R:R, never re-enable |
| decider | DEAD | 11% WR, never re-enable |
| accel-300 family | DEAD | 0% WR, never re-enable |
| pattern_wolf | DEAD | 0% WR, never re-enable |

## Do not
- Pause live trading (boss directive: "Pausing is not an option")
- Re-enable dead signals
- Widen trailing without data evidence
- Chase losses with parameter thrash

## Follow-up (CEO next run)
- [ ] Check trailing stop-out frequency (too many premature exits?)
- [ ] Verify return_exhaustion and vortex_break generating signals
- [ ] tl_break_long WR decay check
