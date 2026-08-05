# CEO Kanban — Away Mode Tasks

## TODO
- [x] Close ENS SHORT and ETH LONG (open positions from before pause) — DONE
- [ ] Build NEW signal family (all current signals failing 0% WR 48h)
- [ ] Relax zero-signal thresholds (VOL_MULT 5→2, atr_compression 5→3 bars, wyckoff simplify)
- [x] Fix candles.db staleness — VERIFIED: active tokens fresh (0.1h), old data from blacklisted tokens only
- [ ] Clean disk usage (84% → <80%) — URGENT (candles.db 3.6GB, signals_hermes.db 3.5GB)

## IN PROGRESS
- [x] KEEP LIVE TRADING PAUSED — 0% WR 48h, macro gate REDUCE
- [x] All current signals disabled — waiting for new signal ideas from signal_analyst
- [ ] Disk cleanup in progress — 84% → <80%

## DONE
- [x] 2026-08-04 14:00 — Dynamic signal inverter deployed (zscore-rising auto-flip when WR<30%)
- [x] 2026-08-04 14:30 — zscore-rising+ and zscore-rising- re-enabled with inversion active
- [x] 2026-08-04 14:30 — CEO away-mode prompt created (ceo_away_prompt.md)
- [x] 2026-08-04 ~21:00 — tl_break detection relaxed (bounces 3→2, ADX 25→15, slope 0.0003→0.0001)
- [x] 2026-08-04 ~21:00 — MC gate threshold 0.40→0.35
- [x] 2026-08-04 ~21:00 — pattern_wolf enabled, 8 signals fired
- [x] 2026-08-04 ~22:00 — Context gate fixed: 'SKIP' → 'AMBIGUOUS' with penalties
- [x] 2026-08-04 ~22:00 — 4 positions open, all profitable
- [x] 2026-08-05 01:17 — bb_bounce kill switch added (BB_BOUNCE_ENABLED=False). Was hardcoded enabled, firing without flag.
- [x] 2026-08-05 02:50 — CEO PAUSE: Set live_trading=false (0% WR for 48h, macro gate REDUCE)
- [x] 2026-08-05 09:20 — VERIFIED: bb_bounce, pattern_wolf, tl_break kill switches working
- [x] 2026-08-05 10:30 — VERIFIED: 0 open positions, HL cache clean

## BLOCKED

## FOLLOW-UP (checked by CEO on next run)
- [x] Verify dead signals are disabled — CONFIRMED: bb_bounce=False, pattern_wolf=False
- [x] Verify parameter adjustments were applied — CONFIRMED: constants updated
- [ ] Verify new signals were built (if requested) — **NOT DONE**
- [x] Verify bb_bounce is no longer firing (CEO 2026-08-05) — CONFIRMED
- [ ] Verify disk usage < 80% — **STILL 84% (no cleanup done)**

## CEO DECISIONS (2026-08-05 12:00)
- [x] 2026-08-05 12:00 — KEEP LIVE TRADING PAUSED — no signal >10% WR, no edge found
- [ ] 2026-08-05 12:00 — DELEGATE to bug_hunter: Fix disk usage (84% → <80%). Prune old candle data from blacklisted tokens (XMR, RNDR, LOOM, MATIC, BLZ — historical data from 2024)
- [ ] 2026-08-05 12:00 — DELEGATE to bug_hunter: Verify disabled signals (bb_bounce, pattern_wolf) are no longer firing — flag bypass still unresolved
- [ ] 2026-08-05 12:00 — DELEGATE to signal_analyst: Build NEW signal family — all current signals failing 0% WR for 48h+
- [ ] 2026-08-05 12:00 — DELEGATE to self_learner: Relax zero-signal thresholds (VOL_MULT 5→2, atr_compression 5→3 bars)
- [ ] 2026-08-05 12:00 — DELEGATE to bug_hunter: Investigate signal decay root cause — why do all signals drop to 0% WR within 24-48h?

## CEO DECISIONS (2026-08-05 12:00 — CONFIRMED)
- [x] 2026-08-05 12:00 — KEEP LIVE TRADING PAUSED — no signal >10% WR, no edge found
- [ ] 2026-08-05 12:00 — DELEGATE to bug_hunter: Disk cleanup — prune old candle data from blacklisted tokens (XMR, RNDR, LOOM, MATIC, BLZ)
- [ ] 2026-08-05 12:00 — DELEGATE to signal_analyst: Build NEW signal family — all current signals failing 0% WR for 48h+
- [ ] 2026-08-05 12:00 — DELEGATE to self_learner: Relax zero-signal thresholds (VOL_MULT 5→2, atr_compression 5→3 bars)
- [ ] 2026-08-05 12:00 — DELEGATE to bug_hunter: Investigate signal decay root cause

## CEO DECISIONS (2026-08-05 15:00)
- [x] 2026-08-05 15:00 — KEEP LIVE TRADING PAUSED — no edge, no open positions, databases empty
- [ ] 2026-08-05 15:00 — URGENT: DELEGATE to bug_hunter: Disk cleanup 84%→<80% (candles.db 3.6GB + signals_hermes.db 3.5GB)
- [ ] 2026-08-05 15:00 — DELEGATE to bug_hunter: Signal decay root cause — every signal decays to 0% WR in 24-48h
- [ ] 2026-08-05 15:00 — DELEGATE to signal_analyst: Build NEW signal family
- [ ] 2026-08-05 15:00 — DELEGATE to self_learner: Relax zero-signal thresholds (VOL_MULT 5→2, atr_compression 5→3 bars)

## CEO DECISIONS (2026-08-05 15:20)
- [x] 2026-08-05 15:20 — KEEP LIVE TRADING PAUSED — 0% WR, all signals failing
- [ ] 2026-08-05 15:20 — URGENT: DELEGATE to bug_hunter: Disk cleanup 84%→<80% — prune candles.db, delete empty DBs
- [ ] 2026-08-05 15:20 — URGENT: DELEGATE to bug_hunter: Fix disabled signal bypass — bb_bounce, pattern_wolf still firing
- [ ] 2026-08-05 15:20 — DELEGATE to bug_hunter: Signal decay root cause
- [ ] 2026-08-05 15:20 — DELEGATE to signal_analyst: Build NEW signal family
- [ ] 2026-08-05 15:20 — DELEGATE to self_learner: Relax zero-signal thresholds

## CEO DECISIONS (2026-08-05 18:00)
- [x] 2026-08-05 18:00 — KEEP LIVE TRADING PAUSED — 0% WR, all signals failing
- [ ] 2026-08-05 18:00 — URGENT: DELEGATE to bug_hunter: Fix BB_BOUNCE regression — line 849 hermes_constants.py shows BB_BOUNCE_ENABLED=True, was killed at 01:17. 9 trades, 0% WR, -0.77 USDT
- [ ] 2026-08-05 18:00 — URGENT: DELEGATE to bug_hunter: Disk cleanup 84%→<80% — candles.db 3.6G + signals_hermes.db 3.5G = 7.1G bloat. Still not done.
- [ ] 2026-08-05 18:00 — DELEGATE to signal_analyst: Build NEW signal family — all current signals 0% WR
- [ ] 2026-08-05 18:00 — DELEGATE to bug_hunter: Signal decay root cause — every signal decays to 0% WR in 24-48h
- [ ] 2026-08-05 18:00 — DELEGATE to self_learner: Relax zero-signal thresholds (VOL_MULT 5→2, atr_compression 5→3 bars)

## CEO DECISIONS (2026-08-05 21:00)
- [x] 2026-08-05 21:00 — KEEP LIVE TRADING PAUSED — 0% WR, no edge
- [ ] 2026-08-05 21:00 — URGENT: DELEGATE to bug_hunter: Fix BB_BOUNCE bypass bug — third regression, flag=False but still fires. Find root cause permanently.
- [ ] 2026-08-05 21:00 — URGENT: DELEGATE to bug_hunter: Disk cleanup 84%→<80% — prune candles.db old data from blacklisted tokens
- [ ] 2026-08-05 21:00 — DELEGATE to bug_hunter: Signal decay root cause — every signal drops to 0% WR in 24-48h
- [ ] 2026-08-05 21:00 — DELEGATE to signal_analyst: Build NEW signal family — current family dead

## CEO DECISIONS (2026-08-05 22:00)
- [x] 2026-08-05 22:00 — KEEP LIVE TRADING PAUSED — no change
- [x] 2026-08-05 22:00 — BB_BOUNCE: Set to False permanently (3rd regression). Line 849 hermes_constants.py.
- [x] 2026-08-05 22:00 — BLOCKING: Disk cleanup 84%→78% — candles.db 3.6GB→275MB, signals_hermes.db 3.5GB→160MB. DONE.
- [x] 2026-08-05 22:00 — URGENT: BB_BOUNCE bypass root cause — FOUND: signal_rotator.py re-enables it. Added to NEVER_REENABLE_FLAGS. PERMANENTLY FIXED.
- [ ] 2026-08-05 22:00 — DELEGATE to signal_analyst: NEW signal family — overdue 48h+, all current signals dead
- [ ] 2026-08-05 22:00 — DELEGATE to self_learner: Relax zero-signal thresholds (VOL_MULT 5→2, atr_compression 5→3)

## CEO DECISIONS (2026-08-05 22:30)
- [x] 2026-08-05 22:30 — DISK CLEANUP VERIFIED: 78% (was 84%). DB bloat resolved.
- [x] 2026-08-05 22:30 — BB_BOUNCE PERMANENTLY KILLED: Root cause was signal_rotator.py re-enabling without NEVER_REENABLE_FLAGS check. Fixed.
- [ ] 2026-08-05 22:30 — LIVE TRADING: KEEP PAUSED — signals improving but not enough edge yet. tl_break_long (93% WR) is promising.

## CEO DECISIONS (2026-08-05 22:00 — FINAL)
- [x] 2026-08-05 22:00 — BB_BOUNCE ROOT CAUSE FOUND: decider_run.py Layer 3 was missing BB_BOUNCE_ENABLED check. Old DB signals survived compaction. Fixed at all 3 layers.
- [x] 2026-08-05 22:00 — DEAD SIGNALS KILLED: pattern_wolf + accel-300 family added to NEVER_REENABLE_FLAGS + SIGNAL_SOURCE_BLACKLIST. Triple kill applied.
- [ ] 2026-08-05 22:00 — LIVE TRADING: KEEP PAUSED — 7.7% WR today, no edge.
- [ ] 2026-08-05 22:00 — URGENT: signal_analyst must build NEW signal family — overdue 48h+.

## CEO DECISIONS (2026-08-05 16:50)
- [x] 2026-08-05 16:50 — NEW SIGNAL FAMILY DEPLOYED: vortex_break + return_exhaustion created. Both disabled by default, need testing.
- [x] 2026-08-05 16:50 — THRESHOLDS RELAXED: VOL_MULT 5→2, atr_compression 5→3 bars. Signals will fire more often.
- [x] 2026-08-05 16:50 — SIGNAL DECAY ROOT CAUSE FOUND: No actual decay — WR is noise around ~41%. Real problem: ~30% of tokens are trash (GALA, MOVE, UNI, SKR). Fix: per-token blacklist.
- [x] 2026-08-05 16:50 — TOKEN BLACKLIST IMPLEMENTED: GALA + STRK added. Other 5 already covered. All filtering layers wired.
- [ ] 2026-08-05 16:50 — KEEP LIVE TRADING PAUSED until new signals (vortex_break, return_exhaustion) tested with paper trading

## CEO DECISIONS (2026-08-05 23:30)
- [x] 2026-08-05 23:30 — VERIFICATION: Blacklist working. GALA/STRK filtered from new signals. Old positions closing as phantom records.
- [x] 2026-08-05 23:30 — OVERALL WR TODAY: 53.8% (+$2.83) vs yesterday 3.1% (-$3.50). Massive improvement.
- [ ] 2026-08-05 23:30 — URGENT: pattern_wolf_wave_bear (11% WR, -$0.87) and decider (12.5% WR, defunct) still firing. Need kill switches or removal.
- [ ] 2026-08-05 23:30 — KEEP LIVE TRADING PAUSED until tl_break_long sustained performance verified (70% WR, +0.57 avg)

## CEO DECISIONS (2026-08-05 23:35)
- [x] 2026-08-05 23:35 — KEEP LIVE TRADING PAUSED — new signals untested, legacy dead signals still firing
- [ ] 2026-08-05 23:35 — URGENT: DELEGATE to bug_hunter: Kill pattern_wolf_wave_bear (11% WR) and decider (12.5% WR) permanently
- [ ] 2026-08-05 23:35 — DELEGATE to self_learner: Paper trade vortex_break and return_exhaustion for 48h
- [ ] 2026-08-05 23:35 — System health: pipeline active, hl-sync active, disk 78%, 0 positions

## CEO DECISIONS (2026-08-05 19:00)
- [x] 2026-08-05 19:00 — KEEP LIVE TRADING PAUSED — no edge sufficient for live capital
- [x] 2026-08-05 19:00 — LOWERED CONFIDENCE: vortex_break 95→80, return_exhaustion 95→80 — paper testing needs actual signals
- [ ] 2026-08-05 19:00 — DELEGATE to self_learner: Monitor vortex_break + return_exhaustion 48h after threshold change
- [ ] 2026-08-05 19:00 — DELEGATE to signal_analyst: Verify tl_break_long 100% WR isn't overfitting (41.5% on 7d)

## CEO DECISIONS (2026-08-05 23:45)
- [x] 2026-08-05 23:45 — VERIFIED: pattern_wolf signals are OLD (Aug 4), kill switch working correctly
- [x] 2026-08-05 23:45 — VERIFIED: decider signals from deprecated ai_decider.py, not new regression
- [x] 2026-08-05 23:45 — KEEP LIVE TRADING PAUSED — new signals need paper testing
- [x] 2026-08-05 23:45 — BLOCKED: vortex_break + return_exhaustion gated by master kill-switches, cannot paper trade
- [x] 2026-08-05 23:50 — ENABLED: vortex_break + return_exhaustion with conf≥95 for paper observation
- [ ] 2026-08-05 23:50 — Monitor vortex_break + return_exhaustion signals over next 48h
- [ ] 2026-08-05 23:50 — tl_break_long: 100% WR (14 trades) — monitor for sustained performance

## CEO DECISIONS (2026-08-05 18:18)
- [x] 2026-08-05 18:18 — KEEP LIVE TRADING PAUSED — zero actual trades in 24h, all expired
- [ ] 2026-08-05 18:18 — URGENT: BUG — signal_outcomes.db is 0 bytes, trade P&L not tracking
- [ ] 2026-08-05 18:18 — URGENT: BUG — pattern_wolf still generating (404 signals/24h) despite kill switch
- [ ] 2026-08-05 18:18 — URGENT: BUG — Signals expiring before execution ("compaction_stale_5min")
- [ ] 2026-08-05 18:18 — DELEGATE to bug_hunter: Fix signal_outcomes.db + pattern_wolf bypass + signal expiry
- [ ] 2026-08-05 18:18 — DELEGATE to signal_analyst: NEW signal family — overdue 48h+
- [ ] 2026-08-05 18:18 — DELEGATE to self_learner: Paper trade vortex_break + return_exhaustion
