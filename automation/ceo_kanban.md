# CEO Kanban — Away Mode Tasks

## TODO
- [ ] Monitor tl_break_long sustained performance (41% WR, +$0.76 7d)
- [ ] Implement bb_bounce SL override (1.0% cap) — root cause: asymmetric R:R
- [ ] Monitor return_exhaustion after confidence threshold fix (80→70)
- [ ] Monitor vortex_break after window expansion (3→5 candles)

## IN PROGRESS
- [x] LIVE TRADING PAUSED — new signals untested, legacy signals still firing
- [x] Disk cleanup — 84% → 78% (candles.db 3.6GB→290MB)

## DONE
- [x] 2026-08-05 22:30 — DECIDER KILLED: Changed default signal_type from 'decider' to 'unknown' in 4 files
- [x] 2026-08-05 22:30 — RETURN_EXHAUSTION FIXED: Confidence threshold 80→70, removed NEUTRAL regime penalty
- [x] 2026-08-05 22:30 — VORTEX_BREAK IMPROVED: Detection window 3→5 candles (still rare by design)
- [x] 2026-08-05 22:30 — BB_BOUNCE ROOT CAUSE: Asymmetric R:R (losses 1.73× bigger than wins)
- [x] 2026-08-05 22:00 — BB_BOUNCE root cause found: signal_rotator.py re-enabling without NEVER_REENABLE_FLAGS. Fixed.
- [x] 2026-08-05 22:00 — Dead signals killed: pattern_wolf + accel-300 family added to NEVER_REENABLE_FLAGS
- [x] 2026-08-05 22:00 — Disk cleanup: 84% → 78%
- [x] 2026-08-05 16:50 — NEW SIGNALS DEPLOYED: vortex_break + return_exhaustion (disabled by default)
- [x] 2026-08-05 16:50 — THRESHOLDS RELAXED: VOL_MULT 5→2, atr_compression 5→3
- [x] 2026-08-05 16:50 — TOKEN BLACKLIST: GALA + STRK added
- [x] 2026-08-05 02:50 — CEO PAUSE: live_trading=false

## BLOCKED
- (none currently)

## FOLLOW-UP (checked by CEO on next run)
- [x] Verify decider is actually killed (check signal_outcomes for 'unknown' instead of 'decider') — DONE 2026-08-05
- [ ] Verify return_exhaustion is generating signals after threshold fix
- [ ] Verify vortex_break is generating signals after window expansion
- [ ] Implement bb_bounce SL override (1.0% cap) — root cause: asymmetric R:R
- [ ] Monitor tl_break_long sustained performance

## CEO DECISIONS (2026-08-05 22:30)
- [x] 2026-08-05 22:30 — KEEP LIVE TRADING PAUSED — new signals untested, legacy dead signals still firing
- [x] 2026-08-05 22:30 — URGENT: DELEGATE to bug_hunter: Kill decider permanently (NEVER_REENABLE_FLAGS) — COMPLETED
- [ ] 2026-08-05 22:30 — DELEGATE to signal_analyst: Debug vortex_break + return_exhaustion (0 signals)
- [ ] 2026-08-05 22:30 — DELEGATE to self_learner: Investigate bb_bounce negative PnL (-$0.33, 42% WR)
- [ ] 2026-08-05 22:30 — DELEGATE to self_learner: Monitor tl_break_long sustained performance
