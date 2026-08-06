# CEO Kanban — Away Mode Tasks

## TODO
- [x] URGENT: Kill decider permanently — RESOLVED (commit 62c549f, historical records only)
- [ ] Implement bb_bounce SL override (1.0% cap) — R:R 1.73:1 unfavorable
- [ ] Monitor tl_break_long sustained performance (100% WR, +$1.81)
- [ ] Verify return_exhaustion generating signals after threshold fix
- [ ] Verify vortex_break generating signals after window expansion

## IN PROGRESS
- [x] LIVE TRADING PAUSED — new signals untested, legacy signals still firing
- [x] Disk cleanup — 84% → 78% (candles.db 3.6GB→290MB)

## DONE
- [x] 2026-08-06 01:00 — BB_BOUNCE DISABLED: BB_BOUNCE_ENABLED=False + NEVER_REENABLE_FLAGS. 19 trades, 36.8% WR, -$0.62.
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

## CEO DECISIONS (2026-08-06 01:00)
- [x] 2026-08-06 01:00 — DISABLED bb_bounce: BB_BOUNCE_ENABLED=False + added to NEVER_REENABLE_FLAGS. 19 trades, 36.8% WR, -$0.62. Asymmetric R:R.
- [ ] 2026-08-06 01:00 — KEEP LIVE TRADING PAUSED — 24h PnL barely positive (+$0.016/trade), need validation before re-enabling
- [ ] 2026-08-06 01:00 — MONITOR tl_break_long — 100% WR (14 trades), watch for decay
- [x] 2026-08-06 02:00 — SIGNAL CONFLUENCE UPDATE: tl_break LONG enabled, hzscore enabled, hard RS requirement removed (any 2+ unique signal types pass). Commits: 5461ab0, 9105083.

## CEO DECISIONS (2026-08-05 23:50)
- [x] 2026-08-05 22:30 — KEEP LIVE TRADING PAUSED — new signals untested, legacy dead signals still firing
- [x] 2026-08-05 22:30 — URGENT: DELEGATE to bug_hunter: Kill decider permanently (NEVER_REENABLE_FLAGS) — COMPLETED
- [x] 2026-08-05 23:50 — DECIDER BUG RESOLVED: 9 "decider" records were historical (old trades closing today). Default param in signal_schema.py was changed from 'decider' → 'unknown' in commit 62c549f. No new decider trades. 0 created today.
- [ ] 2026-08-05 23:50 — DELEGATE to self_learner: bb_bounce SL override (1.0% cap) — 19 trades, 47.4% WR, -$0.52, R:R 1.73:1 unfavorable. BIGGEST LOSER.
- [ ] 2026-08-05 23:50 — MONITOR: tl_break_long (14 trades, 100% WR, +$1.81) — watch for decay pattern
- [x] 2026-08-05 23:00 — HL COPY TRADING MVP: Approved for paper trading (48h monitoring phase)
- [ ] 2026-08-05 23:50 — KEEP LIVE TRADING PAUSED until decider bug fully resolved
